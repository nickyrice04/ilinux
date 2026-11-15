/* SPDX-License-Identifier: MIT */
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <errno.h>

#define INPUT_LIMIT 65536
bool old_policy_parse(const unsigned char *data, size_t length);
bool proposed_policy_parse(const unsigned char *data, size_t length);
unsigned old_policy_failure(void);
unsigned proposed_policy_failure(void);

static int result(bool input, bool old, bool proposed) {
    printf("{\"schema\":\"ilinux31ao-native-policy-parse-v1\","
           "\"scope\":\"DESKTOP_SYNTAX_ONLY\",\"input_within_bounds\":%s,"
           "\"old_parser_accepted\":%s,\"proposed_parser_accepted\":%s,"
           "\"old_failure_line\":%u,\"proposed_failure_line\":%u,"
           "\"read_only\":true,\"admission_verified\":false,"
           "\"native_ready\":false,\"policy_values_returned\":false,"
           "\"identifiers_returned\":false}\n",
           input ? "true" : "false", old ? "true" : "false",
           proposed ? "true" : "false", input ? old_policy_failure() : 0,
           input ? proposed_policy_failure() : 0);
    return input ? 0 : 2;
}

int main(int argc, char **argv) {
    if (argc == 1 || (argc == 2 && !strcmp(argv[1], "--help"))) {
        puts("Inert by default. --stdin checks bounded private policy syntax only.");
        return 0;
    }
    if (argc != 2 || strcmp(argv[1], "--stdin")) return result(false, false, false);
    unsigned char *data = malloc(INPUT_LIMIT + 1);
    if (!data) return result(false, false, false);
    size_t length = 0;
    bool ok = false;
    while (length <= INPUT_LIMIT) {
        ssize_t count = read(STDIN_FILENO, data + length, INPUT_LIMIT + 1 - length);
        if (count < 0 && errno == EINTR) continue;
        if (count < 0) break;
        if (!count) {ok = length > 0 && length <= INPUT_LIMIT; break;}
        length += (size_t)count;
        if (length > INPUT_LIMIT) break;
    }
    bool old = ok && old_policy_parse(data, length);
    bool proposed = ok && proposed_policy_parse(data, length);
    memset(data, 0, INPUT_LIMIT + 1);
    free(data);
    return result(ok, old, proposed);
}
