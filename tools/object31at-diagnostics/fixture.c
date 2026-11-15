/* SPDX-License-Identifier: MIT */
#include "diagnostics.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int refused31at(void) {
    puts("{\"schema\":\"ilinux31at-object-diagnostics-v1\",\"status\":\"REFUSED\","
        "\"scope\":\"WORKSPACE_FIXTURE_ONLY\",\"read_only\":true,"
        "\"host_queries\":false,\"native_ready\":false,\"private_values_returned\":false}");
    return 2;
}

int main(int argc, char **argv) {
    if (argc == 1) {
        puts("{\"schema\":\"ilinux31at-object-diagnostics-v1\",\"status\":\"INERT\","
            "\"scope\":\"WORKSPACE_FIXTURE_ONLY\",\"read_only\":true,"
            "\"host_queries\":false,\"native_ready\":false}");
        return 0;
    }
    if (argc == 2 && !strcmp(argv[1],"--help")) {
        puts("Usage: object31at-diagnostics --fixture WORKSPACE_BUILD_FILE");
        return 0;
    }
    if (argc != 3 || strcmp(argv[1],"--fixture")) return refused31at();
    const char prefix[] = WORKSPACE_ROOT "/build/";
    if (strncmp(argv[2],prefix,sizeof(prefix)-1)) return refused31at();
    /* The original reader refuses every symlink/dot component, special files,
     * oversize input and concurrent inode/size/time changes; no live fallback. */
    uint8_t *data = NULL;
    size_t length = 0;
    if (!read_file(argv[2],FILE_LIMIT,true,&data,&length)) return refused31at();
    ObjectDiagnostics31AT d;
    object_diagnostics31at((Bytes){data,length},&d);
    print_object_diagnostics31at(&d);
    free(data);
    return 0;
}
