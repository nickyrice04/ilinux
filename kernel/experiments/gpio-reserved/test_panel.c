/* Actual eight-lane renderer: bounds, exact glyphs and overwrite recovery. */
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
typedef uint8_t u8;
typedef uint32_t u32;
typedef uint64_t u64;
#define U32_MAX UINT32_MAX
#define READ_ONCE(x) (x)
#define WRITE_ONCE(x,v) ((x)=(v))
#define DIV_ROUND_UP(a,b) (((a)+(b)-1)/(b))
struct font_desc { unsigned int width,height; const unsigned char *data; };
static const struct font_desc *fb_font;
static void *fb_mapping;
static bool mapping_failed;
static u32 fb_width,fb_height,fb_stride;
bool ilinux_probe_diag;
#include "status-panel.h"
static void run(unsigned int w,unsigned int h)
{
 unsigned char font[256*64*4];
 for(size_t i=0;i<sizeof(font);i++)font[i]=(i*19+i/5)&255;
 struct font_desc f={w,h,font};fb_font=&f;
 fb_width=12*w*4;fb_height=22*h;fb_stride=fb_width*4+32;
 size_t words=(size_t)fb_stride/4*fb_height;
 u32 *ram=malloc((words+2)*sizeof(*ram));assert(ram);fb_mapping=ram+1;
 for(size_t i=0;i<words+2;i++)ram[i]=0x12345678;
 for(unsigned int lane=0;lane<8;lane++)assert(ilinux_probe_fb_mark(lane,lane==4?0x1234:lane==6?0x011E:lane==7?0x08D:lane+1));
 const char *lines[]={"P:01 S:02","W:03 H:04","D:1234 I:08D","B:06 C:011E"};
 for(u32 y=0;y<fb_height;y++)for(u32 x=0;x<fb_stride/4;x++) {
  bool touched=false;u32 expected=0x12345678;
  if(y>=fb_height-16*h && x<fb_width){
   u32 row=(y-(fb_height-16*h))/(4*h),col=x/(4*w);
   if(col<strlen(lines[row]) && lines[row][col]!=' '){
    unsigned char ch=lines[row][col];u32 gx=x%(4*w)/4,gy=y%(4*h)/4;
    /* y's origin is not generally a multiple of 4*h. */
    gy=(y-(fb_height-16*h))%(4*h)/4;
    expected=(font[ch*h*DIV_ROUND_UP(w,8)+gy*DIV_ROUND_UP(w,8)+gx/8]&(0x80>>(gx%8)))?U32_MAX:0;touched=true;
   }
  }
  assert(ram[1+(size_t)y*(fb_stride/4)+x]==(touched?expected:0x12345678));
 }
 assert(ram[0]==0x12345678 && ram[words+1]==0x12345678);
 u32 *saved=malloc(words*sizeof(*saved));assert(saved);memcpy(saved,fb_mapping,words*4);
 for(size_t i=0;i<words;i++)((u32*)fb_mapping)[i]=0x12345678;
 assert(ilinux_probe_fb_mark(3,4));assert(!memcmp(saved,fb_mapping,words*4));free(saved);
 assert(!ilinux_probe_fb_mark(8,0) && !ilinux_probe_fb_mark(0,256) && !ilinux_probe_fb_mark(4,65536) && !ilinux_probe_fb_mark(7,4096));
 fb_width--;assert(!ilinux_probe_fb_mark(0,0));fb_width++;
 fb_height--;assert(!ilinux_probe_fb_mark(0,0));fb_height++;
 mapping_failed=true;assert(!ilinux_probe_fb_mark(0,0));mapping_failed=false;
 fb_font=NULL;assert(!ilinux_probe_fb_mark(0,0));fb_font=&f;
 ilinux_probe_diag=false;assert(!ilinux_probe_fb_mark(0,0));ilinux_probe_diag=true;
 fb_mapping=NULL;assert(!ilinux_probe_fb_mark(0,0));free(ram);
}
int main(void){ilinux_probe_diag=true;fb_text_height=0;assert(!fb_text_height);assert(!ilinux_probe_fb_state());run(8,16);run(32,64);run(1,1);puts("PASS: actual compact panel, exact glyph pixels, eight lanes, overwrite repaint, three fonts and bounds");}
