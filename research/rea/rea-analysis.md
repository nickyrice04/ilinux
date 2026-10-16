# REA ("Reverse Engineer Anything"): security and integration analysis

| | |
|---|---|
| **Status** | Research only. Nothing from REA was installed or executed, and no configuration was changed. Every command in the [Proposed project-scoped integration plan](#proposed-project-scoped-integration-plan-not-executed) is **NOT EXECUTED** and needs explicit approval first. |
| **Date** | 2026-10-11 |
| **Subject** | <https://github.com/morluto/rea>, `main` @ `b777e5d4d8` (2026-10-11 21:44 UTC), and npm `rea-agents@6.4.0` (published 2026-10-11 04:02 UTC from commit `a56f7bb6`) |
| **Method** | GitHub REST API reads (`gh api` contents, trees, commits, releases, compare, code search), npm registry metadata (`npm view rea-agents --json`), official Claude Code docs, and read-only host probes (`command -v`, version flags, `csrutil status`, `DevToolsSecurity -status`, path-existence checks). Source files were read only as data. |
| **Release vs main** | `main` is **184 commits / 300+ files ahead** of the `rea-agents-6.4.0` tag. The setup files that matter were diffed against the tag. For Claude Code, the paths, registration shape, skill files, backups and Hopper installer are the same in 6.4.0. Differences are noted where they matter. |

---

## Executive summary

- **What it is.** REA is a TypeScript/Node.js CLI plus a **stdio MCP server**. It's published on npm as `rea-agents` and in the MCP Registry as `io.github.morluto/rea`. It gives an agent **170 tools (npm 6.4.0) or 172 tools (`main`)**:
  - native decompilation and disassembly through **Hopper, headless Ghidra, or IDA**;
  - inspection of Mach-O files, code signatures, plists and app bundles;
  - analysis of JS/Electron, .NET, Android/ADB, web pages over CDP, WASM, EVM and firmware;
  - optional *runtime* observation: LLDB call tracing of processes REA launches itself, PTY process capture, Electron and browser scenarios, and Accessibility-based UI capture.
- **What `npx rea-agents setup` changes.** It writes **user-scope (global)** configuration. For Claude Code that is a top-level `mcpServers.rea` entry in **`~/.claude.json`** plus a 7-file skill in **`~/.claude/skills/reverse-engineer-anything/`**, with `*.rea.backup` copies of anything it changes.
  - It **never** installs Ghidra, Java, Python, Homebrew or radare2, and it never uses `sudo` on macOS.
  - In a separate prompt that defaults to **No**, it can download **Hopper** (commercial; demo available) into `~/Applications`.
- **Red flags found:** no telemetry SDKs, no install-time lifecycle scripts, no obfuscation (the bundle sets `minify: false`), no auto-update, and no published advisories. Releases use npm trusted publishing (OIDC) with SLSA provenance.
- **Main risks:**
  1. Setup writes global config by default.
  2. By its own `SECURITY.md`, REA is "not a sandbox". Five tools run target code, six change attached Android devices, and the server does not gate any of them; approval is left to the client.
  3. Releases move very fast: v3.2.1 to v6.4.0 in 8 days, and `main` is already 184 commits past a release about 18 hours old.
  4. The npm package has a single maintainer.
  5. Content from analysed targets can carry prompt injection.
- **macOS security.** No feature requires disabling SIP; `csrutil` appears nowhere in the codebase. LLDB tracing of hardened-runtime targets that lack `com.apple.security.get-task-allow` fails closed with `debugger-attach-denied`. That covers all Apple platform binaries and most notarized apps.
- **Project scope.** `rea setup` has **no project-scope option**. The registration is a plain stdio command, though, so an exact project-scoped equivalent (`.mcp.json`) can be derived; it's given below.
- **This host.**
  - Ready: Node 26.5.0, npm 11.17.0, Xcode 27 / LLDB / `swiftc`, Google Chrome.
  - Missing: every deep-analysis engine. There's no JDK, Ghidra, Hopper or IDA, so the decompile/disassemble tools would report "unavailable". The Mach-O, plist, signature, artifact, JS and .NET tools would still work.

---

## 1. Repository profile

| Item | Value |
|---|---|
| Purpose | "Reverse engineer anything with agents, from app behavior down to native binaries." It lets an agent investigate a shipped app or binary without its source and return evidence-backed findings. |
| Homepage / docs | <https://rea.tools> · `docs/` in the repo |
| License | MIT |
| Primary language | TypeScript 82.6%. Also JavaScript 9.9%, HTML 2.9%, Java 1.7% (Ghidra/JADX bridges), Python 1.6% (Hopper/LLDB/pwntools/mitmproxy bridges), C++, CSS, Swift (macOS UI helper), C, Shell. |
| Repo size | 48,219 KB as GitHub reports it; about 3,100 tree entries |
| Created | 2026-04-14 |
| Last push / commit | 2026-10-11 21:50 UTC / `b777e5d4d8` "fix(wasm): preserve debug module names in WABT output (#1967)" |
| Stars / forks / watchers | **100,864** / 22,172 / 312. That's very high for a 6-month-old repo. The README also disclaims crypto tokens that use the REA name; see the risk notes in §7. |
| Open issues + PRs | 164 |
| Maintainer | `morluto` (owner, 1,250 commits; sole npm maintainer) |
| Top contributors | N0zoM1z0 (457), kaoru0822-kitauji (379), rudycelekli (85), github-actions[bot] (41); 50+ contributors in total |
| Releases | Tags `rea-agents-X.Y.Z`, cut by release-please. Recent: 6.4.0 (10-11), 6.3.0 (10-09), 6.2.0 (10-09), 6.1.0 (10-09), 6.0.0 (10-08), 5.0.0 (10-07), 4.1.0 (10-06), 4.0.1/4.0.0 (10-05), 3.2.1 (10-03). |
| Commit velocity | ≥100 commits in the last 7 days. Many are pushed straight to `main` by the owner as **unsigned** commits; PR merges are GitHub-verified. |
| npm package | `rea-agents@6.4.0`: 31 versions since 2026-07-12; 1,161 files, 7.78 MB unpacked; `integrity sha512-Vj1zWfSl…EQ==`. Published by **GitHub Actions OIDC** (`npm-oidc-no-reply@github.com`) with an **SLSA v1 provenance** attestation. |
| MCP Registry | `io.github.morluto/rea`; `server.json` declares npm `rea-agents`, `runtimeHint: npx`, `transport: stdio`, argument `mcp`. |
| Advisories | 0 in the GitHub Advisory DB for npm `rea-agents`; 0 repository security advisories |

### Architecture (as read from source)

- **Dispatcher, `scripts/rea.mjs`** (the `bin` for both `rea` and `rea-agents`):
  - `rea mcp` / `rea --mcp` starts the stdio MCP server. That's `dist/mcp/main.js` on `main` and `dist/main.js` in 6.4.0.
  - `rea mcp doctor` starts an MCP self-check.
  - Anything else runs the CLI (`dist/cli.js`, built on the `incur` CLI framework). The CLI exposes the same workflows as the MCP tools, plus `setup`, `doctor`, `update` and `uninstall`.
- **Layers in `src/`:**
  - `domain/` holds pure models.
  - `application/` holds services, including setup, doctor, update and uninstall.
  - `contracts/` holds tool schemas plus the effect audit in `toolEffects.ts`.
  - `server/` holds the MCP server and admission.
  - Provider adapters: `hopper/`, `ghidra/`, `ida/`, `jeb/`, `native/` (LLDB, pwntools, pwndbg), `browser/` (CDP/Playwright), `inspector/` (V8), `javascript/`, `dotnet/`, `android/`, `adb/`, `apktool/`, `wasm/`, `evm/`, `firmware/`, `process/` (PTY capture) and `windows/`.
- **Bridges**, which REA runs inside external tools:
  - `bridge/ghidra/*.java`: a Ghidra HeadlessScript bridge.
  - `bridge/hopper_bridge.py`: runs inside Hopper's Python and talks over an `AF_UNIX` socket.
  - `bridge/native/rea_lldb_tracer.py`: loaded with `lldb --batch -o "command script import …"`.
  - `bridge/native/*.swift`: a UI helper compiled per scenario.
  - `scripts/electron-active-hook.cjs`, plus Linux-only pwntools, pwndbg and mitmproxy helpers.
- **Results:** every result is an "Evidence" record. Records can be retained and referenced, exported or imported as bundles, cached as snapshots, and tracked as an "unknowns" ledger.
- **Bridge security:** each provider bridge session uses a random capability token over a current-user Unix socket. Tokens travel through private descriptors, not argv or env (`SECURITY.md`).

---

## 2. What `npx rea-agents setup` does, step by step

Traced through `src/cli/setupCommands.ts`, `src/cli/interactiveSetup.ts`, `src/application/Setup*.ts`, `SupportedClients.ts`, `ClientConfigurationDocument.ts`, `ClientRegistrationIdentity.ts`, `MacHopper.ts`, `HopperDownload.ts` and `Doctor.ts`.

### 2.1 Before any REA code runs (npx itself)

1. `npx` resolves `rea-agents` (currently `@latest` = 6.4.0) and asks "Ok to proceed?". It then downloads the package and its **148 production packages** into `~/.npm/_npx/<hash>/node_modules`, with tarballs in `~/.npm/_cacache`. That is a write to your home directory, though not to any config file.
2. **No lifecycle scripts run.**
   - `rea-agents` declares only `prepare` and `prepack`, and npm does not run those when installing a registry tarball. `prepare.mjs` only installs husky when a `src/` checkout is present.
   - No production dependency in `package-lock.json` has `hasInstallScript`. The only two packages that do, `fsevents` and `esbuild`, are dev-only.
   - There is **no `postinstall`**.
3. The one native addon loaded on macOS is the prebuilt **`@lydell/node-pty-darwin-arm64`**, an optional platform package with no install script. The tarball also ships a CI-built `native/windows/build/rea-windows-x64.node`, which is only loaded on Windows.

### 2.2 Setup workflow

1. **Node gate.** Setup refuses to run unless Node is `^22.19 || ^24.11 || >=26`.
2. **Initial `doctor` (read-only).** It probes the host locally (for example `sw_vers -productVersion`) and inspects configured providers:
   - Hopper at its default path or `HOPPER_LAUNCHER_PATH`;
   - Ghidra and its JDK through `GHIDRA_INSTALL_DIR` / `JAVA_HOME`;
   - IDA through `REA_IDA_MCP_CONFIG`.

   It also reads existing REA registrations in all 17 supported client config files, and existing skills. It makes **no network calls**.
3. **Client detection.** A client counts as "detected" if its config file or marker path exists. Claude Code is detected through `~/.claude.json` or `~/.claude`, or the same paths under `$CLAUDE_CONFIG_DIR`.
4. **Interactive selection**, which only happens when stdin, stdout and stderr are all TTYs:
   - Setup shows a multi-select of agents. Clients that already have an REA registration are pre-selected. Newly detected clients are **not** pre-selected.
   - If any agent is selected, the REA skill is added automatically, with no separate prompt. If none is selected, setup asks "Install the guided REA skill for CLI use?" (default **No**).
   - **Hopper** is proposed only on macOS ≥ 12 when no provider environment was detected (no Ghidra or Hopper configured). The prompt is "Install Hopper for deep binary analysis?" (default **No**).
5. **Preflight plan.** Setup prints each action with its exact target path, backup path, command line, network origins and integrity evidence. A malformed or unsafe existing config file (for example a symlink owned by someone else) **blocks the whole transaction** before anything is written.
6. **Confirm.** The prompt is "Apply these N changes?" (default Yes). Declining or pressing Ctrl-C changes nothing.
7. **Apply**, in this order:
   1. *(Only if Hopper was approved.)* Run the macOS Hopper installer (§2.4).
   2. **Register each selected client.** For Claude Code (JSON format) setup writes a top-level `mcpServers.rea` entry to `~/.claude.json`:
      ```json
      { "mcpServers": { "rea": { "command": "npx", "args": ["-y", "rea-agents@6.4.0", "mcp"] } } }
      ```
      - An `env` object is added only if provider variables were detected, for example `GHIDRA_INSTALL_DIR`, `JAVA_HOME` or `HOPPER_LAUNCHER_PATH`. Valid existing `REA_*` overrides are kept.
      - Top-level `mcpServers` in `~/.claude.json` is Claude Code's **user scope**, so REA would load in **every project**.
      - When setup runs from a global install instead of npx, the command is the absolute path of `rea.mjs` plus `mcp`.
      - The write is a JSONC-preserving edit, made with `write-file-atomic` at mode `0600`. Setup reads the file back to verify it and restores the original if the check fails.
      - On first change it makes a **one-time backup** at `~/.claude.json.rea.backup`, copied with `COPYFILE_EXCL`. Later runs never refresh that backup.
   3. **Install the skill.** Seven files go to `~/.claude/skills/reverse-engineer-anything/`: `SKILL.md` plus `references/{connection-and-recovery,native-and-artifacts,javascript-applications,android-applications,runtime-observation,evidence-workflows}.md`. Each changed file gets a `*.rea.backup` copy. Writes are atomic, with rollback on failure.
   4. A final read-only doctor runs, then setup prints "restart your agent".
8. **Non-interactive flags.** These are `--client <id>` (repeatable), `--all-detected`, `--skill=false`, `--skill-client <id>`, `--dry-run`, `--yes`/`-y`, `--install-hopper`, `--accessible` and `--json`.
   - `--dry-run --json` returns the plan without writing anything.
   - Without an explicit scope, `--yes` only refreshes **existing** REA registrations.

### 2.3 Files `setup` can write

| Path | When | Notes |
|---|---|---|
| `~/.claude.json` (`mcpServers.rea`) | Claude Code selected | **Global, user scope.** Atomic rewrite of a large, live file that Claude Code itself writes constantly. Setup takes no lock, so a running Claude Code instance could race the write; see §7. |
| `~/.claude.json.rea.backup` | First change to `~/.claude.json` | Never refreshed afterwards |
| `~/.claude/skills/reverse-engineer-anything/**` (7 files, plus `*.rea.backup`) | Claude Code selected, skill enabled | Personal skill, loaded in every project |
| `~/Library/Application Support/Claude/claude_desktop_config.json` | Claude Desktop selected | Detected on this host |
| `~/.copilot/mcp-config.json` | Copilot CLI selected | Detected on this host |
| `~/Library/Application Support/Code/User/mcp.json` | VS Code selected | Detected on this host |
| `~/.agents/skills/reverse-engineer-anything/**` | Any client without its own skill dir (e.g., Claude Desktop, Copilot, VS Code) | Shared skill directory |
| Other clients' files (`~/.codex/config.toml`, `~/.cursor/mcp.json`, `~/.gemini/settings.json`, …) | Only if those clients are selected | Not detected on this host |
| `~/Applications/Hopper Disassembler.app` | Hopper approved | Staged as `….app.rea-stage`, then renamed into place |

Setup writes **nothing** to `~/.claude/settings.json`, to any project `.mcp.json`, or to `/Library`. It doesn't touch shell profiles or `PATH`.

### 2.4 What setup downloads or installs

- **Nothing**, unless you approve Hopper. Setup never downloads or installs Ghidra, Java, Python packages, radare2/rizin, Homebrew formulae, or Node/npm itself ("never upgrades Node.js, npm, or Homebrew").
- **Hopper installer on macOS** (`MacHopper.ts`):
  1. `GET https://www.hopperapp.com/include/files-api.php?request=releases&public=true`.
  2. Download the DMG. The URL must start with `https://www.hopperapp.com:443/downloader/public/`, and the file is capped at 100 MB.
  3. Check the byte length and **SHA-1** against values from that **same** metadata endpoint.
  4. `hdiutil attach -readonly -nobrowse`.
  5. `codesign --verify --deep --strict`, then check that the bundle ID is `com.cryptic-apps.hopper-web-4`.
  6. `ditto` into `~/Applications/Hopper Disassembler.app`.
  7. `open` the app so you can pick the demo or activate a license.

  It uses no Homebrew and no admin rights. On Linux the same feature runs `apt-get`, `dnf` or `pacman` through `pkexec`; it never uses `sudo`.

### 2.5 Network calls and telemetry

| Origin | Why | When |
|---|---|---|
| `registry.npmjs.org` | npx fetches the package and its dependencies | First `npx` run, and on cache misses |
| `www.hopperapp.com` | Hopper metadata and DMG | Only if Hopper install is approved |
| `api.github.com` | `install.sh` looks up the latest release tag | Only if the optional `curl … \| bash` installer is used |
| npm registry, via `npm view` and `npm install -g` | `rea update` | Only when you run `rea update` manually |

- **No telemetry or analytics** was found:
  - There are no analytics SDKs (PostHog, Mixpanel, Amplitude, Segment: 0 hits).
  - The "sentry" code-search hits are false positives on `Entry` tokens.
  - The "telemetry" hits in shipped code are local diagnostic structs (`HopperDiagnostics.ts`, `GhidraClientTypes.ts`).
  - Logs go to **stderr** only, as pino JSON.
  - The README states "REA analyzes targets locally."
- MCP server startup (`src/main.ts`, `src/main/startup.ts`) makes no network calls.
- Some **tools** use the network by design. Browser and CDP tools do, `trace_web_module_imports` and source-map fetching do when requested, ADB tools talk to the adb server, JEB and IDA tools talk to your local MCP endpoints, and the processes or apps that REA runs can do whatever they like.

### 2.6 Related entry points

- **`rea doctor`** is strictly read-only. Use `--client`, `--provider` and `--skill` to scope it.
- **`rea update`** is manual, never automatic. It updates only the global npm or Bun installation that owns the running CLI, then prints a scoped setup command; it doesn't rewrite registrations itself.
- **`rea uninstall`** removes REA-owned registrations and skill files. Adding `--purge-data` also removes `~/.rea/{cache,state}`.
- **`install.sh`** (`curl -fsSL …/install.sh | bash`) runs `npm install --global rea-agents@<latest>` and then starts `rea setup` interactively. It's optional; **don't use it**.

---

## 3. MCP server

- **Transport:** stdio only, via `@modelcontextprotocol/server@2.3.1` `serveStdio`. There is no HTTP or SSE listener. For IDA and JEB, REA acts as an MCP *client* to servers you start yourself.
- **Launch:**
  - The client spawns `npx -y rea-agents@<ver> mcp` (what setup and the Registry write).
  - Or it spawns `node <pkg>/scripts/rea.mjs mcp`, or `rea mcp` from a global install.
- **Catalog:**
  - `tools/list` always returns the **complete** catalog: 170 tools in 6.4.0, 172 on `main`.
  - Availability for the current target and provider is reported by `binary_session.tool_availability`.
  - Annotations (`readOnlyHint`, `destructiveHint`, `idempotentHint`, `openWorldHint`) are derived from a per-tool effect audit in `src/contracts/toolEffects.ts`.
  - The docs state that REA "does not require permission grants or per-call approval flags … MCP clients control their own confirmation UI."
- **Context cost:** 170+ tools is large. Claude Code's MCP **tool search** is on by default and defers tool definitions until they're needed, so mainly the names load. No `alwaysLoad` setting is needed.
- **Prompts (6):** `investigate_feature`, `compare_application_versions`, `verify_reconstruction`, `trace_crash`, `audit_residual_unknowns` and `prepare_bounded_process_capture`. In Claude Code they appear as `/mcp__rea__<name>`.

### 3.1 Tool catalog by family (172 on `main`)

| Family (count) | Tools | Purpose |
|---|---|---|
| Session & Evidence (13) | `open_binary`, `close_binary`, `binary_session`, `get_navigation_context`, `inspect_address_context`, `inspect_analysis_view`, `export_evidence_bundle`, `get_evidence_bundle`, `import_evidence_bundle`, `list_unknowns`, `record_unknown`, `update_unknown`, `verify_unknown_resolution` | Bind a target to a provider, report catalog and tool availability, and manage Evidence and the unknowns ledger |
| Native static analysis (48) | `binary_overview`, `analyze_function`, `batch_decompile`, `procedure_pseudo_code`, `procedure_assembly`, `read_function_instructions`, `procedure_info`, `procedure_callers`, `procedure_callees`, `procedure_references`, `procedure_address`, `resolve_containing_procedure`, `search_procedures`, `list_procedures`, `list_segments`, `list_strings`, `search_strings`, `list_names`, `address_name`, `xrefs`, `find_xrefs_to_name`, `get_call_graph`, `trace_call_path`, `trace_feature`, `resolve_native_call_targets`, `inspect_native_instruction`, `inspect_native_data_type`, `inspect_native_api`, `inspect_native_load_image`, `inspect_native_dispatch_metadata`, `trace_native_values`, `trace_native_ui_action`, `get_objc_classes`, `get_objc_protocols`, `analyze_swift_types`, `read_bytes`, `address_to_file_offset`, `inspect_pe_resources`, `current_document`, `current_address`, `current_procedure`, `list_documents`, `goto_address`, `next_address`, `prev_address`, `comment`, `inline_comment`, `list_bookmarks` | Decompilation, disassembly, xrefs and call graphs through **Hopper, Ghidra or IDA** |
| Native annotation (7) | `annotate_native_function`, `set_address_name`, `set_addresses_names`, `set_comment`, `set_inline_comment`, `set_bookmark`, `unset_bookmark` | Rename and comment in the provider database. Ghidra edits are ephemeral and never touch executable bytes. |
| Apple / artifacts (12) | `inspect_macho`, `inspect_signature`, `inspect_plist`, `list_architectures`, `demangle_swift`, `inspect_asset_catalog`, `decode_interface_builder`, `inspect_keyed_archive`, `trace_dylib_resolution`, `inspect_artifact`, `extract_artifact`, `project_apple_application_graph` | Mach-O, codesign, entitlements, bundles, DMG/IPA/ZIP. These need no engine; some spawn local helpers, including `hdiutil` for DMGs. |
| Runtime on macOS (5) | `observe_native_calls`, `observe_native_ui`, `capture_native_ui_scenario`, `capture_process_scenario`, `compare_process_captures` | LLDB call tracing, AX/ScreenCaptureKit UI capture, PTY process runs |
| Other formats (6) | `inspect_binary_layout`, `inspect_recorded_crash`, `inspect_wasm_artifact`, `inspect_evm_interface`, `inspect_firmware_regions`, `extract_firmware` | Mostly Linux x64 helpers (pwntools, binwalk/unblob). WASM needs a WABT you supply yourself. |
| JavaScript / Electron (13) | `analyze_javascript_application`, `recover_javascript_sources`, `reconcile_javascript_runtime`, `trace_application_feature`, `trace_javascript_semantics`, `compare_application_versions`, `compare_source_to_bundle`, `compare_javascript_export_shapes`, `list_javascript_runtime_targets`, `observe_javascript_runtime`, `list_electron_targets`, `inspect_electron_page`, `capture_electron_scenario` | ASAR/module graphs, source maps, IPC/preload, V8 inspector |
| Web / CDP (15) | `list_browser_targets`, `inspect_web_page`, `analyze_web_bundle`, `observe_web_session`, `discover_webmcp_tools`, `capture_web_screenshot`, `compare_web_screenshots`, `compare_web_captures`, `capture_browser_scenario`, `inspect_web_event_listeners`, `trace_web_source_location`, `trace_web_module_imports`, `export_web_scripts`, `observe_web_execution`, `inspect_web_network_capture` | Passive CDP attach to a browser *you* started, and Playwright scenarios |
| .NET (7) | `inspect_managed_artifact`, `inspect_managed_members`, `inspect_managed_native_boundaries`, `compare_managed_members`, `verify_managed_native_boundaries`, `import_managed_reconstruction`, `project_managed_application_graph` | Static metadata and CIL |
| Android / JEB / Harmony (13) | `inspect_android_package`, `search_android_classes`, `inspect_android_class`, `inspect_android_method`, `trace_android_references`, `project_android_application_graph`, `inspect_apktool_client`, `decode_android_resources`, `inspect_jeb_client`, `open_jeb_project`, `list_jeb_units`, `decompile_jeb_item`, `project_harmony_application_graph` | JADX (headless, needs a JDK), Apktool, JEB |
| ADB (24) | `inspect_adb_client`, `list_adb_devices`, `inspect_adb_device`, `list_adb_packages`, `inspect_adb_package`, `resolve_adb_packages`, `pull_adb_package`, `pull_adb_file`, `push_adb_file`, `read_adb_logcat`, `capture_adb_screen`, `list_adb_processes`, `list_adb_directory`, `list_adb_features`, `list_adb_services`, `inspect_adb_display`, `inspect_adb_window`, `read_adb_setting`, `collect_adb_bugreport`, `install_adb_package`, `uninstall_adb_package`, `start_adb_app`, `start_adb_activity`, `stop_adb_app` | Android device or emulator, through an `adb` you supply |
| Comparison / reconstruction (9) | `compare_artifacts`, `compare_functions`, `compare_bundles`, `find_changed_behavior`, `build_call_path`, `correlate_static_and_runtime`, `verify_reconstruction`, `build_reconstruction_obligation_ledger`, `evaluate_reconstruction_coverage` | Version diffs and checking reconstructions |

`inspect_wasm_artifact` and `project_harmony_application_graph` exist only on `main`, not in 6.4.0.

**Highest-impact tools,** per REA's own effect audit:
- **Run foreign code** (`executesForeignCode`): `capture_process_scenario`, `observe_native_calls`, `capture_native_ui_scenario`, `capture_electron_scenario`, `capture_browser_scenario`.
- **Change an attached device** (`mutatesDevice`): `push_adb_file`, `install_adb_package`, `uninstall_adb_package`, `start_adb_app`, `start_adb_activity`, `stop_adb_app`.
- **Change a live page:** `observe_web_execution` (`mutatesTarget`, `mayDiscardData`).

### 3.2 Server environment variables (`src/config/environment.ts`)

| Variable(s) | Purpose |
|---|---|
| `REA_ANALYSIS_PROVIDER` | `auto` (default), `hopper`, `ghidra` or `ida` |
| `GHIDRA_INSTALL_DIR`, `JAVA_HOME` | Absolute paths to Ghidra and its JDK |
| `REA_GHIDRA_STARTUP_TIMEOUT_MS` | Ghidra startup deadline; default 330,000 |
| `REA_GHIDRA_LANGUAGE_ID`, `REA_GHIDRA_COMPILER_SPEC_ID`, `REA_GHIDRA_DISABLED_ANALYZERS`, `REA_GHIDRA_SEED_FILE`, `REA_GHIDRA_NATIVEAOT_JAR` | Ghidra analysis controls |
| `GHIDRA_HEADLESS_MAXMEM` / `GHIDRA_MAXMEM` | JVM `-Xmx`; default 2G |
| `HOPPER_LAUNCHER_PATH`, `HOPPER_TARGET_PATH`, `HOPPER_TARGET_KIND`, `HOPPER_LOADER_ARGS_JSON`, `REA_HOPPER_STARTUP_TIMEOUT_MS` | Hopper settings |
| `REA_IDA_MCP_CONFIG` | IDA MCP configuration |
| `REA_ILSPY_CMD_PATH` | ILSpy command path |
| `REA_MCP_INPUT_SCHEMA_PROFILE` | `full` or `compact` |
| `REA_MCP_MAX_RESPONSE_BYTES` | Response size cap. Results are designed to fit a 10 MiB stdio budget. |
| `REA_LOG_LEVEL` | Log level |
| `REA_REFERENCE_SECRET_PATTERNS_JSON` | Secret patterns used by reference handling |

---

## 4. Analysis backends

| Backend | Role | Required? | Installed by REA? | Notes |
|---|---|---|---|---|
| **Node.js + npm** | Runtime | **Required** | No | Node `^22.19 \|\| ^24.11 \|\| >=26` |
| **Ghidra 12.1.x** + **64-bit full JDK** (JDK 21+, `javac` must be present) | Deep native provider | Optional; you need one of the three providers for decompilation | **Never.** You install it and set `GHIDRA_INSTALL_DIR` and `JAVA_HOME`. | **Always headless; no GUI needed.** See the notes below this table. |
| **Hopper** (commercial, free demo) | Deep native provider | Optional | **Optional**, through setup with its own approval; macOS installs to `~/Applications` | Driven through Hopper's launcher and an in-app Python bridge over `AF_UNIX`. Needs **Apple Events/Automation** permission. On macOS you must finish the demo or license dialog by hand first. |
| **IDA Pro** + [mrexodia/ida-pro-mcp](https://github.com/mrexodia/ida-pro-mcp) | Deep native provider | Optional | Never | Two modes: an attached GUI (1.4.0 legacy tools) or a headless idalib supervisor. Configured with `REA_IDA_MCP_CONFIG`. |
| **LLDB** (Xcode) | Runtime call tracing | Optional | No | Used by `observe_native_calls` |
| Xcode tools (`swiftc`, plus helpers the inspectors spawn) | UI helper, Mach-O and signature inspection | Optional | No | Present on this host |
| Chrome-family browser | Web and CDP tools | Optional | No; REA never downloads a browser | CDP mode needs one you start yourself with `--remote-debugging-port`. Playwright mode needs a browser path you supply. |
| JADX headless + JDK, Apktool, adb, JEB | Android | Optional | No | |
| WABT 1.0.42 | WASM | Optional | No | You supply it |
| pwntools, pwndbg/GDB, binwalk/unblob, mitmdump, EVM carrier | Linux-only helpers | N/A on macOS | No | |
| radare2/rizin, Binary Ninja, Frida, DTrace | — | **Not supported** | — | No integration. The only Frida mention is an example `adb push` of `frida-server`; the "dtrace" hit was a token false positive. |

**How REA runs Ghidra.**
- It launches the JVM directly using Ghidra's LaunchSupport configuration, with the packaged HeadlessScript bridge (`-scriptPath`), `-readOnly` and `-deleteProject`.
- Each session gets an **ephemeral temporary project** with isolated home, cache, config and temp directories.
- Default heap is `-Xmx2G`.
- **It never opens your own Ghidra projects.**
- It requires the native decompiler for the host architecture, `Ghidra/Features/Decompiler/os/mac_arm_64/` on this machine.
- It exposes 25 read-only operations plus ephemeral annotation edits.
- It never changes Gatekeeper quarantine.

**Without any deep provider,** the native decompile and disassemble tools report `capability_unavailable`. JS/Electron, .NET, Mach-O, plist, signature and artifact inspection still work.

---

## 5. Runtime inspection and macOS security constraints

| Capability | Mechanism | macOS requirements | Host status |
|---|---|---|---|
| `observe_native_calls` | `lldb --batch` imports `rea_lldb_tracer.py` and **launches a new process that REA owns**. It sets breakpoints on symbols and ObjC selectors and records register arguments. It **never attaches to a PID it didn't launch** and evaluates no expressions. | Debugger authorization. Per `man DevToolsSecurity`, while DevToolsSecurity is disabled the first debugger use in each login session prompts for an **admin password**. A **hardened-runtime target without `com.apple.security.get-task-allow` cannot be debugged** and fails closed as `debugger-attach-denied`. That includes Apple platform binaries under SIP and most notarized third-party apps. It works for your own Debug builds and for un-hardened binaries. | SIP **enabled**. DevToolsSecurity **disabled**. User **is** in `_developer`, but per the man page that only skips the password once DevToolsSecurity is enabled. Expect a GUI password prompt on first use per login session. |
| `observe_native_ui` / `capture_native_ui_scenario` | ScreenCaptureKit captures one selected window (macOS 14+). The Accessibility API is used for reads and for AX actions (press, scroll, text). A Swift helper is compiled for each scenario. There's no global event injection. | **Screen Recording** and **Accessibility** TCC grants for the app that hosts the MCP server (Terminal or the Claude app). REA never triggers the prompts itself; it fails with an actionable error. | Not granted or checked (TCC can't be read without Full Disk Access). `swiftc` is present. |
| `capture_process_scenario` | Runs the target under a PTY (`@lydell/node-pty`). Records terminal I/O, exit status, and changes to the file systems you declare. | None beyond your user permissions. **The target really runs.** | Usable |
| `capture_electron_scenario` | Launches an Electron executable you supply, with REA's active hook. The hook blocks and records shell and navigation side effects. | None special. The app really runs. | Usable if you supply the executable |
| Browser CDP tools | Passive attach to a loopback CDP endpoint. No `Runtime.evaluate`, navigation or input is exposed. | You launch Chrome with `--remote-debugging-port` and a dedicated profile. While it runs, any local process can control that browser. | Google Chrome present |
| `capture_browser_scenario` | Playwright launches a browser path you supply, with a temporary profile. | — | Usable |
| Hopper control | AppleScript handoff | **Automation (Apple Events)** permission | Hopper not installed |
| DMG inventory and extraction | `hdiutil attach -readonly -nobrowse` | — | — |

**Bottom line for this project's no-host-security-changes rule:**
- REA has **no feature that needs SIP disabled**; `csrutil` has 0 code hits. It never asks for Gatekeeper changes, kernel extensions or root.
- The only optional host-security knob it mentions is `DevToolsSecurity -enable`, as remediation text. It never runs that itself. You don't need it: you can answer the per-session password prompt instead, or not use `observe_native_calls` at all.
- Re-signing a *copy* of a target with `get-task-allow` would make it debuggable without touching SIP. REA does **not** do this, and it would alter the artifact, so treat it as a separate decision that needs approval.

---

## 6. Project-scoped installation

**Does REA support it?**
- **Not through `rea setup`.** For Claude Code, setup only ever writes the user-scope `mcpServers` in `~/.claude.json`, or `$CLAUDE_CONFIG_DIR/.claude.json`, plus the personal skill directory. It has no `--scope` flag. The docs for other clients say outright, "REA configures only the user scope."
- **Manually, yes.** The registration is a plain stdio command, so Claude Code's project scope works. That means `.mcp.json` in the directory you launch `claude` from, written with `claude mcp add --scope project …` or by hand.
- The repo documents the same manual JSON in `docs/installation.md` → "MCP Registry".

**Exact equivalent of what setup would write, but project-scoped:**
```json
{
  "mcpServers": {
    "rea": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "rea-agents@6.4.0", "mcp"],
      "env": {}
    }
  }
}
```
or:
```bash
claude mcp add --scope project --transport stdio rea -- npx -y rea-agents@6.4.0 mcp
```
This variant still downloads the package into the **home-directory npm cache** (`~/.npm/_npx`) on first start. The plan below therefore recommends a fully project-local install launched with `node`.

**Caveats of project scope:**
- Claude Code asks you to approve project `.mcp.json` servers in interactive sessions; reset with `claude mcp reset-project-choices`. Non-interactive `claude -p` and SDK sessions load them **without asking**.
- `.mcp.json` and `.claude/settings.json` are read from the **launch directory**, with no parent-directory fallback.
- `rea doctor --client claude_code` only inspects `~/.claude.json`, so it will report the Claude Code registration as "missing". That's harmless.
- `rea update` and `rea uninstall` won't manage the project registration; you remove it by hand.
- The equivalent of the skill is `<project>/.claude/skills/reverse-engineer-anything/`. Copy it from the package's `skills/` directory.

---

## 7. Security assessment

### 7.1 Dependencies

- **Direct production dependencies:** 35 in 6.4.0; 36 on `main`, which adds `stream-chain`. All are pinned to exact versions:
  - `@babel/parser`, `@babel/types`
  - `@clack/prompts`
  - `@electron/asar`
  - `@jridgewell/trace-mapping`
  - `@lydell/node-pty` (prebuilt native)
  - `@modelcontextprotocol/client`, `@modelcontextprotocol/server` (2.3.1)
  - `@xmldom/xmldom`
  - `@xterm/headless`, `@xterm/addon-serialize`
  - `@zip.js/zip.js`
  - `ajv`, `ajv-formats`
  - `canonicalize`
  - `cross-spawn`
  - `diff`
  - `evmole`
  - `har-schema`
  - `ignore`
  - `incur`
  - `isomorphic-git`
  - `jsonc-parser`
  - `lossless-json`
  - `parse5`
  - `pino`
  - `playwright-core` (1.58.2, which **does not** download browsers)
  - `plist`
  - `semver`
  - `smol-toml`
  - `stream-json`
  - `write-file-atomic`
  - `ws`
  - `yaml`
  - `zod`
- **Transitive:** 148 production packages in `package-lock.json` (lockfile v3). **None have install scripts.**
- **Python:** there are no runtime pip dependencies on macOS. The bridges run inside Hopper's or LLDB's embedded Python. The only `requirements.txt` is `website/requirements.txt`, used to build the docs site, and it isn't shipped. The Linux helpers expect a pwntools, pwndbg or mitmproxy you supply yourself.
- **Binaries in git:** none. The npm tarball does carry CI-built prebuilt binaries: the `node-pty` platform packages and a Windows-only `.node` file.

### 7.2 Positive signals

- npm **trusted publishing** (GitHub Actions OIDC, `id-token: write`) with an **SLSA v1 provenance** attestation. release-please gates publication and refuses to publish if the merged and tagged SHAs don't match.
- The MCP bundle is built with `minify: false`, so there's **no obfuscation**. Source is TypeScript.
- There are **no lifecycle scripts** and **no auto-update**, and registrations are **pinned to an exact version**.
- Setup is transactional: plan, then approve, then back up, write atomically and verify. Malformed config blocks the whole run, and Hopper defaults to *No*.
- `SECURITY.md` is candid. It says the tool is "not a sandbox", that the SHA-1 is "a corruption check, not a modern package signature", and that it "never invokes `sudo`". Vulnerabilities are reported privately.
- Ghidra runs read-only in an ephemeral project with isolated home directories. Bridge sockets are user-only and token-authenticated.
- The project shows security work, for example "mark target-derived content as untrusted data" (#1150), plus symlink and path-admission hardening.

### 7.3 Red flags and risks, ranked

1. **Global config by default.** The documented one-liner writes `~/.claude.json` (user scope, active in every project) and `~/.claude/skills`. `--all-detected` would also touch Claude Desktop, Copilot CLI and VS Code configs on this host. **Mitigation:** don't run setup; use the project-scoped plan.
2. **`~/.claude.json` write race.** Setup atomically replaces a file that Claude Code rewrites often, and it takes no lock. A running Claude Code instance could clobber REA's edit or lose its own. The one-time backup limits the damage. **Mitigation:** avoid the global write altogether.
3. **Not a sandbox.**
   - Five tools run target code (processes, apps, browsers, Electron, LLDB launches) with **your user privileges**.
   - The server has no approval gate of its own, and the `destructiveHint` annotations are only hints.
   - Opening untrusted binaries hands parsing to Ghidra or Hopper with your permissions, which exposes you to parser bugs.

   **Mitigation:** deny rules in project `.claude/settings.json` (§Plan, Phase 4); only analyse targets in `reverse-engineering/permitted-artifacts/`.
4. **Supply-chain velocity.**
   - v3.2.1 to v6.4.0 took 8 days, a new major release roughly every 1–2 days.
   - `main` is 184 commits past a release about 18 hours old.
   - There are 31 npm versions in 3 months.
   - There's one npm maintainer, and many owner commits are unsigned.
   - The docs push `npx -y rea-agents@latest` and frequent updates.
   - At about 15 MB of TypeScript, a full audit isn't practical.

   **Mitigation:** pin `6.4.0`; run `npm audit signatures` to verify provenance; review release notes and diffs before bumping.
5. **Prompt injection from analysed content.** Strings, web pages, WebMCP declarations and logs that come back to the model can contain instructions. REA marks them as untrusted (#1150), but the model still reads them. Treat findings as data.
6. **Popularity anomaly and impersonation risk.** The repo has about 100k stars and 22k forks in 6 months, and the README disclaims crypto tokens that use the REA name. Watch for typosquats: verify the exact name `rea-agents`, the repo `morluto/rea`, and the provenance.
7. **Weak integrity check on the Hopper download.** The SHA-1 comes from the same origin as the DMG, so HTTPS is the real trust anchor. `codesign --verify` isn't pinned to a Team ID. This only matters if you install Hopper; it isn't planned.
8. **CDP exposure.** The CDP tools need Chrome running with a remote-debugging port. While it runs, any local process can drive that browser. Use a throwaway profile and stop it afterwards.
9. **Runtime state in `$HOME`.** At runtime REA may create `~/.rea/{cache,state}`, which `uninstall --purge-data` removes. It also uses per-session temp directories under `$TMPDIR` and `/tmp` (mode 0700, cleaned up). A project-local install can't fully contain these.
10. **The skill can steer agents toward global writes.** Its recovery guide says to get approval first, then run `rea setup --client <id> --yes`, which is a global write. If you install the skill, add the Bash deny rules in Phase 4.

### 7.4 Permissions REA can require

- **Always:** ordinary user permissions. It never needs root or `sudo` on macOS.
- **Only for specific tools:**
  - Screen Recording and Accessibility (native UI tools);
  - Automation/Apple Events (Hopper);
  - debugger authorization, via a per-session admin-password prompt, or permanently via `DevToolsSecurity -enable`, which **we won't do** (`observe_native_calls`);
  - a local loopback CDP port (web tools).

---

## 8. Prerequisites on this host (read-only checks, 2026-10-11)

| Requirement | Probe | Result | Status |
|---|---|---|---|
| Hardware / OS | `uname -m`, `sw_vers` | arm64, macOS 26.6.2 (25G83) | ✅ (macOS ≥ 12; ≥ 14 for UI capture) |
| Node.js | `node --version` | v26.5.0 (`/opt/homebrew/bin/node`) | ✅ satisfies `>=26.0.0` |
| npm / npx | `npm --version` | 11.17.0 (`/opt/homebrew/bin/npm`, `npx`) | ✅ |
| Xcode / CLT | `xcode-select -p`, `xcodebuild -version` | `/Applications/Xcode.app`, Xcode 27.0 | ✅ |
| LLDB | `lldb --version` | lldb-2103.0.34.103 | ✅ |
| Swift compiler | `xcrun --find swiftc` | present | ✅ |
| clang | `command -v clang` | `/usr/bin/clang` | ✅ (useful for test fixtures) |
| Java (JDK 21+, with `javac`) | `java -version`, `/usr/libexec/java_home -V` | **"Unable to locate a Java Runtime"**: `/usr/bin/java` is only the macOS stub | ❌ missing (needed for Ghidra and JADX) |
| Ghidra 12.1.x | `command -v ghidra/ghidraRun/analyzeHeadless`, `/Applications`, `GHIDRA_INSTALL_DIR` | none; env unset | ❌ missing |
| Hopper | `/Applications`, `~/Applications` | none | ❌ missing (optional) |
| IDA Pro / Binary Ninja | `/Applications`, `command -v` | none | ❌ missing (optional; BN unsupported anyway) |
| radare2 / rizin | `command -v r2 radare2 rizin` | none | ➖ missing, but **REA doesn't use them** |
| Homebrew | `brew --version` | 7.0.7 | ✅ present (REA doesn't need it; the plan avoids it) |
| python3 | `python3 --version` | 3.9.6 (`/usr/bin/python3`, CLT) | ➖ not needed by REA on macOS |
| Chrome-family browser | `/Applications` | Google Chrome.app | ✅ (web tools) |
| jadx / adb / apktool / WABT / ilspycmd / mitmdump / binwalk / unblob / gdb / frida | `command -v` | all missing | ➖ optional or Linux-only |
| `gh`, `git`, `jq`, `uv`, `dtrace`, `codesign` | `command -v` | present | ➖ not required |
| SIP | `csrutil status` | **enabled** | ✅ keep enabled; REA doesn't need it off |
| DevToolsSecurity | `DevToolsSecurity -status` | **disabled**; user is in `_developer` | ⚠️ `observe_native_calls` will trigger an admin-password prompt once per login session |
| Existing REA state | `~/.claude.json` server names (keys only), `~/.claude/skills`, `~/.agents/skills`, `~/.rea`, npx cache, `npm ls -g` | No user-scope MCP servers, no REA anywhere, no `~/.rea` | ✅ clean |
| Clients `rea setup` would detect | marker-path existence | Claude Code, Claude Desktop, GitHub Copilot CLI, VS Code | ⚠️ `--all-detected` would modify all four |

**Missing for decompilation:** a deep provider. The recommended open-source route is **Ghidra 12.1.4 + Temurin JDK 21**, installed project-locally (Phase 5). Nothing else is required for static Mach-O, plist, signature, JS or .NET work.

---

## Proposed project-scoped integration plan (NOT EXECUTED)

> ⚠️ **None of these commands has been run.** Each phase needs explicit user approval. They're written for zsh on this host, and none needs `sudo`.

**Decisions to make first**

- **D1 – project root.** `.mcp.json` and `.claude/settings.json` must sit in the directory you **launch `claude` from**. The plan assumes `PROJECT_ROOT=~/Documents/iLinux/apple-silicon-linux-research`. This session's memory path suggests Claude Code may be launched from the parent, `~/Documents/iLinux`. If so, put the two files there instead. The absolute paths below work either way.
- **D2 – launcher.** **(A) Recommended:** a project-local `npm install` launched with `node`. Nothing goes into the home npm cache, and nothing runs `npx` at startup. **(B)** The pinned `npx` launcher is identical to what setup writes, but it uses `~/.npm`.
- **D3 – engine.** No engine gives static and non-native tools only. Ghidra and the JDK (Phase 5) add decompilation. Hopper and IDA are not planned.
- **D4 – runtime tools.** Deny them by default (Phase 4) and enable individually later.

```bash
# Common variables (NOT EXECUTED)
PROJ=~/Documents/iLinux/apple-silicon-linux-research
PROJECT_ROOT="$PROJ"            # or ~/Documents/iLinux, per D1
REA_VER=6.4.0
NODE_BIN=/opt/homebrew/bin/node
```

### Phase 1: Project-local REA install (D2-A). NOT EXECUTED

```bash
mkdir -p "$PROJ/tools/rea"
cd "$PROJ/tools/rea"
# Exact version; npm cache and logs stay inside the project; never run lifecycle scripts
npm install \
  --prefix "$PROJ/tools/rea" \
  --cache "$PROJ/tools/rea/.npm-cache" \
  --logs-dir "$PROJ/tools/rea/.npm-logs" \
  --ignore-scripts --no-audit --no-fund --save-exact \
  "rea-agents@$REA_VER"

# Verify registry signatures and SLSA provenance of everything installed (network read)
npm audit signatures --cache "$PROJ/tools/rea/.npm-cache"

# Read-only sanity checks
"$NODE_BIN" "$PROJ/tools/rea/node_modules/rea-agents/scripts/rea.mjs" --version   # expect 6.4.0
"$NODE_BIN" "$PROJ/tools/rea/node_modules/rea-agents/scripts/rea.mjs" doctor --skill --json   # strictly read-only
```

### Phase 2: Project-scoped MCP registration. NOT EXECUTED

Either write `$PROJECT_ROOT/.mcp.json` by hand:

```json
{
  "mcpServers": {
    "rea": {
      "type": "stdio",
      "command": "/opt/homebrew/bin/node",
      "args": [
        "~/Documents/iLinux/apple-silicon-linux-research/tools/rea/node_modules/rea-agents/scripts/rea.mjs",
        "mcp"
      ],
      "env": {
        "REA_ANALYSIS_PROVIDER": "auto",
        "REA_LOG_LEVEL": "warn"
      },
      "timeout": 600000
    }
  }
}
```

Or create the same entry with the CLI (it writes `.mcp.json` in the current directory):

```bash
cd "$PROJECT_ROOT"
claude mcp add --scope project --env REA_LOG_LEVEL=warn --transport stdio rea \
  -- /opt/homebrew/bin/node "$PROJ/tools/rea/node_modules/rea-agents/scripts/rea.mjs" mcp
# then add "timeout": 600000 by hand (per-server tool timeout; Ghidra's first query can take minutes)
```

Variant D2-B, the npx launcher, is identical to what `rea setup` writes but project-scoped:
`claude mcp add --scope project --transport stdio rea -- npx -y rea-agents@6.4.0 mcp`.

### Phase 3 (optional): project-scoped skill. NOT EXECUTED

```bash
mkdir -p "$PROJECT_ROOT/.claude/skills"
cp -R "$PROJ/tools/rea/node_modules/rea-agents/skills/reverse-engineer-anything" "$PROJECT_ROOT/.claude/skills/"
```

### Phase 4 (recommended): project permission guardrails. NOT EXECUTED

Create `$PROJECT_ROOT/.claude/settings.json`, merging with any existing file:

```json
{
  "permissions": {
    "deny": [
      "mcp__rea__capture_process_scenario",
      "mcp__rea__observe_native_calls",
      "mcp__rea__capture_native_ui_scenario",
      "mcp__rea__capture_electron_scenario",
      "mcp__rea__capture_browser_scenario",
      "mcp__rea__observe_web_execution",
      "mcp__rea__push_adb_file",
      "mcp__rea__install_adb_package",
      "mcp__rea__uninstall_adb_package",
      "mcp__rea__start_adb_app",
      "mcp__rea__start_adb_activity",
      "mcp__rea__stop_adb_app",
      "Bash(npx *rea-agents* setup*)",
      "Bash(npm exec *rea-agents* setup*)",
      "Bash(rea setup*)",
      "Bash(node *rea.mjs setup*)",
      "Bash(rea update*)",
      "Bash(node *rea.mjs update*)",
      "Bash(npm install -g *rea-agents*)",
      "Bash(npm install --global *rea-agents*)",
      "Bash(npm i -g *rea-agents*)",
      "Bash(curl *morluto/rea*install.sh*)"
    ],
    "ask": [
      "mcp__rea__observe_native_ui",
      "mcp__rea__extract_artifact",
      "mcp__rea__extract_firmware",
      "mcp__rea__export_evidence_bundle",
      "mcp__rea__export_web_scripts",
      "mcp__rea__recover_javascript_sources"
    ]
  }
}
```

- `mcp__<server>__<tool>` rules follow the Claude Code permissions docs, and deny beats ask beats allow.
- The `Bash(...)` glob patterns are illustrative. Confirm them with `/permissions` after adding.
- To enable one runtime tool later, remove only its line.

### Phase 5 (optional): Ghidra 12.1.4 + Temurin JDK 21, project-local. NOT EXECUTED

These downloads are about 734 MiB in total, roughly 1.5–2 GB on disk once extracted (estimate). There is no Homebrew, no `/Library/Java` install and no Gatekeeper change. Files fetched with `curl` aren't quarantined, and integrity is checked against GitHub's published SHA-256 digests.

```bash
mkdir -p "$PROJ/tools/downloads" "$PROJ/tools/jdk" "$PROJ/tools/ghidra"
cd "$PROJ/tools/downloads"

# Eclipse Temurin JDK 21.0.12.1+1, macOS aarch64. 200,073,404 bytes.
curl -fL --proto '=https' --tlsv1.2 -o OpenJDK21U-jdk_aarch64_mac_hotspot_21.0.12.1_1.tar.gz \
  'https://github.com/adoptium/temurin21-binaries/releases/download/jdk-21.0.12.1%2B1/OpenJDK21U-jdk_aarch64_mac_hotspot_21.0.12.1_1.tar.gz'
echo '3623232f33a9c3baadf304480b2535f9a3cba8a58d42ecbb438ba267315d9998  OpenJDK21U-jdk_aarch64_mac_hotspot_21.0.12.1_1.tar.gz' | shasum -a 256 -c -
tar -xzf OpenJDK21U-jdk_aarch64_mac_hotspot_21.0.12.1_1.tar.gz -C "$PROJ/tools/jdk"
codesign -dv --verbose=2 "$PROJ/tools/jdk/jdk-21.0.12.1+1/Contents/Home/bin/java" 2>&1 | grep -E 'Authority|TeamIdentifier'

# Ghidra 12.1.4 (2026-09-21). 569,649,598 bytes.
curl -fL --proto '=https' --tlsv1.2 -o ghidra_12.1.4_PUBLIC_20260921.zip \
  'https://github.com/NationalSecurityAgency/ghidra/releases/download/Ghidra_12.1.4_build/ghidra_12.1.4_PUBLIC_20260921.zip'
echo 'ddac49f903da9d5bac833e5cc79395098b9c33cfd3279be5f31bd00387d2d4db  ghidra_12.1.4_PUBLIC_20260921.zip' | shasum -a 256 -c -
unzip -q ghidra_12.1.4_PUBLIC_20260921.zip -d "$PROJ/tools/ghidra"
ls "$PROJ/tools/ghidra/ghidra_12.1.4_PUBLIC/Ghidra/Features/Decompiler/os/"   # must contain mac_arm_64

# Read-only readiness check (REA doctor validates version, analyzeHeadless, JDK range, javac, native decompiler)
GHIDRA_INSTALL_DIR="$PROJ/tools/ghidra/ghidra_12.1.4_PUBLIC" \
JAVA_HOME="$PROJ/tools/jdk/jdk-21.0.12.1+1/Contents/Home" \
"$NODE_BIN" "$PROJ/tools/rea/node_modules/rea-agents/scripts/rea.mjs" doctor --provider ghidra --json
```

- Check the extracted JDK directory name; the expected name is `jdk-21.0.12.1+1`.
- If `mac_arm_64` is missing, stop. Building the Ghidra natives would need Gradle, which is a separate approval.

Then add these to the `env` of the `.mcp.json` entry:

```json
"GHIDRA_INSTALL_DIR": "~/Documents/iLinux/apple-silicon-linux-research/tools/ghidra/ghidra_12.1.4_PUBLIC",
"JAVA_HOME": "~/Documents/iLinux/apple-silicon-linux-research/tools/jdk/jdk-21.0.12.1+1/Contents/Home",
"REA_ANALYSIS_PROVIDER": "ghidra",
"GHIDRA_HEADLESS_MAXMEM": "4G"
```

Optional smoke test on a self-built fixture, not a third-party binary:
`clang -O1 -o "$PROJ/tools/rea/hello" hello.c && node …/rea.mjs analyze "$PROJ/tools/rea/hello" --provider ghidra --json`.

### Phase 6: Verify, then roll back if needed. NOT EXECUTED

```bash
cd "$PROJECT_ROOT"
claude mcp list          # expect "rea" (project); first interactive session asks to approve the project server
claude mcp get rea
# In an interactive session: approve the .mcp.json server, then /mcp → rea connected, ~170 tools

# Rollback (removes only what this plan created)
claude mcp remove --scope project rea          # or delete $PROJECT_ROOT/.mcp.json
claude mcp reset-project-choices
rm -rf "$PROJECT_ROOT/.claude/skills/reverse-engineer-anything"
rm -rf "$PROJ/tools/rea" "$PROJ/tools/jdk" "$PROJ/tools/ghidra" "$PROJ/tools/downloads"
# Remove the Phase 4 "permissions" block from $PROJECT_ROOT/.claude/settings.json if you added it
# If REA created it at runtime: ~/.rea  (cache/state only)
```

**Explicitly not part of this plan:**
- `npx rea-agents setup`, `rea setup` (any flags) and the `curl … | bash` installer;
- `npm install -g` and `brew install`;
- installing Hopper;
- `DevToolsSecurity -enable`, any SIP change (`csrutil`), and any Gatekeeper change (`spctl`, `xattr -d com.apple.quarantine`);
- granting TCC permissions;
- re-signing targets.

---

## Approval required

Each item is a separate approval. Items 1–2 are the **minimal set**.

1. **Network download and execution of third-party code (Phase 1).** `rea-agents@6.4.0` and about 148 production dependency packages (per the lockfile) come from `registry.npmjs.org` into `apple-silicon-linux-research/tools/rea/`. rea-agents alone is 7.8 MB unpacked; the total is an estimated tens of MB.
   - *Consequences:* REA and its dependencies (including a prebuilt `node-pty` native addon) run with your full user privileges whenever the MCP server or CLI starts.
   - *Host footprint:* none outside the project, given `--cache` and `--logs-dir`.
   - *Reversible* by deleting `tools/rea`.
2. **Project-scoped MCP registration (Phase 2).** Create `$PROJECT_ROOT/.mcp.json` and approve Claude Code's project-server prompt.
   - *Consequences:* every Claude Code session started in `PROJECT_ROOT` can call the 170 REA tools. Sessions started elsewhere can't. Claude Code stores your approval choice in its own per-project state.
   - *Watch out:* `claude -p` and SDK runs load the server without prompting.
   - *Reversible* with `claude mcp remove --scope project rea` and `claude mcp reset-project-choices`.
3. **(Optional) Project skill (Phase 3).** Copy 7 Markdown files into `$PROJECT_ROOT/.claude/skills/`.
   - *Consequences:* agent instructions get loaded into context, and they include recovery steps that suggest `rea setup --yes`. Pair this with item 4.
4. **(Recommended) Project permission rules (Phase 4).** Create or merge `$PROJECT_ROOT/.claude/settings.json`.
   - *Consequences:* it blocks REA's code-executing, device-mutating and setup/update paths in this project.
   - *Watch out:* it may block some legitimate runtime investigations until you edit it.
5. **(Optional) Ghidra 12.1.4 and Temurin JDK 21 (Phase 5).** About 734 MiB downloaded from GitHub (NSA Ghidra and Adoptium releases), verified by SHA-256, and extracted into `tools/`. Roughly 1.5–2 GB on disk (estimate).
   - *Consequences:* the decompile and disassemble tools become available. A JVM then parses untrusted binaries with your privileges, defaulting to a 2 GB heap (planned at 4 GB) and plenty of CPU during analysis.
   - *Unaffected:* no system Java and no `/Library/Java` change.
6. **Runtime side effects that a project install can't contain.** These are accepted implicitly once items 1–2 are approved:
   - REA may create `~/.rea/{cache,state}`;
   - per-session temp directories under `$TMPDIR` and `/tmp` (mode 0700, removed on close);
   - Ghidra's isolated temp home and caches.
7. **(Only if a runtime tool is later enabled).** Each needs its own approval, and the default is *not granted*:
   - **Developer Tools / debugger authorization** for `observe_native_calls`. Answer macOS's admin-password prompt once per login session. Do **not** run `DevToolsSecurity -enable`, which would permanently relax the debugging policy. SIP stays enabled, and targets that lack `get-task-allow` remain undebuggable.
   - **Screen Recording + Accessibility** TCC grants for the hosting app (Terminal or Claude) for `observe_native_ui` and `capture_native_ui_scenario`. Granting them lets *any* code running in that app capture the screen and control the UI.
   - **Running untrusted targets** through `capture_process_scenario` or the Electron/browser scenarios. The target runs as you and can change files or use the network. Use only artifacts in `reverse-engineering/permitted-artifacts/`, ideally inside a VM.
   - **Chrome with `--remote-debugging-port`** and a throwaway `--user-data-dir` for the CDP tools. While it runs, any local process can control that browser.
8. **Rejected or not requested:**
   - `npx rea-agents setup` would add a global `~/.claude.json` user-scope server and `~/.claude/skills`, and could touch the Claude Desktop, Copilot CLI and VS Code configs.
   - Global npm install, the `curl | bash` installer, and Hopper download and installation.
   - Homebrew installs, SIP or Gatekeeper changes, and enabling DevToolsSecurity.

---

## Sources

**Repository** (read via `gh api` at `main`; key setup files also checked at tag `rea-agents-6.4.0`)
- https://github.com/morluto/rea
- https://github.com/morluto/rea/blob/main/README.md
- https://github.com/morluto/rea/blob/main/docs/installation.md
- https://github.com/morluto/rea/blob/main/docs/cli.md
- https://github.com/morluto/rea/blob/main/docs/mcp-contracts.md
- https://github.com/morluto/rea/blob/main/docs/mcp-prompts.md
- https://github.com/morluto/rea/blob/main/docs/native-investigation.md
- https://github.com/morluto/rea/blob/main/docs/ida-provider.md
- https://github.com/morluto/rea/blob/main/docs/browser-observation.md
- https://github.com/morluto/rea/blob/main/docs/browser-scenario-contract.md
- https://github.com/morluto/rea/blob/main/docs/electron-observation.md
- https://github.com/morluto/rea/blob/main/docs/raw-binary.md
- https://github.com/morluto/rea/blob/main/docs/process-capture.md
- https://github.com/morluto/rea/blob/main/docs/apple-application-analysis.md
- https://github.com/morluto/rea/blob/main/SECURITY.md
- https://github.com/morluto/rea/blob/main/install.sh
- https://github.com/morluto/rea/blob/main/package.json
- https://github.com/morluto/rea/blob/main/package-lock.json
- https://github.com/morluto/rea/blob/main/server.json
- https://github.com/morluto/rea/blob/main/scripts/rea.mjs
- https://github.com/morluto/rea/blob/main/scripts/prepare.mjs
- https://github.com/morluto/rea/blob/main/scripts/prepack.mjs
- https://github.com/morluto/rea/blob/main/scripts/bundle-mcp-runtime.mjs
- https://github.com/morluto/rea/blob/main/src/cli/setupCommands.ts
- https://github.com/morluto/rea/blob/main/src/cli/interactiveSetup.ts
- https://github.com/morluto/rea/blob/main/src/application/Setup.ts
- https://github.com/morluto/rea/blob/main/src/application/SetupPlan.ts
- https://github.com/morluto/rea/blob/main/src/application/SetupHost.ts
- https://github.com/morluto/rea/blob/main/src/application/SetupClientConfiguration.ts
- https://github.com/morluto/rea/blob/main/src/application/SetupSkill.ts
- https://github.com/morluto/rea/blob/main/src/application/SupportedClients.ts
- https://github.com/morluto/rea/blob/main/src/application/ClientConfigurationDocument.ts
- https://github.com/morluto/rea/blob/main/src/application/ClientRegistrationIdentity.ts
- https://github.com/morluto/rea/blob/main/src/application/MacHopper.ts
- https://github.com/morluto/rea/blob/main/src/application/HopperDownload.ts
- https://github.com/morluto/rea/blob/main/src/application/LinuxHopper.ts
- https://github.com/morluto/rea/blob/main/src/application/Doctor.ts
- https://github.com/morluto/rea/blob/main/src/application/Uninstall.ts
- https://github.com/morluto/rea/blob/main/src/application/Update.ts
- https://github.com/morluto/rea/blob/main/src/application/UpdateRuntime.ts
- https://github.com/morluto/rea/blob/main/src/application/DoctorProviderIds.ts
- https://github.com/morluto/rea/blob/main/src/contracts/toolEffects.ts
- https://github.com/morluto/rea/blob/main/src/contracts/providerSelection.ts
- https://github.com/morluto/rea/blob/main/src/config/environment.ts
- https://github.com/morluto/rea/blob/main/src/identity.ts
- https://github.com/morluto/rea/blob/main/src/main.ts
- https://github.com/morluto/rea/blob/main/src/main/transport.ts
- https://github.com/morluto/rea/blob/main/src/logger.ts
- https://github.com/morluto/rea/blob/main/src/native/LldbCallTracer.ts
- https://github.com/morluto/rea/blob/main/bridge/hopper_bridge.py
- https://github.com/morluto/rea/blob/main/bridge/native/rea_lldb_tracer.py
- https://github.com/morluto/rea/blob/main/scripts/electron-active-hook.cjs
- https://github.com/morluto/rea/blob/main/.agents/skills/reverse-engineer-anything/SKILL.md
- https://github.com/morluto/rea/blob/main/.agents/skills/reverse-engineer-anything/references/connection-and-recovery.md
- https://github.com/morluto/rea/blob/main/.github/workflows/release.yml
- https://github.com/morluto/rea/tree/rea-agents-6.4.0
- https://github.com/morluto/rea/compare/rea-agents-6.4.0...main
- https://github.com/morluto/rea/releases
- https://github.com/morluto/rea/issues/1150

**npm / registries**
- https://www.npmjs.com/package/rea-agents
- https://registry.npmjs.org/rea-agents (via `npm view rea-agents --json`)
- https://registry.npmjs.org/-/npm/v1/attestations/rea-agents@6.4.0
- https://github.com/advisories?query=rea-agents (GitHub Advisory DB query: 0 results)

**Claude Code documentation**
- https://code.claude.com/docs/en/mcp (scopes, `.mcp.json`, approvals, `timeout`, tool search)
- https://code.claude.com/docs/en/permissions (`mcp__server__tool` rules, deny/ask/allow precedence, settings file locations)

**Third-party components referenced in the plan**
- https://github.com/NationalSecurityAgency/ghidra/releases/tag/Ghidra_12.1.4_build (asset digest `sha256:ddac49f9…d2d4db`)
- https://api.adoptium.net/v3/assets/latest/21/hotspot?architecture=aarch64&image_type=jdk&os=mac&vendor=eclipse
- https://github.com/adoptium/temurin21-binaries/releases/tag/jdk-21.0.12.1%2B1 (asset digest `sha256:3623232f…5d9998`)
- https://github.com/mrexodia/ida-pro-mcp
- https://www.hopperapp.com/include/files-api.php?request=releases&public=true (endpoint REA's installer uses; not fetched)

**Local, read-only**
- `man DevToolsSecurity` (macOS 26.6)
- Host probes: `command -v …`, `node/npm/lldb/xcodebuild --version`, `csrutil status`, `DevToolsSecurity -status`, `id -Gn`, and path-existence checks
