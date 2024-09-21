#!/usr/bin/env bash
set -euo pipefail

Red='\033[0;31m'
Green='\033[0;32m'
Yellow='\033[0;33m'
Purple='\033[0;35m'
NoColor='\033[0m'

C_MODULES=(uinput hiddrv sc_by_bt remotepad cemuhook)
C_VERSION_uinput=9
C_VERSION_hiddrv=5
C_VERSION_sc_by_bt=3
C_VERSION_remotepad=1
C_VERSION_cemuhook=1

function rebuild_c_modules() {
	echo "lib${1}.so is outdated or missing, building one"
	echo "Please wait, this should be done only once."
	echo ""
	# cpython-312-x86_64-linux-gnu
#	SOABI=$(python3 -c 'import sysconfig; print(sysconfig.get_config_var("SOABI").split("-")[0:2])');

	# lib.linux-x86_64-cpython-312 - directory where libuinput.so was just generated
	LIB=$( python3 -c 'import platform; import sysconfig; soabi = sysconfig.get_config_var("SOABI").split("-")[0:2]; print(f"lib.linux-{platform.machine()}-{soabi[0]}-{soabi[1]}")' )
	# .cpython-312-x86_64-linux-gnu.so
	EXT_SUFFIX=$( python3 -c 'import sysconfig ; print(sysconfig.get_config_var("EXT_SUFFIX"))' )
	for cmodRM in "${C_MODULES[@]}"; do
		if [[ -e build/${LIB}/lib${cmodRM}${EXT_SUFFIX} ]]; then
			rm "build/${LIB}/lib${cmodRM}${EXT_SUFFIX}"
		fi
	done

	# Force the build directory as it differs across different systems, setuptools on Debian bullseye with 3.9 happily builds withon the "cpython" part otherwise
	python3 setup.py build --build-lib "build/${LIB}"
	echo ""

	for cmodLN in "${C_MODULES[@]}"; do
		if [[ ! -e lib${cmodLN}.so ]] ; then
			ln -sf "build/${LIB}/lib${cmodLN}${EXT_SUFFIX}" "./lib${cmodLN}.so"
			echo -e "${Yellow}Symlinked ./lib${cmodLN}.so '->' build/${LIB}/lib${cmodLN}${EXT_SUFFIX}${NoColor}"
		fi
	done
	echo ""
}

function testDeps() {
	# Tests if dependencies are present on the system before attempting to build
	if ! command -v python3-config >/dev/null; then
		echo -e "${Red}python3-config not found, install it. ${Yellow}The package may be named python3-dev / python-dev on your distribution!${NoColor}"
		exit 1
	fi
	if ! python -c "import importlib.util; exit(0 if importlib.util.find_spec('usb1') is not None else 1)"; then
		echo -e "${Red}python3-libusb1 not found, install it. ${Yellow}The package may be named python-libusb1 on your distribution!${NoColor}"
		exit 1
	fi
	if ! python -c "import importlib.util; exit(0 if importlib.util.find_spec('setuptools') else 1)"; then
		echo -e "${Red}python3-setuptools not found, install it. ${Yellow}The package may be named python-setuptools on your distribution!${NoColor}"
		exit 1
	fi
	if ! python -c "import importlib.util; exit(0 if importlib.util.find_spec('gi') else 1)"; then
		echo -e "${Red}python3-gi not found, install it. ${Yellow}The package may be named python-gi on your distribution!${NoColor}"
		exit 1
	fi
	if ! python -c "import importlib.util; exit(0 if importlib.util.find_spec('cairo') is not None else 1)"; then
		echo -e "${Red}python3-gi-cairo not found, install it. ${Yellow}The package may be named python3-gobject or python-gobject on your distribution!${NoColor}"
		exit 1
	fi
	if ! python -c "import importlib.util; exit(0 if importlib.util.find_spec('ioctl_opt') is not None else 1)"; then
		echo -e "${Red}python3-ioctl-opt not found, install it. ${Yellow}The package may be named or python-ioctl-opt on your distribution, ioctl-opt on PyPi!${NoColor}"
		exit 1
	fi
	if ! python -c "import importlib.util; exit(0 if importlib.util.find_spec('evdev') is not None else 1)"; then
		echo -e "${Red}python3-evdev not found, install it. ${Yellow}The package may be named or python-evdev on your distribution!${NoColor}"
		exit 1
	fi
	# https://stackoverflow.com/a/48006925/8962143
	#import gi
	#gi.require_version("Gtk", "3.0")
	#from gi.repository import Gtk
	# + Another gi.require_version('Rsvg', '2.0') -> Rsvg -> gir1.2-rsvg-2.0 on Debian
#	if ! python -c "import importlib.util; exit(0 if (lambda: (__import__('gi').require_version('Gtk', '3.0') or __import__('gi').repository.Gtk)) is not None else 1)"; then
#		echo -e "${Red}gi.Gtk not found, install it. ${Yellow}The package may be named gtk3 or gir1.2-gtk-3.0 on your distribution!${NoColor}"
#		exit 1
#	fi
	if ! command -v x86_64-linux-gnu-gcc >/dev/null; then
		echo -e "${Red}x86_64-linux-gnu-gcc not found, install it. ${Yellow}The package is usually named gcc!${NoColor}"
		exit 1
	fi
}

testDeps

# Ensure correct cwd
cd "$(dirname "$0")"

# Check if c modules are compiled and actual
for cmod in "${C_MODULES[@]}"; do
	expected_version_str="C_VERSION_${cmod}"
	expected_version=$(eval echo "\$${expected_version_str}")
	if ! reported_version=$(PYTHONPATH="." python3 -c 'import os, ctypes; lib=ctypes.CDLL("./'lib${cmod}'.so"); print(lib.'${cmod}'_module_version())'); then
		echo -e "${Purple}Failed to check module version for ${Yellow}${cmod}${Purple}, rebuilding modules. If this message only shows once, this is normal!${NoColor}"
	fi
	if [[ "${reported_version}" != "${expected_version}" ]] ; then
		rebuild_c_modules "${cmod}"
		if ! reported_version=$(PYTHONPATH="." python3 -c 'import os, ctypes; lib=ctypes.CDLL("./'lib${cmod}'.so"); print(lib.'${cmod}'_module_version())'); then
			echo -e "${Red}Failed building ${Yellow}${cmod}${Red}, fatal error, exiting!${NoColor}"
			exit 1
		fi
	fi
done

# Set PATH
SCRIPTS="$(pwd)/scripts"
export PATH="${SCRIPTS}":"${PATH}"
export PYTHONPATH=".":"${PYTHONPATH-}"
export SCC_SHARED="$(pwd)"

# Start either the daemon in debug mode if first parameter is 'debug', or the regular sc-controller app
if [[ ${1-} == 'daemon' ]]; then
	# Kill any existing daemons before spawning our own
	pkill -f scc-daemon || true
	python3 'scripts/scc-daemon' debug
else
	python3 'scripts/sc-controller' $@
fi
