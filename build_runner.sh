#!/usr/bin/env bash
# ==============================================================================
# Build script for GoogleApp Native Standalone Web App Runner
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_TARGET="${HOME}/.local/bin/googleapp-runner"
LOCAL_TARGET="${SCRIPT_DIR}/googleapp-runner"

echo "==> Building GoogleApp Native Runner..."

if ! command -v g++ >/dev/null 2>&1; then
    echo "❌ Error: g++ compiler not found."
    exit 1
fi

if ! pkg-config --exists Qt6WebEngineQuick Qt6WebEngineCore Qt6Network Qt6Quick Qt6Gui KF6WindowSystem; then
    echo "❌ Error: Required Qt6/KF6 packages not found via pkg-config."
    exit 1
fi

FLAGS=($(pkg-config --cflags --libs Qt6WebEngineQuick Qt6WebEngineCore Qt6Network Qt6Quick Qt6Gui KF6WindowSystem))

g++ -O2 -fPIC "${SCRIPT_DIR}/googleapp_runner.cpp" "${FLAGS[@]}" -o "${LOCAL_TARGET}"

mkdir -p "$(dirname "${BIN_TARGET}")"
cp -f "${LOCAL_TARGET}" "${BIN_TARGET}"
chmod +x "${BIN_TARGET}"

echo "✅ googleapp-runner successfully built and installed to: ${BIN_TARGET}"
