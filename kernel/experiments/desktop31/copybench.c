// SPDX-License-Identifier: MIT
// Original GLES3 identity-copy equivalence and timing test. No display device access.
#define _GNU_SOURCE
#include <EGL/egl.h>
#include <EGL/eglext.h>
#include <GLES3/gl3.h>
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>
static GLuint fb[3],tex[3],program,vao;
static int width,height,flip,dest_rgb;
static double now(void){struct timespec t;assert(!clock_gettime(CLOCK_MONOTONIC,&t));return t.tv_sec+t.tv_nsec/1e9;}
static GLuint shader(GLenum kind,const char *s){GLuint id=glCreateShader(kind);glShaderSource(id,1,&s,NULL);glCompileShader(id);GLint ok;glGetShaderiv(id,GL_COMPILE_STATUS,&ok);assert(ok);return id;}
static void setup(int w,int h){
 width=w;height=h;
 glGenFramebuffers(3,fb);glGenTextures(3,tex);
 uint32_t *pixels=malloc((size_t)w*h*4);assert(pixels);
 uint32_t rnd=0x12345678;
 for(int y=0;y<h;y++)for(int x=0;x<w;x++){rnd=rnd*1664525u+1013904223u;pixels[y*w+x]=rnd;}
 for(int i=0;i<3;i++){
  glBindTexture(GL_TEXTURE_2D,tex[i]);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_LINEAR);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_LINEAR);
  glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_S,GL_CLAMP_TO_EDGE);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_T,GL_CLAMP_TO_EDGE);
  glTexImage2D(GL_TEXTURE_2D,0,(i && dest_rgb)?GL_RGB8:GL_RGBA8,w,h,0,(i && dest_rgb)?GL_RGB:GL_RGBA,GL_UNSIGNED_BYTE,i==0?pixels:NULL);
  glBindFramebuffer(GL_FRAMEBUFFER,fb[i]);glFramebufferTexture2D(GL_FRAMEBUFFER,GL_COLOR_ATTACHMENT0,GL_TEXTURE_2D,tex[i],0);assert(glCheckFramebufferStatus(GL_FRAMEBUFFER)==GL_FRAMEBUFFER_COMPLETE);
 }
 free(pixels);glViewport(0,0,w,h);glDisable(GL_BLEND);glDisable(GL_DITHER);glDisable(GL_DEPTH_TEST);glDisable(GL_STENCIL_TEST);
}
static void cleanup(void){glDeleteFramebuffers(3,fb);glDeleteTextures(3,tex);}
static void draw(int mode,int x,int y,int w,int h){
 glBindFramebuffer(GL_DRAW_FRAMEBUFFER,fb[mode?2:1]);
 glEnable(GL_SCISSOR_TEST);glScissor(x,y,w,h);
 if(mode){glBindFramebuffer(GL_READ_FRAMEBUFFER,fb[0]);glBlitFramebuffer(x,flip?height-y:y,x+w,flip?height-y-h:y+h,x,y,x+w,y+h,GL_COLOR_BUFFER_BIT,GL_NEAREST);}
 else {glUseProgram(program);glActiveTexture(GL_TEXTURE0);glBindTexture(GL_TEXTURE_2D,tex[0]);glUniform1i(glGetUniformLocation(program,"image"),0);glUniform1i(glGetUniformLocation(program,"flip_y"),flip);glBindVertexArray(vao);glDrawArrays(GL_TRIANGLE_STRIP,0,4);}
}
static void parity(void){
 size_t bytes=(size_t)width*height*4;uint8_t *a=malloc(bytes),*b=malloc(bytes);assert(a&&b);
 int rects[][4]={{0,0,width,height},{0,0,1,1},{width-1,height-1,1,1},{3,5,13,17},{width/3,height/4,width/2,height/2},{0,0,0,0},{-3,-5,9,11},{width-2,height-2,9,11}};
 for(unsigned r=0;r<sizeof(rects)/sizeof(rects[0]);r++){
  for(int mode=0;mode<2;mode++){
   glBindFramebuffer(GL_FRAMEBUFFER,fb[mode?2:1]);glDisable(GL_SCISSOR_TEST);glClearColor(.2,.4,.6,.8);glClear(GL_COLOR_BUFFER_BIT);
   draw(mode,rects[r][0],rects[r][1],rects[r][2],rects[r][3]);glFinish();glBindFramebuffer(GL_READ_FRAMEBUFFER,fb[mode?2:1]);glReadPixels(0,0,width,height,GL_RGBA,GL_UNSIGNED_BYTE,mode?b:a);
  }
  size_t differing=0;for(size_t i=0;i<bytes;i++)differing+=a[i]!=b[i];
  printf("{\"kind\":\"parity\",\"width\":%d,\"height\":%d,\"flip\":%d,\"rgb_destination\":%d,\"rect\":%u,\"different_bytes\":%zu}\n",width,height,flip,dest_rgb,r,differing);assert(!differing);assert(glGetError()==GL_NO_ERROR);
 }
 free(a);free(b);
}
int main(void){
 alarm(90);
 EGLDisplay d=eglGetPlatformDisplay(EGL_PLATFORM_SURFACELESS_MESA,EGL_DEFAULT_DISPLAY,NULL);assert(d!=EGL_NO_DISPLAY);assert(eglInitialize(d,NULL,NULL));assert(eglBindAPI(EGL_OPENGL_ES_API));
 EGLint ca[]={EGL_SURFACE_TYPE,EGL_PBUFFER_BIT,EGL_RENDERABLE_TYPE,EGL_OPENGL_ES3_BIT,EGL_NONE};EGLConfig c;EGLint n;assert(eglChooseConfig(d,ca,&c,1,&n)&&n);
 EGLint attr[]={EGL_CONTEXT_CLIENT_VERSION,3,EGL_NONE};EGLContext ctx=eglCreateContext(d,c,EGL_NO_CONTEXT,attr);assert(ctx!=EGL_NO_CONTEXT);assert(eglMakeCurrent(d,EGL_NO_SURFACE,EGL_NO_SURFACE,ctx));
 const char *vs="#version 300 es\nprecision highp float;out vec2 uv;uniform bool flip_y;void main(){vec2 p=vec2(float((gl_VertexID>>1)&1),float(gl_VertexID&1));uv=vec2(p.x,flip_y?1.-p.y:p.y);gl_Position=vec4(p*2.-1.,0.,1.);}";
 const char *fs="#version 300 es\nprecision highp float;in vec2 uv;uniform sampler2D image;out vec4 outColor;void main(){outColor=texture(image,uv);}";
 GLuint v=shader(GL_VERTEX_SHADER,vs),f=shader(GL_FRAGMENT_SHADER,fs);program=glCreateProgram();glAttachShader(program,v);glAttachShader(program,f);glLinkProgram(program);GLint ok;glGetProgramiv(program,GL_LINK_STATUS,&ok);assert(ok);glDeleteShader(v);glDeleteShader(f);glGenVertexArrays(1,&vao);
 printf("{\"kind\":\"renderer\",\"renderer\":\"%s\"}\n",glGetString(GL_RENDERER));
 for(dest_rgb=0;dest_rgb<2;dest_rgb++)for(flip=0;flip<2;flip++){
  setup(67,49);parity();cleanup();setup(3456,2160);parity();cleanup();
 }
 dest_rgb=0;flip=0;setup(3456,2160);
 int modes[]={0,1,1,0};
 for(int round=0;round<4;round++){
  int mode=modes[round];
  for(int i=0;i<2;i++){draw(mode,0,0,width,height);glFinish();}
  for(int i=0;i<6;i++){double t=now();draw(mode,0,0,width,height);glFinish();printf("{\"kind\":\"timing\",\"round\":%d,\"mode\":%d,\"index\":%d,\"ms\":%.6f}\n",round,mode,i,(now()-t)*1000);}
 }
 assert(glGetError()==GL_NO_ERROR);cleanup();glDeleteVertexArrays(1,&vao);glDeleteProgram(program);eglMakeCurrent(d,EGL_NO_SURFACE,EGL_NO_SURFACE,EGL_NO_CONTEXT);eglDestroyContext(d,ctx);eglTerminate(d);return 0;
}
