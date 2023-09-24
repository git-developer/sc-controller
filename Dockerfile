ARG UBUNTU_RELEASE=latest
FROM ubuntu:$UBUNTU_RELEASE AS build-stage
RUN apt-get update && \
    linux_headers="$(apt-cache search --names-only '^linux-headers-[0-9]+\.[0-9]+\.[0-9]+(-[0-9]+)?$' | sort -V | tail -n 1 | cut -d ' ' -f 1)" && \
    apt-get install -y \
      curl file xz-utils zstd \
      gcc "${linux_headers}" python3-dev python3-setuptools \
      libacl1-dev imagemagick librsvg2-2 \
      zsync

COPY . /work
WORKDIR /work
ARG TARGET=/work/appimage

# Build and install
RUN python3 setup.py build --executable "/usr/bin/env python3" && \
    python3 setup.py install --single-version-externally-managed --prefix "${TARGET}/usr" --record /dev/null

# Provide input-event-codes.h as fallback for runtime systems without linux headers
RUN cp -a \
      "$(find /usr -type f -name input-event-codes.h -print -quit)" \
      "$(find "${TARGET}" -type f -name uinput.py -printf '%h\n' -quit)"

# Create symlinks with short names for static libraries
RUN suffix=".cpython-*-$(uname -m)-linux-gnu.so" && \
    find "${TARGET}/usr" -type f -path "*/site-packages/*${suffix}" \
    | while read -r path; do ln -sfr "${path}" "${path%${suffix}}.so"; done

# Put AppStream metadata into required location
RUN mkdir -p ${TARGET}/usr/share/metainfo && \
    cp scripts/sc-controller.appdata.xml "${TARGET}/usr/share/metainfo/"

# Convert icon to PNG (required for icons in .desktop file)
RUN convert -background none "${TARGET}/usr/share/pixmaps/sc-controller.svg" "${TARGET}/sc-controller.png"

# Copy start script
RUN cp -a scripts/appimage-AppRun.sh "${TARGET}/entrypoint"

# Store build metadata
ARG TARGETOS TARGETARCH TARGETVARIANT
RUN export "TARGETMACHINE=$(uname -m)" && printenv | grep ^TARGET >>.build-metadata.env

FROM scratch AS export-stage
COPY --from=build-stage /work/appimage /work/.build-metadata.env /
