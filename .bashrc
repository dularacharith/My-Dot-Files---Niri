# .bashrc

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
export XCURSOR_THEME="macOS"
export XCURSOR_SIZE=24

# Display system info with CharithD ASCII art on terminal launch
if [[ $- == *i* ]]; then
    fastfetch
fi

# Minimal modern prompt: "> " in home, "> path" in directories
__set_prompt() {
    local dir=""
    if [ "$PWD" != "$HOME" ]; then
        dir=' \w'
    fi
    local branch
    branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null)
    local git_info=""
    if [ -n "$branch" ]; then
        git_info=" \[\033[38;2;129;140;248m\]($branch)\[\033[0m\]"
    fi
    PS1="\[\033[38;2;56;189;248m\033[1m\]>\[\033[0m\]\[\033[38;2;192;132;252m\]${dir}\[\033[0m\]${git_info} "
}
PROMPT_COMMAND=__set_prompt

# Attach ble.sh autosuggestions
[[ ${BLE_VERSION-} ]] && ble-attach
