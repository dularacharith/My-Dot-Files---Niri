#!/usr/bin/env bash
# Pinned header for Kitty terminal

# Hide cursor in header window
printf '\033[?25l'

# Clear screen in header window
printf '\033[2J\033[H'

# Print CharithD ASCII logo and stylized gradient divider
if [[ -f "$HOME/.config/fastfetch/charithd.txt" ]]; then
    cat "$HOME/.config/fastfetch/charithd.txt"
fi

# Life-cycle pipe to companion shell
FIFO="/tmp/kitty_header_${KITTY_PID:-$$}.fifo"
rm -f "$FIFO" 2>/dev/null
mkfifo "$FIFO" 2>/dev/null

# Read from pipe until companion shell closes it
cat "$FIFO" 2>/dev/null
rm -f "$FIFO" 2>/dev/null
