#!/usr/bin/env python3
"""
SC-Controller - Autoswitch Daemon

Observes active window and commands scc-daemon to change profiles as needed.
"""
from scc.x11.autoswitcher import AutoSwitcher
import sys, os, logging

log = logging.getLogger("AutoSwitcher-Daemon")

if __name__ == "__main__":
	from scc.tools import init_logging, set_logging_level
	from scc.paths import get_share_path
	init_logging(suffix=" AutoSwitcher")
	set_logging_level('debug' in sys.argv, 'debug' in sys.argv)

	if "DISPLAY" not in os.environ:
		log.error("DISPLAY env variable not set.")
		sys.exit(1)

	d = AutoSwitcher()
	d.run()
	sys.exit(d.exit_code)
