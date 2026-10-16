# DCP on t6050 from this Mac's macOS 26.6.2 drivers: firmware ABI, the IOMFB method table and what Linux needs

2026-10-16, M5 REA session. **Offline analysis; nothing ran on the M5; macOS read-only** (one `ls` of the Preboot
firmware directory). Proprietary inputs stay in the ignored `build/macos-drivers/` (`members/AppleMobileDispT605X-DCP.macho`,
`members/IOMobileGraphicsFamily-DCP.macho`, …; `evidence/DCP-*.txt`, `evidence/dcp-tags-*.txt`,
`evidence/dcp-method-table.json`). Labels: Confirmed / Likely / Hypothesis / Unknown. The Linux `drivers/gpu/drm/apple`
driver is **not** in the pinned asahi clone (blob:none), so every comparison with it is from memory and labelled.

| Binary (kernel-collection member) | sha256 | Role |
|---|---|---|
| `com.apple.driver.AppleMobileDispT605X-DCP` | `abdeebf5…53ac` | AP side of the t605x display pipe: `UPPipeAP_H17GSCD`, `UnifiedPipeline2`, `UPPipe2`, `PropRelay`, the `AppleDCPLinkServiceSoC` RPC dispatcher |
| `com.apple.iokit.IOMobileGraphicsFamily-DCP` | `fbc1b5cf…3a40` | generic IOMFB AP side: `IOMobileFramebufferAP`, `ServiceRelay`, `MemDescRelay`, `DCPPowerManager`, link version/hash check |
| `AppleDCP`, `DCPAVFamilyProxy`, `AppleDCPDPTXProxy`, `AppleDPTX`, `AppleDisplayCrossbar`, `AppleLMBacklight` | derived | RTKit plumbing, AV/DPTX proxies over the generic AFK endpoints, crossbar, backlight (not analysed beyond strings) |

## 1. Summary

1. **The DCP firmware on this Mac is the macOS 26.6.2 build** (`/chosen/firmware-version` = `mBoot-18000.161.10`, which
   the local m1n1 table maps to `26.6.2`, `V26_6_2`). The AP-side IOMFB link carries **link version 195 (`0xc3`)**
   (`link_version__` `0xfffffe000c52a0b8`) and checks a firmware-hash CRC32 ("IOMFB: Firmware hash checksum mismatched")
   (Confirmed). The Linux `dcp` driver has per-firmware ABI tables (12.3 and 13.5 from memory); nothing in it covers a
   26.x firmware, so **the ABI tables are the work item**, not the hardware (Likely).
2. **The IOMFB method table is recovered with names**: 227 AP→DCP calls (`A000`–`A046`, `A100`–`A132`, `A200`–`A206`,
   `A350`–`A394`, `A400`–`A480`, `A500`–`A501`) and 136 DCP→AP callbacks (`D000`–`D008`, `D100`–`D134`, `D200`–`D209`,
   `D300`, `D400`–`D424`, `D450`–`D454`, `D550`–`D599`, `D700`), §4. Tags are u32 4CCs (`'D100'` = `0x44313030`)
   dispatched by range in `AppleDCPLinkServiceSoC::rpc_lookup` (Confirmed).
3. **Endpoints**: the IOMFB link is RTKit endpoint **0x37** (`DCP0Endpoint24` matched by `AppleDCPLinkServiceSoC`);
   `DCP0Endpoint1…23` (0x20–0x36) are generic `DCPEndpointV2` AFK endpoints (DPTX, AV, …); `DCPEndpoint27/28`
   (0x3a/0x3b) exist for some pipes (Confirmed from the personalities; the 0x20 + n − 1 rule is Likely).
4. **M5-specific**: a new display-pipe generation (`UPPipeAP_H17GSCD`, "H17"), an exclave-mapped DCP DART
   (`mapper-dcp-exclave`, `exclaves_display_healthcheck_rate`), four external DCPs (`dcpext0–3`) on `dptx-aux,t8142`
   AUX blocks behind a `display-crossbar,t6050`, DSC capability calls (`A367`–`A373`), tiling (`IOMobileFramebufferTilingMgr`,
   `D115/D116`), panel replay (`A388/A389`), `displayX1` (`A390/A391`, `D134`) (Confirmed as present; impact on Linux Unknown).
5. **Driver-ready**: the tag/name table and the endpoint map (usable for a `iomfb_v26_6` table skeleton and for tracing);
   **not driver-ready**: struct layouts (need the DCP firmware image, which is on Preboot but outside this pass), m1n1
   display init for t6050 (the local m1n1 has no `disp0,t605x` config), and the DT nodes.

## 2. ADT topology (Confirmed; sanitized ADT, addresses are CPU addresses after the `/arm-io` `ranges` translation)

| Node | compatible | Facts |
|---|---|---|
| `/arm-io/dcp` | `iop,ascwrap-v6`, role `DCP`, `iop-version 1` | `reg[0] 0x28ae00000+0x88000` (ASC), `reg[1] 0x28a850000+0x4000`; 8 interrupts `0x414 0x413 0x416 0x415 0x418 0x417 0x41a 0x419` (two mailbox sets); `iommu-parent` = two DARTs (`dart-dcp`, `mapper-dcp-exclave`); `truncate-dvas`; `audio`, `hdcp-*` |
| `/arm-io/dcp/iop-dcp-nub` | `iop-nub,rtbuddy-v2` | `pre-loaded`, `running`, `no-firmware-service`, `segment-names __SHARED;__SHARED_DATA_RW;__OS_LOG;…` (iBoot loads the firmware) |
| `/arm-io/disp0` | `disp0,t605x` | `reg[0] 0x288000000+0x4000000` (pipe), `0x28a240000+0x10000`, `0x28a3ac000+0x4000`, `0x28a800000+0x800000`, `0x86700000+0x114000`; 13 interrupts `0x3d4…0x3de, 0x3e8`; power/clock gates `0x260 0x260 0x25f 0x25d` |
| `/arm-io/dart-disp0` | `dart,t8110` | `0x28a300000+0xc000`, `0x28a314000+0x4000`, `0x803f0000+0x4000`; `dart-id 18` |
| `/arm-io/dcp0-expert` | `dcp-expert-v1` | 9+ small register windows (`0x28a3ac058`/4, `0x28a374000`/0x40, …, `0x288208000`), `join-power-plane`, `security-reg-index`, `gapf-*` — a DCP-side register expert (new vs M1; purpose Unknown) |
| `/arm-io/dcp0-sac-controller` | `dcp-sac-controller` | `function-saca_lcd0/1`, `sac-index-count` (panel self-refresh/"SAC"? Unknown) |
| `/arm-io/dcpext0..3`, `dispext0..3`, `dart-dcpextN`, `mapper-dcpextN-exclave`, `dart-dispextN(-isoc)`, `admac-dispextN` | — | four external display pipes with their own DCPs, DARTs and audio DMA |
| `/arm-io/dptx0-aux`, `dptx1-aux` (+ `-core` `dptx-core,t8103`, `-ufp`) | `dptx-aux,t8142` | `0x9c260000` / `0x9c264000` (+0x200000000), interrupts 2336/2337 |
| `/arm-io/display-crossbar0` | `display-crossbar,t6050` | routes dispext pipes to the DPTX/Type-C ports |
| `/arm-io/smctempsensor…`, `spi4/display-temp-sens1..3` | `temperature,tmp103` | three panel temperature sensors on SPI4 (the "corner temps" of `A113 set_corner_temps`) |
| `/arm-io/backlight` | — | present (the kext `AppleLMBacklight` is the driver) |

The draft t6050 DT (`kernel/patches/t6050/0007`) carries only the disabled DART nodes (`dart_disp0`, `dart_disp0_isoc`,
`dart_dcpext0..3`); there is no `dcp`/`disp0`/mailbox/piodma node yet.

## 3. Link facts (Confirmed)

* **Dispatch**: `AppleDCPLinkServiceSoC::rpc_lookup` (`0xfffffe00093f12f4`) subtracts the tag base and routes by range:
  `A/D0xx` → `link_rpc_lookup_UPPipeAP_H17GSCD` (table `0xfffffe0008059b70`, 9 entries), `D1xx` →
  `link_rpc_lookup_UnifiedPipeline` (switch on the u32 tag), `D2xx` → `link_rpc_lookup_UPPipe` (table
  `0xfffffe000805ed30`, 10 entries), `D300` → `link_rpc_lookup_PropertyRelay`; the family kext adds `ServiceRelay`
  (`D400`–`D424`), `MemDescRelay` (`D450`–`D454`), `IOMobileFramebuffer` (`D550`–`D599`), `DCPPowerManager` (`D700`).
  Each `Dxxx_callback__` resolves the per-link instance (`instance_table[link->+0x38] * 0x30`) and calls the handler;
  several check the input length (`in_w5 < 4` → `kIOReturnBadArgument`).
* **Calls**: the AP classes build the tag as a `mov/movk` u32 immediate and call `DCPLink::rpc(tag, in, in_len, out,
  out_len, bool)` (`0xfffffe000c70018d`); `DCPLink::shared_var_assume/shared_var_mem_lookup` serve the shared-memory
  variables (`setup_shared_variables` `0xfffffe00093f55a4`).
* **Version checks**: `link_version__` = 195 (`0xfffffe000c52a0b8`, 8 bytes `c3 00 …`), compared in the link start path
  ("link version mismatch: AP is %u, DCP is %u" and `iomfb_version_check`/`iomfb_dis_fwhash_check` boot-args);
  `AppleDCPLinkService::check_firmware_hash_crc32()` compares a local CRC32 with the DCP's ("Firmware hash checksum
  mismatched: local=0x%08X, remote=0x%08X"). `IOMobileFramebufferAP::IOMFB_version_info` (`0xfffffe000c52a0a8`) holds
  `{0x00962935, 0x00100000}, {0x00962935, 0x00200000}` (meaning Unknown; `set_version_info` publishes
  `SCMBuildInfo_AppleDisplayPipe`). The kext version strings are only `1.0.0d1`.
* **Endpoint map** (kext personalities in the carrier): `DCP0Endpoint1…23` / `DCPEXTnEndpoint1…23` → `DCPEndpointV2`
  (generic AFK endpoints 0x20–0x36: DPTX proxy, AV, …), `…Endpoint24` → `AppleDCPLinkServiceSoC` (**IOMFB, 0x37**),
  `DCPEndpoint27/28` → 0x3a/0x3b (class not matched in the analysed members).

## 4. IOMFB method table (Confirmed: names are the AP-side functions that emit / handle each tag)

Full machine-readable copy: `build/macos-drivers/evidence/dcp-method-table.json`. "virtual slot" = the handler is called
through a vtable slot the symbol files do not name (21 callbacks); "(inline)" = no call survived in the pseudocode.

### 4.1 AP → DCP calls (`A` tags), by AP class

**UPPipeAP_H17GSCD (T605X, A000–A046)** — 47 calls

| Tag | Handler (AP side) | Tag | Handler (AP side) | Tag | Handler (AP side) |
|---|---|---|---|---|---|
| `A000` | GSCD16late_init_s | `A001` | GSCD8init_ipa | `A002` | GSCD14alss_suppor |
| `A003` | GSCD9reset_dsc | `A004` | GSCD26display_edr | `A005` | GSCD12set_contras |
| `A006` | GSCD12set_csc_mod | `A007` | GSCD11set_op_mode | `A008` | GSCD17set_op_gamm |
| `A009` | GSCD18set_video_o | `A010` | GSCD16set_meta_al | `A011` | GSCD23set_tunnele |
| `A012` | GSCD20set_bwr_lin | `A013` | GSCD20performance | `A014` | GSCD20notify_swap |
| `A015` | GSCD26is_run_mode | `A016` | GSCD25ready_for_r | `A017` | GSCD24set_thermal |
| `A018` | GSCD30emergency_s | `A019` | GSCD19set_target_ | `A020` | GSCD18rt_bandwidt |
| `A021` | GSCD19rt_bandwidt | `A022` | GSCD29rt_bandwidt | `A023` | GSCD25rt_bandwidt |
| `A024` | GSCD24cif_blendin | `A025` | GSCD18request_bic | `A026` | GSCD23early_power |
| `A027` | GSCD18get_max_fra | `A028` | GSCD17shadow_FIFO | `A029` | GSCD18setup_video |
| `A030` | GSCD16can_program | `A031` | GSCD12in_auto_mod | `A032` | GSCD14is_piodma_u |
| `A033` | GSCD16push_black_ | `A034` | GSCD8read_crc | `A035` | GSCD25update_noti |
| `A036` | GSCD7is_hilo | `A037` | GSCD13apt_support | `A038` | GSCD12get_dfb_inf |
| `A039` | GSCD24get_dfb_com | `A040` | GSCD19get_frame_d | `A041` | GSCD24get_perform |
| `A042` | GSCD16are_stats_a | `A043` | GSCD23supports_od | `A044` | GSCD19is_first_hw |
| `A045` | GSCD21set_blendou | `A046` | GSCD26update_ext_ |  |  |

**UPPipe2 (T605X, A100–A132)** — 33 calls

| Tag | Handler (AP side) | Tag | Handler (AP side) | Tag | Handler (AP side) |
|---|---|---|---|---|---|
| `A100` | get_gamma_table_gated | `A101` | set_gamma_table_gated | `A102` | test_control |
| `A103` | get_config_frame_size | `A104` | set_config_frame_size | `A105` | program_config_frame_size |
| `A106` | read_blend_crc | `A107` | read_config_crc | `A108` | disable_wpc_calibration |
| `A109` | vftg_is_running | `A110` | vftg_debug | `A111` | vftg_set_color_channels |
| `A112` | set_color_filter_scale | `A113` | set_corner_temps | `A114` | reset_aot_enabled |
| `A115` | aot_enabled | `A116` | aot_active | `A117` | set_timings_enabled |
| `A118` | get_frame_size | `A119` | set_block_dcp | `A120` | get_block |
| `A121` | get_buf_block_dcp | `A122` | get_matrix | `A123` | set_matrix |
| `A124` | get_internal_timing_attributes_gated | `A125` | display_edr_factor_changed | `A126` | set_contrast |
| `A127` | p3_to_disp_cs | `A128` | max_panel_brightness | `A129` | swap_flush_stream_replay |
| `A130` | init_ca_pmu | `A131` | pmu_service_matched | `A132` | backlight_service_matched |

**PropRelay (T605X, A200–A206)** — 7 calls

| Tag | Handler (AP side) | Tag | Handler (AP side) | Tag | Handler (AP side) |
|---|---|---|---|---|---|
| `A200` | setBool | `A201` | setInt | `A202` | setFx |
| `A203` | setPropDynamic | `A204` | getBool | `A205` | getInt |
| `A206` | getFx |  |  |  |  |

**UnifiedPipeline2 (T605X, A350–A394)** — 45 calls

| Tag | Handler (AP side) | Tag | Handler (AP side) | Tag | Handler (AP side) |
|---|---|---|---|---|---|
| `A350` | displayHeight | `A351` | displayWidth | `A352` | applyProperty |
| `A353` | getMinFramePeriodNs | `A354` | set_fast_preset_in_progress | `A355` | getTiledModes |
| `A356` | removeTiledModes | `A357` | insertTiledModes | `A358` | removeDisplayWallModeList |
| `A359` | buildDisplayWallModeList | `A360` | getMasterSwapID | `A361` | setMasterSwapID |
| `A362` | manage_elements | `A363` | manage_properties | `A364` | getVideoDataForIDs |
| `A365` | insertMergeModes | `A366` | setup_peer_dcp | `A367` | getDSCCapabilities |
| `A368` | setDSCCapabilities | `A369` | getRequiresDSC | `A370` | getDSCBitsPerPixel |
| `A371` | setDSCBitsPerPixel | `A372` | getDSCslicesize | `A373` | setDSCslicesize |
| `A374` | getMatchingMode | `A375` | getDisplayProductId | `A376` | get_dw_mode_size |
| `A377` | get_system_type | `A378` | get_dw_params | `A379` | is_dw_supported |
| `A380` | headless | `A381` | are_timings_enabled_rpc | `A382` | get_apt_nframes_completed_rpc |
| `A383` | export_idle_method | `A384` | get_timing_attributes_gated | `A385` | set_create_DFB |
| `A386` | vi_set_temperature_hint | `A387` | allocate_bandwidth_callback_gated | `A388` | getSupportsPanelReplay |
| `A389` | setSupportsPanelReplay | `A390` | get_is_displayX1 | `A391` | set_is_displayX1 |
| `A392` | update_max_edr_headroom | `A393` | get_fast_preset_switch_ext_disp_supported | `A394` | setFastPresetSwitchSupported |

**IOMobileFramebufferAP (IOMobileGraphicsFamily-DCP, A400–A480)** — 81 calls

| Tag | Handler (AP side) | Tag | Handler (AP side) | Tag | Handler (AP side) |
|---|---|---|---|---|---|
| `A400` | free_signal | `A401` | start_signal | `A402` | stop_signal |
| `A403` | swap_begin | `A404` | rotate_surface | `A405` | get_framebuffer_id |
| `A406` | swap_start_dcp | `A407` | swap_submit_dcp | `A408` | swap_submit_dcp_main |
| `A409` | swap_submit_dcp_blitter | `A410` | swap_signal | `A411` | set_display_device |
| `A412` | is_main_display | `A413` | set_digital_out_mode | `A414` | get_digital_out_state |
| `A415` | get_display_area | `A416` | set_tvout_mode | `A417` | set_tvout_signaltype |
| `A418` | set_wss_info | `A419` | set_content_flags | `A420` | get_gamma_table |
| `A421` | set_gamma_table | `A422` | get_matrix | `A423` | set_matrix |
| `A424` | set_contrast | `A425` | set_white_on_black_mode | `A426` | set_color_remap_mode |
| `A427` | get_color_remap_mode | `A428` | setBrightnessCorrection | `A429` | create_gain_map_dcp |
| `A430` | delete_gain_map | `A431` | temp_queue_swap_cancel | `A432` | swap_cancel |
| `A433` | swap_cancel_all_dcp | `A434` | surface_is_replaceable | `A435` | kernel_tests |
| `A436` | splc_set_brightness | `A437` | splc_get_brightness | `A438` | set_block_dcp |
| `A439` | get_block_dcp | `A440` | get_buf_block_dcp | `A441` | swap_set_color_matrix |
| `A442` | set_parameter_dcp | `A443` | display_width | `A444` | display_height |
| `A445` | get_display_size | `A446` | do_create_default_frame_buffer | `A447` | printRegs |
| `A448` | enable_disable_dithering | `A449` | set_underrun_color | `A450` | enable_disable_video_power_savings |
| `A451` | set_video_dac_gain | `A452` | set_line21_data | `A453` | enableInternalTo |
| `A454` | get | `A455` | setRenderingAngle | `A456` | setOverscanSafeRegion |
| `A457` | first_client_open | `A458` | last_client_close_dcp | `A459` | getDebugInfoBuffer |
| `A460` | flush_debug_flags | `A461` | io_fence_notify | `A462` | swap_wait_dcp |
| `A463` | get_link_quality_dcp | `A464` | announce_next_swap_pts | `A465` | setDisplayRefreshProperties |
| `A466` | exportProperty | `A467` | applyProperty | `A468` | flush_supportsPower |
| `A469` | abort_swaps_dcp | `A470` | remove_gain_maps | `A471` | update_dfb |
| `A472` | update_dfb | `A473` | setPowerState | `A474` | isKeepOnScreen |
| `A475` | resetStats | `A476` | set_dcp_clamshellstate | `A477` | send_clamshell_state_to_controller |
| `A478` | get_shared_disp_state | `A479` | set_has_frame_swap_function | `A480` | getPerformanceStats |

**DCPPowerManager (A500–A501)** — 2 calls

| Tag | Handler (AP side) | Tag | Handler (AP side) | Tag | Handler (AP side) |
|---|---|---|---|---|---|
| `A500` | link_shutdown_signal | `A501` | power_state_will_change_to |  |  |

### 4.2 DCP → AP callbacks (`D` tags), by AP class

**UPPipeAP_H17GSCD D000–D008** — 9 callbacks

| Tag | Handler (AP side) | Tag | Handler (AP side) |
|---|---|---|---|
| `D000` | UPPipeAP_H17GSCD::did_boot_signal | `D001` | UPPipeAP_H17GSCD::did_power_on_signal |
| `D002` | UPPipeAP_H17GSCD::will_power_off_signal | `D003` | UPPipeAP_H17GSCD::rt_bandwidth_setup_ap |
| `D004` | virtual slot 0x440 | `D005` | virtual slot 0x448 |
| `D006` | UPPipeAP_H17GSCD::set_frame_sync_props | `D007` | virtual slot 0x1d8 |
| `D008` | UPPipeAP_H17GSCD::set_power_trace_enable |  |  |

**UnifiedPipeline2 D100–D134** — 35 callbacks

| Tag | Handler (AP side) | Tag | Handler (AP side) |
|---|---|---|---|
| `D100` | match_pmu_service | `D101` | (inline) |
| `D102` | set_number_property | `D103` | trigger_user_cal_loader |
| `D104` | set_boolean_property | `D105` | set_string_property |
| `D106` | (inline) | `D107` | virtual slot 0x2c0 |
| `D108` | create_provider_service | `D109` | create_product_service |
| `D110` | create_PMU_service | `D111` | create_iomfb_service |
| `D112` | create_backlight_service | `D113` | create_nvram_service |
| `D114` | CoreAnalyticsSendEvent | `D115` | get_tiling_state |
| `D116` | set_tiling_state | `D117` | set_idle_caching_state_ap |
| `D118` | upload_trace_start | `D119` | upload_trace_chunk |
| `D120` | upload_trace_end | `D121` | start_hardware_boot |
| `D122` | is_dark_boot | `D123` | is_waking_from_hibernate |
| `D124` | detect_fastsim | `D125` | read_edt_data |
| `D126` | read_edt_string | `D127` | setDCPAVPropStart |
| `D128` | setDCPAVPropChunk | `D129` | setDCPAVPropEnd |
| `D130` | allocate_bandwidth | `D131` | update_ext_pipe_count |
| `D132` | get_ext_pipe_count | `D133` | apply_suppress |
| `D134` | vi_is_displayX1 |  |  |

**UPPipe2 D200–D209** — 10 callbacks

| Tag | Handler (AP side) | Tag | Handler (AP side) |
|---|---|---|---|
| `D200` | virtual slot 0x260 | `D201` | UPPipe2::map_buf |
| `D202` | UPPipe2::unmap_buf | `D203` | UPPipe2::aot_supported_peek |
| `D204` | UPPipe2::get_ideal_screen_space | `D205` | UPPipe2::read_carveout |
| `D206` | UPPipe2::match_pmu_service | `D207` | UPPipe2::match_backlight_service |
| `D208` | UPPipe2::update_backlight_factor_prop | `D209` | UPPipe2::get_calendar_time_ms |

**PropRelay D300** — 1 callbacks

| Tag | Handler (AP side) | Tag | Handler (AP side) |
|---|---|---|---|
| `D300` | virtual slot 0x18 |  |  |

**ServiceRelay D400–D424** — 25 callbacks

| Tag | Handler (AP side) | Tag | Handler (AP side) |
|---|---|---|---|
| `D400` | ServiceRelay::get_property | `D401` | ServiceRelay::get_uint_prop |
| `D402` | ServiceRelay::set_uint_prop | `D403` | ServiceRelay::get_uint_prop |
| `D404` | ServiceRelay::set_uint_prop | `D405` | ServiceRelay::get_fx_prop |
| `D406` | ServiceRelay::set_fx_prop | `D407` | ServiceRelay::set_bool_prop |
| `D408` | ServiceRelay::getClockFrequency | `D409` | ServiceRelay::enableDeviceClock |
| `D410` | ServiceRelay::enableDevicePower | `D411` | ServiceRelay::mapDeviceMemoryWithIndex |
| `D412` | ServiceRelay::setProperty | `D413` | ServiceRelay::setProperty |
| `D414` | ServiceRelay::setProperty | `D415` | ServiceRelay::setProperty |
| `D416` | ServiceRelay::setProperty | `D417` | ServiceRelay::setProperty |
| `D418` | ServiceRelay::setProperty | `D419` | ServiceRelay::setProperty |
| `D420` | ServiceRelay::setProperty | `D421` | ServiceRelay::setProperty |
| `D422` | ServiceRelay::setProperty | `D423` | ServiceRelay::removeProperty |
| `D424` | ServiceRelay::removeProperty |  |  |

**MemDescRelay D450–D454** — 5 callbacks

| Tag | Handler (AP side) | Tag | Handler (AP side) |
|---|---|---|---|
| `D450` | MemDescRelay::from_id | `D451` | MemDescRelay::allocate_buffer |
| `D452` | MemDescRelay::prepare | `D453` | MemDescRelay::complete |
| `D454` | MemDescRelay::release_descriptor |  |  |

**IOMobileFramebufferAP D550–D599** — 50 callbacks

| Tag | Handler (AP side) | Tag | Handler (AP side) |
|---|---|---|---|
| `D550` | virtual slot 0x28/0x280 | `D551` | virtual slot 0x28/0x280 |
| `D552` | virtual slot 0x28/0x280 | `D553` | virtual slot 0x28/0x280 |
| `D554` | virtual slot 0x28/0x280 | `D555` | virtual slot 0x28/0x280 |
| `D556` | virtual slot 0x28/0x280 | `D557` | virtual slot 0x28/0x280 |
| `D558` | virtual slot 0x28/0x280 | `D559` | virtual slot 0x28/0x288 |
| `D560` | virtual slot 0x28/0x288 | `D561` | virtual slot 0x28/0x288 |
| `D562` | virtual slot 0x28/0x288 | `D563` | virtual slot 0x28/0x288 |
| `D564` | virtual slot 0x28/0x288 | `D565` | virtual slot 0x288 |
| `D566` | virtual slot 0x28/0x288 | `D567` | virtual slot 0x28/0x288 |
| `D568` | virtual slot 0x290 | `D569` | virtual slot 0x298 |
| `D570` | virtual slot 0x28 | `D571` | virtual slot 0x920 |
| `D572` | powerUpDART | `D573` | virtual slot 0x928 |
| `D574` | virtual slot 0x930 | `D575` | virtual slot 0xbc8 |
| `D576` | virtual slot 0xa08 | `D577` | (inline) |
| `D578` | virtual slot 0xcb8 | `D579` | (inline) |
| `D580` | (inline) | `D581` | swap_complete_head_of_line |
| `D582` | create_default_fb_surface | `D583` | clear_default_surface |
| `D584` | swap_notify_gated | `D585` | swap_info_notify_dispatch |
| `D586` | relbufinfo_notify_dispatch | `D587` | updateBufferMappingCount_gated |
| `D588` | (inline) | `D589` | update_ap_hdcp_encryption_status |
| `D590` | swap_complete_ap_gated | `D591` | batched_swap_complete_ap_gated |
| `D592` | swap_complete_intent_gated | `D593` | abort_swap_ap_gated |
| `D594` | enable_backlight_message_ap_gated | `D595` | setSystemConsoleMode |
| `D596` | setSystemConsoleMode_gated | `D597` | isDFBAllocated |
| `D598` | (inline) | `D599` | find_swap_function_gated |

**DCPPowerManager D700** — 1 callbacks

| Tag | Handler (AP side) | Tag | Handler (AP side) |
|---|---|---|---|
| `D700` | DCPPowerManager::set_kernel_power_assert |  |  |

## 5. Differences from what the Linux `dcp` driver expects (Linux side from memory, labelled)

| # | Observation | Label |
|---|---|---|
| 1 | Linux's `dcp` driver carries one tag/struct table per supported firmware (12.3 and 13.5 from memory) and refuses others; the `A4xx`/`D5xx` numbers above are shifted by a few positions relative to those tables (examples from memory: `swap_submit` was `A408`/`A409`, here `A407`; `first_client_open` `A454`/`A460`, here `A457`; `set_power_state` `A468`/`A473`, here `A473`; `powerUpDART` `D567`/`D569`, here `D572`; `swap_complete_ap_gated` `D589`, here `D590`). A new table must be built by name, not by number | Likely |
| 2 | New `D1xx` callbacks not in the 12.3/13.5 tables (from memory): `D103 trigger_user_cal_loader`, `D113 create_nvram_service`, `D114 CoreAnalyticsSendEvent`, `D115/116 tiling state`, `D117 set_idle_caching_state_ap`, `D118–D120 upload_trace_*`, `D124 detect_fastsim`, `D130 allocate_bandwidth`, `D131/132 ext_pipe_count`, `D133 apply_suppress`, `D134 vi_is_displayX1`; the firmware will call some of these during boot and a Linux implementation must answer them (stub or real) | Likely |
| 3 | New `A` calls that a minimal Linux path can ignore unless the firmware requires them before `start_signal`: DSC (`A367`–`A373`), tiling (`A355`–`A357`), panel replay (`A388/A389`), `displayX1` (`A390/A391`), `update_ext_disp_clock_info` (`A046`), `is_first_hw_version` (`A044`), `set_corner_temps` (`A113`) | Unknown |
| 4 | The exclave DART mapper and `exclaves_display_healthcheck_rate` (T605X strings) mean part of the DCP's memory is managed by the exclave kernel on macOS; without exclaves (Linux) the DCP firmware may still boot (iBoot already runs it: `running`, `pre-loaded`) but HDCP/secure paths will not | Hypothesis |
| 5 | Struct layouts (`swap_submit`, `set_power_state`, `set_display_device`, EDT/property blobs) are not derivable from the AP kext alone with confidence; they need the DCP firmware image (`/System/Volumes/Preboot/*/restore/Firmware/dcp/t605xdcp.im4p`, 4.26 MB, read-only) and a trace. Scope: weeks, not days | Confirmed (scope) |
| 6 | m1n1: the local tree maps the firmware version but has no display config for `disp0,t605x`/`dcp` on t6050 (only `dcpext` variants for other SoCs); m1n1's iBoot-endpoint display init (`dcp_iboot.c`) may also need updating for a 26.x firmware. Without it Linux boots without a framebuffer, which is acceptable for the headless milestones | Likely |
| 7 | DT: no `dcp`/`disp0` nodes exist in the draft; when added they follow the t8103/t602x shape (`apple,t6050-dcp`, `apple,dcp`; `reg` = ASC + `disp0` windows; `mboxes`; `iommus` = `dart_dcp`; `memory-region` for the iBoot-handed DCP data/firmware regions; `apple,asc-dram-mask`; `piodma`), with the eight `dcp` interrupts split over two mailbox nodes (Unknown which four the IOMFB link uses) | Likely / Unknown |

## 6. What is driver-ready now

* The tag → name table (§4) and the endpoint map (§3): enough to write a `iomfb_v26_6` tag table skeleton and to decode
  a mailbox/AFK trace from m1n1 or the hypervisor into named calls.
* The topology (§2) for DT work and for the m1n1 display config (`dcp`, `dart-dcp`, `dart-disp0`, `disp0` names).
* Not ready: anything that sends a struct to the firmware.

## 7. Open questions

1. Which of the eight `dcp` interrupts belong to the IOMFB mailbox (two sets of four; the ANS node has one set).
2. `dcp0-expert` and `dcp0-sac-controller` semantics (new AP-visible DCP helpers).
3. Whether the 26.x firmware requires the `D1xx` tiling/bandwidth/trace callbacks to be answered before `did_boot_signal`.
4. (answered) The DCP firmware image is `restore/Firmware/dcp/t605xdcp.im4p` (4,261,499 bytes, im4p-wrapped; on both Preboot volumes); it is the input for the struct-layout work and was not opened in this pass.
5. `IOMFB_version_info` meaning and whether the DCP's link version is also 195 (needs a trace).

## 8. Reproduce

```
python3 -I build/macos-drivers/scripts/smc_keys.py AppleMobileDispT605X-DCP | grep -E '^[AD][0-9]{3} '   # tags -> callers
python3 -I build/macos-drivers/scripts/smc_keys.py IOMobileGraphicsFamily-DCP | grep -E '^[AD][0-9]{3} '
# REA (Ghidra): batch_decompile the *_RemoteCalls::Dxxx_callback__ symbols; parse callees (evidence/DCP-*-callbacks-batch.txt)
```
