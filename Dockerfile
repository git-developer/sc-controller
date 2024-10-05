# syntax=docker/dockerfile:1
ARG BASE_OS=ubuntu
ARG BASE_CODENAME=noble
FROM $BASE_OS:$BASE_CODENAME AS build-stage

# Download build dependencies
RUN <<EOR
	set -eu

	# Workaround for outstanding fix of https://bugs.launchpad.net/ubuntu/+source/python-build/+bug/1992108
	if grep -q ^UBUNTU_CODENAME=jammy /etc/os-release; then
		echo >>/etc/apt/sources.list.d/jammy-proposed.list 'deb [arch=amd64] http://archive.ubuntu.com/ubuntu/     jammy-proposed universe'
		echo >>/etc/apt/sources.list.d/jammy-proposed.list 'deb [arch=arm64] http://ports.ubuntu.com/ubuntu-ports/ jammy-proposed universe'
	fi

	apt-get update
	apt-get install -y --no-install-recommends \
		gcc \
		librsvg2-bin \
		linux-headers-generic \
		python3-dev \
		python3-setuptools \
		python3-venv \
		python-is-python3

	# Workaround for Focal lacking an apt package for python3-build
	dep=build
	package="python3-${dep}"
	if apt-cache search --names-only "^${package}$" | grep -q .; then
		apt-get install -y --no-install-recommends "${package}"
	else
		apt-get install -y --no-install-recommends python3-pip
		pip install "${dep}"
	fi

	apt-get clean && rm -rf /var/lib/apt/lists/*
EOR
# Prepare working directory and target
COPY . /work
WORKDIR /work
ARG TARGET=/build
ARG DAEMON_VERSION
ARG GIT_DESCRIPTION

# Build and install
RUN <<EOR
	set -eu

	##
	# Converts the output of `git describe` to a valid python version (PEP 440),
	# e.g. `v0.4.9.2` to `0.4.9.2` or `ver0.4.8.11-3-123-g030686f` to `0.4.8.11.3.123+g030686f`
	##
	convert_git_description_to_pep440() {
		description="${1}"
		hash="${description##*-g}"
		version="$(printf %s "${description%-g*}" | tr -c -s [0-9.] .)"
		version="${version#.}"
		version="${version%.}"
		if [ "${hash}" != "${description}" ]; then
			version="${version}+g${hash}"
		fi
		printf '%s\n' "${version}"
	}
	if [ -z "${DAEMON_VERSION-}" ] && [ "${GIT_DESCRIPTION-}" ]; then
		DAEMON_VERSION="$(convert_git_description_to_pep440 "${GIT_DESCRIPTION}")"
	fi
	if [ "${DAEMON_VERSION-}" ]; then
		sed -i -E "s/^ *DAEMON_VERSION *= *.+/DAEMON_VERSION = \"${DAEMON_VERSION}\"/" scc/constants.py
	fi

	python -m build --wheel
	python -m venv .env
	. .env/bin/activate
	pip install --prefix "${TARGET}/usr" dist/*.whl
	# fix shebangs of scripts from '#!/work/.env/bin/python'
	find "${TARGET}/usr/bin" -type f | xargs sed -i 's:work/.env:usr:'

	# Provide input-event-codes.h as fallback for runtime systems without linux headers
	cp -a \
		"$(find /usr -type f -name input-event-codes.h -print -quit)" \
		"$(find "${TARGET}" -type f -name uinput.py -printf '%h\n' -quit)"

	# Create short name symlinks for static libraries
	suffix=".cpython-*-$(uname -m)-linux-gnu.so"
	find "${TARGET}" -type f -path "*/site-packages/*${suffix}" \
		| while read -r path; do ln -sfr "${path}" "${path%${suffix}}.so"; done

	share="${TARGET}/usr/share"

	# Put AppStream metadata to required location according to https://wiki.debian.org/AppStream/Guidelines
	metainfo="${share}/metainfo"
	mkdir -p "${metainfo}"
	cp -a scripts/sc-controller.appdata.xml "${metainfo}"

	# Convert icon to png format (required for icons in .desktop file)
	iconpath="${share}/icons/hicolor/512x512/apps"
	mkdir -p "${iconpath}"
	rsvg-convert --background-color none -o "${iconpath}/sc-controller.png" images/sc-controller.svg
EOR

# Store build metadata
ARG TARGETOS TARGETARCH TARGETVARIANT
RUN export "TARGETMACHINE=$(uname -m)" && printenv | grep ^TARGET >>/build/.build-metadata.env

# Keep only files required for runtime
FROM scratch AS export-stage
COPY --from=build-stage /build /
