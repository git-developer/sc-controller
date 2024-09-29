"""SC-Controller - Scripts.

Contains code for most of what can be done using 'scc' script.
Created so scc-* stuff doesn't polute /usr/bin.
"""
from __future__ import annotations

import os
import subprocess
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
	from io import TextIOWrapper


from scc.tools import find_binary, init_logging, set_logging_level


class InvalidArguments(Exception):
	pass

def run_binary(binary_name: str, argv: list[str]) -> int:
	"""Run scc-daemon with passed parameters."""
	binary = find_binary(binary_name)
	child = subprocess.Popen([binary] + argv)
	child.communicate()
	return child.returncode

def cmd_daemon(argv0: str, argv: list[str]) -> int:
	"""Run scc-daemon with passed parameters."""
	return run_binary("scc-daemon", argv)


def help_daemon() -> int:
	"""Run scc-daemon --help."""
	return run_binary("scc-daemon", ["--help"])


def cmd_gui(argv0: str, argv: list[str]) -> int:
	"""Run sc-controller(GUI) with passed parameters."""
	return run_binary("sc-controller", argv)


def help_gui() -> int:
	"""Run sc-controller --help."""
	return run_binary("sc-controller", ["--help"])


def cmd_test_evdev(argv0: str, argv: list[str]) -> int:
	"""
	Evdev driver test. Displays gamepad inputs using evdev driver.

	Usage: scc test-evdev /dev/input/node
	Return codes:
	  0 - normal exit
	  1 - invalid arguments or other error
	  2 - failed to open device
	"""
	from scc.drivers.evdevdrv import evdevdrv_test
	return evdevdrv_test(argv)


def cmd_test_hid(argv0: str, argv: list[str]) -> int:
	"""
	HID driver test. Displays gamepad inputs using hid driver.

	Usage: scc test-hid vendor_id device_id
	Return codes:
	  0 - normal exit
	  1 - invalid arguments or other error
	  2 - failed to open device
	  3 - device is not HID-compatibile
	  4 - failed to parse HID descriptor
	"""
	from scc.drivers.hiddrv import hiddrv_test, HIDController
	return hiddrv_test(HIDController, argv)


def help_osd_keyboard() -> None:
	import_osd()
	from scc.osd.keyboard import Keyboard
	return run_osd_tool(Keyboard(), "osd-keyboard", ["--help"])


def cmd_osd_keyboard(argv0: str, argv: list[str]) -> None:
	"""Display on-screen keyboard."""
	import_osd()
	from scc.osd.keyboard import Keyboard
	return run_osd_tool(Keyboard(), argv0, argv)


def cmd_list_profiles(argv0: str, argv: list[str]) -> int:
	"""List available profiles.

	Usage: scc list-profiles [-a]

	Arguments:
		-a   Include names begining with dot
	"""
	from scc.paths import get_profiles_path, get_default_profiles_path
	paths = [ get_default_profiles_path(), get_profiles_path() ]
	include_hidden = "-a" in argv
	lst = set()
	for path in paths:
		try:
			for x in os.listdir(path):
				if x.endswith(".sccprofile"):
					if not include_hidden and x.startswith("."):
						continue
					lst.add(x[0:-len(".sccprofile")])
		except OSError:
			pass
	for x in sorted(lst):
		print(x)
	return 0


def cmd_set_profile(argv0: str, argv: list[str]) -> int:
	"""Set controller profile.

	Usage: scc set-profile [controller_id] "profile name"
	"""
	from scc.tools import find_profile

	if len(argv) < 1:
		show_help(command = "set_profile", out=sys.stderr)
		return 1
	s = connect_to_daemon()
	if s is None: return -1
	if len(argv) >= 2:
		profile = find_profile(argv[1])
		if profile is None:
			print("Unknown profile:", argv[1], file=sys.stderr)
			return 1
		print("Controller: %s" % (argv[0],), file=s)
		if not check_error(s): return 1
		print("Profile: %s" % (profile,), file=s)
		if not check_error(s): return 1
	else:
		profile = find_profile(argv[0])
		if profile is None:
			print("Unknown profile:", argv[0], file=sys.stderr)
			return 1
		print("Profile: %s" % (profile,), file=s)
		if not check_error(s): return 1
	return 0


def cmd_info(argv0: str, argv: list[str]) -> int:
	"""Display basic information about running driver."""
	s = connect_to_daemon()
	if s is None: return -1
	# Daemon already sends situable info, so this is mostly reading
	# until "Ready." message is received.
	global_profile = None
	any_controller = False
	while True:
		line = s.readline()
		if len(line) == 0:
			break
		line = line.strip("\r\n\t ")
		if line == "Ready.":
			break
		if line.startswith("Current profile:"):
			global_profile = line
			continue
		if line.startswith("Controller:"):
			continue
		if line.startswith("Controller profile:"):
			any_controller = True
		elif line.startswith("Error:"):
			print(line)
			break
		if ":" in line:
			print(line)
	if not any_controller and global_profile:
		print(global_profile)
	return 0


def cmd_dependency_check(argv0: str, argv: list[str]) -> int:
	"""Check if all required libraries are installed on this system."""
	try:
		import gi
		gi.require_version('Gtk', '3.0')
		gi.require_version('GdkX11', '3.0')
		gi.require_version('Rsvg', '2.0')
	except ValueError as e1:
		print(e1, file=sys.stderr)
		if "Rsvg" in str(e1):
			print("Please, install 'gir1.2-rsvg-2.0' package to use this application", file=sys.stderr)
		else:
			print("Please, install 'PyGObject' package to use this application", file=sys.stderr)
	except ImportError as e2:
		print(e2, file=sys.stderr)
		if "gi" in str(e2):
			print("Please, install 'PyGObject' package to use this application", file=sys.stderr)
		return 1
	try:
		import evdev
	except Exception as e:
		print(e, file=sys.stderr)
		print("Please, install python-evdev package to enable non-steam controller support", file=sys.stderr)
	try:
		import scc.lib.xwrappers as X
		X.Atom
	except Exception as e:
		print(e, file=sys.stderr)
		print("Failed to load X11 helpers, please, check your X installation", file=sys.stderr)
		return 1
	return 0


def cmd_lock_inputs(argv0: str, argv: list[str], lock: str = "Lock: ") -> int:
	"""Lock and print pressed buttons, pads and sticks.

	Locks controller inputs and prints buttons, pads and stick as they are
	pressed or moved on controller.

	Usage: scc lock-inputs [button1] [stick1] [button2] ... [buttonN]

	Available button, sticks and pads:
		A X B Y START C BACK RGRIP LGRIP   LB RB LT RT STICK LPAD RPAD

	Return codes:
		-1  - failed to connect to daemon
		-2  - failed to lock inputs
		-3  - connection terminated
		-4  - daemon reported error
	"""
	s = connect_to_daemon()
	if s is None: return -1
	try:
		while True:
			line = s.readline()
			if line == "":
				return -3
			elif line.startswith("Ready."):
				print(lock + " ".join([ x.upper() for x in argv ]), file=s)
				s.flush()
			elif line.startswith("Error:"):
				print(line.strip(), file=sys.stderr)
				return -4
			elif line.startswith("Fail:"):
				print(line.strip(), file=sys.stderr)
				return -2
			elif line.startswith("Event:"):
				data = line.strip().split(" ")
				try:
					print(" ".join(data[2:]), file=sys.stdout)
					sys.stdout.flush()
				except OSError:
					# Output closed, bail out
					return 0
	finally:
		s.close()


def cmd_print_inputs(argv0: str, argv: list[str], lock: str = "Lock: ") -> int:
	"""Print pressed buttons, pads and sticks.

	Prints controller inputs and prints buttons, pads and stick as they are
	pressed or moved on controller, without locking them exclusivelly.

	Usage: scc lock-inputs [button1] [stick1] [button2] ... [buttonN]

	Available button, sticks and pads:
		A X B Y START C BACK RGRIP LGRIP   LB RB LT RT STICK LPAD RPAD

	Return codes:
		-1  - failed to connect to daemon
		-2  - failed to lock inputs
		-3  - connection terminated
		-4  - daemon reported error
	"""
	return cmd_lock_inputs(argv0, argv, lock="Observe: ")


def connect_to_daemon() -> TextIOWrapper | None:
	"""Return socket connected to daemon or None if connection failed.

	Outputs error message in later case.
	"""
	import socket

	from scc.paths import get_daemon_socket
	try:
		s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
		s.connect(get_daemon_socket())
	except Exception as e:
		print("Connection to scc-daemon failed: %s" % (e, ), file=sys.stderr)
		return None
	return s.makefile(mode="rw")


def check_error(s) -> bool:
	"""
	Reads line(s) from socket until "OK." or "Fail:" is read.
	Then return True if message is "OK." or prints message to stderr
	and return False if message is "Fail:"
	"""
	s.flush()
	while True:
		line = s.readline()
		if len(line) == 0:
			print("Connection closed", file=sys.stderr)
			return False
		line = line.strip("\n\r\t ")
		if line == "OK.":
			return True
		if line.startswith("Fail:"):
			if "\\n" in line:
				line = line.replace("\\n", "\n")
			print(line, file=sys.stderr)
			return False


def sigint(*a) -> None:
	print("\n*break*")
	sys.exit(0)


def import_osd() -> None:
	import gi
	gi.require_version('Gtk', '3.0')
	gi.require_version('Rsvg', '2.0')
	gi.require_version('GdkX11', '3.0')


def run_osd_tool(tool, argv0: str, argv: list[str]) -> None:
	import signal, argparse
	signal.signal(signal.SIGINT, sigint)

	from scc.tools import init_logging
	from scc.paths import get_share_path
	init_logging()

	sys.argv[0] = "scc osd-keyboard"
	if not tool.parse_argumets([argv0] + argv):
		sys.exit(1)
	tool.run()
	sys.exit(tool.get_exit_code())


def show_help(command = None, out=sys.stdout) -> int:
	names = [ x[4:] for x in globals() if x.startswith("cmd_") ]
	max_len = max([ len(x) for x in names ])
	if command in names:
		if "help_" + command in globals():
			return globals()["help_" + command]()
		hlp = (globals()["cmd_" + command].__doc__ or "").strip("\t \r\n")
		if hlp:
			lines = hlp.split("\n")
			if len(lines) > 0:
				for line in lines:
					line = (line
						.replace("Usage: scc", "Usage: %s" % (sys.argv[0], )))
					if line.startswith("\t"): line = line[1:]
					print(line, file=out)
				return 0
	print("Usage: %s <command> [ arguments ]" % (sys.argv[0], ), file=out)
	print("", file=out)
	print("List of commands:", file=out)
	for name in sorted(names):
		hlp = ((globals()["cmd_" + name].__doc__ or "")
					.strip("\t \r\n")
					.split("\n")[0])
		print((" - %%-%ss %%s" % (max_len, )) % (
			name.replace("_", "-"), hlp), file=out)
	return 0


def main() -> None:
	init_logging()
	if len(sys.argv) < 2:
		sys.exit(show_help())
	if "-h" in sys.argv or "--help" in sys.argv:
		while "-h" in sys.argv:
			sys.argv.remove("-h")
		while "--help" in sys.argv:
			sys.argv.remove("--help")
		sys.exit(show_help(sys.argv[1].replace("-", "_") if len(sys.argv) > 1 else None))
	if "-v" in sys.argv:
		while "-v" in sys.argv:
			sys.argv.remove("-v")
		set_logging_level(True, True)
	else:
		set_logging_level(False, False)
	try:
		command = globals()["cmd_" + sys.argv[1].replace("-", "_")]
	except:
		print("Unknown command: %s" % (sys.argv[1], ), file=sys.stderr)
		sys.exit(show_help(out=sys.stderr))

	try:
		sys.exit(command(sys.argv[0], sys.argv[2:]))
	except KeyboardInterrupt:
		sys.exit(0)
	except InvalidArguments:
		print("Invalid arguments", file=sys.stderr)
		print("", file=sys.stderr)
		show_help(sys.argv[1], out=sys.stderr)
		sys.exit(1)
