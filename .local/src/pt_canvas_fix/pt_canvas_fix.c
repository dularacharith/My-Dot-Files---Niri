#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>

/*
 * Cisco Packet Tracer In-Canvas Widget Fix for Niri / Wayland Compositors
 *
 * In Cisco Packet Tracer, in-canvas popups like the note text editor (CNoteEdit / editframe)
 * and cluster name editor (editClusterName) were originally created with:
 *     flags = Qt::Window | Qt::FramelessWindowHint (0x801)
 *
 * Under traditional X11 window managers (e.g. Mutter / GNOME), these frameless windows
 * are placed at global coordinates (mapToGlobal) without window decorations.
 *
 * However, under Wayland compositors (like Niri via xwayland-satellite), any window with
 * override_redirect=false is turned into a managed Wayland xdg_toplevel. Because Wayland
 * toplevels cannot be positioned at arbitrary coordinates by clients, Niri receives them
 * as separate windows and either tiles them into huge columns or centers them as floating
 * windows with titles and borders.
 *
 * This shim intercepts the creation of these frameless canvas frames (flags == 0x801)
 * and embeds them directly into the QGraphicsView's viewport as native child widgets
 * (flags = Qt::Widget = 0). When Packet Tracer positions them via setGeometry using global
 * coordinates, this shim translates those coordinates back to local canvas viewport
 * coordinates using QWidget::mapFromGlobal.
 *
 * Result:
 * - In-canvas note edits, labels, and popups appear directly where clicked on the canvas
 * - No extra X11 / Wayland windows are created
 * - No borders, titles, or tiling misbehaviors
 * - Device configuration dialogs (Router, Switch, PC, etc.) remain normal floating windows
 */

struct QPoint {
    int x;
    int y;
};

struct QRect {
    int x1;
    int y1;
    int x2;
    int y2;
};

static void *(*real_QFrame_C1)(void *this, void *parent, int flags) = NULL;
static void *(*real_QFrame_C2)(void *this, void *parent, int flags) = NULL;
static void (*real_setGeometry)(void *this, const struct QRect *rect) = NULL;
static void *(*real_viewport)(void *scrollArea) = NULL;
static uint64_t (*real_mapFromGlobal)(void *widget, const struct QPoint *pt) = NULL;
static void (*real_raise)(void *widget) = NULL;
static void (*real_show)(void *widget) = NULL;

#define MAX_FRAMES 64
static void *g_canvas_frames[MAX_FRAMES];
static void *g_canvas_parents[MAX_FRAMES];
static int g_frame_count = 0;
static int g_debug = -1;

static int is_debug_enabled(void) {
    if (g_debug == -1) {
        const char *env = getenv("PT_DEBUG");
        g_debug = (env && env[0] != '0') ? 1 : 0;
    }
    return g_debug;
}

static void init_symbols(void) {
    if (!real_QFrame_C1) {
        real_QFrame_C1 = dlsym(RTLD_NEXT, "_ZN6QFrameC1EP7QWidget6QFlagsIN2Qt10WindowTypeEE");
        real_QFrame_C2 = dlsym(RTLD_NEXT, "_ZN6QFrameC2EP7QWidget6QFlagsIN2Qt10WindowTypeEE");
        real_setGeometry = dlsym(RTLD_NEXT, "_ZN7QWidget11setGeometryERK5QRect");
        real_viewport = dlsym(RTLD_NEXT, "_ZNK19QAbstractScrollArea8viewportEv");
        real_mapFromGlobal = dlsym(RTLD_NEXT, "_ZNK7QWidget13mapFromGlobalERK6QPoint");
        real_raise = dlsym(RTLD_NEXT, "_ZN7QWidget5raiseEv");
        real_show = dlsym(RTLD_NEXT, "_ZN7QWidget4showEv");
    }
}

static void register_canvas_frame(void *frame, void *parent) {
    for (int i = 0; i < g_frame_count; i++) {
        if (g_canvas_frames[i] == frame) {
            g_canvas_parents[i] = parent;
            return;
        }
    }
    if (g_frame_count < MAX_FRAMES) {
        g_canvas_frames[g_frame_count] = frame;
        g_canvas_parents[g_frame_count] = parent;
        g_frame_count++;
        if (is_debug_enabled()) {
            fprintf(stderr, "[pt_canvas_fix] Registered in-canvas frame %p with parent %p\n", frame, parent);
        }
    }
}

static int is_canvas_frame(void *widget, void **out_parent) {
    for (int i = 0; i < g_frame_count; i++) {
        if (g_canvas_frames[i] == widget) {
            if (out_parent) *out_parent = g_canvas_parents[i];
            return 1;
        }
    }
    return 0;
}

void _ZN6QFrameC1EP7QWidget6QFlagsIN2Qt10WindowTypeEE(void *this, void *parent, int flags) {
    init_symbols();
    // 0x801 is Qt::Window | Qt::FramelessWindowHint
    if (flags == 0x801 && parent != NULL) {
        void *actual_parent = parent;
        if (real_viewport) {
            void *vp = real_viewport(parent);
            if (vp) {
                actual_parent = vp;
            }
        }
        if (is_debug_enabled()) {
            fprintf(stderr, "[pt_canvas_fix] Intercepted QFrame C1: flags 0x%x -> 0, parent %p -> %p\n",
                    flags, parent, actual_parent);
        }
        register_canvas_frame(this, actual_parent);
        real_QFrame_C1(this, actual_parent, 0);
        return;
    }
    real_QFrame_C1(this, parent, flags);
}

void _ZN6QFrameC2EP7QWidget6QFlagsIN2Qt10WindowTypeEE(void *this, void *parent, int flags) {
    init_symbols();
    if (flags == 0x801 && parent != NULL) {
        void *actual_parent = parent;
        if (real_viewport) {
            void *vp = real_viewport(parent);
            if (vp) {
                actual_parent = vp;
            }
        }
        if (is_debug_enabled()) {
            fprintf(stderr, "[pt_canvas_fix] Intercepted QFrame C2: flags 0x%x -> 0, parent %p -> %p\n",
                    flags, parent, actual_parent);
        }
        register_canvas_frame(this, actual_parent);
        real_QFrame_C2(this, actual_parent, 0);
        return;
    }
    real_QFrame_C2(this, parent, flags);
}

void _ZN7QWidget11setGeometryERK5QRect(void *this, const struct QRect *rect) {
    init_symbols();
    void *parent = NULL;
    if (is_canvas_frame(this, &parent) && parent != NULL && real_mapFromGlobal) {
        struct QPoint globalPt;
        globalPt.x = rect->x1;
        globalPt.y = rect->y1;
        uint64_t pt = real_mapFromGlobal(parent, &globalPt);
        int local_x = (int)(pt & 0xffffffff);
        int local_y = (int)(pt >> 32);
        int width = rect->x2 - rect->x1 + 1;
        int height = rect->y2 - rect->y1 + 1;
        struct QRect localRect;
        localRect.x1 = local_x;
        localRect.y1 = local_y;
        localRect.x2 = local_x + width - 1;
        localRect.y2 = local_y + height - 1;
        if (is_debug_enabled()) {
            fprintf(stderr, "[pt_canvas_fix] setGeometry frame %p: global(%d, %d, %d, %d) -> local(%d, %d, %d, %d)\n",
                    this, rect->x1, rect->y1, width, height, local_x, local_y, width, height);
        }
        real_setGeometry(this, &localRect);
        return;
    }
    real_setGeometry(this, rect);
}

void _ZN7QWidget4showEv(void *this) {
    init_symbols();
    real_show(this);
    if (is_canvas_frame(this, NULL) && real_raise) {
        real_raise(this);
    }
}
