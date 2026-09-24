# 🌌 My Dotfiles — Niri & Dank Material Shell (DMS)

> A modern, elegant, and ultra-smooth scrollable-tiling Wayland desktop environment powered by **[Niri](https://github.com/YaLTeR/niri)** and **[Dank Material Shell (DMS)](https://github.com/AvengeMedia/dms)**.

Designed for peak productivity, aesthetic elegance, and seamless multitasking. Features custom GLSL shaders, proactive floating window management, zero-delay media expansion, an integrated Windows-style Snipping Tool, dynamic wallpaper management, and dedicated shims for professional applications like Cisco Packet Tracer.

---

## 📸 Highlights & Features

- **Niri Scrollable-Tiling Compositor**:
  - **Custom GLSL Animation Shaders**:
    - `window-open`: Vibrant zoom pop with lively overshoot.
    - `window-close`: Sleek sink-and-shrink with a subtle downward drop.
    - `window-resize`: Custom progressive shader featuring zero-ghosting scaling on maximize and smooth dissolution on minimize.
  - **Stationary Top Bar**: Locked to `Layer::Top` so it remains perfectly fixed during workspace transitions.
  - **Smart Media Rules**: Floating-by-default with predefined dimensions for VLC, Haruna, MPV, Celluloid, Showtime, Decibels, and Totem.

- **Dank Material Shell (DMS)**:
  - Material 3 / Material You automatic color theming via Matugen.
  - Tailored bar layout with launcher, active workspace switcher, task title, weather, clock, media player controls, system tray, battery, and control center.
  - Consistent dynamic theming synced across Ghostty, Kitty, Alacritty, GTK 3/4, Cava, and swaylock.

- **Intelligent Background Daemon (`niri-floating-stash`)**:
  - Automatically hides (stashes) floating windows when a window is maximized or fullscreened, keeping your view distraction-free.
  - Proactively triggers DMS bar hiding via IPC on frame 0 when media players or windows expand to fullscreen, eliminating top-bar overlap delay.
  - Seamlessly restores stashed windows to their exact positions when unmaximizing or switching workspaces.

- **Windows-Style Snipping Tool (`Mod+Shift+S`)**:
  - Fast sub-30ms screen capture using GTK4 and `gtk4-layer-shell`.
  - Interactive selection overlay, instant clipboard copy, floating toast notification, and a full-featured annotation/markup editor.

- **Wallpaper Manager (`wallpaper-ctl`)**:
  - CLI controller for landscape wallpapers (`next`, `prev`, `random`, `set`, `list`).
  - Bundled with a curated collection of 14 high-resolution landscape wallpapers.

- **Cisco Packet Tracer Wayland Shim**:
  - `libpt_canvas_fix.so`: Custom LD_PRELOAD C shim that embeds in-canvas notes and cluster editing directly into Packet Tracer's graphics viewport under Wayland compositors.

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
1. Back up any existing conflicting configuration files to `~/.config/dotfiles_backup_<timestamp>/`.
2. Deploy `.config/` files (`niri`, `DankMaterialShell`, `environment.d`, `kitty`, `ghostty`, `alacritty`, etc.).
3. Deploy `.local/bin/` utility scripts (`niri-floating-stash`, `wallpaper-ctl`, `packettracer`).
4. Install the Windows Snipping Tool into `~/.local/share/win-snipping-tool` and register its desktop entry.
5. Compile and place `libpt_canvas_fix.so` into `~/.local/lib/`.
6. Deploy the landscape wallpaper collection to `~/Pictures/Wallpapers/Landscape/`.
7. Reload and enable the `niri-floating-stash` systemd user service.

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
   systemctl --user enable --now niri-floating-stash.service
   systemctl --user restart dms.service
   ```

7. **Reload Niri**:
   ```bash
   niri msg action load-config-file
   ```

---

## 📂 Repository Structure

```
My-Dot-Files---Niri/
├── .config/
│   ├── niri/                       # Niri window manager config & custom shaders
│   │   ├── config.kdl              # Main Niri configuration
│   │   ├── window_rules.kdl        # Custom window and floating rules
│   │   └── dms/                    # DMS modular Niri includes (binds, colors, layout)
│   ├── DankMaterialShell/          # DMS shell & widget preferences
│   │   ├── settings.json           # Bar layout, widget configuration, and margins
│   │   └── firefox.css             # Material You themed Firefox userChrome
│   ├── environment.d/              # Wayland & DMS environment variables
│   │   ├── 90-dms.conf
│   │   └── dms.conf                # DMS_DANKBAR_LAYER=top
│   ├── systemd/user/               # User services and overrides
│   │   ├── niri-floating-stash.service
│   │   └── dms.service.d/override.conf
│   ├── alacritty/                  # Alacritty terminal configuration
│   ├── ghostty/                    # Ghostty terminal configuration
│   ├── kitty/                      # Kitty terminal configuration
│   ├── fastfetch/                  # Fastfetch system info layout
│   ├── swaylock/                   # Lockscreen aesthetics
│   ├── cava/                       # Audio visualizer config & shaders
│   ├── gtk-3.0/ & gtk-4.0/         # GTK themes & Material You color bindings
│   ├── fish/ & zsh/                # Shell configs (.zshrc, .p10k.zsh, config.fish)
│   └── danksearch/ & dgop/         # Search provider & widget configurations
├── .local/
│   ├── bin/
│   │   ├── niri-floating-stash     # Python daemon for floating auto-stash & zero-delay bar sync
│   │   ├── wallpaper-ctl           # Wallpaper management script
│   │   └── packettracer            # Cisco Packet Tracer Wayland launcher wrapper
│   ├── share/
│   │   ├── applications/           # Desktop entries (.desktop)
│   │   └── win-snipping-tool/      # Python GTK4 Snipping Tool with editor & toast UI
│   └── src/
│       └── pt_canvas_fix/          # C source & Makefile for Packet Tracer canvas fix
├── wallpapers/                     # 14 curated high-resolution landscape wallpapers
├── install.sh                      # Automated, idempotent installer script
├── .gitignore
└── README.md
```

---

## 🛠️ Customizations & Troubleshooting

### Top Bar Visibility & Layer Settings
The top bar is set to `Layer::Top` via `~/.config/environment.d/dms.conf` (`DMS_DANKBAR_LAYER=top`). This ensures the bar stays static during workspace navigation. The `niri-floating-stash` daemon monitors active workspaces and hides the bar instantaneously when any window enters full-screen or expanded media mode, restoring it seamlessly upon exiting.

### Checking Daemon Status
To check if the background stash daemon is active:
```bash
systemctl --user status niri-floating-stash.service
```
To view real-time logs:
```bash
journalctl --user -u niri-floating-stash -f
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
