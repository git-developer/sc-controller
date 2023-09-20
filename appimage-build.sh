#!/bin/bash
APP="sc-controller"
EXEC="scc"
LIB="lib"

EVDEV_VERSION=1.6.1
[ x"$BUILD_APPDIR" == "x" ] && BUILD_APPDIR=$(pwd)/appimage
PYTHON_VERSION=$(python3 -c 'import sys; version=sys.version_info[:3]; print("{0}.{1}".format(*version))')
SITE_PACKAGES_PATH="/usr/${LIB}/python${PYTHON_VERSION}/site-packages"
SITE_PACKAGES64_PATH="$(echo "${SITE_PACKAGES_PATH}" | sed 's:/lib/:/lib64/:g')"

if [ -z ${SITE_PACKAGES_PATH} ]; then
  echo "Could not determine global site-packages path. Exiting";
  exit 1;
fi

function download_dep() {
	NAME=$1
	URL=$2
	if [ -e ../../${NAME}.obstargz ] ; then
		# Special case for OBS
		cp ../../${NAME}.obstargz /tmp/${NAME}.tar.gz
	elif [ -e ${NAME}.tar.gz ] ; then
		cp ${NAME}.tar.gz /tmp/${NAME}.tar.gz
	elif [ -e /tmp/${NAME}.tar.gz ] ; then
		echo "/tmp/${NAME}.tar.gz already downloaded"
	else
		curl -sSL -C - -o "/tmp/${NAME}.tar.gz" "${URL}"
	fi
}

function build_dep() {
	NAME="$1"
	mkdir -p /tmp/${NAME}
	pushd /tmp/${NAME}
	tar --extract --strip-components=1 -f /tmp/${NAME}.tar.gz
	PYTHONPATH=${BUILD_APPDIR}/${SITE_PACKAGES_PATH} python3 \
		setup.py install --optimize=1 \
		--prefix="/usr/" --root="${BUILD_APPDIR}"
	mkdir -p "${BUILD_APPDIR}/${SITE_PACKAGES_PATH}"
	python3 setup.py install --prefix="/usr/" --root="${BUILD_APPDIR}"
	popd
}

function unpack_dep() {
	NAME="$1"
	pushd ${BUILD_APPDIR}
	tar --extract --exclude="usr/include**" --exclude="usr/lib/pkgconfig**" \
			--exclude="usr/lib/python2.7**" -f /tmp/${NAME}.tar.gz
	popd
}

set -ex		# display commands, terminate after 1st failure

# Download deps
download_dep "python-evdev-${EVDEV_VERSION}" "https://github.com/gvalkov/python-evdev/archive/refs/tags/v${EVDEV_VERSION}.tar.gz"
download_dep "pylibacl-0.6.0" "https://github.com/iustin/pylibacl/releases/download/v0.6.0/pylibacl-0.6.0.tar.gz"
download_dep "python-gobject-3.36.1" "https://archive.archlinux.org/packages/p/python-gobject/python-gobject-3.36.1-1-x86_64.pkg.tar.zst"
download_dep "python-vdf-3.4" "https://github.com/ValvePython/vdf/archive/v3.4.tar.gz"
download_dep "libpng-1.6.34" "https://archive.archlinux.org/packages/l/libpng/libpng-1.6.34-2-x86_64.pkg.tar.xz"
download_dep "gdk-pixbuf-2.36.9" "https://archive.archlinux.org/packages/g/gdk-pixbuf2/gdk-pixbuf2-2.36.9-1-x86_64.pkg.tar.xz"
download_dep "libcroco-0.6.13" "https://archive.archlinux.org/packages/l/libcroco/libcroco-0.6.13-1-x86_64.pkg.tar.xz"
download_dep "libxml2-2.9.10" "https://archive.archlinux.org/packages/l/libxml2/libxml2-2.9.10-2-x86_64.pkg.tar.zst"
download_dep "librsvg-2.48.7" "https://archive.archlinux.org/packages/l/librsvg/librsvg-2%3A2.48.7-1-x86_64.pkg.tar.zst"
download_dep "icu-67.1" "https://archive.archlinux.org/packages/i/icu/icu-67.1-1-x86_64.pkg.tar.zst"
download_dep "zlib-1:1.2.12" "https://archive.archlinux.org/packages/z/zlib/zlib-1%3A1.2.12-2-x86_64.pkg.tar.zst"
download_dep "libffi-3.4.3" "https://archive.archlinux.org/packages/l/libffi/libffi-3.4.3-1-x86_64.pkg.tar.zst"
download_dep "cairo-1.17.6" "https://archive.archlinux.org/packages/c/cairo/cairo-1.17.6-2-x86_64.pkg.tar.zst"

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

build_dep "python-evdev-${EVDEV_VERSION}"
build_dep "pylibacl-0.6.0"
build_dep "python-vdf-3.4"
unpack_dep "python-gobject-3.36.1"
unpack_dep "libpng-1.6.34"
unpack_dep "gdk-pixbuf-2.36.9"
unpack_dep "libcroco-0.6.13"
unpack_dep "libxml2-2.9.10"
unpack_dep "librsvg-2.48.7"
unpack_dep "icu-67.1"
unpack_dep "zlib-1:1.2.12"
unpack_dep "libffi-3.4.3"
unpack_dep "cairo-1.17.6"

# Remove uneeded files
rm -f "${BUILD_APPDIR}/usr/${LIB}/gdk-pixbuf-2.0/2.10.0/loaders/libpixbufloader-ani.so"
rm -f "${BUILD_APPDIR}/usr/${LIB}/gdk-pixbuf-2.0/2.10.0/loaders/libpixbufloader-bmp.so"
rm -f "${BUILD_APPDIR}/usr/${LIB}/gdk-pixbuf-2.0/2.10.0/loaders/libpixbufloader-gif.so"
rm -f "${BUILD_APPDIR}/usr/${LIB}/gdk-pixbuf-2.0/2.10.0/loaders/libpixbufloader-icns.so"
rm -f "${BUILD_APPDIR}/usr/${LIB}/gdk-pixbuf-2.0/2.10.0/loaders/libpixbufloader-ico.so"
rm -f "${BUILD_APPDIR}/usr/${LIB}/gdk-pixbuf-2.0/2.10.0/loaders/libpixbufloader-jasper.so"
rm -f "${BUILD_APPDIR}/usr/${LIB}/gdk-pixbuf-2.0/2.10.0/loaders/libpixbufloader-jpeg.so"
rm -f "${BUILD_APPDIR}/usr/${LIB}/gdk-pixbuf-2.0/2.10.0/loaders/libpixbufloader-qtif.so"
rm -f "${BUILD_APPDIR}/usr/${LIB}/gdk-pixbuf-2.0/2.10.0/loaders/libpixbufloader-tga.so"
rm -f "${BUILD_APPDIR}/usr/${LIB}/gdk-pixbuf-2.0/2.10.0/loaders/libpixbufloader-tiff.so"
rm -R "${BUILD_APPDIR}/usr/lib/cmake"
rm -R "${BUILD_APPDIR}/usr/share/doc"
rm -R "${BUILD_APPDIR}/usr/share/gtk-doc"
rm -R "${BUILD_APPDIR}/usr/share/locale"
rm -R "${BUILD_APPDIR}/usr/share/man"
rm -R "${BUILD_APPDIR}/usr/share/thumbnailers"
rm -R "${BUILD_APPDIR}/usr/share/vala"
rm -R "${BUILD_APPDIR}/usr/share/icu"

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
    scripts/appimage-AppRun.sh >"${BUILD_APPDIR}/AppRun"
chmod +x ${BUILD_APPDIR}/AppRun

echo "Run appimagetool -n ${BUILD_APPDIR} to finish prepared appimage"
