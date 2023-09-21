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
RUN if [ ! -d /usr/include/linux ]; then \
      ln -s "$(find /usr -xdev -type f -name 'input-event-codes.h' -exec dirname '{}' \; -quit)" /usr/include/linux; \
    fi
RUN ./appimage-build.sh

ARG TARGETOS TARGETARCH TARGETVARIANT
RUN export "TARGETMACHINE=$(uname -m)" && printenv | grep ^TARGET >>.build-metadata.env

FROM scratch AS export-stage
COPY --from=build-stage /work/appimage /work/.build-metadata.env /
