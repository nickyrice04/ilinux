# Job 094: direct31AH Aura offline build

This job's executable recipe is `build-aura.sh`. It is invoked by the parent
isolated Linux job with three paths: an exact extracted Aura source tree, a new
workspace build directory, and an output directory. It does not launch a VM,
download sources, install packages, enroll a boot object or access physical USB.

The source archive must be the pinned public Aura
`bd9f3e8273dc79ae9095c19c2c4f32218446ad4e`. Its selected critical file Git blobs
are checked before a copy is compiled; the parent also authenticates the full
archive SHA-256. Both source variants use deterministic version tags and source
epoch. Locked/offline Cargo requires its dependency cache before this job starts.
The compiler and linker are Clang/LLD; native GNU `objcopy` is selected explicitly
because the VM's LLVM package does not provide `llvm-objcopy`. The result records
the exact tool versions and Make variables.

See the [experiment documentation](../../../kernel/experiments/direct31ah/aura/README.md)
for padding/entry contracts, exact file roles, optional CDC delta, source licenses
and native limits. Source-based reproduction does not claim byte identity with
the operator's unpublished complete build or that the optional local patch ran
on hardware. Build results remain separate from format checks and native tests.
