/* SPDX-License-Identifier: MIT */
static u8 *read_file(const char *path, size_t limit, size_t *bytes)
{
    FILE *stream = fopen(path, "rb");
    assert(stream && !fseek(stream, 0, SEEK_END));
    long length = ftell(stream);
    assert(length > 0 && (unsigned long)length <= limit && !fseek(stream, 0, SEEK_SET));
    /* Source's scanner intentionally has an unknown length. Our file/canonical
     * verifier bounds input first, and this guard tail makes its lookahead safe. */
    u8 *data = calloc(1, (size_t)length + 4096);
    assert(data && fread(data, 1, (size_t)length, stream) == (size_t)length);
    assert(!fclose(stream));
    *bytes = (size_t)length;
    return data;
}
int main(int argc, char **argv)
{
    assert(argc == 7);
    input = read_file(argv[1], 32U << 20, &input_size);
    expected_image = read_file(argv[2], 64U << 20, &image_bytes);
    expected_dtb = read_file(argv[3], 4U << 20, &dtb_bytes);
    expected_initrd = read_file(argv[4], 8U << 20, &initrd_bytes);
    os_firmware.version = !strcmp(argv[5], "26.6.2") ? V26_6_2 : 0;
    failure = atoi(argv[6]);
    heap = (u8 *)(((uintptr_t)heap_storage + (2U << 20) - 1) & ~((uintptr_t)(2U << 20) - 1));
    int result = payload_run();
    enum stage1_payload_action action = stage1_proxy_payload_action(
        STAGE1_PROXY_TIMEOUT, result == 0, false, false);
    fprintf(stdout, "{\"scope\":\"PINNED_PUBLIC_PAYLOAD_MOCK_ONLY\",\"payload_result\":%d,"
            "\"profile_26_6_2\":%s,\"selected_fdt_rank\":%d,\"initrd_in_heap\":%s,"
            "\"kernel_in_heap\":%s,\"heap_bytes_reserved\":%zu,\"prepare_calls\":%d,"
            "\"boot_calls\":%d,\"chosen_calls\":%d,\"no_carrier_payload_action\":%d,\"events\":[", result,
            os_firmware.version == V26_6_2 ? "true" : "false", fdt_rank,
            initrd_set && !invalid_initrd ? "true" : "false",
            kernel && in_heap(kernel, image_bytes) ? "true" : "false", heap_used,
            prepare_calls, boot_calls, chosen_calls, action);
    for (unsigned i = 0; i < event_count; i++) fprintf(stdout, "%s%u", i ? "," : "", events[i]);
    fprintf(stdout, "],\"native_tested\":false,\"hardware_hooks_mocked\":true}\n");
    return 0;
}
