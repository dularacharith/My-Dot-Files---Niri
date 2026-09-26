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
    (void)dx;
    (void)dy;
    if (!real_resize) {
        void *lib = dlopen("libwayland-egl.so.1", RTLD_LAZY);
        if (lib) {
            real_resize = (resize_fn_t)dlsym(lib, "wl_egl_window_resize");
        }
    }
    if (real_resize) {
        // Fix VLC 3.0 Wayland letterboxing bug:
        // In fullscreen (w >= 1920 or h >= 1080), calculate symmetrical centering
        // offsets so non-16:9 videos (e.g. 2:1 Silo at 1920x960) are centered
        // vertically and horizontally rather than sticking to the top edge and
        // leaving an asymmetrical blank space at the bottom.
        int out_dx = 0;
        int out_dy = 0;
        if (w >= 1920 || h >= 1080) {
            int target_w = (w > 1920) ? w : 1920;
            int target_h = (h > 1080) ? h : 1080;
            out_dx = (target_w - w) / 2;
            out_dy = (target_h - h) / 2;
        }
        if (out_dx < 0) out_dx = 0;
        if (out_dy < 0) out_dy = 0;

        real_resize(win, w, h, out_dx, out_dy);
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
    if (!real_var_SetChecked) real_var_SetChecked = dlsym(RTLD_DEFAULT, "var_SetChecked");
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

        // Throttle updates so we don't flood VLC with 1000 events/sec
        static int32_t last_x = -1, last_y = -1;
        static uint32_t last_time = 0;
        if (abs(x - last_x) >= 8 || abs(y - last_y) >= 8 || (time - last_time) >= 150) {
            last_x = x;
            last_y = y;
            last_time = time;

            vlc_value_t val;
            val.coords.x = x;
            val.coords.y = y;
            real_var_SetChecked(cur_vout, "mouse-moved", VLC_VAR_COORDS, val);
        }
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

/* =========================================================================
 * 3. Prevent FullscreenControllerWidget from Hiding on Wayland ActivationChange
 * =========================================================================
 * In VLC's Qt interface, FullscreenControllerWidget installs an event filter on
 * the parent window (MainInterface). On Wayland with Niri, when the floating
 * controller widget appears with `open-focused false`, Qt sends an
 * ActivationChange event to the parent window. Because VLC thinks the window
 * is not active on Wayland, it immediately calls hideFSC(), causing the
 * controller to disappear the very instant it appears.
 *
 * By intercepting QObject::installEventFilter and skipping it when the filter
 * object is FullscreenControllerWidget, the bogus ActivationChange events
 * are never delivered to FullscreenControllerWidget. The controller will then
 * stably remain visible while mouse moves and for the full 1.5s timeout!
 * ========================================================================= */
void _ZN7QObject18installEventFilterEPS_(void *watched, void *filterObj) {
    static void (*real_install)(void *, void *) = NULL;
    if (!real_install) {
        void *lib = dlopen("libQt5Core.so.5", RTLD_LAZY | RTLD_NOLOAD);
        if (!lib) lib = dlopen("libQt5Core.so.5", RTLD_LAZY);
        if (lib) real_install = dlsym(lib, "_ZN7QObject18installEventFilterEPS_");
    }

    if (filterObj) {
        void *vtable = *(void **)filterObj;
        if (vtable) {
            void *tinfo = ((void **)vtable)[-1];
            if (tinfo) {
                const char *mangled = ((const char **)tinfo)[1];
                if (mangled && strstr(mangled, "FullscreenControllerWidget")) {
                    return; // Prevent FSC from installing event filter on parent window
                }
            }
        }
    }

    if (real_install) {
        real_install(watched, filterObj);
    }
}
