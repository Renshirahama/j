#!/bin/sh
set -eu

PROJECT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
PLIST_DIR="/Users/$(id -un)/Library/LaunchAgents"
PLIST_PATH="$PLIST_DIR/com.juggler-analysis.daily.plist"

mkdir -p "$PLIST_DIR"
sed "s#__PROJECT_DIR__#$PROJECT_DIR#g" "$PROJECT_DIR/automation/com.juggler-analysis.daily.plist" > "$PLIST_PATH"
launchctl bootout "gui/$(id -u)" "$PLIST_PATH" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST_PATH"
launchctl kickstart -k "gui/$(id -u)/com.juggler-analysis.daily"
echo "scheduled: $PLIST_PATH"
