#!/usr/bin/env python3
"""
Utility functions for the Windows-Style Snipping Tool.
Handles screenshot capture via dms/grim, clipboard operations via wl-copy,
saving to ~/Pictures/Screenshots, and modern CSS styling.
"""

import os
import subprocess
import datetime
import io
from PIL import Image

PICTURES_SCREENSHOTS_DIR = os.path.expanduser("~/Pictures/Screenshots")

def capture_screen_image() -> Image.Image:
    """Captures the full screen using dms screenshot and returns a PIL Image."""
    try:
        proc = subprocess.run(
            ["dms", "screenshot", "full", "--no-notify", "--stdout"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True
        )
        return Image.open(io.BytesIO(proc.stdout)).convert("RGBA")
    except Exception as e:
        # Fallback to grim if available
        try:
            proc = subprocess.run(
                ["grim", "-"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True
            )
            return Image.open(io.BytesIO(proc.stdout)).convert("RGBA")
        except Exception as e2:
            raise RuntimeError(f"Failed to capture screen: {e}; fallback error: {e2}")

def copy_image_to_clipboard(image: Image.Image) -> bool:
    """Copies a PIL Image directly to the Wayland clipboard via wl-copy."""
    try:
        buf = io.BytesIO()
        image.save(buf, format="PNG")
        png_data = buf.getvalue()

        subprocess.run(
            ["wl-copy", "-t", "image/png"],
            input=png_data,
            check=True
        )
        return True
    except Exception as e:
        print(f"[Snipping Tool] Error copying to clipboard: {e}")
        return False

def save_screenshot_to_disk(image: Image.Image, output_dir: str = PICTURES_SCREENSHOTS_DIR) -> str:
    """
    Saves the screenshot ONLY when explicitly called (e.g. Save button clicked).
    Default destination is ~/Pictures/Screenshots.
    """
    os.makedirs(output_dir, exist_ok=True)
    now = datetime.datetime.now()
    filename = f"Screenshot from {now.strftime('%Y-%m-%d %H-%M-%S')}.png"
    filepath = os.path.join(output_dir, filename)

    # Avoid collision if multiple screenshots taken in the same second
    counter = 1
    while os.path.exists(filepath):
        filename = f"Screenshot from {now.strftime('%Y-%m-%d %H-%M-%S')}_{counter}.png"
        filepath = os.path.join(output_dir, filename)
        counter += 1

    image.save(filepath, format="PNG")
    return filepath

def send_notification(summary: str, body: str = "", icon: str = "camera-photo-symbolic"):
    """Sends a system desktop notification."""
    try:
        subprocess.Popen([
            "notify-send",
            "-a", "Snipping Tool",
            "-i", icon,
            summary,
            body
        ])
    except Exception:
        pass

def get_app_css() -> str:
    """Returns CSS dynamically imported from the system theme (dank-colors.css) with fallbacks."""
    dank_css_path = os.path.expanduser("~/.config/gtk-4.0/dank-colors.css")
    import_stmt = ""
    if os.path.exists(dank_css_path):
        import_stmt = f"@import url('file://{dank_css_path}');\n"

    return import_stmt + """
/* Fallback Material/Adwaita theme tokens */
@define-color accent_bg_color #6750a4;
@define-color accent_fg_color #ffffff;
@define-color window_bg_color #fef7ff;
@define-color window_fg_color #1d1b20;
@define-color card_bg_color #f2ecf4;
@define-color card_fg_color #1d1b20;

/* Overlay Window */
window.overlay-window {
    background-color: transparent;
    background: none;
}

/* Floating Pill Toolbar (Windows 11 / Modern Fluent Style) */
.pill-toolbar {
    background-color: rgba(22, 23, 28, 0.90);
    border: 1px solid rgba(255, 255, 255, 0.16);
    border-radius: 24px;
    padding: 4px 6px;
    box-shadow: 0 10px 32px rgba(0, 0, 0, 0.50), 0 2px 8px rgba(0, 0, 0, 0.25);
    margin-top: 18px;
}

.pill-button {
    background: transparent;
    border: none;
    outline: none;
    border-radius: 18px;
    padding: 7px 14px;
    color: rgba(255, 255, 255, 0.88);
    font-size: 13px;
    font-weight: 500;
    transition: all 120ms cubic-bezier(0, 0, 0.2, 1);
    min-height: 34px;
}

.pill-button:hover {
    background-color: rgba(255, 255, 255, 0.15);
    color: #ffffff;
}

.pill-button:active {
    background-color: rgba(255, 255, 255, 0.25);
    transform: scale(0.97);
}

.pill-button.active {
    background-color: @accent_bg_color;
    color: @accent_fg_color;
    box-shadow: 0 2px 10px alpha(@accent_bg_color, 0.45);
}

.pill-separator {
    background-color: rgba(255, 255, 255, 0.20);
    min-width: 1px;
    margin: 0 4px;
}

.pill-button.close-btn {
    padding: 7px 10px;
    border-radius: 18px;
    min-width: 34px;
    min-height: 34px;
}

.pill-button.close-btn:hover {
    background-color: #e81123;
    color: #ffffff;
}

/* Toast Window (Layer shell surface) */
window.toast-window,
window.toast-window.background,
window.toast-window:backdrop {
    background-color: transparent;
    background: transparent;
    border: none;
    box-shadow: none;
    outline: none;
    padding: 0;
    margin: 0;
}

/* Modern Minimalist Toast Card (Blends directly with system theme) */
.toast-card {
    background-color: @card_bg_color;
    color: @card_fg_color;
    border: 1px solid alpha(@card_fg_color, 0.14);
    border-radius: 20px;
    padding: 14px 18px;
    box-shadow: 0 12px 36px rgba(0, 0, 0, 0.22), 0 2px 8px rgba(0, 0, 0, 0.08);
}

.toast-thumb-interactive {
    border-radius: 12px;
    transition: transform 140ms ease, opacity 140ms ease;
}

.toast-thumb-interactive:hover {
    transform: scale(1.05);
    opacity: 0.90;
}

.toast-thumb-interactive:active {
    transform: scale(0.98);
}

.toast-title {
    font-weight: 700;
    font-size: 13.5px;
    color: @card_fg_color;
}

.toast-subtitle {
    font-size: 12px;
    font-weight: 500;
    color: alpha(@card_fg_color, 0.70);
}

window.toast-window button.toast-btn-primary {
    background-color: @accent_bg_color;
    background-image: none;
    color: @accent_fg_color;
    border: none;
    outline: none;
    border-radius: 18px;
    padding: 7px 18px;
    font-size: 12.5px;
    font-weight: 600;
    box-shadow: 0 2px 8px alpha(@accent_bg_color, 0.40);
    transition: all 120ms ease;
}

window.toast-window button.toast-btn-primary label,
window.toast-window button.toast-btn-primary image {
    color: @accent_fg_color;
}

window.toast-window button.toast-btn-primary:hover {
    background-color: alpha(@accent_bg_color, 0.90);
    box-shadow: 0 4px 12px alpha(@accent_bg_color, 0.50);
}

window.toast-window button.toast-btn-secondary {
    background-color: alpha(@card_fg_color, 0.08);
    background-image: none;
    color: @card_fg_color;
    border: 1px solid alpha(@card_fg_color, 0.16);
    outline: none;
    border-radius: 18px;
    padding: 7px 16px;
    font-size: 12.5px;
    font-weight: 600;
    transition: all 120ms ease;
}

window.toast-window button.toast-btn-secondary label,
window.toast-window button.toast-btn-secondary image {
    color: @card_fg_color;
}

window.toast-window button.toast-btn-secondary:hover {
    background-color: alpha(@card_fg_color, 0.14);
}

.toast-btn-close {
    background: transparent;
    border: none;
    outline: none;
    border-radius: 12px;
    color: alpha(@card_fg_color, 0.55);
    padding: 4px;
    min-width: 24px;
    min-height: 24px;
    transition: all 120ms ease;
}

.toast-btn-close:hover {
    background-color: alpha(@card_fg_color, 0.12);
    color: @card_fg_color;
}

/* Editor Styling */
.editor-window {
    background-color: @window_bg_color;
    color: @window_fg_color;
}

.tool-button {
    background: transparent;
    border: none;
    outline: none;
    border-radius: 8px;
    padding: 7px 12px;
    color: @window_fg_color;
    font-weight: 500;
}

.tool-button:hover {
    background-color: alpha(@window_fg_color, 0.08);
}

.tool-button.active {
    background-color: @accent_bg_color;
    color: @accent_fg_color;
}

/* Primary Action Button (Save, Apply Crop) */
window.editor-window headerbar button.action-btn-primary,
window.editor-window headerbar button.suggested-action,
window.editor-window button.action-btn-primary,
button.action-btn-primary {
    background-color: @accent_bg_color;
    background-image: none;
    color: @accent_fg_color;
    border-radius: 18px;
    font-weight: 600;
    padding: 7px 18px;
    border: none;
    outline: none;
    box-shadow: 0 2px 8px alpha(@accent_bg_color, 0.40);
    transition: all 120ms ease;
}

window.editor-window headerbar button.action-btn-primary label,
window.editor-window headerbar button.action-btn-primary image,
window.editor-window headerbar button.suggested-action label,
window.editor-window headerbar button.suggested-action image,
window.editor-window button.action-btn-primary label,
window.editor-window button.action-btn-primary image,
button.action-btn-primary label,
button.action-btn-primary image {
    color: @accent_fg_color;
}

window.editor-window headerbar button.action-btn-primary:hover,
window.editor-window headerbar button.suggested-action:hover,
window.editor-window button.action-btn-primary:hover,
button.action-btn-primary:hover {
    background-color: alpha(@accent_bg_color, 0.90);
    box-shadow: 0 4px 12px alpha(@accent_bg_color, 0.50);
}

window.editor-window headerbar button.action-btn-primary:active,
window.editor-window headerbar button.suggested-action:active,
window.editor-window button.action-btn-primary:active,
button.action-btn-primary:active {
    background-color: alpha(@accent_bg_color, 0.80);
}

/* Secondary Action Button (Copy, Cancel Crop) */
window.editor-window headerbar button.action-btn-secondary,
window.editor-window button.action-btn-secondary,
button.action-btn-secondary {
    background-color: alpha(@window_fg_color, 0.08);
    background-image: none;
    color: @window_fg_color;
    border-radius: 18px;
    font-weight: 600;
    padding: 7px 16px;
    border: 1px solid alpha(@window_fg_color, 0.16);
    box-shadow: none;
    outline: none;
    transition: all 120ms ease;
}

window.editor-window headerbar button.action-btn-secondary label,
window.editor-window headerbar button.action-btn-secondary image,
window.editor-window button.action-btn-secondary label,
window.editor-window button.action-btn-secondary image,
button.action-btn-secondary label,
button.action-btn-secondary image {
    color: @window_fg_color;
}

window.editor-window headerbar button.action-btn-secondary:hover,
window.editor-window button.action-btn-secondary:hover,
button.action-btn-secondary:hover {
    background-color: alpha(@window_fg_color, 0.14);
}

window.editor-window headerbar button.action-btn-secondary:active,
window.editor-window button.action-btn-secondary:active,
button.action-btn-secondary:active {
    background-color: alpha(@window_fg_color, 0.20);
}

/* Status feedback badge */
.feedback-pill {
    background-color: @accent_bg_color;
    color: @accent_fg_color;
    border-radius: 16px;
    font-weight: 600;
    font-size: 13px;
    padding: 6px 18px;
    box-shadow: 0 4px 14px rgba(0, 0, 0, 0.25);
}

/* Zoom badge styling matching tool-button */
.tool-button.zoom-badge {
    min-width: 44px;
    font-weight: 500;
}

/* Tool Palette Popover */
popover.tool-popover contents {
    background-color: #24252e;
    color: #ffffff;
    border: 1px solid rgba(255, 255, 255, 0.14);
    border-radius: 12px;
    padding: 12px;
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.50);
}

.popover-section-label {
    font-size: 11px;
    font-weight: 700;
    color: rgba(255, 255, 255, 0.85);
    text-transform: uppercase;
    letter-spacing: 0.8px;
    margin-bottom: 2px;
}

/* Color Swatch Button */
button.color-swatch-btn {
    min-width: 28px;
    min-height: 28px;
    padding: 2px;
    margin: 1px;
    border-radius: 16px;
    background-color: transparent;
    border: 2px solid transparent;
    box-shadow: none;
    transition: all 120ms ease;
}

button.color-swatch-btn:hover {
    transform: scale(1.18);
    background-color: rgba(255, 255, 255, 0.15);
}

button.color-swatch-btn.selected {
    border: 2px solid #3880ff;
    background-color: rgba(56, 128, 255, 0.25);
    transform: scale(1.12);
}

/* Size Preset Button */
button.size-preset-btn {
    min-width: 32px;
    min-height: 32px;
    padding: 2px;
    border-radius: 8px;
    background-color: rgba(255, 255, 255, 0.08);
    border: 1px solid rgba(255, 255, 255, 0.12);
    box-shadow: none;
    transition: all 120ms ease;
}

button.size-preset-btn:hover {
    background-color: rgba(255, 255, 255, 0.18);
    border-color: rgba(255, 255, 255, 0.30);
}

button.size-preset-btn.selected {
    background-color: rgba(56, 128, 255, 0.25);
    border: 1.5px solid #3880ff;
}

/* Stroke Preview Container */
.stroke-preview-box {
    margin-top: 6px;
    border-radius: 8px;
}
"""

MODERN_CSS = get_app_css()

