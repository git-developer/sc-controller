FROM alpine AS build-stage
COPY . /build
WORKDIR /build
RUN apk add \
    bash coreutils tar zstd xz zlib-dev \
    python3 py3-setuptools python3-dev \
    gcc musl-dev linux-headers \
    acl-dev imagemagick
RUN ./appimage-build.sh
ARG TARGETOS TARGETARCH TARGETVARIANT
RUN export "TARGETMACHINE=$(uname -m)" && \
    printenv | grep ^TARGET >>.build-metadata.env

FROM scratch AS export-stage
COPY --from=build-stage /build/appimage /AppDir
COPY --from=build-stage /build/.build-metadata.env /
