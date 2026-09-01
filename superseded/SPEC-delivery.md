# Spec: `delivery`

Module id `delivery` in `CAPABILITY-MAP.md`. Depends on `render` and `subscribers`.
Project-wide stack, commands, structure, code style, and global boundaries: `SPEC.md`.

## Objective

Send a rendered digest to each active recipient, classify what happens, and record a
per-recipient outcome the runner can act on.

**Assumption, since `SPEC.md` Open Question 2 is still open:** the spec is written against
a provider **port**, with **Resend** as the assumed first adapter. Swapping to SES or
Postmark is then a new adapter class and a config value, not a rewrite. Correct me and
only the adapter changes.

## Sending model

**One message per recipient. Never BCC.** Three reasons, in order of importance: the
unsubscribe link is per-recipient and cannot be shared; BCC-to-a-list is a strong spam
signal; and 1:1 sends give per-recipient failure information that a single BCC send
cannot.

**Headers on every message:**

- `List-Unsubscribe: <mailto:unsubscribe@…?subject=unsubscribe>` (RFC 2369)
- `Precedence: bulk` — suppresses vacation auto-replies
- No `List-Unsubscribe-Post`. RFC 8058 one-click requires an HTTP endpoint, and there is
  no web service in this design. Adding one is `SPEC.md` Open Question 3.

**Rate limiting.** A token bucket at `CATCHUP_SEND_RATE` (default 2/second, matching
Resend's baseline). Irrelevant at a few dozen recipients, and the thing that saves the
run at a few thousand.

## Failure classification

| Outcome | Trigger | Action |
|---|---|---|
| `SENT` | Provider accepted | Record `provider_message_id` |
| `HARD_BOUNCE` | Permanent rejection, invalid recipient, 5.x.x | Record **and** call `subscribers.suppress(..., HARD_BOUNCE)` |
| `TRANSIENT` | 429, 5xx, timeout, 4.x.x soft bounce | Retry 3× with exponential backoff, then record as failed. **Never suppress** |
| `FATAL` | 401/403, malformed API key, provider config error | **Abort the entire batch immediately** |

`FATAL` aborts because an auth failure will fail for every recipient. Continuing would
burn the whole list against a broken credential and produce a report full of noise
concealing one real cause.

**Circuit breaker.** Abort the batch if the first 3 sends fail consecutively, or if the
failure rate exceeds 50% after 10 attempts. A systemic problem should stop the run, not
be discovered at recipient 400.

**Partial failure is not batch failure.** One recipient failing transiently must not stop
the other 99. The report carries the failures; the runner decides what that means.

## The bounce limitation, stated honestly

Most bounces are **asynchronous** — the provider accepts the message, then a bounce
arrives minutes later by webhook. With no web service there is nowhere to receive that
webhook.

So `HARD_BOUNCE` handling here covers only **synchronous** rejections. Asynchronous
bounces must be reconciled by the operator from the provider dashboard, running
`suppress()` by hand.

This is a real gap, not an oversight. It is acceptable at this scale, and it is written
down so nobody later assumes bounce handling is automatic. Closing it requires a webhook
endpoint — the same infrastructure as one-click unsubscribe, which is why those two
questions should be answered together if they are answered at all.

## Defense in depth

`delivery` re-checks the suppression list before every send, even though `subscribers`
already filtered. The check is cheap; sending to someone who unsubscribed is a compliance
failure. A suppressed address reaching this point raises `SuppressedRecipientError` and
aborts the batch, because it means an upstream invariant is broken.

## Interface

```python
class SendStatus(StrEnum):
    SENT = "sent"
    HARD_BOUNCE = "hard_bounce"
    TRANSIENT = "transient"
    FATAL = "fatal"


@dataclass(frozen=True, slots=True)
class SendOutcome:
    recipient_email: str
    status: SendStatus
    provider_message_id: str | None
    error: str | None


@dataclass(frozen=True, slots=True)
class DeliveryReport:
    outcomes: tuple[SendOutcome, ...]
    aborted: bool
    abort_reason: str | None

    @property
    def sent_count(self) -> int: ...


class EmailProvider(Protocol):
    def send(self, message: OutboundMessage) -> SendOutcome: ...


def send_digest(
    digest: Digest,
    recipients: Sequence[Recipient],
    cfg: DeliveryConfig,
    provider: EmailProvider,
    *,
    already_sent: frozenset[str] = frozenset(),
) -> DeliveryReport:
    """Render and send per recipient. Skips addresses in `already_sent`,
    which is how a resumed run avoids double-sending."""
```

**Two provider implementations ship:** `ResendProvider`, and `FileProvider`, which writes
`.eml` files to a directory instead of sending. `FileProvider` is what `--dry-run` uses,
so a dry run exercises the entire real path except the network call.

## Testing Strategy

No test in the default suite touches a network or a real provider.

| Test | Asserts |
|---|---|
| Happy path, 3 recipients | 3 `SENT`; each got a distinct unsubscribe link |
| Hard bounce | Recorded **and** `suppress()` called exactly once |
| Transient then success | Retried with backoff; final status `SENT` |
| Transient exhausted | `TRANSIENT` recorded; `suppress()` **not** called |
| `FATAL` on recipient 1 | Batch aborts; recipients 2+ never attempted |
| Circuit breaker | 3 consecutive failures → abort before recipient 4 |
| Partial failure | 1 of 5 fails transiently; other 4 still sent |
| Suppressed address slips through | Raises `SuppressedRecipientError` |
| `already_sent` | Listed addresses skipped, absent from outcomes |
| Rate limiter | N sends take ≥ expected wall time (clock injected, not slept) |
| `FileProvider` | Writes one parseable `.eml` per recipient |

The provider is a `Protocol`, so every one of these is a fake returning scripted
outcomes — fast and deterministic.

## Boundaries

**Always** — one message per recipient; re-check suppression before sending; record an
outcome for every recipient including failures; classify before retrying.

**Ask first** — the provider choice; changing the rate limit; changing retry counts;
adding a webhook receiver (that is new infrastructure, not a tweak).

**Never** — BCC; suppress on a transient failure; continue after `FATAL`; retry a hard
bounce; send without `List-Unsubscribe`; log a full email address.

## Success Criteria

1. Every recipient appears in `DeliveryReport.outcomes` exactly once.
2. A hard bounce results in exactly one new suppression row.
3. A transient failure never produces a suppression row.
4. `FATAL` on the first send means zero further API calls — asserted with a call counter.
5. `--dry-run` writes one `.eml` per recipient and makes no network call.
6. No full email address in any log line.

## Open Questions

1. **Provider** — assumed Resend. Affects only the adapter.
2. **Async bounce reconciliation** — manual in v1. Revisit if bounces become frequent.
3. **Send window** — should a large run pace itself over hours to protect sender
   reputation? Irrelevant below a few hundred recipients; note it for later.
