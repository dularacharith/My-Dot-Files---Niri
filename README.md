# 🌌 My Dotfiles — Niri & Dank Material Shell (DMS)

> A modern, elegant, and ultra-smooth scrollable-tiling Wayland desktop environment powered by **[Niri](https://github.com/YaLTeR/niri)** and **[Dank Material Shell (DMS)](https://github.com/AvengeMedia/dms)**.

Designed for peak productivity, aesthetic elegance, and seamless multitasking. Features custom GLSL shaders, proactive floating window management, zero-delay media expansion, an integrated Windows-style Snipping Tool, dynamic wallpaper management, and dedicated shims for professional applications like Cisco Packet Tracer.

---

## 📸 Highlights & Features

- **Niri Scrollable-Tiling Compositor**:
  - **Calibrated Butter-Smooth Interaction Animations**:
    - **macOS-Grade Physics**: Calm, organic curves and balanced spring dynamics ($k=200\text{--}250$, damping ratio $0.85\text{--}0.88$).
    - `window-resize`: Calibrated 700ms `ease-out-cubic` progressive texture shader for smooth tile reflow, float-to-tile, and tile-to-float transitions.
    - `window-open`: 650ms `ease-out-cubic` with in-place scale (90% to 100%), alpha fade, and boundary-safe clipping.
    - `window-close`: 500ms `ease-out-cubic` with soft in-place scale (100% to 94%) and gentle dissolve.
    - `workspace-switch`, `overview-open-close`, `window-movement`: Luxurious, fluid momentum transitions with zero stutter.
  - **Stationary Top Bar**: Locked to `Layer::Top` so it remains perfectly fixed during workspace transitions.
  - **Smart Media Rules**: Floating-by-default with predefined dimensions for VLC, Haruna, MPV, Celluloid, Showtime, Decibels, and Totem.

- **Smart Zenity Dialog Wrapper**:
  - Intercepts `--no-wrap` calls from apps like Google Chrome / Chromium (such as the profile lock dialog) and enforces `--width=650`.
  - Enforces `max-width 850` and auto-floating rules in Niri, preventing modal dialogs and notification prompts from exploding beyond screen boundaries.

- **Dank Material Shell (DMS)**:
  - Material 3 / Material You automatic color theming via Matugen.
  - Tailored bar layout with launcher, active workspace switcher, task title, weather, clock, media player controls, system tray, battery, and control center.
  - Consistent dynamic theming synced across Ghostty, Kitty, Alacritty, GTK 3/4, Cava, and swaylock.

- **Intelligent Background Daemon (`niri-auto-float`)**:
  - Automatically manages floating and tiling dynamics based on window focus.
  - Geometry preservation for file managers (Nautilus, Dolphin, Thunar), opening cleanly at 900x600 without secondary resizing glitches.
  - Proactively hides the DMS bar via IPC on frame 0 when media players or windows expand to fullscreen, eliminating top-bar overlap delay.
  - Automatically exempts dialogs, toasts, utilities (USBImager, WoeUSB, Balena Etcher), and media viewers.

- **Windows-Style Snipping Tool (`Mod+Shift+S`)**:
  - Fast sub-30ms screen capture using GTK4 and `gtk4-layer-shell`.
  - Interactive selection overlay, instant clipboard copy, floating toast notification, and a full-featured annotation/markup editor.

- **Wallpaper Manager (`wallpaper-ctl`)**:
  - CLI controller for landscape wallpapers (`next`, `prev`, `random`, `set`, `list`).
  - Bundled with a curated collection of 14 high-resolution landscape wallpapers.

- **Cisco Packet Tracer Wayland Shim**:
  - `libpt_canvas_fix.so`: Custom LD_PRELOAD C shim that embeds in-canvas notes and cluster editing directly into Packet Tracer's graphics viewport under Wayland compositors.

- **Universal Cursor & HiDPI Consistency**:
  - macOS cursor theme synchronized seamlessly across Wayland, XWayland (via `xrdb` and `xwayland-satellite`), GTK 2/3/4, Qt 5/6, and Flatpak apps with consistent 24px scaling.

- **System Typography & Multilingual Precision**:
  - **SF Pro Display / Text**: Apple's San Francisco Pro configured as system default sans-serif font across desktop UI, GTK, Qt, and browser interfaces.
  - **Sinhala Sangam MN**: Apple's native Sinhala font configured with universal fontconfig fallbacks across all browsers (Chrome, Firefox, WebKit) and desktop apps, providing elegant typographic rendering for Sinhala script.
  - **JetBrainsMono Nerd Font**: Modern developer monospace font powering Kitty and Ghostty terminals.

---

## ⌨️ Keybindings Cheat Sheet

| Keybinding | Action |
| :--- | :--- |
| `Mod + Return` | Open Terminal (`ghostty` / `kitty`) |
| `Mod + Space` | Toggle Application Launcher (`dms spotlight` / `hamr`) |
| `Mod + W` | Open Web Browser (`firefox` / `zen`) |
| `Mod + Shift + S` | **Windows-Style Snipping Tool** (Region Capture & Editor) |
| `Mod + Q` | Close Focused Window |
| `Mod + F` | Maximize / Unmaximize Column |
| `Mod + Shift + F` | Fullscreen Window (Full-bleed, hides bar) |
| `Mod + Shift + T` | Toggle Window Floating State |
| `Mod + Shift + V` | Switch Focus Between Floating and Tiling |
| `Mod + R` / `Mod + Shift + R` | Cycle Column Preset Widths / Window Heights |
| `Mod + Left / Right` | Focus Column Left / Right |
| `Mod + Up / Down` | Focus Window Up / Down |
| `Mod + Shift + Left / Right` | Move Column Left / Right |
| `Mod + Shift + Up / Down` | Move Window Up / Down in Column |
| `Mod + WheelScrollDown / Up` | Navigate Workspaces Down / Up |
| `Mod + Alt + L` | Lock Screen (DMS Material You Lock) |
| `Ctrl + Alt + Delete` | Quit Niri Session |

*(Note: `Mod` is mapped to the `Super` / Windows key)*

---

## 📦 Prerequisites & Dependencies

### Fedora Linux (Recommended)

1. Enable the DMS & DankLinux Copr repositories:
   ```bash
   sudo dnf copr enable avengemedia/dms
   sudo dnf copr enable avengemedia/danklinux
   ```

2. Install the necessary packages:
   ```bash
   sudo dnf install -y \
     niri \
     dms-cli \
     quickshell \
     ghostty \
     kitty \
     alacritty \
     swaylock \
     fastfetch \
     cava \
     fish \
     zsh \
     python3 \
     python3-pillow \
     python3-gobject \
     gtk4 \
     gtk4-layer-shell \
     gcc \
     make \
     wl-clipboard \
     grim \
     slurp
   ```

### Arch Linux

1. Install packages via `pacman`:
   ```bash
   sudo pacman -S --needed \
     niri \
     ghostty \
     kitty \
     alacritty \
     swaylock \
     fastfetch \
     cava \
     fish \
     zsh \
     python \
     python-pillow \
     python-gobject \
     gtk4 \
     gcc \
     make \
     wl-clipboard \
     grim \
     slurp
   ```

2. Install DMS and Quickshell from AUR (using `yay` or `paru`):
   ```bash
   yay -S --needed dms-bin quickshell-git gtk4-layer-shell
   ```

---

## 🚀 Installation

### Automated Install (Recommended)

Clone this repository and run the provided `install.sh` script:

```bash
git clone https://github.com/dularacharith/My-Dot-Files---Niri.git
cd My-Dot-Files---Niri
chmod +x install.sh
./install.sh
```

The installer will:
1. Back up any existing conflicting configuration files, root dotfiles, and local binaries to `~/.config/dotfiles_backup_<timestamp>/`.
2. Deploy `.config/` files (`niri`, `DankMaterialShell`, `environment.d`, `kitty`, `ghostty`, `alacritty`, etc.).
3. Deploy `.local/bin/` utility scripts (`niri-auto-float`, `zenity` wrapper, `wallpaper-ctl`, `packettracer`, etc.).
4. Install the Windows Snipping Tool into `~/.local/share/win-snipping-tool` and register its desktop entry.
5. Compile and place `libpt_canvas_fix.so` into `~/.local/lib/`.
6. Deploy the landscape wallpaper collection to `~/Pictures/Wallpapers/Landscape/`.
7. Reload and enable the `niri-auto-float` systemd user service.

---

### Manual Installation (Step-by-Step)

If you prefer to install manually:

1. **Deploy Configuration Files**:
   ```bash
   cp -r .config/* ~/.config/
   ```

2. **Deploy Scripts & Set Permissions**:
   ```bash
   mkdir -p ~/.local/bin ~/.local/lib ~/.local/share
   cp -r .local/bin/* ~/.local/bin/
   chmod +x ~/.local/bin/*
   ```

3. **Install Snipping Tool**:
   ```bash
   cp -r .local/share/win-snipping-tool ~/.local/share/
   cp -r .local/share/applications/* ~/.local/share/applications/
   chmod +x ~/.local/share/win-snipping-tool/snip_main.py
   ln -sf ~/.local/share/win-snipping-tool/snip_main.py ~/.local/bin/win-snipping-tool
   update-desktop-database ~/.local/share/applications/
   ```

4. **Compile Packet Tracer Canvas Fix**:
   ```bash
   mkdir -p ~/.local/src/pt_canvas_fix ~/.local/lib
   cp -r .local/src/pt_canvas_fix/* ~/.local/src/pt_canvas_fix/
   make -C ~/.local/src/pt_canvas_fix TARGET="$HOME/.local/lib/libpt_canvas_fix.so"
   ```

5. **Deploy Wallpapers**:
   ```bash
   mkdir -p ~/Pictures/Wallpapers/Landscape
   cp -r wallpapers/* ~/Pictures/Wallpapers/Landscape/
   ```

6. **Enable Systemd Services**:
   ```bash
   systemctl --user daemon-reload
   systemctl --user enable --now niri-auto-float.service
   systemctl --user restart dms.service
   ```

7. **Reload Niri**:
   ```bash
   niri msg action load-config-file
   ```

---

## 🗑️ Uninstallation & Removal

### Automated Removal & Backup Rollback (Recommended)

To completely remove the dotfiles or restore your desktop to its exact pre-installation state, run `uninstall.sh`:

```bash
chmod +x uninstall.sh
./uninstall.sh
```

The uninstaller will:
1. Prompt for confirmation (or run non-interactively with `-y`).
2. Stop and disable the `niri-auto-float` systemd user service.
3. Remove deployed utility scripts from `~/.local/bin/` (`niri-auto-float`, `zenity`, `wallpaper-ctl`, `win-snipping-tool`, etc.).
4. Remove application data and shims (`~/.local/share/win-snipping-tool`, `~/.local/lib/libpt_canvas_fix.so`).
5. Automatically detect your latest configuration backup (`~/.config/dotfiles_backup_*`) and offer to restore all original configurations and root dotfiles.
6. Refresh system caches (desktop database and font cache) and reload Niri.

#### Uninstaller Options

| Flag | Description |
| :--- | :--- |
| `-y, --yes` | Run non-interactively, assuming Yes to all prompts |
| `--restore-backup DIR` | Restore from a specific backup directory instead of auto-detecting the latest |
| `--no-restore` | Remove repository dotfiles and scripts without restoring any previous backup |
| `-h, --help` | Show command-line help |

### Manual Removal (Step-by-Step)

If you prefer to remove components manually:

1. **Stop & Disable Daemons**:
   ```bash
   systemctl --user stop niri-auto-float.service
   systemctl --user disable niri-auto-float.service
   rm -f ~/.config/systemd/user/niri-auto-float.service
   rm -f ~/.config/systemd/user/dms.service.d/override.conf
   systemctl --user daemon-reload
   ```

2. **Remove Deployed Binaries**:
   ```bash
   rm -f ~/.local/bin/niri-auto-float \
         ~/.local/bin/zenity \
         ~/.local/bin/wallpaper-ctl \
         ~/.local/bin/win-snipping-tool \
         ~/.local/bin/brightness-step \
         ~/.local/bin/fn-feedback \
         ~/.local/bin/niri-display-manager \
         ~/.local/bin/packettracer \
         ~/.local/bin/wl-mirror
   ```

3. **Remove Application Data & Fixes**:
   ```bash
   rm -rf ~/.local/share/win-snipping-tool
   rm -f ~/.local/share/applications/win-snipping-tool.desktop
   rm -f ~/.local/lib/libpt_canvas_fix.so
   rm -rf ~/.local/src/pt_canvas_fix
   ```

4. **Restore Configuration Files**:
   Locate your latest backup directory in `~/.config/dotfiles_backup_<timestamp>/` and copy your original files back:
   ```bash
   cp -r ~/.config/dotfiles_backup_<timestamp>/* ~/.config/
   if [ -d ~/.config/dotfiles_backup_<timestamp>/root_dotfiles ]; then
       cp -r ~/.config/dotfiles_backup_<timestamp>/root_dotfiles/* ~/
   fi
   ```

---

## 📂 Repository Structure

```
My-Dot-Files---Niri/
├── .config/
│   ├── niri/                       # Niri window manager config & custom shaders
│   │   ├── config.kdl              # Main Niri configuration (calibrated animations & window rules)
│   │   ├── window_rules.kdl        # Custom window, dialog & floating rules
│   │   ├── touchpad.kdl            # Touchpad gesture & scroll tuning
│   │   └── dms/                    # DMS modular Niri includes (binds, colors, layout)
│   ├── DankMaterialShell/          # DMS shell & widget preferences
│   │   ├── settings.json           # Bar layout, widget configuration, and margins
│   │   └── firefox.css             # Material You themed Firefox userChrome
│   ├── environment.d/              # Wayland & DMS environment variables
│   │   ├── 90-dms.conf
│   │   └── dms.conf                # DMS_DANKBAR_LAYER=top
│   ├── systemd/user/               # User services and overrides
│   │   ├── niri-auto-float.service # Dynamic window floating manager daemon
│   │   └── dms.service.d/override.conf
│   ├── alacritty/                  # Alacritty terminal configuration
│   ├── ghostty/                    # Ghostty terminal configuration
│   ├── kitty/                      # Kitty terminal configuration
│   ├── fastfetch/                  # Fastfetch system info layout
│   ├── swaylock/                   # Lockscreen aesthetics
│   ├── cava/                       # Audio visualizer config & shaders
│   ├── vlc/                        # VLC configuration (xlib/XWayland mode, pulse audio, clean view)
│   ├── kdeglobals, qt5ct, qt6ct    # Qt5/Qt6/KDE cursor theme & appearance synchronization
│   ├── gtk-3.0/ & gtk-4.0/         # GTK themes & Material You color bindings
│   ├── fish/ & zsh/                # Shell configs (.zshrc, .p10k.zsh, config.fish)
│   └── danksearch/ & dgop/         # Search provider & widget configurations
├── .local/
│   ├── bin/
│   │   ├── niri-auto-float         # Python daemon for floating window management & zero-delay bar sync
│   │   ├── zenity                  # Smart Zenity wrapper (dialog width auto-fitting & overflow fix)
│   │   ├── wallpaper-ctl           # Wallpaper management script
│   │   ├── win-snipping-tool       # Windows-style Snipping Tool launcher
│   │   ├── brightness-step         # Smooth brightness controller
│   │   ├── fn-feedback             # Function key visual feedback
│   │   ├── niri-display-manager    # Display configuration and mirroring manager
│   │   ├── packettracer            # Cisco Packet Tracer Wayland launcher wrapper
│   │   └── wl-mirror               # Wayland mirror utility
│   ├── share/
│   │   ├── applications/           # Desktop entries (Chrome, Snipping Tool, Cisco Packet Tracer)
│   │   ├── icons/                  # macOS cursor theme collection & Packet Tracer app icons
│   │   └── win-snipping-tool/      # Python GTK4 Snipping Tool with editor & toast UI
│   └── src/
│       └── pt_canvas_fix/          # C source & Makefile for Packet Tracer canvas fix
├── .icons/                         # Default cursor inheritance (macOS)
├── .Xresources & .xprofile         # X11 / XWayland xrdb cursor scaling & resource synchronization
├── .gtkrc-2.0                      # GTK2 cursor theme & size fallback
├── wallpapers/                     # 14 curated high-resolution landscape wallpapers
├── install.sh                      # Automated, idempotent installer script (with auto-backup)
├── uninstall.sh                    # Automated uninstaller & configuration rollback script
├── .gitignore
└── README.md
```

---

## 🛠️ Customizations & Troubleshooting

### Top Bar Visibility & Layer Settings
The top bar is set to `Layer::Top` via `~/.config/environment.d/dms.conf` (`DMS_DANKBAR_LAYER=top`). This ensures the bar stays static during workspace navigation. The `niri-auto-float` daemon monitors active workspaces and hides the bar instantaneously when any window enters full-screen or expanded media mode, restoring it seamlessly upon exiting.

### Checking Daemon Status
To check if the background auto-float manager daemon is active:
```bash
systemctl --user status niri-auto-float.service
```
To view real-time logs:
```bash
journalctl --user -u niri-auto-float -f
```

### Changing Wallpapers
Use the bundled controller:
```bash
wallpaper-ctl next      # Switch to next wallpaper
wallpaper-ctl prev      # Switch to previous wallpaper
wallpaper-ctl random    # Pick random wallpaper
wallpaper-ctl list      # List available wallpapers
```

---

## 👤 Author

- **Dulara Charith** — [GitHub Profile](https://github.com/dularacharith)
- Repository: [My-Dot-Files---Niri](https://github.com/dularacharith/My-Dot-Files---Niri)
