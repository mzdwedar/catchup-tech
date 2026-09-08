# Interests

What `/scrape` looks for and what it ignores. Edit freely — this file is the single
source of truth for scope, and nothing in the code assumes AI specifically.

Update interactively with `/setup --section interests`.

## Topics

Ordered roughly by how much you care. Scoring uses the order.

| Topic | Keywords |
|---|---|
| Frontier models and releases | model release, context window, benchmark, multimodal, reasoning model |
| Agents and tool use | agent, tool use, computer use, MCP, orchestration, long-horizon |
| Developer tooling | coding agent, IDE, SDK, inference API, evaluation, observability |
| Research results | scaling, interpretability, RL, post-training, distillation, architecture |
| Open models | open weights, license, fine-tuning, quantization, local inference |
| Compute and infrastructure | accelerator, datacenter, inference cost, serving, memory bandwidth |
| Safety and alignment | alignment, red-team, jailbreak, evaluation, model card, incident |
| Policy and regulation | AI act, export control, copyright ruling, procurement, standard |

## Always surface

Anything from these, even if it scores below the cutoff on topic match alone.

**Labs and vendors:** Anthropic, OpenAI, Google DeepMind, Meta AI, Mistral, Qwen,
DeepSeek, xAI, Hugging Face, NVIDIA

**People:** Simon Willison, Andrej Karpathy, Jeff Dean, Sasha Rush

## Exclude

Removed outright, not down-ranked.

- Funding rounds, valuations, and share-price commentary, unless the story is about what
  is being built rather than what it is worth
- Listicles: "top N tools", "N prompts that", "N ways AI will"
- Speculation with no artifact behind it — no paper, release, or announcement
- Reposts of an announcement already covered by its primary source this period
- Vendor content marketing dressed as research
- Personality and hiring drama with no technical substance
