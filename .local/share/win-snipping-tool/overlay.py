#!/usr/bin/env python3
"""
Modern Fullscreen Overlay for Windows-Style Snipping Tool.
Displays the frozen screen with dimming effect, floating pill toolbar,
live rectangle cutout, window hover detection, and instant capture.
"""

import sys
import os
import math
import cairo
from typing import Optional, Callable
from PIL import Image

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
try:
    gi.require_version("Gtk4LayerShell", "1.0")
    from gi.repository import Gtk4LayerShell
    HAS_LAYER_SHELL = True
except Exception:
    HAS_LAYER_SHELL = False

from gi.repository import Gtk, Gdk, GLib, Pango, PangoCairo

from utils import copy_image_to_clipboard, get_app_css
from window_detector import get_niri_windows, find_window_at, WindowInfo

class VectorIcon(Gtk.DrawingArea):
    """Clean, high-DPI vector icon matching Windows 11 Snipping Tool iconography."""
    def __init__(self, icon_type: str, size: int = 16):
        super().__init__()
        self.icon_type = icon_type
        self.icon_size = size
        self.set_content_width(size)
        self.set_content_height(size)
        self.set_halign(Gtk.Align.CENTER)
        self.set_valign(Gtk.Align.CENTER)
        self.set_draw_func(self.on_draw)

    def on_draw(self, area, cr: cairo.Context, width: int, height: int):
        # Mathematically center and proportionally scale in allocated width & height
        base_size = 16.0
        scale = min(width, height) / base_size
        offset_x = (width - base_size * scale) / 2.0
        offset_y = (height - base_size * scale) / 2.0
        cr.translate(offset_x, offset_y)
        cr.scale(scale, scale)

        # Inherit active text color from CSS button state (white or accent fg)
        rgba = area.get_color()
        cr.set_source_rgba(rgba.red, rgba.green, rgba.blue, rgba.alpha)
        cr.set_line_cap(cairo.LINE_CAP_ROUND)
        cr.set_line_join(cairo.LINE_JOIN_ROUND)

        if self.icon_type == "rectangle":
            # Selection marquee rectangle (dashed rounded box)
            cr.set_line_width(1.4)
            cr.set_dash([3.0, 2.0])
            x, y, w, h, r = 1.5, 2.5, 13.0, 11.0, 2.0
            cr.new_sub_path()
            cr.arc(x + w - r, y + r, r, -1.5708, 0)
            cr.arc(x + w - r, y + h - r, r, 0, 1.5708)
            cr.arc(x + r, y + h - r, r, 1.5708, 3.1416)
            cr.arc(x + r, y + r, r, 3.1416, 4.7124)
            cr.close_path()
            cr.stroke()

        elif self.icon_type == "window":
            # Application window with titlebar line & window buttons
            cr.set_line_width(1.4)
            x, y, w, h, r = 1.5, 2.5, 13.0, 11.0, 2.0
            cr.new_sub_path()
            cr.arc(x + w - r, y + r, r, -1.5708, 0)
            cr.arc(x + w - r, y + h - r, r, 0, 1.5708)
            cr.arc(x + r, y + h - r, r, 1.5708, 3.1416)
            cr.arc(x + r, y + r, r, 3.1416, 4.7124)
            cr.close_path()
            cr.stroke()
            # Titlebar separator
            cr.move_to(1.5, 6.0)
            cr.line_to(14.5, 6.0)
            cr.stroke()
            # Titlebar dots
            cr.arc(4.0, 4.25, 0.75, 0, 6.28)
            cr.fill()
            cr.arc(6.5, 4.25, 0.75, 0, 6.28)
            cr.fill()

        elif self.icon_type == "fullscreen":
            # Display monitor screen with stand
            cr.set_line_width(1.4)
            x, y, w, h, r = 1.5, 2.0, 13.0, 9.5, 1.8
            cr.new_sub_path()
            cr.arc(x + w - r, y + r, r, -1.5708, 0)
            cr.arc(x + w - r, y + h - r, r, 0, 1.5708)
            cr.arc(x + r, y + h - r, r, 1.5708, 3.1416)
            cr.arc(x + r, y + r, r, 3.1416, 4.7124)
            cr.close_path()
            cr.stroke()
            # Stand
            cr.move_to(8.0, 11.5)
            cr.line_to(8.0, 14.0)
            cr.stroke()
            cr.move_to(5.0, 14.0)
            cr.line_to(11.0, 14.0)
            cr.stroke()

        elif self.icon_type == "close":
            # Dismiss cross
            cr.set_line_width(1.6)
            cr.move_to(4.0, 4.0)
            cr.line_to(12.0, 12.0)
            cr.stroke()
            cr.move_to(12.0, 4.0)
            cr.line_to(4.0, 12.0)
            cr.stroke()
            cr.stroke()

class SnippingOverlay(Gtk.ApplicationWindow):
    def __init__(self, app: Gtk.Application, full_image: Image.Image, on_complete: Callable[[Image.Image], None]):
        super().__init__(application=app)
        self.set_title("Snipping Tool Overlay")
        self.full_image = full_image
        self.on_complete = on_complete

        self.img_w, self.img_h = full_image.size
        # Prepare Cairo surface from BGRA byte data
        raw_bgra = bytearray(self.full_image.tobytes("raw", "BGRA"))
        stride = cairo.ImageSurface.format_stride_for_width(cairo.FORMAT_ARGB32, self.img_w)
        self.cairo_surface = cairo.ImageSurface.create_for_data(
            raw_bgra, cairo.FORMAT_ARGB32, self.img_w, self.img_h, stride
        )

        # Detect open windows in Niri
        self.windows, self.scale, self.screen_w, self.screen_h = get_niri_windows()

        # State
        self.mode = "rectangle"  # "rectangle", "window", "fullscreen"
        self.is_dragging = False
        self.drag_start_x = 0.0
        self.drag_start_y = 0.0
        self.drag_curr_x = 0.0
        self.drag_curr_y = 0.0
        self.hovered_window: Optional[WindowInfo] = None

        # Apply CSS
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(get_app_css().encode("utf-8"))
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        self.add_css_class("overlay-window")
        if HAS_LAYER_SHELL and Gtk4LayerShell.is_supported():
            Gtk4LayerShell.init_for_window(self)
            Gtk4LayerShell.set_layer(self, Gtk4LayerShell.Layer.OVERLAY)
            Gtk4LayerShell.set_anchor(self, Gtk4LayerShell.Edge.TOP, True)
            Gtk4LayerShell.set_anchor(self, Gtk4LayerShell.Edge.BOTTOM, True)
            Gtk4LayerShell.set_anchor(self, Gtk4LayerShell.Edge.LEFT, True)
            Gtk4LayerShell.set_anchor(self, Gtk4LayerShell.Edge.RIGHT, True)
            Gtk4LayerShell.set_keyboard_mode(self, Gtk4LayerShell.KeyboardMode.EXCLUSIVE)
            Gtk4LayerShell.set_exclusive_zone(self, -1)
            Gtk4LayerShell.set_namespace(self, "snipping-overlay")
        else:
            self.fullscreen()

        # Main overlay layout
        self.overlay = Gtk.Overlay()
        self.set_child(self.overlay)

        # Drawing Area for screen, dimming, and selection
        self.drawing_area = Gtk.DrawingArea()
        self.drawing_area.set_draw_func(self.on_draw)
        self.overlay.set_child(self.drawing_area)

        # Mouse and keyboard controllers
        self.setup_controllers()

        # Floating Pill Toolbar
        self.toolbar_box = self.create_pill_toolbar()
        self.overlay.add_overlay(self.toolbar_box)

    def setup_controllers(self):
        # Drag controller for rectangular selection
        drag = Gtk.GestureDrag()
        drag.connect("drag-begin", self.on_drag_begin)
        drag.connect("drag-update", self.on_drag_update)
        drag.connect("drag-end", self.on_drag_end)
        self.drawing_area.add_controller(drag)

        # Click controller for window and fullscreen selection
        click = Gtk.GestureClick()
        click.connect("pressed", self.on_click_pressed)
        self.drawing_area.add_controller(click)

        # Motion controller for window hovering
        motion = Gtk.EventControllerMotion()
        motion.connect("motion", self.on_mouse_motion)
        self.drawing_area.add_controller(motion)

        # Keyboard controller for Esc key
        key = Gtk.EventControllerKey()
        key.connect("key-pressed", self.on_key_pressed)
        self.add_controller(key)

        # Initial cursor
        self.update_cursor()

    def update_cursor(self):
        cursor_name = "crosshair" if self.mode == "rectangle" else "pointer"
        try:
            cursor = Gdk.Cursor.new_from_name(cursor_name, None)
            self.drawing_area.set_cursor(cursor)
        except Exception:
            pass

    def _create_pill_btn(self, icon_type: str, label_text: str, tooltip: str, on_click) -> Tuple[Gtk.Button, VectorIcon]:
        btn = Gtk.Button()
        btn.add_css_class("pill-button")
        btn.set_tooltip_text(tooltip)
        btn.set_valign(Gtk.Align.CENTER)

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        box.set_valign(Gtk.Align.CENTER)
        box.set_halign(Gtk.Align.CENTER)

        icon = VectorIcon(icon_type, size=16)
        icon.set_valign(Gtk.Align.CENTER)
        icon.set_halign(Gtk.Align.CENTER)
        box.append(icon)

        if label_text:
            lbl = Gtk.Label(label=label_text)
            lbl.set_valign(Gtk.Align.CENTER)
            lbl.set_halign(Gtk.Align.CENTER)
            lbl.set_yalign(0.5)
            box.append(lbl)

        btn.set_child(box)
        btn.connect("clicked", on_click)
        return btn, icon

    def create_pill_toolbar(self) -> Gtk.Box:
        pill = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        pill.add_css_class("pill-toolbar")
        pill.set_halign(Gtk.Align.CENTER)
        pill.set_valign(Gtk.Align.START)

        # Rectangle Mode Button
        self.btn_rect, self.icon_rect = self._create_pill_btn(
            "rectangle", "Rectangle", "Rectangle (Drag area to snip)",
            lambda _: self.set_mode("rectangle")
        )
        self.btn_rect.add_css_class("active")
        pill.append(self.btn_rect)

        # Window Mode Button
        self.btn_win, self.icon_win = self._create_pill_btn(
            "window", "Window", "Window (Click window to snip)",
            lambda _: self.set_mode("window")
        )
        pill.append(self.btn_win)

        # Fullscreen Mode Button
        self.btn_full, self.icon_full = self._create_pill_btn(
            "fullscreen", "Full Screen", "Full Screen (Capture display)",
            lambda _: self.capture_fullscreen()
        )
        pill.append(self.btn_full)

        # Separator
        sep = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        sep.add_css_class("pill-separator")
        sep.set_valign(Gtk.Align.CENTER)
        sep.set_size_request(1, 18)
        pill.append(sep)

        # Close / Cancel Button
        btn_close = Gtk.Button()
        btn_close.add_css_class("pill-button")
        btn_close.add_css_class("close-btn")
        btn_close.set_tooltip_text("Cancel (Esc)")
        btn_close.set_valign(Gtk.Align.CENTER)

        close_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        close_box.set_valign(Gtk.Align.CENTER)
        close_box.set_halign(Gtk.Align.CENTER)

        self.icon_close = VectorIcon("close", size=16)
        self.icon_close.set_valign(Gtk.Align.CENTER)
        self.icon_close.set_halign(Gtk.Align.CENTER)
        close_box.append(self.icon_close)

        btn_close.set_child(close_box)
        btn_close.connect("clicked", lambda _: self.cancel())
        pill.append(btn_close)

        return pill

    def set_mode(self, mode: str):
        self.mode = mode
        self.btn_rect.remove_css_class("active")
        self.btn_win.remove_css_class("active")
        self.btn_full.remove_css_class("active")

        if mode == "rectangle":
            self.btn_rect.add_css_class("active")
        elif mode == "window":
            self.btn_win.add_css_class("active")
        elif mode == "fullscreen":
            self.btn_full.add_css_class("active")

        # Redraw vector icons so get_color() captures the active accent color
        self.icon_rect.queue_draw()
        self.icon_win.queue_draw()
        self.icon_full.queue_draw()
        self.icon_close.queue_draw()

        self.hovered_window = None
        self.is_dragging = False
        self.update_cursor()
        self.drawing_area.queue_draw()

    def on_drag_begin(self, gesture, start_x, start_y):
        if self.mode != "rectangle":
            return
        self.is_dragging = True
        self.drag_start_x = start_x
        self.drag_start_y = start_y
        self.drag_curr_x = start_x
        self.drag_curr_y = start_y
        self.drawing_area.queue_draw()

    def on_drag_update(self, gesture, offset_x, offset_y):
        if self.mode != "rectangle" or not self.is_dragging:
            return
        self.drag_curr_x = self.drag_start_x + offset_x
        self.drag_curr_y = self.drag_start_y + offset_y
        self.drawing_area.queue_draw()

    def on_drag_end(self, gesture, offset_x, offset_y):
        if self.mode != "rectangle" or not self.is_dragging:
            return
        self.is_dragging = False

        rx = min(self.drag_start_x, self.drag_curr_x)
        ry = min(self.drag_start_y, self.drag_curr_y)
        rw = abs(self.drag_curr_x - self.drag_start_x)
        rh = abs(self.drag_curr_y - self.drag_start_y)

        # Require a minimum drag distance to prevent misclicks
        if rw >= 8 and rh >= 8:
            px = int(round(rx * self.scale))
            py = int(round(ry * self.scale))
            pw = int(round(rw * self.scale))
            ph = int(round(rh * self.scale))

            px = max(0, min(px, self.img_w - 1))
            py = max(0, min(py, self.img_h - 1))
            pw = min(pw, self.img_w - px)
            ph = min(ph, self.img_h - py)

            if pw > 0 and ph > 0:
                cropped = self.full_image.crop((px, py, px + pw, py + ph))
                self.finish_capture(cropped)
                return

        self.drawing_area.queue_draw()

    def on_click_pressed(self, gesture, n_press, x, y):
        if self.mode == "window":
            win = self.hovered_window if (self.hovered_window and self.hovered_window.contains(x, y)) else find_window_at(self.windows, x, y)
            if win:
                px, py, pw, ph = win.rect_physical
                px = max(0, min(px, self.img_w - 1))
                py = max(0, min(py, self.img_h - 1))
                pw = min(pw, self.img_w - px)
                ph = min(ph, self.img_h - py)
                if pw > 0 and ph > 0:
                    cropped = self.full_image.crop((px, py, px + pw, py + ph))
                    self.finish_capture(cropped)
        elif self.mode == "fullscreen":
            self.capture_fullscreen()

    def on_mouse_motion(self, controller, x, y):
        if self.mode == "window":
            target_win = find_window_at(self.windows, x, y)
            if target_win != self.hovered_window:
                self.hovered_window = target_win
                self.drawing_area.queue_draw()

    def on_key_pressed(self, controller, keyval, keycode, state):
        if keyval == Gdk.KEY_Escape:
            self.cancel()
            return True
        return False

    def capture_fullscreen(self):
        self.finish_capture(self.full_image)

    def finish_capture(self, image: Image.Image):
        self.hide()
        self.on_complete(image)
        self.close()

    def cancel(self):
        self.hide()
        self.close()

    def on_draw(self, area, cr: cairo.Context, width: int, height: int):
        # 1. Background full screenshot
        cr.save()
        cr.scale(width / self.img_w, height / self.img_h)
        cr.set_source_surface(self.cairo_surface, 0, 0)
        cr.paint()
        cr.restore()

        # 2. Dimming overlay veil
        cr.set_source_rgba(0, 0, 0, 0.45)
        cr.paint()

        # 3. Mode-specific cutout and highlights
        if self.mode == "rectangle" and self.is_dragging:
            rx = min(self.drag_start_x, self.drag_curr_x)
            ry = min(self.drag_start_y, self.drag_curr_y)
            rw = abs(self.drag_curr_x - self.drag_start_x)
            rh = abs(self.drag_curr_y - self.drag_start_y)

            if rw > 0 and rh > 0:
                # Bright cutout
                cr.save()
                cr.rectangle(rx, ry, rw, rh)
                cr.clip()
                cr.scale(width / self.img_w, height / self.img_h)
                cr.set_source_surface(self.cairo_surface, 0, 0)
                cr.paint()
                cr.restore()

                # Crisp white selection border
                cr.set_source_rgba(1.0, 1.0, 1.0, 0.95)
                cr.set_line_width(2.0)
                cr.rectangle(rx, ry, rw, rh)
                cr.stroke()

                # Dimension indicator pill
                pw = int(round(rw * self.scale))
                ph = int(round(rh * self.scale))
                self.draw_dimension_pill(cr, rx, ry, rw, rh, pw, ph)

        elif self.mode == "window" and self.hovered_window:
            wx, wy, ww, wh = self.hovered_window.rect_logical
            # Bright window cutout
            cr.save()
            cr.rectangle(wx, wy, ww, wh)
            cr.clip()
            cr.scale(width / self.img_w, height / self.img_h)
            cr.set_source_surface(self.cairo_surface, 0, 0)
            cr.paint()
            cr.restore()

            # Fluent Blue highlight border
            cr.set_source_rgba(0.20, 0.52, 0.90, 0.95)
            cr.set_line_width(3.0)
            cr.rectangle(wx, wy, ww, wh)
            cr.stroke()

            # Window Title Pill
            self.draw_title_pill(cr, wx, wy, self.hovered_window.title)

    def draw_dimension_pill(self, cr: cairo.Context, rx: float, ry: float, rw: float, rh: float, pw: int, ph: int):
        text = f"{pw} × {ph} px"
        layout = self.create_pango_layout(text)
        layout.set_font_description(Pango.FontDescription("Cantarell, Sans Bold 11"))
        ink_rect, log_rect = layout.get_pixel_extents()

        pill_w = log_rect.width + 20
        pill_h = log_rect.height + 12

        # Position below selection, or above if close to bottom
        pill_x = rx + (rw - pill_w) / 2
        pill_y = ry + rh + 10
        if pill_y + pill_h > self.screen_h - 10:
            pill_y = ry - pill_h - 10

        cr.save()
        cr.set_source_rgba(0.12, 0.13, 0.16, 0.88)
        self.draw_rounded_rect(cr, pill_x, pill_y, pill_w, pill_h, 6)
        cr.fill_preserve()
        cr.set_source_rgba(1.0, 1.0, 1.0, 0.2)
        cr.set_line_width(1.0)
        cr.stroke()

        cr.set_source_rgba(1.0, 1.0, 1.0, 1.0)
        cr.move_to(pill_x + 10, pill_y + 6)
        PangoCairo.show_layout(cr, layout)
        cr.restore()

    def draw_title_pill(self, cr: cairo.Context, wx: float, wy: float, title: str):
        if len(title) > 40:
            title = title[:37] + "..."
        text = f"🪟 {title}"
        layout = self.create_pango_layout(text)
        layout.set_font_description(Pango.FontDescription("Cantarell, Sans Bold 11"))
        _, log_rect = layout.get_pixel_extents()

        pill_w = log_rect.width + 22
        pill_h = log_rect.height + 12
        pill_x = wx + 12
        pill_y = wy + 12

        cr.save()
        cr.set_source_rgba(0.12, 0.13, 0.16, 0.92)
        self.draw_rounded_rect(cr, pill_x, pill_y, pill_w, pill_h, 6)
        cr.fill_preserve()
        cr.set_source_rgba(0.20, 0.52, 0.90, 0.8)
        cr.set_line_width(1.5)
        cr.stroke()

        cr.set_source_rgba(1.0, 1.0, 1.0, 1.0)
        cr.move_to(pill_x + 11, pill_y + 6)
        PangoCairo.show_layout(cr, layout)
        cr.restore()

    def draw_rounded_rect(self, cr: cairo.Context, x: float, y: float, w: float, h: float, r: float):
        cr.new_sub_path()
        cr.arc(x + w - r, y + r, r, -math.pi / 2, 0)
        cr.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
        cr.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
        cr.arc(x + r, y + r, r, math.pi, 3 * math.pi / 2)
        cr.close_path()
