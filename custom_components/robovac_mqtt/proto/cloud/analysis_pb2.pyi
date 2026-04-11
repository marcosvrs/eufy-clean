from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class AnalysisRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class AnalysisInternalStatus(_message.Message):
    __slots__ = ("robotapp_state", "motion_state")
    ROBOTAPP_STATE_FIELD_NUMBER: _ClassVar[int]
    MOTION_STATE_FIELD_NUMBER: _ClassVar[int]
    robotapp_state: str
    motion_state: str
    def __init__(self, robotapp_state: _Optional[str] = ..., motion_state: _Optional[str] = ...) -> None: ...

class AnalysisStatistics(_message.Message):
    __slots__ = ("clean", "gohome", "relocate", "collect", "ctrl_event", "distribute_event", "battery_info", "battery_curve")
    class CleanRecord(_message.Message):
        __slots__ = ("clean_id", "result", "fail_code", "mode", "type", "start_time", "end_time", "clean_time", "clean_area", "slam_area", "map_id", "room_count", "roll_brush")
        class FailCode(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
            __slots__ = ()
            UNKNOW: _ClassVar[AnalysisStatistics.CleanRecord.FailCode]
            ROBOT_FAULT: _ClassVar[AnalysisStatistics.CleanRecord.FailCode]
            ROBOT_ALERT: _ClassVar[AnalysisStatistics.CleanRecord.FailCode]
            MANUAL_BREAK: _ClassVar[AnalysisStatistics.CleanRecord.FailCode]
        UNKNOW: AnalysisStatistics.CleanRecord.FailCode
        ROBOT_FAULT: AnalysisStatistics.CleanRecord.FailCode
        ROBOT_ALERT: AnalysisStatistics.CleanRecord.FailCode
        MANUAL_BREAK: AnalysisStatistics.CleanRecord.FailCode
        class Mode(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
            __slots__ = ()
            AUTO_CLEAN: _ClassVar[AnalysisStatistics.CleanRecord.Mode]
            SELECT_ROOMS_CLEAN: _ClassVar[AnalysisStatistics.CleanRecord.Mode]
            SELECT_ZONES_CLEAN: _ClassVar[AnalysisStatistics.CleanRecord.Mode]
            SPOT_CLEAN: _ClassVar[AnalysisStatistics.CleanRecord.Mode]
            FAST_MAPPING: _ClassVar[AnalysisStatistics.CleanRecord.Mode]
        AUTO_CLEAN: AnalysisStatistics.CleanRecord.Mode
        SELECT_ROOMS_CLEAN: AnalysisStatistics.CleanRecord.Mode
        SELECT_ZONES_CLEAN: AnalysisStatistics.CleanRecord.Mode
        SPOT_CLEAN: AnalysisStatistics.CleanRecord.Mode
        FAST_MAPPING: AnalysisStatistics.CleanRecord.Mode
        class Type(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
            __slots__ = ()
            SWEEP_ONLY: _ClassVar[AnalysisStatistics.CleanRecord.Type]
            MOP_ONLY: _ClassVar[AnalysisStatistics.CleanRecord.Type]
            SWEEP_AND_MOP: _ClassVar[AnalysisStatistics.CleanRecord.Type]
        SWEEP_ONLY: AnalysisStatistics.CleanRecord.Type
        MOP_ONLY: AnalysisStatistics.CleanRecord.Type
        SWEEP_AND_MOP: AnalysisStatistics.CleanRecord.Type
        class RollBrush(_message.Message):
            __slots__ = ("protect_count", "stalled_count")
            PROTECT_COUNT_FIELD_NUMBER: _ClassVar[int]
            STALLED_COUNT_FIELD_NUMBER: _ClassVar[int]
            protect_count: int
            stalled_count: int
            def __init__(self, protect_count: _Optional[int] = ..., stalled_count: _Optional[int] = ...) -> None: ...
        CLEAN_ID_FIELD_NUMBER: _ClassVar[int]
        RESULT_FIELD_NUMBER: _ClassVar[int]
        FAIL_CODE_FIELD_NUMBER: _ClassVar[int]
        MODE_FIELD_NUMBER: _ClassVar[int]
        TYPE_FIELD_NUMBER: _ClassVar[int]
        START_TIME_FIELD_NUMBER: _ClassVar[int]
        END_TIME_FIELD_NUMBER: _ClassVar[int]
        CLEAN_TIME_FIELD_NUMBER: _ClassVar[int]
        CLEAN_AREA_FIELD_NUMBER: _ClassVar[int]
        SLAM_AREA_FIELD_NUMBER: _ClassVar[int]
        MAP_ID_FIELD_NUMBER: _ClassVar[int]
        ROOM_COUNT_FIELD_NUMBER: _ClassVar[int]
        ROLL_BRUSH_FIELD_NUMBER: _ClassVar[int]
        clean_id: int
        result: bool
        fail_code: AnalysisStatistics.CleanRecord.FailCode
        mode: AnalysisStatistics.CleanRecord.Mode
        type: AnalysisStatistics.CleanRecord.Type
        start_time: int
        end_time: int
        clean_time: int
        clean_area: int
        slam_area: int
        map_id: int
        room_count: int
        roll_brush: AnalysisStatistics.CleanRecord.RollBrush
        def __init__(self, clean_id: _Optional[int] = ..., result: bool = ..., fail_code: _Optional[_Union[AnalysisStatistics.CleanRecord.FailCode, str]] = ..., mode: _Optional[_Union[AnalysisStatistics.CleanRecord.Mode, str]] = ..., type: _Optional[_Union[AnalysisStatistics.CleanRecord.Type, str]] = ..., start_time: _Optional[int] = ..., end_time: _Optional[int] = ..., clean_time: _Optional[int] = ..., clean_area: _Optional[int] = ..., slam_area: _Optional[int] = ..., map_id: _Optional[int] = ..., room_count: _Optional[int] = ..., roll_brush: _Optional[_Union[AnalysisStatistics.CleanRecord.RollBrush, _Mapping]] = ...) -> None: ...
    class GoHomeRecord(_message.Message):
        __slots__ = ("clean_id", "result", "fail_code", "power_level", "start_time", "end_time")
        class FailCode(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
            __slots__ = ()
            UNKNOW: _ClassVar[AnalysisStatistics.GoHomeRecord.FailCode]
            MANUAL_BREAK: _ClassVar[AnalysisStatistics.GoHomeRecord.FailCode]
            NAVIGATE_FAIL: _ClassVar[AnalysisStatistics.GoHomeRecord.FailCode]
            ENTER_HOME_FAIL: _ClassVar[AnalysisStatistics.GoHomeRecord.FailCode]
        UNKNOW: AnalysisStatistics.GoHomeRecord.FailCode
        MANUAL_BREAK: AnalysisStatistics.GoHomeRecord.FailCode
        NAVIGATE_FAIL: AnalysisStatistics.GoHomeRecord.FailCode
        ENTER_HOME_FAIL: AnalysisStatistics.GoHomeRecord.FailCode
        CLEAN_ID_FIELD_NUMBER: _ClassVar[int]
        RESULT_FIELD_NUMBER: _ClassVar[int]
        FAIL_CODE_FIELD_NUMBER: _ClassVar[int]
        POWER_LEVEL_FIELD_NUMBER: _ClassVar[int]
        START_TIME_FIELD_NUMBER: _ClassVar[int]
        END_TIME_FIELD_NUMBER: _ClassVar[int]
        clean_id: int
        result: bool
        fail_code: AnalysisStatistics.GoHomeRecord.FailCode
        power_level: int
        start_time: int
        end_time: int
        def __init__(self, clean_id: _Optional[int] = ..., result: bool = ..., fail_code: _Optional[_Union[AnalysisStatistics.GoHomeRecord.FailCode, str]] = ..., power_level: _Optional[int] = ..., start_time: _Optional[int] = ..., end_time: _Optional[int] = ...) -> None: ...
    class RelocateRecord(_message.Message):
        __slots__ = ("clean_id", "result", "map_count", "start_time", "end_time")
        CLEAN_ID_FIELD_NUMBER: _ClassVar[int]
        RESULT_FIELD_NUMBER: _ClassVar[int]
        MAP_COUNT_FIELD_NUMBER: _ClassVar[int]
        START_TIME_FIELD_NUMBER: _ClassVar[int]
        END_TIME_FIELD_NUMBER: _ClassVar[int]
        clean_id: int
        result: bool
        map_count: int
        start_time: int
        end_time: int
        def __init__(self, clean_id: _Optional[int] = ..., result: bool = ..., map_count: _Optional[int] = ..., start_time: _Optional[int] = ..., end_time: _Optional[int] = ...) -> None: ...
    class CollectRecord(_message.Message):
        __slots__ = ("clean_id", "result", "start_time")
        CLEAN_ID_FIELD_NUMBER: _ClassVar[int]
        RESULT_FIELD_NUMBER: _ClassVar[int]
        START_TIME_FIELD_NUMBER: _ClassVar[int]
        clean_id: int
        result: bool
        start_time: int
        def __init__(self, clean_id: _Optional[int] = ..., result: bool = ..., start_time: _Optional[int] = ...) -> None: ...
    class ControlEvent(_message.Message):
        __slots__ = ("clean_id", "type", "source", "timestamp")
        class Type(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
            __slots__ = ()
            AUTO_CLEAN: _ClassVar[AnalysisStatistics.ControlEvent.Type]
            SPOT_CLEAN: _ClassVar[AnalysisStatistics.ControlEvent.Type]
            GOHOME: _ClassVar[AnalysisStatistics.ControlEvent.Type]
            CLEAN_PAUSE: _ClassVar[AnalysisStatistics.ControlEvent.Type]
            CLEAN_RESUME: _ClassVar[AnalysisStatistics.ControlEvent.Type]
        AUTO_CLEAN: AnalysisStatistics.ControlEvent.Type
        SPOT_CLEAN: AnalysisStatistics.ControlEvent.Type
        GOHOME: AnalysisStatistics.ControlEvent.Type
        CLEAN_PAUSE: AnalysisStatistics.ControlEvent.Type
        CLEAN_RESUME: AnalysisStatistics.ControlEvent.Type
        class Source(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
            __slots__ = ()
            KEY: _ClassVar[AnalysisStatistics.ControlEvent.Source]
            APP: _ClassVar[AnalysisStatistics.ControlEvent.Source]
            TIMER: _ClassVar[AnalysisStatistics.ControlEvent.Source]
        KEY: AnalysisStatistics.ControlEvent.Source
        APP: AnalysisStatistics.ControlEvent.Source
        TIMER: AnalysisStatistics.ControlEvent.Source
        CLEAN_ID_FIELD_NUMBER: _ClassVar[int]
        TYPE_FIELD_NUMBER: _ClassVar[int]
        SOURCE_FIELD_NUMBER: _ClassVar[int]
        TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
        clean_id: int
        type: AnalysisStatistics.ControlEvent.Type
        source: AnalysisStatistics.ControlEvent.Source
        timestamp: int
        def __init__(self, clean_id: _Optional[int] = ..., type: _Optional[_Union[AnalysisStatistics.ControlEvent.Type, str]] = ..., source: _Optional[_Union[AnalysisStatistics.ControlEvent.Source, str]] = ..., timestamp: _Optional[int] = ...) -> None: ...
    class DistributeEvent(_message.Message):
        __slots__ = ("timestamp", "mode", "result", "software_version", "sn", "mac", "uuid", "country_code", "token")
        class Mode(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
            __slots__ = ()
            AP: _ClassVar[AnalysisStatistics.DistributeEvent.Mode]
            BLE: _ClassVar[AnalysisStatistics.DistributeEvent.Mode]
        AP: AnalysisStatistics.DistributeEvent.Mode
        BLE: AnalysisStatistics.DistributeEvent.Mode
        class Result(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
            __slots__ = ()
            E_OK: _ClassVar[AnalysisStatistics.DistributeEvent.Result]
            E_SRV_ERR: _ClassVar[AnalysisStatistics.DistributeEvent.Result]
            E_AP_NOT_FOUND: _ClassVar[AnalysisStatistics.DistributeEvent.Result]
            E_PASSWD_ERR: _ClassVar[AnalysisStatistics.DistributeEvent.Result]
            E_DHCP_ERR: _ClassVar[AnalysisStatistics.DistributeEvent.Result]
            E_GW_ERR: _ClassVar[AnalysisStatistics.DistributeEvent.Result]
            E_DNS_ERR: _ClassVar[AnalysisStatistics.DistributeEvent.Result]
            E_NET_ERR: _ClassVar[AnalysisStatistics.DistributeEvent.Result]
        E_OK: AnalysisStatistics.DistributeEvent.Result
        E_SRV_ERR: AnalysisStatistics.DistributeEvent.Result
        E_AP_NOT_FOUND: AnalysisStatistics.DistributeEvent.Result
        E_PASSWD_ERR: AnalysisStatistics.DistributeEvent.Result
        E_DHCP_ERR: AnalysisStatistics.DistributeEvent.Result
        E_GW_ERR: AnalysisStatistics.DistributeEvent.Result
        E_DNS_ERR: AnalysisStatistics.DistributeEvent.Result
        E_NET_ERR: AnalysisStatistics.DistributeEvent.Result
        class TimeStamp(_message.Message):
            __slots__ = ("value",)
            VALUE_FIELD_NUMBER: _ClassVar[int]
            value: int
            def __init__(self, value: _Optional[int] = ...) -> None: ...
        TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
        MODE_FIELD_NUMBER: _ClassVar[int]
        RESULT_FIELD_NUMBER: _ClassVar[int]
        SOFTWARE_VERSION_FIELD_NUMBER: _ClassVar[int]
        SN_FIELD_NUMBER: _ClassVar[int]
        MAC_FIELD_NUMBER: _ClassVar[int]
        UUID_FIELD_NUMBER: _ClassVar[int]
        COUNTRY_CODE_FIELD_NUMBER: _ClassVar[int]
        TOKEN_FIELD_NUMBER: _ClassVar[int]
        timestamp: AnalysisStatistics.DistributeEvent.TimeStamp
        mode: AnalysisStatistics.DistributeEvent.Mode
        result: AnalysisStatistics.DistributeEvent.Result
        software_version: str
        sn: str
        mac: str
        uuid: str
        country_code: str
        token: str
        def __init__(self, timestamp: _Optional[_Union[AnalysisStatistics.DistributeEvent.TimeStamp, _Mapping]] = ..., mode: _Optional[_Union[AnalysisStatistics.DistributeEvent.Mode, str]] = ..., result: _Optional[_Union[AnalysisStatistics.DistributeEvent.Result, str]] = ..., software_version: _Optional[str] = ..., sn: _Optional[str] = ..., mac: _Optional[str] = ..., uuid: _Optional[str] = ..., country_code: _Optional[str] = ..., token: _Optional[str] = ...) -> None: ...
    class BatteryInfo(_message.Message):
        __slots__ = ("update_time", "show_level", "real_level", "voltage", "current", "temperature")
        UPDATE_TIME_FIELD_NUMBER: _ClassVar[int]
        SHOW_LEVEL_FIELD_NUMBER: _ClassVar[int]
        REAL_LEVEL_FIELD_NUMBER: _ClassVar[int]
        VOLTAGE_FIELD_NUMBER: _ClassVar[int]
        CURRENT_FIELD_NUMBER: _ClassVar[int]
        TEMPERATURE_FIELD_NUMBER: _ClassVar[int]
        update_time: int
        show_level: int
        real_level: int
        voltage: int
        current: int
        temperature: _containers.RepeatedScalarFieldContainer[int]
        def __init__(self, update_time: _Optional[int] = ..., show_level: _Optional[int] = ..., real_level: _Optional[int] = ..., voltage: _Optional[int] = ..., current: _Optional[int] = ..., temperature: _Optional[_Iterable[int]] = ...) -> None: ...
    class BatteryDischargeCurve(_message.Message):
        __slots__ = ("discharge",)
        class Series(_message.Message):
            __slots__ = ("values",)
            VALUES_FIELD_NUMBER: _ClassVar[int]
            values: _containers.RepeatedScalarFieldContainer[int]
            def __init__(self, values: _Optional[_Iterable[int]] = ...) -> None: ...
        DISCHARGE_FIELD_NUMBER: _ClassVar[int]
        discharge: AnalysisStatistics.BatteryDischargeCurve.Series
        def __init__(self, discharge: _Optional[_Union[AnalysisStatistics.BatteryDischargeCurve.Series, _Mapping]] = ...) -> None: ...
    CLEAN_FIELD_NUMBER: _ClassVar[int]
    GOHOME_FIELD_NUMBER: _ClassVar[int]
    RELOCATE_FIELD_NUMBER: _ClassVar[int]
    COLLECT_FIELD_NUMBER: _ClassVar[int]
    CTRL_EVENT_FIELD_NUMBER: _ClassVar[int]
    DISTRIBUTE_EVENT_FIELD_NUMBER: _ClassVar[int]
    BATTERY_INFO_FIELD_NUMBER: _ClassVar[int]
    BATTERY_CURVE_FIELD_NUMBER: _ClassVar[int]
    clean: AnalysisStatistics.CleanRecord
    gohome: AnalysisStatistics.GoHomeRecord
    relocate: AnalysisStatistics.RelocateRecord
    collect: AnalysisStatistics.CollectRecord
    ctrl_event: AnalysisStatistics.ControlEvent
    distribute_event: AnalysisStatistics.DistributeEvent
    battery_info: AnalysisStatistics.BatteryInfo
    battery_curve: AnalysisStatistics.BatteryDischargeCurve
    def __init__(self, clean: _Optional[_Union[AnalysisStatistics.CleanRecord, _Mapping]] = ..., gohome: _Optional[_Union[AnalysisStatistics.GoHomeRecord, _Mapping]] = ..., relocate: _Optional[_Union[AnalysisStatistics.RelocateRecord, _Mapping]] = ..., collect: _Optional[_Union[AnalysisStatistics.CollectRecord, _Mapping]] = ..., ctrl_event: _Optional[_Union[AnalysisStatistics.ControlEvent, _Mapping]] = ..., distribute_event: _Optional[_Union[AnalysisStatistics.DistributeEvent, _Mapping]] = ..., battery_info: _Optional[_Union[AnalysisStatistics.BatteryInfo, _Mapping]] = ..., battery_curve: _Optional[_Union[AnalysisStatistics.BatteryDischargeCurve, _Mapping]] = ...) -> None: ...

class AnalysisResponse(_message.Message):
    __slots__ = ("internal_status", "statistics")
    INTERNAL_STATUS_FIELD_NUMBER: _ClassVar[int]
    STATISTICS_FIELD_NUMBER: _ClassVar[int]
    internal_status: AnalysisInternalStatus
    statistics: AnalysisStatistics
    def __init__(self, internal_status: _Optional[_Union[AnalysisInternalStatus, _Mapping]] = ..., statistics: _Optional[_Union[AnalysisStatistics, _Mapping]] = ...) -> None: ...
