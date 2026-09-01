# Spec: Biweekly Tech Digest (project-wide)

**Revision 2.** Holds the areas that are the same for every module: tech stack, commands,
structure, code style, testing strategy, and global boundaries. Module specs
(`SPEC-<module-id>.md`) reference this and add only what is specific to them.

Index of modules and their dependency order: `CAPABILITY-MAP.md`.

## Objective

Every two weeks, email a digest of notable tech news from the trailing 14 days to a
self-serve subscriber list, with no human in the loop between generation and send.

**User:** people who want a periodic catch-up on tech without following it daily.

**Success looks like:** a run fires on schedule, produces 8–12 genuinely notable items all
published inside the window, and publishes a readable broadcast with working links — or
sends nothing at all and tells the operator why.

The last clause is load-bearing. Because nobody reviews the content before it reaches real
inboxes, *sending nothing* is always an acceptable outcome and *sending something wrong*
never is.

## Tech Stack

| Concern | Choice | Notes |
|---|---|---|
| Language | Python 3.12+ | |
| Packaging / venv | `uv` | `pyproject.toml`, `uv.lock` committed |
| LLM | `anthropic` (official Python SDK) | Default model `claude-opus-5`; see `SPEC-digest.md` |
| Newsletter platform | Buttondown-style product, via `httpx` | List, signup, opt-in, unsubscribe, fan-out. Adapter behind a port |
| HTTP | `httpx` | Already a transitive dep of the SDK |
| Templating | `jinja2` | For `render` — **only if** the platform takes HTML. Pending the T1 spike |
| Lint + format | `ruff` | |
| Types | `ty` | Matches the repo's installed MLOps skills. `mypy` is a drop-in swap |
| Tests | `pytest`, `pytest-cov`, `pytest-socket` | `pytest-socket` is what enforces "no network in CI" |
| Schedule | GitHub Actions `schedule:` cron | Weekly cron, biweekly decision in code — see `SPEC-runner.md` |

## Commands

```
uv sync --all-extras                                  # install
uv run pytest                                         # test (no network, no cost)
uv run pytest --cov=src/catchup --cov-report=term-missing
uv run pytest -m live                                 # opt-in; makes REAL, BILLED calls
uv run ruff check --fix .                             # lint
uv run ruff format .                                  # format
uv run ty check                                       # typecheck
uv run python -m catchup.digest --print               # generate a digest, print it
uv run python -m catchup.runner --dry-run             # full run, publish nothing
uv run python -m catchup.runner --send                # real; also needs CATCHUP_ALLOW_SEND=1
```

`uv run pytest` must pass with the network unplugged. A test that needs the network is
either mis-designed or belongs behind the `live` marker.

## Project Structure

```
CAPABILITY-MAP.md          → module index, dependency order, locked decisions
SPEC.md                    → this file
SPEC-<module-id>.md        → one per module, named by module id
superseded/                → specs replaced by a later map revision, kept for their reasoning
tasks/                     → plan.md and todo.md

src/catchup/
  digest/                  → Claude + web_search, schema, validation gates
  render/                  → email body composition
  broadcast/               → platform port + adapter, preflight, publish
  runner/                  → __main__, orchestration, run records

prompts/
  digest.md                → the digest prompt template (versioned; expected to churn)

tests/
  unit/                    → mirrors src/catchup/ package for package
  fixtures/api/            → recorded Claude API responses, keys scrubbed
  fixtures/golden/         → golden email bodies

runs/                      → run records, committed by the workflow as the audit log
.github/workflows/
  digest.yml               → the weekly cron that runs biweekly
  ci.yml                   → lint, typecheck, test on push
```

There is no `data/` directory and no subscriber file. The platform holds the list, so real
email addresses never enter this repository.

## Code Style

Frozen dataclasses at module boundaries, explicit types on everything public, pure
functions wherever the work is not I/O, and typed exceptions rather than sentinel returns.

```python
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date

logger = logging.getLogger(__name__)


class GateError(Exception):
    """Raised when a validation gate refuses to pass a digest along."""


@dataclass(frozen=True, slots=True)
class NewsItem:
    title: str
    url: str
    published_date: date


def within_window(
    items: tuple[NewsItem, ...], start: date, end: date
) -> tuple[NewsItem, ...]:
    """Drop items published outside [start, end). Pure — no clock, no network."""
    kept = tuple(i for i in items if start <= i.published_date < end)
    logger.info(
        "window gate", extra={"before": len(items), "after": len(kept)}
    )
    return kept
```

Conventions not obvious from the snippet:

- `from __future__ import annotations` at the top of every module.
- Functions that can fail partway raise; they do not return `None` to mean failure.
- No bare `except:`, and no `except Exception` without re-raising or logging the type.
- Anything that costs money (an API call) or reaches people (a publish) is logged with counts.
- Dates and times are injected, never read from the clock inside a pure function.

## Testing Strategy

| Level | Where | Rule |
|---|---|---|
| Unit | `tests/unit/` | Mirrors the package tree. No network, no filesystem outside `tmp_path` |
| Replay | `tests/unit/digest/` | Recorded API responses drive parsing and gate tests — deterministic and free |
| Golden | `tests/fixtures/golden/` | Rendered email bodies diffed against committed expected output |
| Live | marked `@pytest.mark.live` | Excluded by default. Real billed calls. Run by hand, never in CI |

Coverage floor: **90%** overall; **95%** for `digest`'s validation gates, which are pure
logic with no excuse for gaps.

`pytest-socket` disables sockets for the default suite, so a test that suddenly needs the
network fails loudly instead of quietly costing money.

## Boundaries

**Always**

- Run `uv run pytest` and `uv run ruff check` before committing.
- Read secrets from the environment (`ANTHROPIC_API_KEY`, platform API key); GitHub Actions
  supplies them as repository secrets.
- Treat "abort the run" as a normal outcome with exit code 1, not a crash.
- Let the platform own anything to do with subscriber identity.

**Ask first**

- Adding a dependency.
- Changing the `Digest` dataclass — it is a cross-module contract.
- Raising the web-search `max_uses` cap or switching model — both change what a run costs.
- Changing the cron cadence or the anchor date.
- Anything that would require hosting a service.

**Never**

- Commit an API key or a `.env`.
- Store subscriber email addresses in this repository, in a run record, or in a log line.
- Publish a broadcast from a developer machine by accident: `--send` requires both the flag
  and `CATCHUP_ALLOW_SEND=1`, and `--dry-run` is the default.
- Ship a digest that failed a validation gate. Abort instead.
- Weaken a gate threshold to make a run pass.

## Success Criteria

1. `uv run pytest` passes with no network access and no API spend.
2. `uv run python -m catchup.runner --dry-run` produces a digest of 8–12 items, every
   `published_date` inside the 14-day window, every URL resolving.
3. A real run publishes one broadcast that reaches subscribers with a working unsubscribe.
4. A run whose gates fail publishes **nothing** and surfaces the reason to the operator.
5. Re-running the same period does not publish twice.
6. No secret and no subscriber address is present in git history.

## Open Questions

Revision 2 resolved the revision-1 questions about repo visibility, email provider, and the
unsubscribe mechanism — the platform owns all three.

1. **Which newsletter platform**, confirmed against real capabilities rather than
   expectation. Settled by the T1 spike.
2. **Anchor date** for the biweekly cadence. Suggest the date of the first successful
   manual send. Needed before the schedule is enabled.
3. **Editorial scope** — "tech news" is currently unbounded. Left to prompt iteration
   rather than encoded here.
