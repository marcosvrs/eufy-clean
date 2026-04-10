from proto.cloud import common_pb2 as _common_pb2
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class Fan(_message.Message):
    __slots__ = ("suction",)
    class Suction(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        QUIET: _ClassVar[Fan.Suction]
        STANDARD: _ClassVar[Fan.Suction]
        TURBO: _ClassVar[Fan.Suction]
        MAX: _ClassVar[Fan.Suction]
        MAX_PLUS: _ClassVar[Fan.Suction]
    QUIET: Fan.Suction
    STANDARD: Fan.Suction
    TURBO: Fan.Suction
    MAX: Fan.Suction
    MAX_PLUS: Fan.Suction
    SUCTION_FIELD_NUMBER: _ClassVar[int]
    suction: Fan.Suction
    def __init__(self, suction: _Optional[_Union[Fan.Suction, str]] = ...) -> None: ...

class MopMode(_message.Message):
    __slots__ = ("level", "corner_clean")
    class Level(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        LOW: _ClassVar[MopMode.Level]
        MIDDLE: _ClassVar[MopMode.Level]
        HIGH: _ClassVar[MopMode.Level]
    LOW: MopMode.Level
    MIDDLE: MopMode.Level
    HIGH: MopMode.Level
    class CornerClean(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        NORMAL: _ClassVar[MopMode.CornerClean]
        DEEP: _ClassVar[MopMode.CornerClean]
    NORMAL: MopMode.CornerClean
    DEEP: MopMode.CornerClean
    LEVEL_FIELD_NUMBER: _ClassVar[int]
    CORNER_CLEAN_FIELD_NUMBER: _ClassVar[int]
    level: MopMode.Level
    corner_clean: MopMode.CornerClean
    def __init__(self, level: _Optional[_Union[MopMode.Level, str]] = ..., corner_clean: _Optional[_Union[MopMode.CornerClean, str]] = ...) -> None: ...

class CleanCarpet(_message.Message):
    __slots__ = ("strategy", "unknown_2")
    class Strategy(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        AUTO_RAISE: _ClassVar[CleanCarpet.Strategy]
        AVOID: _ClassVar[CleanCarpet.Strategy]
        IGNORE: _ClassVar[CleanCarpet.Strategy]
    AUTO_RAISE: CleanCarpet.Strategy
    AVOID: CleanCarpet.Strategy
    IGNORE: CleanCarpet.Strategy
    STRATEGY_FIELD_NUMBER: _ClassVar[int]
    UNKNOWN_2_FIELD_NUMBER: _ClassVar[int]
    strategy: CleanCarpet.Strategy
    unknown_2: bytes
    def __init__(self, strategy: _Optional[_Union[CleanCarpet.Strategy, str]] = ..., unknown_2: _Optional[bytes] = ...) -> None: ...

class CleanType(_message.Message):
    __slots__ = ("value",)
    class Value(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        SWEEP_ONLY: _ClassVar[CleanType.Value]
        MOP_ONLY: _ClassVar[CleanType.Value]
        SWEEP_AND_MOP: _ClassVar[CleanType.Value]
        SWEEP_THEN_MOP: _ClassVar[CleanType.Value]
    SWEEP_ONLY: CleanType.Value
    MOP_ONLY: CleanType.Value
    SWEEP_AND_MOP: CleanType.Value
    SWEEP_THEN_MOP: CleanType.Value
    VALUE_FIELD_NUMBER: _ClassVar[int]
    value: CleanType.Value
    def __init__(self, value: _Optional[_Union[CleanType.Value, str]] = ...) -> None: ...

class CleanExtent(_message.Message):
    __slots__ = ("value",)
    class Value(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        NORMAL: _ClassVar[CleanExtent.Value]
        NARROW: _ClassVar[CleanExtent.Value]
        QUICK: _ClassVar[CleanExtent.Value]
    NORMAL: CleanExtent.Value
    NARROW: CleanExtent.Value
    QUICK: CleanExtent.Value
    VALUE_FIELD_NUMBER: _ClassVar[int]
    value: CleanExtent.Value
    def __init__(self, value: _Optional[_Union[CleanExtent.Value, str]] = ...) -> None: ...

class CleanTimes(_message.Message):
    __slots__ = ("auto_clean", "select_rooms", "spot_clean")
    AUTO_CLEAN_FIELD_NUMBER: _ClassVar[int]
    SELECT_ROOMS_FIELD_NUMBER: _ClassVar[int]
    SPOT_CLEAN_FIELD_NUMBER: _ClassVar[int]
    auto_clean: int
    select_rooms: int
    spot_clean: int
    def __init__(self, auto_clean: _Optional[int] = ..., select_rooms: _Optional[int] = ..., spot_clean: _Optional[int] = ...) -> None: ...

class CleanParam(_message.Message):
    __slots__ = ("clean_type", "clean_carpet", "clean_extent", "mop_mode", "smart_mode_sw", "fan", "clean_times")
    CLEAN_TYPE_FIELD_NUMBER: _ClassVar[int]
    CLEAN_CARPET_FIELD_NUMBER: _ClassVar[int]
    CLEAN_EXTENT_FIELD_NUMBER: _ClassVar[int]
    MOP_MODE_FIELD_NUMBER: _ClassVar[int]
    SMART_MODE_SW_FIELD_NUMBER: _ClassVar[int]
    FAN_FIELD_NUMBER: _ClassVar[int]
    CLEAN_TIMES_FIELD_NUMBER: _ClassVar[int]
    clean_type: CleanType
    clean_carpet: CleanCarpet
    clean_extent: CleanExtent
    mop_mode: MopMode
    smart_mode_sw: _common_pb2.Switch
    fan: Fan
    clean_times: int
    def __init__(self, clean_type: _Optional[_Union[CleanType, _Mapping]] = ..., clean_carpet: _Optional[_Union[CleanCarpet, _Mapping]] = ..., clean_extent: _Optional[_Union[CleanExtent, _Mapping]] = ..., mop_mode: _Optional[_Union[MopMode, _Mapping]] = ..., smart_mode_sw: _Optional[_Union[_common_pb2.Switch, _Mapping]] = ..., fan: _Optional[_Union[Fan, _Mapping]] = ..., clean_times: _Optional[int] = ...) -> None: ...

class CleanParamRequest(_message.Message):
    __slots__ = ("clean_param", "area_clean_param")
    CLEAN_PARAM_FIELD_NUMBER: _ClassVar[int]
    AREA_CLEAN_PARAM_FIELD_NUMBER: _ClassVar[int]
    clean_param: CleanParam
    area_clean_param: CleanParam
    def __init__(self, clean_param: _Optional[_Union[CleanParam, _Mapping]] = ..., area_clean_param: _Optional[_Union[CleanParam, _Mapping]] = ...) -> None: ...

class CleanParamResponse(_message.Message):
    __slots__ = ("clean_param", "clean_times", "area_clean_param", "running_clean_param")
    CLEAN_PARAM_FIELD_NUMBER: _ClassVar[int]
    CLEAN_TIMES_FIELD_NUMBER: _ClassVar[int]
    AREA_CLEAN_PARAM_FIELD_NUMBER: _ClassVar[int]
    RUNNING_CLEAN_PARAM_FIELD_NUMBER: _ClassVar[int]
    clean_param: CleanParam
    clean_times: CleanTimes
    area_clean_param: CleanParam
    running_clean_param: CleanParam
    def __init__(self, clean_param: _Optional[_Union[CleanParam, _Mapping]] = ..., clean_times: _Optional[_Union[CleanTimes, _Mapping]] = ..., area_clean_param: _Optional[_Union[CleanParam, _Mapping]] = ..., running_clean_param: _Optional[_Union[CleanParam, _Mapping]] = ...) -> None: ...
