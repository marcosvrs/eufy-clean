from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class CleaningPreferences:
    """Represent cleaning preferences (suction, water, etc)."""

    fan_speed: str = "Standard"
    water_level: int = 1
    auto_empty_mode: bool = False
    auto_mop_wash_mode: bool = False


@dataclass
class AccessoryState:
    """Represent accessory usage/lifespan state."""

    filter_usage: int = 0
    main_brush_usage: int = 0
    side_brush_usage: int = 0
    sensor_usage: int = 0
    scrape_usage: int = 0
    mop_usage: int = 0
    dustbag_usage: int = 0
    dirty_watertank_usage: int = 0
    dirty_waterfilter_usage: int = 0
    accessory_12_usage: int = 0
    accessory_13_usage: int = 0
    accessory_15_usage: int = 0
    accessory_19_usage: int = 0


@dataclass
class VacuumState:
    """Represent the complete state of a Eufy vacuum."""

    # Basic
    activity: str = "idle"  # cleaning, docked, error, etc.
    battery_level: int = 0
    fan_speed: str = "Standard"

    # Error state
    error_code: int = 0
    error_message: str = ""
    error_codes_all: list[int] = field(default_factory=list)
    error_messages_all: list[str] = field(default_factory=list)
    charging: bool = False
    charging_state: str = ""

    # Cleaning Stats
    cleaning_time: int = 0  # seconds
    cleaning_area: int = 0  # m2
    total_cleaning_time: int = 0
    total_cleaning_area: int = 0
    total_cleaning_count: int = 0
    user_total_cleaning_time: int = 0
    user_total_cleaning_area: int = 0
    user_total_cleaning_count: int = 0

    # Advanced Status
    task_status: str = "idle"
    find_robot: bool = False

    # Map
    map_id: int = 0
    map_url: str | None = None
    rooms: list[dict[str, Any]] = field(default_factory=list)
    scenes: list[dict[str, Any]] = field(default_factory=list)
    schedules: list[dict[str, Any]] = field(default_factory=list)

    # Detailed Status
    status_code: int = 0  # Raw status value if needed
    dock_status: str | None = None  # Text description (debounced in coordinator)
    water_tank_clear_adding: bool = False
    water_tank_waste_recycling: bool = False
    station_clean_water: int = 0  # Percentage?
    station_waste_water: int = 0
    station_clean_level: int = 0
    dock_auto_cfg: dict[str, Any] = field(default_factory=dict)
    go_wash_state: str = ""
    go_wash_mode: str = ""
    dock_connected: bool = False
    trigger_source: str = "unknown"
    work_mode: str = "unknown"
    current_scene_id: int = 0
    current_scene_name: str | None = None

    # Active cleaning targets (from DPS 152 echo)
    active_room_ids: list[int] = field(default_factory=list)
    active_room_names: str = ""  # Comma-separated resolved names
    active_zone_count: int = 0

    # Accessories
    accessories: AccessoryState = field(default_factory=AccessoryState)
    consumable_last_time: int = 0

    # Preferences
    preferences: CleaningPreferences = field(default_factory=CleaningPreferences)
    cleaning_mode: str = "Vacuum"  # Matter-compatible cleaning mode preference
    mop_water_level: str = "Medium"  # Global mop water level from DPS 154

    # Additional DPS 154 fields for enhanced functionality
    cleaning_intensity: str = "Normal"  # Clean extent from DPS 154
    carpet_strategy: str = "Auto Raise"  # Clean carpet strategy from DPS 154
    corner_cleaning: str = "Normal"  # Mop corner cleaning from DPS 154
    smart_mode: bool = False  # Smart mode switch from DPS 154
    clean_times: int = 1

    # Plain-value DPS fields (not protobuf-wrapped)
    boost_iq: bool = False  # DPS 159: auto-boost suction on carpet
    volume: int = 50  # DPS 161: voice volume 0-100

    # Device settings (from DPS 176 UnisettingResponse)
    wifi_signal: float = -100.0  # AP signal strength in dBm (converted from 0-100%)
    child_lock: bool = False  # Children lock switch

    # UnisettingResponse switch fields (from DPS 176)
    ai_see: bool = False
    pet_mode_sw: bool = False
    poop_avoidance_sw: bool = False
    live_photo_sw: bool = False
    deep_mop_corner_sw: bool = False
    smart_follow_sw: bool = False
    cruise_continue_sw: bool = False
    multi_map_sw: bool = False
    suggest_restricted_zone_sw: bool = False
    water_level_sw: bool = False
    dust_full_remind: int = 0

    # UniState sub-fields (from DPS 176 unistate)
    mop_state: bool = False
    mop_holder_state_l: bool = False
    mop_holder_state_r: bool = False
    map_valid: bool = False
    live_map_state_bits: int = 0
    clean_strategy_version: int = 0
    custom_clean_mode: bool = False

    # WiFi data (from DPS 176 wifi_data)
    wifi_ap_ssid: str = ""
    wifi_frequency: int = 0
    wifi_connection_result: int = 0
    wifi_connection_timestamp: int = 0
    dnd_enabled: bool = False  # Do Not Disturb switch
    dnd_start_hour: int = 22  # Do Not Disturb start hour
    dnd_start_minute: int = 0  # Do Not Disturb start minute
    dnd_end_hour: int = 8  # Do Not Disturb end hour
    dnd_end_minute: int = 0  # Do Not Disturb end minute

    # Device network info (from DPS 169, DeviceInfo proto)
    device_mac: str = ""
    wifi_ssid: str = ""
    wifi_ip: str = ""
    firmware_version: str = ""
    hardware_version: int = 0
    product_name: str = ""
    ota_channel: str = ""
    video_sn: str = ""
    station_firmware: str = ""
    station_hardware: int = 0

    # Robot telemetry (from DPS 179, no known proto definition)
    robot_position_x: int = 0  # Raw map X coordinate (firmware-internal grid)
    robot_position_y: int = 0  # Raw map Y coordinate (firmware-internal grid)

    # Toast notifications (DPS 178)
    notification_codes: list[int] = field(default_factory=list)
    notification_message: str = ""
    notification_time: int = 0

    # Media manager (DPS 174)
    media_recording: bool = False
    media_storage_state: str = "Normal"
    media_total_space: int = 0
    media_photo_space: int = 0
    media_video_space: int = 0
    media_recording_resolution: str = "720p"
    media_last_capture_path: str = ""
    media_last_capture_id: str = ""

    # Analysis diagnostics (from DPS 179, AnalysisResponse proto)
    robotapp_state: str = ""       # Internal robot app state string
    motion_state: str = ""         # Internal motion state string
    battery_real_level: int = 0    # True battery percentage (0-100)
    battery_show_level: int = 0
    battery_update_time: int = 0
    battery_voltage: int = 0       # Battery voltage in mV
    battery_current: int = 0       # Battery current in mA (signed)
    battery_temperature: float = 0.0  # Battery temperature in °C (from millidegree units)

    last_clean_area: int = 0
    last_clean_time: int = 0
    last_clean_mode: int = 0
    last_clean_start: int = 0
    last_clean_end: int = 0
    last_gohome_result: bool = False
    last_gohome_fail_code: int = 0
    last_gohome_start: int = 0
    last_gohome_end: int = 0
    dust_collect_result: bool = False
    dust_collect_start_time: int = 0
    ctrl_event_type: int = 0
    ctrl_event_source: int = 0
    ctrl_event_timestamp: int = 0

    # WorkStatus extended fields (from DPS 153)
    upgrading: bool = False                # Firmware update in progress
    mapping_state: int = 0                 # Mapping run state (0=idle, 1=doing, 2=paused)
    mapping_mode: int = 0                  # Mapping mode (0=mapping only, 1=map+clean)
    relocating: bool = False               # Robot finding its position
    roller_brush_cleaning: bool = False    # Dock cleaning roller brush
    breakpoint_available: bool = False     # Resume-from-breakpoint available
    station_work_status: int = 0           # Dock's active operation (from WorkStatus)
    cruise_state: int = 0                  # Cruise mode run state
    cruise_mode: int = 0                   # Cruise mode type
    smart_follow_state: int = 0            # Smart follow state
    smart_follow_mode: int = 0             # Smart follow mode
    smart_follow_elapsed: int = 0          # Smart follow elapsed time
    smart_follow_area: int = 0             # Smart follow area

    # Raw data for fallback/diagnostics
    raw_dps: dict[str, Any] = field(default_factory=dict)
    dynamic_values: dict[str, Any] = field(default_factory=dict)

    # Track which optional fields have ever been received from the device
    # Used by sensors to determine availability (e.g., water level on C20)
    received_fields: set[str] = field(default_factory=set)


@dataclass
class CleaningSession:
    """Record of a completed or in-progress cleaning session."""
    start_time: str = ""
    end_time: str | None = None
    duration_seconds: int = 0
    area_m2: int = 0
    trigger_source: str = "unknown"
    rooms: list[str] = field(default_factory=list)
    scene_name: str | None = None
    fan_speed: str = "Standard"
    work_mode: str = "unknown"
    dock_visits: int = 0
    error_message: str = ""
    completed: bool = False
