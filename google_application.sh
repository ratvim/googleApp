#!/usr/bin/env bash
set -euo pipefail

CHROME_APP_ID="com.google.Chrome"
SANDBOX_APPS_DIR="$HOME/.var/app/${CHROME_APP_ID}/data/applications"
SANDBOX_ICONS_DIR="$HOME/.var/app/${CHROME_APP_ID}/data/icons"
HOST_APPS_DIR="$HOME/.local/share/applications"
HOST_ICONS_DIR="$HOME/.local/share/icons"
KWIN_RULES_FILE="$HOME/.config/kwinrulesrc"

echo "=== [1/5] Ensuring Directories & Permissions ==="
mkdir -p "$HOST_APPS_DIR" "$HOST_ICONS_DIR"
flatpak override --user --filesystem=xdg-data:create "${CHROME_APP_ID}" 2>/dev/null || true

echo "=== [2/5] Syncing .desktop Files & App Icons ==="
if [ -d "$SANDBOX_APPS_DIR" ]; then
    find "$SANDBOX_APPS_DIR" -maxdepth 1 -name "${CHROME_APP_ID}.flextop.*.desktop" -exec cp -u {} "$HOST_APPS_DIR/" \; 2>/dev/null || true
fi

if [ -d "$SANDBOX_ICONS_DIR" ]; then
    cp -ru "$SANDBOX_ICONS_DIR"/* "$HOST_ICONS_DIR/" 2>/dev/null || true
fi

echo "=== [3/5] Sanitizing Exec & TryExec Lines in Desktop Files ==="
shopt -s nullglob
desktop_files=("$HOST_APPS_DIR/${CHROME_APP_ID}.flextop."*.desktop)

if [ ${#desktop_files[@]} -eq 0 ]; then
    echo "No Chrome PWA .desktop files found in $HOST_APPS_DIR."
else
    for file in "${desktop_files[@]}"; do
        sed -i '/^TryExec=/d' "$file"
        app_id=$(basename "$file" | sed -E 's/.*chrome-([a-z0-9]+)-Default\.desktop/\1/')

        if [ -n "$app_id" ]; then
            clean_exec="Exec=flatpak run --command=/app/bin/chrome ${CHROME_APP_ID} --profile-directory=Default --app-id=${app_id}"
            sed -i "s|^Exec=.*|${clean_exec}|" "$file"
        fi
    done
    echo "Sanitized ${#desktop_files[@]} .desktop files."
fi

echo "=== [4/5] Configuring KWin Rules for Taskbar Icons ==="
if [ ${#desktop_files[@]} -gt 0 ]; then
    for file in "${desktop_files[@]}"; do
        full_name=$(grep -m1 '^Name=' "$file" | cut -d'=' -f2- | tr -d '\r')
        [ -z "$full_name" ] && continue

        desktop_id=$(basename "$file" .desktop)
        rule_group="PWA-${full_name// /_}"

        case "$full_name" in
            *"WhatsApp"*)
                title_keyword="WhatsApp"
                ;;
            *"Instagram"*)
                title_keyword="Instagram"
                ;;
            *"YouTube Music"*)
                title_keyword="YouTube Music"
                ;;
            *"YouTube"*)
                title_keyword="YouTube"
                ;;
            *"Google Drive"*)
                title_keyword="Drive"
                ;;
            *"Google Photos"*)
                title_keyword="Photos"
                ;;
            *"Google Chat"*)
                title_keyword="Chat"
                ;;
            *"Google One"*)
                title_keyword="Google One"
                ;;
            *)
                title_keyword=$(echo "$full_name" | awk '{print $1}')
                ;;
        esac

        echo "Configuring rule: $full_name (Title: '$title_keyword') -> $desktop_id"

        kwriteconfig6 --file "$KWIN_RULES_FILE" --group "$rule_group" --key "Description" "$full_name PWA Icon"
        kwriteconfig6 --file "$KWIN_RULES_FILE" --group "$rule_group" --key "wmclass" "${CHROME_APP_ID}"
        kwriteconfig6 --file "$KWIN_RULES_FILE" --group "$rule_group" --key "wmclassmatch" "1"
        kwriteconfig6 --file "$KWIN_RULES_FILE" --group "$rule_group" --key "title" "$title_keyword"
        kwriteconfig6 --file "$KWIN_RULES_FILE" --group "$rule_group" --key "titlematch" "2"
        kwriteconfig6 --file "$KWIN_RULES_FILE" --group "$rule_group" --key "desktopfile" "$desktop_id"
        kwriteconfig6 --file "$KWIN_RULES_FILE" --group "$rule_group" --key "desktopfilerule" "2"
    done
fi

echo "=== [5/5] Reloading KDE Plasma Cache & KWin ==="
kbuildsycoca6 --noincremental 2>/dev/null || update-desktop-database "$HOST_APPS_DIR" 2>/dev/null || true
dbus-send --session --dest=org.kde.KWin --type=method_call /KWin org.kde.KWin.reconfigure 2>/dev/null || true

echo "=== Synchronization complete. Instagram, YouTube, and all PWAs updated! ==="
