# syntax=docker/dockerfile:1
ARG BASE_OS=ubuntu
ARG BASE_CODENAME=noble
FROM $BASE_OS:$BASE_CODENAME
WORKDIR /tmp
COPY *.AppImage /opt/
RUN <<EOR
  set -eu

  log() {
    echo >&2 "${@}"
  }

  cancel() {
    log "${@}"
    return 1
  }

  handle_failure() {
    return_code="${1}"
    file="${2}"
    if [ "${return_code}" = 139 ] && echo "${file}" | grep -q -P -- '-(noble|trixie|bookworm)-'; then
       log "Ignoring failure ${return_code} for ${file}" \
           "which is currently known to cause a segmentation fault"
    else
      return "${return_code}"
    fi
  }

  main() {
    files="$(find /opt/ -maxdepth 1 -type f -name '*.AppImage')"
    if [ -z "${files}" ]; then
      cancel "Error: No AppImage file found."
    fi
    echo "${files}" | while read -r file; do
      log "${file}"
      chmod +x "${file}"
      rm -rf squashfs-root/
      "${file}" --appimage-extract >/dev/null
      (
       cd squashfs-root/runtime/compat
       ../../AppRun dependency-check || handle_failure "$?" "${file}"
      )
      rm -f "${file}"
    done
  }
  main "${@}"
EOR