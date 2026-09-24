"""Process-wide handles so the web admin can apply live config without a reboot."""

from __future__ import annotations

from typing import Any

application: Any = None
loop: Any = None
restart_requested = False
