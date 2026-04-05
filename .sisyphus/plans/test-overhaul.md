# Integration Test Suite with Real-World Fixtures

## TL;DR

> **Quick Summary**: Build a comprehensive integration/E2E test suite for the eufy-clean HA integration using real-world data fixtures captured from a live X-Series device. Includes a data capture + anonymization toolchain, fixture infrastructure, and tests organized by functional area — all designed to find real bugs by validating expected behavior rather than mirroring implementation.
> 
> **Deliverables**:
> - Data capture mode added to `tools/eufy_mqtt_client.py` + new `tools/anonymize_fixtures.py` for sanitizing real MQTT/HTTP data
> - Integration test infrastructure (conftest, fixture loaders, mock transport helpers)
> - Realistic sample fixture files for all DPS key types (X-Series)
> - Integration tests covering: parser pipeline, coordinator lifecycle, HA entity behavior, edge cases, full cleaning cycle E2E
> - Audit + cleanup of existing unit tests to eliminate duplication
> - CI pipeline update with integration test job + coverage
> 
> **Estimated Effort**: Large
> **Parallel Execution**: YES — 6 waves (with user checkpoint between Waves 1 and 2)
> **Critical Path**: Task 1 → USER CHECKPOINT → Task 3 → Task 6 → Task 9 → Task 12 → Task 17 → Final Verification

---

## Context

### Original Request
Build an integration test suite that:
- Uses fixtures derived from real account data (anonymized)
- Leverages pytest-homeassistant-custom-component for HA runtime
- Validates expected business behavior, not implementation details
- Primary goal: find bugs through careful behavior verification and edge case exploration
- No production code changes — tests only

### Interview Summary
**Key Discussions**:
- **Real data capture**: Build a recording tool rather than using existing logs. Script connects to Eufy cloud, captures HTTP/MQTT traffic, dumps to JSON files.
- **Scope**: Existing 195 unit tests stay as unit tests. NEW test suite is separate. Everything conflicting or redundant gets refactored/removed.
- **Device coverage**: X-Series (T2261, T2262, T2266, T2276, T2320, T2351) — full feature set including dock station, auto-empty, mop wash/dry.
- **pytest-homeassistant-custom-component evaluation**: Sufficient for HA layer (config flows, coordinator, entity lifecycle). Gap: MQTT transport must be mocked directly since eufy-clean uses Paho MQTT, not HA's MQTT integration. This is not a blocker — it's the natural boundary.

### Research Findings
- **Current test state**: 195 tests across 29 test files. Heavy mocking (MagicMock/AsyncMock). Single conftest.py with only `auto_enable_custom_integrations`. No real data fixtures. No coverage measurement.
- **High-risk areas**: WorkStatus state=5 ambiguity (150+ lines conditional logic), trigger source inference fallback, dock status debouncing (2s timer), dual proto format fallbacks (CleanParam, MapData), task status flapping (known issue).
- **Data flow**: 5 HTTP endpoints (login chain + device discovery), MQTT JSON wrapper with DPS key→base64 protobuf payloads, 12+ DPS keys each with specific proto types.
- **PII fields**: email, device_sn, user_center_id, access/refresh tokens, MQTT certificates/keys, client_id (openudid+user_id), device MAC, wifi SSID/IP.

### Self-Performed Gap Analysis (Metis unavailable)
**Identified Gaps** (addressed in plan):
- **Capture tool scope**: Locked to single-session, single-device recording. No reconnection logic or multi-device orchestration — keep it simple.
- **Fixture freshness**: Sample fixtures are hand-crafted initially. Real fixtures replace them once user runs capture tool. Tests must work with both.
- **Timer testing**: Coordinator dock debouncing uses `async_call_later(2.0)`. Tests need HA's `async_fire_time_changed` to simulate timer expiry.
- **CI separation**: Integration tests should run as a separate CI job to keep unit test feedback fast.

---

## Work Objectives

### Core Objective
Create an integration test suite that exercises real-world behavior of the eufy-clean integration — from MQTT message arrival through protobuf decoding, state management, dock debouncing, and HA entity state updates — using fixtures shaped by real device data.

### Concrete Deliverables
- `tools/eufy_mqtt_client.py` (extended) — `--capture` mode to record HTTP/MQTT data from a live Eufy account
- `tools/anonymize_fixtures.py` — CLI script to strip PII and produce test fixture files
- `tests/integration/conftest.py` — Fixture infrastructure with mock transport, fixture loaders, state factories
- `tests/fixtures/` — Directory with JSON fixture files for all DPS types, HTTP responses, and MQTT sequences
- `tests/integration/test_*.py` — Integration test modules organized by functional area
- Updated `.github/workflows/tests.yaml` — Separate integration test job with coverage

### Definition of Done
- [ ] `pytest tests/integration/` runs to completion (all tests execute without import/infrastructure errors)
- [ ] Test failures are reviewed and categorized: each is either a confirmed bug, a test error, or needs investigation
- [ ] `pytest tests/` (unit tests) still passes with 0 failures
- [ ] No test file imports from both `tests/` and `tests/integration/` testing the same behavior
- [ ] All fixture files are real captured data (anonymized), not synthetically generated
- [ ] CI pipeline runs both unit and integration test jobs

### Must Have
- Fixture files use real captured data from actual Eufy X-Series device (anonymized), captured across multiple sessions
- All PII anonymized in fixture files (no real serials, emails, tokens, MACs)
- Integration tests assert on observable outcomes (VacuumState fields, entity state attributes, HA state machine)
- Coordinator dock debouncing tested with real HA timer simulation (async_fire_time_changed + async_block_till_done)
- WorkStatus state=5 ambiguity tested (cleaning vs docked-washing/drying)
- Edge cases: malformed protobuf, unknown DPS keys, missing/optional fields, payload nesting variants
- Full cleaning cycle test: ordered sequence of MQTT messages representing idle→cleaning→returning→docked
- ALL entity platforms tested: vacuum, sensor, select, switch, button, number, binary_sensor, time
- ALL DPS keys that X-Series uses: 152-154, 157-160, 163, 165, 167-169, 172-173, 176-177, 179-180
- HA lifecycle tested: unload, remove, storage, segment migration
- Parser path _process_play_pause() tested (active room/zone/scene clearing)

### Must NOT Have (Guardrails)
- No production code changes (this is a tests-only plan)
- No duplicate tests: if a behavior is tested in integration tests, it must NOT also be tested in unit tests (deduplicate during audit)
- No mocking of `update_state()` or `build_command()` in integration tests — these are the code under test
- No network access in tests — all HTTP and MQTT transport is mocked at the connection boundary
- No hard-coded magic numbers without named constants or comments explaining the value
- No tests that simply assert the current implementation is correct — define expected behavior FIRST
- No synthetic fixture data that doesn't match real proto message structure (use actual protobuf serialization)
- No `@pytest.mark.skip` without a linked issue/reason (but `@pytest.mark.xfail` IS allowed for discovered bugs — see below)

### Bug Discovery Protocol
When a test reveals a real bug (expected behavior per spec ≠ actual code behavior):
1. The test FAILS — this is the desired outcome. Test failures ARE the bug report.
2. Do NOT add `@pytest.mark.xfail` — let the test fail honestly. A red test = a discovered bug.
3. Do NOT modify production code to fix the bug.
4. After the full suite runs, review failures and categorize each as: **confirmed bug** / **test error** / **needs investigation**.
5. The Definition of Done counts discovered bugs as success, not failure. The suite's purpose is bug-finding.

---

## Verification Strategy

> **ZERO HUMAN INTERVENTION in per-task QA** — All QA scenarios within tasks (1-18) are agent-executed. No exceptions.
> The Final Verification Wave (F1-F4) is also agent-executed, but its results are PRESENTED to the user for approval before marking work complete. This user checkpoint is an orchestration gate, not a test step.

### Test Decision
- **Infrastructure exists**: YES (pytest + pytest-homeassistant-custom-component already configured)
- **Automated tests**: Tests-after (writing tests is the deliverable itself)
- **Framework**: pytest with pytest-homeassistant-custom-component, asyncio_mode="auto"

### QA Policy
Every task MUST include agent-executed QA scenarios.
Evidence saved to `.sisyphus/evidence/task-{N}-{scenario-slug}.{ext}`.

**IMPORTANT — QA interpretation for integration tests:**
When a QA scenario says "Assert all tests pass," this means "tests execute to completion without infrastructure errors." Assertion failures caused by discovered bugs are EXPECTED and ACCEPTABLE — they are the desired outcome. The QA check verifies that tests RUN correctly (no import errors, no missing fixtures, no conftest failures), NOT that every assertion passes. Record the pass/fail breakdown in evidence. A test file with 10 tests where 8 pass and 2 fail (exposing real bugs) is a SUCCESSFUL QA result.

- **Test infrastructure**: Use Bash — run pytest, verify pass/fail counts, check fixture loading
- **Fixture files**: Use Bash (python) — validate JSON schema, protobuf decode roundtrip
- **Integration tests**: Use Bash — run pytest with verbose output, capture assertion details
- **Audit results**: Use Bash — grep for duplication patterns, run both test suites

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (Foundation — no real data needed):
├── Task 1: Extend eufy_mqtt_client.py capture mode + anonymizer [unspecified-high]
├── Task 2: Integration test infrastructure (conftest, directory, mock helpers) [deep]
├── Task 4: Unit test audit — identify overlap with integration scope [deep]
└── Task 5: Fixture helpers: state factory, DPS builder, MQTT wrapper [unspecified-high]

⏸ USER CHECKPOINT: Run capture tool against real device, anonymize data, commit to tests/fixtures/
   → This requires MULTIPLE capture sessions to cover all needed states:
   
   **Session 1 — Normal cleaning cycle** (~5 min):
     1. Start auto clean, let it run for 1-2 min, pause, resume, send home
     2. Captures: WorkStatus states 0/3/4/5/7, battery, cleaning stats, cleaning params
   
   **Session 2 — Dock operations** (~30-60 min, or trigger and wait):
     1. Trigger mop wash (go_selfcleaning), wait for wash→dry cycle
     2. Trigger dust empty if available
     3. Captures: Station status (washing, drying, emptying), dock_status transitions
   
   **Session 3 — Room/scene/settings** (~5 min):
     1. Trigger a scene clean, trigger room-specific clean
     2. Change cleaning parameters (fan speed, water level, mode)
     3. Toggle find robot, child lock, DND
     4. Captures: Scene info, map data, cleaning params, DPS 157/160/176
   
   **For EACH session:**
     1. Run `python tools/eufy_mqtt_client.py --email X --password Y --capture-dir ./raw_capture_N --duration DURATION`
     2. Note timestamps and what vacuum was doing physically
     3. Run `python tools/anonymize_fixtures.py --input-dir ./raw_capture_N --output-dir tests/fixtures`
   
   **States that may require patience or luck:**
   - Error states (wheel stuck, etc.) — may need to physically block the vacuum
   - All trigger variants — app, button, schedule; some may not be capturable on demand
   - DPS 169 (device info) and DPS 179 (telemetry) — may arrive automatically
   
   If a state cannot be captured after reasonable effort, document it in `tests/fixtures/UNCAPTURED.md` and the executor will note the gap in test coverage.

Wave 2 (Fixture organization — requires captured data):
└── Task 3: Organize captured data into fixture directory structure [unspecified-high]

Wave 3 (Protocol/contract tests — all independent, all require Task 3):
├── Task 6: WorkStatus protocol tests [deep]
├── Task 7: Station + CleanParam + MapData protocol tests [deep]
├── Task 8: ErrorCode + TaskStatus + Scene + Accessories + plain DPS protocol tests [unspecified-high]
├── Task 10: Command roundtrip protocol tests [unspecified-high]
├── Task 11: Config flow integration tests [unspecified-high]
└── Task 15: Edge case + robustness tests [deep]

Wave 4 (Coordinator — depends on Task 6):
└── Task 9: Coordinator lifecycle integration tests [deep]

Wave 5 (Entity integration — all depend on Task 9):
├── Task 12: Vacuum entity integration tests [unspecified-high]
├── Task 13: Sensor entity integration tests [unspecified-high]
├── Task 14: Control entity integration tests (select/switch/button/number/time) [unspecified-high]
├── Task 15b: HA lifecycle tests (unload, remove, storage) [unspecified-high]
└── Task 16: Full cleaning cycle E2E tests [deep]

Wave 6 (Polish — after all tests):
├── Task 17: Unit test audit resolution — refactor/remove conflicts [unspecified-high]
└── Task 18: CI pipeline update — integration job + coverage [quick]

Wave FINAL (After ALL tasks — 4 parallel reviews, then user okay):
├── Task F1: Plan compliance audit (oracle)
├── Task F2: Code quality review (unspecified-high)
├── Task F3: Real manual QA (unspecified-high)
└── Task F4: Scope fidelity check (deep)
-> Present results -> Get explicit user okay

Critical Path: Task 1 → USER CHECKPOINT → Task 3 → Task 6 → Task 9 → Task 12 → Task 17 → F1-F4
Max Concurrent: 6 (Wave 3)
```

### Dependency Matrix

| Task | Depends On | Blocks | Wave |
|------|-----------|--------|------|
| 1 | — | USER CHECKPOINT | 1 |
| 2 | — | 6-16, 15b | 1 |
| 4 | — | 17 | 1 |
| 5 | — | 6-16, 15b | 1 |
| USER CHECKPOINT | 1 | 3 | — |
| 3 | USER CHECKPOINT | 6-9, 11-16, 15b | 2 |
| 6 | 2, 3, 5 | 9 | 3 |
| 7 | 2, 3, 5 | — | 3 |
| 8 | 2, 3, 5 | — | 3 |
| 10 | 2, 3, 5 | — | 3 |
| 11 | 2, 3, 5 | — | 3 |
| 15 | 2, 3, 5 | — | 3 |
| 9 | 2, 3, 5, 6 | 12-14, 15b, 16 | 4 |
| 12 | 9 | — | 5 |
| 13 | 9 | — | 5 |
| 14 | 9 | — | 5 |
| 15b | 9 | — | 5 |
| 16 | 9 | — | 5 |
| 17 | 4, 6-16, 15b | — | 6 |
| 18 | all 1-17 | — | 6 |
| F1-F4 | all 1-18 | — | FINAL |

### Agent Dispatch Summary

- **Wave 1**: **4 tasks** — T1 → `unspecified-high`, T2 → `deep`, T4 → `deep`, T5 → `unspecified-high`
- **Wave 2**: **1 task** — T3 → `unspecified-high`
- **Wave 3**: **6 tasks** — T6 → `deep`, T7 → `deep`, T8 → `unspecified-high`, T10 → `unspecified-high`, T11 → `unspecified-high`, T15 → `deep`
- **Wave 4**: **1 task** — T9 → `deep`
- **Wave 5**: **5 tasks** — T12 → `unspecified-high`, T13 → `unspecified-high`, T14 → `unspecified-high`, T15b → `unspecified-high`, T16 → `deep`
- **Wave 6**: **2 tasks** — T17 → `unspecified-high`, T18 → `quick`
- **FINAL**: **4 tasks** — F1 → `oracle`, F2 → `unspecified-high`, F3 → `unspecified-high`, F4 → `deep`

---

## TODOs

- [x] 1. Data Capture + Anonymization Tooling

  **What to do**:
  - **Extend** `tools/eufy_mqtt_client.py` (344 lines, already handles cloud auth + MQTT subscription) with a `--capture` mode that:
    - Accepts `--capture-dir` and `--duration` (seconds, default 300) arguments
    - Saves each HTTP API response (login, user center, device list, cloud device list, MQTT credentials) to `{capture-dir}/http/{endpoint_name}.json` — these are the normalized return values from the API methods
    - Note: `tools/eufy_mqtt_client.py` currently has login, get_user_center, get_mqtt_certs, get_devices. You must ADD a `get_cloud_device_list()` method (call `EUFY_API_DEVICE_V2` with access token, same pattern as existing methods) to capture the cloud device list response.
    - Records every incoming MQTT message as a JSON file: `{capture-dir}/mqtt/{timestamp}_{dps_keys}.json`
    - Prints summary on completion: N HTTP responses captured, N MQTT messages captured
    - The existing `eufy_mqtt_client.py` already has `EufyCloudAuth.login()`, `.get_user_center()`, `.get_mqtt_certs()`, `.get_devices()` and MQTT subscription — extend these to also dump raw responses to disk
  - Create `tools/anonymize_fixtures.py` — CLI script that:
    - Accepts `--input-dir` (raw capture output), `--output-dir` (fixture destination, default `tests/fixtures`)
    - Loads all JSON files from input directory
    - Replaces PII fields with deterministic fake values:
      - Email → `test@example.com`
      - Device serial numbers → `T2261_ANON_001`, `T2261_ANON_002`, etc. (preserving model prefix)
      - `user_center_id`, `user_id` → `ANON_USER_001`
      - `access_token`, `user_center_token` → `ANON_TOKEN_XXX`
      - `certificate_pem`, `private_key` → `ANON_CERT` / `ANON_KEY` (placeholder strings)
      - `client_id`, `sess_id` → `android-anon-openudid-anon_user-0`
      - `account_id` → `ANON_USER_001`
      - `device_mac` → `00:00:00:00:00:01`
      - `wifi_ssid` → `ANON_WIFI`
      - `wifi_ip` → `192.168.1.100`
      - Timestamps → relative offsets from T=0 (preserve order, zero-base)
    - Preserves ALL other data verbatim (proto payloads, DPS values, device models, state values, error codes)
    - Organizes output into the fixture directory structure (see Task 3)
    - Prints anonymization report: N fields replaced, output files written
  - Both scripts must be runnable standalone (no HA runtime required, no pytest dependency)
  - Do NOT create a new `tools/README.md` — it already exists for the map extractor. Add capture/anonymize usage as a new section at the end of the existing README.

  **Must NOT do**:
  - Do NOT create a new `tools/capture_fixtures.py` — extend the existing `tools/eufy_mqtt_client.py`
  - Do NOT overwrite `tools/README.md` — append to it
  - Do NOT implement reconnection logic, multi-device support, or session resumption — single session, single device
  - Do NOT store raw (unanonymized) data in any directory tracked by git
  - Do NOT add `tools/` to pytest test paths
  - Do NOT modify any production code under `custom_components/`

  **Must NOT do**:
  - Do NOT implement reconnection logic, multi-device support, or session resumption — single session, single device
  - Do NOT store raw (unanonymized) data in any directory tracked by git
  - Do NOT add `tools/` to pytest test paths
  - Do NOT modify any existing production code

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Python scripting with Eufy API domain knowledge, not a standard HA pattern
  - **Skills**: []
    - No specialized skills needed — pure Python + existing API classes

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 2, 3, 4, 5)
  - **Blocks**: Nothing directly (tools are optional for test execution)
  - **Blocked By**: None (can start immediately)

  **References**:

  **Pattern References** (existing code to follow):
  - `tools/eufy_mqtt_client.py` — **The existing capture tool** (344 lines). Already has `EufyCloudAuth` class with `login()`, `get_user_center()`, `get_mqtt_certs()`, `get_devices()` methods, plus MQTT connection via Paho with `on_message` callback. Extend this with a `--capture` mode, NOT a new script.
  - `tools/eufy_mqtt_client.py:69-77` — `login()` method: returns raw session dict. Save this as login_response.json.
  - `tools/eufy_mqtt_client.py:79-100` — `get_user_center()` and `get_mqtt_certs()`: save their responses. NOTE: the method is `get_mqtt_certs()`, NOT `get_mqtt_info()`.
  - `tools/README.md` — Already exists for map extractor toolkit. APPEND capture instructions, do NOT overwrite.
  - `custom_components/robovac_mqtt/coordinator.py:117-181` — `_handle_mqtt_message()` shows the exact JSON parsing path: `json.loads(payload) → payload["payload"]["data"]` — the capture tool should save the raw payload BEFORE this parsing.

  **API/Type References** (data shapes to capture):
  - `custom_components/robovac_mqtt/api/http.py:72-76` — Login response shape: full JSON dict stored as `self.session` (contains `access_token`, `user_center_id`, `user_center_token`)
  - `custom_components/robovac_mqtt/api/http.py:137-142` — Device list: returns `[device["device"] for device in devices]` — already unwrapped from `data.devices[]`
  - `custom_components/robovac_mqtt/api/http.py:163-165` — Cloud device list: returns `data.get("devices", [])` — already unwrapped
  - `custom_components/robovac_mqtt/api/http.py:188-189` — MQTT credentials: returns `(await response.json()).get("data")` — dict with `user_id`, `app_name`, `thing_name`, `certificate_pem`, `private_key`, `endpoint_addr`
  - `custom_components/robovac_mqtt/api/http.py:99-111` — User info: returns dict with `user_center_id`, `user_center_token`, computed `gtoken`
  - `custom_components/robovac_mqtt/coordinator.py:120-127` — MQTT message JSON shape: `{"head": {...}, "payload": {"data": {"dps_key": "base64_value"}}}`

  **PII Field References** (what to anonymize):
  - `custom_components/robovac_mqtt/api/http.py:59` — `username` (email) in login request
  - `custom_components/robovac_mqtt/api/client.py:152` — `client_id` contains `openudid` and `user_id`
  - `custom_components/robovac_mqtt/api/client.py:110` — `account_id` is user_id
  - `custom_components/robovac_mqtt/api/client.py:112` — `device_sn` is serial number
  - `custom_components/robovac_mqtt/models.py:100-103` — `device_mac`, `wifi_ssid`, `wifi_ip` from DPS 169

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Capture mode shows help text
    Tool: Bash
    Preconditions: tools/eufy_mqtt_client.py updated with --capture mode
    Steps:
      1. Run `python tools/eufy_mqtt_client.py --help`
      2. Assert exit code 0
      3. Assert output contains "--capture" or "--capture-dir" and "--duration"
    Expected Result: Help text includes capture mode arguments
    Failure Indicators: Non-zero exit code, missing capture arguments
    Evidence: .sisyphus/evidence/task-1-capture-help.txt

  Scenario: Anonymizer shows help text
    Tool: Bash
    Preconditions: tools/anonymize_fixtures.py exists
    Steps:
      1. Run `python tools/anonymize_fixtures.py --help`
      2. Assert exit code 0
      3. Assert output contains "--input-dir", "--output-dir"
    Expected Result: Help text printed with both arguments documented
    Evidence: .sisyphus/evidence/task-1-anonymize-help.txt

  Scenario: Anonymizer processes sample raw data correctly
    Tool: Bash
    Preconditions: Create a temporary directory with sample raw data containing known PII values
    Steps:
      1. Create temp dir with a sample HTTP response JSON containing `"user_center_id": "REAL_USER_123"` and `"device_sn": "T2261REALSERIAL"`
      2. Run `python tools/anonymize_fixtures.py --input-dir /tmp/test_raw --output-dir /tmp/test_anon`
      3. Read output files
      4. Assert `"REAL_USER_123"` does NOT appear anywhere in output
      5. Assert `"T2261REALSERIAL"` does NOT appear anywhere in output
      6. Assert `"ANON_USER_001"` or similar appears where user_center_id was
      7. Assert `"T2261_ANON_001"` or similar appears where device_sn was
    Expected Result: All PII replaced, data structure preserved
    Failure Indicators: Any original PII value found in output files
    Evidence: .sisyphus/evidence/task-1-anonymizer-pii-check.txt
  ```

  **Evidence to Capture:**
  - [ ] task-1-capture-help.txt
  - [ ] task-1-anonymize-help.txt
  - [ ] task-1-anonymizer-pii-check.txt

  **Commit**: YES (group 1a)
  - Message: `feat(test): add data capture mode and anonymization tooling`
  - Files: `tools/eufy_mqtt_client.py` (modified), `tools/anonymize_fixtures.py` (new), `tools/README.md` (appended)
  - Pre-commit: `python tools/eufy_mqtt_client.py --help && python tools/anonymize_fixtures.py --help`

---

- [x] 2. Integration Test Infrastructure

  **What to do**:
  - Create directory structure: `tests/integration/__init__.py`, `tests/integration/conftest.py`
  - In `tests/integration/conftest.py`, build the core fixture infrastructure:
    - **`mock_eufy_login` fixture**: Returns a `MagicMock` of `EufyLogin` with:
      - `init()` as AsyncMock (return value is ignored — `async_setup_entry` reads attributes after init)
      - `mqtt_devices` property returning a list of device info dicts loaded from HTTP fixture files (this is what `__init__.py:52` reads after `init()`)
      - `mqtt_credentials` property returning MQTT creds dict (used by `coordinator.py:88`)
      - `checkLogin()` as AsyncMock (used by `coordinator.py:86` when mqtt_credentials is None)
      - `openudid` = `"anon-openudid"`
      - NOTE: `async_setup_entry()` ignores `init()` return value and reads `eufy_login.mqtt_devices` directly (see `__init__.py:52`). The mock MUST populate this property.
    - **`mock_mqtt_client` fixture**: Returns a mock `EufyCleanClient` that:
      - Captures `send_command()` calls in a list for assertion (e.g., `client.sent_commands`)
      - Stores the `on_message` callback registered via `set_on_message()` so tests can invoke it to simulate inbound MQTT messages
      - Has `connect()` and `disconnect()` as no-op AsyncMocks
    - **`simulate_mqtt_message` fixture**: A helper function that accepts a DPS dict (or fixture file path) and invokes the coordinator's `_handle_mqtt_message` with a properly formatted MQTT JSON payload (with head/payload/data wrapper)
    - **`load_fixture` fixture**: Loads a JSON file from `tests/fixtures/` by relative path, returns parsed dict
    - **`integration_coordinator` fixture**: Creates a real `EufyCleanCoordinator` with `mock_eufy_login`, injects `mock_mqtt_client`, and returns it ready for testing. Uses the `hass` fixture from pytest-homeassistant-custom-component.
    - **`setup_integration` fixture**: Full HA integration setup — creates `MockConfigEntry`, calls `async_setup_entry()`, returns (hass, coordinator, config_entry). Mocks `EufyLogin` and `EufyCleanClient` at the module level so the real setup code runs with controlled dependencies.
  - Add `tests/integration/__init__.py` (empty)
  - Update `pyproject.toml` testpaths to include integration tests: `testpaths = ["tests", "tests/integration"]` — actually NO, `tests` already recursively includes subdirectories. Just verify pytest discovers `tests/integration/` automatically.
  - Ensure `tests/integration/conftest.py` does NOT duplicate `auto_enable_custom_integrations` — it's already in `tests/conftest.py` and applies globally.

  **Must NOT do**:
  - Do NOT mock `update_state()` or `build_command()` — these are code under test
  - Do NOT create a separate pytest configuration for integration tests
  - Do NOT duplicate fixtures already in `tests/conftest.py`
  - Do NOT use `hass_config` or similar fixtures that require network access

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: Architectural foundation that all subsequent tasks depend on. Must be correct and extensible.
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 3, 4, 5)
  - **Blocks**: Tasks 6-16 (all integration tests depend on this infrastructure)
  - **Blocked By**: None

  **References**:

  **Pattern References**:
  - `tests/conftest.py` — Existing conftest, 9 lines. Only has `auto_enable_custom_integrations`. Integration conftest must NOT duplicate this.
  - `tests/test_coordinator.py` — Current coordinator test fixtures (`mock_hass`, `mock_login`). Study the mock patterns to understand what needs to become more realistic in integration tests.
  - `tests/test_vacuum.py` — Current vacuum test fixtures (`mock_coordinator`, `mock_config_entry`). The `mock_coordinator` pattern here is what we're replacing with `integration_coordinator` that uses real coordinator code.
  - `custom_components/robovac_mqtt/__init__.py` — `async_setup_entry()`: this is what `setup_integration` must exercise. Key flow: creates `EufyLogin` (line 40), calls `init()` (line 42, return value ignored), reads `eufy_login.mqtt_devices` (line 52), iterates to create coordinators. Patch `EufyLogin` at `custom_components.robovac_mqtt.EufyLogin` so the real setup code runs with the mock.
  - `custom_components/robovac_mqtt/coordinator.py:31-64` — Constructor parameters: `hass`, `eufy_login`, `device_info` dict with keys `deviceId`, `deviceModel`, `deviceName`, `softVersion`, optional `dps`.
  - `custom_components/robovac_mqtt/coordinator.py:82-114` — `initialize()` method: creates `EufyCleanClient`, sets `on_message`, calls `connect()`. The `mock_mqtt_client` must be injectable here.
  - `custom_components/robovac_mqtt/coordinator.py:116-181` — `_handle_mqtt_message()`: the entry point for `simulate_mqtt_message`. Accepts `payload: bytes` (raw MQTT bytes, not parsed JSON). Must encode the JSON wrapper to bytes before calling.
  - `custom_components/robovac_mqtt/api/client.py:125-137` — MQTT message JSON format: `{"head": {"client_id": ..., "cmd": 65537, ...}, "payload": {"account_id": ..., "data": {...}, "device_sn": ...}}`. The `simulate_mqtt_message` helper must construct this exact wrapper.

  **API/Type References**:
  - `custom_components/robovac_mqtt/models.py:33-113` — `VacuumState` dataclass: all fields that integration tests will assert against. Study default values — these are the "no data received" baseline.
  - `custom_components/robovac_mqtt/api/cloud.py` — `EufyLogin`: properties `mqtt_credentials` (dict), `devices` (list of device dicts), method `init()`, `checkLogin()`. Mock must match these interfaces.
  - `requirements_test.txt` — Existing test dependencies. Verify `pytest-homeassistant-custom-component>=0.13.102` is sufficient.

  **External References**:
  - pytest-homeassistant-custom-component: provides `hass` fixture (real HA event loop), `enable_custom_integrations`, `MockConfigEntry` from `pytest_homeassistant_custom_component.common`

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Integration test infrastructure loads without errors
    Tool: Bash
    Preconditions: tests/integration/conftest.py exists
    Steps:
      1. Run `pytest tests/integration/ --co -q` (collect tests only, no execution)
      2. Assert exit code 0
      3. Assert output shows "no tests ran" or "0 items" (no test files yet, but conftest loads)
    Expected Result: pytest can import and load the conftest without errors
    Failure Indicators: ImportError, fixture not found, conftest syntax error
    Evidence: .sisyphus/evidence/task-2-conftest-loads.txt

  Scenario: Existing unit tests still pass after infrastructure changes
    Tool: Bash
    Preconditions: tests/ directory unchanged except new tests/integration/ added
    Steps:
      1. Run `pytest tests/ --ignore=tests/integration/ -v`
      2. Assert all 195+ tests pass
      3. Assert 0 failures, 0 errors
    Expected Result: No regression in unit tests
    Failure Indicators: Any test failure or import error
    Evidence: .sisyphus/evidence/task-2-unit-tests-pass.txt

  Scenario: simulate_mqtt_message helper produces correct payload format
    Tool: Bash
    Preconditions: conftest.py with simulate_mqtt_message defined
    Steps:
      1. Write a minimal test that uses `simulate_mqtt_message` with DPS `{"163": "50"}` (battery=50)
      2. Run the test
      3. Assert the coordinator's `_handle_mqtt_message` was called with bytes containing valid JSON
      4. Assert the JSON has `head.cmd` = 65537 and `payload.data` containing the DPS dict
    Expected Result: Helper correctly wraps DPS dict into MQTT message bytes
    Evidence: .sisyphus/evidence/task-2-simulate-mqtt.txt
  ```

  **Evidence to Capture:**
  - [ ] task-2-conftest-loads.txt
  - [ ] task-2-unit-tests-pass.txt
  - [ ] task-2-simulate-mqtt.txt

  **Commit**: YES (group 1b)
  - Message: `feat(test): add integration test infrastructure and fixtures`
  - Files: `tests/integration/__init__.py`, `tests/integration/conftest.py`
  - Pre-commit: `pytest tests/integration/ --co -q && pytest tests/ --ignore=tests/integration/ -q`

---

- [x] 3. Organize Captured Data into Fixture Directory Structure

  **What to do**:
  - Take the anonymized captured data (committed after the USER CHECKPOINT) and organize it into a structured fixture hierarchy under `tests/fixtures/`
  - The anonymized capture will contain raw HTTP response JSON files and raw MQTT message JSON files
  - Organize into this structure:
    ```
    tests/fixtures/
    ├── http/
    │   ├── login_response.json          (raw session dict with access_token, user_center_id, etc.)
    │   ├── user_info_response.json      (user center info dict with user_center_id, gtoken, etc.)
    │   ├── device_list_response.json    (list of device dicts — already unwrapped from data.devices[].device)
    │   ├── cloud_device_list_response.json  (list of cloud device dicts — unwrapped from data.devices)
    │   └── mqtt_credentials_response.json   (MQTT creds dict — unwrapped from data: user_id, app_name, etc.)
    ├── mqtt/
    │   ├── work_status/
    │   │   ├── idle_standby.json          (state=0)
    │   │   ├── idle_sleep.json            (state=1)
    │   │   ├── error.json                 (state=2)
    │   │   ├── docked_charging.json       (state=3, charging=true)
    │   │   ├── cleaning_positioning.json  (state=4)
    │   │   ├── cleaning_active.json       (state=5, no station washing)
    │   │   ├── docked_washing.json        (state=5, station washing active)
    │   │   ├── docked_drying.json         (state=5, station drying active)
    │   │   ├── returning.json             (state=7)
    │   │   ├── trigger_app.json           (trigger.source=1)
    │   │   ├── trigger_button.json        (trigger.source=2)
    │   │   ├── trigger_schedule.json      (trigger.source=3)
    │   │   └── trigger_missing.json       (no trigger field, mode in APP_TRIGGER_MODES)
    │   ├── station_status/
    │   │   ├── idle.json
    │   │   ├── washing.json
    │   │   ├── drying.json
    │   │   └── emptying_dust.json
    │   ├── cleaning_params/
    │   │   ├── response_format.json       (CleanParamResponse proto)
    │   │   └── request_format.json        (CleanParamRequest proto — fallback)
    │   ├── map_data/
    │   │   ├── universal_data_response.json  (primary format)
    │   │   └── room_params.json              (fallback format)
    │   ├── error_code/
    │   │   ├── wheel_stuck.json           (common error)
    │   │   └── no_error.json              (code=0)
    │   ├── task_status/
    │   │   ├── cleaning.json
    │   │   ├── paused.json
    │   │   └── returning_to_charge.json
    │   ├── accessories/
    │   │   └── consumable_response.json
    │   ├── scene_info/
    │   │   └── scenes_with_rooms.json
    │   └── cleaning_stats/
    │       └── stats_response.json
    ├── dps_plain/
    │   ├── battery_level.json          (DPS 163 — plain integer)
    │   ├── clean_speed.json            (DPS 158 — plain integer index)
    │   └── find_robot.json             (DPS 160 — plain boolean string)
    ├── undisturbed/
    │   └── dnd_config.json             (DPS 157 — UndisturbedResponse)
    ├── device_info/
    │   └── device_info.json            (DPS 169 — DeviceInfo with MAC, wifi, IP)
    ├── unisetting/
    │   └── unisetting.json             (DPS 176 — UnisettingResponse with wifi_signal, child_lock, DND)
    ├── telemetry/
    │   └── robot_position.json         (DPS 179 — custom varint with x,y position)
    ├── multi_map/
    │   └── multi_map_manage.json       (DPS 172 — MultiMapsManageResponse)
    └── sequences/
        ├── full_cleaning_cycle.json       (ordered list of MQTT messages: idle→cleaning→returning→docked)
        └── dock_wash_dry_cycle.json       (docked→washing→drying→idle)
    ```
  - Each MQTT fixture file must be the REAL captured MQTT payload (anonymized). The JSON structure should be:
    ```json
    {
      "description": "Human-readable description of what this fixture represents",
      "raw_payload": { ... the full MQTT JSON message as captured ... },
      "dps": {
        "DPS_KEY": "value_exactly_as_captured"
      },
      "expected_state": {
        "activity": "cleaning",
        "battery_level": 85,
        ...fields that should change from this message — determined by observing real device behavior
      }
    }
    ```
  - The `expected_state` for each fixture is determined through a TWO-STEP process:
    1. **Proto definitions + const.py mappings**: For protobuf DPS values, decode them and look up the expected field values in the mapping tables (e.g., WorkStatus.state=5 → check DOCK_ACTIVITY_STATES to determine if cleaning or docked). For plain DPS values (163, 158, 160), the mapping is direct.
    2. **User annotation during capture**: The user should note what the vacuum was PHYSICALLY doing when messages arrived (e.g., "I started a clean at T+30s, vacuum started washing mop at T+120s"). The executor uses these annotations + proto definitions to fill in expected_state.
  - If there is no user annotation for a specific message, the executor derives expected_state from proto definitions + const.py mapping tables + the overall sequence context (e.g., a WorkStatus.state=7 between cleaning and docked messages is clearly "returning").
  - For HTTP fixtures, use the actual response structure as returned by the API
  - **CRITICAL**: DPS values must be EXACTLY as captured from the real device. Do NOT regenerate them from proto classes. The captured bytes ARE the source of truth. Note that some DPS keys are plain values (163=battery as int, 158=speed as int index, 160=find_robot as bool string), not base64 protobuf.
  - For proto DPS values, verify they decode correctly using the proto classes as a VALIDATION step (not generation)
  - **Sequence fixture schema** (for `tests/fixtures/sequences/`): an array of ordered messages:
    ```json
    {
      "description": "Full cleaning cycle",
      "messages": [
        {
          "dps": {"153": "base64..."},
          "expected_state_after": {"activity": "cleaning"},
          "delay_seconds": 0
        },
        {
          "dps": {"163": "70"},
          "expected_state_after": {"battery_level": 70},
          "delay_seconds": 30
        }
      ]
    }
    ```
    Note: sequence fixtures use `expected_state_after` (per-message), not `expected_state`. The `delay_seconds` field represents the time gap before this message, used for debounce testing.

  **Must NOT do**:
  - Do NOT generate fixtures from proto classes — use real captured data as source of truth
  - Do NOT include any real PII in fixture files — they should already be anonymized
  - Do NOT invent expected_state values from reading parser.py — use what the user observed on the real device
  - Do NOT hand-craft base64 protobuf values — they must come from real captures

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Organizing captured data into structured fixtures, requires proto validation
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (alone — organizes fixture data before protocol tests begin)
  - **Blocks**: Tasks 6-16 (all tests load these fixtures)
  - **Blocked By**: USER CHECKPOINT (requires anonymized captured data to be committed)

  **References**:

  **Pattern References**:
  - `tests/test_task_status_flapping.py` — The best existing example of using real DPS payloads in tests. Study how it constructs `dps` dicts with base64-encoded protobuf values and feeds them to `update_state()`. Use this as the pattern for fixture organization.

  **API/Type References** (for VALIDATING captured data, NOT for generating fixtures):
  - `custom_components/robovac_mqtt/utils.py` — `decode(ProtoType, value)`: use to VALIDATE that captured DPS values decode correctly. Do NOT use `encode_message()` to generate fixture values.
  - `custom_components/robovac_mqtt/proto/cloud/work_status_pb2.py` — `WorkStatus` proto: use to validate DPS 153 captures decode correctly.
  - (remaining proto refs are for validation only — same list as before)

  **State Mapping References** (for deriving `expected_state` when user annotations are unavailable):
  - `custom_components/robovac_mqtt/const.py` — Mapping tables (TRIGGER_SOURCE_NAMES, WORK_MODE_NAMES, FAN_SUCTION_NAMES, etc.) are the PRIMARY reference for expected_state derivation.
  - Proto field definitions (e.g., WorkStatus.state integer meanings) combined with const.py mappings define what each captured value SHOULD produce.
  - `custom_components/robovac_mqtt/api/parser.py` — Read for CONTEXT on how fields interact, but do NOT treat current parser behavior as authoritative. The expected_state should reflect what the device MEANS, not what the parser currently does. If they disagree, that's a discovered bug.

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: All fixture files are valid JSON
    Tool: Bash
    Preconditions: tests/fixtures/ directory populated
    Steps:
      1. Run `find tests/fixtures -name '*.json' -exec python -m json.tool {} + > /dev/null`
      2. Assert exit code 0 (all files are valid JSON)
      3. Count files: `find tests/fixtures -name '*.json' | wc -l`
      4. Assert at least 25 fixture files exist
    Expected Result: All fixture files parse as valid JSON, minimum 25 files
    Failure Indicators: JSON parse error, fewer than 25 files
    Evidence: .sisyphus/evidence/task-3-fixtures-valid.txt

  Scenario: DPS fixture values decode correctly via protobuf
    Tool: Bash
    Preconditions: Fixture files with base64 DPS values exist
    Steps:
      1. Write a Python script that loads each MQTT fixture file
      2. For each fixture, decode the base64 DPS value using the appropriate proto type (based on DPS key)
      3. Assert no protobuf decode errors
      4. For work_status fixtures, assert WorkStatus.state matches expected_state.activity mapping
    Expected Result: All fixture DPS values are valid protobuf, decodable by the correct proto type
    Failure Indicators: Base64 decode error, protobuf ParseFromString error, mismatched state values
    Evidence: .sisyphus/evidence/task-3-fixtures-protobuf-valid.txt

  Scenario: Sequence fixtures have correct ordering
    Tool: Bash
    Preconditions: tests/fixtures/sequences/ populated
    Steps:
      1. Load full_cleaning_cycle.json
      2. Assert it has a `messages` array with at least 4 entries
      3. Assert first message expected_state_after.activity is "idle" or "cleaning"
      4. Assert last message expected_state_after.activity is "docked"
      5. Assert each message has `dps`, `expected_state_after`, and `delay_seconds` keys
    Expected Result: Sequence fixtures represent valid state progression
    Evidence: .sisyphus/evidence/task-3-sequence-valid.txt
  ```

  **Evidence to Capture:**
  - [ ] task-3-fixtures-valid.txt
  - [ ] task-3-fixtures-protobuf-valid.txt
  - [ ] task-3-sequence-valid.txt

  **Commit**: YES (group 1b)
  - Message: `feat(test): add integration test infrastructure and fixtures`
  - Files: `tests/fixtures/**/*.json`
  - Pre-commit: `python -c "import json, glob; [json.load(open(f)) for f in glob.glob('tests/fixtures/**/*.json', recursive=True)]"`

---

- [x] 4. Unit Test Audit — Identify Overlap with Integration Scope

  **What to do**:
  - Systematically review all 29 test files in `tests/` directory
  - For each test file, classify every test function into one of:
    - **KEEP**: Pure unit test — tests a single function's logic in isolation (e.g., `test_encode_varint_edge_cases`). No overlap with integration scope.
    - **REDUNDANT**: Tests behavior that the new integration tests will cover more realistically (e.g., a test that mocks `update_state` return value and checks entity attribute — the integration test will do this without mocking `update_state`)
    - **CONFLICT**: Tests that encode current implementation bugs as valid behavior (e.g., assertions that match a buggy state mapping). These MUST be flagged for investigation.
    - **REFACTOR**: Tests that test the right behavior but use excessive mocking that makes them brittle. Candidate for simplification.
  - Produce `tests/integration/AUDIT.md` with:
    - Table: file, test name, classification (KEEP/REDUNDANT/CONFLICT/REFACTOR), reason
    - Summary: N keep, N redundant, N conflict, N refactor
    - Specific recommendations for each REDUNDANT and CONFLICT test
  - **Key overlap areas to check**:
    - `test_parser.py` (31 tests) — many of these test `update_state()` behavior which will also be tested in integration. KEEP tests that exercise specific parsing edge cases (e.g., room deduplication). REDUNDANT if they're just smoke tests of normal state mapping.
    - `test_coordinator.py` (8 tests) — overlap with Task 9 coordinator lifecycle tests. KEEP unit tests of individual methods. REDUNDANT if they test MQTT→state pipeline with mocked parser.
    - `test_vacuum.py` (11 tests) — overlap with Task 12 entity tests. KEEP command dispatch tests. REDUNDANT if they test state attribute mapping with mock coordinator.
    - `test_sensor.py`, `test_select.py`, `test_switch.py` etc. — entity tests that may overlap with Tasks 12-14.
  - **Do NOT modify any test files yet** — this is audit only. Modifications happen in Task 17.

  **Must NOT do**:
  - Do NOT delete or modify any existing test files in this task
  - Do NOT run tests with code coverage (save that for Task 18)
  - Do NOT make value judgments about test quality beyond the overlap classification

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: Requires understanding both the existing unit test behavior AND the planned integration test scope to accurately classify overlap
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 2, 3, 5)
  - **Blocks**: Task 17 (audit resolution depends on audit findings)
  - **Blocked By**: None

  **References**:

  **Test Files to Audit** (read ALL of these completely):
  - `tests/test_parser.py` — 31 tests, most complex. Focus on which test `update_state()` behavior vs specific parsing edge cases.
  - `tests/test_api.py` — 26 tests. Mix of parser and command tests. Some may overlap with Tasks 6-10.
  - `tests/test_select.py` — 15 tests. Entity tests with mock coordinator.
  - `tests/test_vacuum.py` — 11 tests. Vacuum entity with mock coordinator.
  - `tests/test_switch.py` — 9 tests. Switch entity tests.
  - `tests/test_coordinator.py` — 8 tests. Coordinator tests with mocked update_state.
  - `tests/test_utils.py` — 8 tests. Utility function tests (likely KEEP all).
  - `tests/test_segment_detection.py` — 7 tests. Segment change detection.
  - `tests/test_sensor.py` — 6 tests. Sensor entity tests.
  - `tests/test_number.py` — 6 tests. Number entity tests.
  - `tests/test_client.py` — 6 tests. MQTT client tests.
  - `tests/test_cloud.py` — 6 tests. Login flow tests.
  - `tests/test_commands.py` — 5 tests. Command building tests.
  - `tests/test_scene_state.py` — 5 tests. Scene parsing tests.
  - `tests/test_segment_cleaning.py` — 5 tests. Segment cleaning command tests.
  - `tests/test_binary_sensor.py` — 4 tests. Binary sensor tests.
  - `tests/test_http.py` — 4 tests. HTTP client tests.
  - `tests/test_task_status.py` — 2 tests. Task status mapping.
  - `tests/test_task_status_flapping.py` — 3 tests. Task status flapping.
  - `tests/test_parser_cleaning_stats.py` — 3 tests. Cleaning stats.
  - `tests/test_parser_accessories.py` — 2 tests. Accessory parsing.
  - `tests/test_config_flow.py` — 2 tests. Config flow.
  - `tests/test_button.py` — 2 tests. Button entity.
  - `tests/test_time.py` — 2 tests. Time entity.
  - `tests/test_init.py` — 1 test. Setup entry.
  - `tests/test_error_parsing.py` — 1 test. Error code mapping.
  - `tests/test_orphaned_devices.py` — 1 test. Device cleanup.
  - `tests/test_sensor_accessories.py` — Accessory sensor tests.
  - `tests/test_vacuum_rooms_custom.py` — Room custom settings tests.

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Audit report covers all test files
    Tool: Bash
    Preconditions: AUDIT.md generated
    Steps:
      1. Read tests/integration/AUDIT.md
      2. Count unique test files mentioned
      3. Count unique test functions classified
      4. Assert all 29 test files in tests/ are covered
      5. Assert total classified tests >= 195
    Expected Result: Complete coverage of all existing test files and functions
    Failure Indicators: Missing test files, missing test functions, incomplete classification
    Evidence: .sisyphus/evidence/task-4-audit-coverage.txt

  Scenario: No unclassified tests remain
    Tool: Bash
    Preconditions: AUDIT.md exists
    Steps:
      1. Grep AUDIT.md for any rows without a classification (KEEP/REDUNDANT/CONFLICT/REFACTOR)
      2. Assert zero unclassified rows
    Expected Result: Every test function has a classification
    Evidence: .sisyphus/evidence/task-4-no-unclassified.txt
  ```

  **Evidence to Capture:**
  - [ ] task-4-audit-coverage.txt
  - [ ] task-4-no-unclassified.txt

  **Commit**: YES (group 1c)
  - Message: `chore(test): audit existing unit tests for integration overlap`
  - Files: `tests/integration/AUDIT.md`
  - Pre-commit: —

---

- [x] 5. Fixture Helpers: State Factory, DPS Builder, MQTT Wrapper

  **What to do**:
  - Create `tests/integration/helpers.py` with reusable test helper functions:
    - **`make_vacuum_state(**overrides)`**: Factory function that creates a `VacuumState` with sensible defaults for an X-Series device in a common state (docked, charged, no error). Accepts keyword overrides for any field. Avoids repeating default construction in every test.
    - **`make_dps_payload(dps_key: str, proto_msg)`**: Takes a DPS key string and a protobuf message, returns `{dps_key: base64_encoded_value}` dict using `encode_message()` from utils.py. Centralizes the encode step so tests don't need to import encode utilities.
    - **`make_mqtt_bytes(dps: dict, device_sn: str = "T2261_ANON_001")`**: Wraps a DPS dict into the full MQTT JSON message format (with head and payload) and returns UTF-8 encoded bytes. This is what `_handle_mqtt_message` expects. The wrapper structure must match `api/client.py:125-137`.
    - **`make_work_status(state: int = 0, **kwargs)`**: Convenience builder for `WorkStatus` proto messages. Accepts optional `charging`, `trigger`, `station`, and `mode` parameters. NOTE: the proto field is `charging` (nested Charging message), NOT `charge_state`.
    - **`make_station_response(**kwargs)`**: Convenience builder for `StationResponse` proto messages.
    - **`make_clean_param_response(**kwargs)`**: Convenience for `CleanParamResponse` proto.
    - **`make_device_info_dict(device_id="T2261_ANON_001", model="T2261", name="Test Vacuum")`**: Returns the device info dict expected by `EufyCleanCoordinator.__init__()`. Must match the key names used in coordinator.py:38-41 (`deviceId`, `deviceModel`, `deviceName`, `softVersion`).
    - **`assert_state_field(state: VacuumState, field: str, expected: Any)`**: Helper that provides clear assertion messages: `f"Expected {field}={expected!r}, got {getattr(state, field)!r}"`.
  - Keep helpers focused — no business logic, no assertions about correctness. They're factories and formatters only.
  - Add docstrings to every helper explaining what it does and when to use it.

  **Must NOT do**:
  - Do NOT put test assertions in helpers (except `assert_state_field`)
  - Do NOT duplicate logic from `utils.py` — import and use `encode_message`
  - Do NOT create helpers for DPS keys not used by X-Series
  - Do NOT make helpers HA-dependent (no `hass` parameter) — keep them pure Python so they can be used in any context

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Utility code that requires understanding of proto types and MQTT format, but straightforward implementation
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 2, 3, 4)
  - **Blocks**: Tasks 6-16 (all integration tests use these helpers)
  - **Blocked By**: None

  **References**:

  **Pattern References**:
  - `tests/test_parser.py` — `_make_work_status()` and `_mock_clean_param()` helpers: these are the existing patterns. Our new helpers should be more complete and reusable versions of these.
  - `tests/test_api.py` — Uses `encode_message()` directly in tests. Our `make_dps_payload()` wraps this for convenience.
  - `tests/test_coordinator.py` — Has inline `mock_login` fixture with device_info dict. Our `make_device_info_dict()` standardizes this.
  - `custom_components/robovac_mqtt/api/client.py:125-137` — The exact MQTT JSON wrapper format that `make_mqtt_bytes()` must produce.

  **API/Type References**:
  - `custom_components/robovac_mqtt/models.py:33-113` — `VacuumState` dataclass with all fields and defaults. `make_vacuum_state()` must accept any of these as keyword args.
  - `custom_components/robovac_mqtt/utils.py` — `encode_message()`: used by `make_dps_payload()`. Import path: `custom_components.robovac_mqtt.utils.encode_message`.
  - `custom_components/robovac_mqtt/proto/cloud/work_status_pb2.py` — `WorkStatus` proto fields for `make_work_status()`.
  - `custom_components/robovac_mqtt/proto/cloud/station_pb2.py` — `StationResponse` proto fields for `make_station_response()`.
  - `custom_components/robovac_mqtt/proto/cloud/clean_param_pb2.py` — `CleanParamResponse` proto fields for `make_clean_param_response()`.
  - `custom_components/robovac_mqtt/coordinator.py:38-41` — Device info dict keys: `deviceId`, `deviceModel`, `deviceName`, `softVersion`.

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: All helper functions are importable and documented
    Tool: Bash
    Preconditions: tests/integration/helpers.py exists
    Steps:
      1. Run `python -c "from tests.integration.helpers import make_vacuum_state, make_dps_payload, make_mqtt_bytes, make_work_status, make_station_response, make_clean_param_response, make_device_info_dict, assert_state_field; print('All imports OK')"`
      2. Assert exit code 0
      3. Run `python -c "import inspect; from tests.integration import helpers; funcs = [f for f in dir(helpers) if callable(getattr(helpers, f)) and not f.startswith('_')]; missing_docs = [f for f in funcs if not getattr(helpers, f).__doc__]; print(f'{len(missing_docs)} undocumented'); assert not missing_docs, missing_docs"`
    Expected Result: All helpers importable, all have docstrings
    Failure Indicators: ImportError, missing docstring
    Evidence: .sisyphus/evidence/task-5-helpers-importable.txt

  Scenario: make_dps_payload produces decodable protobuf
    Tool: Bash
    Preconditions: helpers.py with make_dps_payload defined
    Steps:
      1. Run Python script that calls `make_dps_payload("153", WorkStatus(state=5))` 
      2. Take the resulting base64 value, decode it using `decode(WorkStatus, value, has_length=True)`
      3. Assert decoded message.state == 5
    Expected Result: Roundtrip encode/decode succeeds
    Evidence: .sisyphus/evidence/task-5-dps-roundtrip.txt

  Scenario: make_mqtt_bytes produces valid coordinator input
    Tool: Bash
    Preconditions: helpers.py with make_mqtt_bytes defined
    Steps:
      1. Call `make_mqtt_bytes({"163": "50"})` (battery=50 as PLAIN INTEGER STRING — DPS 163/158/160 are NOT protobuf)
      2. Decode returned bytes as JSON
      3. Assert JSON has `head.cmd` == 65537
      4. Assert JSON has `payload.data.163` == "50"
      5. Assert JSON has `payload.device_sn` == "T2261_ANON_001"
    Expected Result: MQTT wrapper matches api/client.py format. Note: DPS 163 (battery), 158 (clean_speed), 160 (find_robot) are plain values, NOT base64 protobuf.
    Evidence: .sisyphus/evidence/task-5-mqtt-wrapper.txt
  ```

  **Evidence to Capture:**
  - [ ] task-5-helpers-importable.txt
  - [ ] task-5-dps-roundtrip.txt
  - [ ] task-5-mqtt-wrapper.txt

  **Commit**: YES (group 1b)
  - Message: `feat(test): add integration test infrastructure and fixtures`
  - Files: `tests/integration/helpers.py`
  - Pre-commit: `python -c "from tests.integration.helpers import make_vacuum_state, make_dps_payload, make_mqtt_bytes"`

---

- [x] 6. WorkStatus Parser Integration Tests

  **What to do**:
  - Create `tests/integration/test_parser_work_status.py`
  - Test the FULL pipeline: raw protobuf → `update_state()` → `VacuumState` field values
  - Use fixtures from `tests/fixtures/mqtt/work_status/` and helpers from `tests/integration/helpers.py`
  - **Test cases (define expected behavior FIRST, then assert)**:
    - **State mapping correctness**:
      - State 0 → activity="idle", task_status="idle"
      - State 1 → activity="idle" (sleep mode)
      - State 2 → activity="error"
      - State 3 → activity="docked", charging=True
      - State 4 → activity="cleaning" (positioning phase)
      - State 5 (no station activity) → activity="cleaning"
      - State 7 → activity="returning"
    - **State=5 ambiguity** (THE critical edge case):
      - State=5 + station washing active → activity="docked", dock_status contains "Washing"
      - State=5 + station drying active → activity="docked", dock_status contains "Drying"
      - State=5 + station idle → activity="cleaning" (NOT docked)
      - State=5 + station emptying dust → activity should reflect dock activity
    - **Trigger source inference** (note: all values are LOWERCASE per const.py:121-128):
      - WorkStatus with trigger.source=1 → trigger_source="app"
      - WorkStatus with trigger.source=2 → trigger_source="button"
      - WorkStatus with trigger.source=3 → trigger_source="schedule"
      - WorkStatus with trigger.source=4 → trigger_source="robot"
      - WorkStatus with trigger.source=5 → trigger_source="remote_control"
      - WorkStatus WITHOUT trigger field + mode in EUFY_CLEAN_APP_TRIGGER_MODES → trigger_source="app"
      - WorkStatus WITHOUT trigger field + mode NOT in APP_TRIGGER_MODES → trigger_source stays "unknown" (does NOT infer from mode)
    - **Charging state**:
      - State=3 with charging field → charging=True
      - State=5 (cleaning) → charging=False
      - Transition from charging to cleaning → charging flips to False
    - **Work mode tracking**:
      - Various mode values → correct work_mode string from WORK_MODE_NAMES
    - **State transitions** (feed multiple DPS updates sequentially):
      - idle → cleaning → returning → docked (verify each intermediate state)
      - cleaning → error → idle (error recovery)
  - **Testing principle**: For EACH test, the expected value comes from: (1) real captured device data (the source of truth), (2) proto definitions in `proto/cloud/`, (3) const.py mapping tables. If the parser disagrees with these sources, the test FAILS — that's a discovered bug, which is the primary goal. Do NOT read `parser.py` to determine expected values. Do NOT use xfail — let failures be honest.
  - Use `update_state(VacuumState(), dps)` directly — no coordinator, no HA runtime. This is parser-level integration (real protobuf → real parser → real state).

  **Must NOT do**:
  - Do NOT mock `decode()` or any protobuf functions — use real protobuf serialization
  - Do NOT read parser.py source to determine expected values — use the DPS mapping specification from const.py and the proto definitions
  - Do NOT test implementation details (internal variable names, function call order)

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: Most complex parsing logic (150+ lines). Requires understanding business rules, not just current code behavior.
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 7, 8, 9, 10, 11)
  - **Blocks**: Task 9 (coordinator tests build on parser test patterns)
  - **Blocked By**: Tasks 2, 3, 5 (infrastructure, fixtures, helpers)

  **References**:

  **Pattern References**:
  - `tests/test_parser.py` — Current WorkStatus tests. Study what's already tested vs what's missing. The integration versions should be more thorough and use real protobuf, not mocked decode.
  - `tests/test_task_status_flapping.py` — Uses real DPS payloads from logs fed into `update_state()`. This is closest to the pattern we want.
  - `tests/test_scene_state.py` — Creates WorkStatus protos with specific fields, encodes them, feeds to parser. Good pattern.

  **API/Type References**:
  - `custom_components/robovac_mqtt/api/parser.py:195-345` — `_process_work_status()`: the function under test. Note: the activity mapping helper is `_map_work_status()` (NOT `_activity_from_work_state()`). Read it to understand the branching, but define expected values from real captures + proto definitions.
  - `custom_components/robovac_mqtt/api/parser.py:537-614` — Task status derivation logic.
  - `custom_components/robovac_mqtt/api/parser.py:617-658` — Activity derivation: `_map_work_status()` (the state→activity mapping function).
  - `custom_components/robovac_mqtt/const.py` — `EUFY_CLEAN_APP_TRIGGER_MODES` (mode IDs 1-9 implying app trigger), `TRIGGER_SOURCE_NAMES` (source int → string), `WORK_MODE_NAMES` (mode int → string), `DOCK_ACTIVITY_STATES` (tuple of dock activity strings).
  - `custom_components/robovac_mqtt/proto/cloud/work_status_pb2.py` — WorkStatus fields: `state`, `charging` (nested Charging message with charge state), `trigger` (has `.source`, `.mode`), `station` (has activity-related fields).
  - `custom_components/robovac_mqtt/models.py:33-113` — VacuumState fields that WorkStatus affects: `activity`, `task_status`, `charging`, `trigger_source`, `work_mode`, `dock_status`, `status_code`.

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: All WorkStatus state mappings produce correct activity
    Tool: Bash
    Preconditions: test_parser_work_status.py exists, fixtures loaded
    Steps:
      1. Run `pytest tests/integration/test_parser_work_status.py -v -k "state_mapping"`
      2. Assert all tests pass
      3. Verify output shows tests for states 0,1,2,3,4,5,7
    Expected Result: Each WorkStatus.state value maps to the documented activity string
    Failure Indicators: Test failure indicating parser maps state to wrong activity
    Evidence: .sisyphus/evidence/task-6-state-mapping.txt

  Scenario: State=5 ambiguity tests exercise all branches
    Tool: Bash
    Preconditions: Fixtures for state=5 with different station conditions exist
    Steps:
      1. Run `pytest tests/integration/test_parser_work_status.py -v -k "state_5"`
      2. Assert all tests pass
      3. Verify output shows separate tests for: state_5_cleaning, state_5_washing, state_5_drying
    Expected Result: State=5 correctly resolves to cleaning OR docked depending on station activity
    Failure Indicators: Test failure indicating wrong activity for state=5 with station activity
    Evidence: .sisyphus/evidence/task-6-state5-ambiguity.txt

  Scenario: Trigger inference tests cover both explicit and missing trigger
    Tool: Bash
    Preconditions: Fixtures with and without trigger field exist
    Steps:
      1. Run `pytest tests/integration/test_parser_work_status.py -v -k "trigger"`
      2. Assert all tests pass
      3. Verify at least 7 trigger-related tests (5 explicit sources + 2 missing trigger scenarios)
    Expected Result: Trigger source correctly derived from explicit field or inferred from mode
    Evidence: .sisyphus/evidence/task-6-trigger-inference.txt
  ```

  **Evidence to Capture:**
  - [ ] task-6-state-mapping.txt
  - [ ] task-6-state5-ambiguity.txt
  - [ ] task-6-trigger-inference.txt

  **Commit**: YES (group 2a)
  - Message: `test(integration): add parser integration tests`
  - Files: `tests/integration/test_parser_work_status.py`
  - Pre-commit: `pytest tests/integration/test_parser_work_status.py -v`

---

- [x] 7. Station + CleanParam + MapData Parser Integration Tests

  **What to do**:
  - Create `tests/integration/test_parser_station.py` — Station status parsing
  - Create `tests/integration/test_parser_clean_param.py` — Cleaning parameter parsing
  - Create `tests/integration/test_parser_map_data.py` — Map/room data parsing
  - Use fixtures and helpers from Wave 1 tasks.
  - **Station Status tests (DPS 173)**:
    - Idle station → dock_status reflects idle/None
    - Washing active → dock_status contains washing indicator
    - Drying active → dock_status contains drying indicator
    - Emptying dust → dock_status contains emptying indicator
    - Water level fields → station_clean_water, station_waste_water populated
    - Auto config fields → dock_auto_cfg dict populated correctly
    - Station + WorkStatus interaction: station status affects activity interpretation (cross-DPS test — send both DPS 153 and 173 in sequence)
  - **Cleaning Parameters tests (DPS 154)**:
    - **Dual format fallback**: CleanParamResponse decodes correctly (primary path)
    - **Dual format fallback**: CleanParamRequest decodes when Response fails (fallback path). To test this, craft a protobuf payload that is valid as CleanParamRequest but not as CleanParamResponse.
    - Fan speed extraction → fan_speed string matches FAN_SUCTION_NAMES mapping
    - Water level extraction → mop_water_level string matches MOP_WATER_LEVEL_NAMES
    - Cleaning mode extraction → cleaning_mode string matches CLEANING_MODE_NAMES
    - Cleaning intensity → cleaning_intensity string matches CLEANING_INTENSITY_NAMES
    - Carpet strategy → carpet_strategy string matches CARPET_STRATEGY_NAMES
    - Corner cleaning → corner_cleaning string matches CORNER_CLEANING_NAMES
    - Smart mode flag → smart_mode boolean
    - All 7 fields populated from a single DPS 154 message
  - **Map Data tests (DPS 165)**:
    - UniversalDataResponse format (primary) → rooms list populated with id and name
    - RoomParams format (fallback) → rooms list populated
    - Room deduplication: duplicate room names get suffixed (e.g., "Kitchen", "Kitchen (2)")
    - Map ID extraction → map_id populated
    - Empty room list → rooms = []
    - Rooms with special characters in names

  **Must NOT do**:
  - Do NOT mock protobuf decode — use real serialization
  - Do NOT test internal parser function signatures — test through `update_state()`
  - Do NOT combine all three areas into a single test file — keep them separate for clarity

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: Dual format fallbacks and cross-DPS interactions require careful test design
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 6, 8, 9, 10, 11)
  - **Blocks**: None directly
  - **Blocked By**: Tasks 2, 3, 5

  **References**:

  **Pattern References**:
  - `tests/test_parser.py` — Current station and clean param tests. Identify gaps.
  - `tests/test_parser_cleaning_stats.py` — Pattern for proto→state tests.

  **API/Type References**:
  - `custom_components/robovac_mqtt/api/parser.py:346-460` — `_process_station_status()`: station response parsing
  - `custom_components/robovac_mqtt/api/parser.py:859-975` — Cleaning parameter parsing with dual format fallback
  - `custom_components/robovac_mqtt/api/parser.py:760-799` — Map data parsing with dual format
  - `custom_components/robovac_mqtt/api/parser.py` — `deduplicate_room_names()` or similar (imported from utils.py as `deduplicate_names`)
  - `custom_components/robovac_mqtt/const.py` — `FAN_SUCTION_NAMES`, `MOP_WATER_LEVEL_NAMES`, `CLEANING_MODE_NAMES`, `CLEANING_INTENSITY_NAMES`, `CARPET_STRATEGY_NAMES`, `CORNER_CLEANING_NAMES`
  - `custom_components/robovac_mqtt/proto/cloud/station_pb2.py` — StationResponse fields
  - `custom_components/robovac_mqtt/proto/cloud/clean_param_pb2.py` — CleanParamResponse, CleanParamRequest fields
  - `custom_components/robovac_mqtt/proto/cloud/universal_data_pb2.py` — UniversalDataResponse fields
  - `custom_components/robovac_mqtt/proto/cloud/stream_pb2.py` — RoomParams fields

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Station status tests pass
    Tool: Bash
    Steps:
      1. Run `pytest tests/integration/test_parser_station.py -v`
      2. Assert all tests pass, at least 6 test functions
    Expected Result: All station status scenarios produce correct VacuumState fields
    Evidence: .sisyphus/evidence/task-7-station.txt

  Scenario: Cleaning param dual format tested
    Tool: Bash
    Steps:
      1. Run `pytest tests/integration/test_parser_clean_param.py -v`
      2. Assert tests include both response_format and request_format scenarios
      3. Assert all 7 fields tested (fan_speed, mop_water_level, cleaning_mode, cleaning_intensity, carpet_strategy, corner_cleaning, smart_mode)
    Expected Result: Both proto formats decode correctly, all fields mapped
    Evidence: .sisyphus/evidence/task-7-clean-param.txt

  Scenario: Map data with room deduplication
    Tool: Bash
    Steps:
      1. Run `pytest tests/integration/test_parser_map_data.py -v`
      2. Assert deduplication test exists and passes
      3. Assert both UniversalDataResponse and RoomParams formats tested
    Expected Result: Duplicate room names suffixed, both formats produce room lists
    Evidence: .sisyphus/evidence/task-7-map-data.txt
  ```

  **Evidence to Capture:**
  - [ ] task-7-station.txt
  - [ ] task-7-clean-param.txt
  - [ ] task-7-map-data.txt

  **Commit**: YES (group 2a)
  - Message: `test(integration): add parser integration tests`
  - Files: `tests/integration/test_parser_station.py`, `tests/integration/test_parser_clean_param.py`, `tests/integration/test_parser_map_data.py`
  - Pre-commit: `pytest tests/integration/test_parser_station.py tests/integration/test_parser_clean_param.py tests/integration/test_parser_map_data.py -v`

---

- [x] 8. ErrorCode + TaskStatus + Scene + Accessories Parser Integration Tests

  **What to do**:
  - Create `tests/integration/test_parser_remaining.py` — covers the simpler DPS key parsers
  - **Error Code tests (DPS 177)**:
    - Error code 0 → error_code=0, error_message="" (no error)
    - Known error code (e.g., wheel stuck) → error_code=N, error_message=EUFY_CLEAN_ERROR_CODES[N]
    - Unknown error code → error_code=N, error_message contains "Unknown" or numeric fallback
  - **Task Status tests (DPS 153 — task_status field)**:
    - Verify task_status strings for common scenarios: "Cleaning", "Paused", "Returning to Charge", "Completed" (NOTE: "Drying" goes to dock_status, NOT task_status — task_status for go_wash.mode==2 is "Completed")
    - Task status flapping: send rapid state changes and verify final state is stable (reference test_task_status_flapping.py for the known scenario)
  - **Scene Info tests (DPS 180)**:
    - SceneResponse with multiple scenes → scenes list populated with id, name, and type (NOTE: scenes do NOT include room references — only id/name/type per _parse_scene_info())
    - Empty scene list → scenes = []
  - **Accessories tests (DPS 168)**:
    - ConsumableResponse with all accessory types → accessories.filter_usage, main_brush_usage, etc. populated
    - ConsumableResponse with missing Runtime field → graceful handling (no crash, fields default to 0)
    - Partial accessory data → only present fields updated
  - **Cleaning Statistics tests (DPS 167)**:
    - CleanStatistics → cleaning_time, cleaning_area populated
  - **Battery Level test (DPS 163)** — NOTE: this is a PLAIN INTEGER, not protobuf:
    - Plain integer string "50" → battery_level=50
    - Boundary values: "0", "100"
  - **Find Robot test (DPS 160)** — NOTE: this is a PLAIN BOOLEAN STRING, not protobuf:
    - String "true" → find_robot=True
    - String "false" → find_robot=False
  - **Clean Speed test (DPS 158)** — NOTE: this is a PLAIN INTEGER INDEX, not protobuf:
    - Integer index → fan_speed string from EUFY_CLEAN_NOVEL_CLEAN_SPEED mapping
  - **Multi-Map Management test (DPS 172)**:
    - MultiMapsManageResponse → map list populated
  - **Play/Pause echo test (DPS 152 inbound — `_process_play_pause()`)**:
    - ModeCtrlRequest echo with room IDs → active_room_ids and active_room_names populated
    - ModeCtrlRequest echo with zone count → active_zone_count populated
    - Scene clearing: when new play command arrives → current_scene_id/name cleared
    - Active target clearing: when go_home received → active_room_ids/zone_count cleared

  **Must NOT do**:
  - Do NOT create a separate file per DPS key for these simpler parsers — one file is fine
  - Do NOT duplicate tests from test_task_status_flapping.py — reference it in audit as complementary

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Simpler parsing logic, multiple proto types but straightforward mapping
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 6, 7, 9, 10, 11)
  - **Blocks**: None
  - **Blocked By**: Tasks 2, 3, 5

  **References**:

  **Pattern References**:
  - `tests/test_error_parsing.py` — Current error code test (1 test). Integration version should cover more error codes.
  - `tests/test_task_status.py` — Current task status tests (2 tests). Integration should add more scenarios.
  - `tests/test_task_status_flapping.py` — Known flapping scenario with real DPS payloads. Reference but don't duplicate.
  - `tests/test_parser_accessories.py` — Current accessory tests (2 tests). Integration should test missing Runtime.
  - `tests/test_parser_cleaning_stats.py` — Current stats tests (3 tests).

  **API/Type References**:
  - `custom_components/robovac_mqtt/api/parser.py:413-425` — Error code parsing
  - `custom_components/robovac_mqtt/api/parser.py:822-856` — Accessory parsing with Runtime field checks
  - `custom_components/robovac_mqtt/api/parser.py:800-820` — Scene info parsing
  - `custom_components/robovac_mqtt/const.py` — `EUFY_CLEAN_ERROR_CODES` dict (100+ entries), `DPS_MAP`
  - `custom_components/robovac_mqtt/proto/cloud/error_code_pb2.py` — ErrorCode proto
  - `custom_components/robovac_mqtt/proto/cloud/consumable_pb2.py` — ConsumableResponse proto
  - `custom_components/robovac_mqtt/proto/cloud/scene_pb2.py` — SceneResponse proto
  - `custom_components/robovac_mqtt/proto/cloud/clean_statistics_pb2.py` — CleanStatistics proto

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: All remaining parser tests pass
    Tool: Bash
    Steps:
      1. Run `pytest tests/integration/test_parser_remaining.py -v`
      2. Assert all tests pass
      3. Count test functions — assert at least 12 (error codes: 3, task status: 3, scenes: 2, accessories: 3, stats: 1, battery: 2)
    Expected Result: All simpler DPS parsers produce correct state fields
    Evidence: .sisyphus/evidence/task-8-remaining-parsers.txt

  Scenario: Missing accessory Runtime field handled gracefully
    Tool: Bash
    Steps:
      1. Run `pytest tests/integration/test_parser_remaining.py -v -k "missing_runtime"`
      2. Assert test passes (no crash/exception)
      3. Assert accessory fields default to 0 when Runtime is missing
    Expected Result: Graceful degradation, not crash
    Evidence: .sisyphus/evidence/task-8-missing-runtime.txt
  ```

  **Evidence to Capture:**
  - [ ] task-8-remaining-parsers.txt
  - [ ] task-8-missing-runtime.txt

  **Commit**: YES (group 2a)
  - Message: `test(integration): add parser integration tests`
  - Files: `tests/integration/test_parser_remaining.py`
  - Pre-commit: `pytest tests/integration/test_parser_remaining.py -v`

---

- [x] 9. Coordinator Lifecycle Integration Tests

  **What to do**:
  - Create `tests/integration/test_coordinator.py`
  - Test the coordinator as a BLACK BOX: MQTT message in → entity data out. Uses the real `EufyCleanCoordinator` class with real `update_state()`, mocked only at the transport boundary (MQTT connection and HTTP login).
  - Uses `hass` fixture from pytest-homeassistant-custom-component for real HA event loop.
  - **Test cases**:
    - **MQTT message processing pipeline**:
      - Simulate MQTT bytes (via `_handle_mqtt_message`) with a WorkStatus DPS → verify `coordinator.data` has updated activity, task_status
      - Simulate MQTT with battery DPS → verify `coordinator.data.battery_level` updated
      - Simulate MQTT with multiple DPS keys in one message → verify all fields updated
      - Verify `coordinator.async_set_updated_data()` is called (entities would refresh)
    - **Dock status debouncing** (CRITICAL — uses real HA timers):
      - Send dock_status="Washing" → verify data.dock_status is NOT "Washing" yet (debounce pending)
      - Fire time 2 seconds forward with `async_fire_time_changed(hass, utcnow() + timedelta(seconds=2))` → verify data.dock_status IS now "Washing"
      - Send rapid dock_status changes: "Washing" then "Idle" within 2 seconds → verify only final value ("Idle") is committed after timer
      - Send dock_status change, then a NON-dock message within 2 seconds → verify dock debounce timer is NOT reset by unrelated messages (this tests the `"dock_status" in changes` guard at coordinator.py:134)
    - **State transition sequences**:
      - idle → cleaning → returning → docked: simulate 4 MQTT messages in sequence, verify state after each
      - cleaning → error → idle: error interrupts cleaning, then clears
    - **Payload format variants**:
      - Payload as nested JSON string (coordinator.py:124 handles `isinstance(payload_data, str)`)
      - Payload as dict (normal path)
      - Malformed payload → warning logged, no crash, state unchanged
    - **Initialization with DPS**:
      - Construct coordinator with `device_info` containing `dps` dict → verify initial state parsed from DPS
    - **send_command**:
      - Call `async_send_command({"152": "base64..."})` → verify `client.send_command()` called with exact payload
      - Call `async_send_command` without client → verify warning logged, no crash
    - **Segment change detection**:
      - Send rooms update → verify segment debounce timer started (async_call_later called)
      - Fire time forward → verify dispatcher signal sent

  **Must NOT do**:
  - Do NOT mock `update_state()` — it's the core code under test
  - Do NOT test parser logic details — that's covered in Tasks 6-8
  - **Do NOT use `time.sleep()`** — use HA's `async_fire_time_changed` for timer simulation
  - **CRITICAL**: After every `async_fire_time_changed()` call, add `await hass.async_block_till_done()` to drain the event loop. Without this, the `async_call_later()` callback may not have executed yet, causing flaky tests.

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: Timer-based debouncing, real HA event loop, complex async interactions
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 6, 7, 8, 10, 11)
  - **Blocks**: Tasks 12-16 (entity and E2E tests depend on coordinator patterns)
  - **Blocked By**: Tasks 2, 3, 5, 6 (needs infrastructure + WorkStatus tests as pattern reference)

  **References**:

  **Pattern References**:
  - `tests/test_coordinator.py` — Current coordinator tests (8 tests). All mock `update_state` — the integration version should NOT mock it.
  - `tests/test_task_status_flapping.py` — Uses real DPS payloads with `update_state`. Good pattern for state transition tests.

  **API/Type References**:
  - `custom_components/robovac_mqtt/coordinator.py:28-65` — `EufyCleanCoordinator.__init__()`: constructor, initial state setup, DPS initialization
  - `custom_components/robovac_mqtt/coordinator.py:82-114` — `initialize()`: creates MQTT client, sets on_message, connects. This is what `integration_coordinator` fixture should exercise.
  - `custom_components/robovac_mqtt/coordinator.py:116-181` — `_handle_mqtt_message()`: the main entry point. Parses JSON, calls update_state, handles dock debouncing, publishes state.
  - `custom_components/robovac_mqtt/coordinator.py:134` — `if "dock_status" in changes:` — the guard that prevents non-dock messages from resetting the debounce timer. TEST THIS.
  - `custom_components/robovac_mqtt/coordinator.py:158-160` — `async_call_later(self.hass, 2.0, ...)` — dock debounce timer. Test with `async_fire_time_changed`.
  - `custom_components/robovac_mqtt/coordinator.py:183-199` — `_async_commit_dock_status()`: timer callback that commits pending dock status.
  - `custom_components/robovac_mqtt/coordinator.py:261-266` — `async_send_command()`: sends command via MQTT client.

  **External References**:
  - pytest-homeassistant-custom-component: `async_fire_time_changed` from `homeassistant.util.dt` — used with `from pytest_homeassistant_custom_component.common import async_fire_time_changed`

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: MQTT message updates coordinator state
    Tool: Bash
    Steps:
      1. Run `pytest tests/integration/test_coordinator.py -v -k "mqtt_message_updates_state"`
      2. Assert test passes
      3. Verify coordinator.data reflects the DPS values from the simulated message
    Expected Result: Real update_state() processes real protobuf and updates coordinator.data
    Evidence: .sisyphus/evidence/task-9-mqtt-update.txt

  Scenario: Dock debouncing works with HA timers
    Tool: Bash
    Steps:
      1. Run `pytest tests/integration/test_coordinator.py -v -k "dock_debounce"`
      2. Assert all debounce tests pass
      3. Verify at least 3 debounce scenarios: basic delay, rapid change, non-dock message interference
    Expected Result: Dock status changes are delayed 2 seconds, rapid changes coalesce, unrelated messages don't reset timer
    Failure Indicators: Dock status committed immediately (debounce bypassed), timer reset by non-dock message
    Evidence: .sisyphus/evidence/task-9-dock-debounce.txt

  Scenario: Malformed payload doesn't crash coordinator
    Tool: Bash
    Steps:
      1. Run `pytest tests/integration/test_coordinator.py -v -k "malformed"`
      2. Assert test passes
      3. Verify coordinator.data unchanged after malformed message
    Expected Result: Warning logged, state preserved, no exception propagated
    Evidence: .sisyphus/evidence/task-9-malformed.txt
  ```

  **Evidence to Capture:**
  - [ ] task-9-mqtt-update.txt
  - [ ] task-9-dock-debounce.txt
  - [ ] task-9-malformed.txt

  **Commit**: YES (group 2b)
  - Message: `test(integration): add coordinator and command integration tests`
  - Files: `tests/integration/test_coordinator.py`
  - Pre-commit: `pytest tests/integration/test_coordinator.py -v`

---

- [x] 10. Command Roundtrip Integration Tests

  **What to do**:
  - Create `tests/integration/test_commands.py`
  - Test the OUTBOUND path: `build_command(command_name, **params)` → DPS dict → verify protobuf content by decoding
  - **Test cases** (use exact command names from `build_command()` dispatcher):
    - `build_command("start_auto")` → produces DPS 152 with ModeCtrlRequest(method=EUFY_CLEAN_CONTROL.START_AUTO_CLEAN)
    - `build_command("go_home")` → produces DPS 152 with method=START_GOHOME
    - `build_command("pause")` → produces correct pause control (PAUSE_TASK)
    - `build_command("resume")` → produces correct resume control (RESUME_TASK)
    - `build_command("stop")` → produces correct stop control (STOP_TASK)
    - `build_command("clean_spot")` → produces START_SPOT_CLEAN with spot_clean param
    - `build_command("scene_clean", scene_id=5)` → produces DPS 152 with START_SCENE_CLEAN mode and correct scene ID
    - `build_command("room_clean", room_ids=[1,2], map_id=4)` → produces correct room selection command
    - `build_command("set_room_custom", room_config=[...], map_id=3)` → produces DPS 170 MapEditRequest with per-room settings
    - `build_command("set_auto_cfg", cfg={"collect_dust": True})` → produces DPS 173 StationRequest with auto_cfg
    - `build_command("go_selfcleaning")` → produces DPS 173 StationRequest with manual_cmd.go_selfcleaning=True
    - `build_command("go_dry")` → produces DPS 173 with manual_cmd.go_dry=True
    - `build_command("stop_dry")` → produces DPS 173 with manual_cmd.go_dry=False
    - `build_command("collect_dust")` → produces DPS 173 with manual_cmd.go_collect_dust=True
    - `build_command("locate", active=True)` → produces DPS 160 with boolean True
    - `build_command("set_fan_speed", fan_speed="Turbo")` → produces DPS 158 with correct index
    - `build_command("set_cleaning_mode", clean_mode="vacuum_mop")` → produces DPS 154 CleanParamRequest
    - `build_command("set_water_level", water_level="high")` → produces DPS 154 CleanParamRequest
    - `build_command("set_cleaning_intensity", cleaning_intensity="deep")` → produces DPS 154 CleanParamRequest
    - `build_command("reset_accessory", reset_type=1)` → produces DPS 168 ConsumableRequest
    - `build_command("set_child_lock", active=True)` → produces DPS 176 UnisettingRequest
    - `build_command("set_do_not_disturb", active=True, begin_hour=22, ...)` → produces DPS **157** UndisturbedRequest (NOT 178 — the DPS key is "UNDISTURBED" = "157")
    - **Command aliases** (verify these map to the same behavior as their primary):
      - `build_command("play")` → same as `resume` (RESUME_TASK)
      - `build_command("return_to_base")` → same as `go_home` (START_GOHOME)
      - `build_command("find_robot")` → same as `locate`
    - **Plain-value commands** (these return raw DPS values, NOT protobuf):
      - `build_command("set_fan_speed", fan_speed="Turbo")` → returns `{DPS 158: "2"}` (plain string index, NOT base64 protobuf)
      - `build_command("locate", active=True)` → returns `{DPS 160: True}` (raw boolean, NOT protobuf)
    - Unknown command: `build_command("nonexistent")` → returns empty dict `{}` (does NOT raise exception)
    - Invalid params (e.g., `set_fan_speed` with invalid speed name) → returns empty dict `{}` (logged as warning)
  - For each test: call `build_command()`, get the DPS dict, decode the base64 protobuf value using the appropriate proto type, assert proto fields match expectations
  - This is a ROUNDTRIP test: encode → decode → verify. If both encode and decode agree, the on-the-wire format is correct.

  **Must NOT do**:
  - Do NOT mock `encode_message` or `encode` — use real encoding
  - Do NOT test the MQTT sending (that's coordinator's job) — test only the command building

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Straightforward encode-decode testing, many commands but simple pattern
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 6-9, 11)
  - **Blocks**: None
  - **Blocked By**: Tasks 2, 3, 5

  **References**:

  **Pattern References**:
  - `tests/test_commands.py` — Current command tests (5 tests, edge cases only). Integration version should test every command type.
  - `tests/test_api.py` — Some command tests mixed with parser tests. Study command-related tests.

  **API/Type References**:
  - `custom_components/robovac_mqtt/api/commands.py` — `build_command()` dispatcher. Read the entire file to enumerate all supported commands.
  - `custom_components/robovac_mqtt/const.py` — `EUFY_CLEAN_CONTROL` enum (command codes: 0=AUTO, 1=SELECT_ROOMS, etc.)
  - `custom_components/robovac_mqtt/proto/cloud/control_pb2.py` — `ModeCtrlRequest` proto: the primary outbound command message
  - `custom_components/robovac_mqtt/proto/cloud/station_pb2.py` — `StationRequest` for dock commands
  - `custom_components/robovac_mqtt/proto/cloud/map_edit_pb2.py` — `MapEditRequest` for room custom settings

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: All command types produce valid protobuf
    Tool: Bash
    Steps:
      1. Run `pytest tests/integration/test_commands.py -v`
      2. Assert all tests pass
      3. Count test functions — at least 20 (one per command type + 2 invalid/unknown cases)
    Expected Result: Every build_command output decodes to expected protobuf fields
    Evidence: .sisyphus/evidence/task-10-commands.txt

  Scenario: Unknown and invalid param handling
    Tool: Bash
    Steps:
      1. Run `pytest tests/integration/test_commands.py -v -k "unknown or invalid"`
      2. Assert tests pass (empty dict returned as expected, no exceptions)
    Expected Result: Unknown command returns {}, invalid params return {} with warning logged
    Evidence: .sisyphus/evidence/task-10-invalid-commands.txt
  ```

  **Evidence to Capture:**
  - [ ] task-10-commands.txt
  - [ ] task-10-invalid-commands.txt

  **Commit**: YES (group 2b)
  - Message: `test(integration): add coordinator and command integration tests`
  - Files: `tests/integration/test_commands.py`
  - Pre-commit: `pytest tests/integration/test_commands.py -v`

---

- [x] 11. Config Flow Integration Tests

  **What to do**:
  - Create `tests/integration/test_config_flow.py`
  - Test the config flow THROUGH the HA runtime using `hass.config_entries.flow`
  - Mock only the network layer: patch `EufyHTTPClient` at the import path used by `config_flow.py`
  - **Test cases**:
    - **Happy path**: user step → enter email/password → mock login succeeds → entry created with correct data
    - **Login failure**: mock login raises exception → form shown again with error message
    - **Duplicate entry**: existing config entry with same email → abort with "already_configured"
    - **Entry data**: verify created entry's `data` dict contains email and any required config
    - **Reconfigure flow** (`async_step_reconfigure`): test reconfiguration when user wants to update credentials (NOTE: the code supports `reconfigure`, NOT `reauth`)
  - Use `MockConfigEntry` from `pytest_homeassistant_custom_component.common`
  - Assert on flow results: `result["type"]`, `result["step_id"]`, `result["errors"]`, `result["data"]`

  **Must NOT do**:
  - Do NOT mock the entire config flow — let the real flow handler execute
  - Do NOT test implementation details of EufyHTTPClient — just mock its responses

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Standard HA config flow testing pattern, well-documented
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 6-10)
  - **Blocks**: None
  - **Blocked By**: Tasks 2, 3, 5

  **References**:

  **Pattern References**:
  - `tests/test_config_flow.py` — Current config flow tests (2 tests: duplicate entry, entry data). Integration version should add happy path, login failure, full flow.
  - `custom_components/robovac_mqtt/config_flow.py` — The actual config flow handler. Read to understand steps, validation, and error handling.

  **API/Type References**:
  - `custom_components/robovac_mqtt/config_flow.py` — `RobovacMqttConfigFlow`: the flow class, `async_step_user()` method
  - `custom_components/robovac_mqtt/const.py` — `DOMAIN = "robovac_mqtt"`
  - `custom_components/robovac_mqtt/__init__.py` — `async_setup_entry()`: called after config entry created

  **External References**:
  - pytest-homeassistant-custom-component: `MockConfigEntry` from `.common`, `hass.config_entries.flow.async_init()` and `.async_configure()`

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Full config flow happy path
    Tool: Bash
    Steps:
      1. Run `pytest tests/integration/test_config_flow.py -v -k "happy_path"`
      2. Assert test passes
      3. Verify flow completes with type="create_entry"
    Expected Result: User can login and create config entry through HA flow
    Evidence: .sisyphus/evidence/task-11-config-flow.txt

  Scenario: Login failure shows error
    Tool: Bash
    Steps:
      1. Run `pytest tests/integration/test_config_flow.py -v -k "login_failure"`
      2. Assert test passes
      3. Verify flow shows form with errors, does NOT create entry
    Expected Result: Failed login returns to form with error indication
    Evidence: .sisyphus/evidence/task-11-login-failure.txt
  ```

  **Evidence to Capture:**
  - [ ] task-11-config-flow.txt
  - [ ] task-11-login-failure.txt

  **Commit**: YES (group 2c)
  - Message: `test(integration): add config flow integration tests`
  - Files: `tests/integration/test_config_flow.py`
  - Pre-commit: `pytest tests/integration/test_config_flow.py -v`

---

- [x] 12. Vacuum Entity Integration Tests

  **What to do**:
  - Create `tests/integration/test_vacuum_entity.py`
  - Test the vacuum entity THROUGH the HA runtime: setup integration → simulate MQTT messages → assert HA entity state/attributes
  - Use the `setup_integration` fixture from conftest.py to get a fully wired HA instance with coordinator
  - **Test cases**:
    - **State mapping**: Simulate WorkStatus messages → verify `hass.states.get("vacuum.{name}")` has correct `state` attribute (cleaning, docked, idle, returning, error)
    - **Fan speed**: Simulate CleanParam with fan speed → verify entity's `fan_speed` attribute
    - **Fan speed list**: Verify `fan_speed_list` attribute contains expected speed options
    - **Battery**: Simulate battery DPS → verify entity's `battery_level` attribute
    - **Start command**: Call `hass.services.async_call("vacuum", "start", ...)` → verify `coordinator.async_send_command` called with correct DPS for auto clean
    - **Stop command**: Call stop service → verify correct stop command sent
    - **Pause command**: Call pause service → verify correct pause command sent
    - **Return to base**: Call return_to_base service → verify go_home command sent
    - **Set fan speed**: Call set_fan_speed service → verify correct command sent
    - **Locate**: Call locate service → verify find_robot command sent
    - **Send command (scene_clean)**: Call `vacuum.send_command` with `scene_clean` → verify correct scene command sent
    - **Send command (room_clean)**: Call with `room_clean` params → verify room command with correct IDs
    - **Supported features**: Verify entity reports correct `supported_features` bitmask for X-Series
    - **Entity attributes**: Verify extra state attributes include rooms, segments, error info
  - Assert on `hass.states.get()` for state values — these are the user-visible outcomes

  **Must NOT do**:
  - Do NOT construct entity objects directly — use HA runtime setup
  - Do NOT check internal coordinator fields — check HA entity state only
  - Do NOT mock update_state or build_command

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Standard HA entity testing pattern with real runtime, well-documented pattern
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Tasks 13, 14, 15, 16, 17)
  - **Blocks**: None
  - **Blocked By**: Task 9 (coordinator pattern established)

  **References**:

  **Pattern References**:
  - `tests/test_vacuum.py` — Current vacuum tests (11 tests). Uses mock_coordinator directly. Integration version goes through HA runtime.
  - `tests/test_segment_cleaning.py` — Room/segment command tests.

  **API/Type References**:
  - `custom_components/robovac_mqtt/vacuum.py` — `RoboVacMQTTEntity`: the vacuum entity. Study `async_start()`, `async_stop()`, `async_pause()`, `async_return_to_base()`, `async_set_fan_speed()`, `async_locate()`, `async_send_command()`.
  - `custom_components/robovac_mqtt/vacuum.py` — `@property state`, `fan_speed`, `fan_speed_list`, `battery_level`, `extra_state_attributes`
  - `custom_components/robovac_mqtt/const.py` — `DOMAIN = "robovac_mqtt"` — needed for entity_id construction

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Vacuum entity state reflects MQTT WorkStatus
    Tool: Bash
    Steps:
      1. Run `pytest tests/integration/test_vacuum_entity.py -v -k "state_mapping"`
      2. Assert all state mapping tests pass
    Expected Result: HA entity state matches expected value for each WorkStatus.state
    Evidence: .sisyphus/evidence/task-12-vacuum-state.txt

  Scenario: Vacuum commands produce correct MQTT payloads
    Tool: Bash
    Steps:
      1. Run `pytest tests/integration/test_vacuum_entity.py -v -k "command"`
      2. Assert all command tests pass
      3. Verify at least 6 command types tested (start, stop, pause, return, fan_speed, locate)
    Expected Result: Each HA service call produces the expected DPS command
    Evidence: .sisyphus/evidence/task-12-vacuum-commands.txt
  ```

  **Evidence to Capture:**
  - [ ] task-12-vacuum-state.txt
  - [ ] task-12-vacuum-commands.txt

  **Commit**: YES (group 3a)
  - Message: `test(integration): add entity integration tests`
  - Files: `tests/integration/test_vacuum_entity.py`
  - Pre-commit: `pytest tests/integration/test_vacuum_entity.py -v`

---

- [x] 13. Sensor Entity Integration Tests

  **What to do**:
  - Create `tests/integration/test_sensor_entities.py`
  - Test sensor entities through HA runtime: setup integration → simulate MQTT → verify sensor states
  - **Test cases**:
    - **Battery sensor**: DPS 163 → sensor shows battery percentage
    - **Error sensor**: DPS 177 → sensor shows error description from EUFY_CLEAN_ERROR_CODES
    - **Task status sensor**: DPS 153 → sensor shows task_status string
    - **Cleaning area sensor**: DPS 167 → sensor shows cleaning_area value
    - **Cleaning time sensor**: DPS 167 → sensor shows cleaning_time value
    - **Work mode sensor**: DPS 153 → sensor shows work_mode string
    - **Active cleaning target sensor**: shows active room names or zone count
    - **Consumable sensors**: DPS 168 → each consumable sensor (filter, main brush, side brush, sensor, scrape, mop) shows remaining life hours
    - **WiFi signal sensor**: DPS 176 → sensor shows wifi_signal dBm value
    - **WiFi SSID sensor**: DPS 169 → sensor shows wifi_ssid
    - **WiFi IP sensor**: DPS 169 → sensor shows wifi_ip
    - **Robot position sensors**: DPS 179 → robot_position_x, robot_position_y
    - **Binary sensors** (`binary_sensor.py`): charging binary sensor → on when charging, off otherwise
    - **Availability**: Sensors that depend on specific DPS data → unavailable until first DPS received, available after
    - **Dock status sensor**: Verify dock_status sensor reflects debounced dock state
    - **Active map sensor**: DPS 165 → sensor shows map_id

  **Must NOT do**:
  - Do NOT test each sensor in isolation — test through HA runtime
  - Do NOT test value extraction lambda functions directly — test the observable sensor state

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Multiple sensors but straightforward pattern — simulate DPS, check sensor state
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Tasks 12, 14, 15, 16, 17)
  - **Blocks**: None
  - **Blocked By**: Task 9

  **References**:

  **Pattern References**:
  - `tests/test_sensor.py` — Current sensor tests (6 tests). Integration version uses HA runtime.
  - `tests/test_sensor_accessories.py` — Accessory sensor tests.

  **API/Type References**:
  - `custom_components/robovac_mqtt/sensor.py` — `RoboVacSensor` entities, `async_setup_entry()` entity list with `value_fn` lambdas and `availability_fn` lambdas
  - `custom_components/robovac_mqtt/models.py` — VacuumState fields that sensors read

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: All sensor types respond to DPS updates
    Tool: Bash
    Steps:
      1. Run `pytest tests/integration/test_sensor_entities.py -v`
      2. Assert all tests pass
      3. Count at least 9 test functions
    Expected Result: Each sensor type correctly reflects its DPS data
    Evidence: .sisyphus/evidence/task-13-sensors.txt

  Scenario: Sensor availability tracks received_fields
    Tool: Bash
    Steps:
      1. Run `pytest tests/integration/test_sensor_entities.py -v -k "availability"`
      2. Assert availability test passes — sensor unavailable before DPS, available after
    Expected Result: Sensors with availability_fn are unavailable until relevant DPS received
    Evidence: .sisyphus/evidence/task-13-availability.txt
  ```

  **Evidence to Capture:**
  - [ ] task-13-sensors.txt
  - [ ] task-13-availability.txt

  **Commit**: YES (group 3a)
  - Message: `test(integration): add entity integration tests`
  - Files: `tests/integration/test_sensor_entities.py`
  - Pre-commit: `pytest tests/integration/test_sensor_entities.py -v`

---

- [x] 14. Control Entity Integration Tests (Select/Switch/Button/Number/Time)

  **What to do**:
  - Create `tests/integration/test_control_entities.py`
  - Test all control-type entities through HA runtime
  - **Select entities** (ALL selects from `select.py:76-125`):
    - Scene selection: select option → verify scene_clean command sent with correct scene_id
    - Room selection: select room → verify room_clean command sent
    - Suction level (fan speed) select → verify set_fan_speed command
    - Cleaning mode selection → verify set_cleaning_mode command
    - Water level select → verify set_water_level command
    - **Mop intensity select** → verify set_water_level command (Matter-compatible alias)
    - Cleaning intensity select → verify set_cleaning_intensity command
    - **Wash frequency mode select** → verify set_auto_cfg command
    - **Dry duration select** (NOTE: this is a SELECT entity in `select.py`, NOT a number) → verify set_auto_cfg command
    - **Auto empty mode select** → verify set_auto_cfg command
    - Select options populated from state (scenes list, rooms list)
  - **Switch entities** (ALL switches from `switch.py`):
    - Find robot toggle → verify DPS 160 sent
    - Auto empty toggle → verify DPS 173 StationRequest with auto-empty config
    - Auto mop wash toggle → verify correct command
    - Child lock toggle → verify set_child_lock command
    - **Do Not Disturb switch** → verify set_do_not_disturb command (DPS 157)
  - **Button entities**:
    - Wash mop button → verify go_selfcleaning command sent
    - Dry mop button → verify go_dry command
    - Stop dry button → verify stop_dry command
    - Empty dust button → verify collect_dust command
    - Reset consumable buttons → verify reset_accessory commands
  - **Number entities**:
    - Wash frequency value → verify set_auto_cfg command with correct value
  - **Time entities** (`time.py` — Do Not Disturb):
    - DND start time entity: set time → verify set_do_not_disturb command with correct begin_hour/begin_minute
    - DND end time entity: set time → verify set_do_not_disturb command with correct end_hour/end_minute
    - DND time values reflect current state (dnd_start_hour/minute, dnd_end_hour/minute from VacuumState)
  - For each: call HA service → capture `coordinator.async_send_command` argument → verify DPS payload

  **Must NOT do**:
  - Do NOT test entity constructors — test through HA services
  - Do NOT combine select/switch/button/number into separate files — one file is manageable

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Many entity types but repetitive pattern — service call → verify command
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Tasks 12, 13, 15, 16, 17)
  - **Blocks**: None
  - **Blocked By**: Task 9

  **References**:

  **Pattern References**:
  - `tests/test_select.py` — Current select tests (15 tests). Integration version uses HA services. Note: dry duration is a select, not a number.
  - `tests/test_switch.py` — Current switch tests (9 tests).
  - `tests/test_button.py` — Current button tests (2 tests).
  - `tests/test_number.py` — Current number tests (6 tests).
  - `tests/test_time.py` — Current time entity tests (2 tests). DND start/end time entities.

  **API/Type References**:
  - `custom_components/robovac_mqtt/select.py` — Select entities: `SceneSelectEntity`, `RoomSelectEntity`, cleaning parameter selects, **dry duration select**
  - `custom_components/robovac_mqtt/switch.py` — Switch entities: find robot, auto-empty, auto-wash, child lock
  - `custom_components/robovac_mqtt/button.py` — Button entities: wash mop (go_selfcleaning), dry (go_dry), stop dry (stop_dry), empty dust (collect_dust), reset consumables
  - `custom_components/robovac_mqtt/number.py` — Number entities: wash frequency value
  - `custom_components/robovac_mqtt/time.py` — Time entities: DND start time, DND end time (DoNotDisturbStartTimeEntity, DoNotDisturbEndTimeEntity)
  - `custom_components/robovac_mqtt/api/commands.py` — `build_command()` for expected DPS payloads

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Control entities send correct commands
    Tool: Bash
    Steps:
      1. Run `pytest tests/integration/test_control_entities.py -v`
      2. Assert all tests pass
      3. Count at least 15 test functions covering selects, switches, buttons, and numbers
    Expected Result: Every control entity action produces the correct DPS command
    Evidence: .sisyphus/evidence/task-14-controls.txt

  Scenario: Select options reflect device state
    Tool: Bash
    Steps:
      1. Run `pytest tests/integration/test_control_entities.py -v -k "options_populated"`
      2. Assert test passes — scene select has options matching scenes in state, room select matches rooms
    Expected Result: Dynamic select entities reflect current device state
    Evidence: .sisyphus/evidence/task-14-dynamic-options.txt
  ```

  **Evidence to Capture:**
  - [ ] task-14-controls.txt
  - [ ] task-14-dynamic-options.txt

  **Commit**: YES (group 3a)
  - Message: `test(integration): add entity integration tests`
  - Files: `tests/integration/test_control_entities.py`
  - Pre-commit: `pytest tests/integration/test_control_entities.py -v`

---

- [x] 15. Edge Case + Robustness Tests

  **What to do**:
  - Create `tests/integration/test_edge_cases.py`
  - Test behavior at the boundaries — malformed input, missing data, unexpected values
  - **Test cases**:
    - **Malformed protobuf**: DPS value that isn't valid base64 → warning logged, state unchanged
    - **Truncated protobuf**: Valid base64 but incomplete protobuf bytes → warning logged, state unchanged
    - **Unknown DPS key**: DPS key not in DPS_MAP (e.g., "999") → either ignored or logged, no crash
    - **Missing optional fields**: WorkStatus without station field → activity derived without station data
    - **Empty DPS dict**: `update_state(state, {})` → state unchanged
    - **None values in DPS**: `update_state(state, {"163": None})` → handled gracefully
    - **Extremely large values**: Battery=999, error_code=99999 → handled without crash
    - **Rapid state updates**: 10 DPS messages in quick succession → final state is correct
    - **Payload nesting variants**: 
      - `payload.data` as dict (normal)
      - `payload` as JSON string that needs double-parsing (coordinator.py:124)
      - Missing `payload` key → graceful handling
      - Missing `data` key inside payload → graceful handling
    - **Concurrent DPS keys**: Message with both DPS 153 (WorkStatus) and DPS 163 (battery) → both processed
    - **Received_fields tracking**: Verify that `received_fields` set grows as DPS messages arrive, never shrinks
    - **DPS 158 (CLEAN_SPEED)**: Plain integer handling (not protobuf) — verify it doesn't go through protobuf decode
    - **DPS 160 (FIND_ROBOT)**: Plain boolean handling — verify it doesn't go through protobuf decode

  **Must NOT do**:
  - Do NOT test implementation-specific error messages — test that the system doesn't crash and state is preserved
  - Do NOT create edge cases that are impossible in practice (e.g., negative battery) unless testing defensive coding

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: Requires adversarial thinking about boundary conditions and failure modes
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Tasks 12, 13, 14, 16, 17)
  - **Blocks**: None
  - **Blocked By**: Tasks 2, 3, 5

  **References**:

  **Pattern References**:
  - `tests/test_utils.py` — Tests for encode/decode edge cases (varint edge cases). Reference for encoding boundary tests.
  - `custom_components/robovac_mqtt/coordinator.py:180-181` — `except Exception as e: _LOGGER.warning(...)` — the catch-all handler. Edge case tests should verify this catches errors gracefully.

  **API/Type References**:
  - `custom_components/robovac_mqtt/api/parser.py` — `update_state()` function: the main entry point. Read error handling paths.
  - `custom_components/robovac_mqtt/coordinator.py:116-181` — `_handle_mqtt_message()`: JSON parsing and error handling.
  - `custom_components/robovac_mqtt/const.py` — `DPS_MAP`, `KNOWN_UNPROCESSED_DPS` — understand which keys are expected vs unknown.

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Malformed input doesn't crash the system
    Tool: Bash
    Steps:
      1. Run `pytest tests/integration/test_edge_cases.py -v`
      2. Assert all tests pass
      3. Count at least 12 test functions
    Expected Result: All edge cases handled gracefully (no crashes, state preserved when appropriate)
    Evidence: .sisyphus/evidence/task-15-edge-cases.txt

  Scenario: Unknown DPS key is handled gracefully
    Tool: Bash
    Steps:
      1. Run `pytest tests/integration/test_edge_cases.py -v -k "unknown_dps"`
      2. Assert test passes, no exception raised
    Expected Result: Unknown DPS keys logged or ignored, not crashing
    Evidence: .sisyphus/evidence/task-15-unknown-dps.txt
  ```

  **Evidence to Capture:**
  - [ ] task-15-edge-cases.txt
  - [ ] task-15-unknown-dps.txt

  **Commit**: YES (group 3b)
  - Message: `test(integration): add edge case and E2E cleaning cycle tests`
  - Files: `tests/integration/test_edge_cases.py`
  - Pre-commit: `pytest tests/integration/test_edge_cases.py -v`

---

- [x] 15b. HA Lifecycle Integration Tests (Unload, Remove, Storage)

  **What to do**:
  - Create `tests/integration/test_ha_lifecycle.py`
  - Test HA lifecycle paths that are NOT covered by other tasks:
  - **Unload entry** (`async_unload_entry`):
    - Setup integration → call `await hass.config_entries.async_unload(config_entry.entry_id)` → verify timers are shut down, MQTT client disconnected, hass.data cleaned up
    - NOTE: call `async_unload()` on the config entry, NOT `async_unload_platforms()` directly. The timer shutdown and MQTT disconnect logic lives in `async_unload_entry()` (`__init__.py:135-149`) which wraps the platform unload.
    - Verify `coordinator.async_shutdown_timers()` is called
    - Verify `coordinator.client.disconnect()` is called
  - **Remove device** (`async_remove_config_entry_device`):
    - Verify it returns True (currently a passthrough, but test that it doesn't crash)
  - **Storage operations**:
    - `async_load_storage()`: verify segments loaded from persistent store
    - `async_save_segments()`: verify segments saved to persistent store
    - Config entry segment migration (`__init__.py:73-84`): verify segments migrate from config entry data to per-device Store on first load, and are skipped for multi-device setups
  - **Update listener**:
    - Trigger config entry update → verify integration reloads

  **Must NOT do**:
  - Do NOT test storage internals (HA Store implementation) — test the coordinator's use of it

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Standard HA lifecycle testing, well-documented patterns
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Tasks 9, 11-15)
  - **Blocks**: None
  - **Blocked By**: Task 9

  **References**:

  **Pattern References**:
  - `tests/test_init.py` — Current setup test (1 test). Check what's already covered.
  - `tests/test_orphaned_devices.py` — Current orphaned device test (1 test).

  **API/Type References**:
  - `custom_components/robovac_mqtt/__init__.py:135-149` — `async_unload_entry()`: unloads platforms, shuts down timers, disconnects clients
  - `custom_components/robovac_mqtt/__init__.py:152-156` — `async_remove_config_entry_device()`: returns True
  - `custom_components/robovac_mqtt/__init__.py:73-84` — Segment migration: loads from config entry, saves to Store if single device
  - `custom_components/robovac_mqtt/coordinator.py:207-214` — `async_shutdown_timers()`: cancels debounce timers
  - `custom_components/robovac_mqtt/coordinator.py:278-296` — `async_load_storage()` and `async_save_segments()`

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Unload entry cleans up correctly
    Tool: Bash
    Steps:
      1. Run `pytest tests/integration/test_ha_lifecycle.py -v -k "unload"`
      2. Assert test passes — timers cancelled, client disconnected, data cleaned
    Expected Result: Clean unload with no resource leaks
    Evidence: .sisyphus/evidence/task-15b-unload.txt

  Scenario: Storage roundtrip works
    Tool: Bash
    Steps:
      1. Run `pytest tests/integration/test_ha_lifecycle.py -v -k "storage"`
      2. Assert tests pass — save then load returns same segments
    Expected Result: Segments persist and reload correctly
    Evidence: .sisyphus/evidence/task-15b-storage.txt
  ```

  **Evidence to Capture:**
  - [ ] task-15b-unload.txt
  - [ ] task-15b-storage.txt

  **Commit**: YES (group 3a)
  - Message: `test(integration): add entity integration tests`
  - Files: `tests/integration/test_ha_lifecycle.py`
  - Pre-commit: `pytest tests/integration/test_ha_lifecycle.py -v`

---

- [x] 16. Full Cleaning Cycle E2E Tests

  **What to do**:
  - Create `tests/integration/test_cleaning_cycle.py`
  - Test COMPLETE cleaning lifecycle through the FULL pipeline: MQTT messages → coordinator → HA entity states
  - Uses `setup_integration` fixture for full HA runtime
  - Loads sequence fixtures from `tests/fixtures/sequences/`
  - **Test cases**:
    - **Full auto clean cycle**:
      1. Initial state: docked, battery=100
      2. Start command issued → DPS 152 sent
      3. MQTT: WorkStatus state=4 (positioning) → entity state=cleaning
      4. MQTT: WorkStatus state=5 (active clean) → entity state=cleaning, task_status=cleaning
      5. MQTT: battery DPS 163 decreasing (100→85→70) → battery sensor updates
      6. MQTT: WorkStatus state=7 (returning) → entity state=returning
      7. MQTT: WorkStatus state=3 (docked, charging) → entity state=docked, charging=true
      Verify entity state after EACH message.
    - **Dock wash-dry cycle**:
      1. State: docked
      2. Go-wash command issued
      3. MQTT: WorkStatus state=5 + station washing → entity state=docked, dock_status=Washing
      4. Wait 2s (debounce) → dock_status committed
      5. MQTT: station drying → dock_status=Drying (after debounce)
      6. MQTT: station idle → dock_status=Idle (after debounce)
    - **Interrupted clean cycle**:
      1. Cleaning active
      2. MQTT: WorkStatus state=2 (error, e.g., wheel stuck) → entity state=error, error sensor shows message
      3. MQTT: WorkStatus state=0 (idle after error cleared) → entity state=idle, error cleared
    - **Scene clean cycle**:
      1. Scene command issued with scene_id=5
      2. MQTT: WorkStatus with mode reflecting scene clean
      3. Verify scene_name attribute populated
      4. Cleaning → returning → docked sequence
    - **Room clean cycle**:
      1. Room command issued with room_ids=[1,2]
      2. MQTT: WorkStatus with active room information
      3. Verify active_room_names attribute populated
  - Use `async_fire_time_changed` for debounce timing in dock tests
  - This is the highest-fidelity test — closest to actual runtime behavior

  **Must NOT do**:
  - Do NOT hardcode DPS values — use sequence fixtures
  - Do NOT skip debounce timing — dock status must go through real debounce
  - Do NOT assert on intermediate implementation details — assert on HA entity state

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: Complex multi-step sequences through full HA runtime, timing-sensitive, highest integration level
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Tasks 12-15, 17)
  - **Blocks**: None
  - **Blocked By**: Task 9 (coordinator patterns)

  **References**:

  **Pattern References**:
  - `tests/integration/test_coordinator.py` (from Task 9) — Coordinator test patterns, especially debounce timing
  - `tests/test_task_status_flapping.py` — Sequential state update pattern with real DPS payloads

  **API/Type References**:
  - `tests/fixtures/sequences/full_cleaning_cycle.json` — Sequence fixture for auto clean
  - `tests/fixtures/sequences/dock_wash_dry_cycle.json` — Sequence fixture for dock cycle
  - `custom_components/robovac_mqtt/coordinator.py:116-199` — Message handling + debounce logic
  - `custom_components/robovac_mqtt/vacuum.py` — Entity state properties
  - `custom_components/robovac_mqtt/sensor.py` — Sensor state properties

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Full auto clean cycle produces correct state sequence
    Tool: Bash
    Steps:
      1. Run `pytest tests/integration/test_cleaning_cycle.py -v -k "auto_clean"`
      2. Assert test passes
      3. Verify state progression: docked → cleaning → cleaning → returning → docked
    Expected Result: Entity state correctly reflects each phase of cleaning cycle
    Failure Indicators: State stuck, wrong intermediate state, debounce failure
    Evidence: .sisyphus/evidence/task-16-auto-clean.txt

  Scenario: Dock wash-dry cycle with debouncing
    Tool: Bash
    Steps:
      1. Run `pytest tests/integration/test_cleaning_cycle.py -v -k "dock_wash_dry"`
      2. Assert test passes
      3. Verify dock_status transitions through Washing → Drying → Idle with 2s delays
    Expected Result: Dock status correctly debounced and committed after timer
    Evidence: .sisyphus/evidence/task-16-dock-cycle.txt

  Scenario: Error interrupts cleaning cycle gracefully
    Tool: Bash
    Steps:
      1. Run `pytest tests/integration/test_cleaning_cycle.py -v -k "interrupted"`
      2. Assert test passes — cleaning → error → idle
    Expected Result: Error state correctly interrupts cleaning, error message populated
    Evidence: .sisyphus/evidence/task-16-interrupted.txt
  ```

  **Evidence to Capture:**
  - [ ] task-16-auto-clean.txt
  - [ ] task-16-dock-cycle.txt
  - [ ] task-16-interrupted.txt

  **Commit**: YES (group 3b)
  - Message: `test(integration): add edge case and E2E cleaning cycle tests`
  - Files: `tests/integration/test_cleaning_cycle.py`
  - Pre-commit: `pytest tests/integration/test_cleaning_cycle.py -v`

---

- [x] 17. Unit Test Audit Resolution — Refactor/Remove Conflicts

  **What to do**:
  - Read `tests/integration/AUDIT.md` (produced by Task 4)
  - For each test classified as **REDUNDANT**: remove it from the unit test file. Add a comment at the top of the unit test file noting which tests moved to integration suite.
  - For each test classified as **CONFLICT**: investigate whether the unit test or the integration test has the correct expected behavior. If the unit test encodes a bug, remove it. If the integration test is wrong, fix the integration test instead. Document each conflict resolution in a `CONFLICT_LOG` section of AUDIT.md.
  - For each test classified as **REFACTOR**: simplify the unit test (reduce unnecessary mocking, clarify assertions). Keep it as a unit test but make it more robust.
  - **Constraints**:
    - After all changes, `pytest tests/ --ignore=tests/integration/` must still pass with 0 failures
    - After all changes, `pytest tests/integration/` must execute to completion without infrastructure errors (assertion failures from discovered bugs are acceptable per Bug Discovery Protocol)
    - No test should exist in BOTH unit and integration suites testing the same behavior
  - Update AUDIT.md with a "Resolution" column showing what was done for each test

  **Must NOT do**:
  - Do NOT remove unit tests that have no integration equivalent (KEEP classified tests)
  - Do NOT modify production code to fix conflicting tests
  - Do NOT delete test files entirely — only remove specific test functions
  - Do NOT change test behavior to make both suites pass if there's a genuine conflict — the integration test wins (closer to real behavior)

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Systematic refactoring based on audit findings, requires careful judgment
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Tasks 12-16)
  - **Blocks**: None
  - **Blocked By**: Task 4 (audit findings) + Tasks 6-16 (need integration tests written first to verify no duplication)

  **References**:

  **Pattern References**:
  - `tests/integration/AUDIT.md` — The audit report from Task 4, containing classifications and recommendations
  - All test files in `tests/` — the files to be modified

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Unit tests pass after resolution
    Tool: Bash
    Steps:
      1. Run `pytest tests/ --ignore=tests/integration/ -v`
      2. Assert 0 failures, 0 errors (unit tests must remain green)
      3. Note total test count (should be less than original 195 if redundant tests removed)
    Expected Result: All remaining unit tests pass
    Evidence: .sisyphus/evidence/task-17-unit-pass.txt

  Scenario: Integration tests execute after resolution
    Tool: Bash
    Steps:
      1. Run `pytest tests/integration/ -v --tb=short`
      2. Assert 0 infrastructure errors (import errors, fixture errors)
      3. Record pass/fail: N passed, M failed (assertion failures from discovered bugs are acceptable)
    Expected Result: All integration tests execute to completion
    Evidence: .sisyphus/evidence/task-17-integration-pass.txt

  Scenario: No duplicate test names across suites
    Tool: Bash
    Steps:
      1. Run `pytest tests/ tests/integration/ --co -q`
      2. Extract test names, check for duplicates
      3. Assert no test name appears in both suites
    Expected Result: Zero duplicate test identifiers
    Evidence: .sisyphus/evidence/task-17-no-duplicates.txt
  ```

  **Evidence to Capture:**
  - [ ] task-17-unit-pass.txt
  - [ ] task-17-integration-pass.txt
  - [ ] task-17-no-duplicates.txt

  **Commit**: YES (group 3c)
  - Message: `refactor(test): remove unit test overlap per audit findings`
  - Files: `tests/test_*.py` (modified), `tests/integration/AUDIT.md` (updated)
  - Pre-commit: `pytest tests/ --ignore=tests/integration/ -q && pytest tests/integration/ --co -q`

---

- [x] 18. CI Pipeline Update — Integration Test Job + Coverage

  **What to do**:
  - Update `.github/workflows/tests.yaml` to:
    - Split into two jobs: `unit-tests` and `integration-tests`
    - **unit-tests job**: runs `pytest tests/ --ignore=tests/integration/ -v` (fast feedback, existing behavior)
    - **integration-tests job**: runs `pytest tests/integration/ -v` (separate, may be slower)
    - Both jobs share the same Python version (3.13), OS (ubuntu-latest), and dependency install steps
    - Add `pytest-cov` to dependencies and run integration tests with `--cov=custom_components/robovac_mqtt --cov-report=term-missing`
    - Add coverage report as job summary (use `--cov-report=html` and upload as artifact, or just print to log)
  - Add `pytest-cov` to `requirements_test.txt`
  - Verify the split doesn't break the existing test run

  **Must NOT do**:
  - Do NOT remove the ability to run all tests with a single `pytest` command locally
  - Do NOT add coverage thresholds that would fail CI (coverage is informational at this stage)
  - Do NOT add matrix testing for multiple Python versions (out of scope)

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Small configuration change to CI and requirements file
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 4 (alone)
  - **Blocks**: None
  - **Blocked By**: All previous tasks (CI should reflect final test structure)

  **References**:

  **Pattern References**:
  - `.github/workflows/tests.yaml` — Current CI config (25 lines). Single job, single `pytest` run.

  **API/Type References**:
  - `pyproject.toml:71-81` — Current pytest config: testpaths, asyncio_mode
  - `requirements_test.txt` — Current test dependencies

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: CI workflow is valid YAML
    Tool: Bash
    Steps:
      1. Run `python -c "import yaml; yaml.safe_load(open('.github/workflows/tests.yaml'))"`
      2. Assert exit code 0
      3. Assert output contains two job definitions
    Expected Result: Valid YAML with unit-tests and integration-tests jobs
    Evidence: .sisyphus/evidence/task-18-ci-valid.txt

  Scenario: Both test suites runnable locally
    Tool: Bash
    Steps:
      1. Run `pytest tests/ --ignore=tests/integration/ -q` — assert passes (unit tests green)
      2. Run `pytest tests/integration/ --co -q` — assert collects all tests without errors
      3. Run `pytest tests/integration/ -v --tb=short` — verify runs to completion (assertion failures from bugs are acceptable)
    Expected Result: Tests runnable both separately. Unit tests green. Integration tests execute to completion.
    Evidence: .sisyphus/evidence/task-18-both-suites.txt
  ```

  **Evidence to Capture:**
  - [ ] task-18-ci-valid.txt
  - [ ] task-18-both-suites.txt

  **Commit**: YES (group 4a)
  - Message: `ci: add integration test job with coverage reporting`
  - Files: `.github/workflows/tests.yaml`, `requirements_test.txt`
  - Pre-commit: —

---

## Final Verification Wave

> 4 review agents run in PARALLEL. ALL must APPROVE. Results are presented to user for explicit approval before completing.
> Agent-executed reviews — no manual testing by humans. "Real Manual QA" means the agent performs end-to-end QA (not a human).

- [x] F1. **Plan Compliance Audit** — `oracle`
  Read the plan end-to-end. For each "Must Have": verify implementation exists. For each "Must NOT Have": search codebase for forbidden patterns. Check evidence files exist in .sisyphus/evidence/.

  ```
  Scenario: Plan compliance verified
    Tool: Bash + Grep
    Steps:
      1. For each "Must Have" item, search codebase for evidence (grep for fixture files, test files, anonymization)
      2. For each "Must NOT Have" item, grep for forbidden patterns (production code changes, mocked update_state in integration tests, network calls)
      3. Verify .sisyphus/evidence/ has files for each task
      4. Compare deliverables list against actual files created
    Expected Result: All Must Have items present, all Must NOT Have items absent
    Evidence: .sisyphus/evidence/f1-compliance.txt
  ```
  Output: `Must Have [N/N] | Must NOT Have [N/N] | Tasks [N/N] | VERDICT: APPROVE/REJECT`

- [x] F2. **Code Quality Review** — `unspecified-high`
  Run linter + type check. Review all new test files for quality.

  ```
  Scenario: Code quality passes review
    Tool: Bash
    Steps:
      1. Run `pytest tests/ --ignore=tests/integration/ -v` — verify unit tests still pass
      2. Run `pytest tests/integration/ --co -q` — verify all integration tests are collectible
      3. Review new test files for: proper assertions (not just `assert True`), no mocking of code-under-test, no duplicate test names
      4. Check for AI slop: excessive comments, over-abstraction, generic names
    Expected Result: Unit tests green, integration tests collectible, no quality red flags
    Evidence: .sisyphus/evidence/f2-quality.txt
  ```
  Output: `Unit Tests [PASS/FAIL] | Integration Tests [COLLECTIBLE/ERROR] | Files [N clean/N issues] | VERDICT`

- [x] F3. **Real Manual QA** — `unspecified-high`
  Execute the full test suite from clean state.

  ```
  Scenario: Full suite executes cleanly
    Tool: Bash
    Steps:
      1. Run `pytest tests/integration/ -v --tb=short` — capture full output
      2. Verify all tests EXECUTE (no import errors, no fixture errors, no conftest failures)
      3. Record pass/fail breakdown: N passed, M failed, K errors
      4. For each failure, verify it's an assertion failure (= discovered bug) not an infrastructure error
      5. Verify fixture files are valid JSON and proto payloads decode correctly
      6. Verify no network calls are made (check for DNS/socket activity)
    Expected Result: All tests execute. Failures are categorized as bugs or test errors. Zero infrastructure errors.
    Evidence: .sisyphus/evidence/f3-manual-qa.txt
  ```
  Output: `Executed [N/N] | Passed [M] | Failed (bugs) [K] | Errors (infra) [0] | VERDICT`

- [x] F4. **Scope Fidelity Check** — `deep`
  Verify every task was implemented as specified, nothing extra added.

  ```
  Scenario: Scope fidelity verified
    Tool: Bash + Grep
    Steps:
      1. For each task: read "What to do", compare against actual files created
      2. Verify no production code under custom_components/ was modified
      3. Verify no unit tests were deleted without being classified as REDUNDANT in AUDIT.md
      4. Verify capture tool extends eufy_mqtt_client.py (not a new file)
      5. Flag any unaccounted changes not in the plan
    Expected Result: 1:1 match between plan and implementation, no scope creep
    Evidence: .sisyphus/evidence/f4-scope.txt
  ```
  Output: `Tasks [N/N compliant] | Scope [CLEAN/N issues] | VERDICT`

---

## Commit Strategy

| Wave | Commit | Message | Files | Pre-commit |
|------|--------|---------|-------|------------|
| 1 | 1a | `feat(test): add data capture mode and anonymization tooling` | tools/eufy_mqtt_client.py (modified), tools/anonymize_fixtures.py | `python tools/eufy_mqtt_client.py --help && python tools/anonymize_fixtures.py --help` |
| 1 | 1b | `feat(test): add integration test infrastructure and fixtures` | tests/integration/conftest.py, tests/integration/helpers.py, tests/integration/__init__.py | `pytest tests/integration/ --co -q` |
| 1 | 1c | `chore(test): audit existing unit tests for integration overlap` | tests/integration/AUDIT.md | — |
| 2 | 2a | `feat(test): organize captured fixture data` | tests/fixtures/**/*.json | `python -c "import json, glob; [json.load(open(f)) for f in glob.glob('tests/fixtures/**/*.json', recursive=True)]"` |
| 3 | 3a | `test(protocol): add parser protocol tests` | tests/integration/test_parser_work_status.py, test_parser_station.py, test_parser_clean_param.py, test_parser_map_data.py, test_parser_remaining.py | `pytest tests/integration/test_parser*.py --co -q` (collect-only, verify no import errors) |
| 3 | 3b | `test(protocol): add command roundtrip tests` | tests/integration/test_commands.py | `pytest tests/integration/test_commands.py --co -q` |
| 3 | 3c | `test(integration): add config flow and edge case tests` | tests/integration/test_config_flow.py, tests/integration/test_edge_cases.py | `pytest tests/integration/test_config_flow.py tests/integration/test_edge_cases.py --co -q` |
| 4 | 4a | `test(integration): add coordinator lifecycle tests` | tests/integration/test_coordinator.py | `pytest tests/integration/test_coordinator.py --co -q` |
| 5 | 5a | `test(integration): add entity integration tests` | tests/integration/test_vacuum_entity.py, test_sensor_entities.py, test_control_entities.py, test_ha_lifecycle.py | `pytest tests/integration/test_vacuum_entity.py tests/integration/test_sensor_entities.py tests/integration/test_control_entities.py tests/integration/test_ha_lifecycle.py --co -q` |
| 5 | 5b | `test(integration): add full cleaning cycle E2E tests` | tests/integration/test_cleaning_cycle.py | `pytest tests/integration/test_cleaning_cycle.py --co -q` |
| 6 | 6a | `refactor(test): remove unit test overlap per audit findings` | tests/test_*.py (modified), tests/integration/AUDIT.md (updated) | `pytest tests/ --ignore=tests/integration/ -q` |
| 6 | 6b | `ci: add integration test job with coverage reporting` | .github/workflows/tests.yaml, requirements_test.txt | — |

---

## Success Criteria

### Verification Commands
```bash
pytest tests/ --ignore=tests/integration/ -v    # Expected: all unit tests pass (0 failures)
pytest tests/integration/ -v                     # Expected: runs to completion, failures = discovered bugs
pytest tests/ tests/integration/ --co -q         # Expected: no duplicate test names
python tools/eufy_mqtt_client.py --help          # Expected: prints usage help including --capture mode
python tools/anonymize_fixtures.py --help        # Expected: prints usage help
```

### Final Checklist
- [ ] All "Must Have" present (real fixtures, anonymization, behavior assertions, debouncing, state=5, edge cases, E2E)
- [ ] All "Must NOT Have" absent (no prod changes, no duplication, no mocked code-under-test, no network, no magic numbers)
- [ ] All unit tests still pass
- [ ] All integration tests execute without infrastructure errors (assertion failures = discovered bugs)
- [ ] Fixture files are real captured data (anonymized), committed and valid
- [ ] CI pipeline updated with both jobs
- [ ] HA lifecycle tested (unload, remove, storage)
