# Spec: `subscribers`

Module id `subscribers` in `CAPABILITY-MAP.md`. Depends on nothing. Project-wide stack,
commands, structure, code style, and global boundaries: `SPEC.md`.

## Objective

Answer one question correctly: **who receives this run?**

Given a hand-maintained roster and an append-only suppression record, produce the list of
`Recipient`s that `delivery` will send to. Every failure mode here is a person who either
gets an email they asked not to receive, or silently stops getting one they wanted.

## Data model

Two files, deliberately not one.

`data/subscribers.csv` — the roster. Append-mostly, edited by hand.

```csv
email,name,subscribed_at
ada@example.com,Ada Lovelace,2026-08-14
grace@example.org,,2026-08-20
```

`data/suppressions.csv` — the compliance record. Append-only, never edited by hand.

```csv
email,reason,suppressed_at
someone@example.com,unsubscribed,2026-08-28
bounced@example.net,hard_bounce,2026-08-30
```

`reason` is one of `unsubscribed`, `hard_bounce`, `complained`, `manual`.

**Why two files.** Deleting a row from the roster removes the address but destroys the
record of *why* it left — and a later re-add would silently resurrect someone who asked
to be removed. Keeping suppressions separate and append-only means suppression is
permanent unless a human deliberately overrides it.

## Rules

1. **Normalization.** Strip surrounding whitespace; lowercase the whole address.
   Lowercasing the local part is not RFC-strict but is universally safe in practice.
   **Do not** strip `+tags` or dots — `a+news@gmail.com` is a distinct deliverable
   address and collapsing it would drop a real subscriber.
2. **Validation.** Syntax-checked with `email-validator` in offline mode (no DNS lookup,
   so tests stay deterministic and CI stays network-free).
3. **A malformed address fails the load.** It does not get skipped with a warning. In a
   hand-edited file, a typo is a person who will never receive the email and nobody will
   ever notice. The error names the file and the line number.
4. **Duplicates collapse, with a warning.** Two rows normalizing to the same address is a
   human mistake, not a corrupt file — keep the earliest `subscribed_at` and log it.
5. **Suppression always wins.** An address in both files is excluded, regardless of
   `subscribed_at` ordering. There is no "re-subscribed after unsubscribing" path in v1;
   reinstating someone is a deliberate manual edit.
6. **An empty result is an error, not a quiet success.** Zero recipients means the roster
   is missing or misread; the run aborts rather than reporting a successful send of
   nothing.

## Interface

The contract `delivery` and `render` consume:

```python
@dataclass(frozen=True, slots=True)
class Recipient:
    email: str            # normalized
    name: str | None
    subscribed_at: date

    def masked(self) -> str: ...


class SuppressionReason(StrEnum):
    UNSUBSCRIBED = "unsubscribed"
    HARD_BOUNCE = "hard_bounce"
    COMPLAINED = "complained"
    MANUAL = "manual"


def load_recipients(roster: Path, suppressions: Path) -> list[Recipient]:
    """Active recipients, sorted by email. Raises RosterError on malformed input
    or an empty result."""


def suppress(
    email: str, reason: SuppressionReason, path: Path, *, at: date | None = None
) -> bool:
    """Append a suppression. Idempotent: returns False and appends nothing if the
    address is already suppressed. Never rewrites or removes existing rows."""


class RosterError(Exception): ...
```

`suppress()` is what `delivery` calls when the provider reports a hard bounce, and what
the operator calls by hand on an unsubscribe request.

## Testing Strategy

Pure logic, no network, no I/O outside `tmp_path`. Table-driven `pytest` cases.

| Test | Asserts |
|---|---|
| Suppressed address excluded | Present in roster + suppressions → absent from output |
| Case and whitespace variants | `" Ada@Example.COM "` and `ada@example.com` → one recipient |
| Plus-addressing preserved | `a+news@x.com` and `a@x.com` → **two** distinct recipients |
| Malformed address | Raises `RosterError` naming the file and line number |
| Empty roster | Raises `RosterError`, does not return `[]` |
| Duplicate rows | Collapse to one, earliest `subscribed_at` kept, warning logged |
| `suppress()` idempotence | Second call appends nothing, returns `False` |
| `suppress()` append-only | Pre-existing rows byte-identical afterwards |
| `masked()` | Never emits the full local part |
| Missing file | Raises `RosterError`, not `FileNotFoundError` |

Coverage floor for this module: **95%**.

## Boundaries

**Always** — validate before the run reaches the send path; keep suppression checks in
this module rather than in `delivery`.

**Ask first** — changing CSV columns (the user hand-edits these), adding a re-subscribe
path, relaxing rule 3 into a warning.

**Never** — delete or rewrite suppression rows; log a full email address; return an empty
recipient list as a success; normalize away `+tags`.

## Success Criteria

1. A suppressed address is provably unable to appear in `load_recipients()` output — the
   suppressed-address test is the one that must never be marked `xfail`.
2. Malformed roster input aborts the run with a message naming the file and line.
3. `suppress()` called twice with the same address leaves exactly one row.
4. Module test suite runs with sockets disabled and completes in under a second.
5. No test and no log line contains a full email address.

## Open Questions

1. Repo visibility and where the roster lives — inherited from `SPEC.md` Open Question 1.
   **Blocks the first real send, not this module's implementation.**
2. Should `hard_bounce` require two consecutive bounces before suppressing? v1 assumes a
   single hard bounce is definitive; soft bounces are never suppressed. Revisit if the
   provider's classification proves noisy.
