# syntax=docker/dockerfile:1
ARG BASE_OS=ubuntu
ARG BASE_CODENAME=noble
FROM $BASE_OS:$BASE_CODENAME AS build-stage

# Download build dependencies
RUN <<EOR
  set -eu

  apt-get update
  apt-get install -y --no-install-recommends \
	  gcc \
	  librsvg2-bin \
	  linux-headers-generic \
	  python3-dev \
	  python3-setuptools \
	  python-is-python3
  apt-get clean && rm -rf /var/lib/apt/lists/*
EOR
# Prepare working directory and target
COPY . /work
WORKDIR /work
ARG TARGET=/build/usr
ARG DAEMON_VERSION
ARG GIT_DESCRIPTION

# Build and install
RUN <<EOR
  set -eu

  ##
  # Converts the output of `git describe` to a valid python version (PEP 440)
  #
  # Examples:
  # - v0.4.9.2                 -> 0.4.9.2
  # - ver0.4.8.11-3-123-g030686f -> 0.4.8.11.3.123.dev3172463
  #
  # References:
  # - https://packaging.python.org/en/latest/specifications/version-specifiers/#version-specifiers
  ##
  convert_git_description_to_python_version() {
    description="${1}"

    version="$(printf %s "${description%-g*}" | tr -c -s [0-9.] .)"
    version="${version#.}"
    version="${version%.}"
    hash="${description##*-g}"
    if [ "${hash}" != "${description}" ]; then
      version="${version}.dev$(printf %d "0x${hash}")"
    fi
    echo "${version}"
  }
  if [ -z "${DAEMON_VERSION-}" ] && [ "${GIT_DESCRIPTION-}" ]; then
    DAEMON_VERSION="$(convert_git_description_to_python_version "${GIT_DESCRIPTION}")"
  fi
  if [ "${DAEMON_VERSION-}" ]; then
    sed -i -E "s/^ *DAEMON_VERSION *= *.+/DAEMON_VERSION = \"${DAEMON_VERSION}\"/" scc/constants.py
  fi

  python setup.py build --executable "/usr/bin/env python3"
  python setup.py install --single-version-externally-managed --home "${TARGET}" --record /dev/null

  # Provide input-event-codes.h as fallback for runtime systems without linux headers
  cp -a \
	  "$(find /usr -type f -name input-event-codes.h -print -quit)" \
	  "$(find "${TARGET}" -type f -name uinput.py -printf '%h\n' -quit)"

  # Create short name symlinks for static libraries
  suffix=".cpython-*-$(uname -m)-linux-gnu.so"
  find "${TARGET}" -type f -path "*/site-packages/*${suffix}" \
    | while read -r path; do ln -sfr "${path}" "${path%${suffix}}.so"; done

  # Put AppStream metadata to required location according to https://wiki.debian.org/AppStream/Guidelines
  metainfo=/build/usr/share/metainfo
  mkdir -p "${metainfo}"
  cp -a scripts/sc-controller.appdata.xml "${metainfo}"

  # Convert icon to png format (required for icons in .desktop file)
  iconpath="${TARGET}/share/icons/hicolor/512x512/apps"
  mkdir -p "${iconpath}"
  rsvg-convert --background-color none -o "${iconpath}/sc-controller.png" images/sc-controller.svg
EOR

# Store build metadata
ARG TARGETOS TARGETARCH TARGETVARIANT
RUN export "TARGETMACHINE=$(uname -m)" && printenv | grep ^TARGET >>/build/.build-metadata.env

# Keep only files required for runtime
FROM scratch AS export-stage
COPY --from=build-stage /build /
