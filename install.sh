#!/usr/bin/env bash
# Adds "NVIDIA GPU Toggle" to the application menu for the current user.
set -euo pipefail

# Works with or without sudo: under sudo, install for the user who ran it, not root.
if [ -n "${SUDO_USER:-}" ]; then
    exec sudo -u "$SUDO_USER" "$0" "$@"
fi

DIR="$(cd "$(dirname "$0")" && pwd)"
chmod +x "$DIR/gpu_toggle.py"
mkdir -p ~/.local/share/applications

cat > ~/.local/share/applications/gpu-toggle.desktop <<EOF
[Desktop Entry]
Type=Application
Name=NVIDIA GPU Toggle
Comment=Switch the NVIDIA GPU on or off (envycontrol)
Exec=$DIR/gpu_toggle.py
Icon=video-display
Terminal=false
Categories=Settings;System;
EOF

echo "Installed. Search for 'NVIDIA GPU Toggle' in Activities."
