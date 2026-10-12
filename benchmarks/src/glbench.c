// glbench.c - OpenGL 4.1 core micro-benchmarks with identical GL code on
// macOS (CGL, offscreen) and Linux (EGL surfaceless, e.g. Mesa virgl in the
// VM).  The VM's desktop GPU path is guest GL -> virgl -> host CGL/OpenGL
// 4.1 (Metal), so running this on both sides isolates the virtualization
// overhead of that path.
//
//   macOS:  clang -O2 glbench.c -o glbench -framework OpenGL
//   Linux:  cc -O2 glbench.c -o glbench -lEGL -lOpenGL
//   glbench [alu|fill|draws|upload|readback ...]      (default: all)
//   env GLB_W / GLB_H: render-target size (default 2592x1458, the VM desktop)
//
// Output: one JSON line per test (bench, test, value, unit, iterations, s).
#define _POSIX_C_SOURCE 200809L
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#ifdef __APPLE__
#define GL_SILENCE_DEPRECATION
#include <OpenGL/OpenGL.h>
#include <OpenGL/gl3.h>
#else
#define GL_GLEXT_PROTOTYPES 1
#include <EGL/egl.h>
#include <EGL/eglext.h>
#include <GL/gl.h>
#include <GL/glext.h>
#endif

static int W = 2592, H = 1458;
static GLuint fbo, fbtex, vao;

static double now(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec + ts.tv_nsec * 1e-9;
}

static void die(const char *m) { fprintf(stderr, "glbench: %s\n", m); exit(1); }

static void ctx_init(void) {
#ifdef __APPLE__
    CGLPixelFormatAttribute a[] = {
        kCGLPFAOpenGLProfile, (CGLPixelFormatAttribute)kCGLOGLPVersion_GL4_Core,
        kCGLPFAAccelerated, kCGLPFAColorSize, (CGLPixelFormatAttribute)24,
        kCGLPFAAlphaSize, (CGLPixelFormatAttribute)8, (CGLPixelFormatAttribute)0 };
    CGLPixelFormatObj pf; GLint n; CGLContextObj c;
    if (CGLChoosePixelFormat(a, &pf, &n) || !pf) die("CGLChoosePixelFormat");
    if (CGLCreateContext(pf, NULL, &c)) die("CGLCreateContext");
    CGLDestroyPixelFormat(pf);
    CGLSetCurrentContext(c);
#else
    PFNEGLGETPLATFORMDISPLAYEXTPROC gpd =
        (PFNEGLGETPLATFORMDISPLAYEXTPROC)eglGetProcAddress("eglGetPlatformDisplayEXT");
    EGLDisplay d = gpd ? gpd(EGL_PLATFORM_SURFACELESS_MESA, EGL_DEFAULT_DISPLAY, NULL)
                       : EGL_NO_DISPLAY;
    if (d == EGL_NO_DISPLAY) d = eglGetDisplay(EGL_DEFAULT_DISPLAY);
    if (!eglInitialize(d, NULL, NULL)) die("eglInitialize");
    if (!eglBindAPI(EGL_OPENGL_API)) die("eglBindAPI");
    EGLint ca[] = { EGL_RENDERABLE_TYPE, EGL_OPENGL_BIT, EGL_NONE };
    EGLConfig cfg = NULL; EGLint nc = 0;
    eglChooseConfig(d, ca, &cfg, 1, &nc);
    EGLint xa[] = { EGL_CONTEXT_MAJOR_VERSION, 4, EGL_CONTEXT_MINOR_VERSION, 1,
                    EGL_CONTEXT_OPENGL_PROFILE_MASK, EGL_CONTEXT_OPENGL_CORE_PROFILE_BIT,
                    EGL_NONE };
    EGLContext c = eglCreateContext(d, nc ? cfg : (EGLConfig)0, EGL_NO_CONTEXT, xa);
    if (c == EGL_NO_CONTEXT) die("eglCreateContext (GL 4.1 core)");
    if (!eglMakeCurrent(d, EGL_NO_SURFACE, EGL_NO_SURFACE, c)) die("eglMakeCurrent");
#endif
}

static GLuint compile(GLenum type, const char *src) {
    GLuint s = glCreateShader(type);
    glShaderSource(s, 1, &src, NULL);
    glCompileShader(s);
    GLint ok; glGetShaderiv(s, GL_COMPILE_STATUS, &ok);
    if (!ok) { char log[2048]; glGetShaderInfoLog(s, sizeof log, NULL, log); fprintf(stderr, "%s\n", log); die("shader"); }
    return s;
}

static GLuint program(const char *vs, const char *fs) {
    GLuint p = glCreateProgram();
    glAttachShader(p, compile(GL_VERTEX_SHADER, vs));
    glAttachShader(p, compile(GL_FRAGMENT_SHADER, fs));
    glLinkProgram(p);
    GLint ok; glGetProgramiv(p, GL_LINK_STATUS, &ok);
    if (!ok) die("link");
    return p;
}

// Full-screen triangle from gl_VertexID; `scale`/`offset` shrink it for the
// draw-call test.
static const char *VS =
    "#version 410 core\n"
    "uniform vec2 scale; uniform vec2 offset; out vec2 uv;\n"
    "void main() {\n"
    "  vec2 p = vec2((gl_VertexID << 1) & 2, gl_VertexID & 2);\n"
    "  uv = p;\n"
    "  gl_Position = vec4((p * 2.0 - 1.0) * scale + offset, 0.0, 1.0);\n"
    "}\n";

// Four independent FMA chains per pixel (ILP); coefficients are uniforms so
// the compiler cannot fold the loop.  8 flops per chain-step x 4 lanes.
static const char *FS_ALU =
    "#version 410 core\n"
    "uniform int iters; uniform vec4 a; uniform vec4 b; out vec4 color;\n"
    "void main() {\n"
    "  vec4 v0 = vec4(gl_FragCoord.xyxy * 1e-4), v1 = v0 + 0.1, v2 = v0 + 0.2, v3 = v0 + 0.3;\n"
    "  for (int i = 0; i < iters; i++) {\n"
    "    v0 = fma(v0, a, b); v1 = fma(v1, a, b); v2 = fma(v2, a, b); v3 = fma(v3, a, b);\n"
    "  }\n"
    "  color = v0 + v1 + v2 + v3;\n"
    "}\n";

static const char *FS_FLAT =
    "#version 410 core\n"
    "uniform vec4 col; out vec4 color;\n"
    "void main() { color = col; }\n";

static const char *FS_TEX =
    "#version 410 core\n"
    "uniform sampler2D tex; in vec2 uv; out vec4 color;\n"
    "void main() { color = texture(tex, uv); }\n";

static void target_init(void) {
    glGenTextures(1, &fbtex);
    glBindTexture(GL_TEXTURE_2D, fbtex);
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA8, W, H, 0, GL_RGBA, GL_UNSIGNED_BYTE, NULL);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST);
    glGenFramebuffers(1, &fbo);
    glBindFramebuffer(GL_FRAMEBUFFER, fbo);
    glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, fbtex, 0);
    if (glCheckFramebufferStatus(GL_FRAMEBUFFER) != GL_FRAMEBUFFER_COMPLETE) die("fbo");
    glViewport(0, 0, W, H);
    glGenVertexArrays(1, &vao);
    glBindVertexArray(vao);
}

static void set_quad(GLuint p, float sx, float sy, float ox, float oy) {
    glUniform2f(glGetUniformLocation(p, "scale"), sx, sy);
    glUniform2f(glGetUniformLocation(p, "offset"), ox, oy);
}

static void report(const char *test, double value, const char *unit, long iters, double s) {
    printf("{\"bench\":\"glbench\",\"test\":\"%s\",\"value\":%.4g,\"unit\":\"%s\","
           "\"iterations\":%ld,\"seconds\":%.3f,\"size\":\"%dx%d\"}\n",
           test, value, unit, iters, s, W, H);
    fflush(stdout);
}

// Run `step` repeatedly (glFinish after each batch) for ~2 s after one
// warm-up batch; return iterations done and elapsed seconds.
typedef void (*step_fn)(void *);
static double run_timed(step_fn step, void *arg, int batch, long *iters) {
    for (int i = 0; i < batch; i++) step(arg);
    glFinish();
    long n = 0; double t0 = now(), t;
    do {
        for (int i = 0; i < batch; i++) step(arg);
        glFinish();
        n += batch;
    } while ((t = now() - t0) < 2.0);
    *iters = n;
    return t;
}

static void draw_full(void *p) { (void)p; glDrawArrays(GL_TRIANGLES, 0, 3); }

static void test_alu(void) {
    GLuint p = program(VS, FS_ALU);
    glUseProgram(p); set_quad(p, 1, 1, 0, 0);
    const int iters = 256;
    glUniform1i(glGetUniformLocation(p, "iters"), iters);
    glUniform4f(glGetUniformLocation(p, "a"), 0.99991f, 0.99992f, 0.99993f, 0.99994f);
    glUniform4f(glGetUniformLocation(p, "b"), 1e-4f, 2e-4f, 3e-4f, 4e-4f);
    // Additive blending: a tile-based GPU's hidden-surface removal would
    // otherwise shade only the last of several opaque full-screen draws.
    glEnable(GL_BLEND); glBlendFunc(GL_ONE, GL_ONE);
    long n; double s = run_timed(draw_full, NULL, 4, &n);
    glDisable(GL_BLEND);
    double flops = (double)W * H * iters * 4 /*chains*/ * 4 /*lanes*/ * 2 * n;
    report("alu", flops / s / 1e9, "GFLOPS", n, s);
}

static void test_fill(void) {
    GLuint p = program(VS, FS_FLAT);
    glUseProgram(p); set_quad(p, 1, 1, 0, 0);
    glUniform4f(glGetUniformLocation(p, "col"), 0.2f, 0.4f, 0.6f, 0.5f);
    glEnable(GL_BLEND); glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);
    long n; double s = run_timed(draw_full, NULL, 16, &n);
    glDisable(GL_BLEND);
    // The full-screen triangle covers W*H pixels (the rest is clipped).
    report("fill_blend", (double)W * H * n / s / 1e9, "Gpix/s", n, s);
}

struct draws_arg { GLuint p; GLint off; int per_frame; };
static void draws_frame(void *v) {
    struct draws_arg *d = v;
    for (int i = 0; i < d->per_frame; i++) {
        glUniform2f(d->off, (float)(i % 100) / 50.0f - 1.0f, (float)(i / 100 % 100) / 50.0f - 1.0f);
        glDrawArrays(GL_TRIANGLES, 0, 3);
    }
}
static void test_draws(void) {
    struct draws_arg d = { program(VS, FS_FLAT), 0, 10000 };
    glUseProgram(d.p); set_quad(d.p, 0.01f, 0.01f, 0, 0);
    glUniform4f(glGetUniformLocation(d.p, "col"), 1, 1, 1, 1);
    d.off = glGetUniformLocation(d.p, "offset");
    long n; double s = run_timed(draws_frame, &d, 1, &n);
    report("draw_calls", (double)n * d.per_frame / s / 1e6, "Mdraws/s", n * d.per_frame, s);
}

struct xfer_arg { GLuint tex; int tw, th; unsigned char *buf; };
static void upload_step(void *v) {
    struct xfer_arg *x = v;
    glBindTexture(GL_TEXTURE_2D, x->tex);
    glTexSubImage2D(GL_TEXTURE_2D, 0, 0, 0, x->tw, x->th, GL_RGBA, GL_UNSIGNED_BYTE, x->buf);
    x->buf[0]++;   // defeat any upload de-duplication
    glDrawArrays(GL_TRIANGLES, 0, 3);   // consume it
}
static void test_upload(void) {
    struct xfer_arg x = { 0, 2048, 2048, malloc(2048 * 2048 * 4) };
    memset(x.buf, 0x5a, 2048 * 2048 * 4);
    GLuint p = program(VS, FS_TEX);
    glUseProgram(p); set_quad(p, 0.05f, 0.05f, 0, 0);
    glGenTextures(1, &x.tex);
    glBindTexture(GL_TEXTURE_2D, x.tex);
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA8, x.tw, x.th, 0, GL_RGBA, GL_UNSIGNED_BYTE, NULL);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST);
    long n; double s = run_timed(upload_step, &x, 4, &n);
    report("tex_upload", (double)x.tw * x.th * 4 * n / s / 1e9, "GB/s", n, s);
    free(x.buf);
}

static void readback_step(void *v) {
    struct xfer_arg *x = v;
    glReadPixels(0, 0, x->tw, x->th, GL_RGBA, GL_UNSIGNED_BYTE, x->buf);
}
static void test_readback(void) {
    int tw = W < 2048 ? W : 2048, th = H < 2048 ? H : 2048;
    struct xfer_arg x = { 0, tw, th, malloc((size_t)tw * th * 4) };
    glBindFramebuffer(GL_FRAMEBUFFER, fbo);
    long n; double s = run_timed(readback_step, &x, 2, &n);
    report("readback", (double)tw * th * 4 * n / s / 1e9, "GB/s", n, s);
    free(x.buf);
}

int main(int argc, char **argv) {
    if (getenv("GLB_W")) W = atoi(getenv("GLB_W"));
    if (getenv("GLB_H")) H = atoi(getenv("GLB_H"));
    ctx_init();
    printf("{\"bench\":\"glbench-info\",\"renderer\":\"%s\",\"version\":\"%s\"}\n",
           (const char *)glGetString(GL_RENDERER), (const char *)glGetString(GL_VERSION));
    target_init();
    struct { const char *name; void (*fn)(void); } tests[] = {
        { "alu", test_alu }, { "fill", test_fill }, { "draws", test_draws },
        { "upload", test_upload }, { "readback", test_readback } };
    int ntests = sizeof tests / sizeof tests[0];
    for (int t = 0; t < ntests; t++) {
        int run = argc < 2;
        for (int i = 1; i < argc; i++) run |= !strcmp(argv[i], tests[t].name);
        if (run) tests[t].fn();
        if (glGetError() != GL_NO_ERROR) fprintf(stderr, "glbench: GL error after %s\n", tests[t].name);
    }
    return 0;
}
