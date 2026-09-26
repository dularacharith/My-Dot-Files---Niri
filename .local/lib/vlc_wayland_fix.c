#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdio.h>

typedef void (*resize_fn_t)(void *, int, int, int, int);
static resize_fn_t real_resize = NULL;

void wl_egl_window_resize(void *win, int w, int h, int dx, int dy) {
    if (!real_resize) {
        void *lib = dlopen("libwayland-egl.so.1", RTLD_LAZY);
        if (lib) {
            real_resize = (resize_fn_t)dlsym(lib, "wl_egl_window_resize");
        }
    }
    if (real_resize) {
        // Fix VLC 3.0 Wayland letterboxing bug:
        // On Wayland, VLC calculates place.width / place.height and resizes
        // the Wayland EGL buffer to only the video frame height (e.g. 1536 instead
        // of 1728 for 2:1 on 16:9), while attaching the subsurface at (0, 0).
        // This causes the video to be pinned to the top with a massive black bar at the bottom.
        // In fullscreen (w >= 1920 or h >= 1080), expand the buffer to the full 16:9 monitor
        // so OpenGL centers the video with symmetrical letterboxing.
        if (w >= 1920) {
            int expected_h = (w * 9) / 16;
            if (h < expected_h) {
                h = expected_h;
            }
        }
        if (h >= 1080) {
            int expected_w = (h * 16) / 9;
            if (w < expected_w) {
                w = expected_w;
            }
        }
        // Force dx=0, dy=0 to eliminate the unsigned integer underflow bug
        // where (sys->width - width) / 2 passed negative offsets to Wayland.
        real_resize(win, w, h, 0, 0);
    }
}
