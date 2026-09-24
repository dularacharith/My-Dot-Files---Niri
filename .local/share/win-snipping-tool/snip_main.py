#!/usr/bin/env python3
"""
Main Entry Point for Windows-Style Snipping Tool.
Handles hotkey invocation (Mod+Shift+S), screen capture, overlay, toast, and editor.
"""

import os
import sys

# Ensure GTK4 Layer Shell is preloaded for True Wayland Overlay support
layer_shell_lib = "/usr/lib64/libgtk4-layer-shell.so.1.3.0"
if os.path.exists(layer_shell_lib) and "libgtk4-layer-shell" not in os.environ.get("LD_PRELOAD", ""):
    current_ld = os.environ.get("LD_PRELOAD", "")
    os.environ["LD_PRELOAD"] = f"{layer_shell_lib}:{current_ld}".strip(":")
    os.execv(sys.executable, [sys.executable] + sys.argv)

import argparse
import subprocess
from PIL import Image

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
gi.require_version("Gio", "2.0")
from gi.repository import Gtk, Gio, GLib

from utils import capture_screen_image, copy_image_to_clipboard
from overlay import SnippingOverlay
from editor import SnippingEditor
from toast import SnippingToast

TEMP_IMAGE_PATH = "/tmp/snipping_current.png"

def run_overlay():
    # 1. Pre-capture the screen immediately (sub-30ms) before opening UI
    try:
        full_image = capture_screen_image()
    except Exception as e:
        print(f"Failed to capture screen: {e}", file=sys.stderr)
        sys.exit(1)

    app = Gtk.Application(flags=Gio.ApplicationFlags.NON_UNIQUE)

    def on_activate(app):
        def on_complete(captured_img: Image.Image):
            # 1. Copy to clipboard by default
            copy_image_to_clipboard(captured_img)

            # 2. Save temporary file for toast / editor preview
            captured_img.save(TEMP_IMAGE_PATH, format="PNG")

            # 3. Launch the floating toast card in background
            script_path = os.path.abspath(__file__)
            subprocess.Popen([sys.executable, script_path, "--toast", TEMP_IMAGE_PATH])

        overlay = SnippingOverlay(app, full_image, on_complete)
        overlay.present()

    app.connect("activate", on_activate)
    app.run(None)

def run_editor(image_path: str):
    if not os.path.exists(image_path):
        print(f"Image not found: {image_path}", file=sys.stderr)
        sys.exit(1)

    image = Image.open(image_path)
    app = Gtk.Application(application_id="com.snipping.editor", flags=Gio.ApplicationFlags.NON_UNIQUE)

    def on_activate(app):
        editor = SnippingEditor(app, image, image_path)
        editor.present()

    app.connect("activate", on_activate)
    app.run(None)

def run_toast(image_path: str):
    if not os.path.exists(image_path):
        print(f"Image not found: {image_path}", file=sys.stderr)
        sys.exit(1)

    app = Gtk.Application(flags=Gio.ApplicationFlags.NON_UNIQUE)

    def on_activate(app):
        toast = SnippingToast(app, image_path)
        toast.present()

    app.connect("activate", on_activate)
    app.run(None)

def main():
    parser = argparse.ArgumentParser(description="Windows-Style Snipping Tool for Linux")
    parser.add_argument("--editor", nargs="?", const=TEMP_IMAGE_PATH, help="Open image in editor")
    parser.add_argument("--toast", nargs="?", const=TEMP_IMAGE_PATH, help="Display toast notification for image")
    args = parser.parse_args()

    if args.editor:
        run_editor(args.editor)
    elif args.toast:
        run_toast(args.toast)
    else:
        run_overlay()

if __name__ == "__main__":
    main()
