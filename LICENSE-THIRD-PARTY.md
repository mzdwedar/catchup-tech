# Third-party licenses

This repository vendors files that are not its own work. Their licenses and copyright
notices are reproduced below, as those licenses require.

## agent-skills

**Source:** https://github.com/addyosmani/agent-skills
**Version:** 0.6.8
**Copyright:** (c) 2025 Addy Osmani
**License:** MIT (full text below)

Vendored into this repository as byte-identical copies:

- `.claude/skills/*/SKILL.md` — 30 general engineering workflow skills
  (`test-driven-development`, `code-review-and-quality`, `spec-driven-development`, and
  others). These are **not** part of this project. The only skill authored here is
  `.claude/skills/ai-news-tracker/`, which holds this project's configuration.
- `.claude/references/*.md` — 7 checklists, including `definition-of-done.md`, which
  `tasks/plan.md` and several of the vendored skills reference by path.

They are checked in so the repository is self-contained: a clone gets the same working
setup without separately installing the plugin. If you already run the
`agent-skills` plugin, these duplicate it and can be removed — but update the
`definition-of-done.md` references in `tasks/plan.md` if you do.

### MIT License

MIT License

Copyright (c) 2025 Addy Osmani

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
