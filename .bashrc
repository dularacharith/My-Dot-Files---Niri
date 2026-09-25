# .bashrc

# Suppress keyboard echo during startup to prevent leaked keystrokes
[[ $- == *i* ]] && stty -echo 2>/dev/null

# ble.sh: Bash autosuggestions and line editor
[[ $- == *i* ]] && [ -f "$HOME/.local/share/blesh/ble.sh" ] && source "$HOME/.local/share/blesh/ble.sh" --noattach

# Source global definitions
if [ -f /etc/bashrc ]; then
    . /etc/bashrc
fi

# User specific environment
if ! [[ "$PATH" =~ "$HOME/.local/bin:$HOME/bin:" ]]; then
    PATH="$HOME/.local/bin:$HOME/bin:$PATH"
fi
export PATH

# Uncomment the following line if you don't like systemctl's auto-paging feature:
# export SYSTEMD_PAGER=

# User specific aliases and functions
if [ -d ~/.bashrc.d ]; then
    for rc in ~/.bashrc.d/*; do
        if [ -f "$rc" ]; then
            . "$rc"
        fi
    done
fi
unset rc
export PATH="$PATH:/opt/Antigravity/Antigravity-x64"

# Cursor theme configuration
export XCURSOR_THEME="macOS-White"
export XCURSOR_SIZE=24

# Reset any terminal margins from prior sessions to restore full scrollability
printf '\033[?6l\033[r' 2>/dev/null || true

# Display CharithD ASCII art with stylized gradient divider
_show_charithd_header() {
    if [ -f "$HOME/.config/fastfetch/charithd.txt" ]; then
        cat "$HOME/.config/fastfetch/charithd.txt"
    fi
}

# Display CharithD ASCII art on terminal launch
if [[ $- == *i* ]]; then
    _show_charithd_header
    # Flush any buffered keystrokes and restore echo
    read -t 0.01 -n 10000 discard 2>/dev/null || true
    stty echo 2>/dev/null
fi

# Re-anchor CharithD header at top when clearing or resetting terminal
clear() {
    command clear "$@"
    _show_charithd_header
}

reset() {
    command reset "$@"
    _show_charithd_header
}

# Modern minimalist prompt: sleek chevron, italic directory path, new-line prompt
__set_prompt() {
    local last_status=$?
    local chevron_color="\[\033[1;38;2;56;189;248m\]" # cyan
    if [ $last_status -ne 0 ]; then
        chevron_color="\[\033[1;38;2;248;113;113m\]" # coral red on error
    fi

    if [ "$PWD" != "$HOME" ]; then
        local branch
        branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null)
        local git_info=""
        if [ -n "$branch" ]; then
            git_info=" \[\033[2;38;2;114;122;160m\]($branch)\[\033[0m\]"
        fi
        # Line 1: Dim italic path in muted slate-violet + dim git branch
        # Line 2: Modern chevron prompt on new line
        PS1="\n\[\033[2;3;38;2;140;135;160m\]\w\[\033[0m\]${git_info}\n${chevron_color}❯\[\033[0m\] "
    else
        PS1="\n${chevron_color}❯\[\033[0m\] "
    fi
}
PROMPT_COMMAND=__set_prompt

# Attach ble.sh autosuggestions
if [[ $- == *i* ]] && [[ ${BLE_VERSION-} ]]; then
    ble-attach
fi

