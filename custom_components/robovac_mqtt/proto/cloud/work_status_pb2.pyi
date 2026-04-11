from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class WorkStatus(_message.Message):
    __slots__ = ("mode", "state", "charging", "upgrading", "mapping", "cleaning", "go_wash", "go_home", "cruisiing", "relocating", "breakpoint", "roller_brush_cleaning", "smart_follow", "station", "unknown_15", "current_scene", "trigger")
    class State(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        STANDBY: _ClassVar[WorkStatus.State]
        SLEEP: _ClassVar[WorkStatus.State]
        FAULT: _ClassVar[WorkStatus.State]
        CHARGING: _ClassVar[WorkStatus.State]
        FAST_MAPPING: _ClassVar[WorkStatus.State]
        CLEANING: _ClassVar[WorkStatus.State]
        REMOTE_CTRL: _ClassVar[WorkStatus.State]
        GO_HOME: _ClassVar[WorkStatus.State]
        CRUISIING: _ClassVar[WorkStatus.State]
    STANDBY: WorkStatus.State
    SLEEP: WorkStatus.State
    FAULT: WorkStatus.State
    CHARGING: WorkStatus.State
    FAST_MAPPING: WorkStatus.State
    CLEANING: WorkStatus.State
    REMOTE_CTRL: WorkStatus.State
    GO_HOME: WorkStatus.State
    CRUISIING: WorkStatus.State
    class Mode(_message.Message):
        __slots__ = ("value",)
        class Value(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
            __slots__ = ()
            AUTO: _ClassVar[WorkStatus.Mode.Value]
            SELECT_ROOM: _ClassVar[WorkStatus.Mode.Value]
            SELECT_ZONE: _ClassVar[WorkStatus.Mode.Value]
            SPOT: _ClassVar[WorkStatus.Mode.Value]
            FAST_MAPPING: _ClassVar[WorkStatus.Mode.Value]
            GLOBAL_CRUISE: _ClassVar[WorkStatus.Mode.Value]
            ZONES_CRUISE: _ClassVar[WorkStatus.Mode.Value]
            POINT_CRUISE: _ClassVar[WorkStatus.Mode.Value]
            SCENE: _ClassVar[WorkStatus.Mode.Value]
            SMART_FOLLOW: _ClassVar[WorkStatus.Mode.Value]
        AUTO: WorkStatus.Mode.Value
        SELECT_ROOM: WorkStatus.Mode.Value
        SELECT_ZONE: WorkStatus.Mode.Value
        SPOT: WorkStatus.Mode.Value
        FAST_MAPPING: WorkStatus.Mode.Value
        GLOBAL_CRUISE: WorkStatus.Mode.Value
        ZONES_CRUISE: WorkStatus.Mode.Value
        POINT_CRUISE: WorkStatus.Mode.Value
        SCENE: WorkStatus.Mode.Value
        SMART_FOLLOW: WorkStatus.Mode.Value
        VALUE_FIELD_NUMBER: _ClassVar[int]
        value: WorkStatus.Mode.Value
        def __init__(self, value: _Optional[_Union[WorkStatus.Mode.Value, str]] = ...) -> None: ...
    class Charging(_message.Message):
        __slots__ = ("state", "unknown_3")
        class State(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
            __slots__ = ()
            DOING: _ClassVar[WorkStatus.Charging.State]
            DONE: _ClassVar[WorkStatus.Charging.State]
            ABNORMAL: _ClassVar[WorkStatus.Charging.State]
        DOING: WorkStatus.Charging.State
        DONE: WorkStatus.Charging.State
        ABNORMAL: WorkStatus.Charging.State
        STATE_FIELD_NUMBER: _ClassVar[int]
        UNKNOWN_3_FIELD_NUMBER: _ClassVar[int]
        state: WorkStatus.Charging.State
        unknown_3: bytes
        def __init__(self, state: _Optional[_Union[WorkStatus.Charging.State, str]] = ..., unknown_3: _Optional[bytes] = ...) -> None: ...
    class Upgrading(_message.Message):
        __slots__ = ("state",)
        class State(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
            __slots__ = ()
            DOING: _ClassVar[WorkStatus.Upgrading.State]
            DONE: _ClassVar[WorkStatus.Upgrading.State]
        DOING: WorkStatus.Upgrading.State
        DONE: WorkStatus.Upgrading.State
        STATE_FIELD_NUMBER: _ClassVar[int]
        state: WorkStatus.Upgrading.State
        def __init__(self, state: _Optional[_Union[WorkStatus.Upgrading.State, str]] = ...) -> None: ...
    class Mapping(_message.Message):
        __slots__ = ("state", "mode")
        class RunState(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
            __slots__ = ()
            DOING: _ClassVar[WorkStatus.Mapping.RunState]
            PAUSED: _ClassVar[WorkStatus.Mapping.RunState]
        DOING: WorkStatus.Mapping.RunState
        PAUSED: WorkStatus.Mapping.RunState
        class Mode(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
            __slots__ = ()
            MAPPING: _ClassVar[WorkStatus.Mapping.Mode]
            RELOCATING: _ClassVar[WorkStatus.Mapping.Mode]
        MAPPING: WorkStatus.Mapping.Mode
        RELOCATING: WorkStatus.Mapping.Mode
        STATE_FIELD_NUMBER: _ClassVar[int]
        MODE_FIELD_NUMBER: _ClassVar[int]
        state: WorkStatus.Mapping.RunState
        mode: WorkStatus.Mapping.Mode
        def __init__(self, state: _Optional[_Union[WorkStatus.Mapping.RunState, str]] = ..., mode: _Optional[_Union[WorkStatus.Mapping.Mode, str]] = ...) -> None: ...
    class Cleaning(_message.Message):
        __slots__ = ("state", "mode", "scheduled_task")
        class RunState(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
            __slots__ = ()
            DOING: _ClassVar[WorkStatus.Cleaning.RunState]
            PAUSED: _ClassVar[WorkStatus.Cleaning.RunState]
        DOING: WorkStatus.Cleaning.RunState
        PAUSED: WorkStatus.Cleaning.RunState
        class Mode(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
            __slots__ = ()
            CLEANING: _ClassVar[WorkStatus.Cleaning.Mode]
            RELOCATING: _ClassVar[WorkStatus.Cleaning.Mode]
            GOTO_POS: _ClassVar[WorkStatus.Cleaning.Mode]
            POOP_CLEANING: _ClassVar[WorkStatus.Cleaning.Mode]
        CLEANING: WorkStatus.Cleaning.Mode
        RELOCATING: WorkStatus.Cleaning.Mode
        GOTO_POS: WorkStatus.Cleaning.Mode
        POOP_CLEANING: WorkStatus.Cleaning.Mode
        STATE_FIELD_NUMBER: _ClassVar[int]
        MODE_FIELD_NUMBER: _ClassVar[int]
        SCHEDULED_TASK_FIELD_NUMBER: _ClassVar[int]
        state: WorkStatus.Cleaning.RunState
        mode: WorkStatus.Cleaning.Mode
        scheduled_task: bool
        def __init__(self, state: _Optional[_Union[WorkStatus.Cleaning.RunState, str]] = ..., mode: _Optional[_Union[WorkStatus.Cleaning.Mode, str]] = ..., scheduled_task: bool = ...) -> None: ...
    class GoWash(_message.Message):
        __slots__ = ("state", "mode")
        class RunState(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
            __slots__ = ()
            DOING: _ClassVar[WorkStatus.GoWash.RunState]
            PAUSED: _ClassVar[WorkStatus.GoWash.RunState]
        DOING: WorkStatus.GoWash.RunState
        PAUSED: WorkStatus.GoWash.RunState
        class Mode(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
            __slots__ = ()
            NAVIGATION: _ClassVar[WorkStatus.GoWash.Mode]
            WASHING: _ClassVar[WorkStatus.GoWash.Mode]
            DRYING: _ClassVar[WorkStatus.GoWash.Mode]
        NAVIGATION: WorkStatus.GoWash.Mode
        WASHING: WorkStatus.GoWash.Mode
        DRYING: WorkStatus.GoWash.Mode
        STATE_FIELD_NUMBER: _ClassVar[int]
        MODE_FIELD_NUMBER: _ClassVar[int]
        state: WorkStatus.GoWash.RunState
        mode: WorkStatus.GoWash.Mode
        def __init__(self, state: _Optional[_Union[WorkStatus.GoWash.RunState, str]] = ..., mode: _Optional[_Union[WorkStatus.GoWash.Mode, str]] = ...) -> None: ...
    class GoHome(_message.Message):
        __slots__ = ("state", "mode")
        class RunState(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
            __slots__ = ()
            DOING: _ClassVar[WorkStatus.GoHome.RunState]
            PAUSED: _ClassVar[WorkStatus.GoHome.RunState]
        DOING: WorkStatus.GoHome.RunState
        PAUSED: WorkStatus.GoHome.RunState
        class Mode(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
            __slots__ = ()
            COMPLETE_TASK: _ClassVar[WorkStatus.GoHome.Mode]
            COLLECT_DUST: _ClassVar[WorkStatus.GoHome.Mode]
            OTHRERS: _ClassVar[WorkStatus.GoHome.Mode]
        COMPLETE_TASK: WorkStatus.GoHome.Mode
        COLLECT_DUST: WorkStatus.GoHome.Mode
        OTHRERS: WorkStatus.GoHome.Mode
        STATE_FIELD_NUMBER: _ClassVar[int]
        MODE_FIELD_NUMBER: _ClassVar[int]
        state: WorkStatus.GoHome.RunState
        mode: WorkStatus.GoHome.Mode
        def __init__(self, state: _Optional[_Union[WorkStatus.GoHome.RunState, str]] = ..., mode: _Optional[_Union[WorkStatus.GoHome.Mode, str]] = ...) -> None: ...
    class Cruisiing(_message.Message):
        __slots__ = ("state", "mode")
        class RunState(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
            __slots__ = ()
            DOING: _ClassVar[WorkStatus.Cruisiing.RunState]
            PAUSED: _ClassVar[WorkStatus.Cruisiing.RunState]
        DOING: WorkStatus.Cruisiing.RunState
        PAUSED: WorkStatus.Cruisiing.RunState
        class Mode(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
            __slots__ = ()
            RELOCATING: _ClassVar[WorkStatus.Cruisiing.Mode]
            CRUISIING: _ClassVar[WorkStatus.Cruisiing.Mode]
        RELOCATING: WorkStatus.Cruisiing.Mode
        CRUISIING: WorkStatus.Cruisiing.Mode
        STATE_FIELD_NUMBER: _ClassVar[int]
        MODE_FIELD_NUMBER: _ClassVar[int]
        state: WorkStatus.Cruisiing.RunState
        mode: WorkStatus.Cruisiing.Mode
        def __init__(self, state: _Optional[_Union[WorkStatus.Cruisiing.RunState, str]] = ..., mode: _Optional[_Union[WorkStatus.Cruisiing.Mode, str]] = ...) -> None: ...
    class Relocating(_message.Message):
        __slots__ = ("state",)
        class State(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
            __slots__ = ()
            DOING: _ClassVar[WorkStatus.Relocating.State]
        DOING: WorkStatus.Relocating.State
        STATE_FIELD_NUMBER: _ClassVar[int]
        state: WorkStatus.Relocating.State
        def __init__(self, state: _Optional[_Union[WorkStatus.Relocating.State, str]] = ...) -> None: ...
    class Breakpoint(_message.Message):
        __slots__ = ("state",)
        class State(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
            __slots__ = ()
            DOING: _ClassVar[WorkStatus.Breakpoint.State]
        DOING: WorkStatus.Breakpoint.State
        STATE_FIELD_NUMBER: _ClassVar[int]
        state: WorkStatus.Breakpoint.State
        def __init__(self, state: _Optional[_Union[WorkStatus.Breakpoint.State, str]] = ...) -> None: ...
    class RollerBrushCleaning(_message.Message):
        __slots__ = ("state",)
        class State(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
            __slots__ = ()
            DOING: _ClassVar[WorkStatus.RollerBrushCleaning.State]
        DOING: WorkStatus.RollerBrushCleaning.State
        STATE_FIELD_NUMBER: _ClassVar[int]
        state: WorkStatus.RollerBrushCleaning.State
        def __init__(self, state: _Optional[_Union[WorkStatus.RollerBrushCleaning.State, str]] = ...) -> None: ...
    class SmartFollow(_message.Message):
        __slots__ = ("state", "mode", "elapsed_time", "area")
        class State(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
            __slots__ = ()
            DOING: _ClassVar[WorkStatus.SmartFollow.State]
        DOING: WorkStatus.SmartFollow.State
        class Mode(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
            __slots__ = ()
            FOLLOWING: _ClassVar[WorkStatus.SmartFollow.Mode]
            SEARCHING: _ClassVar[WorkStatus.SmartFollow.Mode]
        FOLLOWING: WorkStatus.SmartFollow.Mode
        SEARCHING: WorkStatus.SmartFollow.Mode
        STATE_FIELD_NUMBER: _ClassVar[int]
        MODE_FIELD_NUMBER: _ClassVar[int]
        ELAPSED_TIME_FIELD_NUMBER: _ClassVar[int]
        AREA_FIELD_NUMBER: _ClassVar[int]
        state: WorkStatus.SmartFollow.State
        mode: WorkStatus.SmartFollow.Mode
        elapsed_time: int
        area: int
        def __init__(self, state: _Optional[_Union[WorkStatus.SmartFollow.State, str]] = ..., mode: _Optional[_Union[WorkStatus.SmartFollow.Mode, str]] = ..., elapsed_time: _Optional[int] = ..., area: _Optional[int] = ...) -> None: ...
    class Station(_message.Message):
        __slots__ = ("water_injection_system", "dust_collection_system", "washing_drying_system", "water_tank_state")
        class WaterInjectionSystem(_message.Message):
            __slots__ = ("state",)
            class State(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
                __slots__ = ()
                ADDING: _ClassVar[WorkStatus.Station.WaterInjectionSystem.State]
                EMPTYING: _ClassVar[WorkStatus.Station.WaterInjectionSystem.State]
            ADDING: WorkStatus.Station.WaterInjectionSystem.State
            EMPTYING: WorkStatus.Station.WaterInjectionSystem.State
            STATE_FIELD_NUMBER: _ClassVar[int]
            state: WorkStatus.Station.WaterInjectionSystem.State
            def __init__(self, state: _Optional[_Union[WorkStatus.Station.WaterInjectionSystem.State, str]] = ...) -> None: ...
        class DustCollectionSystem(_message.Message):
            __slots__ = ("state",)
            class State(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
                __slots__ = ()
                EMPTYING: _ClassVar[WorkStatus.Station.DustCollectionSystem.State]
            EMPTYING: WorkStatus.Station.DustCollectionSystem.State
            STATE_FIELD_NUMBER: _ClassVar[int]
            state: WorkStatus.Station.DustCollectionSystem.State
            def __init__(self, state: _Optional[_Union[WorkStatus.Station.DustCollectionSystem.State, str]] = ...) -> None: ...
        class WashingDryingSystem(_message.Message):
            __slots__ = ("state",)
            class State(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
                __slots__ = ()
                WASHING: _ClassVar[WorkStatus.Station.WashingDryingSystem.State]
                DRYING: _ClassVar[WorkStatus.Station.WashingDryingSystem.State]
            WASHING: WorkStatus.Station.WashingDryingSystem.State
            DRYING: WorkStatus.Station.WashingDryingSystem.State
            STATE_FIELD_NUMBER: _ClassVar[int]
            state: WorkStatus.Station.WashingDryingSystem.State
            def __init__(self, state: _Optional[_Union[WorkStatus.Station.WashingDryingSystem.State, str]] = ...) -> None: ...
        class WaterTankState(_message.Message):
            __slots__ = ("clear_water_adding", "waste_water_recycling")
            CLEAR_WATER_ADDING_FIELD_NUMBER: _ClassVar[int]
            WASTE_WATER_RECYCLING_FIELD_NUMBER: _ClassVar[int]
            clear_water_adding: bool
            waste_water_recycling: bool
            def __init__(self, clear_water_adding: bool = ..., waste_water_recycling: bool = ...) -> None: ...
        WATER_INJECTION_SYSTEM_FIELD_NUMBER: _ClassVar[int]
        DUST_COLLECTION_SYSTEM_FIELD_NUMBER: _ClassVar[int]
        WASHING_DRYING_SYSTEM_FIELD_NUMBER: _ClassVar[int]
        WATER_TANK_STATE_FIELD_NUMBER: _ClassVar[int]
        water_injection_system: WorkStatus.Station.WaterInjectionSystem
        dust_collection_system: WorkStatus.Station.DustCollectionSystem
        washing_drying_system: WorkStatus.Station.WashingDryingSystem
        water_tank_state: WorkStatus.Station.WaterTankState
        def __init__(self, water_injection_system: _Optional[_Union[WorkStatus.Station.WaterInjectionSystem, _Mapping]] = ..., dust_collection_system: _Optional[_Union[WorkStatus.Station.DustCollectionSystem, _Mapping]] = ..., washing_drying_system: _Optional[_Union[WorkStatus.Station.WashingDryingSystem, _Mapping]] = ..., water_tank_state: _Optional[_Union[WorkStatus.Station.WaterTankState, _Mapping]] = ...) -> None: ...
    class Scene(_message.Message):
        __slots__ = ("id", "elapsed_time", "estimate_time", "name", "task_mode")
        class TaskMode(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
            __slots__ = ()
            AUTO: _ClassVar[WorkStatus.Scene.TaskMode]
            SELECT_ROOM: _ClassVar[WorkStatus.Scene.TaskMode]
            SELECT_ZONE: _ClassVar[WorkStatus.Scene.TaskMode]
        AUTO: WorkStatus.Scene.TaskMode
        SELECT_ROOM: WorkStatus.Scene.TaskMode
        SELECT_ZONE: WorkStatus.Scene.TaskMode
        ID_FIELD_NUMBER: _ClassVar[int]
        ELAPSED_TIME_FIELD_NUMBER: _ClassVar[int]
        ESTIMATE_TIME_FIELD_NUMBER: _ClassVar[int]
        NAME_FIELD_NUMBER: _ClassVar[int]
        TASK_MODE_FIELD_NUMBER: _ClassVar[int]
        id: int
        elapsed_time: int
        estimate_time: int
        name: str
        task_mode: WorkStatus.Scene.TaskMode
        def __init__(self, id: _Optional[int] = ..., elapsed_time: _Optional[int] = ..., estimate_time: _Optional[int] = ..., name: _Optional[str] = ..., task_mode: _Optional[_Union[WorkStatus.Scene.TaskMode, str]] = ...) -> None: ...
    class Trigger(_message.Message):
        __slots__ = ("source",)
        class Source(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
            __slots__ = ()
            UNKNOWN: _ClassVar[WorkStatus.Trigger.Source]
            APP: _ClassVar[WorkStatus.Trigger.Source]
            KEY: _ClassVar[WorkStatus.Trigger.Source]
            TIMING: _ClassVar[WorkStatus.Trigger.Source]
            ROBOT: _ClassVar[WorkStatus.Trigger.Source]
            REMOTE_CTRL: _ClassVar[WorkStatus.Trigger.Source]
        UNKNOWN: WorkStatus.Trigger.Source
        APP: WorkStatus.Trigger.Source
        KEY: WorkStatus.Trigger.Source
        TIMING: WorkStatus.Trigger.Source
        ROBOT: WorkStatus.Trigger.Source
        REMOTE_CTRL: WorkStatus.Trigger.Source
        SOURCE_FIELD_NUMBER: _ClassVar[int]
        source: WorkStatus.Trigger.Source
        def __init__(self, source: _Optional[_Union[WorkStatus.Trigger.Source, str]] = ...) -> None: ...
    MODE_FIELD_NUMBER: _ClassVar[int]
    STATE_FIELD_NUMBER: _ClassVar[int]
    CHARGING_FIELD_NUMBER: _ClassVar[int]
    UPGRADING_FIELD_NUMBER: _ClassVar[int]
    MAPPING_FIELD_NUMBER: _ClassVar[int]
    CLEANING_FIELD_NUMBER: _ClassVar[int]
    GO_WASH_FIELD_NUMBER: _ClassVar[int]
    GO_HOME_FIELD_NUMBER: _ClassVar[int]
    CRUISIING_FIELD_NUMBER: _ClassVar[int]
    RELOCATING_FIELD_NUMBER: _ClassVar[int]
    BREAKPOINT_FIELD_NUMBER: _ClassVar[int]
    ROLLER_BRUSH_CLEANING_FIELD_NUMBER: _ClassVar[int]
    SMART_FOLLOW_FIELD_NUMBER: _ClassVar[int]
    STATION_FIELD_NUMBER: _ClassVar[int]
    UNKNOWN_15_FIELD_NUMBER: _ClassVar[int]
    CURRENT_SCENE_FIELD_NUMBER: _ClassVar[int]
    TRIGGER_FIELD_NUMBER: _ClassVar[int]
    mode: WorkStatus.Mode
    state: WorkStatus.State
    charging: WorkStatus.Charging
    upgrading: WorkStatus.Upgrading
    mapping: WorkStatus.Mapping
    cleaning: WorkStatus.Cleaning
    go_wash: WorkStatus.GoWash
    go_home: WorkStatus.GoHome
    cruisiing: WorkStatus.Cruisiing
    relocating: WorkStatus.Relocating
    breakpoint: WorkStatus.Breakpoint
    roller_brush_cleaning: WorkStatus.RollerBrushCleaning
    smart_follow: WorkStatus.SmartFollow
    station: WorkStatus.Station
    unknown_15: bytes
    current_scene: WorkStatus.Scene
    trigger: WorkStatus.Trigger
    def __init__(self, mode: _Optional[_Union[WorkStatus.Mode, _Mapping]] = ..., state: _Optional[_Union[WorkStatus.State, str]] = ..., charging: _Optional[_Union[WorkStatus.Charging, _Mapping]] = ..., upgrading: _Optional[_Union[WorkStatus.Upgrading, _Mapping]] = ..., mapping: _Optional[_Union[WorkStatus.Mapping, _Mapping]] = ..., cleaning: _Optional[_Union[WorkStatus.Cleaning, _Mapping]] = ..., go_wash: _Optional[_Union[WorkStatus.GoWash, _Mapping]] = ..., go_home: _Optional[_Union[WorkStatus.GoHome, _Mapping]] = ..., cruisiing: _Optional[_Union[WorkStatus.Cruisiing, _Mapping]] = ..., relocating: _Optional[_Union[WorkStatus.Relocating, _Mapping]] = ..., breakpoint: _Optional[_Union[WorkStatus.Breakpoint, _Mapping]] = ..., roller_brush_cleaning: _Optional[_Union[WorkStatus.RollerBrushCleaning, _Mapping]] = ..., smart_follow: _Optional[_Union[WorkStatus.SmartFollow, _Mapping]] = ..., station: _Optional[_Union[WorkStatus.Station, _Mapping]] = ..., unknown_15: _Optional[bytes] = ..., current_scene: _Optional[_Union[WorkStatus.Scene, _Mapping]] = ..., trigger: _Optional[_Union[WorkStatus.Trigger, _Mapping]] = ...) -> None: ...
