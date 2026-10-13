/* Exercise real VA images, texture uploads/downloads, pitches and even crops.
 * cc -O2 va_image_roundtrip.c -o va_image_roundtrip $(pkg-config --cflags --libs libva libva-drm)
 * Run with LIBVA_DRIVERS_PATH pointing at the driver under test.
 */
#include <va/va.h>
#include <va/va_drm.h>
#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

static void check(VAStatus status, const char *operation)
{
    if (status != VA_STATUS_SUCCESS) {
        fprintf(stderr, "%s: %s\n", operation, vaErrorStr(status));
        exit(1);
    }
}
#define CHECK(call) check((call), #call)

static unsigned char pattern(unsigned component, unsigned x, unsigned y)
{
    return component == 0 ? 16 + (3*x + 5*y) % 200 :
           component == 1 ? 32 + (7*x + y) % 80 : 144 + (x + 3*y) % 80;
}

static uint8_t *pixel(uint8_t *data, const VAImage *image,
                      unsigned component, unsigned x, unsigned y)
{
    unsigned plane = component, step = 1, offset = 0;
    if (image->format.fourcc == VA_FOURCC_NV12 && component) {
        plane = 1;
        step = 2;
        offset = component - 1;
    } else if (image->format.fourcc == VA_FOURCC_YV12 && component) {
        plane = 3 - component;
    }
    return data + image->offsets[plane] + y * image->pitches[plane] + step*x + offset;
}

int main(void)
{
    const unsigned width = 66, height = 38;
    const uint32_t formats[] = { VA_FOURCC_NV12, VA_FOURCC_I420, VA_FOURCC_YV12 };
    int fd = open("/dev/dri/renderD128", O_RDWR);
    if (fd < 0) { perror("render node"); return 1; }
    VADisplay display = vaGetDisplayDRM(fd);
    int major, minor;
    CHECK(vaInitialize(display, &major, &minor));
    unsigned long failures = 0;
    unsigned cases = 0;
    for (unsigned src = 0; src < 3; src++) {
        VASurfaceAttrib attr = {
            .type = VASurfaceAttribPixelFormat,
            .flags = VA_SURFACE_ATTRIB_SETTABLE,
            .value = { .type = VAGenericValueTypeInteger, .value.i = formats[src] }
        };
        VASurfaceID surface;
        CHECK(vaCreateSurfaces(display, VA_RT_FORMAT_YUV420, width, height,
                               &surface, 1, &attr, 1));
        VAImage input;
        VAImageFormat format = { .fourcc = formats[src] };
        CHECK(vaCreateImage(display, &format, width, height, &input));
        uint8_t *data;
        CHECK(vaMapBuffer(display, input.buf, (void **)&data));
        memset(data, 0xcd, input.data_size);
        for (unsigned c = 0; c < 3; c++)
            for (unsigned y = 0; y < (c ? height/2 : height); y++)
                for (unsigned x = 0; x < (c ? width/2 : width); x++)
                    *pixel(data, &input, c, x, y) = pattern(c, x, y);
        CHECK(vaUnmapBuffer(display, input.buf));
        CHECK(vaPutImage(display, surface, input.image_id, 0, 0, width, height,
                         0, 0, width, height));
        CHECK(vaSyncSurface(display, surface));
        for (unsigned dst = 0; dst < 3; dst++) {
            for (unsigned crop = 0; crop < 2; crop++) {
                unsigned ox = crop ? 2 : 0, oy = crop ? 4 : 0;
                unsigned w = crop ? 32 : width, h = crop ? 18 : height;
                VAImage output;
                format.fourcc = formats[dst];
                CHECK(vaCreateImage(display, &format, w, h, &output));
                CHECK(vaGetImage(display, surface, ox, oy, w, h, output.image_id));
                CHECK(vaMapBuffer(display, output.buf, (void **)&data));
                unsigned long mismatches = 0;
                for (unsigned c = 0; c < 3; c++)
                    for (unsigned y = 0; y < (c ? h/2 : h); y++)
                        for (unsigned x = 0; x < (c ? w/2 : w); x++)
                            mismatches += *pixel(data, &output, c, x, y) !=
                                pattern(c, x + (c ? ox/2 : ox), y + (c ? oy/2 : oy));
                CHECK(vaUnmapBuffer(display, output.buf));
                CHECK(vaDestroyImage(display, output.image_id));
                printf("{\"src_fourcc\":%u,\"dst_fourcc\":%u,\"crop\":%u,"
                       "\"mismatched_bytes\":%lu}\n", formats[src], formats[dst], crop, mismatches);
                failures += mismatches;
                cases++;
            }
        }
        CHECK(vaDestroyImage(display, input.image_id));
        CHECK(vaDestroySurfaces(display, &surface, 1));
    }
    CHECK(vaTerminate(display));
    close(fd);
    fprintf(stderr, "%u cases, %lu mismatched bytes\n", cases, failures);
    return failures != 0;
}
