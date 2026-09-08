#!/usr/bin/env python3
"""Discovery shim for `feed-search`.

Source tools live at a predictable path so /scrape can find them without being told
they exist — the same convention ai-job-search uses for its portal tools. The logic is
in `catchup.tools.feed_search` so it stays inside the tested package.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

from catchup.tools.feed_search import main

if __name__ == "__main__":
    raise SystemExit(main())
