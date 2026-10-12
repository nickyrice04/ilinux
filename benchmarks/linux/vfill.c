// vfill.c - minimal Wayland EGL client for display-path measurements.
// Opens an opaque fullscreen (or WxH) xdg toplevel, clears it to a new colour
// every frame (full-surface damage, like video), presents with FIFO, and paces
// to a target frame rate.  The client itself costs almost nothing, so power
// and CPU measured while it runs belong to the compositor and display chain.
//
//   wayland-scanner client-header $XDG_SHELL xdg-shell-client-protocol.h
//   wayland-scanner private-code  $XDG_SHELL xdg-shell-protocol.c
//   cc -O2 vfill.c xdg-shell-protocol.c -o vfill $(pkg-config --cflags --libs
//      wayland-client wayland-egl egl glesv2)
//   vfill [-f FPS] [-t SECONDS] [-s WIDTHxHEIGHT] [-i] [-o STATSFILE]
//     defaults: 60 fps, 30 s, fullscreen; -f 0 = unpaced; -i = swap interval 0;
//     -o rewrites "vfill_frames=N" once a second (for windowed measurements);
//     SIGTERM/SIGINT end the run normally (the summary line is still printed)
// The buffer is rendered at the output's scale (wl_output.scale), so on a
// scale-2 output a fullscreen surface is drawn at full physical resolution.
//
// Prints one JSON line at exit: frames presented, elapsed time, mean fps.
#define _GNU_SOURCE
#include <EGL/egl.h>
#include <GLES2/gl2.h>
#include <signal.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <wayland-client.h>
#include <wayland-egl.h>
#include "xdg-shell-client-protocol.h"

static struct wl_compositor *compositor;
static struct xdg_wm_base *wm_base;
static int out_scale = 1;
static int cfg_w, cfg_h;
static bool configured;
static volatile sig_atomic_t closed;

static void on_signal(int sig)
{
    (void)sig;
    closed = 1;
}

static void write_stats(const char *path, long frames)
{
    char tmp[4096];
    snprintf(tmp, sizeof(tmp), "%s.tmp", path);
    FILE *f = fopen(tmp, "w");
    if (!f)
        return;
    fprintf(f, "vfill_frames=%ld\n", frames);
    fclose(f);
    rename(tmp, path);
}

static void output_geometry(void *d, struct wl_output *o, int32_t x, int32_t y, int32_t pw,
                            int32_t ph, int32_t sp, const char *make, const char *model,
                            int32_t tr)
{
    (void)d; (void)o; (void)x; (void)y; (void)pw; (void)ph; (void)sp; (void)make;
    (void)model; (void)tr;
}
static void output_mode(void *d, struct wl_output *o, uint32_t f, int32_t w, int32_t h, int32_t r)
{
    (void)d; (void)o; (void)f; (void)w; (void)h; (void)r;
}
static void output_done(void *d, struct wl_output *o)
{
    (void)d; (void)o;
}
static void output_scale(void *d, struct wl_output *o, int32_t factor)
{
    (void)d; (void)o;
    if (factor > out_scale)
        out_scale = factor;
}
static const struct wl_output_listener output_listener = { output_geometry, output_mode,
                                                           output_done, output_scale };

static void registry_global(void *data, struct wl_registry *r, uint32_t name,
                            const char *iface, uint32_t version)
{
    (void)data;
    if (!strcmp(iface, wl_compositor_interface.name))
        compositor = wl_registry_bind(r, name, &wl_compositor_interface, 4);
    else if (!strcmp(iface, xdg_wm_base_interface.name))
        wm_base = wl_registry_bind(r, name, &xdg_wm_base_interface, 1);
    else if (!strcmp(iface, wl_output_interface.name) && version >= 2)
        wl_output_add_listener(wl_registry_bind(r, name, &wl_output_interface, 2),
                               &output_listener, NULL);
}
static void registry_remove(void *data, struct wl_registry *r, uint32_t name)
{
    (void)data; (void)r; (void)name;
}
static const struct wl_registry_listener registry_listener = { registry_global, registry_remove };

static void wm_ping(void *data, struct xdg_wm_base *b, uint32_t serial)
{
    (void)data;
    xdg_wm_base_pong(b, serial);
}
static const struct xdg_wm_base_listener wm_listener = { wm_ping };

static void surface_configure(void *data, struct xdg_surface *s, uint32_t serial)
{
    (void)data;
    xdg_surface_ack_configure(s, serial);
    configured = true;
}
static const struct xdg_surface_listener surface_listener = { surface_configure };

static void toplevel_configure(void *data, struct xdg_toplevel *t, int32_t w, int32_t h,
                               struct wl_array *states)
{
    (void)data; (void)t; (void)states;
    if (w > 0 && h > 0) {
        cfg_w = w;
        cfg_h = h;
    }
}
static void toplevel_close(void *data, struct xdg_toplevel *t)
{
    (void)data; (void)t;
    closed = true;
}
static const struct xdg_toplevel_listener toplevel_listener = { toplevel_configure, toplevel_close };

static double now_s(void)
{
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec + ts.tv_nsec / 1e9;
}

int main(int argc, char **argv)
{
    double fps = 60, secs = 30;
    int win_w = 0, win_h = 0, interval = 1;
    const char *stats = NULL;
    for (int i = 1; i < argc; i++) {
        if (!strcmp(argv[i], "-f") && i + 1 < argc)
            fps = atof(argv[++i]);
        else if (!strcmp(argv[i], "-t") && i + 1 < argc)
            secs = atof(argv[++i]);
        else if (!strcmp(argv[i], "-s") && i + 1 < argc)
            sscanf(argv[++i], "%dx%d", &win_w, &win_h);
        else if (!strcmp(argv[i], "-i"))
            interval = 0;
        else if (!strcmp(argv[i], "-o") && i + 1 < argc)
            stats = argv[++i];
        else {
            fprintf(stderr, "usage: vfill [-f FPS] [-t SECONDS] [-s WIDTHxHEIGHT] [-i] [-o FILE]\n");
            return 2;
        }
    }

    signal(SIGTERM, on_signal);
    signal(SIGINT, on_signal);
    struct wl_display *dpy = wl_display_connect(NULL);
    if (!dpy) {
        fprintf(stderr, "vfill: no Wayland display\n");
        return 1;
    }
    struct wl_registry *reg = wl_display_get_registry(dpy);
    wl_registry_add_listener(reg, &registry_listener, NULL);
    wl_display_roundtrip(dpy);
    wl_display_roundtrip(dpy); /* wl_output events */
    if (!compositor || !wm_base) {
        fprintf(stderr, "vfill: compositor lacks wl_compositor/xdg_wm_base\n");
        return 1;
    }
    xdg_wm_base_add_listener(wm_base, &wm_listener, NULL);

    struct wl_surface *surf = wl_compositor_create_surface(compositor);
    struct xdg_surface *xs = xdg_wm_base_get_xdg_surface(wm_base, surf);
    xdg_surface_add_listener(xs, &surface_listener, NULL);
    struct xdg_toplevel *top = xdg_surface_get_toplevel(xs);
    xdg_toplevel_add_listener(top, &toplevel_listener, NULL);
    xdg_toplevel_set_title(top, "vfill");
    xdg_toplevel_set_app_id(top, "vfill");
    if (!win_w)
        xdg_toplevel_set_fullscreen(top, NULL);
    wl_surface_commit(surf);
    while (!configured && wl_display_dispatch(dpy) != -1)
        ;
    /* configure sizes are logical; the buffer is out_scale times larger */
    int lw = win_w ? win_w : (cfg_w ? cfg_w : 1280);
    int lh = win_h ? win_h : (cfg_h ? cfg_h : 720);
    int w = lw * out_scale, h = lh * out_scale;
    wl_surface_set_buffer_scale(surf, out_scale);

    EGLDisplay edpy = eglGetDisplay((EGLNativeDisplayType)dpy);
    eglInitialize(edpy, NULL, NULL);
    eglBindAPI(EGL_OPENGL_ES_API);
    /* no alpha: an opaque XRGB buffer, eligible for direct scanout */
    const EGLint cfg_attr[] = { EGL_SURFACE_TYPE, EGL_WINDOW_BIT, EGL_RED_SIZE, 8,
                                EGL_GREEN_SIZE, 8, EGL_BLUE_SIZE, 8, EGL_ALPHA_SIZE, 0,
                                EGL_RENDERABLE_TYPE, EGL_OPENGL_ES2_BIT, EGL_NONE };
    EGLConfig cfg;
    EGLint n = 0;
    if (!eglChooseConfig(edpy, cfg_attr, &cfg, 1, &n) || n < 1) {
        fprintf(stderr, "vfill: no EGL config\n");
        return 1;
    }
    const EGLint ctx_attr[] = { EGL_CONTEXT_CLIENT_VERSION, 2, EGL_NONE };
    EGLContext ctx = eglCreateContext(edpy, cfg, EGL_NO_CONTEXT, ctx_attr);
    struct wl_egl_window *ew = wl_egl_window_create(surf, w, h);
    EGLSurface es = eglCreateWindowSurface(edpy, cfg, (EGLNativeWindowType)ew, NULL);
    eglMakeCurrent(edpy, es, es, ctx);
    eglSwapInterval(edpy, interval); /* 1 = FIFO */

    struct wl_region *opaque = wl_compositor_create_region(compositor);
    wl_region_add(opaque, 0, 0, lw, lh);
    wl_surface_set_opaque_region(surf, opaque);
    wl_region_destroy(opaque);

    const double t0 = now_s(), period = fps > 0 ? 1.0 / fps : 0;
    double next = t0, next_stats = t0 + 1;
    long frames = 0;
    while (!closed && now_s() - t0 < secs) {
        if (cfg_w && cfg_h && !win_w && (cfg_w != lw || cfg_h != lh)) {
            lw = cfg_w;
            lh = cfg_h;
            w = lw * out_scale;
            h = lh * out_scale;
            wl_egl_window_resize(ew, w, h, 0, 0);
        }
        const float p = (float)(frames % 240) / 240.0f;
        glViewport(0, 0, w, h);
        glClearColor(p, 1.0f - p, 0.5f, 1.0f);
        glClear(GL_COLOR_BUFFER_BIT);
        eglSwapBuffers(edpy, es); /* also dispatches Wayland events */
        frames++;
        if (stats && now_s() >= next_stats) {
            write_stats(stats, frames);
            next_stats += 1;
        }
        if (period > 0) {
            next += period;
            const double wait = next - now_s();
            if (wait > 0) {
                struct timespec ts = { (time_t)wait, (long)((wait - (time_t)wait) * 1e9) };
                nanosleep(&ts, NULL);
            } else if (wait < -period) {
                next = now_s(); /* fell behind: do not try to catch up */
            }
        }
        wl_display_dispatch_pending(dpy);
    }
    const double el = now_s() - t0;
    printf("{\"bench\":\"vfill\",\"width\":%d,\"height\":%d,\"scale\":%d,\"interval\":%d,"
           "\"target_fps\":%.1f,\"frames\":%ld,\"seconds\":%.2f,\"fps\":%.2f}\n", w, h,
           out_scale, interval, fps, frames, el, frames / el);
    eglMakeCurrent(edpy, EGL_NO_SURFACE, EGL_NO_SURFACE, EGL_NO_CONTEXT);
    eglDestroySurface(edpy, es);
    wl_egl_window_destroy(ew);
    eglDestroyContext(edpy, ctx);
    eglTerminate(edpy);
    xdg_toplevel_destroy(top);
    xdg_surface_destroy(xs);
    wl_surface_destroy(surf);
    wl_display_disconnect(dpy);
    return 0;
}
