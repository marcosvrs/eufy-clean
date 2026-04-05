
## Task 17: Unit Test Audit Resolution

### Key Findings
- 119 REDUNDANT tests removed across 21 files (195 → 76 unit tests)
- 9 CONFLICT tests investigated: **all agree** with integration suite (no actual conflicts)
- 2 REFACTOR tests simplified:
  - `test_build_set_clean_speed`: removed unused `@patch("...encode")` decorator
  - `test_dock_select_entity`: removed dead `pass` block and unused async test setup
- All 65 KEEP tests retained untouched

### Patterns
- Files where ALL tests were REDUNDANT: left as comment-only files (not deleted per task constraints)
- CONFLICT tests provide unique edge case coverage for: active target clearing, task status flapping, emptying dust status
- The integration suite covers broad behavior; unit tests remain valuable for pure helpers, edge cases, and transport-layer logic

### Verification Results
- Unit tests: 76 passed, 0 failures
- Integration tests: 260 passed, 0 failures
- Duplicate test names: 0

## Task: Replace Synthetic Fixtures with Real Captured Data

### What was done
- Replaced all 5 HTTP fixtures with real anonymized captured data from `/tmp/eufy_anon_1/http/`
- Replaced 17 MQTT fixtures with real captured proto bytes (work_status, station_status, cleaning_params, accessories, cleaning_stats, dps_plain, error_code)
- Kept 14 MQTT fixtures as synthetic (marked with "SYNTHETIC:" prefix in description) where no real data was captured
- Built 2 real sequence fixtures from actual captured message timestamps
- Updated `test_parser_work_status.py`: 12 tests now load real fixture bytes via `load_fixture()`
- Updated `test_coordinator.py`: 1 test now loads real fixture bytes

### Discovered Parser Bugs (from real data)
1. **charging=True during cleaning**: Real WorkStatus has `charging {}` (empty Charging message) even during CLEANING state. Parser interprets presence of Charging field as charging=True. Bug: should check `charging.state` value, not just field presence.
2. **trigger_source for AUTO mode**: Real auto-clean message has `mode=AUTO (value=0)` with no trigger field. Since AUTO (0) is NOT in APP_TRIGGER_MODES (1-9), trigger_source correctly resolves to "unknown". The trigger_app fixture was updated to use this real data, exposing that the test expectation was wrong for AUTO mode.
3. **dock_status from go_wash**: Real washing data sends only DPS 153 with `go_wash.mode=WASHING` — no DPS 173 in same message. Parser may need to detect dock activity from go_wash alone.
4. **Station washing → "Recycling waste water"**: Real station washing data has additional fields (clear_water_adding, waste_water_recycling) that cause parser to report "Recycling waste water" instead of "Washing".

### Verification Results
- Unit tests: 76 passed, 0 failures
- Integration tests: 256 passed, 4 failed (all assertion failures from discovered bugs, 0 infrastructure errors)

## Task: Complete Fixture and Test Coverage for All 102 Captured DPS Values

### What was done
- Decoded and classified all 102 unique captured DPS values from /tmp/eufy_anon_1/mqtt/
- Created 42 new fixture files (bringing total from ~37 to 79 fixtures)
- Added 48 new integration tests (bringing total from ~260 to 326)
- Every fixture is now exercised by at least one test via load_fixture()

### DPS Key Coverage Summary
| DPS Key | Proto Type | Captured | Unique | Fixtures |
|---------|-----------|----------|--------|----------|
| 152 | ModeCtrlRequest | 9 | 9 | 6 (deduplicated by method) |
| 153 | WorkStatus | 28 | 17 | 13 new + 14 existing = 27 |
| 154 | CleanParamResponse | 2 | 2 | 1 new + 2 existing = 3 |
| 158 | plain int | 2 | 2 | 1 new + 1 existing = 2 |
| 164 | MapEditRequest | 1 | 1 | 1 new |
| 167 | CleanStatistics | 1 | 1 | 1 existing |
| 168 | ConsumableResponse | 6 | 6 | 2 new + 2 existing = 4 |
| 169 | DeviceInfo | 2 | 1 | 1 new |
| 173 | StationResponse | 34 | 20 | 5 new + 4 existing = 9 |
| 176 | UnisettingResponse | 2 | 2 | 2 new |
| 177 | ErrorCode | 15 | 15 | 2 new + 2 existing = 4 |
| 178 | Unknown (KNOWN_UNPROCESSED) | 1 | 1 | 1 new |
| 179 | Robot telemetry | 25 | 25 | 7 new |

### Key Deduplication Decisions
- DPS 152: 9 unique → 6 fixtures (multiple PAUSE_TASK/START_GOHOME with only seq# differences)
- DPS 153: 17 unique → 27 fixtures (some pre-existing synthetic fixtures kept; all real states covered)
- DPS 173: 20 unique → 9 fixtures (heavy dedup of washing states that only differ in water level countdown)
- DPS 177: 15 unique → 4 fixtures (all no-error; two semantic variants: with/without warn_mask)
- DPS 179: 25 unique → 7 fixtures (position updates with same structure but different coords/timestamps)

### DPS 176 Discovery
- DPS 176 maps to DPS_MAP["UNSETTING"] = UnisettingResponse, NOT unknown
- Contains WiFi signal strength (ap_signal_strength), children_lock, water_level_sw, mop holder states
- Parser converts: wifi_signal = (ap_signal_strength / 2) - 100 (dBm)

### Known Parser Bugs (same 4 as before, not fixed per task constraints)
1. test_state_5_station_washing_is_docked — dock_status reports "Recycling waste water" not "Washing"
2. test_trigger_source_app — trigger_source for AUTO mode is "unknown" not "app"
3. test_charging_false_when_cleaning — charging=True when WorkStatus has empty Charging message
4. test_dock_wash_dry_cycle — E2E sequence fails due to bug #1

### Verification Results
 - Integration tests: 326 passed, 4 failed (same 4 known parser bugs, 0 infrastructure errors)
 - Unit tests: 76 passed, 0 failures
 - All 79 fixture files exercised by at least one test

## Task: eufy_mqtt_client DPS display cleanup

### What worked
- Added lazy protobuf imports so the standalone tool still runs outside the repo tree.
- Kept DPS 169 readable by stripping the length prefix and printing printable strings from the blob.
- Reused one decoder path for DPS 153/173/176/177 so status output is consistent.

### Notes
- `DPS_MAP` now includes the real captured keys 164, 169, 176, 177, 178, 179, and 180.
- Timestamp headers in `_on_message()` make live MQTT logs easier to scan.
