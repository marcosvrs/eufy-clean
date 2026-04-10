from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class ConsumableRequest(_message.Message):
    __slots__ = ("reset_types",)
    class Type(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        SIDE_BRUSH: _ClassVar[ConsumableRequest.Type]
        ROLLING_BRUSH: _ClassVar[ConsumableRequest.Type]
        FILTER_MESH: _ClassVar[ConsumableRequest.Type]
        SCRAPE: _ClassVar[ConsumableRequest.Type]
        SENSOR: _ClassVar[ConsumableRequest.Type]
        MOP: _ClassVar[ConsumableRequest.Type]
        DUSTBAG: _ClassVar[ConsumableRequest.Type]
        DIRTY_WATERTANK: _ClassVar[ConsumableRequest.Type]
        DIRTY_WATERFILTER: _ClassVar[ConsumableRequest.Type]
    SIDE_BRUSH: ConsumableRequest.Type
    ROLLING_BRUSH: ConsumableRequest.Type
    FILTER_MESH: ConsumableRequest.Type
    SCRAPE: ConsumableRequest.Type
    SENSOR: ConsumableRequest.Type
    MOP: ConsumableRequest.Type
    DUSTBAG: ConsumableRequest.Type
    DIRTY_WATERTANK: ConsumableRequest.Type
    DIRTY_WATERFILTER: ConsumableRequest.Type
    RESET_TYPES_FIELD_NUMBER: _ClassVar[int]
    reset_types: _containers.RepeatedScalarFieldContainer[ConsumableRequest.Type]
    def __init__(self, reset_types: _Optional[_Iterable[_Union[ConsumableRequest.Type, str]]] = ...) -> None: ...

class ConsumableRuntime(_message.Message):
    __slots__ = ("side_brush", "rolling_brush", "filter_mesh", "scrape", "sensor", "mop", "dustbag", "dirty_watertank", "dirty_waterfilter", "accessory_12", "accessory_13", "accessory_15", "accessory_17", "accessory_19", "accessory_detail", "last_time")
    class Duration(_message.Message):
        __slots__ = ("duration",)
        DURATION_FIELD_NUMBER: _ClassVar[int]
        duration: int
        def __init__(self, duration: _Optional[int] = ...) -> None: ...
    SIDE_BRUSH_FIELD_NUMBER: _ClassVar[int]
    ROLLING_BRUSH_FIELD_NUMBER: _ClassVar[int]
    FILTER_MESH_FIELD_NUMBER: _ClassVar[int]
    SCRAPE_FIELD_NUMBER: _ClassVar[int]
    SENSOR_FIELD_NUMBER: _ClassVar[int]
    MOP_FIELD_NUMBER: _ClassVar[int]
    DUSTBAG_FIELD_NUMBER: _ClassVar[int]
    DIRTY_WATERTANK_FIELD_NUMBER: _ClassVar[int]
    DIRTY_WATERFILTER_FIELD_NUMBER: _ClassVar[int]
    ACCESSORY_12_FIELD_NUMBER: _ClassVar[int]
    ACCESSORY_13_FIELD_NUMBER: _ClassVar[int]
    ACCESSORY_15_FIELD_NUMBER: _ClassVar[int]
    ACCESSORY_17_FIELD_NUMBER: _ClassVar[int]
    ACCESSORY_19_FIELD_NUMBER: _ClassVar[int]
    ACCESSORY_DETAIL_FIELD_NUMBER: _ClassVar[int]
    LAST_TIME_FIELD_NUMBER: _ClassVar[int]
    side_brush: ConsumableRuntime.Duration
    rolling_brush: ConsumableRuntime.Duration
    filter_mesh: ConsumableRuntime.Duration
    scrape: ConsumableRuntime.Duration
    sensor: ConsumableRuntime.Duration
    mop: ConsumableRuntime.Duration
    dustbag: ConsumableRuntime.Duration
    dirty_watertank: ConsumableRuntime.Duration
    dirty_waterfilter: ConsumableRuntime.Duration
    accessory_12: ConsumableRuntime.Duration
    accessory_13: ConsumableRuntime.Duration
    accessory_15: ConsumableRuntime.Duration
    accessory_17: bytes
    accessory_19: ConsumableRuntime.Duration
    accessory_detail: bytes
    last_time: int
    def __init__(self, side_brush: _Optional[_Union[ConsumableRuntime.Duration, _Mapping]] = ..., rolling_brush: _Optional[_Union[ConsumableRuntime.Duration, _Mapping]] = ..., filter_mesh: _Optional[_Union[ConsumableRuntime.Duration, _Mapping]] = ..., scrape: _Optional[_Union[ConsumableRuntime.Duration, _Mapping]] = ..., sensor: _Optional[_Union[ConsumableRuntime.Duration, _Mapping]] = ..., mop: _Optional[_Union[ConsumableRuntime.Duration, _Mapping]] = ..., dustbag: _Optional[_Union[ConsumableRuntime.Duration, _Mapping]] = ..., dirty_watertank: _Optional[_Union[ConsumableRuntime.Duration, _Mapping]] = ..., dirty_waterfilter: _Optional[_Union[ConsumableRuntime.Duration, _Mapping]] = ..., accessory_12: _Optional[_Union[ConsumableRuntime.Duration, _Mapping]] = ..., accessory_13: _Optional[_Union[ConsumableRuntime.Duration, _Mapping]] = ..., accessory_15: _Optional[_Union[ConsumableRuntime.Duration, _Mapping]] = ..., accessory_17: _Optional[bytes] = ..., accessory_19: _Optional[_Union[ConsumableRuntime.Duration, _Mapping]] = ..., accessory_detail: _Optional[bytes] = ..., last_time: _Optional[int] = ...) -> None: ...

class ConsumableResponse(_message.Message):
    __slots__ = ("runtime",)
    RUNTIME_FIELD_NUMBER: _ClassVar[int]
    runtime: ConsumableRuntime
    def __init__(self, runtime: _Optional[_Union[ConsumableRuntime, _Mapping]] = ...) -> None: ...
