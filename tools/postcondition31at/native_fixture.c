/* SPDX-License-Identifier: MIT */
/* Differential oracle: only synthetic workspace captures, no live dispatch. */
#include "reader.h"
#include <stdio.h>
#include <string.h>

int main(int argc, char **argv) {
    if (argc != 4) return 2;
    Snapshot baseline, candidate;
    ComparisonKey key;
    Profile profile = {0};
    strcpy(profile.sha, "27e265da1fac084db457f084dcd8f52b63e5daa1629575a13de64d68f24b4ecc");
    /* All three original readers independently require WORKSPACE_ROOT. */
    bool accepted = parse_snapshot(argv[1], &baseline, true) &&
        parse_snapshot(argv[2], &candidate, true) &&
        load_comparison_key(argv[3], true, &key) &&
        validate_snapshot(&candidate, &baseline, &profile, &key, "candidate", true);
    puts(accepted ? "ACCEPTED" : "REFUSED");
    return accepted ? 0 : 1;
}
