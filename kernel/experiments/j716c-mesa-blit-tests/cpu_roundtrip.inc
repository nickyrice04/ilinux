/* Original iLinux test-only CPU transfer coverage. No GPU pixel oracle. */
static bool
check_cpu_transfer_roundtrip(struct pipe_context *pctx)
{
   enum { WIDTH = 4, HEIGHT = 8, ROW = 32 };
   static const enum pipe_format formats[] = {
      PIPE_FORMAT_B8G8R8A8_UNORM, PIPE_FORMAT_R8G8B8A8_UNORM,
   };
   const struct pipe_box box = {.width = WIDTH, .height = HEIGHT, .depth = 1};
   for (unsigned f = 0; f < ARRAY_SIZE(formats); ++f) {
      uint8_t input[ROW * HEIGHT], rgba[ROW * HEIGHT], back[ROW * HEIGHT];
      memset(input, 0xa5, sizeof(input));
      memset(rgba, 0xcd, sizeof(rgba));
      memset(back, 0xef, sizeof(back));
      for (unsigned y = 0; y < HEIGHT; ++y) {
         for (unsigned x = 0; x < WIDTH; ++x) {
            const uint8_t r = 17 + 13 * x + 7 * y;
            const uint8_t g = 91 + 11 * x + 5 * y;
            const uint8_t b = 203 + 3 * x + 17 * y;
            const uint8_t a = (x == 0 && y == 0) ? 0 : 255 - 9 * (x + y);
            uint8_t *pixel = input + y * ROW + x * 4;
            pixel[0] = f == 0 ? b : r;
            pixel[1] = g;
            pixel[2] = f == 0 ? r : b;
            pixel[3] = a;
         }
      }
      struct pipe_resource *resource = make_2d(
         pctx->screen, formats[f], WIDTH, HEIGHT, PIPE_BIND_SAMPLER_VIEW);
      if (!resource)
         return false;
      /* This case must stay CPU-only: compressed staging needs real GPU work. */
      if (agx_resource(resource)->layout.compressed) {
         pipe_resource_reference(&resource, NULL);
         return false;
      }
      pctx->texture_subdata(pctx, resource, 0, 0, &box, input, ROW, sizeof(input));
      struct pipe_transfer *transfer = NULL;
      const uint8_t *map = pipe_texture_map(
         pctx, resource, 0, 0, PIPE_MAP_READ, 0, 0, WIDTH, HEIGHT, &transfer);
      bool ok = map && transfer && transfer->stride >= WIDTH * 4;
      if (ok) {
         for (unsigned y = 0; y < HEIGHT; ++y)
            ok &= memcmp(map + y * transfer->stride, input + y * ROW,
                         WIDTH * 4) == 0;
         ok &= util_format_translate(PIPE_FORMAT_R8G8B8A8_UNORM,
                                     rgba, ROW, 0, 0, formats[f], map,
                                     transfer->stride, 0, 0, WIDTH, HEIGHT);
         ok &= util_format_translate(formats[f], back, ROW, 0, 0,
                                     PIPE_FORMAT_R8G8B8A8_UNORM,
                                     rgba, ROW, 0, 0, WIDTH, HEIGHT);
         for (unsigned y = 0; y < HEIGHT; ++y) {
            for (unsigned x = 0; x < WIDTH; ++x) {
               const uint8_t *pixel = rgba + y * ROW + x * 4;
               ok &= pixel[0] == (uint8_t)(17 + 13 * x + 7 * y);
               ok &= pixel[1] == (uint8_t)(91 + 11 * x + 5 * y);
               ok &= pixel[2] == (uint8_t)(203 + 3 * x + 17 * y);
               ok &= pixel[3] == ((x == 0 && y == 0) ? 0 : 255 - 9 * (x + y));
            }
            ok &= memcmp(back + y * ROW, input + y * ROW, WIDTH * 4) == 0;
            for (unsigned byte = WIDTH * 4; byte < ROW; ++byte)
               ok &= rgba[y * ROW + byte] == 0xcd && back[y * ROW + byte] == 0xef;
         }
      }
      if (transfer)
         pctx->texture_unmap(pctx, transfer);
      pipe_resource_reference(&resource, NULL);
      if (!ok) {
         fprintf(stderr, "CPU texture transfer/conversion roundtrip failed\n");
         return false;
      }
   }
   printf("CPU texture transfer/conversion: 2 formats, 64 pixels PASS\n");
   return true;
}

