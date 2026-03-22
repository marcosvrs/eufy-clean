## v1.8.0

### New Features

**Cleaning Parameter Controls**
Fine-grained cleaning settings exposed as select entities — shown only when supported by your device firmware:
- **Suction Level** — Quiet, Standard, Turbo, Max
- **Cleaning Mode** — Vacuum, Mop, Vacuum and mop, Mopping after sweeping
- **Water Level** — Low, Medium, High
- **Cleaning Intensity** — Normal, Narrow, Quick
- **Mop Intensity** — Quiet, Automatic, Max (Matter-compatible alias for Water Level)

**DPS 154 Support**
Full protobuf parsing of the `CleanParam` message from newer device firmware, extracting cleaning mode, fan speed, water level, corner cleaning, carpet strategy, and smart mode — with 100% backward compatibility for older models.

**Matter Hub Compatibility**
Designed to work with [home-assistant-matter-hub](https://github.com/RiDDiX/home-assistant-matter-hub) for exposing your Eufy vacuum to Apple Home, Google Home, and other Matter ecosystems:
- Mop Intensity entity uses Matter-standard option names
- Room segments exposed with guaranteed unique names
- Dedicated battery sensor entity for Matter bridge discovery

**Segment Change Detection**
When the vacuum's room map changes (rooms added, removed, or renamed), a **Repair issue** is raised in Home Assistant under Settings → System → Repairs. This prevents stale room names from breaking automations, especially when using the Matter bridge.

**Dedicated Battery Sensor**
Standalone battery entity required by newer versions of Home Assistant.

### Improvements

- Dock configuration controls: Wash Frequency Mode, Dry Duration, Auto Empty Mode
- Work mode tracking (Auto, Room, Zone, Spot, etc.) from DPS 153
- Trigger source detection (app, button, schedule, robot, remote control)
- Per-device segment storage using HA `Store` (migrated from config entry data)
- Multi-device setup: segment migration safely skipped to avoid cross-device corruption

### Bug Fixes

**Critical**
- Fixed config flow saving entry data without `VACS` key — new installations could fail to load
- Fixed thread-unsafe `asyncio.Event` access from MQTT callbacks — could cause intermittent crashes
- Fixed dock config entities (select, switch, number) mutating coordinator state in-place via shallow copy — could corrupt state if commands failed
- Fixed debounce timers not cancelled on integration unload — could cause errors after removing the integration

**High**
- Fixed suction level entity showing unavailable until DPS 154 received — now also tracks fan speed from DPS 158
- Fixed HTTP API calls crashing when `user_info` is None after failed login
- Fixed login response body read twice on auth failure (aiohttp error)
- Added 30-second timeout to all HTTP API calls — prevents indefinite hangs during cloud outages
- Fixed water injection "emptying" state not setting dock status to "Recycling waste water"
- Fixed room-specific cleaning parameters (`area_clean_param`) not being parsed from DPS 154
- Fixed auto-wash switch getter/setter mismatch (comparing strings vs writing integers)

**Medium**
- Fixed `checkLogin()` always re-authenticating (checked never-set `sid` field instead of `mqtt_credentials`)
- Fixed `disconnect()` crash when event loop reference is None
- Fixed WorkStatus state 15 mapped to "idle" instead of "paused" (inconsistent with task status)
- Fixed `MopIntensitySelectEntity` returning raw unmapped values instead of None
- Fixed duplicate `fan_speed` attribute in vacuum entity's extra state attributes
- Fixed `decode()` crash on empty or truncated protobuf data
- Fixed `encode_varint()` infinite loop on negative input
- Fixed error code parsing crash when protobuf decode fails — falls back gracefully
- Fixed phantom rooms without names showing as blank — now displayed as "Room {id}"
- Fixed room name deduplication for rooms with identical names
- Fixed smart mode parsing when field is missing from protobuf message
- Fixed optimistic state updates not propagating to coordinator listeners
- Fixed race condition in segment initialization during entity setup

**Entity availability**
- Dock switches, selects, and number entities now correctly show as unavailable until dock config is received
- Private key temp files now created with restricted permissions (0o600)

### Code Quality

- Added 49 new tests across 5 new test files and 7 updated test files (124 → 174 total)
- New test coverage for: `utils.py`, `api/http.py`, `api/cloud.py`, `api/client.py`, `number.py`
- Removed ~6,000 lines of duplicate tests across 4 redundant test files
- Removed unused `sleep()`, `set_dry_cfg()`, `sid` field, and dead imports
- Derived list constants from enum dicts to eliminate value duplication
- Added strict no-duplication rules to `CLAUDE.md` for maintainability

### Contributors

- [@pkajaba](https://github.com/pkajaba) — comprehensive cleaning controls and Matter hub integration (PR #99)
- [@m11tch](https://github.com/m11tch) — code review, architecture guidance
- [@jeppesens](https://github.com/jeppesens) — end-to-end testing, review feedback
