// SPDX-License-Identifier: MIT
// Original Wayland SHM workload. Callback latency is not photon or keyboard latency.
#define _GNU_SOURCE
#include <wayland-client.h>
#include "xdg-shell-client-protocol.h"
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <time.h>
#include <unistd.h>

static struct wl_display *display;
static struct wl_compositor *compositor;
static struct wl_shm *shm;
static struct xdg_wm_base *wm;
static struct wl_surface *surface;
static struct xdg_surface *xs;
static struct wl_callback *callback;
static int width=640, height=480, configured, frame, waiting, finished;
static double submitted, started;
static const int frames=20;
struct buffer { struct wl_buffer *wl; uint32_t *pixels; size_t bytes; int busy; };
static struct buffer buffers[2];

static double now(void) {
    struct timespec t;
    if (clock_gettime(CLOCK_MONOTONIC, &t)) abort();
    return t.tv_sec + t.tv_nsec / 1e9;
}
static void fail(const char *s) { fprintf(stderr,"frameprobe: %s\n",s); exit(3); }
static void draw(void);
static void release(void *data, struct wl_buffer *b) {
    (void)b;
    ((struct buffer *)data)->busy=0;
    if (configured && !waiting && !finished) draw();
}
static const struct wl_buffer_listener bl={.release=release};
static void make_buffer(struct buffer *b) {
    b->bytes=(size_t)width*height*4;
    int fd=memfd_create("ilinux-frameprobe",MFD_CLOEXEC);
    if(fd<0 || ftruncate(fd,(off_t)b->bytes)) fail("memfd");
    b->pixels=mmap(NULL,b->bytes,PROT_READ|PROT_WRITE,MAP_SHARED,fd,0);
    if(b->pixels==MAP_FAILED) fail("mmap");
    struct wl_shm_pool *pool=wl_shm_create_pool(shm,fd,(int)b->bytes);
    b->wl=wl_shm_pool_create_buffer(pool,0,width,height,width*4,WL_SHM_FORMAT_XRGB8888);
    wl_shm_pool_destroy(pool); close(fd);
    wl_buffer_add_listener(b->wl,&bl,b);
    for(int y=0;y<height;y++) for(int x=0;x<width;x++)
        b->pixels[(size_t)y*width+x]=0xff000000u |
            ((uint32_t)(x*255/width)<<16) | ((uint32_t)(y*255/height)<<8) | 0x40;
}
static void done(void *data,struct wl_callback *cb,uint32_t t) {
    (void)data; (void)t;
    double elapsed=now()-submitted;
    wl_callback_destroy(cb); callback=NULL; waiting=0;
    printf("{\"event\":\"frame\",\"index\":%d,\"warmup\":%s,\"damage\":\"%s\",\"callback_ms\":%.6f,\"width\":%d,\"height\":%d}\n",
           frame,frame<4?"true":"false",frame<12?"cell":"full",elapsed*1e3,width,height);
    fflush(stdout);
    if(++frame>=frames) {finished=1;return;}
    draw();
}
static const struct wl_callback_listener cl={.done=done};
static void draw(void) {
    if(waiting || finished) return;
    struct buffer *b=NULL;
    for(int i=0;i<2;i++) if(!buffers[i].busy) {b=&buffers[i];break;}
    if(!b) return;
    if(!b->wl) make_buffer(b);
    for(int y=32;y<48;y++) for(int x=32;x<48;x++)
        b->pixels[(size_t)y*width+x]=(frame&1)?0xffffffff:0xff000000;
    wl_surface_attach(surface,b->wl,0,0);
    // First use of each buffer/full expose must advertise all initialized pixels.
    if(frame<2 || frame>=12) wl_surface_damage_buffer(surface,0,0,width,height);
    else wl_surface_damage_buffer(surface,32,32,16,16);
    callback=wl_surface_frame(surface); wl_callback_add_listener(callback,&cl,NULL);
    b->busy=waiting=1; submitted=now();
    wl_surface_commit(surface); wl_display_flush(display);
}
static void configure(void *data,struct xdg_surface *s,uint32_t serial) {
    (void)data; xdg_surface_ack_configure(s,serial);
    if(!configured) {configured=1; printf("{\"event\":\"configured\",\"elapsed_ms\":%.6f}\n",(now()-started)*1e3);draw();}
}
static const struct xdg_surface_listener sl={.configure=configure};
static void top_config(void *data,struct xdg_toplevel *top,int32_t w,int32_t h,struct wl_array *states) {
    (void)data;(void)top;(void)states;
    if(w==0 || h==0) return;
    if(w<64 || h<64 || w>3840 || h>2400) fail("unexpected surface extent");
    if(configured && (w!=width || h!=height)) fail("resize during measurement");
    width=w;height=h;
}
static void top_close(void *data,struct xdg_toplevel *top) {(void)data;(void)top;fail("closed by user");}
static const struct xdg_toplevel_listener tl={.configure=top_config,.close=top_close};
static void ping(void *data,struct xdg_wm_base *base,uint32_t serial) {(void)data;xdg_wm_base_pong(base,serial);}
static const struct xdg_wm_base_listener wl={.ping=ping};
static void global(void *data,struct wl_registry *registry,uint32_t name,const char *interface,uint32_t version) {
    (void)data;
    if(!strcmp(interface,"wl_compositor") && version>=4) compositor=wl_registry_bind(registry,name,&wl_compositor_interface,4);
    if(!strcmp(interface,"wl_shm")) shm=wl_registry_bind(registry,name,&wl_shm_interface,1);
    if(!strcmp(interface,"xdg_wm_base")) {wm=wl_registry_bind(registry,name,&xdg_wm_base_interface,1);xdg_wm_base_add_listener(wm,&wl,NULL);}
}
static void removed(void *data,struct wl_registry *r,uint32_t name) {(void)data;(void)r;(void)name;}
static const struct wl_registry_listener rl={.global=global,.global_remove=removed};
int main(void) {
    alarm(45); started=now();
    display=wl_display_connect(NULL); if(!display) fail("Wayland connect");
    struct wl_registry *registry=wl_display_get_registry(display);
    wl_registry_add_listener(registry,&rl,NULL);
    if(wl_display_roundtrip(display)<0 || !compositor || !shm || !wm) fail("required protocol missing");
    surface=wl_compositor_create_surface(compositor);
    xs=xdg_wm_base_get_xdg_surface(wm,surface);xdg_surface_add_listener(xs,&sl,NULL);
    struct xdg_toplevel *top=xdg_surface_get_toplevel(xs);
    xdg_toplevel_add_listener(top,&tl,NULL);
    xdg_toplevel_set_title(top,"iLinux attempt30 frame test — no input needed");
    xdg_toplevel_set_app_id(top,"ilinux-frameprobe30");
    xdg_toplevel_set_fullscreen(top,NULL);
    wl_surface_commit(surface);
    while(!finished) if(wl_display_dispatch(display)<0) fail("Wayland disconnected");
    printf("{\"event\":\"done\",\"frames\":%d,\"elapsed_ms\":%.6f}\n",frame,(now()-started)*1e3);
    xdg_toplevel_destroy(top);xdg_surface_destroy(xs);wl_surface_destroy(surface);
    for(int i=0;i<2;i++) if(buffers[i].wl) {wl_buffer_destroy(buffers[i].wl);munmap(buffers[i].pixels,buffers[i].bytes);}
    xdg_wm_base_destroy(wm);wl_shm_destroy(shm);wl_compositor_destroy(compositor);wl_registry_destroy(registry);
    wl_display_flush(display);wl_display_disconnect(display);return 0;
}
