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

    def _make_tool_btn(self, icon_name: str, label_text: str, tooltip: str, on_click) -> Gtk.Button:
        btn = Gtk.Button()
        btn.add_css_class("tool-button")
        btn.set_tooltip_text(tooltip)
        btn.set_valign(Gtk.Align.CENTER)
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        box.set_valign(Gtk.Align.CENTER)
        box.set_halign(Gtk.Align.CENTER)
        if icon_name:
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

    def setup_ui(self):
        # Header / Toolbar
        header = Gtk.HeaderBar()
        self.set_titlebar(header)

        # Left: Tools
        left_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        header.pack_start(left_box)

        # Pen Button
        self.btn_pen = self._make_tool_btn(
            "document-edit-symbolic", "Pen", "Draw with pen", lambda _: self.set_tool("pen")
        )
        self.btn_pen.add_css_class("active")
        left_box.append(self.btn_pen)

        # Highlighter Button
        self.btn_highlighter = self._make_tool_btn(
            "view-paged-symbolic", "Highlighter", "Highlight content", lambda _: self.set_tool("highlighter")
        )
        left_box.append(self.btn_highlighter)

        # Eraser Button
        self.btn_eraser = self._make_tool_btn(
            "edit-clear-symbolic", "Eraser", "Erase annotations", lambda _: self.set_tool("eraser")
        )
        left_box.append(self.btn_eraser)

        # Separator
        left_box.append(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL))

        # Crop Tool Button
        self.btn_crop = self._make_tool_btn(
            "object-select-symbolic", "Crop", "Crop image", lambda _: self.toggle_crop_mode()
        )
        left_box.append(self.btn_crop)

        # Crop action buttons (hidden by default)
        self.crop_actions_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        self.crop_actions_box.set_visible(False)

        btn_apply_crop = Gtk.Button(label="✓ Apply")
        btn_apply_crop.add_css_class("action-btn-primary")
        btn_apply_crop.connect("clicked", lambda _: self.apply_crop())
        self.crop_actions_box.append(btn_apply_crop)

        btn_cancel_crop = Gtk.Button(label="✕ Cancel")
        btn_cancel_crop.add_css_class("action-btn-secondary")
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

        # Zoom Out Button
        btn_zoom_out = Gtk.Button()
        btn_zoom_out.add_css_class("zoom-btn")
        btn_zoom_out.set_tooltip_text("Zoom Out (Ctrl - or Scroll Down)")
        icon_out = Gtk.Image.new_from_icon_name("zoom-out-symbolic")
        icon_out.set_pixel_size(15)
        btn_zoom_out.set_child(icon_out)
        btn_zoom_out.connect("clicked", lambda _: self.zoom_step(zoom_in=False))
        center_box.append(btn_zoom_out)

        # Zoom Percentage / Fit Badge Button
        self.btn_zoom_badge = Gtk.Button(label="Fit")
        self.btn_zoom_badge.add_css_class("zoom-badge")
        self.btn_zoom_badge.set_tooltip_text("Click to Fit to Window (Ctrl+0)")
        self.btn_zoom_badge.connect("clicked", lambda _: self.zoom_to(1.0))
        center_box.append(self.btn_zoom_badge)

        # Zoom In Button
        btn_zoom_in = Gtk.Button()
        btn_zoom_in.add_css_class("zoom-btn")
        btn_zoom_in.set_tooltip_text("Zoom In (Ctrl + or Scroll Up)")
        icon_in = Gtk.Image.new_from_icon_name("zoom-in-symbolic")
        icon_in.set_pixel_size(15)
        btn_zoom_in.set_child(icon_in)
        btn_zoom_in.connect("clicked", lambda _: self.zoom_step(zoom_in=True))
        center_box.append(btn_zoom_in)

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

            # Initialize crop box with 6% margins in image coordinates
            w, h = self.current_image.size
            self.crop_x = int(w * 0.06)
            self.crop_y = int(h * 0.06)
            self.crop_w = int(w * 0.88)
            self.crop_h = int(h * 0.88)
        else:
            self.cancel_crop()
        self.update_cursor()
        self.canvas.queue_draw()

    def cancel_crop(self):
        self.crop_active = False
        self.btn_crop.remove_css_class("active")
        self.crop_actions_box.set_visible(False)
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
            self.crop_drag_start = (start_x, start_y)
            self.crop_rect_start = (self.crop_x, self.crop_y, self.crop_w, self.crop_h)
            self.crop_drag_mode = self.get_crop_handle_at(start_x, start_y)
            return

        # Check if click is on the scaled image
        if not (self.offset_x <= start_x <= self.offset_x + self.disp_w and
                self.offset_y <= start_y <= self.offset_y + self.disp_h):
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

        start_x, start_y = gesture.get_start_point()
        curr_x = start_x + offset_x
        curr_y = start_y + offset_y

        if self.crop_active and self.crop_drag_mode:
            dx = offset_x / max(0.001, self.scale)
            dy = offset_y / max(0.001, self.scale)
            ox, oy, ow, oh = self.crop_rect_start

            if self.crop_drag_mode == "inside":
                self.crop_x = int(ox + dx)
                self.crop_y = int(oy + dy)
            elif self.crop_drag_mode == "tl":
                self.crop_x = int(min(ox + dx, ox + ow - 10))
                self.crop_y = int(min(oy + dy, oy + oh - 10))
                self.crop_w = int(ox + ow - self.crop_x)
                self.crop_h = int(oy + oh - self.crop_y)
            elif self.crop_drag_mode == "br":
                self.crop_w = int(max(10, ow + dx))
                self.crop_h = int(max(10, oh + dy))
            elif self.crop_drag_mode == "tr":
                self.crop_y = int(min(oy + dy, oy + oh - 10))
                self.crop_w = int(max(10, ow + dx))
                self.crop_h = int(oy + oh - self.crop_y)
            elif self.crop_drag_mode == "bl":
                self.crop_x = int(min(ox + dx, ox + ow - 10))
                self.crop_w = int(ox + ow - self.crop_x)
                self.crop_h = int(max(10, oh + dy))
            elif self.crop_drag_mode == "t":
                self.crop_y = int(min(oy + dy, oy + oh - 10))
                self.crop_h = int(oy + oh - self.crop_y)
            elif self.crop_drag_mode == "b":
                self.crop_h = int(max(10, oh + dy))
            elif self.crop_drag_mode == "l":
                self.crop_x = int(min(ox + dx, ox + ow - 10))
                self.crop_w = int(ox + ow - self.crop_x)
            elif self.crop_drag_mode == "r":
                self.crop_w = int(max(10, ow + dx))

            # Clamp bounds
            self.crop_x = max(0, min(self.crop_x, self.current_image.width - self.crop_w))
            self.crop_y = max(0, min(self.crop_y, self.current_image.height - self.crop_h))
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
            self.crop_drag_mode = None
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
            handle = self.get_crop_handle_at(self.mouse_pos[0], self.mouse_pos[1])
            cursor_name = "default"
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
        cx = self.offset_x + self.crop_x * self.scale
        cy = self.offset_y + self.crop_y * self.scale
        cw = self.crop_w * self.scale
        ch = self.crop_h * self.scale
        h_hit = 15.0

        if abs(x - cx) <= h_hit and abs(y - cy) <= h_hit:
            return "tl"
        if abs(x - (cx + cw)) <= h_hit and abs(y - cy) <= h_hit:
            return "tr"
        if abs(x - cx) <= h_hit and abs(y - (cy + ch)) <= h_hit:
            return "bl"
        if abs(x - (cx + cw)) <= h_hit and abs(y - (cy + ch)) <= h_hit:
            return "br"
        if abs(x - (cx + cw / 2)) <= h_hit and abs(y - cy) <= h_hit:
            return "t"
        if abs(x - (cx + cw / 2)) <= h_hit and abs(y - (cy + ch)) <= h_hit:
            return "b"
        if abs(x - cx) <= h_hit and abs(y - (cy + ch / 2)) <= h_hit:
            return "l"
        if abs(x - (cx + cw)) <= h_hit and abs(y - (cy + ch / 2)) <= h_hit:
            return "r"
        if cx <= x <= cx + cw and cy <= y <= cy + ch:
            return "inside"
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

        # 6. Crop frame & handles if crop is active
        if self.crop_active:
            cx = self.offset_x + self.crop_x * self.scale
            cy = self.offset_y + self.crop_y * self.scale
            cw = self.crop_w * self.scale
            ch = self.crop_h * self.scale

            cr.save()
            # Dim outside the crop box (over the image)
            cr.set_source_rgba(0, 0, 0, 0.55)
            cr.rectangle(self.offset_x, self.offset_y, self.disp_w, self.disp_h)
            cr.rectangle(cx, cy, cw, ch)
            cr.set_fill_rule(cairo.FILL_RULE_EVEN_ODD)
            cr.fill()

            # Crop border
            cr.set_source_rgba(1.0, 1.0, 1.0, 0.95)
            cr.set_line_width(2.0)
            cr.rectangle(cx, cy, cw, ch)
            cr.stroke()

            # Handles
            h_sz = 10
            handles = [
                (cx, cy),
                (cx + cw, cy),
                (cx, cy + ch),
                (cx + cw, cy + ch),
                (cx + cw / 2, cy),
                (cx + cw / 2, cy + ch),
                (cx, cy + ch / 2),
                (cx + cw, cy + ch / 2)
            ]
            for hx, hy in handles:
                cr.rectangle(hx - h_sz / 2, hy - h_sz / 2, h_sz, h_sz)
                cr.set_source_rgba(0.2, 0.6, 1.0, 1.0)
                cr.fill_preserve()
                cr.set_source_rgba(1.0, 1.0, 1.0, 1.0)
                cr.set_line_width(1.5)
                cr.stroke()

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
