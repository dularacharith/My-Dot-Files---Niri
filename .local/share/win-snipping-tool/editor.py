#!/usr/bin/env python3
"""
Snipping Editor for Windows-Style Snipping Tool.
Provides interactive cropping, pen markup, highlighter, eraser, undo/redo, copy, and save.
Supports responsive fit-to-window scaling, zoom in/out via buttons, mouse scroll wheel,
and touchpad pinch-to-zoom gestures.
"""

import os
import sys
import math
from typing import Optional, List, Tuple
from PIL import Image

import cairo
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gtk, Gdk, GLib

from utils import (
    copy_image_to_clipboard,
    save_screenshot_to_disk,
    send_notification,
    get_app_css
)

class Stroke:
    def __init__(self, tool: str, color_rgba: Tuple[float, float, float, float], width: float):
        self.tool = tool  # "pen" or "highlighter"
        self.color_rgba = color_rgba
        self.width = width
        self.points: List[Tuple[float, float]] = []

class VectorCropIcon(Gtk.DrawingArea):
    """Vector Cairo-rendered modern interlocking-blade crop icon matching Windows 11 / Fluent style."""
    def __init__(self, size: int = 16):
        super().__init__()
        self.size = size
        self.set_content_width(size)
        self.set_content_height(size)
        self.set_valign(Gtk.Align.CENTER)
        self.set_halign(Gtk.Align.CENTER)
        self.set_draw_func(self._draw)

    def _draw(self, area, cr: cairo.Context, width: int, height: int):
        col = self.get_color()
        cr.set_source_rgba(col.red, col.green, col.blue, col.alpha)
        cr.set_line_cap(cairo.LINE_CAP_ROUND)
        cr.set_line_join(cairo.LINE_JOIN_ROUND)

        s = min(width, height) / 24.0
        cr.translate((width - 24.0 * s) / 2.0, (height - 24.0 * s) / 2.0)
        cr.scale(s, s)
        cr.set_line_width(2.2)

        # Path 1: Top-Left blade extending down and right
        cr.move_to(6.0, 2.0)
        cr.line_to(6.0, 18.0)
        cr.line_to(22.0, 18.0)
        cr.stroke()

        # Path 2: Bottom-Right blade extending up and left
        cr.move_to(18.0, 22.0)
        cr.line_to(18.0, 6.0)
        cr.line_to(2.0, 6.0)
        cr.stroke()


class VectorMinusIcon(Gtk.DrawingArea):
    """Clean minimalist vector minus icon for zoom control matching tool icons."""
    def __init__(self, size: int = 16):
        super().__init__()
        self.set_content_width(size)
        self.set_content_height(size)
        self.set_valign(Gtk.Align.CENTER)
        self.set_halign(Gtk.Align.CENTER)
        self.set_draw_func(self._draw)

    def _draw(self, area, cr: cairo.Context, width: int, height: int):
        col = self.get_color()
        cr.set_source_rgba(col.red, col.green, col.blue, col.alpha)
        cr.set_line_cap(cairo.LINE_CAP_ROUND)
        cr.set_line_width(2.0)
        cr.move_to(2.0, height / 2.0)
        cr.line_to(width - 2.0, height / 2.0)
        cr.stroke()


class VectorPlusIcon(Gtk.DrawingArea):
    """Clean minimalist vector plus icon for zoom control matching tool icons."""
    def __init__(self, size: int = 16):
        super().__init__()
        self.set_content_width(size)
        self.set_content_height(size)
        self.set_valign(Gtk.Align.CENTER)
        self.set_halign(Gtk.Align.CENTER)
        self.set_draw_func(self._draw)

    def _draw(self, area, cr: cairo.Context, width: int, height: int):
        col = self.get_color()
        cr.set_source_rgba(col.red, col.green, col.blue, col.alpha)
        cr.set_line_cap(cairo.LINE_CAP_ROUND)
        cr.set_line_width(2.0)
        cr.move_to(2.0, height / 2.0)
        cr.line_to(width - 2.0, height / 2.0)
        cr.stroke()
        cr.move_to(width / 2.0, 2.0)
        cr.line_to(width / 2.0, height - 2.0)
        cr.stroke()


class VectorCloseIcon(Gtk.DrawingArea):
    """Modern bold vector cross icon with rounded caps and balanced geometry."""
    def __init__(self, size: int = 13, stroke_width: float = 2.4):
        super().__init__()
        self.size = size
        self.stroke_width = stroke_width
        self.set_content_width(size)
        self.set_content_height(size)
        self.set_valign(Gtk.Align.CENTER)
        self.set_halign(Gtk.Align.CENTER)
        self.set_draw_func(self._draw)

    def _draw(self, area, cr: cairo.Context, w: int, h: int):
        col = self.get_color()
        cr.set_source_rgba(col.red, col.green, col.blue, col.alpha)
        cr.set_line_cap(cairo.LINE_CAP_ROUND)
        cr.set_line_join(cairo.LINE_JOIN_ROUND)
        cr.set_line_width(self.stroke_width)
        pad = 2.4
        cr.move_to(pad, pad)
        cr.line_to(w - pad, h - pad)
        cr.stroke()
        cr.move_to(w - pad, pad)
        cr.line_to(pad, h - pad)
        cr.stroke()


class VectorCheckIcon(Gtk.DrawingArea):
    """Modern bold vector checkmark icon with rounded caps."""
    def __init__(self, size: int = 13, stroke_width: float = 2.4):
        super().__init__()
        self.size = size
        self.stroke_width = stroke_width
        self.set_content_width(size)
        self.set_content_height(size)
        self.set_valign(Gtk.Align.CENTER)
        self.set_halign(Gtk.Align.CENTER)
        self.set_draw_func(self._draw)

    def _draw(self, area, cr: cairo.Context, w: int, h: int):
        col = self.get_color()
        cr.set_source_rgba(col.red, col.green, col.blue, col.alpha)
        cr.set_line_cap(cairo.LINE_CAP_ROUND)
        cr.set_line_join(cairo.LINE_JOIN_ROUND)
        cr.set_line_width(self.stroke_width)
        cr.move_to(w * 0.16, h * 0.52)
        cr.line_to(w * 0.42, h * 0.78)
        cr.line_to(w * 0.86, h * 0.22)
        cr.stroke()


class VectorChevronDown(Gtk.DrawingArea):
    """Minimal chevron down for dropdown toolbar buttons."""
    def __init__(self, size: int = 8):
        super().__init__()
        self.set_content_width(size)
        self.set_content_height(size)
        self.set_valign(Gtk.Align.CENTER)
        self.set_halign(Gtk.Align.CENTER)
        self.set_draw_func(self._draw)

    def _draw(self, area, cr: cairo.Context, w: int, h: int):
        col = self.get_color()
        cr.set_source_rgba(col.red, col.green, col.blue, col.alpha * 0.75)
        cr.set_line_cap(cairo.LINE_CAP_ROUND)
        cr.set_line_join(cairo.LINE_JOIN_ROUND)
        cr.set_line_width(1.5)
        cr.move_to(1.5, h * 0.35)
        cr.line_to(w / 2.0, h * 0.70)
        cr.line_to(w - 1.5, h * 0.35)
        cr.stroke()


class ColorBar(Gtk.DrawingArea):
    """Horizontal colored accent indicator bar under toolbar buttons."""
    def __init__(self, initial_rgba: Tuple[float, float, float, float], width: int = 34, height: int = 3):
        super().__init__()
        self.rgba = initial_rgba
        self.set_content_width(width)
        self.set_content_height(height)
        self.set_valign(Gtk.Align.END)
        self.set_halign(Gtk.Align.FILL)
        self.set_draw_func(self._draw)

    def set_color(self, rgba: Tuple[float, float, float, float]):
        self.rgba = rgba
        self.queue_draw()

    def _draw(self, area, cr: cairo.Context, w: int, h: int):
        r, g, b, a = self.rgba
        # Ensure indicator bar is vividly visible even for translucent colors (e.g. highlighter)
        cr.set_source_rgba(r, g, b, max(0.90, a))
        radius = h / 2.0
        cr.new_sub_path()
        cr.arc(w - radius, radius, radius, -math.pi / 2, math.pi / 2)
        cr.arc(radius, h - radius, radius, math.pi / 2, 3 * math.pi / 2)
        cr.close_path()
        cr.fill()


class ColorDot(Gtk.DrawingArea):
    """Circular color swatch for popover palettes."""
    def __init__(self, rgba: Tuple[float, float, float, float], diameter: int = 20, is_white: bool = False):
        super().__init__()
        self.rgba = rgba
        self.diameter = diameter
        self.is_white = is_white
        self.set_content_width(diameter)
        self.set_content_height(diameter)
        self.set_valign(Gtk.Align.CENTER)
        self.set_halign(Gtk.Align.CENTER)
        self.set_draw_func(self._draw)

    def _draw(self, area, cr: cairo.Context, w: int, h: int):
        cx, cy = w / 2.0, h / 2.0
        radius = (min(w, h) - 2) / 2.0
        r, g, b, a = self.rgba
        cr.arc(cx, cy, radius, 0, 2 * math.pi)
        cr.set_source_rgba(r, g, b, max(0.85, a))
        cr.fill_preserve()
        if self.is_white or (r > 0.85 and g > 0.85 and b > 0.85):
            cr.set_source_rgba(0.5, 0.5, 0.5, 0.6)
            cr.set_line_width(1.0)
            cr.stroke()
        else:
            cr.set_source_rgba(0.0, 0.0, 0.0, 0.25)
            cr.set_line_width(0.8)
            cr.stroke()


class SizeDot(Gtk.DrawingArea):
    """Circular dot representing a stroke thickness option."""
    def __init__(self, dot_size: float = 6.0):
        super().__init__()
        self.dot_size = dot_size
        self.set_content_width(24)
        self.set_content_height(24)
        self.set_valign(Gtk.Align.CENTER)
        self.set_halign(Gtk.Align.CENTER)
        self.set_draw_func(self._draw)

    def _draw(self, area, cr: cairo.Context, w: int, h: int):
        cx, cy = w / 2.0, h / 2.0
        radius = min(w - 4, h - 4, self.dot_size) / 2.0
        cr.arc(cx, cy, radius, 0, 2 * math.pi)
        col = self.get_color()
        cr.set_source_rgba(col.red, col.green, col.blue, col.alpha * 0.90)
        cr.fill()


class StrokePreview(Gtk.DrawingArea):
    """Live preview of stroke with current color and width."""
    def __init__(self, is_highlighter: bool = False):
        super().__init__()
        self.is_highlighter = is_highlighter
        self.rgba = (0.92, 0.18, 0.18, 1.0)
        self.stroke_width = 3.5
        self.set_content_width(200)
        self.set_content_height(42)
        self.add_css_class("stroke-preview-box")
        self.set_draw_func(self._draw)

    def update_stroke(self, rgba: Tuple[float, float, float, float], width: float):
        self.rgba = rgba
        self.stroke_width = width
        self.queue_draw()

    def _draw(self, area, cr: cairo.Context, w: int, h: int):
        cr.set_source_rgba(0.12, 0.13, 0.16, 0.95)
        radius = 8.0
        cr.new_sub_path()
        cr.arc(w - radius, radius, radius, -math.pi / 2, 0)
        cr.arc(w - radius, h - radius, radius, 0, math.pi / 2)
        cr.arc(radius, h - radius, radius, math.pi / 2, math.pi)
        cr.arc(radius, radius, radius, math.pi, 3 * math.pi / 2)
        cr.close_path()
        cr.fill_preserve()
        cr.set_source_rgba(1.0, 1.0, 1.0, 0.12)
        cr.set_line_width(1.0)
        cr.stroke()

        cr.set_line_cap(cairo.LINE_CAP_ROUND)
        cr.set_line_join(cairo.LINE_JOIN_ROUND)
        r, g, b, a = self.rgba
        cr.set_source_rgba(r, g, b, a)
        cr.set_line_width(min(self.stroke_width, h - 8))

        margin = 16.0
        y_mid = h / 2.0
        cr.move_to(margin, y_mid)
        cr.curve_to(
            w * 0.28, y_mid - 11.0,
            w * 0.72, y_mid + 11.0,
            w - margin, y_mid
        )
        cr.stroke()


class SnippingEditor(Gtk.ApplicationWindow):
    def __init__(self, app: Gtk.Application, image: Image.Image, initial_path: Optional[str] = None):
        super().__init__(application=app)
        self.set_title("Snipping Tool - Markup & Crop")
        self.set_default_size(1120, 750)
        self.set_resizable(True)

        self.current_image = image.convert("RGBA")
        self.initial_path = initial_path

        # Zoom & Pan State
        self.fit_scale = 1.0
        self.zoom_multiplier = 1.0  # 1.0 means Fit to Window
        self.scale = 1.0
        self.pan_x = 0.0
        self.pan_y = 0.0
        self.offset_x = 0.0
        self.offset_y = 0.0
        self.disp_w = 0.0
        self.disp_h = 0.0

        # Mouse & Gesture Tracking
        self.mouse_pos = (0.0, 0.0)
        self.space_pressed = False
        self.is_panning = False
        self.pan_drag_start = (0.0, 0.0)
        self.pinch_start_multiplier = 1.0
        self.drag_start_x = 0.0
        self.drag_start_y = 0.0

        # Undo / Redo history
        self.strokes: List[Stroke] = []
        self.redo_stack: List[Stroke] = []
        self.image_history: List[Image.Image] = []

        # Current tool & properties
        self.active_tool = "pen"  # "pen", "highlighter", "eraser", "crop"
        self.pen_color = (0.92, 0.18, 0.18, 1.0)  # Vibrant Red
        self.pen_width = 3.5
        self.highlighter_color = (1.0, 0.90, 0.12, 0.35)  # Neon Yellow
        self.highlighter_width = 24.0

        # Crop state (in image coordinates)
        self.crop_active = False
        self.crop_x = 0
        self.crop_y = 0
        self.crop_w = 0
        self.crop_h = 0
        self.crop_drag_mode = None
        self.crop_drag_start = (0, 0)
        self.crop_rect_start = (0, 0, 0, 0)

        # Active drawing stroke
        self.current_stroke: Optional[Stroke] = None

        # Build Cairo surface for background image
        self.update_cairo_surface()

        # Apply CSS
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(get_app_css().encode("utf-8"))
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_USER
        )
        self.add_css_class("editor-window")

        # UI Components
        self.setup_ui()

    def update_cairo_surface(self):
        w, h = self.current_image.size
        raw_bgra = bytearray(self.current_image.tobytes("raw", "BGRA"))
        stride = cairo.ImageSurface.format_stride_for_width(cairo.FORMAT_ARGB32, w)
        self.cairo_surface = cairo.ImageSurface.create_for_data(
            raw_bgra, cairo.FORMAT_ARGB32, w, h, stride
        )

    def _make_tool_btn(self, icon_name: Optional[str], label_text: str, tooltip: str, on_click, custom_icon: Optional[Gtk.Widget] = None) -> Gtk.Button:
        btn = Gtk.Button()
        btn.add_css_class("tool-button")
        btn.set_tooltip_text(tooltip)
        btn.set_valign(Gtk.Align.CENTER)
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        box.set_valign(Gtk.Align.CENTER)
        box.set_halign(Gtk.Align.CENTER)
        if custom_icon is not None:
            box.append(custom_icon)
        elif icon_name:
            icon = Gtk.Image.new_from_icon_name(icon_name)
            icon.set_pixel_size(16)
            icon.set_valign(Gtk.Align.CENTER)
            box.append(icon)
        if label_text:
            lbl = Gtk.Label(label=label_text)
            lbl.set_valign(Gtk.Align.CENTER)
            lbl.set_yalign(0.5)
            box.append(lbl)
        btn.set_child(box)
        btn.connect("clicked", on_click)
        return btn

    def _make_palette_tool_btn(self, icon_name: str, label_text: str, tooltip: str, initial_color: Tuple[float, float, float, float], on_click) -> Tuple[Gtk.Button, ColorBar]:
        btn = Gtk.Button()
        btn.add_css_class("tool-button")
        btn.set_tooltip_text(tooltip)
        btn.set_valign(Gtk.Align.CENTER)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        vbox.set_valign(Gtk.Align.CENTER)
        vbox.set_halign(Gtk.Align.CENTER)

        top_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        top_box.set_valign(Gtk.Align.CENTER)
        top_box.set_halign(Gtk.Align.CENTER)

        icon = Gtk.Image.new_from_icon_name(icon_name)
        icon.set_pixel_size(16)
        icon.set_valign(Gtk.Align.CENTER)
        top_box.append(icon)

        lbl = Gtk.Label(label=label_text)
        lbl.set_valign(Gtk.Align.CENTER)
        lbl.set_yalign(0.5)
        top_box.append(lbl)

        chevron = VectorChevronDown(size=8)
        top_box.append(chevron)

        vbox.append(top_box)

        color_bar = ColorBar(initial_color, width=38, height=3)
        vbox.append(color_bar)

        btn.set_child(vbox)
        btn.connect("clicked", on_click)
        return btn, color_bar

    def setup_ui(self):
        # Header / Toolbar
        header = Gtk.HeaderBar()
        self.set_titlebar(header)

        # Left: Tools
        left_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        header.pack_start(left_box)

        # Pen Button & Popover
        self.btn_pen, self.pen_color_bar = self._make_palette_tool_btn(
            "document-edit-symbolic", "Pen", "Draw with pen (click when active to customize)",
            self.pen_color, self.on_pen_btn_clicked
        )
        self.btn_pen.add_css_class("active")
        left_box.append(self.btn_pen)
        self._build_pen_popover()

        # Highlighter Button & Popover
        self.btn_highlighter, self.highlighter_color_bar = self._make_palette_tool_btn(
            "view-paged-symbolic", "Highlighter", "Highlight content (click when active to customize)",
            self.highlighter_color, self.on_highlighter_btn_clicked
        )
        left_box.append(self.btn_highlighter)
        self._build_highlighter_popover()

        # Eraser Button
        self.btn_eraser = self._make_tool_btn(
            "edit-clear-symbolic", "Eraser", "Erase annotations", lambda _: self.set_tool("eraser")
        )
        left_box.append(self.btn_eraser)

        # Separator
        left_box.append(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL))

        # Crop Tool Button (Modern Vector Icon)
        self.crop_icon_widget = VectorCropIcon(16)
        self.btn_crop = self._make_tool_btn(
            None, "Crop", "Crop image (Ctrl+K or click)", lambda _: self.toggle_crop_mode(),
            custom_icon=self.crop_icon_widget
        )
        left_box.append(self.btn_crop)

        # Crop action buttons (hidden by default)
        self.crop_actions_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.crop_actions_box.set_visible(False)

        # Apply Crop Button (Modern vector checkmark with 8px spacing)
        btn_apply_crop = Gtk.Button()
        btn_apply_crop.add_css_class("action-btn-primary")
        btn_apply_crop.set_tooltip_text("Apply crop (Enter)")
        apply_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        apply_box.set_valign(Gtk.Align.CENTER)
        apply_box.set_halign(Gtk.Align.CENTER)
        self.apply_check_icon = VectorCheckIcon(size=13, stroke_width=2.4)
        apply_lbl = Gtk.Label(label="Apply")
        apply_lbl.set_valign(Gtk.Align.CENTER)
        apply_box.append(self.apply_check_icon)
        apply_box.append(apply_lbl)
        btn_apply_crop.set_child(apply_box)
        btn_apply_crop.connect("clicked", lambda _: self.apply_crop())
        self.crop_actions_box.append(btn_apply_crop)

        # Cancel Crop Button (Modern bold vector cross with 8px spacing)
        btn_cancel_crop = Gtk.Button()
        btn_cancel_crop.add_css_class("action-btn-secondary")
        btn_cancel_crop.set_tooltip_text("Cancel crop (Esc)")
        cancel_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        cancel_box.set_valign(Gtk.Align.CENTER)
        cancel_box.set_halign(Gtk.Align.CENTER)
        self.cancel_cross_icon = VectorCloseIcon(size=13, stroke_width=2.4)
        cancel_lbl = Gtk.Label(label="Cancel")
        cancel_lbl.set_valign(Gtk.Align.CENTER)
        cancel_box.append(self.cancel_cross_icon)
        cancel_box.append(cancel_lbl)
        btn_cancel_crop.set_child(cancel_box)
        btn_cancel_crop.connect("clicked", lambda _: self.cancel_crop())
        self.crop_actions_box.append(btn_cancel_crop)

        left_box.append(self.crop_actions_box)

        # Center: Undo/Redo & Zoom Controls
        center_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        header.set_title_widget(center_box)

        self.btn_undo = self._make_tool_btn(
            "edit-undo-symbolic", "Undo", "Undo (Ctrl+Z)", lambda _: self.undo()
        )
        center_box.append(self.btn_undo)

        self.btn_redo = self._make_tool_btn(
            "edit-redo-symbolic", "Redo", "Redo (Ctrl+Y)", lambda _: self.redo()
        )
        center_box.append(self.btn_redo)

        center_box.append(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL))

        # Zoom Controls - styled as clean tool-buttons matching Undo / Redo
        zoom_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        zoom_box.set_valign(Gtk.Align.CENTER)

        # Zoom Out Button
        btn_zoom_out = self._make_tool_btn(
            None, "", "Zoom Out (Ctrl - or Scroll Down)", lambda _: self.zoom_step(zoom_in=False),
            custom_icon=VectorMinusIcon(16)
        )
        zoom_box.append(btn_zoom_out)

        # Zoom Percentage / Fit Badge Button
        self.btn_zoom_badge = Gtk.Button(label="Fit")
        self.btn_zoom_badge.add_css_class("tool-button")
        self.btn_zoom_badge.add_css_class("zoom-badge")
        self.btn_zoom_badge.set_tooltip_text("Click to Fit to Window (Ctrl+0)")
        self.btn_zoom_badge.set_valign(Gtk.Align.CENTER)
        self.btn_zoom_badge.connect("clicked", lambda _: self.zoom_to(1.0))
        zoom_box.append(self.btn_zoom_badge)

        # Zoom In Button
        btn_zoom_in = self._make_tool_btn(
            None, "", "Zoom In (Ctrl + or Scroll Up)", lambda _: self.zoom_step(zoom_in=True),
            custom_icon=VectorPlusIcon(16)
        )
        zoom_box.append(btn_zoom_in)

        center_box.append(zoom_box)

        # Right: Copy & Save Buttons
        right_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        header.pack_end(right_box)

        # Save Button
        self.btn_save = Gtk.Button()
        self.btn_save.add_css_class("suggested-action")
        self.btn_save.add_css_class("action-btn-primary")
        self.btn_save.set_valign(Gtk.Align.CENTER)
        save_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        save_box.set_valign(Gtk.Align.CENTER)
        save_box.set_halign(Gtk.Align.CENTER)
        save_icon = Gtk.Image.new_from_icon_name("document-save-symbolic")
        save_icon.set_pixel_size(15)
        save_icon.set_valign(Gtk.Align.CENTER)
        save_box.append(save_icon)
        lbl_save = Gtk.Label(label="Save")
        lbl_save.set_valign(Gtk.Align.CENTER)
        lbl_save.set_yalign(0.5)
        save_box.append(lbl_save)
        self.btn_save.set_child(save_box)
        self.btn_save.set_tooltip_text("Save to ~/Pictures/Screenshots")
        self.btn_save.connect("clicked", lambda _: self.save_screenshot())
        right_box.append(self.btn_save)

        # Copy Button
        self.btn_copy = Gtk.Button()
        self.btn_copy.add_css_class("action-btn-secondary")
        self.btn_copy.set_valign(Gtk.Align.CENTER)
        copy_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        copy_box.set_valign(Gtk.Align.CENTER)
        copy_box.set_halign(Gtk.Align.CENTER)
        copy_icon = Gtk.Image.new_from_icon_name("edit-copy-symbolic")
        copy_icon.set_pixel_size(15)
        copy_icon.set_valign(Gtk.Align.CENTER)
        copy_box.append(copy_icon)
        lbl_copy = Gtk.Label(label="Copy")
        lbl_copy.set_valign(Gtk.Align.CENTER)
        lbl_copy.set_yalign(0.5)
        copy_box.append(lbl_copy)
        self.btn_copy.set_child(copy_box)
        self.btn_copy.set_tooltip_text("Copy image to clipboard")
        self.btn_copy.connect("clicked", lambda _: self.copy_to_clipboard())
        right_box.append(self.btn_copy)

        # Main Layout: Canvas directly under header bar
        main_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_child(main_vbox)

        # Canvas Drawing Area
        self.canvas = Gtk.DrawingArea()
        self.canvas.set_vexpand(True)
        self.canvas.set_hexpand(True)
        self.canvas.set_draw_func(self.on_draw_canvas)
        main_vbox.append(self.canvas)

        # 1. Canvas Drag Gesture (Supports left-click drawing, right/middle click panning)
        drag = Gtk.GestureDrag()
        drag.set_button(0)  # Receive all mouse buttons
        drag.connect("drag-begin", self.on_canvas_drag_begin)
        drag.connect("drag-update", self.on_canvas_drag_update)
        drag.connect("drag-end", self.on_canvas_drag_end)
        self.canvas.add_controller(drag)

        # 2. Touchpad Pinch-to-Zoom Gesture
        zoom_gesture = Gtk.GestureZoom()
        zoom_gesture.connect("begin", self.on_zoom_gesture_begin)
        zoom_gesture.connect("scale-changed", self.on_zoom_gesture_scale_changed)
        self.canvas.add_controller(zoom_gesture)

        # 3. Mouse Wheel & Touchpad 2-Finger Scroll Controller
        scroll_ctrl = Gtk.EventControllerScroll.new(Gtk.EventControllerScrollFlags.BOTH_AXES)
        scroll_ctrl.connect("scroll", self.on_canvas_scroll)
        self.canvas.add_controller(scroll_ctrl)

        # 4. Motion Controller (Tracks mouse cursor coordinates)
        motion = Gtk.EventControllerMotion()
        motion.connect("motion", self.on_canvas_motion)
        self.canvas.add_controller(motion)

        # 5. Keyboard Controller (Window level for shortcuts & Spacebar pan)
        key = Gtk.EventControllerKey()
        key.connect("key-pressed", self.on_key_pressed)
        key.connect("key-released", self.on_key_released)
        self.add_controller(key)

        # Status feedback label
        self.feedback_revealer = Gtk.Revealer()
        self.feedback_revealer.set_transition_type(Gtk.RevealerTransitionType.SLIDE_DOWN)
        self.feedback_label = Gtk.Label(label="")
        self.feedback_label.add_css_class("feedback-pill")
        self.feedback_label.set_margin_top(8)
        self.feedback_label.set_margin_bottom(8)
        self.feedback_revealer.set_child(self.feedback_label)
        main_vbox.prepend(self.feedback_revealer)

    # ==========================
    # TOOL PALETTES & POPOVERS
    # ==========================

    def on_pen_btn_clicked(self, _btn):
        if self.active_tool == "pen":
            # Already active: toggle popover!
            if self.pen_popover.get_visible():
                self.pen_popover.popdown()
            else:
                self.pen_popover.popup()
        else:
            self.set_tool("pen")

    def on_highlighter_btn_clicked(self, _btn):
        if self.active_tool == "highlighter":
            # Already active: toggle popover!
            if self.highlighter_popover.get_visible():
                self.highlighter_popover.popdown()
            else:
                self.highlighter_popover.popup()
        else:
            self.set_tool("highlighter")

    def _color_matches(self, c1, c2):
        return (abs(c1[0] - c2[0]) < 0.05 and
                abs(c1[1] - c2[1]) < 0.05 and
                abs(c1[2] - c2[2]) < 0.05)

    def _build_pen_popover(self):
        self.pen_popover = Gtk.Popover()
        self.pen_popover.add_css_class("tool-popover")
        self.pen_popover.set_parent(self.btn_pen)
        self.pen_popover.set_position(Gtk.PositionType.BOTTOM)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        content.set_size_request(210, -1)

        # 1. Color Palette Section
        lbl_color = Gtk.Label(label="Color")
        lbl_color.add_css_class("popover-section-label")
        lbl_color.set_halign(Gtk.Align.START)
        content.append(lbl_color)

        pen_colors = [
            ("#000000", (0.10, 0.10, 0.12, 1.0), "Black"),
            ("#FFFFFF", (1.00, 1.00, 1.00, 1.0), "White"),
            ("#E81123", (0.91, 0.07, 0.14, 1.0), "Red"),
            ("#FF8C00", (1.00, 0.55, 0.00, 1.0), "Orange"),
            ("#FFF100", (1.00, 0.95, 0.00, 1.0), "Yellow"),
            ("#107C41", (0.06, 0.49, 0.25, 1.0), "Green"),
            ("#00B7C3", (0.00, 0.72, 0.76, 1.0), "Cyan"),
            ("#0078D4", (0.00, 0.47, 0.83, 1.0), "Blue"),
            ("#881798", (0.53, 0.09, 0.59, 1.0), "Purple"),
            ("#E3008C", (0.89, 0.00, 0.55, 1.0), "Pink"),
        ]

        # Swatches grid (2 rows of 5)
        swatches_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        swatches_box.set_halign(Gtk.Align.CENTER)
        row1 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        row1.set_halign(Gtk.Align.CENTER)
        row2 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        row2.set_halign(Gtk.Align.CENTER)

        self.pen_swatch_btns = []
        for i, (hex_code, rgba, name) in enumerate(pen_colors):
            btn = Gtk.Button()
            btn.add_css_class("color-swatch-btn")
            btn.set_tooltip_text(name)
            is_white = (name == "White")
            btn.set_child(ColorDot(rgba, diameter=22, is_white=is_white))

            if self._color_matches(rgba, self.pen_color):
                btn.add_css_class("selected")

            def make_handler(c_rgba=rgba, b=btn):
                return lambda _: self._select_pen_color(c_rgba, b)

            btn.connect("clicked", make_handler())
            if i < 5:
                row1.append(btn)
            else:
                row2.append(btn)
            self.pen_swatch_btns.append((btn, rgba))

        swatches_box.append(row1)
        swatches_box.append(row2)
        content.append(swatches_box)

        # 2. Size / Thickness Section
        lbl_size = Gtk.Label(label="Size")
        lbl_size.add_css_class("popover-section-label")
        lbl_size.set_halign(Gtk.Align.START)
        content.append(lbl_size)

        size_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        size_box.set_halign(Gtk.Align.CENTER)

        pen_sizes = [
            (1.5, 3.0, "Fine (1px)"),
            (3.5, 5.0, "Medium (4px)"),
            (6.0, 7.5, "Thick (8px)"),
            (10.0, 10.5, "Heavy (12px)"),
            (16.0, 14.0, "Extra Heavy (16px)"),
        ]

        self.pen_size_btns = []
        for width_val, dot_size, name in pen_sizes:
            btn = Gtk.Button()
            btn.add_css_class("size-preset-btn")
            btn.set_tooltip_text(name)
            btn.set_child(SizeDot(dot_size=dot_size))

            if abs(self.pen_width - width_val) < 1.0:
                btn.add_css_class("selected")

            def make_size_handler(w=width_val, b=btn):
                return lambda _: self._select_pen_size(w, b)

            btn.connect("clicked", make_size_handler())
            size_box.append(btn)
            self.pen_size_btns.append((btn, width_val))

        content.append(size_box)

        # Size slider for fine adjustment
        self.pen_slider = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 1.0, 24.0, 1.0)
        self.pen_slider.set_value(self.pen_width)
        self.pen_slider.set_draw_value(False)
        self.pen_slider.connect("value-changed", self._on_pen_slider_changed)
        content.append(self.pen_slider)

        # 3. Live Stroke Preview
        self.pen_stroke_preview = StrokePreview(is_highlighter=False)
        self.pen_stroke_preview.update_stroke(self.pen_color, self.pen_width)
        content.append(self.pen_stroke_preview)

        self.pen_popover.set_child(content)

    def _select_pen_color(self, rgba: Tuple[float, float, float, float], active_btn: Gtk.Button):
        self.pen_color = rgba
        for btn, _ in self.pen_swatch_btns:
            btn.remove_css_class("selected")
        active_btn.add_css_class("selected")
        self.pen_color_bar.set_color(rgba)
        self.pen_stroke_preview.update_stroke(self.pen_color, self.pen_width)
        self.set_tool("pen")

    def _select_pen_size(self, width: float, active_btn: Gtk.Button):
        self.pen_width = width
        for btn, _ in self.pen_size_btns:
            btn.remove_css_class("selected")
        active_btn.add_css_class("selected")
        self.pen_slider.set_value(width)
        self.pen_stroke_preview.update_stroke(self.pen_color, self.pen_width)
        self.set_tool("pen")

    def _on_pen_slider_changed(self, slider: Gtk.Scale):
        val = slider.get_value()
        self.pen_width = val
        for btn, w in self.pen_size_btns:
            if abs(w - val) < 1.0:
                btn.add_css_class("selected")
            else:
                btn.remove_css_class("selected")
        self.pen_stroke_preview.update_stroke(self.pen_color, self.pen_width)

    def _build_highlighter_popover(self):
        self.highlighter_popover = Gtk.Popover()
        self.highlighter_popover.add_css_class("tool-popover")
        self.highlighter_popover.set_parent(self.btn_highlighter)
        self.highlighter_popover.set_position(Gtk.PositionType.BOTTOM)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        content.set_size_request(210, -1)

        # 1. Color Palette Section
        lbl_color = Gtk.Label(label="Highlighter Color")
        lbl_color.add_css_class("popover-section-label")
        lbl_color.set_halign(Gtk.Align.START)
        content.append(lbl_color)

        highlighter_colors = [
            ("#FFF100", (1.00, 0.95, 0.00, 0.35), "Neon Yellow"),
            ("#7FBA00", (0.50, 0.73, 0.00, 0.35), "Neon Green"),
            ("#00B7C3", (0.00, 0.72, 0.76, 0.35), "Neon Cyan"),
            ("#E3008C", (0.89, 0.00, 0.55, 0.35), "Neon Pink"),
            ("#FF8C00", (1.00, 0.55, 0.00, 0.35), "Neon Orange"),
            ("#B146C2", (0.69, 0.27, 0.76, 0.35), "Lavender"),
        ]

        swatches_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        swatches_row.set_halign(Gtk.Align.CENTER)

        self.highlighter_swatch_btns = []
        for hex_code, rgba, name in highlighter_colors:
            btn = Gtk.Button()
            btn.add_css_class("color-swatch-btn")
            btn.set_tooltip_text(name)
            btn.set_child(ColorDot(rgba, diameter=22))

            if self._color_matches(rgba, self.highlighter_color):
                btn.add_css_class("selected")

            def make_handler(c_rgba=rgba, b=btn):
                return lambda _: self._select_highlighter_color(c_rgba, b)

            btn.connect("clicked", make_handler())
            swatches_row.append(btn)
            self.highlighter_swatch_btns.append((btn, rgba))

        content.append(swatches_row)


        # 2. Size Section
        lbl_size = Gtk.Label(label="Size")
        lbl_size.add_css_class("popover-section-label")
        lbl_size.set_halign(Gtk.Align.START)
        content.append(lbl_size)

        size_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        size_box.set_halign(Gtk.Align.CENTER)

        hl_sizes = [
            (12.0, 5.0, "Fine (12px)"),
            (18.0, 7.5, "Medium (18px)"),
            (24.0, 10.5, "Thick (24px)"),
            (36.0, 14.0, "Extra Thick (36px)"),
        ]

        self.highlighter_size_btns = []
        for width_val, dot_size, name in hl_sizes:
            btn = Gtk.Button()
            btn.add_css_class("size-preset-btn")
            btn.set_tooltip_text(name)
            btn.set_child(SizeDot(dot_size=dot_size))

            if abs(self.highlighter_width - width_val) < 2.0:
                btn.add_css_class("selected")

            def make_hl_size_handler(w=width_val, b=btn):
                return lambda _: self._select_highlighter_size(w, b)

            btn.connect("clicked", make_hl_size_handler())
            size_box.append(btn)
            self.highlighter_size_btns.append((btn, width_val))

        content.append(size_box)

        self.hl_slider = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 8.0, 48.0, 2.0)
        self.hl_slider.set_value(self.highlighter_width)
        self.hl_slider.set_draw_value(False)
        self.hl_slider.connect("value-changed", self._on_hl_slider_changed)
        content.append(self.hl_slider)

        # 3. Live Stroke Preview
        self.hl_stroke_preview = StrokePreview(is_highlighter=True)
        self.hl_stroke_preview.update_stroke(self.highlighter_color, self.highlighter_width)
        content.append(self.hl_stroke_preview)

        self.highlighter_popover.set_child(content)

    def _select_highlighter_color(self, rgba: Tuple[float, float, float, float], active_btn: Gtk.Button):
        self.highlighter_color = rgba
        for btn, _ in self.highlighter_swatch_btns:
            btn.remove_css_class("selected")
        active_btn.add_css_class("selected")
        self.highlighter_color_bar.set_color(rgba)
        self.hl_stroke_preview.update_stroke(self.highlighter_color, self.highlighter_width)
        self.set_tool("highlighter")

    def _select_highlighter_size(self, width: float, active_btn: Gtk.Button):
        self.highlighter_width = width
        for btn, _ in self.highlighter_size_btns:
            btn.remove_css_class("selected")
        active_btn.add_css_class("selected")
        self.hl_slider.set_value(width)
        self.hl_stroke_preview.update_stroke(self.highlighter_color, self.highlighter_width)
        self.set_tool("highlighter")

    def _on_hl_slider_changed(self, slider: Gtk.Scale):
        val = slider.get_value()
        self.highlighter_width = val
        for btn, w in self.highlighter_size_btns:
            if abs(w - val) < 2.0:
                btn.add_css_class("selected")
            else:
                btn.remove_css_class("selected")
        self.hl_stroke_preview.update_stroke(self.highlighter_color, self.highlighter_width)

    # ==========================
    # ZOOM & PAN LOGIC
    # ==========================


    def zoom_to(self, new_multiplier: float, focal_x: Optional[float] = None, focal_y: Optional[float] = None):
        """Zooms to a specific multiplier level, preserving the image point under the focal point."""
        new_multiplier = max(0.20, min(10.0, new_multiplier))
        if abs(new_multiplier - self.zoom_multiplier) < 0.005:
            return

        iw, ih = self.current_image.size
        alloc_w = self.canvas.get_width()
        alloc_h = self.canvas.get_height()

        if focal_x is None or focal_y is None:
            focal_x = alloc_w / 2.0
            focal_y = alloc_h / 2.0

        # Point in image space under the focal point before zoom
        old_scale = max(0.0001, self.scale)
        ix = (focal_x - self.offset_x) / old_scale
        iy = (focal_y - self.offset_y) / old_scale

        # Calculate new scale
        new_scale = self.fit_scale * new_multiplier
        new_disp_w = iw * new_scale
        new_disp_h = ih * new_scale

        self.zoom_multiplier = new_multiplier
        self.scale = new_scale
        self.disp_w = new_disp_w
        self.disp_h = new_disp_h

        if self.zoom_multiplier <= 1.01:
            self.pan_x = 0.0
            self.pan_y = 0.0
        else:
            # Shift pan so the image point stays under the focal coordinate
            new_offset_x = focal_x - ix * new_scale
            new_offset_y = focal_y - iy * new_scale
            self.pan_x = new_offset_x - (alloc_w - new_disp_w) / 2.0
            self.pan_y = new_offset_y - (alloc_h - new_disp_h) / 2.0

        self.update_zoom_label()
        self.canvas.queue_draw()

    def zoom_step(self, zoom_in: bool = True):
        factor = 1.25 if zoom_in else (1.0 / 1.25)
        cx, cy = self.mouse_pos
        if cx <= 0 or cy <= 0:
            cx = self.canvas.get_width() / 2.0
            cy = self.canvas.get_height() / 2.0
        self.zoom_to(self.zoom_multiplier * factor, cx, cy)

    def update_zoom_label(self):
        if abs(self.zoom_multiplier - 1.0) < 0.05:
            self.btn_zoom_badge.set_label("Fit")
        else:
            pct = int(round(self.zoom_multiplier * 100))
            self.btn_zoom_badge.set_label(f"{pct}%")

    def on_zoom_gesture_begin(self, gesture, sequence):
        self.pinch_start_multiplier = self.zoom_multiplier

    def on_zoom_gesture_scale_changed(self, gesture, scale):
        has_center, center_x, center_y = gesture.get_bounding_box_center()
        if not has_center:
            center_x, center_y = self.mouse_pos
        new_multiplier = self.pinch_start_multiplier * scale
        self.zoom_to(new_multiplier, center_x, center_y)

    def on_canvas_scroll(self, controller, dx: float, dy: float) -> bool:
        cursor_x, cursor_y = self.mouse_pos
        state = controller.get_current_event_state()
        ctrl_held = bool(state & Gdk.ModifierType.CONTROL_MASK)

        if ctrl_held:
            # Ctrl + Scroll Wheel / Touchpad: Zoom smoothly at cursor position
            factor = 1.15 if dy < 0 else (1.0 / 1.15) if dy > 0 else 1.0
            if factor != 1.0:
                self.zoom_to(self.zoom_multiplier * factor, cursor_x, cursor_y)
            return True
        else:
            # Without Ctrl:
            if self.zoom_multiplier > 1.02:
                # Two-finger touchpad swipe or wheel pans the zoomed canvas
                self.pan_x -= dx * 20.0
                self.pan_y -= dy * 20.0
                self.canvas.queue_draw()
                return True
            else:
                # When at 100% Fit, scrolling up immediately zooms in
                if dy < 0:
                    self.zoom_to(self.zoom_multiplier * 1.15, cursor_x, cursor_y)
                    return True
        return False

    # ==========================
    # COORDINATE MAPPING
    # ==========================

    def canvas_to_image(self, cx: float, cy: float) -> Tuple[float, float]:
        """Converts canvas screen coordinates to native image coordinates."""
        if self.scale <= 0:
            return (0.0, 0.0)
        ix = (cx - self.offset_x) / self.scale
        iy = (cy - self.offset_y) / self.scale
        ix = max(0.0, min(float(self.current_image.width), ix))
        iy = max(0.0, min(float(self.current_image.height), iy))
        return (ix, iy)

    # ==========================
    # TOOL & CROP LOGIC
    # ==========================

    def set_tool(self, tool: str):
        self.active_tool = tool
        self.btn_pen.remove_css_class("active")
        self.btn_highlighter.remove_css_class("active")
        self.btn_eraser.remove_css_class("active")

        # Close any open popovers when changing tools
        if hasattr(self, "pen_popover"):
            self.pen_popover.popdown()
        if hasattr(self, "highlighter_popover"):
            self.highlighter_popover.popdown()

        if self.crop_active:
            self.cancel_crop()

        if tool == "pen":
            self.btn_pen.add_css_class("active")
        elif tool == "highlighter":
            self.btn_highlighter.add_css_class("active")
        elif tool == "eraser":
            self.btn_eraser.add_css_class("active")

        self.update_cursor()
        self.canvas.queue_draw()

    def toggle_crop_mode(self):
        if not self.crop_active:
            self.crop_active = True
            self.btn_crop.add_css_class("active")
            self.crop_actions_box.set_visible(True)

            self.btn_pen.remove_css_class("active")
            self.btn_highlighter.remove_css_class("active")
            self.btn_eraser.remove_css_class("active")

            # Initialize crop box with 5% margins in image coordinates
            w, h = self.current_image.size
            margin_x = max(10, int(w * 0.05))
            margin_y = max(10, int(h * 0.05))
            self.crop_x = margin_x
            self.crop_y = margin_y
            self.crop_w = max(20, w - 2 * margin_x)
            self.crop_h = max(20, h - 2 * margin_y)
        else:
            self.cancel_crop()
        self.update_cursor()
        self.canvas.queue_draw()

    def cancel_crop(self):
        self.crop_active = False
        self.crop_drag_mode = None
        self.btn_crop.remove_css_class("active")
        self.crop_actions_box.set_visible(False)
        # Restore active visual class to the active markup tool
        if self.active_tool == "pen":
            self.btn_pen.add_css_class("active")
        elif self.active_tool == "highlighter":
            self.btn_highlighter.add_css_class("active")
        elif self.active_tool == "eraser":
            self.btn_eraser.add_css_class("active")
        self.update_cursor()
        self.canvas.queue_draw()

    def apply_crop(self):
        if not self.crop_active or self.crop_w <= 10 or self.crop_h <= 10:
            self.cancel_crop()
            return

        rendered = self.render_current_composite()
        self.image_history.append(self.current_image.copy())

        x1 = max(0, self.crop_x)
        y1 = max(0, self.crop_y)
        x2 = min(self.current_image.width, self.crop_x + self.crop_w)
        y2 = min(self.current_image.height, self.crop_y + self.crop_h)

        self.current_image = rendered.crop((x1, y1, x2, y2))
        self.strokes.clear()
        self.redo_stack.clear()
        self.update_cairo_surface()

        # Reset zoom to Fit the new cropped image
        self.zoom_multiplier = 1.0
        self.pan_x = 0.0
        self.pan_y = 0.0
        self.update_zoom_label()

        self.cancel_crop()
        self.show_feedback("Crop applied!")

    # ==========================
    # MOUSE / DRAG INTERACTION
    # ==========================

    def on_canvas_drag_begin(self, gesture, start_x, start_y):
        self.drag_start_x = start_x
        self.drag_start_y = start_y
        button = gesture.get_current_button()

        # Panning with middle click, right click, or Spacebar + drag
        if button in (2, 3) or self.space_pressed:
            self.is_panning = True
            self.pan_drag_start = (self.pan_x, self.pan_y)
            try:
                self.canvas.set_cursor(Gdk.Cursor.new_from_name("grabbing", None))
            except Exception:
                pass
            return

        # Crop Dragging
        if self.crop_active:
            handle = self.get_crop_handle_at(start_x, start_y)
            if handle:
                self.crop_drag_start = (start_x, start_y)
                self.crop_rect_start = (self.crop_x, self.crop_y, self.crop_w, self.crop_h)
                self.crop_drag_mode = handle
                self.update_cursor()
            return

        # Check if click is on or near the scaled image (tolerance 24px)
        margin = 24.0
        if not (self.offset_x - margin <= start_x <= self.offset_x + self.disp_w + margin and
                self.offset_y - margin <= start_y <= self.offset_y + self.disp_h + margin):
            return

        ix, iy = self.canvas_to_image(start_x, start_y)

        if self.active_tool in ("pen", "highlighter"):
            color = self.pen_color if self.active_tool == "pen" else self.highlighter_color

            width = self.pen_width if self.active_tool == "pen" else self.highlighter_width
            self.current_stroke = Stroke(self.active_tool, color, width)
            self.current_stroke.points.append((ix, iy))
            self.strokes.append(self.current_stroke)
            self.redo_stack.clear()
            self.canvas.queue_draw()

        elif self.active_tool == "eraser":
            self.erase_at(ix, iy)

    def on_canvas_drag_update(self, gesture, offset_x, offset_y):
        if self.is_panning:
            px, py = self.pan_drag_start
            self.pan_x = px + offset_x
            self.pan_y = py + offset_y
            self.canvas.queue_draw()
            return

        start_x = self.drag_start_x
        start_y = self.drag_start_y
        curr_x = start_x + offset_x
        curr_y = start_y + offset_y

        if self.crop_active and self.crop_drag_mode:
            if self.crop_drag_mode == "new":
                ix1, iy1 = self.canvas_to_image(start_x, start_y)
                curr_ix, curr_iy = self.canvas_to_image(curr_x, curr_y)
                x1 = min(ix1, curr_ix)
                x2 = max(ix1, curr_ix)
                y1 = min(iy1, curr_iy)
                y2 = max(iy1, curr_iy)
                if (x2 - x1) >= 5 or (y2 - y1) >= 5:
                    self.crop_x = int(round(x1))
                    self.crop_y = int(round(y1))
                    self.crop_w = int(round(x2 - x1))
                    self.crop_h = int(round(y2 - y1))
                    self.canvas.queue_draw()
                return

            dx = offset_x / max(0.001, self.scale)
            dy = offset_y / max(0.001, self.scale)
            ox, oy, ow, oh = self.crop_rect_start
            img_w = self.current_image.width
            img_h = self.current_image.height
            MIN_SZ = 20

            if self.crop_drag_mode == "inside":
                # Translate entire crop box bounded cleanly inside image
                max_dx = img_w - (ox + ow)
                min_dx = -ox
                clamped_dx = max(min_dx, min(max_dx, dx))

                max_dy = img_h - (oy + oh)
                min_dy = -oy
                clamped_dy = max(min_dy, min(max_dy, dy))

                self.crop_x = int(round(ox + clamped_dx))
                self.crop_y = int(round(oy + clamped_dy))
                self.crop_w = int(round(ow))
                self.crop_h = int(round(oh))
            else:
                ox1, oy1 = ox, oy
                ox2, oy2 = ox + ow, oy + oh
                x1, y1, x2, y2 = ox1, oy1, ox2, oy2

                # Horizontal anchor logic (opposite edge strictly pinned)
                if self.crop_drag_mode in ("tl", "l", "bl"):
                    x1 = min(ox2 - MIN_SZ, max(0, ox1 + dx))
                elif self.crop_drag_mode in ("tr", "r", "br"):
                    x2 = max(ox1 + MIN_SZ, min(img_w, ox2 + dx))

                # Vertical anchor logic (opposite edge strictly pinned)
                if self.crop_drag_mode in ("tl", "t", "tr"):
                    y1 = min(oy2 - MIN_SZ, max(0, oy1 + dy))
                elif self.crop_drag_mode in ("bl", "b", "br"):
                    y2 = max(oy1 + MIN_SZ, min(img_h, oy2 + dy))

                self.crop_x = int(round(x1))
                self.crop_y = int(round(y1))
                self.crop_w = int(round(x2 - x1))
                self.crop_h = int(round(y2 - y1))

            self.canvas.queue_draw()
            return

        if self.current_stroke:
            ix, iy = self.canvas_to_image(curr_x, curr_y)
            self.current_stroke.points.append((ix, iy))
            self.canvas.queue_draw()

        elif self.active_tool == "eraser":
            ix, iy = self.canvas_to_image(curr_x, curr_y)
            self.erase_at(ix, iy)

    def on_canvas_drag_end(self, gesture, offset_x, offset_y):
        if self.is_panning:
            self.is_panning = False
            self.update_cursor()
            return
        if self.crop_active:
            if self.crop_drag_mode == "new":
                if self.crop_w < 20 or self.crop_h < 20:
                    self.crop_x, self.crop_y, self.crop_w, self.crop_h = self.crop_rect_start
                    self.canvas.queue_draw()
            self.crop_drag_mode = None
            self.update_cursor()
            return
        self.current_stroke = None

    def on_canvas_motion(self, controller, x, y):
        self.mouse_pos = (x, y)
        self.update_cursor()

    def update_cursor(self):
        if self.is_panning:
            cursor_name = "grabbing"
        elif self.space_pressed:
            cursor_name = "grab"
        elif self.crop_active:
            # If dragging, lock cursor to the active drag handle
            handle = self.crop_drag_mode if self.crop_drag_mode else self.get_crop_handle_at(self.mouse_pos[0], self.mouse_pos[1])
            if handle in ("tl", "br"):
                cursor_name = "nwse-resize"
            elif handle in ("tr", "bl"):
                cursor_name = "nesw-resize"
            elif handle in ("t", "b"):
                cursor_name = "ns-resize"
            elif handle in ("l", "r"):
                cursor_name = "ew-resize"
            elif handle == "inside":
                cursor_name = "move"
            elif handle == "new":
                cursor_name = "crosshair"
            else:
                cursor_name = "default"
        elif self.active_tool in ("pen", "highlighter"):
            cursor_name = "crosshair"
        elif self.active_tool == "eraser":
            cursor_name = "cell"
        else:
            cursor_name = "default"

        try:
            self.canvas.set_cursor(Gdk.Cursor.new_from_name(cursor_name, None))
        except Exception:
            pass

    def get_crop_handle_at(self, x: float, y: float) -> Optional[str]:
        if not self.crop_active:
            return None

        cx = self.offset_x + self.crop_x * self.scale
        cy = self.offset_y + self.crop_y * self.scale
        cw = self.crop_w * self.scale
        ch = self.crop_h * self.scale

        CORNER_HIT = 28.0
        EDGE_HIT = 18.0

        # Check 4 corners first (hypot radius)
        if math.hypot(x - cx, y - cy) <= CORNER_HIT:
            return "tl"
        if math.hypot(x - (cx + cw), y - cy) <= CORNER_HIT:
            return "tr"
        if math.hypot(x - cx, y - (cy + ch)) <= CORNER_HIT:
            return "bl"
        if math.hypot(x - (cx + cw), y - (cy + ch)) <= CORNER_HIT:
            return "br"

        # Check 4 edges (corridors along the full length of each edge)
        if (cx - 10) <= x <= (cx + cw + 10) and abs(y - cy) <= EDGE_HIT:
            return "t"
        if (cx - 10) <= x <= (cx + cw + 10) and abs(y - (cy + ch)) <= EDGE_HIT:
            return "b"
        if (cy - 10) <= y <= (cy + ch + 10) and abs(x - cx) <= EDGE_HIT:
            return "l"
        if (cy - 10) <= y <= (cy + ch + 10) and abs(x - (cx + cw)) <= EDGE_HIT:
            return "r"

        # Check inside crop box
        if cx <= x <= (cx + cw) and cy <= y <= (cy + ch):
            return "inside"

        # Check if within image bounds (for drawing a new crop box)
        if (self.offset_x <= x <= self.offset_x + self.disp_w and
            self.offset_y <= y <= self.offset_y + self.disp_h):
            return "new"

        return None

    def erase_at(self, ix: float, iy: float):
        radius = 18.0 / max(0.1, self.scale)
        to_remove = []
        for stroke in self.strokes:
            for px, py in stroke.points:
                if math.hypot(px - ix, py - iy) <= radius + stroke.width / 2:
                    to_remove.append(stroke)
                    break
        if to_remove:
            for s in to_remove:
                self.strokes.remove(s)
            self.canvas.queue_draw()

    def undo(self):
        if self.strokes:
            stroke = self.strokes.pop()
            self.redo_stack.append(stroke)
            self.canvas.queue_draw()
        elif self.image_history:
            self.current_image = self.image_history.pop()
            self.update_cairo_surface()
            self.canvas.queue_draw()
            self.show_feedback("Undo crop")

    def redo(self):
        if self.redo_stack:
            stroke = self.redo_stack.pop()
            self.strokes.append(stroke)
            self.canvas.queue_draw()

    def on_key_pressed(self, controller, keyval, keycode, state):
        ctrl = state & Gdk.ModifierType.CONTROL_MASK
        shift = state & Gdk.ModifierType.SHIFT_MASK

        if keyval == Gdk.KEY_space:
            self.space_pressed = True
            self.update_cursor()
            return True

        if ctrl and keyval in (Gdk.KEY_plus, Gdk.KEY_equal, Gdk.KEY_KP_Add):
            self.zoom_step(zoom_in=True)
            return True
        elif ctrl and keyval in (Gdk.KEY_minus, Gdk.KEY_KP_Subtract, Gdk.KEY_underscore):
            self.zoom_step(zoom_in=False)
            return True
        elif ctrl and keyval in (Gdk.KEY_0, Gdk.KEY_KP_0):
            self.zoom_to(1.0)
            return True
        elif ctrl and keyval in (Gdk.KEY_z, Gdk.KEY_Z):
            if shift:
                self.redo()
            else:
                self.undo()
            return True
        elif ctrl and keyval in (Gdk.KEY_y, Gdk.KEY_Y):
            self.redo()
            return True
        elif ctrl and keyval in (Gdk.KEY_s, Gdk.KEY_S):
            self.save_screenshot()
            return True
        elif ctrl and keyval in (Gdk.KEY_c, Gdk.KEY_C):
            self.copy_to_clipboard()
            return True
        elif ctrl and keyval in (Gdk.KEY_k, Gdk.KEY_K):
            self.toggle_crop_mode()
            return True
        elif keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter):
            if self.crop_active:
                self.apply_crop()
                return True
        elif keyval == Gdk.KEY_Escape:
            if self.crop_active:
                self.cancel_crop()
            else:
                self.close()
            return True
        return False

    def on_key_released(self, controller, keyval, keycode, state):
        if keyval == Gdk.KEY_space:
            self.space_pressed = False
            self.update_cursor()

    # ==========================
    # RENDERING & EXPORT
    # ==========================

    def render_current_composite(self) -> Image.Image:
        w, h = self.current_image.size
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
        cr = cairo.Context(surface)

        # Base image
        cr.set_source_surface(self.cairo_surface, 0, 0)
        cr.paint()

        # Render all strokes in original full resolution
        self.render_strokes_to_cairo(cr)

        # Convert back to PIL Image
        data = surface.get_data()
        pil_img = Image.frombuffer("RGBA", (w, h), bytes(data), "raw", "BGRA", 0, 1)
        return pil_img.copy()

    def render_strokes_to_cairo(self, cr: cairo.Context):
        cr.set_line_cap(cairo.LINE_CAP_ROUND)
        cr.set_line_join(cairo.LINE_JOIN_ROUND)

        for stroke in self.strokes:
            if len(stroke.points) < 1:
                continue
            r, g, b, a = stroke.color_rgba
            cr.set_source_rgba(r, g, b, a)
            cr.set_line_width(stroke.width)

            if len(stroke.points) == 1:
                cr.arc(stroke.points[0][0], stroke.points[0][1], stroke.width / 2, 0, 2 * math.pi)
                cr.fill()
            else:
                cr.move_to(*stroke.points[0])
                for pt in stroke.points[1:]:
                    cr.line_to(*pt)
                cr.stroke()

    def on_draw_canvas(self, area, cr: cairo.Context, width: int, height: int):
        # 1. Fill backdrop with dark neutral workbench tone
        cr.set_source_rgba(0.13, 0.14, 0.17, 1.0)
        cr.paint()

        iw, ih = self.current_image.size
        if iw <= 0 or ih <= 0:
            return

        # 2. Compute dynamic fit-to-window scaling
        padding = 24
        avail_w = max(10, width - padding * 2)
        avail_h = max(10, height - padding * 2)

        fit_scale = min(avail_w / iw, avail_h / ih)
        self.fit_scale = 1.0 if (iw <= avail_w and ih <= avail_h and fit_scale >= 1.0) else fit_scale

        self.scale = self.fit_scale * self.zoom_multiplier
        self.disp_w = iw * self.scale
        self.disp_h = ih * self.scale

        # Auto-center when at 1.0 fit
        if self.zoom_multiplier <= 1.01:
            self.pan_x = 0.0
            self.pan_y = 0.0

        self.offset_x = (width - self.disp_w) / 2.0 + self.pan_x
        self.offset_y = (height - self.disp_h) / 2.0 + self.pan_y

        # 3. Soft drop shadow behind the screenshot
        cr.save()
        cr.set_source_rgba(0, 0, 0, 0.35)
        cr.rectangle(self.offset_x + 3, self.offset_y + 3, self.disp_w + 2, self.disp_h + 2)
        cr.fill()
        cr.restore()

        # 4. Render screenshot and annotations
        cr.save()
        cr.translate(self.offset_x, self.offset_y)
        cr.scale(self.scale, self.scale)

        # Base full-resolution image
        cr.set_source_surface(self.cairo_surface, 0, 0)
        cr.paint()

        # Annotations in image coordinates
        self.render_strokes_to_cairo(cr)
        cr.restore()

        # 5. Image boundary border
        cr.save()
        cr.set_source_rgba(1.0, 1.0, 1.0, 0.16)
        cr.set_line_width(1.0)
        cr.rectangle(self.offset_x, self.offset_y, self.disp_w, self.disp_h)
        cr.stroke()
        cr.restore()

        # 6. Crop frame & modern handles if crop is active
        if self.crop_active:
            cx = self.offset_x + self.crop_x * self.scale
            cy = self.offset_y + self.crop_y * self.scale
            cw = self.crop_w * self.scale
            ch = self.crop_h * self.scale

            cr.save()
            # Dim outside the crop box (over the screenshot)
            cr.set_source_rgba(0, 0, 0, 0.55)
            cr.rectangle(self.offset_x, self.offset_y, self.disp_w, self.disp_h)
            cr.rectangle(cx, cy, cw, ch)
            cr.set_fill_rule(cairo.FILL_RULE_EVEN_ODD)
            cr.fill()

            # Rule-of-thirds grid lines
            cr.set_source_rgba(1.0, 1.0, 1.0, 0.22)
            cr.set_line_width(1.0)
            cr.move_to(cx + cw / 3.0, cy)
            cr.line_to(cx + cw / 3.0, cy + ch)
            cr.move_to(cx + 2.0 * cw / 3.0, cy)
            cr.line_to(cx + 2.0 * cw / 3.0, cy + ch)
            cr.move_to(cx, cy + ch / 3.0)
            cr.line_to(cx + cw, cy + ch / 3.0)
            cr.move_to(cx, cy + 2.0 * ch / 3.0)
            cr.line_to(cx + cw, cy + 2.0 * ch / 3.0)
            cr.stroke()

            # Crisp crop border
            cr.set_source_rgba(1.0, 1.0, 1.0, 0.85)
            cr.set_line_width(1.5)
            cr.rectangle(cx, cy, cw, ch)
            cr.stroke()

            # Modern Windows 11 Corner L-brackets
            corner_len = max(10.0, min(22.0, cw / 2.5, ch / 2.5))
            corner_thick = 3.5

            def draw_corner(px, py, dx, dy):
                cr.save()
                # Contrast shadow
                cr.set_source_rgba(0, 0, 0, 0.45)
                cr.set_line_width(corner_thick + 1.5)
                cr.set_line_cap(cairo.LINE_CAP_SQUARE)
                cr.move_to(px + dx * corner_len, py)
                cr.line_to(px, py)
                cr.line_to(px, py + dy * corner_len)
                cr.stroke()
                # Foreground bracket
                cr.set_source_rgba(1.0, 1.0, 1.0, 1.0)
                cr.set_line_width(corner_thick)
                cr.move_to(px + dx * corner_len, py)
                cr.line_to(px, py)
                cr.line_to(px, py + dy * corner_len)
                cr.stroke()
                cr.restore()

            draw_corner(cx, cy, 1, 1)              # Top-Left
            draw_corner(cx + cw, cy, -1, 1)         # Top-Right
            draw_corner(cx, cy + ch, 1, -1)         # Bottom-Left
            draw_corner(cx + cw, cy + ch, -1, -1)   # Bottom-Right

            # Centered edge bars (pill handles)
            bar_len = min(24.0, cw * 0.4)
            bar_thick = 3.5

            def draw_edge_bar(mx, my, is_horizontal):
                cr.save()
                cr.set_line_cap(cairo.LINE_CAP_ROUND)
                # Contrast shadow
                cr.set_source_rgba(0, 0, 0, 0.45)
                cr.set_line_width(bar_thick + 1.5)
                if is_horizontal:
                    cr.move_to(mx - bar_len / 2.0, my)
                    cr.line_to(mx + bar_len / 2.0, my)
                else:
                    cr.move_to(mx, my - bar_len / 2.0)
                    cr.line_to(mx, my + bar_len / 2.0)
                cr.stroke()
                # Foreground bar
                cr.set_source_rgba(1.0, 1.0, 1.0, 1.0)
                cr.set_line_width(bar_thick)
                if is_horizontal:
                    cr.move_to(mx - bar_len / 2.0, my)
                    cr.line_to(mx + bar_len / 2.0, my)
                else:
                    cr.move_to(mx, my - bar_len / 2.0)
                    cr.line_to(mx, my + bar_len / 2.0)
                cr.stroke()
                cr.restore()

            if cw >= 50:
                draw_edge_bar(cx + cw / 2.0, cy, True)          # Top
                draw_edge_bar(cx + cw / 2.0, cy + ch, True)     # Bottom
            if ch >= 50:
                draw_edge_bar(cx, cy + ch / 2.0, False)         # Left
                draw_edge_bar(cx + cw, cy + ch / 2.0, False)    # Right

            # Live dimension indicator pill
            dim_str = f"{int(self.crop_w)} × {int(self.crop_h)} px"
            cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
            cr.set_font_size(11)
            ext = cr.text_extents(dim_str)
            badge_w = ext.width + 16
            badge_h = ext.height + 10
            badge_x = cx + (cw - badge_w) / 2.0
            badge_y = cy + ch + 10
            if badge_y + badge_h > height - 10:
                badge_y = max(10, cy - badge_h - 10)

            r = badge_h / 2.0
            cr.set_source_rgba(0.10, 0.11, 0.14, 0.90)
            cr.new_sub_path()
            cr.arc(badge_x + badge_w - r, badge_y + r, r, -math.pi / 2, math.pi / 2)
            cr.arc(badge_x + r, badge_y + r, r, math.pi / 2, 3 * math.pi / 2)
            cr.close_path()
            cr.fill_preserve()
            cr.set_source_rgba(1.0, 1.0, 1.0, 0.16)
            cr.set_line_width(1.0)
            cr.stroke()

            cr.set_source_rgba(0.95, 0.95, 0.95, 1.0)
            cr.move_to(badge_x + 8 - ext.x_bearing, badge_y + (badge_h - ext.height) / 2.0 - ext.y_bearing)
            cr.show_text(dim_str)

            cr.restore()

    def copy_to_clipboard(self):
        composite = self.render_current_composite()
        if copy_image_to_clipboard(composite):
            self.show_feedback("✓ Copied to Clipboard!")

    def save_screenshot(self):
        composite = self.render_current_composite()
        path = save_screenshot_to_disk(composite)
        self.show_feedback(f"✓ Saved to {os.path.basename(path)}")
        send_notification("Screenshot Saved", f"Saved to {path}")

    def show_feedback(self, text: str):
        self.feedback_label.set_text(text)
        self.feedback_revealer.set_reveal_child(True)
        GLib.timeout_add(2500, lambda: self.feedback_revealer.set_reveal_child(False))


if __name__ == "__main__":
    img_path = sys.argv[1] if len(sys.argv) > 1 else "/tmp/snipping_current.png"
    if not os.path.exists(img_path):
        print(f"File not found: {img_path}")
        sys.exit(1)

    app = Gtk.Application(application_id="com.snipping.editor", flags=gi.repository.Gio.ApplicationFlags.NON_UNIQUE)

    def on_act(a):
        im = Image.open(img_path)
        ed = SnippingEditor(a, im, img_path)
        ed.present()

    app.connect("activate", on_act)
    app.run(None)
