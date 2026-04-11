from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class Global(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    NONE: _ClassVar[Global]
    PROTO_VERSION: _ClassVar[Global]
NONE: Global
PROTO_VERSION: Global

class ProtoInfo(_message.Message):
    __slots__ = ("global_verison", "collect_dust", "map_format", "continue_clean", "cut_hair", "timing", "capability_7", "capability_8", "capability_10")
    class CollectDustOptionBit(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        COLLECT_DUST_APP_START: _ClassVar[ProtoInfo.CollectDustOptionBit]
    COLLECT_DUST_APP_START: ProtoInfo.CollectDustOptionBit
    class MapFormatOptionBit(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        MAP_FORMAT_ANGLE: _ClassVar[ProtoInfo.MapFormatOptionBit]
        MAP_FORMAT_RESERVE_MAP: _ClassVar[ProtoInfo.MapFormatOptionBit]
        MAP_FORMAT_DEFAULT_NAME: _ClassVar[ProtoInfo.MapFormatOptionBit]
    MAP_FORMAT_ANGLE: ProtoInfo.MapFormatOptionBit
    MAP_FORMAT_RESERVE_MAP: ProtoInfo.MapFormatOptionBit
    MAP_FORMAT_DEFAULT_NAME: ProtoInfo.MapFormatOptionBit
    class ContinueCleanOptionBit(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        SMART_CONTINUE_CLEAN: _ClassVar[ProtoInfo.ContinueCleanOptionBit]
    SMART_CONTINUE_CLEAN: ProtoInfo.ContinueCleanOptionBit
    class TimingOptionBit(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        SCHEDULE_ROOMS_CLEAN_CUSTOM: _ClassVar[ProtoInfo.TimingOptionBit]
        SCHEDULE_SCENE_CLEAN: _ClassVar[ProtoInfo.TimingOptionBit]
    SCHEDULE_ROOMS_CLEAN_CUSTOM: ProtoInfo.TimingOptionBit
    SCHEDULE_SCENE_CLEAN: ProtoInfo.TimingOptionBit
    class Module(_message.Message):
        __slots__ = ("version", "options")
        VERSION_FIELD_NUMBER: _ClassVar[int]
        OPTIONS_FIELD_NUMBER: _ClassVar[int]
        version: int
        options: int
        def __init__(self, version: _Optional[int] = ..., options: _Optional[int] = ...) -> None: ...
    GLOBAL_VERISON_FIELD_NUMBER: _ClassVar[int]
    COLLECT_DUST_FIELD_NUMBER: _ClassVar[int]
    MAP_FORMAT_FIELD_NUMBER: _ClassVar[int]
    CONTINUE_CLEAN_FIELD_NUMBER: _ClassVar[int]
    CUT_HAIR_FIELD_NUMBER: _ClassVar[int]
    TIMING_FIELD_NUMBER: _ClassVar[int]
    CAPABILITY_7_FIELD_NUMBER: _ClassVar[int]
    CAPABILITY_8_FIELD_NUMBER: _ClassVar[int]
    CAPABILITY_10_FIELD_NUMBER: _ClassVar[int]
    global_verison: int
    collect_dust: ProtoInfo.Module
    map_format: ProtoInfo.Module
    continue_clean: ProtoInfo.Module
    cut_hair: ProtoInfo.Module
    timing: ProtoInfo.Module
    capability_7: ProtoInfo.Module
    capability_8: ProtoInfo.Module
    capability_10: ProtoInfo.Module
    def __init__(self, global_verison: _Optional[int] = ..., collect_dust: _Optional[_Union[ProtoInfo.Module, _Mapping]] = ..., map_format: _Optional[_Union[ProtoInfo.Module, _Mapping]] = ..., continue_clean: _Optional[_Union[ProtoInfo.Module, _Mapping]] = ..., cut_hair: _Optional[_Union[ProtoInfo.Module, _Mapping]] = ..., timing: _Optional[_Union[ProtoInfo.Module, _Mapping]] = ..., capability_7: _Optional[_Union[ProtoInfo.Module, _Mapping]] = ..., capability_8: _Optional[_Union[ProtoInfo.Module, _Mapping]] = ..., capability_10: _Optional[_Union[ProtoInfo.Module, _Mapping]] = ...) -> None: ...

class AppFunction(_message.Message):
    __slots__ = ("multi_maps", "optimization")
    class MultiMapsFunctionBit(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        REMIND_MAP_SAVE: _ClassVar[AppFunction.MultiMapsFunctionBit]
    REMIND_MAP_SAVE: AppFunction.MultiMapsFunctionBit
    class OptimizationFunctionBit(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        PATH_HIDE_TYPE: _ClassVar[AppFunction.OptimizationFunctionBit]
    PATH_HIDE_TYPE: AppFunction.OptimizationFunctionBit
    class Module(_message.Message):
        __slots__ = ("version", "options")
        VERSION_FIELD_NUMBER: _ClassVar[int]
        OPTIONS_FIELD_NUMBER: _ClassVar[int]
        version: int
        options: int
        def __init__(self, version: _Optional[int] = ..., options: _Optional[int] = ...) -> None: ...
    MULTI_MAPS_FIELD_NUMBER: _ClassVar[int]
    OPTIMIZATION_FIELD_NUMBER: _ClassVar[int]
    multi_maps: AppFunction.Module
    optimization: AppFunction.Module
    def __init__(self, multi_maps: _Optional[_Union[AppFunction.Module, _Mapping]] = ..., optimization: _Optional[_Union[AppFunction.Module, _Mapping]] = ...) -> None: ...
