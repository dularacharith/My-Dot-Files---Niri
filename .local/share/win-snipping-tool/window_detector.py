#!/usr/bin/env python3
"""
Window Detector for Niri compositor.
Queries niri IPC to detect open windows and compute their screen bounding boxes
in logical coordinates and physical pixel coordinates.
"""

import json
import subprocess
from typing import List, Dict, Any, Optional, Tuple

class WindowInfo:
    def __init__(self, win_id: int, app_id: str, title: str, rect_logical: Tuple[int, int, int, int], scale: float):
        self.win_id = win_id
        self.app_id = app_id
        self.title = title
        self.rect_logical = rect_logical  # (x, y, w, h) in logical points
        self.scale = scale

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
    """
    try:
        ws_raw = subprocess.check_output(["niri", "msg", "--json", "workspaces"], text=True)
        workspaces = json.loads(ws_raw)
        active_ws = next((w for w in workspaces if w.get("is_active") and w.get("is_focused")), workspaces[0])
        active_ws_id = active_ws["id"]
        active_output_name = active_ws.get("output")

        out_raw = subprocess.check_output(["niri", "msg", "--json", "outputs"], text=True)
        outputs = json.loads(out_raw)
        out_info = outputs.get(active_output_name, list(outputs.values())[0])
        logical = out_info.get("logical", {})
        scale = float(logical.get("scale", 1.0))
        screen_w = int(logical.get("width", 1920))
        screen_h = int(logical.get("height", 1080))

        win_raw = subprocess.check_output(["niri", "msg", "--json", "windows"], text=True)
        windows = json.loads(win_raw)
        ws_windows = [w for w in windows if w.get("workspace_id") == active_ws_id]

        gaps = 4
        bar_height = 40

        # Sort windows: floating windows on top, tiled by column
        floating_wins = [w for w in ws_windows if w.get("is_floating")]
        tiled_wins = [w for w in ws_windows if not w.get("is_floating")]

        results: List[WindowInfo] = []

        # Floating windows
        for w in floating_wins:
            layout = w.get("layout", {})
            w_size = layout.get("window_size", [800, 600])
            t_pos = layout.get("tile_pos_in_workspace_view")
            if t_pos:
                rx = int(t_pos[0])
                ry = int(t_pos[1])
                rw = int(w_size[0])
                rh = int(w_size[1])
                title = w.get("title") or w.get("app_id") or "Window"
                results.append(WindowInfo(w.get("id", 0), w.get("app_id", ""), title, (rx, ry, rw, rh), scale))

        # Tiled windows: group by column if multiple
        if len(tiled_wins) == 1:
            w = tiled_wins[0]
            layout = w.get("layout", {})
            w_size = layout.get("window_size", [screen_w - 2 * gaps, screen_h - bar_height - gaps])
            cw = int(w_size[0])
            ch = int(w_size[1])
            cx = int((screen_w - cw) / 2)
            cy = int(screen_h - ch - gaps)
            title = w.get("title") or w.get("app_id") or "Window"
            results.append(WindowInfo(w.get("id", 0), w.get("app_id", ""), title, (cx, cy, cw, ch), scale))
        elif len(tiled_wins) > 1:
            # Sort by pos_in_scrolling_layout
            tiled_wins.sort(key=lambda x: x.get("layout", {}).get("pos_in_scrolling_layout", [0, 0])[0])
            total_width = sum(w.get("layout", {}).get("window_size", [0, 0])[0] for w in tiled_wins) + gaps * (len(tiled_wins) - 1)
            start_x = max(gaps, int((screen_w - total_width) / 2))
            curr_x = start_x

            for w in tiled_wins:
                layout = w.get("layout", {})
                w_size = layout.get("window_size", [400, screen_h - bar_height - gaps])
                cw = int(w_size[0])
                ch = int(w_size[1])
                cy = int(screen_h - ch - gaps)
                title = w.get("title") or w.get("app_id") or "Window"
                results.append(WindowInfo(w.get("id", 0), w.get("app_id", ""), title, (curr_x, cy, cw, ch), scale))
                curr_x += cw + gaps

        return results, scale, screen_w, screen_h

    except Exception as e:
        print(f"[WindowDetector] Error fetching Niri windows: {e}")
        return [], 1.0, 1920, 1080

def find_window_at(windows: List[WindowInfo], x: float, y: float) -> Optional[WindowInfo]:
    """Returns the top-most window containing point (x, y)."""
    for win in windows:
        if win.contains(x, y):
            return win
    return None
