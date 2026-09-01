> **Pending revision.** Written under capability map revision 1, when this module rendered
> per-recipient and owned the unsubscribe link. Under revision 2 the platform performs fan-out,
> so `Recipient` leaves the signature and the unsubscribe link becomes a platform merge tag.
> Whether the body is HTML or markdown depends on the T1 spike. Rewrite tracked as **T8** in
> `tasks/todo.md`. Everything below is revision-1 text.

# Spec: `render`

Module id `render` in `CAPABILITY-MAP.md`. Depends on `digest`. Project-wide stack,
commands, structure, code style, and global boundaries: `SPEC.md`.

## Objective

Turn a `Digest` plus one `Recipient` into a subject line, an HTML body, and a plain-text
body that render correctly in real mail clients.

This module is pure: same inputs, same bytes out, no network, no clock. That is what
makes golden-file testing possible and what keeps `generated_at` an injected value rather
than a call to `now()`.

## Email HTML is not web HTML

The constraints below are not stylistic preferences; they are what mail clients enforce.

| Constraint | Reason |
|---|---|
| **Inline styles only** | Gmail strips `<style>` blocks in several delivery paths. A `<style>`-based design silently degrades to unstyled text for a chunk of readers |
| **No JavaScript, no external CSS, no web fonts** | Stripped or blocked everywhere. Font stacks only |
| **No images in v1** | Blocked by default in many clients, breaks layout when absent, and a lone image reads as a tracking pixel |
| **Max 600px, single column, percentage widths** | The width every client handles; single column removes the responsive problem instead of solving it |
| **Explicit `background-color` and `color` on every styled element** | Clients that force dark mode invert unspecified colors unpredictably |
| **Plain-text body is mandatory** | HTML-only mail is penalized by spam filters, and it is the accessible fallback. It must be a real rendering, not "view this in your browser" |

If a dependency (`premailer`) later proves necessary to inline styles from a stylesheet,
that is an **Ask first** per `SPEC.md`. v1 writes inline styles directly in the template.

## Security: LLM output reaching an HTML document

Item titles, summaries, and URLs originate from web pages, pass through a model, and land
in HTML sent to real people. Treat every field as untrusted.

1. **Jinja2 autoescape is on.** Not optional, and there is no `|safe` filter anywhere in
   these templates. A title containing `<` must render as text.
2. **URL scheme allowlist.** Every `href` is validated to be `http` or `https` before
   rendering. A `javascript:` or `data:` URI in an `href` is the one injection vector that
   survives autoescaping, because escaping the attribute value does not make the scheme
   safe. An item with a disallowed scheme is dropped and logged.
3. **No unescaped interpolation into the text body either.** Control characters are
   stripped; lines wrap at 78 characters.

## Composition

**Subject:** `Tech Catchup · {period_start:%b %-d} – {period_end:%b %-d}` — deterministic
and testable. A model-generated subject naming the top story would likely perform better
and is deliberately deferred; it would make the subject non-reproducible in golden tests.

**Preheader:** a visually hidden line at the top of the body supplying the inbox preview
snippet. Without one, clients preview whatever text comes first, usually "View in
browser" or the unsubscribe line.

**Body order:** greeting (uses `recipient.name` when present, otherwise no greeting rather
than "Hi there") → items grouped by `category`, in the category order defined in
`digest` → footer.

**Footer, required in both HTML and text:**
- Unsubscribe link (per-recipient — this is why `render` takes a `Recipient`)
- Sender postal address (legally required; `SPEC.md` Open Question 4)
- One line stating what this is and why they receive it

## Accessibility

- `lang` attribute on the root element.
- Layout tables carry `role="presentation"`.
- Link text is the article title, never "click here" or a bare URL.
- Body text ≥ 14px with contrast ratio ≥ 4.5:1 against its explicit background.
- Heading levels descend in order; category headings are real headings.

## Interface

```python
@dataclass(frozen=True, slots=True)
class RenderedEmail:
    subject: str
    html: str
    text: str


@dataclass(frozen=True, slots=True)
class RenderConfig:
    sender_name: str
    sender_postal_address: str
    unsubscribe_mailto: str      # e.g. "unsubscribe@example.com"
    accent_color: str = "#1a1a1a"


def render_email(
    digest: Digest, recipient: Recipient, cfg: RenderConfig
) -> RenderedEmail:
    """Pure. Raises RenderError if the digest has no renderable items."""


class RenderError(Exception): ...
```

## Testing Strategy

**Golden files.** A fixed `Digest` and `Recipient` render to
`tests/fixtures/golden/digest.html` and `digest.txt`, diffed byte for byte. Any styling
change shows up as a reviewable diff instead of a surprise in someone's inbox.

| Test | Asserts |
|---|---|
| Golden HTML / text | Byte-identical to committed fixtures |
| Title containing `<script>` | Rendered escaped; no live tag in output |
| Item with `javascript:` URL | Dropped, logged, not present in output |
| Recipient without a name | No greeting block, no "Hi there," no empty line |
| Two recipients, same digest | Bodies differ **only** in greeting and unsubscribe link |
| Unsubscribe + postal address | Present in **both** HTML and text |
| Text body | Contains every item title and URL; no HTML tags; lines ≤ 78 chars |
| Empty digest | Raises `RenderError` |
| Determinism | Same inputs twice → identical bytes |

Manual check before the first real send, not automatable here: view the golden HTML in
Gmail web, Gmail iOS, and Apple Mail. Cheap, and catches what no unit test will.

## Boundaries

**Always** — autoescape on; validate URL schemes; render both bodies; keep the module
pure.

**Ask first** — adding `premailer` or any dependency; introducing images; a
model-generated subject line.

**Never** — use `|safe` in these templates; call `datetime.now()`; emit an HTML body with
no text counterpart; send anything.

## Success Criteria

1. Golden fixtures reproduce byte for byte on any machine.
2. A crafted malicious title or URL cannot produce a live tag or a non-`http(s)` `href`.
3. Both bodies contain a working unsubscribe and the postal address.
4. Rendering is provably clock-independent — no `now()` in the module.
5. Suite runs with sockets disabled.

## Open Questions

1. Sender postal address and unsubscribe mailbox — inherited from `SPEC.md`. **Blocks the
   first real send, not implementation.**
2. Grouping by category versus one flat ranked list. Spec assumes grouped; a flat list is
   a template change only, decidable after seeing a real digest.
