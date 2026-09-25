#!/usr/bin/env bash
# ==============================================================================
# My-Dot-Files---Niri Installer Script
# Automated installer for Niri Wayland Compositor, Dank Material Shell (DMS),
# custom shaders, floating auto-stash daemon, snipping tool, and accessories.
# ==============================================================================

set -euo pipefail

# ANSI Colors
BOLD="\033[1m"
GREEN="\033[0;32m"
BLUE="\033[0;34m"
CYAN="\033[0;36m"
YELLOW="\033[1;33m"
RED="\033[0;31m"
NC="\033[0m"

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_DIR="$HOME/.config/dotfiles_backup_$(date +%Y%m%d_%H%M%S)"

echo -e "${BOLD}${CYAN}"
cat << 'EOF'
  _   _ _       _   ____        _    __ _ _           
 | \ | (_)_ __ (_) |  _ \  ___ | |_ / _(_) | ___  ___ 
 |  \| | | '__|| | | | | |/ _ \| __| |_| | |/ _ \/ __|
 | |\  | | |   | | | |_| | (_) | |_|  _| | |  __/\__ \
 |_| \_|_|_|   |_| |____/ \___/ \__|_| |_|_|\___||___/
EOF
echo -e "${NC}"
echo -e "${BOLD}Welcome to the Niri & Dank Material Shell Setup Installer${NC}\n"

# ------------------------------------------------------------------------------
# 1. Dependency checks & hints
# ------------------------------------------------------------------------------
check_dependencies() {
    log_info "Checking system dependencies..."
    
    local missing=()
    for cmd in niri dms python3 gcc make; do
        if ! command -v "$cmd" &>/dev/null; then
            missing+=("$cmd")
        fi
    done

    if [ ${#missing[@]} -gt 0 ]; then
        log_warn "The following recommended packages were not found in PATH: ${missing[*]}"
        echo ""
        if [ -f /etc/fedora-release ]; then
            echo -e "${YELLOW}To install dependencies on Fedora Linux, run:${NC}"
            echo "  sudo dnf copr enable avengemedia/dms"
            echo "  sudo dnf copr enable avengemedia/danklinux"
            echo "  sudo dnf install niri dms-cli quickshell ghostty kitty alacritty \\"
            echo "                   swaylock fastfetch cava python3 python3-pillow \\"
            echo "                   python3-gobject gtk4 gtk4-layer-shell gcc make wl-clipboard"
        elif [ -f /etc/arch-release ]; then
            echo -e "${YELLOW}To install dependencies on Arch Linux, run:${NC}"
            echo "  sudo pacman -S niri ghostty kitty alacritty swaylock fastfetch cava python \\"
            echo "                 python-pillow python-gobject gtk4 gcc make wl-clipboard"
            echo "  # Install DMS and quickshell from AUR (using yay or paru):"
            echo "  yay -S dms-bin quickshell-git gtk4-layer-shell"
        fi
        echo ""
        read -rp "Do you want to continue copying configurations anyway? [y/N]: " proceed
        if [[ ! "$proceed" =~ ^[Yy]$ ]]; then
            log_error "Installation aborted."
            exit 1
        fi
    else
        log_success "Core binaries detected."
    fi
}

# ------------------------------------------------------------------------------
# 2. Backup existing configurations
# ------------------------------------------------------------------------------
backup_existing() {
    log_info "Creating backup of existing configurations in: $BACKUP_DIR"
    mkdir -p "$BACKUP_DIR"

    local configs=(
        "niri"
        "DankMaterialShell"
        "environment.d"
        "alacritty"
        "ghostty"
        "kitty"
        "fastfetch"
        "swaylock"
        "cava"
        "dgop"
        "danksearch"
        "gtk-3.0"
        "gtk-4.0"
        "fish"
        "zsh"
        "vlc"
    )

    for cfg in "${configs[@]}"; do
        if [ -d "$HOME/.config/$cfg" ] || [ -f "$HOME/.config/$cfg" ]; then
            cp -r "$HOME/.config/$cfg" "$BACKUP_DIR/" 2>/dev/null || true
        fi
    done
    log_success "Backup completed."
}

# ------------------------------------------------------------------------------
# 3. Deploy configurations (.config)
# ------------------------------------------------------------------------------
deploy_configs() {
    log_info "Deploying ~/.config files..."

    mkdir -p "$HOME/.config"
    cp -r "$SCRIPT_DIR/.config/"* "$HOME/.config/"

    # Replace personal username in danksearch config if present
    if [ -f "$HOME/.config/danksearch/config.toml" ]; then
        sed -i "s|/home/[^/]*|$HOME|g" "$HOME/.config/danksearch/config.toml"
    fi

    # Deploy root dotfiles (.Xresources, .Xdefaults, .xprofile, .gtkrc-2.0, .icons)
    for f in .Xresources .Xdefaults .xprofile .gtkrc-2.0; do
        if [ -f "$SCRIPT_DIR/$f" ]; then
            cp "$SCRIPT_DIR/$f" "$HOME/$f"
        fi
    done
    if [ -f "$HOME/.xprofile" ]; then
        chmod +x "$HOME/.xprofile"
    fi
    if [ -d "$SCRIPT_DIR/.icons" ]; then
        mkdir -p "$HOME/.icons"
        cp -r "$SCRIPT_DIR/.icons/"* "$HOME/.icons/"
    fi

    log_success "~/.config and root dotfiles deployed successfully."
}

# ------------------------------------------------------------------------------
# 4. Deploy executables and scripts (~/.local/bin)
# ------------------------------------------------------------------------------
deploy_binaries() {
    log_info "Deploying scripts to ~/.local/bin..."

    mkdir -p "$HOME/.local/bin"
    cp -r "$SCRIPT_DIR/.local/bin/"* "$HOME/.local/bin/"
    chmod +x "$HOME/.local/bin/"*

    log_success "Scripts installed in ~/.local/bin."
}

# ------------------------------------------------------------------------------
# 5. Deploy Win-Snipping-Tool & Applications (~/.local/share)
# ------------------------------------------------------------------------------
deploy_local_share() {
    log_info "Deploying Win Snipping Tool and applications..."

    mkdir -p "$HOME/.local/share/win-snipping-tool"
    mkdir -p "$HOME/.local/share/applications"

    cp -r "$SCRIPT_DIR/.local/share/win-snipping-tool/"* "$HOME/.local/share/win-snipping-tool/"
    chmod +x "$HOME/.local/share/win-snipping-tool/snip_main.py"

    # Create / update symlink in ~/.local/bin
    ln -sf "$HOME/.local/share/win-snipping-tool/snip_main.py" "$HOME/.local/bin/win-snipping-tool"

    # Deploy icons (macOS cursor theme, application icons)
    if [ -d "$SCRIPT_DIR/.local/share/icons" ]; then
        mkdir -p "$HOME/.local/share/icons"
        cp -r "$SCRIPT_DIR/.local/share/icons/"* "$HOME/.local/share/icons/"
        mkdir -p "$HOME/.icons"
        if [ -d "$HOME/.local/share/icons/macOS" ]; then
            ln -sfn "$HOME/.local/share/icons/macOS" "$HOME/.icons/macOS"
        fi
    fi

    # Install desktop entries
    cp -r "$SCRIPT_DIR/.local/share/applications/"* "$HOME/.local/share/applications/"
    sed -i "s|/home/[^/]*/.local/bin/packettracer|packettracer|g" "$HOME/.local/share/applications/CiscoPacketTracer"*.desktop 2>/dev/null || true
    update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true

    # Flatpak sandbox overrides for cursor theme access
    if command -v flatpak &>/dev/null; then
        flatpak override --user --filesystem=xdg-data/icons:ro --filesystem=~/.icons:ro --env=XCURSOR_THEME=macOS --env=XCURSOR_SIZE=24 2>/dev/null || true
    fi

    log_success "Applications, desktop entries, and macOS cursor theme installed."
}

# ------------------------------------------------------------------------------
# 6. Cisco Packet Tracer Canvas Fix Library
# ------------------------------------------------------------------------------
build_packet_tracer_fix() {
    if [ -d "$SCRIPT_DIR/.local/src/pt_canvas_fix" ]; then
        log_info "Building Cisco Packet Tracer Wayland Canvas Fix library..."
        mkdir -p "$HOME/.local/src/pt_canvas_fix"
        mkdir -p "$HOME/.local/lib"
        cp -r "$SCRIPT_DIR/.local/src/pt_canvas_fix/"* "$HOME/.local/src/pt_canvas_fix/"

        if command -v gcc &>/dev/null; then
            make -C "$HOME/.local/src/pt_canvas_fix" TARGET="$HOME/.local/lib/libpt_canvas_fix.so"
            log_success "libpt_canvas_fix.so compiled and placed in ~/.local/lib/."
        else
            log_warn "gcc not found. Please compile ~/.local/src/pt_canvas_fix manually after installing gcc."
        fi
    fi
}

# ------------------------------------------------------------------------------
# 7. Install Wallpapers
# ------------------------------------------------------------------------------
deploy_wallpapers() {
    log_info "Deploying wallpapers..."
    local wp_dir="$HOME/Pictures/Wallpapers/Landscape"
    mkdir -p "$wp_dir"
    if [ -d "$SCRIPT_DIR/wallpapers" ]; then
        cp -r "$SCRIPT_DIR/wallpapers/"* "$wp_dir/" 2>/dev/null || true
        log_success "Wallpapers installed to $wp_dir."
    fi
}

# ------------------------------------------------------------------------------
# 8. Setup Systemd User Services
# ------------------------------------------------------------------------------
setup_systemd() {
    log_info "Configuring systemd user services..."
    mkdir -p "$HOME/.config/systemd/user/dms.service.d"
    cp -r "$SCRIPT_DIR/.config/systemd/user/"* "$HOME/.config/systemd/user/"

    if command -v systemctl &>/dev/null; then
        systemctl --user daemon-reload 2>/dev/null || true
        systemctl --user enable niri-floating-stash.service 2>/dev/null || true
        
        # If running inside graphical session, restart or start service
        if [ -n "${WAYLAND_DISPLAY:-}" ]; then
            systemctl --user restart niri-floating-stash.service 2>/dev/null || true
            systemctl --user restart dms.service 2>/dev/null || true
        fi
        log_success "Systemd user services enabled."
    fi
}

# ------------------------------------------------------------------------------
# 9. Main Routine
# ------------------------------------------------------------------------------
main() {
    check_dependencies
    backup_existing
    deploy_configs
    deploy_binaries
    deploy_local_share
    build_packet_tracer_fix
    deploy_wallpapers
    setup_systemd

    echo ""
    echo -e "${BOLD}${GREEN}================================================================${NC}"
    echo -e "${BOLD}${GREEN}        Installation completed successfully!                   ${NC}"
    echo -e "${BOLD}${GREEN}================================================================${NC}"
    echo ""
    echo -e "${BOLD}What's configured:${NC}"
    echo "  - Niri with custom cubic-bezier shaders & smooth window-resize"
    echo "  - Dank Material Shell (DMS) on Layer::Top with auto-sync"
    echo "  - Background Daemon: niri-floating-stash (smooth media expand & stash)"
    echo "  - Windows Snipping Tool (Mod+Shift+S)"
    echo "  - Wallpaper Controller: wallpaper-ctl (next, prev, random)"
    echo "  - Cisco Packet Tracer canvas fix shim (embedded note editing)"
    echo "  - Ghostty, Kitty, Alacritty, Swaylock, Cava, Fish, and Zsh configs"
    echo ""
    echo -e "${CYAN}To reload Niri right now:${NC}"
    echo "  niri msg action load-config-file"
    echo ""
}

main "$@"
