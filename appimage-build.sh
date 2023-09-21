#!/bin/bash
set -eu

APP="sc-controller"
EXEC="scc"
LIB="lib"

BUILD_APPDIR="${BUILD_APPDIR:-${PWD}/appimage}"
PYTHON_VERSION=$(python3 -c 'import sys; version=sys.version_info[:3]; print("{0}.{1}".format(*version))')
SITE_PACKAGES_PATH=$(python3 -c "import os,sys; print([p for p in sys.path if p.endswith('-packages') and sys.prefix in p][0])")
#SITE_PACKAGES_PATH="/usr/${LIB}/python${PYTHON_VERSION}/site-packages"
SITE_PACKAGES64_PATH="$(echo "${SITE_PACKAGES_PATH}" | sed 's:/lib/:/lib64/:g')"

set -x		# display commands

# Prepare & build deps
export PYTHONPATH=${BUILD_APPDIR}/${SITE_PACKAGES_PATH}
mkdir -p "$PYTHONPATH"
if [[ $(grep ID_LIKE /etc/os-release) == *"suse"* ]] ; then
	# Special handling for OBS
	ln -s lib64 ${BUILD_APPDIR}/usr/lib
	export PYTHONPATH="${PYTHONPATH}:${BUILD_APPDIR}/${SITE_PACKAGES64_PATH}"
	LIB=lib64
	SITE_PACKAGES_PATH="usr/${LIB}/python${PYTHON_VERSION}/site-packages"
fi

# Build important part. Need executable flag to place custom interpreter line.
# Setuptools overrrides original #! line in scripts with /usr/bin/python.
# Ubuntu 22.04 LTS does not provide an executable at /usr/bin/python
# by default.
python3 setup.py build --executable "/usr/bin/env python3"

# Need to use single-version-externally-managed due to setuptools behavior
python3 setup.py install --single-version-externally-managed --prefix ${BUILD_APPDIR}/usr --record /dev/null

# Move udev stuff
mv ${BUILD_APPDIR}/usr/lib/udev/rules.d/69-${APP}.rules ${BUILD_APPDIR}/
rmdir ${BUILD_APPDIR}/usr/lib/udev/rules.d/
rmdir ${BUILD_APPDIR}/usr/lib/udev/
mkdir -p ${BUILD_APPDIR}/${SITE_PACKAGES_PATH}/scc/
cp "/usr/include/linux/input-event-codes.h" ${BUILD_APPDIR}/${SITE_PACKAGES_PATH}/scc/

# Move & patch desktop file
mv ${BUILD_APPDIR}/usr/share/applications/${APP}.desktop ${BUILD_APPDIR}/
sed -i "s/Icon=.*/Icon=${APP}/g" ${BUILD_APPDIR}/${APP}.desktop
sed -i "s/Exec=.*/Exec=.\/usr\/bin\/scc gui/g" ${BUILD_APPDIR}/${APP}.desktop

# Convert icon
convert -background none ${BUILD_APPDIR}/usr/share/pixmaps/${APP}.svg ${BUILD_APPDIR}/${APP}.png

# Copy appdata.xml
mkdir -p ${BUILD_APPDIR}/usr/share/metainfo/
cp scripts/${APP}.appdata.xml ${BUILD_APPDIR}/usr/share/metainfo/${APP}.appdata.xml

# Make symlinks
for lib in libcemuhook libhiddrv libremotepad libsc_by_bt libuinput posix1e; do
  find "${BUILD_APPDIR}" -type f -name "${lib}.cpython-*-$(uname -m)-linux-gnu.so" | while read -r path; do
    ln -sfr "${path}" "$(dirname "${path}")/${lib}.so"
  done
done

# Copy AppRun script
sed -e "s:/usr/lib/python3.10/site-packages:${SITE_PACKAGES_PATH}:g" \
    -e "s:/usr/lib64/python3.10/site-packages:${SITE_PACKAGES64_PATH}:g" \
    scripts/appimage-AppRun.sh >"${BUILD_APPDIR}/entrypoint"
chmod +x ${BUILD_APPDIR}/entrypoint
