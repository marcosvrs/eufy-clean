# `vacuum.send_command` Reference

> **Audience**: Power users who need advanced vacuum control or automation beyond what the standard entities provide.

> [!NOTE]
> Most common operations are available directly via entities (switches, selects, buttons) without needing `send_command`. This reference covers commands that either have no entity equivalent or offer additional parameters not exposed by the UI.

## Command Format

All commands use:
```yaml
action: vacuum.send_command
target:
  entity_id: vacuum.robovac
data:
  command: "<command_name>"
  params:
    <param>: <value>
```

---

## Cleaning Commands

| Command | Params | Description |
|---------|--------|-------------|
| `start_auto` | — | Start full-home auto clean |
| `pause` | — | Pause current task |
| `resume` | — | Resume paused task |
| `stop` | — | Stop and stay in place |
| `return_to_base` | — | Return to charging dock |
| `clean_spot` | — | Spot clean at current position |
| `scene_clean` | `scene_id` (int) | Run a cleaning scene. IDs available in scene select entity. |
| `room_clean` | `room_ids` (list), `map_id` (int), `fan_speed` (str), `water_level` (str), `clean_times` (int) | Clean specific rooms. See [Room Cleaning in README](../README.md#cleaning-specific-rooms). |
| `zone_clean` | `zones` (list of `{x, y, w, h}`), `map_id` (int) | Clean rectangular zones by coordinates |
| `spot_clean` | `clean_times` (int, default 1) | Spot clean with repeat count |
| `goto_clean` | `x` (int), `y` (int), `map_id` (int) | Navigate to a specific map coordinate and clean |

### Zone Clean Example
```yaml
action: vacuum.send_command
target:
  entity_id: vacuum.robovac
data:
  command: zone_clean
  params:
    map_id: 4
    zones:
      - { x: 1000, y: 2000, w: 3000, h: 4000 }
      - { x: 5000, y: 6000, w: 2000, h: 2000 }
```

### Go-To Clean Example
```yaml
action: vacuum.send_command
target:
  entity_id: vacuum.robovac
data:
  command: goto_clean
  params:
    map_id: 4
    x: 15000
    y: 25000
```

---

## Per-Room Custom Settings

Override cleaning parameters per room in a single session. This replicates the Eufy App's per-room configuration feature.

```yaml
action: vacuum.send_command
target:
  entity_id: vacuum.robovac
data:
  command: set_room_custom
  params:
    map_id: 4
    room_config:
      - id: 3
        fan_speed: "Turbo"
        clean_mode: "vacuum_mop"
        water_level: "high"
        clean_times: 2
      - id: 4
        fan_speed: "Quiet"
        clean_mode: "vacuum"
        clean_intensity: "quick"
```

### Valid Values

| Parameter | Options |
|-----------|---------|
| `fan_speed` | `Quiet`, `Standard`, `Turbo`, `Max`, `Boost_IQ` |
| `clean_mode` | `vacuum`, `mop`, `vacuum_mop`, `mopping_after_sweeping` |
| `water_level` | `low`, `middle` / `medium`, `high` |
| `clean_intensity` | `quick`, `normal` / `standard`, `narrow` / `deep` |
| `clean_times` | `1`–`3` |
| `edge_mopping` | `true` / `false` |

---

## Cleaning Parameter Commands

These change the **default** cleaning parameters for subsequent runs. Most users should use the corresponding select entities instead.

| Command | Params | Entity Alternative |
|---------|--------|--------------------|
| `set_fan_speed` | `fan_speed`: `Quiet` / `Standard` / `Turbo` / `Max` / `Boost_IQ` | `vacuum.set_fan_speed` or suction select |
| `set_cleaning_mode` | `clean_mode`: `Vacuum` / `Mop` / `Vacuum and mop` / `Mopping after sweeping` | Cleaning mode select |
| `set_water_level` | `water_level`: `Low` / `Medium` / `High` | Water level select |
| `set_cleaning_intensity` | `cleaning_intensity`: `Normal` / `Narrow` / `Quick` | Cleaning intensity select |
| `set_carpet_strategy` | `carpet_strategy`: `Auto Raise` / `Avoid` / `Ignore` | Carpet strategy select |
| `set_corner_cleaning` | `corner_cleaning`: `Normal` / `Deep` | Corner cleaning select |

---

## Dock Control Commands

Most dock operations are available as button entities. These commands are for automation use:

| Command | Params | Entity Alternative |
|---------|--------|--------------------|
| `go_dry` | — | Dry mop button |
| `stop_dry` | — | Stop dry mop button |
| `go_selfcleaning` | — | Wash mop button |
| `collect_dust` | — | Empty dust bin button |

---

## Device Settings Commands

| Command | Params | Entity Alternative |
|---------|--------|--------------------|
| `set_volume` | `volume` (int, 0–100) | Volume number entity |
| `set_smart_mode` | `active` (bool) | Smart mode switch |
| `set_boost_iq` | `active` (bool) | Boost IQ switch |
| `set_child_lock` | `active` (bool) | Child lock switch |
| `set_do_not_disturb` | `active` (bool), `begin_hour`, `begin_minute`, `end_hour`, `end_minute` | DND switch + time entities |

---

## Schedule Management Commands

Schedule enable/disable is available as switch entities (`switch.<device>_schedule_<id>`). These commands are for advanced schedule manipulation:

| Command | Params | Description |
|---------|--------|-------------|
| `timer_open` | `timer_id` (int) | Enable a schedule |
| `timer_close` | `timer_id` (int) | Disable a schedule |
| `timer_inquiry` | — | Request schedule list from device |
| `timer_delete` | `timer_id` (int) | Delete a schedule |
| `timer_add` | `timer_info` (dict) | Create a new schedule |
| `timer_modify` | `timer_info` (dict) | Modify an existing schedule |

---

## Cruise / Patrol Commands

| Command | Params | Description |
|---------|--------|-------------|
| `start_global_cruise` | `map_id` (int) | Patrol entire map without cleaning |
| `start_point_cruise` | `x` (int), `y` (int), `map_id` (int) | Patrol to a specific point |
| `start_zones_cruise` | `points` (list of `{x, y}`), `map_id` (int) | Patrol through waypoints |
| `stop_smart_follow` | — | Stop smart follow / pet tracking mode |

---

## Mapping Commands

| Command | Params | Description |
|---------|--------|-------------|
| `mapping_then_clean` | — | Create a new map, then auto-clean |

---

## Remote Control Commands

| Command | Params | Description |
|---------|--------|-------------|
| `start_rc` | — | Enter remote control mode |
| `stop_rc` | — | Exit remote control mode |

> [!NOTE]
> Remote control directional movement (Forward, Back, Left, Right, Brake) is sent via DPS 155 and is not currently exposed. Use the Eufy app for joystick control.

---

## Media Commands

| Command | Params | Description |
|---------|--------|-------------|
| `media_capture` | `seq` (int, default 1) | Capture a photo from the onboard camera |
| `media_record` | `start` (bool), `seq` (int) | Start/stop video recording |
| `media_set_resolution` | `resolution`: `720p` / `1080p` | Set recording resolution |

---

## Accessory Reset

| Command | Params | Description |
|---------|--------|-------------|
| `reset_accessory` | `reset_type` (int) | Reset a consumable counter. See table below. |

| `reset_type` | Accessory |
|---|---|
| 1 | Filter |
| 2 | Main (rolling) brush |
| 3 | Side brush |
| 4 | Sensors |
| 5 | Cleaning tray (scrape) |
| 6 | Mop pad |

> [!TIP]
> Reset buttons are available as button entities — you don't need `send_command` for accessory resets.

---

## Generic / Raw Command

For developers testing new DPS commands:

```yaml
action: vacuum.send_command
target:
  entity_id: vacuum.robovac
data:
  command: generic
  params:
    dp_id: "158"
    value: "3"
```

This sends a raw DPS value without any protobuf encoding. Use with caution — invalid values may be silently ignored or cause unexpected device behavior.
