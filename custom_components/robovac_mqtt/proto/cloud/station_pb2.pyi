from proto.cloud import common_pb2 as _common_pb2
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class Duration(_message.Message):
    __slots__ = ("level",)
    class Level(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        SHORT: _ClassVar[Duration.Level]
        MEDIUM: _ClassVar[Duration.Level]
        LONG: _ClassVar[Duration.Level]
    SHORT: Duration.Level
    MEDIUM: Duration.Level
    LONG: Duration.Level
    LEVEL_FIELD_NUMBER: _ClassVar[int]
    level: Duration.Level
    def __init__(self, level: _Optional[_Union[Duration.Level, str]] = ...) -> None: ...

class CollectDustCfg(_message.Message):
    __slots__ = ("cfg",)
    class Cfg(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        CLOSE: _ClassVar[CollectDustCfg.Cfg]
        ONCE: _ClassVar[CollectDustCfg.Cfg]
        TWICE: _ClassVar[CollectDustCfg.Cfg]
    CLOSE: CollectDustCfg.Cfg
    ONCE: CollectDustCfg.Cfg
    TWICE: CollectDustCfg.Cfg
    CFG_FIELD_NUMBER: _ClassVar[int]
    cfg: CollectDustCfg.Cfg
    def __init__(self, cfg: _Optional[_Union[CollectDustCfg.Cfg, str]] = ...) -> None: ...

class CollectDustCfgV2(_message.Message):
    __slots__ = ("sw", "mode", "auto_start")
    class Mode(_message.Message):
        __slots__ = ("value", "task", "time")
        class Value(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
            __slots__ = ()
            BY_TASK: _ClassVar[CollectDustCfgV2.Mode.Value]
            BY_TIME: _ClassVar[CollectDustCfgV2.Mode.Value]
            SMART: _ClassVar[CollectDustCfgV2.Mode.Value]
        BY_TASK: CollectDustCfgV2.Mode.Value
        BY_TIME: CollectDustCfgV2.Mode.Value
        SMART: CollectDustCfgV2.Mode.Value
        VALUE_FIELD_NUMBER: _ClassVar[int]
        TASK_FIELD_NUMBER: _ClassVar[int]
        TIME_FIELD_NUMBER: _ClassVar[int]
        value: CollectDustCfgV2.Mode.Value
        task: int
        time: int
        def __init__(self, value: _Optional[_Union[CollectDustCfgV2.Mode.Value, str]] = ..., task: _Optional[int] = ..., time: _Optional[int] = ...) -> None: ...
    SW_FIELD_NUMBER: _ClassVar[int]
    MODE_FIELD_NUMBER: _ClassVar[int]
    AUTO_START_FIELD_NUMBER: _ClassVar[int]
    sw: _common_pb2.Switch
    mode: CollectDustCfgV2.Mode
    auto_start: _common_pb2.Switch
    def __init__(self, sw: _Optional[_Union[_common_pb2.Switch, _Mapping]] = ..., mode: _Optional[_Union[CollectDustCfgV2.Mode, _Mapping]] = ..., auto_start: _Optional[_Union[_common_pb2.Switch, _Mapping]] = ...) -> None: ...

class DryCfg(_message.Message):
    __slots__ = ("cfg", "duration")
    class Cfg(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        CLOSE: _ClassVar[DryCfg.Cfg]
        STANDARD: _ClassVar[DryCfg.Cfg]
        QUICK: _ClassVar[DryCfg.Cfg]
    CLOSE: DryCfg.Cfg
    STANDARD: DryCfg.Cfg
    QUICK: DryCfg.Cfg
    CFG_FIELD_NUMBER: _ClassVar[int]
    DURATION_FIELD_NUMBER: _ClassVar[int]
    cfg: DryCfg.Cfg
    duration: Duration
    def __init__(self, cfg: _Optional[_Union[DryCfg.Cfg, str]] = ..., duration: _Optional[_Union[Duration, _Mapping]] = ...) -> None: ...

class WashCfg(_message.Message):
    __slots__ = ("wash_freq", "wash_duration", "cfg")
    class Cfg(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        CLOSE: _ClassVar[WashCfg.Cfg]
        STANDARD: _ClassVar[WashCfg.Cfg]
    CLOSE: WashCfg.Cfg
    STANDARD: WashCfg.Cfg
    class BackwashFreq(_message.Message):
        __slots__ = ("mode", "duration", "time_or_area")
        class Mode(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
            __slots__ = ()
            ByPartition: _ClassVar[WashCfg.BackwashFreq.Mode]
            ByTime: _ClassVar[WashCfg.BackwashFreq.Mode]
            ByArea: _ClassVar[WashCfg.BackwashFreq.Mode]
        ByPartition: WashCfg.BackwashFreq.Mode
        ByTime: WashCfg.BackwashFreq.Mode
        ByArea: WashCfg.BackwashFreq.Mode
        MODE_FIELD_NUMBER: _ClassVar[int]
        DURATION_FIELD_NUMBER: _ClassVar[int]
        TIME_OR_AREA_FIELD_NUMBER: _ClassVar[int]
        mode: WashCfg.BackwashFreq.Mode
        duration: Duration
        time_or_area: _common_pb2.Numerical
        def __init__(self, mode: _Optional[_Union[WashCfg.BackwashFreq.Mode, str]] = ..., duration: _Optional[_Union[Duration, _Mapping]] = ..., time_or_area: _Optional[_Union[_common_pb2.Numerical, _Mapping]] = ...) -> None: ...
    WASH_FREQ_FIELD_NUMBER: _ClassVar[int]
    WASH_DURATION_FIELD_NUMBER: _ClassVar[int]
    CFG_FIELD_NUMBER: _ClassVar[int]
    wash_freq: WashCfg.BackwashFreq
    wash_duration: Duration
    cfg: WashCfg.Cfg
    def __init__(self, wash_freq: _Optional[_Union[WashCfg.BackwashFreq, _Mapping]] = ..., wash_duration: _Optional[_Union[Duration, _Mapping]] = ..., cfg: _Optional[_Union[WashCfg.Cfg, str]] = ...) -> None: ...

class CutHairCfg(_message.Message):
    __slots__ = ("sw",)
    SW_FIELD_NUMBER: _ClassVar[int]
    sw: _common_pb2.Switch
    def __init__(self, sw: _Optional[_Union[_common_pb2.Switch, _Mapping]] = ...) -> None: ...

class SelfPurifyingCfg(_message.Message):
    __slots__ = ("type", "standard_cfg", "strong_cfg", "energy_saving_cfg", "custom_cfg")
    class Type(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        STANDARD: _ClassVar[SelfPurifyingCfg.Type]
        STRONG: _ClassVar[SelfPurifyingCfg.Type]
        ENERGY_SAVING: _ClassVar[SelfPurifyingCfg.Type]
        CUSTOM: _ClassVar[SelfPurifyingCfg.Type]
    STANDARD: SelfPurifyingCfg.Type
    STRONG: SelfPurifyingCfg.Type
    ENERGY_SAVING: SelfPurifyingCfg.Type
    CUSTOM: SelfPurifyingCfg.Type
    class Config(_message.Message):
        __slots__ = ("frequency", "intensity")
        class Frequency(_message.Message):
            __slots__ = ("mode", "task", "time")
            class Mode(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
                __slots__ = ()
                BY_TASK: _ClassVar[SelfPurifyingCfg.Config.Frequency.Mode]
                BY_TIME: _ClassVar[SelfPurifyingCfg.Config.Frequency.Mode]
            BY_TASK: SelfPurifyingCfg.Config.Frequency.Mode
            BY_TIME: SelfPurifyingCfg.Config.Frequency.Mode
            MODE_FIELD_NUMBER: _ClassVar[int]
            TASK_FIELD_NUMBER: _ClassVar[int]
            TIME_FIELD_NUMBER: _ClassVar[int]
            mode: SelfPurifyingCfg.Config.Frequency.Mode
            task: int
            time: int
            def __init__(self, mode: _Optional[_Union[SelfPurifyingCfg.Config.Frequency.Mode, str]] = ..., task: _Optional[int] = ..., time: _Optional[int] = ...) -> None: ...
        class Intensity(_message.Message):
            __slots__ = ("level",)
            class Level(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
                __slots__ = ()
                LOW: _ClassVar[SelfPurifyingCfg.Config.Intensity.Level]
                MEDIUM: _ClassVar[SelfPurifyingCfg.Config.Intensity.Level]
                HIGH: _ClassVar[SelfPurifyingCfg.Config.Intensity.Level]
            LOW: SelfPurifyingCfg.Config.Intensity.Level
            MEDIUM: SelfPurifyingCfg.Config.Intensity.Level
            HIGH: SelfPurifyingCfg.Config.Intensity.Level
            LEVEL_FIELD_NUMBER: _ClassVar[int]
            level: SelfPurifyingCfg.Config.Intensity.Level
            def __init__(self, level: _Optional[_Union[SelfPurifyingCfg.Config.Intensity.Level, str]] = ...) -> None: ...
        FREQUENCY_FIELD_NUMBER: _ClassVar[int]
        INTENSITY_FIELD_NUMBER: _ClassVar[int]
        frequency: SelfPurifyingCfg.Config.Frequency
        intensity: SelfPurifyingCfg.Config.Intensity
        def __init__(self, frequency: _Optional[_Union[SelfPurifyingCfg.Config.Frequency, _Mapping]] = ..., intensity: _Optional[_Union[SelfPurifyingCfg.Config.Intensity, _Mapping]] = ...) -> None: ...
    TYPE_FIELD_NUMBER: _ClassVar[int]
    STANDARD_CFG_FIELD_NUMBER: _ClassVar[int]
    STRONG_CFG_FIELD_NUMBER: _ClassVar[int]
    ENERGY_SAVING_CFG_FIELD_NUMBER: _ClassVar[int]
    CUSTOM_CFG_FIELD_NUMBER: _ClassVar[int]
    type: SelfPurifyingCfg.Type
    standard_cfg: SelfPurifyingCfg.Config
    strong_cfg: SelfPurifyingCfg.Config
    energy_saving_cfg: SelfPurifyingCfg.Config
    custom_cfg: SelfPurifyingCfg.Config
    def __init__(self, type: _Optional[_Union[SelfPurifyingCfg.Type, str]] = ..., standard_cfg: _Optional[_Union[SelfPurifyingCfg.Config, _Mapping]] = ..., strong_cfg: _Optional[_Union[SelfPurifyingCfg.Config, _Mapping]] = ..., energy_saving_cfg: _Optional[_Union[SelfPurifyingCfg.Config, _Mapping]] = ..., custom_cfg: _Optional[_Union[SelfPurifyingCfg.Config, _Mapping]] = ...) -> None: ...

class AutoActionCfg(_message.Message):
    __slots__ = ("wash", "dry", "collectdust", "detergent", "make_disinfectant", "collectdust_v2", "cut_hair", "self_purifying")
    WASH_FIELD_NUMBER: _ClassVar[int]
    DRY_FIELD_NUMBER: _ClassVar[int]
    COLLECTDUST_FIELD_NUMBER: _ClassVar[int]
    DETERGENT_FIELD_NUMBER: _ClassVar[int]
    MAKE_DISINFECTANT_FIELD_NUMBER: _ClassVar[int]
    COLLECTDUST_V2_FIELD_NUMBER: _ClassVar[int]
    CUT_HAIR_FIELD_NUMBER: _ClassVar[int]
    SELF_PURIFYING_FIELD_NUMBER: _ClassVar[int]
    wash: WashCfg
    dry: DryCfg
    collectdust: CollectDustCfg
    detergent: bool
    make_disinfectant: bool
    collectdust_v2: CollectDustCfgV2
    cut_hair: CutHairCfg
    self_purifying: SelfPurifyingCfg
    def __init__(self, wash: _Optional[_Union[WashCfg, _Mapping]] = ..., dry: _Optional[_Union[DryCfg, _Mapping]] = ..., collectdust: _Optional[_Union[CollectDustCfg, _Mapping]] = ..., detergent: bool = ..., make_disinfectant: bool = ..., collectdust_v2: _Optional[_Union[CollectDustCfgV2, _Mapping]] = ..., cut_hair: _Optional[_Union[CutHairCfg, _Mapping]] = ..., self_purifying: _Optional[_Union[SelfPurifyingCfg, _Mapping]] = ...) -> None: ...

class ManualActionCmd(_message.Message):
    __slots__ = ("self_maintain", "go_dry", "go_collect_dust", "go_selfcleaning", "go_remove_scale", "go_cut_hair", "go_selfpurifying")
    SELF_MAINTAIN_FIELD_NUMBER: _ClassVar[int]
    GO_DRY_FIELD_NUMBER: _ClassVar[int]
    GO_COLLECT_DUST_FIELD_NUMBER: _ClassVar[int]
    GO_SELFCLEANING_FIELD_NUMBER: _ClassVar[int]
    GO_REMOVE_SCALE_FIELD_NUMBER: _ClassVar[int]
    GO_CUT_HAIR_FIELD_NUMBER: _ClassVar[int]
    GO_SELFPURIFYING_FIELD_NUMBER: _ClassVar[int]
    self_maintain: bool
    go_dry: bool
    go_collect_dust: bool
    go_selfcleaning: bool
    go_remove_scale: bool
    go_cut_hair: bool
    go_selfpurifying: bool
    def __init__(self, self_maintain: bool = ..., go_dry: bool = ..., go_collect_dust: bool = ..., go_selfcleaning: bool = ..., go_remove_scale: bool = ..., go_cut_hair: bool = ..., go_selfpurifying: bool = ...) -> None: ...

class StationRequest(_message.Message):
    __slots__ = ("auto_cfg", "manual_cmd")
    AUTO_CFG_FIELD_NUMBER: _ClassVar[int]
    MANUAL_CMD_FIELD_NUMBER: _ClassVar[int]
    auto_cfg: AutoActionCfg
    manual_cmd: ManualActionCmd
    def __init__(self, auto_cfg: _Optional[_Union[AutoActionCfg, _Mapping]] = ..., manual_cmd: _Optional[_Union[ManualActionCmd, _Mapping]] = ...) -> None: ...

class StationResponse(_message.Message):
    __slots__ = ("auto_cfg_status", "status", "clean_level", "dirty_level", "clean_water")
    class WaterLevel(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        EMPTY: _ClassVar[StationResponse.WaterLevel]
        VERY_LOW: _ClassVar[StationResponse.WaterLevel]
        LOW: _ClassVar[StationResponse.WaterLevel]
        MEDIUM: _ClassVar[StationResponse.WaterLevel]
        HIGH: _ClassVar[StationResponse.WaterLevel]
    EMPTY: StationResponse.WaterLevel
    VERY_LOW: StationResponse.WaterLevel
    LOW: StationResponse.WaterLevel
    MEDIUM: StationResponse.WaterLevel
    HIGH: StationResponse.WaterLevel
    class StationStatus(_message.Message):
        __slots__ = ("connected", "state", "collecting_dust", "clear_water_adding", "waste_water_recycling", "disinfectant_making", "cutting_hair")
        class State(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
            __slots__ = ()
            IDLE: _ClassVar[StationResponse.StationStatus.State]
            WASHING: _ClassVar[StationResponse.StationStatus.State]
            DRYING: _ClassVar[StationResponse.StationStatus.State]
            REMOVING_SCALE: _ClassVar[StationResponse.StationStatus.State]
        IDLE: StationResponse.StationStatus.State
        WASHING: StationResponse.StationStatus.State
        DRYING: StationResponse.StationStatus.State
        REMOVING_SCALE: StationResponse.StationStatus.State
        CONNECTED_FIELD_NUMBER: _ClassVar[int]
        STATE_FIELD_NUMBER: _ClassVar[int]
        COLLECTING_DUST_FIELD_NUMBER: _ClassVar[int]
        CLEAR_WATER_ADDING_FIELD_NUMBER: _ClassVar[int]
        WASTE_WATER_RECYCLING_FIELD_NUMBER: _ClassVar[int]
        DISINFECTANT_MAKING_FIELD_NUMBER: _ClassVar[int]
        CUTTING_HAIR_FIELD_NUMBER: _ClassVar[int]
        connected: bool
        state: StationResponse.StationStatus.State
        collecting_dust: bool
        clear_water_adding: bool
        waste_water_recycling: bool
        disinfectant_making: bool
        cutting_hair: bool
        def __init__(self, connected: bool = ..., state: _Optional[_Union[StationResponse.StationStatus.State, str]] = ..., collecting_dust: bool = ..., clear_water_adding: bool = ..., waste_water_recycling: bool = ..., disinfectant_making: bool = ..., cutting_hair: bool = ...) -> None: ...
    AUTO_CFG_STATUS_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    CLEAN_LEVEL_FIELD_NUMBER: _ClassVar[int]
    DIRTY_LEVEL_FIELD_NUMBER: _ClassVar[int]
    CLEAN_WATER_FIELD_NUMBER: _ClassVar[int]
    auto_cfg_status: AutoActionCfg
    status: StationResponse.StationStatus
    clean_level: StationResponse.WaterLevel
    dirty_level: StationResponse.WaterLevel
    clean_water: _common_pb2.Numerical
    def __init__(self, auto_cfg_status: _Optional[_Union[AutoActionCfg, _Mapping]] = ..., status: _Optional[_Union[StationResponse.StationStatus, _Mapping]] = ..., clean_level: _Optional[_Union[StationResponse.WaterLevel, str]] = ..., dirty_level: _Optional[_Union[StationResponse.WaterLevel, str]] = ..., clean_water: _Optional[_Union[_common_pb2.Numerical, _Mapping]] = ...) -> None: ...
