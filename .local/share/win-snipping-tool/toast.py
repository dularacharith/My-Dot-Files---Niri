#!/usr/bin/env python3
"""
Floating Toast Notification for Windows-Style Snipping Tool.
Displays a modern, minimalist preview card with 'Edit & Crop' and 'Save' buttons,
blending seamlessly with the system theme (light/dark Material You / Adwaita).
"""

import os
import sys
import subprocess
from PIL import Image, ImageDraw, ImageOps

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
gi.require_version("GdkPixbuf", "2.0")
gi.require_version("Gio", "2.0")

try:
    gi.require_version("Gtk4LayerShell", "1.0")
    from gi.repository import Gtk4LayerShell
    HAS_LAYER_SHELL = True
except Exception:
    HAS_LAYER_SHELL = False

from gi.repository import Gtk, Gdk, GdkPixbuf, Gio, GLib

from utils import (
    save_screenshot_to_disk,
    send_notification,
    get_app_css
)

class SnippingToast(Gtk.ApplicationWindow):
    def __init__(self, app: Gtk.Application, image_path: str):
        super().__init__(application=app)
        self.set_title("Snipping Tool Notification")
        self.set_default_size(470, 160)
        self.set_resizable(False)
        self.add_css_class("toast-window")

        if HAS_LAYER_SHELL and Gtk4LayerShell.is_supported():
            Gtk4LayerShell.init_for_window(self)
            Gtk4LayerShell.set_layer(self, Gtk4LayerShell.Layer.OVERLAY)
            Gtk4LayerShell.set_anchor(self, Gtk4LayerShell.Edge.BOTTOM, True)
            Gtk4LayerShell.set_anchor(self, Gtk4LayerShell.Edge.RIGHT, True)
            Gtk4LayerShell.set_margin(self, Gtk4LayerShell.Edge.BOTTOM, 24)
            Gtk4LayerShell.set_margin(self, Gtk4LayerShell.Edge.RIGHT, 24)
            Gtk4LayerShell.set_keyboard_mode(self, Gtk4LayerShell.KeyboardMode.NONE)
            Gtk4LayerShell.set_exclusive_zone(self, -1)
            Gtk4LayerShell.set_namespace(self, "snipping-toast")

        self.image_path = image_path

        # Apply Theme CSS
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(get_app_css().encode("utf-8"))
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_USER
        )

        self.setup_ui()

        # Auto-dismiss after 8 seconds
        GLib.timeout_add_seconds(8, self.on_timeout)

    def generate_thumbnail(self, src_path: str, dest_path: str, max_w: int = 112, max_h: int = 72, radius: int = 10):
        """Generates a crisp, proportional antialiased rounded preview thumbnail."""
        try:
            img = Image.open(src_path).convert("RGBA")
            iw, ih = img.size

            # Upscale tiny snippets so they are visible
            if iw < 48 or ih < 48:
                scale_up = max(48 / max(1, iw), 48 / max(1, ih))
                img = img.resize((max(1, int(iw * scale_up)), max(1, int(ih * scale_up))), Image.Resampling.NEAREST)
                iw, ih = img.size

            aspect = iw / max(1, ih)

            # Determine dimensions matching screenshot aspect ratio within max bounds
            if aspect >= 1.0:
                tw = min(max_w, max(56, int(max_h * aspect)))
                th = int(tw / aspect)
                if th > max_h:
                    th = max_h
                    tw = int(th * aspect)
            else:
                th = min(max_h, max(56, int(max_w / aspect)))
                tw = int(th * aspect)
                if tw > max_w:
                    tw = max_w
                    th = int(tw / aspect)

            tw = max(48, min(tw, max_w))
            th = max(48, min(th, max_h))

            resized = img.resize((tw, th), Image.Resampling.LANCZOS)

            # Supersampled mask for smooth rounded corners
            scale = 4
            mask = Image.new("L", (tw * scale, th * scale), 0)
            draw = ImageDraw.Draw(mask)
            draw.rounded_rectangle(
                [0, 0, tw * scale - 1, th * scale - 1],
                radius=radius * scale,
                fill=255
            )
            mask = mask.resize((tw, th), Image.Resampling.LANCZOS)

            output = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
            output.paste(resized, (0, 0), mask)

            # Smooth border matching the shape
            border = Image.new("RGBA", (tw * scale, th * scale), (0, 0, 0, 0))
            b_draw = ImageDraw.Draw(border)
            b_draw.rounded_rectangle(
                [0, 0, tw * scale - 1, th * scale - 1],
                radius=radius * scale,
                outline=(128, 128, 128, 110),
                width=scale
            )
            border = border.resize((tw, th), Image.Resampling.LANCZOS)
            output.alpha_composite(border)

            output.save(dest_path, "PNG")
        except Exception as e:
            print(f"[Toast] Error generating thumbnail: {e}")

    def setup_ui(self):
        # Card container with generous margins so drop-shadow and rounded corners never clip
        card = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
        card.add_css_class("toast-card")
        card.set_margin_start(16)
        card.set_margin_end(16)
        card.set_margin_top(16)
        card.set_margin_bottom(16)
        card.set_valign(Gtk.Align.CENTER)
        card.set_halign(Gtk.Align.END)
        self.set_child(card)

        # Interactive Thumbnail Preview
        thumb_file = "/tmp/snipping_toast_thumb.png"
        self.generate_thumbnail(self.image_path, thumb_file, max_w=112, max_h=72, radius=10)

        thumb_box = Gtk.Box()
        thumb_box.add_css_class("toast-thumb-interactive")
        thumb_box.set_valign(Gtk.Align.CENTER)
        thumb_box.set_cursor_from_name("pointer")
        thumb_box.set_tooltip_text("Click to open editor")

        img_widget = Gtk.Picture.new_for_filename(thumb_file)
        img_widget.set_can_shrink(False)
        img_widget.set_halign(Gtk.Align.CENTER)
        img_widget.set_valign(Gtk.Align.CENTER)
        thumb_box.append(img_widget)

        click = Gtk.GestureClick()
        click.connect("pressed", lambda g, n, x, y: self.open_editor())
        thumb_box.add_controller(click)
        card.append(thumb_box)

        # Content Column
        content_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        content_vbox.set_valign(Gtk.Align.CENTER)
        content_vbox.set_hexpand(True)
        card.append(content_vbox)

        # Title Row
        title_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

        icon = Gtk.Image.new_from_icon_name("camera-photo-symbolic")
        icon.set_pixel_size(15)
        title_box.append(icon)

        lbl_title = Gtk.Label(label="Screenshot copied")
        lbl_title.add_css_class("toast-title")
        lbl_title.set_halign(Gtk.Align.START)
        title_box.append(lbl_title)

        title_box.append(Gtk.Box(hexpand=True))

        btn_close = Gtk.Button()
        btn_close.add_css_class("toast-btn-close")
        btn_close.set_cursor_from_name("pointer")
        close_icon = Gtk.Image.new_from_icon_name("window-close-symbolic")
        close_icon.set_pixel_size(12)
        btn_close.set_child(close_icon)
        btn_close.set_tooltip_text("Dismiss")
        btn_close.connect("clicked", lambda _: self.close())
        title_box.append(btn_close)

        content_vbox.append(title_box)

        lbl_desc = Gtk.Label(label="Ready to paste, or edit below.")
        lbl_desc.add_css_class("toast-subtitle")
        lbl_desc.set_halign(Gtk.Align.START)
        content_vbox.append(lbl_desc)

        # Actions Row
        actions_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        actions_box.set_margin_top(6)

        btn_edit = Gtk.Button()
        btn_edit.add_css_class("toast-btn-secondary")
        btn_edit.set_cursor_from_name("pointer")
        edit_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        edit_icon = Gtk.Image.new_from_icon_name("document-edit-symbolic")
        edit_icon.set_pixel_size(14)
        edit_box.append(edit_icon)
        edit_box.append(Gtk.Label(label="Edit & Crop"))
        btn_edit.set_child(edit_box)
        btn_edit.set_tooltip_text("Markup and crop screenshot")
        btn_edit.connect("clicked", lambda _: self.open_editor())
        actions_box.append(btn_edit)

        btn_save = Gtk.Button()
        btn_save.add_css_class("toast-btn-primary")
        btn_save.set_cursor_from_name("pointer")
        save_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        save_icon = Gtk.Image.new_from_icon_name("document-save-symbolic")
        save_icon.set_pixel_size(14)
        save_box.append(save_icon)
        save_box.append(Gtk.Label(label="Save"))
        btn_save.set_child(save_box)
        btn_save.set_tooltip_text("Save to ~/Pictures/Screenshots")
        btn_save.connect("clicked", lambda _: self.save_now())
        actions_box.append(btn_save)

        content_vbox.append(actions_box)

    def open_editor(self):
        self.hide()
        bin_path = os.path.expanduser("~/.local/share/win-snipping-tool/snip_main.py")
        subprocess.Popen([sys.executable, bin_path, "--editor", self.image_path])
        self.close()

    def save_now(self):
        try:
            img = Image.open(self.image_path)
            dest = save_screenshot_to_disk(img)
            send_notification("Screenshot Saved", f"Saved to {os.path.basename(dest)}")
        except Exception as e:
            print(f"[Toast] Error saving: {e}")
        self.close()

    def on_timeout(self) -> bool:
        self.close()
        return False


if __name__ == "__main__":
    img_p = sys.argv[1] if len(sys.argv) > 1 else "/tmp/snipping_current.png"
    app = Gtk.Application(flags=Gio.ApplicationFlags.NON_UNIQUE)

    def on_act(a):
        t = SnippingToast(a, img_p)
        t.present()

    app.connect("activate", on_act)
    app.run(None)
