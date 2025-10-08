#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DIST_DIR="${PROJECT_ROOT}/dist"
TIMESTAMP="$(date +%Y%m%d%H%M%S)"
COMMIT_HASH="$(git -C "${PROJECT_ROOT}" rev-parse --short HEAD)"
PACKAGE_NAME="hubx-${TIMESTAMP}-${COMMIT_HASH}"
ARCHIVE_PATH="${DIST_DIR}/${PACKAGE_NAME}.tar"

mkdir -p "${DIST_DIR}"

git -C "${PROJECT_ROOT}" archive --format=tar --output="${ARCHIVE_PATH}" HEAD

gzip -f "${ARCHIVE_PATH}"

if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "${ARCHIVE_PATH}.gz" > "${ARCHIVE_PATH}.gz.sha256"
fi

printf '\nPacote gerado em %s.gz\n' "${ARCHIVE_PATH}"
if [[ -f "${ARCHIVE_PATH}.gz.sha256" ]]; then
    printf 'Checksum salvo em %s.gz.sha256\n' "${ARCHIVE_PATH}"
fi
