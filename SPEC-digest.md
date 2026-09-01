# Spec: `digest`

Module id `digest` in `CAPABILITY-MAP.md`. Depends on nothing. Project-wide stack,
commands, structure, code style, and global boundaries: `SPEC.md`.

## Objective

Produce a **validated** structured digest of notable tech news published in the trailing
14 days, using Claude with the `web_search` server tool.

"Validated" is the whole job. Generating plausible-looking output is easy and the model
does it unprompted; this module's real responsibility is refusing to pass along output it
cannot stand behind. It returns data — it never sends anything.

## Window

`[run_date - 14 days, run_date)` — start inclusive, end exclusive.

Both bounds are injected into the prompt as **explicit ISO dates**, never as the phrase
"the past two weeks." The model has no reliable knowledge of today's date, and
`page_age` on search results is approximate ("April 30, 2025"), so the window has to be
stated and then enforced afterwards rather than trusted.

## API call

| Parameter | Value | Why |
|---|---|---|
| `model` | `claude-opus-5` (config: `CATCHUP_MODEL`) | Deferred decision; one config value to change |
| `tools` | `[{"type": "web_search_20260318", "name": "web_search", "max_uses": 20}]` | Latest variant: dynamic filtering keeps irrelevant page content out of context, and adds `response_inclusion` |
| `max_uses` | 20 | Hard cost ceiling. Search is **$10 per 1,000 searches** plus tokens |
| `response_inclusion` | `"excluded"` | Single-turn — we never echo raw search blocks back, so dropping them cuts output tokens |
| `output_config.format` | JSON schema below | Structured output is what makes per-item date and URL validation possible at all |
| `thinking` | `{"type": "adaptive"}` | Selection and ranking is exactly the kind of work that benefits |
| Streaming | yes, `.stream()` + `get_final_message()` | Search turns are long; avoids HTTP timeouts |
| Fallbacks | `betas=["server-side-fallback-2026-07-01"]`, `fallbacks="default"` | Safety classifiers can return `stop_reason: "refusal"` on a news request; without this a refusal is a failed run |

Do **not** separately declare the `code_execution` tool. On `web_search_20260209` and
later, dynamic filtering provisions it automatically, and a second execution environment
confuses the model.

### Response handling the SDK will not do for you

1. **`pause_turn`.** A long search turn can return `stop_reason: "pause_turn"`. Send the
   assistant message back **unchanged** to continue. Loop with a cap (5 continuations),
   then abort.
2. **Server-tool errors arrive as HTTP 200.** A failed search is a
   `web_search_tool_result` whose `content` is a single error **object**
   (`{"error_code": "max_uses_exceeded"}`) rather than a **list** of results. Branch on
   that before indexing, or you get a confusing `TypeError` instead of the real cause.
3. **`stop_reason: "refusal"`.** Check it before reading `content`; `stop_details.category`
   says why.
4. **Cost telemetry.** Record `usage.server_tool_use.web_search_requests`, input tokens,
   and output tokens on the returned `Digest`. Cost per run should be observable without
   opening a billing dashboard.

## Output schema

```json
{
  "type": "object",
  "additionalProperties": false,
  "required": ["items"],
  "properties": {
    "items": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["title", "url", "source", "published_date", "summary", "why_it_matters", "category"],
        "properties": {
          "title":          {"type": "string"},
          "url":            {"type": "string"},
          "source":         {"type": "string"},
          "published_date": {"type": "string", "description": "YYYY-MM-DD"},
          "summary":        {"type": "string", "description": "2-3 sentences"},
          "why_it_matters": {"type": "string", "description": "one sentence"},
          "category":       {"type": "string", "enum": ["ai", "hardware", "software", "security", "business", "science"]}
        }
      }
    }
  }
}
```

`category` exists so `render` can group items and the email stays skimmable.

## Validation gates

Run in order, after generation, before returning. Each gate either drops items or aborts.

| Gate | Rule | On failure |
|---|---|---|
| **G1 – count** | ≥ `MIN_ITEMS` (default 6), target 8–12 | Abort |
| **G2 – window** | `published_date` inside `[start, end)` | Drop the item |
| **G3 – liveness** | `HEAD` (falling back to `GET`) each URL, 10s timeout, ≤5 concurrent | Drop **only** on `404`/`410` or connection failure |
| **G4 – duplicates** | No repeated URL; no two titles with >0.9 similarity | Drop the later item |
| **G5 – recount** | After G2–G4, count still ≥ `MIN_ITEMS` | Abort |

**G3 deserves its explicit rule.** A `403` or `429` is bot protection, not evidence that
the page is missing — Cloudflare-fronted sites return them routinely to a `HEAD` from CI.
Dropping on `403` would silently gut the digest of exactly the mainstream sources it
should contain. Only a definitive `404`/`410` or a connection failure removes an item.

**Regeneration is capped at one.** If G1 or G5 aborts, the module may regenerate the
digest **once**, then abort for good. Uncapped retries double the bill and paper over a
prompt that has stopped working.

## Prompt

Lives at `prompts/digest.md`, versioned, loaded at runtime — never inlined in Python.
It is a template over `{period_start}`, `{period_end}`, `{max_items}`.

This is the file expected to churn most. Keeping it out of code means a prompt change is
a reviewable diff whose effect can be replayed against recorded fixtures.

## Interface

The contract `render` consumes:

```python
@dataclass(frozen=True, slots=True)
class NewsItem:
    title: str
    url: str
    source: str
    published_date: date
    summary: str
    why_it_matters: str
    category: Category


@dataclass(frozen=True, slots=True)
class Usage:
    web_search_requests: int
    input_tokens: int
    output_tokens: int


@dataclass(frozen=True, slots=True)
class Digest:
    period_start: date
    period_end: date
    generated_at: datetime
    items: tuple[NewsItem, ...]
    usage: Usage


def generate_digest(
    period: DateRange, cfg: DigestConfig, client: Anthropic
) -> Digest:
    """Generate, validate, return. Raises DigestGateError if a gate aborts."""


class DigestGateError(Exception):
    """Carries which gate failed and the item counts before and after."""
```

The `client` is injected rather than constructed here — that injection point is what
makes replay testing possible.

## Testing Strategy

The default suite makes **zero** API calls and costs nothing.

- **Recorded responses.** Real API responses are captured once into
  `tests/fixtures/api/*.json` with API keys scrubbed, then replayed through a fake client.
  Parsing, `pause_turn` continuation, error-object branching, and every gate are tested
  against them deterministically.
- **Hand-built fixtures for gate edges.** Out-of-window dates, a `403` URL, a `404` URL,
  near-duplicate titles, and a five-item thin result are constructed directly rather than
  hunted for in a recording.
- **`@pytest.mark.live`.** One end-to-end test that really calls the API. Excluded from
  CI, run by hand, costs roughly a dollar.

| Test | Asserts |
|---|---|
| Out-of-window item | Dropped by G2, absent from `Digest.items` |
| Thin result (5 items) | Raises `DigestGateError`, does **not** return a short digest |
| URL returning 403 | **Kept** — bot protection is not a dead link |
| URL returning 404 | Dropped |
| Duplicate URLs | One survives |
| `max_uses_exceeded` error object | Surfaces as a typed error, not `TypeError` |
| `pause_turn` response | Continuation sent unchanged; loop terminates |
| `stop_reason: "refusal"` | Raises before touching `content` |
| Regeneration cap | At most two generations, ever |
| Usage telemetry | `web_search_requests` and token counts populated |

Coverage floor for the gates: **95%**.

## Boundaries

**Always** — inject explicit ISO dates into the prompt; record `usage` on every run; keep
the prompt in `prompts/digest.md`; check `stop_reason` before reading `content`.

**Ask first** — changing `CATCHUP_MODEL`, raising `max_uses` above 20, changing the JSON
schema (it is `render`'s contract), lowering `MIN_ITEMS`.

**Never** — send email from this module; return items that failed a gate; retry
generation more than once; commit an unscrubbed API fixture; add `code_execution` to
`tools` alongside `web_search_20260209+`.

## Success Criteria

1. `generate_digest()` on recorded fixtures returns byte-identical output across runs.
2. No item in a returned `Digest` has a `published_date` outside the window — verified by
   a property test over generated dates, not a single example.
3. A thin or out-of-window-heavy response raises `DigestGateError` and returns nothing.
4. The full module suite runs with sockets disabled.
5. A live run reports its own cost: search count and token counts, both logged.
6. Changing `prompts/digest.md` requires no Python change.

## Risks

**R1 — structured outputs alongside web search citations is unverified.**
`output_config.format` is documented as incompatible with *document* citations, and web
search citations are always on. Whether they compose is not something I can settle from
the docs. **First task in this module is a ~15-minute spike: one real API call with both
enabled.** If it returns 400, the fallback is a two-pass design — pass 1 searches and
returns prose with citations, pass 2 (no tools) restructures it into the schema. That
roughly doubles token cost per run, from ~$1 to ~$2, and stays negligible at 26 runs a
year. Do not write the rest of the module before this spike resolves.

**R2 — `page_age` imprecision leaks stale items.** Mitigated by G2, but G2 depends on the
model reporting `published_date` honestly. If live runs show it inventing dates, the
fallback is fetching each item's page and reading its published metadata — real work,
deferred until there is evidence it is needed.

**R3 — search variance makes "did my prompt change help?" unanswerable.** Accepted
consequence of the chosen approach. Partly mitigated by replaying a fixed recording when
iterating on wording, which isolates prompt effects from search variance.

## Open Questions

1. **Model choice** — deferred by design. `claude-opus-5` is the default; a live A/B
   against a cheaper model is worth running once the gates are in place and can score the
   output objectively.
2. **Editorial scope** — "tech news" is currently unbounded. If the digest reads as
   scattered, the prompt gains an explicit topic weighting. Deliberately left to prompt
   iteration rather than encoded in the spec.
