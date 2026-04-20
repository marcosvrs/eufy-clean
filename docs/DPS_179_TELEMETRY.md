# DPS 179 — Robot Telemetry (AnalysisResponse)

DPS 179 provides real-time robot telemetry including position tracking, battery analysis, cleaning session records, and go-home results. It fires approximately every **2 seconds** during active operations and every **15-20 seconds** while idle.

> [!NOTE]
> This analysis is based on payloads captured from a T2351 (X10 Pro Omni). All fields described below are fully parsed by the integration.

## Parsed Fields

### Position Tracking (`status`)
| Field | VacuumState | Type | Description |
|-------|------------|------|-------------|
| `status.robot_position_x` | `robot_position_x` | int | X coordinate (device-relative units) |
| `status.robot_position_y` | `robot_position_y` | int | Y coordinate (device-relative units) |
| `status.robotapp_state` | `robotapp_state` | str | Application state string |
| `status.motion_state` | `motion_state` | str | Motion state string |

### Battery Analysis (`statistics.battery_info`)
| Field | VacuumState | Type | Description |
|-------|------------|------|-------------|
| `battery_info.real_level` | `battery_real_level` | int | Actual battery percentage (0-100) |
| `battery_info.show_level` | `battery_show_level` | int | Smoothed display percentage |
| `battery_info.voltage` | `battery_voltage` | int | Battery voltage in mV (~13900-16500) |
| `battery_info.current` | `battery_current` | int | Current draw in mA (negative = discharging) |
| `battery_info.temperature` | `battery_temperature` | float | Battery temperature in °C |
| `battery_info.update_time` | `battery_update_time` | int | Unix timestamp of reading |

**Battery Heartbeat Guard**: The device sends a zeroed `battery_info` heartbeat every ~10 seconds with `real_level=0, voltage=0, current=0`. The integration discards these to prevent battery sensors from flickering 0→real→0→real, which would flood below-threshold automations.

### Cleaning Session Records (`statistics.clean`)
| Field | VacuumState | Type | Description |
|-------|------------|------|-------------|
| `clean.clean_area` | `last_clean_area` | int | Area cleaned (m²) |
| `clean.clean_time` | `last_clean_time` | int | Duration (seconds, excludes pauses/washes) |
| `clean.mode` | `last_clean_mode` | int | 0=AUTO, 1=ROOMS, 2=ZONES, 3=SPOT, 4=FAST_MAP |
| `clean.start_time` | `last_clean_start` | int | Unix timestamp |
| `clean.end_time` | `last_clean_end` | int | Unix timestamp |
| `clean.result` | `last_clean_result` | bool | true=success, false=failure |
| `clean.fail_code` | `last_clean_fail_code` | int | 0=UNKNOWN, 1=ROBOT_FAULT, 2=ROBOT_ALERT, 3=MANUAL_BREAK |
| **Field 14** (firmware extension) | `last_clean_abort_error` | int | Error code that caused the session to abort (e.g., 7033) |

**Field 14**: This is a firmware extension not present in the proto definition. It contains the specific error code that caused a cleaning session to abort. The integration extracts it from protobuf UnknownFields. Observed with value `7033` (STATION EXPLORATION FAILED) during a failed cleaning session.

### Go-Home Records (`statistics.gohome`)
| Field | VacuumState | Type | Description |
|-------|------------|------|-------------|
| `gohome.result` | `last_gohome_result` | bool | true=docked, false=failed |
| `gohome.fail_code` | `last_gohome_fail_code` | int | 0=UNKNOWN, 1=MANUAL_BREAK, 2=NAVIGATE_FAIL, 3=ENTER_HOME_FAIL |
| `gohome.start_time` | `last_gohome_start` | int | Unix timestamp |
| `gohome.end_time` | `last_gohome_end` | int | Unix timestamp |

### Dust Collection (`statistics.dust_collect`)
| Field | VacuumState | Type | Description |
|-------|------------|------|-------------|
| `dust_collect.result` | `dust_collect_result` | bool | true=success |
| `dust_collect.start_time` | `dust_collect_start_time` | int | Unix timestamp |

### Other Tracked Fields
| Field | VacuumState | Description |
|-------|------------|-------------|
| `statistics.battery_curve` | `battery_discharge_curve` | Discharge curve data (logged, not surfaced) |
| `statistics.ctrl_event` | `ctrl_event_type/source/timestamp` | Control events |
| Various status flags | `upgrading`, `mapping_state`, `relocating`, etc. | Device status indicators |

## Observed Battery Death Sequence (T2351)

Captured during a controlled battery drain on 2026-04-20. The robot was stranded off-dock after a failed exploration (error 7033) and drained to 0%:

| Time | DPS 163 (shown) | Real Level | Voltage (mV) | Current (mA) | Temp (°C) |
|------|----------------|-----------|-------------|-------------|----------|
| 09:49 | 7% | 7 | 14,106 | -146 | 19.4 |
| 10:04 | 5% | 6 | 14,085 | -146 | 19.2 |
| 10:38 | 4% | 4 | 14,034 | -148 | 18.9 |
| 10:54 | 3% | 3 | 14,007 | -152 | 18.8 |
| 11:09 | 2% | 2 | 13,982 | -145 | 18.7 |
| 11:24 | 1% | 1 | 13,952 | -146 | 18.6 |
| 11:24 | — | — | — | — | — |

**Final message**: Error `5014` (DOCKING STATION POWER OFF) appeared in DPS 177. The robot's `power` field remained `True` until MQTT connection was lost — no graceful shutdown message.

**Idle drain rate**: ~1% every 15 minutes at room temperature (18-19°C). Current draw: ~145-150 mA.

## Visual Reference

![Cleaning Pattern](./cleaning_pattern.jpg)
*Figure 1: Observed horizontal zigzag pattern in the Eufy Clean app (T2351).*
