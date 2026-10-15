#!/usr/bin/env bash
# ==============================================================================
# My-Dot-Files---Niri Uninstaller Script
# Cleanly removes deployed scripts, disables systemd user services, and
# restores prior configuration backups created by install.sh.
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

print_banner() {
    echo -e "${BOLD}${RED}"
    cat << 'EOF'
  _   _ _       _   _   _       _           _        _ _           
 | \ | (_)_ __ (_) | | | |_ __ (_)_ __  ___| |_ __ _| | | ___ _ __ 
 |  \| | | '__|| | | | | | '_ \| | '_ \/ __| __/ _` | | |/ _ \ '__|
 | |\  | | |   | | | |_| | | | | | | | \__ \ || (_| | | |  __/ |   
 |_| \_|_|_|   |_|  \___/|_| |_|_|_| |_|___/\__\__,_|_|_|\___|_|   
EOF
    echo -e "${NC}"
    echo -e "${BOLD}Dotfiles Uninstaller & Configuration Rollback${NC}\n"
}

usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -y, --yes               Run non-interactively, assuming Yes to all prompts"
    echo "      --restore-backup DIR Restore from a specific backup directory"
    echo "      --no-restore        Remove dotfiles without restoring any previous backup"
    echo "  -h, --help              Show this help message and exit"
    echo ""
}

# ------------------------------------------------------------------------------
# Parse Arguments
# ------------------------------------------------------------------------------
AUTO_CONFIRM=0
CUSTOM_BACKUP=""
NO_RESTORE=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        -y|--yes)
            AUTO_CONFIRM=1
            shift
            ;;
        --restore-backup)
            if [[ $# -gt 1 ]]; then
                CUSTOM_BACKUP="$2"
                shift 2
            else
                log_error "--restore-backup requires a directory argument."
                exit 1
            fi
            ;;
        --no-restore)
            NO_RESTORE=1
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

# ------------------------------------------------------------------------------
# Locate Backup Directory
# ------------------------------------------------------------------------------
find_backup() {
    if [[ -n "$CUSTOM_BACKUP" ]]; then
        if [[ -d "$CUSTOM_BACKUP" ]]; then
            echo "$CUSTOM_BACKUP"
            return
        else
            log_error "Specified backup directory does not exist: $CUSTOM_BACKUP"
            exit 1
        fi
    fi

    # Check pointer file
    local pointer="$HOME/.config/.dotfiles_last_backup"
    if [[ -f "$pointer" ]]; then
        local pdir
        pdir="$(cat "$pointer" 2>/dev/null || true)"
        if [[ -d "$pdir" ]]; then
            echo "$pdir"
            return
        fi
    fi

    # Fallback: scan ~/.config/dotfiles_backup_* (newest first)
    local latest
    latest="$(ls -td "$HOME"/.config/dotfiles_backup_* 2>/dev/null | head -n 1 || true)"
    if [[ -n "$latest" && -d "$latest" ]]; then
        echo "$latest"
        return
    fi

    echo ""
}

# ------------------------------------------------------------------------------
# Confirm Removal
# ------------------------------------------------------------------------------
confirm_removal() {
    if [[ $AUTO_CONFIRM -eq 1 ]]; then
        return 0
    fi

    echo -e "${YELLOW}This script will:${NC}"
    echo "  1. Stop and disable the niri-auto-float systemd user service."
    echo "  2. Remove deployed utility binaries from ~/.local/bin/ (niri-auto-float, zenity, wallpaper-ctl, etc.)."
    echo "  3. Remove Windows Snipping Tool and Cisco Packet Tracer fix shims."
    echo "  4. Restore prior desktop configurations from backup (or purge if chosen)."
    echo ""

    read -rp "Are you sure you want to proceed with uninstallation? [y/N]: " confirm
    if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
        log_info "Uninstallation cancelled."
        exit 0
    fi
}

# ------------------------------------------------------------------------------
# 1. Stop & Disable Systemd Services
# ------------------------------------------------------------------------------
stop_services() {
    log_info "Stopping and disabling systemd user services..."

    if command -v systemctl &>/dev/null; then
        systemctl --user stop niri-auto-float.service 2>/dev/null || true
        systemctl --user disable niri-auto-float.service 2>/dev/null || true
    fi

    rm -f "$HOME/.config/systemd/user/niri-auto-float.service"
    rm -f "$HOME/.config/systemd/user/dms.service.d/override.conf"
    rmdir "$HOME/.config/systemd/user/dms.service.d" 2>/dev/null || true

    if command -v systemctl &>/dev/null; then
        systemctl --user daemon-reload 2>/dev/null || true
    fi

    log_success "Systemd user services removed."
}

# ------------------------------------------------------------------------------
# 2. Remove Deployed Binaries (~/.local/bin)
# ------------------------------------------------------------------------------
remove_binaries() {
    log_info "Removing deployed utility scripts from ~/.local/bin..."

    local binaries=(
        "niri-auto-float"
        "zenity"
        "wallpaper-ctl"
        "win-snipping-tool"
        "brightness-step"
        "fn-feedback"
        "niri-display-manager"
        "packettracer"
        "wl-mirror"
        "google-chrome"
        "google-chrome-stable"
    )

    for b in "${binaries[@]}"; do
        if [[ -e "$HOME/.local/bin/$b" || -L "$HOME/.local/bin/$b" ]]; then
            rm -f "$HOME/.local/bin/$b"
            log_info "  Removed ~/.local/bin/$b"
        fi
    done

    log_success "Binaries removed from ~/.local/bin."
}

# ------------------------------------------------------------------------------
# 3. Remove Shared Applications & Fixes (~/.local/share, ~/.local/lib)
# ------------------------------------------------------------------------------
remove_shared_data() {
    log_info "Removing application data and build shims..."

    # Snipping tool
    rm -rf "$HOME/.local/share/win-snipping-tool"
    rm -f "$HOME/.local/share/applications/win-snipping-tool.desktop"

    # Packet tracer fix
    rm -f "$HOME/.local/lib/libpt_canvas_fix.so"
    rm -rf "$HOME/.local/src/pt_canvas_fix"

    # Clean up empty parent dirs if applicable
    rmdir "$HOME/.local/lib" 2>/dev/null || true
    rmdir "$HOME/.local/src" 2>/dev/null || true

    log_success "Application data and shims removed."
}

# ------------------------------------------------------------------------------
# 4. Restore Backups or Clean Configs
# ------------------------------------------------------------------------------
restore_or_clean_configs() {
    local backup_dir
    backup_dir="$(find_backup)"

    if [[ $NO_RESTORE -eq 0 && -n "$backup_dir" ]]; then
        log_info "Found existing backup at: $backup_dir"
        
        local do_restore=1
        if [[ $AUTO_CONFIRM -eq 0 ]]; then
            read -rp "Restore configurations from this backup? [Y/n]: " restore_ans
            if [[ "$restore_ans" =~ ^[Nn]$ ]]; then
                do_restore=0
            fi
        fi

        if [[ $do_restore -eq 1 ]]; then
            log_info "Restoring configurations from $backup_dir..."

            # Restore ~/.config directories
            for item in "$backup_dir"/*; do
                local bname
                bname="$(basename "$item")"
                if [[ "$bname" != "root_dotfiles" && "$bname" != "local_bin" && "$bname" != "MANIFEST.txt" ]]; then
                    rm -rf "$HOME/.config/$bname"
                    cp -r "$item" "$HOME/.config/"
                    log_info "  Restored ~/.config/$bname"
                fi
            done

            # Restore root dotfiles if present
            if [[ -d "$backup_dir/root_dotfiles" ]]; then
                for rf in "$backup_dir/root_dotfiles"/*; do
                    if [[ -f "$rf" ]]; then
                        local rfname
                        rfname="$(basename "$rf")"
                        cp "$rf" "$HOME/$rfname"
                        log_info "  Restored ~/$rfname"
                    fi
                done
            fi

            # Restore local binaries if present
            if [[ -d "$backup_dir/local_bin" ]]; then
                for lb in "$backup_dir/local_bin"/*; do
                    if [[ -e "$lb" || -L "$lb" ]]; then
                        local lbname
                        lbname="$(basename "$lb")"
                        cp -P "$lb" "$HOME/.local/bin/$lbname"
                        log_info "  Restored ~/.local/bin/$lbname"
                    fi
                done
            fi

            rm -f "$HOME/.config/.dotfiles_last_backup"
            log_success "Configurations successfully restored from backup."
            return
        fi
    fi

    # If not restoring backup, ask whether to remove deployed config directories
    log_warn "No backup restored. Cleaning up repository-deployed configurations..."
    local configs_to_remove=(
        "niri"
        "DankMaterialShell"
        "danksearch"
        "dgop"
    )

    for cfg in "${configs_to_remove[@]}"; do
        if [[ -d "$HOME/.config/$cfg" ]]; then
            rm -rf "$HOME/.config/$cfg"
            log_info "  Removed ~/.config/$cfg"
        fi
    done

    # Remove root dotfiles deployed by repo
    for rf in .Xresources .Xdefaults .xprofile .blerc; do
        if [[ -f "$HOME/$rf" ]]; then
            rm -f "$HOME/$rf"
            log_info "  Removed ~/$rf"
        fi
    done

    log_success "Dotfiles configurations cleaned."
}

# ------------------------------------------------------------------------------
# 5. Refresh Caches
# ------------------------------------------------------------------------------
refresh_system() {
    log_info "Refreshing system caches..."

    if command -v update-desktop-database &>/dev/null; then
        update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true
    fi

    if command -v fc-cache &>/dev/null; then
        fc-cache -fv "$HOME/.local/share/fonts" 2>/dev/null || true
    fi

    # If Niri is running, attempt reload
    if command -v niri &>/dev/null && [ -n "${WAYLAND_DISPLAY:-}" ]; then
        niri msg action load-config-file 2>/dev/null || true
    fi

    log_success "System caches refreshed."
}

# ------------------------------------------------------------------------------
# Main Routine
# ------------------------------------------------------------------------------
main() {
    print_banner
    confirm_removal
    stop_services
    remove_binaries
    remove_shared_data
    restore_or_clean_configs
    refresh_system

    echo ""
    echo -e "${BOLD}${GREEN}================================================================${NC}"
    echo -e "${BOLD}${GREEN}        Uninstallation completed successfully!                 ${NC}"
    echo -e "${BOLD}${GREEN}================================================================${NC}"
    echo ""
    echo "All dotfiles components and background daemons have been removed."
    if [ -n "${WAYLAND_DISPLAY:-}" ]; then
        echo -e "${CYAN}Please log out and log back into your session to complete the reset.${NC}"
    fi
    echo ""
}

main "$@"
