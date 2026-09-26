#!/usr/bin/env python3
import sys
import os
import subprocess
import json
import time

if len(sys.argv) < 2:
    sys.exit(0)

try:
    vlc_pid = int(sys.argv[1])
except ValueError:
    sys.exit(0)

proc = subprocess.Popen(['niri', 'msg', '-j', 'event-stream'], stdout=subprocess.PIPE, bufsize=1, text=True)

moved_windows = {}

while True:
    try:
        os.kill(vlc_pid, 0)
    except OSError:
        break

    line = proc.stdout.readline()
    if not line:
        break

    try:
        data = json.loads(line)
        win = None
        if 'WindowOpenedOrChanged' in data:
            win = data['WindowOpenedOrChanged']['window']
        elif 'WindowsChanged' in data:
            for w in data['WindowsChanged']['windows']:
                if w.get('app_id') == 'vlc' and w.get('title') == 'vlc':
                    win = w
                    break

        if win and win.get('app_id') == 'vlc' and win.get('title') == 'vlc':
            wid = win.get('id')
            layout = win.get('layout', {})
            pos = layout.get('tile_pos_in_workspace_view')
            size = layout.get('tile_size')

            if pos and size:
                # Target: 20px above the bottom of the screen (height 864)
                target_y = 864.0 - size[1] - 20.0
                curr_y = pos[1]
                
                # If window is near the vertical center (y < 650)
                if curr_y < 650:
                    delta = int(target_y - curr_y)
                    if delta > 0:
                        subprocess.run(['niri', 'msg', 'action', 'move-floating-window', '--id', str(wid), '-y', f'+{delta}'])
                        moved_windows[wid] = time.time()
    except Exception:
        pass

proc.terminate()
