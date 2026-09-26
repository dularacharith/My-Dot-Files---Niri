#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdatomic.h>

/* =========================================================================
 * 1. Wayland EGL Letterbox Centering & Integer Underflow Fix
 * ========================================================================= */
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

/* =========================================================================
 * 2. Fullscreen Mouse Motion Forwarding to VLC vout
 * =========================================================================
 * On Wayland, VLC 3.0's Wayland video output module does not implement pointer
 * input handling, so mouse motion over the video window is never reported to
 * the vout "mouse-moved" variable. As a result, the fullscreen controller never
 * appears when moving/shaking the mouse pointer.
 *
 * Here we capture the active vout instance via vout_Request/vout_Close, hook
 * the Wayland wl_pointer motion events, and forward coordinates to the vout's
 * "mouse-moved" variable so VLC natively triggers the fullscreen controller.
 * ========================================================================= */

typedef union {
    int64_t i_int;
    bool b_bool;
    float f_float;
    char *psz_string;
    void *p_address;
    struct { int32_t x; int32_t y; } coords;
} vlc_value_t;

#define VLC_VAR_COORDS 0x00A0

static _Atomic(void *) g_vout = NULL;
static int (*real_var_SetChecked)(void *, const char *, int, vlc_value_t) = NULL;

typedef void *(*vout_req_fn)(void *, const void *);
static vout_req_fn real_vout_req = NULL;

void *vout_Request(void *object, const void *cfg) {
    if (!real_vout_req) real_vout_req = dlsym(RTLD_NEXT, "vout_Request");
    void *v = real_vout_req(object, cfg);
    if (v) {
        atomic_store(&g_vout, v);
    }
    return v;
}

void vout_Close(void *p_vout) {
    static void (*real_close)(void *) = NULL;
    if (!real_close) real_close = dlsym(RTLD_NEXT, "vout_Close");
    void *cur = atomic_load(&g_vout);
    if (p_vout == cur) {
        atomic_store(&g_vout, NULL);
    }
    real_close(p_vout);
}

typedef void (*motion_fn_t)(void *data, void *pointer, uint32_t time, int32_t sx, int32_t sy);

struct pointer_hook {
    void *proxy;
    void *table[16];
    motion_fn_t orig_motion;
    void *orig_data;
};

#define MAX_POINTER_HOOKS 8
static struct pointer_hook g_hooks[MAX_POINTER_HOOKS];
static int g_num_hooks = 0;

static void my_motion(void *data, void *pointer, uint32_t time, int32_t sx, int32_t sy) {
    motion_fn_t orig = NULL;
    for (int i = 0; i < g_num_hooks; i++) {
        if (g_hooks[i].orig_data == data) {
            orig = g_hooks[i].orig_motion;
            break;
        }
    }
    if (orig) {
        orig(data, pointer, time, sx, sy);
    }

    void *cur_vout = atomic_load(&g_vout);
    if (cur_vout && real_var_SetChecked) {
        int32_t x = sx / 256;
        int32_t y = sy / 256;
        vlc_value_t val;
        val.coords.x = x;
        val.coords.y = y;
        real_var_SetChecked(cur_vout, "mouse-moved", VLC_VAR_COORDS, val);
    }
}

int wl_proxy_add_listener(void *proxy, void (**impl)(void), void *data) {
    static int (*real_add)(void *, void (**)(void), void *) = NULL;
    static const char *(*real_get_class)(void *) = NULL;
    if (!real_add) {
        void *lib = dlopen("libwayland-client.so.0", RTLD_LAZY);
        if (lib) {
            real_add = dlsym(lib, "wl_proxy_add_listener");
            real_get_class = dlsym(lib, "wl_proxy_get_class");
        }
    }
    if (!real_var_SetChecked) {
        real_var_SetChecked = dlsym(RTLD_DEFAULT, "var_SetChecked");
    }

    if (proxy && impl && real_get_class) {
        const char *cls = real_get_class(proxy);
        if (cls && strcmp(cls, "wl_pointer") == 0 && g_num_hooks < MAX_POINTER_HOOKS) {
            int idx = g_num_hooks++;
            g_hooks[idx].proxy = proxy;
            g_hooks[idx].orig_motion = (motion_fn_t)impl[2];
            g_hooks[idx].orig_data = data;
            memcpy(g_hooks[idx].table, impl, sizeof(void *) * 9);
            g_hooks[idx].table[2] = (void *)my_motion;
            return real_add(proxy, (void (**)(void))g_hooks[idx].table, data);
        }
    }
    return real_add(proxy, impl, data);
}
