#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

VENV=".venv/bin"
PYINSTALLER="$VENV/pyinstaller"
SPEC="swuift_app.spec"
DIST_DIR="dist"
TARGET_ARCH="${1:-$(uname -m)}"

echo "========================================"
echo " SWUIFT macOS build"
echo " Target architecture: $TARGET_ARCH"
echo "========================================"

if [ "$TARGET_ARCH" != "arm64" ] && [ "$TARGET_ARCH" != "x86_64" ]; then
    echo "ERROR: target architecture must be arm64 or x86_64."
    exit 1
fi

"$VENV/python" build_assets.py
printf '%s\n' "${SWUIFT_BUILD_ID:-local-$(date -u +%Y%m%d%H%M%S)}" > BUILD_INFO

echo ""
echo "── Building for $TARGET_ARCH …"
arch "-$TARGET_ARCH" "$PYINSTALLER" "$SPEC" --noconfirm --clean

APP_PATH="${DIST_DIR}/SWUIFT.app"
DMG_PATH="${DIST_DIR}/SWUIFT_macOS_${TARGET_ARCH}.dmg"

if [ ! -d "$APP_PATH" ]; then
    echo "ERROR: $APP_PATH not found after build."
    exit 1
fi

if [ -n "${APPLE_SIGNING_IDENTITY:-}" ]; then
    echo "── Signing app with configured Developer ID …"
    codesign --force --deep --options runtime --timestamp \
        --sign "$APPLE_SIGNING_IDENTITY" "$APP_PATH"
    codesign --verify --deep --strict --verbose=2 "$APP_PATH"
else
    echo "NOTE: APPLE_SIGNING_IDENTITY is not configured; app remains unsigned."
fi

echo ""
echo "── Creating DMG …"
STAGE=$(mktemp -d)
cp -R "$APP_PATH" "$STAGE/"
hdiutil create \
    -volname "SWUIFT" \
    -srcfolder "$STAGE" \
    -ov \
    -format UDZO \
    "$DMG_PATH"
rm -rf "$STAGE"

if [ -n "${APPLE_NOTARY_PROFILE:-}" ] && [ -n "${APPLE_SIGNING_IDENTITY:-}" ]; then
    echo "── Submitting signed DMG for notarization …"
    xcrun notarytool submit "$DMG_PATH" --keychain-profile "$APPLE_NOTARY_PROFILE" --wait
    xcrun stapler staple "$DMG_PATH"
else
    echo "NOTE: notarization credentials are not configured; DMG is not notarized."
fi

echo ""
echo "── Build complete:"
echo "   $APP_PATH"
echo "   $DMG_PATH"
echo "========================================"
