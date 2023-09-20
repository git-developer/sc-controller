ARG UBUNTU_RELEASE=latest
FROM ubuntu:$UBUNTU_RELEASE AS build-stage
RUN apt-get update && \
    linux_headers="$(apt-cache search --names-only '^linux-headers-[0-9]+\.[0-9]+\.[0-9]+(-[0-9]+)?$' | sort -V | tail -n 1 | cut -d ' ' -f 1)" && \
    apt-get install -y \
      curl file xz-utils zstd \
      gcc "${linux_headers}" python3-dev python3-setuptools \
      libacl1-dev imagemagick librsvg2-2 \
      zsync

RUN curl -sSL -o /tmp/appimagetool.AppImage "https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-$(uname -m).AppImage" && \
    chmod +x /tmp/appimagetool.AppImage && \
    cd /opt && /tmp/appimagetool.AppImage --appimage-extract && \
    mv squashfs-root appimage-tool.AppDir && \
    ln -s /opt/appimage-tool.AppDir/AppRun /usr/bin/appimagetool && \
    rm /tmp/appimagetool.AppImage

COPY . /work
WORKDIR /work
RUN if [ ! -d /usr/include/linux ]; then \
      ln -s "$(find /usr -xdev -type f -name 'input-event-codes.h' -exec dirname '{}' \; -quit)" /usr/include/linux; \
    fi
RUN ./appimage-build.sh

ARG TARGETOS TARGETARCH TARGETVARIANT
RUN export "TARGETMACHINE=$(uname -m)" && printenv | grep ^TARGET >>.build-metadata.env
ARG APPIMAGE_VERSION=latest
ARG REPO_OWNER=Ryochan7
ARG APPIMAGE_UPDATE_INFO
RUN set -a && . ./.build-metadata.env && \
    update_info="${APPIMAGE_UPDATE_INFO:-gh-releases-zsync|${REPO_OWNER}|sc-controller|latest|sc-controller-*.glibc-${TARGETMACHINE}.AppImage.zsync}" && \
    appimagetool -n -u "${update_info}" appimage "sc-controller-${APPIMAGE_VERSION}.glibc-${TARGETMACHINE}.AppImage"

FROM scratch AS export-stage
COPY --from=build-stage /work/*.AppImage* /work/appimage /work/.build-metadata.env /
