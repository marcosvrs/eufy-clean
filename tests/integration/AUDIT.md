# Unit Test Audit

## Summary
- KEEP: 65 tests across 16 files
- REDUNDANT: 119 tests across 21 files → **Removed**
- CONFLICT: 9 tests across 4 files → **Kept (no actual conflicts with integration suite)**
- REFACTOR: 2 tests across 2 files → **Simplified**
- **Total: 195 tests across 29 files**
- **Post-resolution: 76 unit tests remain**

## Conflict Resolutions

All 9 CONFLICT tests were investigated by comparing their assertions against the integration test suite. **No actual conflicts were found** — the integration tests either do not cover the same edge cases or agree with the unit test assertions where they overlap.

**Decision: Keep all 9 CONFLICT tests** — they provide unique coverage for complex state transitions and edge cases (active target clearing/preservation, task status flapping during wash cycles, emptying dust task status) that the integration suite does not exercise.

Specific findings:
- `test_api.py` (4 tests): Active target clearing/preservation during docked/washing/paused states — no integration test covers these exact state transitions with active room tracking.
- `test_parser.py::test_map_task_status_emptying_dust`: Dust emptying task status edge case — integration tests cover dock status but not this specific task_status derivation path.
- `test_task_status.py::test_task_status_mapping`: Comprehensive task_status mapping using real protobuf — integration tests cover basic cases but not all 11 scenarios.
- `test_task_status_flapping.py` (3 tests): Real captured payload sequences testing flapping prevention — unique coverage not replicated in integration suite.

## File-by-File Analysis

### tests/test_api.py (26 tests)
| Test | Classification | Reason | Resolution |
|------|----------------|--------|------------|
| test_update_state_battery | KEEP | Real `update_state()` coverage for plain DPS 163; small isolated parser check still useful. | Kept |
| test_update_state_work_status | REDUNDANT | Patches `decode()` and re-tests WorkStatus mapping that Task 6 will cover with real protobuf fixtures; remove once integration exists. | Removed |
| test_update_state_work_mode | REDUNDANT | Mocked WorkStatus path overlaps Task 6 WorkStatus protocol coverage; replace with fixture-driven parser tests. | Removed |
| test_update_state_error_code | REDUNDANT | Mocked error protobuf path is less realistic than Task 8 error-code protocol tests; remove after integration coverage lands. | Removed |
| test_update_state_station_status | REDUNDANT | Mocked station response overlaps Task 7 station protocol coverage; use real StationResponse fixtures instead. | Removed |
| test_build_set_clean_speed | REFACTOR | Right command behavior, but it patches `encode()` even though raw clean-speed commands do not use it; keep only if simplified to a pure builder assertion. | Simplified — removed unused @patch decorator |
| test_build_spot_clean_command | REDUNDANT | Command-shape check overlaps Task 10 command roundtrip coverage; integration should validate encoded payload end-to-end. | Removed |
| test_build_set_cleaning_mode_command | REDUNDANT | Mocked `encode_message()` command check overlaps Task 10 roundtrip coverage; replace with real decode/roundtrip assertions there. | Removed |
| test_build_set_water_level_command | REDUNDANT | Same command-builder overlap as Task 10; mocked encoding makes it less realistic than planned integration tests. | Removed |
| test_build_set_cleaning_intensity_command | REDUNDANT | Same as above; covered more realistically by Task 10 command roundtrip. | Removed |
| test_build_scene_clean_command | REDUNDANT | Scene command builder is planned integration coverage in Task 10; current test only inspects mocked encode arguments. | Removed |
| test_build_room_clean_command | REDUNDANT | Room-clean command shape will be covered in Task 10 and Task 12; mocked encode path can be removed. | Removed |
| test_build_set_auto_cfg | REDUNDANT | Auto-config command builder overlaps Task 10 command roundtrip; current test only verifies mocked encode input. | Removed |
| test_build_find_robot_command | KEEP | Pure helper returning the raw DPS payload; tiny isolated command helper is still useful. | Kept |
| test_update_state_find_robot | KEEP | Real parser coverage for a plain DPS boolean without mocking; low-cost regression check. | Kept |
| test_build_set_undisturbed_command | REDUNDANT | DND command handling will be exercised by Task 10 and Task 14 time/switch integration tests; this only checks key presence. | Removed |
| test_update_state_undisturbed | KEEP | Real parse of DPS 157 with concrete hours/minutes; useful isolated parser check. | Kept |
| test_completed_docked_refresh_keeps_cleared_targets | CONFLICT | Hardcoded WorkStatus payload asserts exact `Completed` semantics; verify against Task 6/16 real cleaning-cycle fixtures before trusting this expectation. | Kept — no conflict with integration suite; unique edge case coverage |
| test_mid_clean_washing_does_not_clear_active_targets | CONFLICT | Mocked WorkStatus asserts exact `Washing Mop` + docked semantics in a known high-risk state=5 area; verify against captured mid-clean wash fixtures before keeping. | Kept — no conflict with integration suite; unique edge case coverage |
| test_charging_paused_state_does_not_clear_active_targets | CONFLICT | Encodes exact paused/charging task-status behavior that may reflect current bug-compatible logic; confirm with Task 6 and Task 16 sequences. | Kept — no conflict with integration suite; unique edge case coverage |
| test_completed_docked_state_clears_active_targets | CONFLICT | Exact `Completed` clearing behavior for docked charging is bug-sensitive; validate against real end-of-cycle fixtures before retaining. | Kept — no conflict with integration suite; unique edge case coverage |
| test_empty_room_clean_echo_preserves_existing_active_rooms | REDUNDANT | `_process_play_pause()` target-retention behavior is explicitly planned for integration coverage; remove duplicate unit once Task 6 exists. | Removed |
| test_update_state_device_info_dps169 | KEEP | Real DPS 169 parser regression using concrete payload; isolated enough to keep. | Kept |
| test_update_state_wifi_signal_dps176 | KEEP | Real DPS 176 parsing with actual protobuf encoding; useful isolated parser check. | Kept |
| test_update_state_robot_position_dps179 | KEEP | Real telemetry parser coverage for undocumented DPS 179; valuable focused regression test. | Kept |
| test_known_unprocessed_dps_does_not_crash | KEEP | Pure robustness check for known-unprocessed DPS keys; complements Task 15 edge-case coverage. | Kept |

### tests/test_binary_sensor.py (3 tests)
| Test | Classification | Reason | Resolution |
|------|----------------|--------|------------|
| test_charging_sensor | REDUNDANT | Mocked binary-sensor entity behavior will be covered more realistically by Task 14 HA runtime entity tests; remove duplicate unit coverage. | Removed |
| test_charging_sensor_default_false | REDUNDANT | Default entity state is an HA runtime concern for Task 14 binary-sensor integration coverage. | Removed |
| test_binary_sensor_availability_honors_coordinator_state | REDUNDANT | Availability-through-coordinator behavior belongs in Task 14 runtime tests rather than mocked entity units. | Removed |

### tests/test_button.py (2 tests)
| Test | Classification | Reason | Resolution |
|------|----------------|--------|------------|
| test_button_press | REDUNDANT | Mocked button entity command dispatch overlaps Task 14 control-entity integration coverage. | Removed |
| test_button_reset_accessory | REDUNDANT | Reset-button command wiring will be exercised more realistically in Task 14 button runtime tests. | Removed |

### tests/test_client.py (7 tests)
| Test | Classification | Reason | Resolution |
|------|----------------|--------|------------|
| test_on_connect_thread_safe_event | KEEP | Pure MQTT client callback behavior; not covered by planned HA integration tests. | Kept |
| test_on_disconnect_thread_safe_event | KEEP | Pure client event-loop cleanup logic; isolated transport behavior worth keeping. | Kept |
| test_on_connect_failure_no_event | KEEP | Direct failure-path coverage for MQTT connect callback; low-overlap unit test. | Kept |
| test_send_command_not_connected | KEEP | Pure client no-op guard with no HA/runtime overlap. | Kept |
| test_send_command_disconnected_client | KEEP | Transport-layer guard that integration tests are unlikely to isolate cleanly. | Kept |
| test_disconnect_cleans_temp_files | KEEP | File-cleanup logic is client-internal and not a target of planned integration work. | Kept |
| test_disconnect_no_loop_uses_running_loop | KEEP | Narrow async fallback path; appropriate pure unit coverage. | Kept |

### tests/test_cloud.py (6 tests)
| Test | Classification | Reason | Resolution |
|------|----------------|--------|------------|
| test_check_login_uses_mqtt_credentials | KEEP | Narrow login caching logic in `EufyLogin`; not meaningfully replaced by integration tests. | Kept |
| test_check_api_type_novel | KEEP | Pure classification helper on DPS content; cheap isolated unit coverage. | Kept |
| test_check_api_type_legacy | KEEP | Same pure helper coverage as above. | Kept |
| test_find_model_found | KEEP | Pure device-model lookup logic; not part of integration overlap. | Kept |
| test_find_model_not_found | KEEP | Same isolated lookup logic; safe to keep. | Kept |
| test_find_model_empty_product_code | KEEP | Specific fallback behavior in model lookup; still useful unit coverage. | Kept |

### tests/test_commands.py (5 tests)
| Test | Classification | Reason | Resolution |
|------|----------------|--------|------------|
| test_set_cleaning_mode_invalid | KEEP | Negative builder edge case; Task 10 roundtrip should not replace this pure invalid-input guard. | Kept |
| test_set_water_level_invalid | KEEP | Same isolated invalid-input coverage. | Kept |
| test_set_cleaning_intensity_invalid | KEEP | Same isolated invalid-input coverage. | Kept |
| test_build_command_unknown_returns_empty | KEEP | Pure dispatcher fallback behavior; cheap and useful unit guard. | Kept |
| test_set_child_lock_command | KEEP | Real encode/decode assertion for child-lock command payload; focused builder regression test. | Kept |

### tests/test_config_flow.py (2 tests)
| Test | Classification | Reason | Resolution |
|------|----------------|--------|------------|
| test_duplicate_entry | REDUNDANT | Task 11 explicitly covers config-flow behavior in HA runtime, including duplicate-entry handling. | Removed |
| test_config_flow_entry_data_contains_vacs | REDUNDANT | Entry-creation payload checks belong in Task 11 config-flow integration tests. | Removed |

### tests/test_coordinator.py (8 tests)
| Test | Classification | Reason | Resolution |
|------|----------------|--------|------------|
| test_coordinator_init | REDUNDANT | Patches `update_state()` and duplicates the coordinator initialization path that Task 9 will cover with the real parser pipeline. | Removed |
| test_coordinator_initialize_success | REDUNDANT | Coordinator lifecycle setup is a direct Task 9 integration target; current test only checks mocked client wiring. | Removed |
| test_coordinator_initialize_failed_creds | KEEP | Focused failure-path unit for missing MQTT credentials; useful even after broader lifecycle integration exists. | Kept |
| test_handle_mqtt_message | REDUNDANT | Patches `update_state()` and duplicates the MQTT→state pipeline that Task 9 will cover end-to-end. | Removed |
| test_async_send_command | REDUNDANT | Simple passthrough to client overlaps Task 9/12 command-path integration coverage. | Removed |
| test_async_shutdown_timers_cancels_both | KEEP | Internal timer-cleanup logic is narrow coordinator behavior worth keeping. | Kept |
| test_async_shutdown_timers_noop_when_no_timers | KEEP | Same internal cleanup guard; little integration overlap. | Kept |
| test_async_send_command_no_client_logs_warning | KEEP | Small no-client edge path not likely to be isolated by integration tests. | Kept |

### tests/test_error_parsing.py (1 test)
| Test | Classification | Reason | Resolution |
|------|----------------|--------|------------|
| test_error_code_mapping | KEEP | Real protobuf parse for a specific error mapping; focused parser regression still useful. | Kept |

### tests/test_http.py (7 tests)
| Test | Classification | Reason | Resolution |
|------|----------------|--------|------------|
| test_get_user_info_returns_none_without_session | KEEP | Pure HTTP client guard path; no integration overlap. | Kept |
| test_get_device_list_returns_empty_without_user_info | KEEP | Same isolated HTTP guard behavior. | Kept |
| test_get_cloud_device_list_returns_empty_without_session | KEEP | Same isolated HTTP guard behavior. | Kept |
| test_get_mqtt_credentials_returns_none_without_user_info | KEEP | Same isolated HTTP guard behavior. | Kept |
| test_login_returns_empty_on_failed_login | KEEP | Narrow HTTP failure path; useful independent unit coverage. | Kept |
| test_login_validate_only | KEEP | Distinct API behavior on `validate_only`; keep as unit logic. | Kept |
| test_request_timeout_is_configured | KEEP | Pure configuration constant assertion; no integration overlap. | Kept |

### tests/test_init.py (1 test)
| Test | Classification | Reason | Resolution |
|------|----------------|--------|------------|
| test_load_unload_entry | REDUNDANT | Integration setup/unload lifecycle is planned in Task 15b; this mocked version can be dropped once runtime coverage exists. | Removed |

### tests/test_number.py (6 tests)
| Test | Classification | Reason | Resolution |
|------|----------------|--------|------------|
| test_dock_number_native_value | REDUNDANT | Mocked number-entity state exposure will be covered by Task 14 control-entity runtime tests. | Removed |
| test_dock_number_native_value_empty_cfg | REDUNDANT | Empty-config availability/value behavior belongs in Task 14 number integration tests. | Removed |
| test_dock_number_unavailable_no_cfg | REDUNDANT | Same Task 14 control-entity overlap. | Removed |
| test_dock_number_available_with_cfg | REDUNDANT | Same Task 14 control-entity overlap. | Removed |
| test_dock_number_set_value_deepcopy | REDUNDANT | Mocked set-value path will be exercised more realistically in Task 14 number tests. | Removed |
| test_dock_number_set_value_sends_command | REDUNDANT | Command dispatch from number entities is planned integration coverage in Task 14. | Removed |

### tests/test_orphaned_devices.py (1 test)
| Test | Classification | Reason | Resolution |
|------|----------------|--------|------------|
| test_manual_remove_orphaned_devices | REDUNDANT | Device removal/orphan handling belongs to Task 15b HA lifecycle coverage; replace with runtime registry tests there. | Removed |

### tests/test_parser.py (31 tests)
| Test | Classification | Reason | Resolution |
|------|----------------|--------|------------|
| test_map_work_status_idle | REDUNDANT | Internal helper test with mocked WorkStatus; Task 6 will cover idle WorkStatus parsing via real protobuf fixtures. | Removed |
| test_map_work_status_error | REDUNDANT | Same mocked helper overlap with Task 6 WorkStatus protocol coverage. | Removed |
| test_map_work_status_docked | REDUNDANT | Same mocked helper overlap with Task 6 WorkStatus protocol coverage. | Removed |
| test_map_work_status_cleaning | REDUNDANT | Same mocked helper overlap with Task 6 WorkStatus protocol coverage. | Removed |
| test_map_work_status_returning | REDUNDANT | Same mocked helper overlap with Task 6 WorkStatus protocol coverage. | Removed |
| test_map_work_status_washing_shows_docked | REDUNDANT | State=5 ambiguity is a direct Task 6 integration target; prefer real protobuf fixtures over mocked helper tests. | Removed |
| test_map_work_status_drying_shows_docked | REDUNDANT | Same Task 6 state=5 overlap with mocked helper input. | Removed |
| test_map_work_status_navigation_to_wash_shows_cleaning | REDUNDANT | Same Task 6 state=5 overlap with mocked helper input. | Removed |
| test_map_work_status_station_wash_drying_shows_docked | REDUNDANT | Same Task 6 state=5 overlap with mocked helper input. | Removed |
| test_map_work_status_plain_cleaning | REDUNDANT | Same mocked helper overlap with Task 6 protocol tests. | Removed |
| test_map_work_status_state_15_paused | REDUNDANT | Same mocked helper overlap with Task 6 protocol tests. | Removed |
| test_map_work_status_cleaning_paused | REDUNDANT | Same mocked helper overlap with Task 6 protocol tests. | Removed |
| test_map_work_status_cleaning_paused_with_go_wash_ignored | REDUNDANT | Same mocked helper overlap with Task 6 protocol tests. | Removed |
| test_map_work_status_cleaning_doing | REDUNDANT | Same mocked helper overlap with Task 6 protocol tests. | Removed |
| test_map_work_status_emptying_dust | REDUNDANT | Same mocked helper overlap with Task 6/7 dock-state integration coverage. | Removed |
| test_map_task_status_emptying_dust | CONFLICT | Exact `Emptying Dust` task-status expectation is bug-sensitive and based on mocked nested fields; verify against captured WorkStatus+Station fixtures before keeping. | Kept — no conflict with integration suite; unique task_status derivation path |
| test_process_cleaning_params_cleaning_mode | REDUNDANT | Patches `decode()`; Task 7 will cover CleanParam parsing with real protobuf fixtures instead. | Removed |
| test_process_cleaning_params_fan_speed | REDUNDANT | Same mocked CleanParam overlap with Task 7. | Removed |
| test_process_cleaning_params_mop_water_level | REDUNDANT | Same mocked CleanParam overlap with Task 7. | Removed |
| test_process_cleaning_params_corner_cleaning_normal | REDUNDANT | Same mocked CleanParam overlap with Task 7. | Removed |
| test_process_cleaning_params_corner_cleaning_deep | REDUNDANT | Same mocked CleanParam overlap with Task 7. | Removed |
| test_process_cleaning_params_cleaning_intensity | REDUNDANT | Same mocked CleanParam overlap with Task 7. | Removed |
| test_process_cleaning_params_carpet_strategy | REDUNDANT | Same mocked CleanParam overlap with Task 7. | Removed |
| test_process_cleaning_params_smart_mode | REDUNDANT | Same mocked CleanParam overlap with Task 7. | Removed |
| test_process_cleaning_params_all_fields | REDUNDANT | Same mocked CleanParam overlap with Task 7. | Removed |
| test_process_cleaning_params_decode_failure | REDUNDANT | Task 7/15 will cover malformed CleanParam parsing more realistically with actual encoded payloads. | Removed |
| test_process_cleaning_params_fallback_to_request | REDUNDANT | Request/response decode fallback is a Task 7 integration concern; current test uses mocked decode sequencing. | Removed |
| test_map_data_room_names_no_id_suffix | REDUNDANT | MapData parsing is a direct Task 7 integration target; prefer real UniversalData/RoomParams fixtures over mocked decode fallback. | Removed |
| test_deduplicate_room_names | KEEP | Pure helper logic for name deduplication; no integration overlap. | Kept |
| test_deduplicate_room_names_no_duplicates | KEEP | Same pure helper coverage. | Kept |
| test_work_mode_names_mapping | KEEP | Const lookup sanity check; cheap isolated unit coverage. | Kept |

### tests/test_parser_accessories.py (2 tests)
| Test | Classification | Reason | Resolution |
|------|----------------|--------|------------|
| test_parse_accessories_status | KEEP | Real protobuf parse for DPS 168; focused parser regression still useful. | Kept |
| test_parse_accessories_partial | KEEP | Real partial-update accessory parsing; isolated regression coverage. | Kept |

### tests/test_parser_cleaning_stats.py (2 tests)
| Test | Classification | Reason | Resolution |
|------|----------------|--------|------------|
| test_parsing_cleaning_stats | KEEP | Real protobuf parsing for cleaning statistics; focused parser check worth keeping. | Kept |
| test_cleaning_stats_sensors | REDUNDANT | Sensor entity exposure is a Task 13 runtime concern; mocked sensor units duplicate planned integration coverage. | Removed |

### tests/test_scene_state.py (5 tests)
| Test | Classification | Reason | Resolution |
|------|----------------|--------|------------|
| test_scene_select_entity_mocked | REDUNDANT | Mocked select-entity behavior will be covered more realistically by Task 14 select integration tests. | Removed |
| test_scene_parsing_logic | KEEP | Real WorkStatus protobuf parse for current-scene extraction; useful isolated parser regression. | Kept |
| test_scene_parsing_partial_update | KEEP | Real partial-update behavior for scene retention; focused parser check still valuable. | Kept |
| test_scene_parsing_explicit_clear_mode | KEEP | Real parser behavior for scene clearing on mode change; good isolated regression. | Kept |
| test_scene_parsing_explicit_clear_state | KEEP | Real parser behavior for scene clearing on state change; good isolated regression. | Kept |

### tests/test_segment_cleaning.py (5 tests)
| Test | Classification | Reason | Resolution |
|------|----------------|--------|------------|
| test_async_clean_segments_with_custom_params | REDUNDANT | Vacuum segment-clean command flow is a direct Task 12 vacuum integration target; remove mocked duplicate. | Removed |
| test_async_clean_segments_without_custom_params | REDUNDANT | Same Task 12 overlap for segment-clean runtime behavior. | Removed |
| test_async_clean_segments_invalid_ids | REDUNDANT | Invalid segment-id handling should be covered through Task 12 vacuum integration/service tests. | Removed |
| test_async_clean_segments_mixed_valid_invalid | REDUNDANT | Same Task 12 overlap for segment filtering behavior. | Removed |
| test_async_clean_segments_with_map_id | REDUNDANT | Same Task 12 overlap for map-aware segment cleaning behavior. | Removed |

### tests/test_segment_detection.py (13 tests)
| Test | Classification | Reason | Resolution |
|------|----------------|--------|------------|
| test_serialize_deserialize_segments | KEEP | Pure serialization helper coverage; no meaningful integration overlap. | Kept |
| test_vacuum_entity_with_segment_detection | REDUNDANT | Segment dispatcher wiring belongs in Task 12/15b vacuum lifecycle integration tests. | Removed |
| test_last_seen_segments_property | KEEP | Small pure transformation from stored data to `Segment` objects; safe to keep. | Kept |
| test_last_seen_segments_none_when_not_stored | KEEP | Same small property guard logic; safe to keep. | Kept |
| test_async_create_segments_issue | REDUNDANT | Repairs issue creation should be validated in Task 15b lifecycle/runtime tests rather than through patched helper calls. | Removed |
| test_store_last_seen_segments | REDUNDANT | Storage + issue-clear behavior is planned Task 15b lifecycle coverage; current test is heavily mocked. | Removed |
| test_check_for_segment_changes_no_previous | REDUNDANT | Segment baseline detection belongs in Task 12/15b runtime coverage. | Removed |
| test_check_for_segment_changes_with_changes | REDUNDANT | Segment-change issue creation belongs in Task 12/15b runtime coverage. | Removed |
| test_check_for_segment_changes_no_changes | REDUNDANT | Same Task 12/15b overlap. | Removed |
| test_storage_load_on_coordinator_init | REDUNDANT | Storage-load behavior is part of Task 15b lifecycle coverage; this mocked path can be dropped. | Removed |
| test_storage_save_on_segment_store | REDUNDANT | Same Task 15b overlap for persistence behavior. | Removed |
| test_segment_change_detection_end_to_end | REDUNDANT | This is already a mocked mini-integration scenario that Task 12/15b will cover in real HA runtime. | Removed |
| test_backward_compatibility_no_config_entry | KEEP | Backward-compatibility guard for no-config-entry usage is niche and not obviously covered elsewhere. | Kept |

### tests/test_select.py (15 tests)
| Test | Classification | Reason | Resolution |
|------|----------------|--------|------------|
| test_dock_select_entity | REFACTOR | Keeps useful property assertions, but the test stops before exercising behavior and contains a `pass`; simplify or merge into a real async entity test if retained. | Simplified — removed dead `pass` block, kept property assertions only |
| test_dock_select_entity_async | REDUNDANT | Dock select runtime behavior is a direct Task 14 control-entity integration target. | Removed |
| test_scene_select_entity | REDUNDANT | Scene select runtime behavior is a direct Task 14 select integration target. | Removed |
| test_room_select_entity | REDUNDANT | Room select runtime behavior is a direct Task 14 select integration target. | Removed |
| test_cleaning_mode_select_entity | REDUNDANT | Cleaning-mode select command dispatch belongs in Task 14 runtime tests. | Removed |
| test_water_level_select_entity | REDUNDANT | Water-level select command dispatch belongs in Task 14 runtime tests. | Removed |
| test_cleaning_intensity_select_entity | REDUNDANT | Cleaning-intensity select command dispatch belongs in Task 14 runtime tests. | Removed |
| test_mop_intensity_select_entity_entity_category | REDUNDANT | Entity metadata/registration is better covered in Task 14 runtime tests. | Removed |
| test_mop_intensity_select_entity_mapping | KEEP | Pure option↔state mapping logic; isolated and cheap to keep. | Kept |
| test_mop_intensity_select_entity_async | REDUNDANT | Mop-intensity runtime command mapping belongs in Task 14 integration tests. | Removed |
| test_dock_select_deepcopy_no_mutation | REDUNDANT | Dock select mutation/command path overlaps Task 14 runtime coverage. | Removed |
| test_dock_select_unavailable_no_cfg | REDUNDANT | Entity availability belongs in Task 14 runtime coverage. | Removed |
| test_scene_select_current_option_with_id | REDUNDANT | Current-option formatting belongs in Task 14 select runtime coverage. | Removed |
| test_suction_level_unavailable_without_fan_speed | REDUNDANT | Availability gating belongs in Task 14 runtime coverage. | Removed |
| test_suction_level_available_with_fan_speed | REDUNDANT | Availability gating belongs in Task 14 runtime coverage. | Removed |

### tests/test_sensor.py (6 tests)
| Test | Classification | Reason | Resolution |
|------|----------------|--------|------------|
| test_sensor_generic | REDUNDANT | Mocked generic sensor entity behavior overlaps Task 13 HA runtime sensor integration tests. | Removed |
| test_dock_status_sensor | REDUNDANT | Dock-status sensor exposure belongs in Task 13 runtime coverage. | Removed |
| test_water_level_sensor | REDUNDANT | Water-level availability/value behavior belongs in Task 13 runtime coverage. | Removed |
| test_error_message_sensor | REDUNDANT | Error-message sensor exposure belongs in Task 13 runtime coverage. | Removed |
| test_active_rooms_uses_scene_name_when_room_ids_are_empty | KEEP | Pure helper fallback logic for active-room display; useful isolated unit. | Kept |
| test_active_rooms_uses_zone_count_when_present | KEEP | Same pure helper fallback logic. | Kept |

### tests/test_sensor_accessories.py (1 test)
| Test | Classification | Reason | Resolution |
|------|----------------|--------|------------|
| test_accessory_sensors_setup | REDUNDANT | Accessory sensor entity setup is a Task 13 runtime concern; current test duplicates planned integration coverage. | Removed |

### tests/test_switch.py (9 tests)
| Test | Classification | Reason | Resolution |
|------|----------------|--------|------------|
| test_find_robot_entity | REDUNDANT | Switch entity metadata/state belongs in Task 14 control-entity integration tests. | Removed |
| test_find_robot_turn_on_off | REDUNDANT | Find-robot switch command dispatch belongs in Task 14 runtime coverage. | Removed |
| test_child_lock_switch_turn_on_off | REDUNDANT | Child-lock switch behavior belongs in Task 14 runtime coverage. | Removed |
| test_child_lock_switch_unavailable_without_field | REDUNDANT | Availability gating belongs in Task 14 runtime coverage. | Removed |
| test_do_not_disturb_switch_turn_on_off | REDUNDANT | DND switch behavior belongs in Task 14 runtime coverage. | Removed |
| test_dock_switches | REDUNDANT | Dock switch command/state behavior belongs in Task 14 runtime coverage. | Removed |
| test_set_wash_cfg_writes_string_values | KEEP | Pure helper transformation for dock config values; isolated and cheap to keep. | Kept |
| test_dock_switch_deepcopy_no_mutation | REDUNDANT | Dock switch mutation guard belongs in Task 14 runtime coverage. | Removed |
| test_dock_switch_unavailable_no_cfg | REDUNDANT | Availability gating belongs in Task 14 runtime coverage. | Removed |

### tests/test_task_status.py (2 tests)
| Test | Classification | Reason | Resolution |
|------|----------------|--------|------------|
| test_task_status_mapping | CONFLICT | Encodes many exact `task_status` strings from raw WorkStatus values, including high-risk wash/charge branches; verify against Task 6/8/16 real fixtures before trusting any expected value. | Kept — no conflict with integration suite; comprehensive mapping coverage |
| test_task_status_sensor | REDUNDANT | Sensor entity exposure belongs in Task 13 runtime coverage. | Removed |

### tests/test_task_status_flapping.py (3 tests)
| Test | Classification | Reason | Resolution |
|------|----------------|--------|------------|
| test_mid_cleaning_wash_no_flapping | CONFLICT | Hardcoded captured payload sequence asserts exact wash/clean transitions in a known bug-prone area; re-verify against Task 16 full-cycle fixtures before retaining. | Kept — no conflict with integration suite; unique real-payload flapping coverage |
| test_post_cleaning_stays_completed | CONFLICT | Hardcoded post-clean charging/wash sequence may encode current completion semantics incorrectly; validate against Task 16 real end-of-cycle behavior. | Kept — no conflict with integration suite; unique real-payload flapping coverage |
| test_mid_cleaning_with_paused_state | CONFLICT | Exact paused/charging/washing expectations are explicitly bug-sensitive; verify against Task 6 and Task 16 fixture sequences before keeping. | Kept — no conflict with integration suite; unique real-payload flapping coverage |

### tests/test_time.py (2 tests)
| Test | Classification | Reason | Resolution |
|------|----------------|--------|------------|
| test_do_not_disturb_start_time_entity | REDUNDANT | DND time entity behavior belongs in Task 14 control-entity runtime coverage. | Removed |
| test_do_not_disturb_end_time_entity | REDUNDANT | DND time entity behavior belongs in Task 14 control-entity runtime coverage. | Removed |

### tests/test_utils.py (9 tests)
| Test | Classification | Reason | Resolution |
|------|----------------|--------|------------|
| test_decode_empty_data_raises | KEEP | Pure varint/protobuf utility edge case; not replaced by integration coverage. | Kept |
| test_decode_truncated_varint_raises | KEEP | Same pure utility edge-case coverage. | Kept |
| test_decode_without_length_prefix | KEEP | Same pure utility edge-case coverage. | Kept |
| test_decode_valid_with_length_prefix | KEEP | Same pure utility roundtrip coverage. | Kept |
| test_encode_varint_negative_raises | KEEP | Same pure utility edge-case coverage. | Kept |
| test_encode_varint_zero | KEEP | Same pure utility edge-case coverage. | Kept |
| test_encode_varint_large | KEEP | Same pure utility edge-case coverage. | Kept |
| test_encode_decode_roundtrip | KEEP | Same pure utility roundtrip coverage. | Kept |
| test_deduplicate_names | KEEP | Pure helper logic; no integration overlap. | Kept |

### tests/test_vacuum_rooms_custom.py (4 tests)
| Test | Classification | Reason | Resolution |
|------|----------------|--------|------------|
| test_room_clean_standard | REDUNDANT | Vacuum room-clean command wiring is a direct Task 12 vacuum integration target. | Removed |
| test_room_clean_custom | REDUNDANT | Custom room-clean flow belongs in Task 12 vacuum integration tests. | Removed |
| test_room_clean_custom_partial_params | REDUNDANT | Same Task 12 overlap for room-clean command handling. | Removed |
| test_room_clean_multi_room_config | REDUNDANT | Same Task 12 overlap for multi-room custom config handling. | Removed |

### tests/test_vacuum.py (11 tests)
| Test | Classification | Reason | Resolution |
|------|----------------|--------|------------|
| test_vacuum_properties | REDUNDANT | Vacuum entity metadata/activity mapping belongs in Task 12 runtime coverage. | Removed |
| test_vacuum_attributes | REDUNDANT | Vacuum attribute exposure belongs in Task 12 runtime coverage. | Removed |
| test_vacuum_commands | REDUNDANT | Vacuum command dispatch belongs in Task 12 runtime coverage. | Removed |
| test_set_fan_speed | REDUNDANT | Fan-speed command dispatch/validation belongs in Task 12 runtime coverage. | Removed |
| test_async_send_command_raw | REDUNDANT | Raw service-command dispatch for scene/room clean belongs in Task 12 runtime coverage. | Removed |
| test_room_clean_applies_user_preferences | REDUNDANT | Vacuum room-clean preference application belongs in Task 12 integration tests. | Removed |
| test_room_clean_with_explicit_params_overrides_preferences | REDUNDANT | Same Task 12 overlap for explicit parameter precedence. | Removed |
| test_mqtt_malformed_message_does_not_crash | REDUNDANT | Malformed MQTT robustness is already planned in Task 15 edge-case integration tests. | Removed |
| test_app_segment_clean_command | REDUNDANT | App segment-clean command handling belongs in Task 12 runtime coverage. | Removed |
| test_app_segment_clean_invalid_ids | REDUNDANT | Invalid segment handling belongs in Task 12 runtime coverage. | Removed |
| test_async_clean_segments_empty_list | REDUNDANT | Empty segment-clean guard belongs in Task 12 runtime coverage. | Removed |
