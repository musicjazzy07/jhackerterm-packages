#!/bin/bash
# Jhacker Theme Installer for Official Termux
# Run: curl -sL <url> | bash

echo "[*] Installing Jhacker Theme..."

# Create .termux directory
mkdir -p ~/.termux

# Install colors (neon green on black)
cat > ~/.termux/colors.properties << 'COLORS'
background=#000000
foreground=#39FF14
cursor=#39FF14
color0=#000000
color8=#555555
color1=#FF0000
color9=#FF5555
color2=#39FF14
color10=#39FF14
color3=#FFFF00
color11=#FFFF55
color4=#0000FF
color12=#5555FF
color5=#FF00FF
color13=#FF55FF
color6=#00FFFF
color14=#55FFFF
color7=#FFFFFF
color15=#FFFFFF
COLORS

# Add skeleton banner to .bashrc (if not already there)
if ! grep -q "JHACKER TERMINAL" ~/.bashrc 2>/dev/null; then
cat >> ~/.bashrc << 'BASHRC'

# Jhacker Skeleton Banner
if [[ $- == *i* ]]; then
clear
cat << 'SKULL'

    .-""-.
   / .--. \
  / /    \ \
  | |    | |
  | |.-""-.|
 ///`.::::.`\
 ||| ::/  \:: ;
 ||; ::\__/:: ;
  \\\ '::::' /
   `=':-..-'`

  -- JHACKER --
  neon // blood

SKULL
fi
BASHRC
fi

echo "[+] Done! Restart Termux to see the theme."
echo "[!] Go to Termux Settings if colors don't apply immediately."
