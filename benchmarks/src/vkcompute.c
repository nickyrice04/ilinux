// vkcompute.c - minimal Vulkan compute benchmark with a correctness check.
// The same code runs natively on macOS (Khronos loader + MoltenVK) and in the
// Linux VM (Mesa Venus -> virglrenderer -> MoltenVK), so the two results
// isolate the cost of the virtualized Vulkan path.
//
//   glslangValidator -V vkcompute.comp -o vkcompute.spv
//   macOS:  clang -O2 vkcompute.c -I$RT/include -L$RT/lib -lvulkan -Wl,-rpath,$RT/lib
//   Linux:  cc -O2 vkcompute.c -lvulkan -lm
//   vkcompute vkcompute.spv [iters] [reps]
//
// Output: JSON lines (bench, test, value, unit ...).  Exit status 1 if the
// GPU result does not match the CPU reference.
#define _POSIX_C_SOURCE 200809L
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <vulkan/vulkan.h>

#define CHECK(x) do { VkResult r_ = (x); if (r_ != VK_SUCCESS) { \
    fprintf(stderr, "vkcompute: %s failed: %d\n", #x, r_); exit(2); } } while (0)

static double now(void)
{
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec + ts.tv_nsec * 1e-9;
}

static int cmpd(const void *a, const void *b)
{
    double x = *(const double *)a, y = *(const double *)b;
    return x < y ? -1 : x > y;
}

static uint32_t *read_file(const char *path, size_t *size)
{
    FILE *f = fopen(path, "rb");
    if (!f) { perror(path); exit(2); }
    fseek(f, 0, SEEK_END);
    *size = (size_t)ftell(f);
    fseek(f, 0, SEEK_SET);
    uint32_t *buf = malloc(*size);
    if (fread(buf, 1, *size, f) != *size) { perror("read"); exit(2); }
    fclose(f);
    return buf;
}

static int has_ext(const VkExtensionProperties *e, uint32_t n, const char *name)
{
    for (uint32_t i = 0; i < n; i++)
        if (!strcmp(e[i].extensionName, name)) return 1;
    return 0;
}

struct pc { uint32_t iters; float a, b; };

int main(int argc, char **argv)
{
    if (argc < 2) { fprintf(stderr, "usage: vkcompute shader.spv [iters] [reps]\n"); return 2; }
    const uint32_t iters = argc > 2 ? (uint32_t)atoi(argv[2]) : 2048;
    const int reps = argc > 3 ? atoi(argv[3]) : 10;
    const uint32_t n = 1u << 22;                       /* 4M floats, 16 MiB */
    const struct pc check_pc = { 8, 0.999f, 0.001f }, bench_pc = { iters, 0.99991f, 0.0001f };

    /* Instance: portability enumeration lets the loader list MoltenVK. */
    uint32_t ie_n = 0;
    vkEnumerateInstanceExtensionProperties(NULL, &ie_n, NULL);
    VkExtensionProperties *ie = calloc(ie_n ? ie_n : 1, sizeof(*ie));
    vkEnumerateInstanceExtensionProperties(NULL, &ie_n, ie);
    const char *iexts[1]; uint32_t iext_n = 0; VkInstanceCreateFlags iflags = 0;
    if (has_ext(ie, ie_n, "VK_KHR_portability_enumeration")) {
        iexts[iext_n++] = "VK_KHR_portability_enumeration";
        iflags |= VK_INSTANCE_CREATE_ENUMERATE_PORTABILITY_BIT_KHR;
    }
    VkApplicationInfo app = { .sType = VK_STRUCTURE_TYPE_APPLICATION_INFO,
                              .pApplicationName = "vkcompute", .apiVersion = VK_API_VERSION_1_1 };
    VkInstanceCreateInfo ici = { .sType = VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO, .flags = iflags,
                                 .pApplicationInfo = &app, .enabledExtensionCount = iext_n,
                                 .ppEnabledExtensionNames = iexts };
    VkInstance inst;
    CHECK(vkCreateInstance(&ici, NULL, &inst));

    uint32_t pd_n = 1;
    VkPhysicalDevice pd;
    CHECK(vkEnumeratePhysicalDevices(inst, &pd_n, &pd) < 0 ? VK_ERROR_INITIALIZATION_FAILED : VK_SUCCESS);
    if (!pd_n) { fprintf(stderr, "vkcompute: no Vulkan device\n"); return 2; }
    VkPhysicalDeviceProperties props;
    vkGetPhysicalDeviceProperties(pd, &props);

    uint32_t qf_n = 0, qf = UINT32_MAX;
    vkGetPhysicalDeviceQueueFamilyProperties(pd, &qf_n, NULL);
    VkQueueFamilyProperties *qfp = calloc(qf_n, sizeof(*qfp));
    vkGetPhysicalDeviceQueueFamilyProperties(pd, &qf_n, qfp);
    for (uint32_t i = 0; i < qf_n && qf == UINT32_MAX; i++)
        if (qfp[i].queueFlags & VK_QUEUE_COMPUTE_BIT) qf = i;

    /* Device: a portability-subset driver (MoltenVK) requires that extension. */
    uint32_t de_n = 0;
    vkEnumerateDeviceExtensionProperties(pd, NULL, &de_n, NULL);
    VkExtensionProperties *de = calloc(de_n ? de_n : 1, sizeof(*de));
    vkEnumerateDeviceExtensionProperties(pd, NULL, &de_n, de);
    const char *dexts[1]; uint32_t dext_n = 0;
    if (has_ext(de, de_n, "VK_KHR_portability_subset")) dexts[dext_n++] = "VK_KHR_portability_subset";
    float prio = 1.0f;
    VkDeviceQueueCreateInfo dqci = { .sType = VK_STRUCTURE_TYPE_DEVICE_QUEUE_CREATE_INFO,
                                     .queueFamilyIndex = qf, .queueCount = 1, .pQueuePriorities = &prio };
    VkDeviceCreateInfo dci = { .sType = VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO, .queueCreateInfoCount = 1,
                               .pQueueCreateInfos = &dqci, .enabledExtensionCount = dext_n,
                               .ppEnabledExtensionNames = dexts };
    VkDevice dev;
    CHECK(vkCreateDevice(pd, &dci, NULL, &dev));
    VkQueue q;
    vkGetDeviceQueue(dev, qf, 0, &q);

    /* Host-visible, coherent storage buffer. */
    VkBufferCreateInfo bci = { .sType = VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO, .size = n * sizeof(float),
                               .usage = VK_BUFFER_USAGE_STORAGE_BUFFER_BIT };
    VkBuffer buf;
    CHECK(vkCreateBuffer(dev, &bci, NULL, &buf));
    VkMemoryRequirements mr;
    vkGetBufferMemoryRequirements(dev, buf, &mr);
    VkPhysicalDeviceMemoryProperties mp;
    vkGetPhysicalDeviceMemoryProperties(pd, &mp);
    const VkMemoryPropertyFlags want = VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT;
    uint32_t mt = UINT32_MAX;
    for (uint32_t i = 0; i < mp.memoryTypeCount && mt == UINT32_MAX; i++)
        if ((mr.memoryTypeBits & (1u << i)) && (mp.memoryTypes[i].propertyFlags & want) == want) mt = i;
    VkMemoryAllocateInfo mai = { .sType = VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO,
                                 .allocationSize = mr.size, .memoryTypeIndex = mt };
    VkDeviceMemory mem;
    CHECK(vkAllocateMemory(dev, &mai, NULL, &mem));
    CHECK(vkBindBufferMemory(dev, buf, mem, 0));
    float *v;
    CHECK(vkMapMemory(dev, mem, 0, VK_WHOLE_SIZE, 0, (void **)&v));

    /* Pipeline. */
    size_t spv_size;
    uint32_t *spv = read_file(argv[1], &spv_size);
    VkShaderModuleCreateInfo smci = { .sType = VK_STRUCTURE_TYPE_SHADER_MODULE_CREATE_INFO,
                                      .codeSize = spv_size, .pCode = spv };
    VkShaderModule sm;
    CHECK(vkCreateShaderModule(dev, &smci, NULL, &sm));
    VkDescriptorSetLayoutBinding b0 = { .binding = 0, .descriptorType = VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,
                                        .descriptorCount = 1, .stageFlags = VK_SHADER_STAGE_COMPUTE_BIT };
    VkDescriptorSetLayoutCreateInfo dslci = { .sType = VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO,
                                              .bindingCount = 1, .pBindings = &b0 };
    VkDescriptorSetLayout dsl;
    CHECK(vkCreateDescriptorSetLayout(dev, &dslci, NULL, &dsl));
    VkPushConstantRange pcr = { VK_SHADER_STAGE_COMPUTE_BIT, 0, sizeof(struct pc) };
    VkPipelineLayoutCreateInfo plci = { .sType = VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO,
                                        .setLayoutCount = 1, .pSetLayouts = &dsl,
                                        .pushConstantRangeCount = 1, .pPushConstantRanges = &pcr };
    VkPipelineLayout pl;
    CHECK(vkCreatePipelineLayout(dev, &plci, NULL, &pl));
    VkComputePipelineCreateInfo cpci = { .sType = VK_STRUCTURE_TYPE_COMPUTE_PIPELINE_CREATE_INFO,
        .stage = { .sType = VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO,
                   .stage = VK_SHADER_STAGE_COMPUTE_BIT, .module = sm, .pName = "main" },
        .layout = pl };
    VkPipeline pipe;
    CHECK(vkCreateComputePipelines(dev, VK_NULL_HANDLE, 1, &cpci, NULL, &pipe));

    VkDescriptorPoolSize ps = { VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, 1 };
    VkDescriptorPoolCreateInfo dpci = { .sType = VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO,
                                        .maxSets = 1, .poolSizeCount = 1, .pPoolSizes = &ps };
    VkDescriptorPool dp;
    CHECK(vkCreateDescriptorPool(dev, &dpci, NULL, &dp));
    VkDescriptorSetAllocateInfo dsai = { .sType = VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO,
                                         .descriptorPool = dp, .descriptorSetCount = 1, .pSetLayouts = &dsl };
    VkDescriptorSet ds;
    CHECK(vkAllocateDescriptorSets(dev, &dsai, &ds));
    VkDescriptorBufferInfo dbi = { buf, 0, VK_WHOLE_SIZE };
    VkWriteDescriptorSet wds = { .sType = VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET, .dstSet = ds,
                                 .descriptorCount = 1, .descriptorType = VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,
                                 .pBufferInfo = &dbi };
    vkUpdateDescriptorSets(dev, 1, &wds, 0, NULL);

    VkCommandPoolCreateInfo cpi = { .sType = VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO,
                                    .flags = VK_COMMAND_POOL_CREATE_RESET_COMMAND_BUFFER_BIT,
                                    .queueFamilyIndex = qf };
    VkCommandPool cp;
    CHECK(vkCreateCommandPool(dev, &cpi, NULL, &cp));
    VkCommandBufferAllocateInfo cbai = { .sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO,
                                         .commandPool = cp, .level = VK_COMMAND_BUFFER_LEVEL_PRIMARY,
                                         .commandBufferCount = 1 };
    VkCommandBuffer cb;
    CHECK(vkAllocateCommandBuffers(dev, &cbai, &cb));
    VkFenceCreateInfo fci = { .sType = VK_STRUCTURE_TYPE_FENCE_CREATE_INFO };
    VkFence fence;
    CHECK(vkCreateFence(dev, &fci, NULL, &fence));

    /* One dispatch over the buffer with the given push constants, timed. */
    #define RUN(pcv, seconds) do { \
        VkCommandBufferBeginInfo bi = { .sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO, \
                                        .flags = VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT }; \
        CHECK(vkBeginCommandBuffer(cb, &bi)); \
        vkCmdBindPipeline(cb, VK_PIPELINE_BIND_POINT_COMPUTE, pipe); \
        vkCmdBindDescriptorSets(cb, VK_PIPELINE_BIND_POINT_COMPUTE, pl, 0, 1, &ds, 0, NULL); \
        vkCmdPushConstants(cb, pl, VK_SHADER_STAGE_COMPUTE_BIT, 0, sizeof(pcv), &(pcv)); \
        vkCmdDispatch(cb, n / 256, 1, 1); \
        VkMemoryBarrier mb = { .sType = VK_STRUCTURE_TYPE_MEMORY_BARRIER, \
                               .srcAccessMask = VK_ACCESS_SHADER_WRITE_BIT, \
                               .dstAccessMask = VK_ACCESS_HOST_READ_BIT }; \
        vkCmdPipelineBarrier(cb, VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT, VK_PIPELINE_STAGE_HOST_BIT, \
                             0, 1, &mb, 0, NULL, 0, NULL); \
        CHECK(vkEndCommandBuffer(cb)); \
        VkSubmitInfo si = { .sType = VK_STRUCTURE_TYPE_SUBMIT_INFO, .commandBufferCount = 1, \
                            .pCommandBuffers = &cb }; \
        double t0_ = now(); \
        CHECK(vkQueueSubmit(q, 1, &si, fence)); \
        CHECK(vkWaitForFences(dev, 1, &fence, VK_TRUE, UINT64_MAX)); \
        (seconds) = now() - t0_; \
        CHECK(vkResetFences(dev, 1, &fence)); \
    } while (0)

    printf("{\"bench\":\"vkcompute-info\",\"device\":\"%s\",\"api\":\"%u.%u.%u\"}\n", props.deviceName,
           VK_API_VERSION_MAJOR(props.apiVersion), VK_API_VERSION_MINOR(props.apiVersion),
           VK_API_VERSION_PATCH(props.apiVersion));

    /* Correctness: GPU vs CPU reference for a short loop. */
    for (uint32_t i = 0; i < n; i++) v[i] = (float)(i % 1000) * 1e-3f;
    double s;
    RUN(check_pc, s);
    double max_err = 0;
    for (uint32_t i = 0; i < n; i++) {
        float x0 = (float)(i % 1000) * 1e-3f, x1 = x0 + 0.125f, x2 = x0 + 0.25f, x3 = x0 + 0.375f;
        for (uint32_t k = 0; k < check_pc.iters; k++) {
            x0 = fmaf(x0, check_pc.a, check_pc.b); x1 = fmaf(x1, check_pc.a, check_pc.b);
            x2 = fmaf(x2, check_pc.a, check_pc.b); x3 = fmaf(x3, check_pc.a, check_pc.b);
        }
        double err = fabs((double)v[i] - (double)(x0 + x1 + x2 + x3));
        if (err > max_err) max_err = err;
    }
    const int ok = max_err < 1e-4;
    printf("{\"bench\":\"vkcompute\",\"test\":\"correctness\",\"max_abs_err\":%.3g,\"ok\":%s}\n",
           max_err, ok ? "true" : "false");

    /* Throughput. */
    double *t = calloc(reps, sizeof(double));
    RUN(bench_pc, s);                                  /* warm-up */
    for (int r = 0; r < reps; r++) RUN(bench_pc, t[r]);
    qsort(t, reps, sizeof(double), cmpd);
    const double flop = (double)n * iters * 4 * 2;
    printf("{\"bench\":\"vkcompute\",\"test\":\"fma_f32\",\"iters\":%u,\"reps\":%d,"
           "\"best_TFLOPS\":%.3f,\"median_TFLOPS\":%.3f,\"median_ms\":%.3f}\n",
           iters, reps, flop / t[0] / 1e12, flop / t[reps / 2] / 1e12, t[reps / 2] * 1e3);

    /* Submit+wait round trip with an empty-ish dispatch: per-sync overhead. */
    const struct pc tiny = { 0, 1.0f, 0.0f };
    double lat[64];
    for (int r = 0; r < 64; r++) RUN(tiny, lat[r]);
    qsort(lat, 64, sizeof(double), cmpd);
    printf("{\"bench\":\"vkcompute\",\"test\":\"submit_wait_roundtrip\",\"p50_us\":%.1f,\"p90_us\":%.1f}\n",
           lat[32] * 1e6, lat[57] * 1e6);

    vkDeviceWaitIdle(dev);
    vkDestroyDevice(dev, NULL);
    vkDestroyInstance(inst, NULL);
    return ok ? 0 : 1;
}
