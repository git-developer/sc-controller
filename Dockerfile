ARG UBUNTU_RELEASE=latest
FROM ubuntu:$UBUNTU_RELEASE AS build-stage

# Download build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
      gcc librsvg2-bin linux-headers-generic python3-dev python3-setuptools

# Prepare working directory and target
COPY . /work
WORKDIR /work
ARG TARGET=/build/usr

# Build and install
RUN python3 setup.py build --executable "/usr/bin/env python3" && \
    python3 setup.py install --single-version-externally-managed --prefix "${TARGET}" --record /dev/null

# Provide input-event-codes.h as fallback for runtime systems without linux headers
RUN cp -a \
      "$(find /usr -type f -name input-event-codes.h -print -quit)" \
      "$(find "${TARGET}" -type f -name uinput.py -printf '%h\n' -quit)"

# Create short name symlinks for static libraries
RUN suffix=".cpython-*-$(uname -m)-linux-gnu.so" && \
    find "${TARGET}" -type f -path "*/site-packages/*${suffix}" \
    | while read -r path; do ln -sfr "${path}" "${path%${suffix}}.so"; done

# Put AppStream metadata to required location
RUN mkdir -p "${TARGET}/share/metainfo" && \
    cp -a scripts/sc-controller.appdata.xml "${TARGET}/share/metainfo/"

# Convert icon to png format (required for icons in .desktop file)
RUN iconpath="${TARGET}/share/icons/hicolor/512x512/apps" && \
    mkdir -p "${iconpath}" && \
    rsvg-convert --background-color none -o "${iconpath}/sc-controller.png" "${TARGET}/share/pixmaps/sc-controller.svg"

# Store build metadata
ARG TARGETOS TARGETARCH TARGETVARIANT
RUN export "TARGETMACHINE=$(uname -m)" && printenv | grep ^TARGET >>/build/.build-metadata.env

# Keep only files required for runtime
FROM scratch AS export-stage
COPY --from=build-stage /build /
