#!/usr/bin/env python3
import signal
import sys

def main() -> None:
	def sigint(*a):
		print("\n*break*")
		sys.exit(0)

	if __name__ == "__main__":
		signal.signal(signal.SIGINT, sigint)

		import gi
		gi.require_version('Gtk', '3.0')
		gi.require_version('Rsvg', '2.0')
		gi.require_version('GdkX11', '3.0')

		from scc.tools import init_logging
		from scc.paths import get_share_path
		init_logging()

		from scc.osd.message import Message
		m = Message()
		if not m.parse_argumets(sys.argv):
			sys.exit(1)
		m.run()
		sys.exit(m.get_exit_code())

if __name__ == "__main__":
	main()
