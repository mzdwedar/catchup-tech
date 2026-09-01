# Superseded specs

These were approved under **capability map revision 1** (static CSV roster, per-recipient
sending) and were replaced when the initiative moved to a hosted newsletter platform in
revision 2 on 2026-09-01.

| File | Replaced by | Why |
|---|---|---|
| `SPEC-subscribers.md` | the platform | The platform owns the list, signup, double opt-in, and unsubscribe. What remained on our side folded into `broadcast` |
| `SPEC-delivery.md` | `SPEC-broadcast.md` | The platform owns fan-out. Per-recipient sending, rate limiting, retry classification, the circuit breaker, and resume logic were all solving a problem we no longer have |

Kept rather than deleted: they record decisions and their reasoning, and there is no git
history here to recover them from.
