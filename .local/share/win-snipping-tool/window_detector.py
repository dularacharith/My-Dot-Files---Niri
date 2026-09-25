#!/usr/bin/env python3
"""
Window Detector for Niri compositor.
Queries niri IPC to detect open windows and compute their exact on-screen bounding boxes
in logical coordinates and physical pixel coordinates, handling scrolling layouts,
floating windows, and layer surfaces.
"""

import json
import subprocess
from typing import List, Dict, Any, Optional, Tuple

class WindowInfo:
    def __init__(self, win_id: int, app_id: str, title: str, rect_logical: Tuple[int, int, int, int], scale: float, is_floating: bool = False):
        self.win_id = win_id
        self.app_id = app_id
        self.title = title
        self.rect_logical = rect_logical  # (x, y, w, h) in logical points
        self.scale = scale
        self.is_floating = is_floating

    @property
    def rect_physical(self) -> Tuple[int, int, int, int]:
        x, y, w, h = self.rect_logical
        return (
            int(round(x * self.scale)),
            int(round(y * self.scale)),
            int(round(w * self.scale)),
            int(round(h * self.scale))
        )

    def contains(self, x: float, y: float) -> bool:
        wx, wy, ww, wh = self.rect_logical
        return wx <= x <= wx + ww and wy <= y <= wy + wh

def get_niri_windows() -> Tuple[List[WindowInfo], float, int, int]:
    """
    Returns (list_of_windows, scale, screen_logical_w, screen_logical_h).
    Accurately computes visible positions for tiled columns and floating windows.
    """
    try:
        # 1. Query focused output for exact screen geometry and scale
        out_raw = subprocess.check_output(["niri", "msg", "--json", "focused-output"], text=True)
        out_info = json.loads(out_raw)
        logical = out_info.get("logical", {})
        scale = float(logical.get("scale", 1.0))
        screen_w = int(logical.get("width", 1920))
        screen_h = int(logical.get("height", 1080))
        output_name = out_info.get("name")

        # 2. Get focused window to determine active workspace and focused column
        focused_win = None
        active_ws_id = None
        try:
            f_raw = subprocess.check_output(["niri", "msg", "--json", "focused-window"], text=True)
            if f_raw.strip():
                focused_win = json.loads(f_raw)
                active_ws_id = focused_win.get("workspace_id")
        except Exception:
            pass

        if not active_ws_id:
            ws_raw = subprocess.check_output(["niri", "msg", "--json", "workspaces"], text=True)
            workspaces = json.loads(ws_raw)
            active_ws = next((w for w in workspaces if w.get("is_active") and (w.get("output") == output_name or not output_name)), workspaces[0])
            active_ws_id = active_ws["id"]

        # 3. Query all open windows and filter to the active workspace
        win_raw = subprocess.check_output(["niri", "msg", "--json", "windows"], text=True)
        windows = json.loads(win_raw)
        ws_windows = [w for w in windows if w.get("workspace_id") == active_ws_id]

        gap = 4
        results: List[WindowInfo] = []

        # 4. Floating windows (topmost priority)
        floating_wins = [w for w in ws_windows if w.get("is_floating")]
        for w in floating_wins:
            layout = w.get("layout", {})
            w_size = layout.get("window_size", [800, 600])
            t_pos = layout.get("tile_pos_in_workspace_view")
            rw = int(w_size[0])
            rh = int(w_size[1])
            if t_pos:
                rx, ry = int(t_pos[0]), int(t_pos[1])
            else:
                rx = int((screen_w - rw) / 2)
                ry = int((screen_h - rh) / 2)
            title = w.get("title") or w.get("app_id") or "Window"
            results.append(WindowInfo(w.get("id", 0), w.get("app_id", ""), title, (rx, ry, rw, rh), scale, is_floating=True))

        # 5. Tiled windows with Niri scrolling layout geometry
        tiled_wins = [w for w in ws_windows if not w.get("is_floating")]
        if tiled_wins:
            # Group windows by column index
            columns: Dict[int, List[Dict[str, Any]]] = {}
            for w in tiled_wins:
                col_idx = w.get("layout", {}).get("pos_in_scrolling_layout", [1, 1])[0]
                columns.setdefault(col_idx, []).append(w)
            
            for col_idx in columns:
                columns[col_idx].sort(key=lambda w: w.get("layout", {}).get("pos_in_scrolling_layout", [1, 1])[1])

            col_indices = sorted(columns.keys())
            col_widths = {
                c: columns[c][0].get("layout", {}).get("window_size", [screen_w - 2 * gap, screen_h - 2 * gap])[0]
                for c in col_indices
            }

            # Calculate horizontal positions along the ribbon (starts at left gap)
            col_ribbon_x = {}
            curr_x = gap
            for c in col_indices:
                col_ribbon_x[c] = curr_x
                curr_x += col_widths[c] + gap
            total_ribbon_w = curr_x

            # Determine scroll offset S based on focused column
            focused_col = col_indices[0]
            if focused_win and not focused_win.get("is_floating"):
                fc = focused_win.get("layout", {}).get("pos_in_scrolling_layout", [1, 1])[0]
                if fc in col_indices:
                    focused_col = fc

            if total_ribbon_w <= screen_w:
                scroll_s = 0
            else:
                f_x = col_ribbon_x.get(focused_col, gap)
                f_w = col_widths.get(focused_col, screen_w - 2 * gap)
                if f_w >= screen_w - 2 * gap:
                    scroll_s = f_x - gap
                elif focused_col == col_indices[-1]:
                    scroll_s = f_x + f_w - (screen_w - gap)
                elif focused_col == col_indices[0]:
                    scroll_s = f_x - gap
                else:
                    scroll_s = f_x + f_w - (screen_w - gap)

            # Map columns to on-screen viewports
            for c in col_indices:
                screen_col_x = col_ribbon_x[c] - scroll_s
                cw = col_widths[c]
                vis_x1 = max(gap, screen_col_x)
                vis_x2 = min(screen_w - gap, screen_col_x + cw)

                if vis_x2 > vis_x1 + 10:  # Column is visible with meaningful width
                    col_wins = columns[c]
                    curr_y = gap
                    for w in col_wins:
                        wh = w.get("layout", {}).get("window_size", [cw, screen_h - 2 * gap])[1]
                        title = w.get("title") or w.get("app_id") or "Window"
                        rx = int(round(vis_x1))
                        ry = int(round(curr_y))
                        rw = int(round(vis_x2 - vis_x1))
                        rh = int(round(wh))
                        results.append(WindowInfo(w.get("id", 0), w.get("app_id", ""), title, (rx, ry, rw, rh), scale, is_floating=False))
                        curr_y += wh + gap

        # 6. Add Top Bar layer surface if detected
        try:
            layers_raw = subprocess.check_output(["niri", "msg", "--json", "layers"], text=True)
            layers = json.loads(layers_raw)
            has_bar = any("bar" in l.get("namespace", "").lower() for l in layers)
            if has_bar:
                bar_h = 36
                results.append(WindowInfo(99999, "dms:bar", "Top Status Bar", (0, 0, screen_w, bar_h), scale, is_floating=False))
        except Exception:
            pass

        return results, scale, screen_w, screen_h

    except Exception as e:
        print(f"[WindowDetector] Error fetching Niri windows: {e}")
        return [], 1.0, 1920, 1080

def find_window_at(windows: List[WindowInfo], x: float, y: float) -> Optional[WindowInfo]:
    """Returns the top-most window containing point (x, y)."""
    # 1. Floating windows first (highest Z-order over tiled windows)
    for win in windows:
        if win.app_id != "dms:bar" and win.is_floating and win.contains(x, y):
            return win

    # 2. Regular tiled application windows
    for win in windows:
        if win.app_id != "dms:bar" and not win.is_floating and win.contains(x, y):
            return win

    # 3. Layer surfaces (e.g. status bar) only if no window contains point
    for win in windows:
        if win.app_id == "dms:bar" and win.contains(x, y):
            return win

    return None

