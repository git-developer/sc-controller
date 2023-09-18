FROM archlinux/archlinux:base-devel AS build-stage

RUN pacman -Sy --noconfirm python-setuptools imagemagick librsvg zsync

RUN curl -sSL -o /tmp/appimagetool.AppImage "https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-$(uname -m).AppImage" && \
    chmod +x /tmp/appimagetool.AppImage && \
    cd /opt && /tmp/appimagetool.AppImage --appimage-extract && \
    mv squashfs-root appimage-tool.AppDir && \
    ln -s /opt/appimage-tool.AppDir/AppRun /usr/bin/appimagetool && \
    rm /tmp/appimagetool.AppImage

COPY . /work
WORKDIR /work
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
