#!/usr/bin/env python3
import os, sys, signal

def sigint(*a):
	print("\n*break*")
	sys.exit(-1)

def main():
	signal.signal(signal.SIGINT, sigint)

	import gi
	gi.require_version('Gtk', '3.0')
	gi.require_version('Rsvg', '2.0')
	gi.require_version('GdkX11', '3.0')

	from scc.tools import init_logging
	from scc.paths import get_share_path
	init_logging()

	from scc.osd.dialog import Dialog
	m = Dialog()
	if not m.parse_argumets(sys.argv):
		sys.exit(1)
	m.run()
	if m.get_exit_code() == 0:
		print(m.get_selected_item_id())
	sys.exit(m.get_exit_code())


if __name__ == "__main__":
	main()
