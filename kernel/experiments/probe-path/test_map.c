/* Actual DT parser, preparation, mapping and renderer with controlled I/O. */
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <stdarg.h>
#include <errno.h>
#include <libfdt.h>
typedef uint8_t u8;
typedef uint32_t u32;
typedef uint64_t u64;
#define __init
#define U32_MAX UINT32_MAX
#define U64_MAX UINT64_MAX
#define READ_ONCE(x) (x)
#define WRITE_ONCE(x,v) ((x)=(v))
#define DIV_ROUND_UP(a,b) (((a)+(b)-1)/(b))
#define MEMREMAP_WC 4
struct font_desc { unsigned int width, height; const unsigned char *data; };
struct console { bool registered; };
static u64 fb_base, fb_size;
static u32 fb_width, fb_height, fb_stride, cx, cy;
static const struct font_desc *fb_font;
static struct console *fb_console;
static void *fb_mapping;
static bool mapping_failed;
bool ilinux_probe_diag;
static unsigned char dt[16384], font_data[256*16];
static void *initial_boot_params = dt;
static struct font_desc font = { 8,16,font_data };
static struct console con;
static u32 pixels[640*400];
static unsigned int maps, console_queries, logs;
static bool map_ok, font_ok;
static bool console_is_registered(struct console *c) { console_queries++; return c->registered; }
static const struct font_desc *get_default_font(u32 w,u32 h,void *a,void *b) { (void)w;(void)h;(void)a;(void)b;return font_ok ? &font : NULL; }
static void *memremap(u64 base,u64 size,int flags) { assert(base==0x100000000ULL && size==sizeof(pixels) && flags==MEMREMAP_WC); maps++;return map_ok ? pixels : NULL; }
static void pr_info(const char *fmt,...) __attribute__((format(printf,1,2)));
static void pr_info(const char *fmt,...) { (void)fmt;logs++; }
#include "status-panel.h"
#include "tested-parser.h"
#ifdef TEST_BASELINE
#include "baseline-map.h"
#else
#include "fb-map.h"
#endif

static int fixture(void)
{
    int c,n;
    assert(!fdt_create_empty_tree(dt,sizeof(dt)));
    assert(!fdt_setprop_string(dt,0,"compatible","apple,j716c"));
    c=fdt_add_subnode(dt,0,"chosen");assert(c>=0);
    assert(!fdt_setprop_u32(dt,c,"#address-cells",2));
    assert(!fdt_setprop_u32(dt,c,"#size-cells",2));
    assert(!fdt_setprop(dt,c,"ranges",NULL,0));
    n=fdt_add_subnode(dt,c,"framebuffer");assert(n>=0);
    assert(!fdt_setprop_string(dt,n,"compatible","simple-framebuffer"));
    assert(!fdt_setprop_string(dt,n,"format","x8r8g8b8"));
    assert(!fdt_setprop_string(dt,n,"status","okay"));
    fdt64_t reg[2]={cpu_to_fdt64(0x100000000ULL),cpu_to_fdt64(sizeof(pixels))};
    assert(!fdt_setprop(dt,n,"reg",reg,sizeof(reg)));
    assert(!fdt_setprop_u32(dt,n,"width",640));
    assert(!fdt_setprop_u32(dt,n,"height",400));
    assert(!fdt_setprop_u32(dt,n,"stride",640*4));
    fb_mapping=NULL;fb_console=NULL;fb_font=NULL;fb_diag_state=0;mapping_failed=false;
    maps=console_queries=logs=0;ilinux_probe_diag=true;map_ok=font_ok=true;
    con.registered=false; font.width=8;font.height=16;
    return n;
}
int main(void)
{
#ifdef TEST_BASELINE
    (void)initial_boot_params;
    fixture(); fb_console=&con;
    assert(!fb_remap() && !maps && !fb_mapping);
    puts("REPRODUCED: boot028 skips the diagnostic mapping when the boot console has retired");
#else
    int n;
    fixture();ilinux_probe_diag=false;assert(!fb_remap() && !maps && !logs);
    fixture();assert(!fb_remap() && fb_diag_state==6 && maps==1 && !console_queries && fb_mapping==pixels && fb_text_height==144);
    fixture();fb_console=&con;assert(!fb_remap() && fb_diag_state==6 && !console_queries); /* retired console */
    fixture();fb_console=&con;con.registered=true;assert(!fb_remap() && !console_queries); /* active console */
    fixture();fb_console=&con;ilinux_probe_diag=false;assert(!fb_remap() && !maps && console_queries==1);
    fixture();fb_console=&con;con.registered=true;ilinux_probe_diag=false;assert(!fb_remap() && maps==1 && console_queries==1);
    fixture();assert(!fdt_setprop_string(dt,0,"compatible","test,generic"));assert(!fb_remap() && fb_diag_state==1 && !maps);
    fixture();initial_boot_params=NULL;assert(!fb_remap() && fb_diag_state==1 && !maps);initial_boot_params=dt;
    n=fixture();assert(!fdt_setprop_u32(dt,n,"stride",1));assert(fb_remap()==-EINVAL && fb_diag_state==2 && !maps);
    n=fixture();assert(!fdt_setprop_string(dt,n,"format","unsupported"));assert(fb_remap()==-EINVAL && fb_diag_state==2 && !maps);
    n=fixture();assert(!fdt_setprop_string(dt,n,"status","disabled"));assert(!fb_remap() && fb_diag_state==1 && !maps);
    fixture();font_ok=false;assert(fb_remap()==-EINVAL && fb_diag_state==3 && !maps);
    fixture();font.height=65;assert(fb_remap()==-EINVAL && fb_diag_state==3 && !maps);
    fixture();font.width=16;assert(fb_remap()==-EINVAL && fb_diag_state==4 && !maps);
    fixture();map_ok=false;assert(fb_remap()==-ENOMEM && fb_diag_state==5 && mapping_failed && maps==1);
    puts("PASS: 15 actual mapping/parser scenarios, including absent/retired console, bounds and mapping failures");
#endif
}
