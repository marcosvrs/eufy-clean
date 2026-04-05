from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class PositionTelemetry(_message.Message):
    __slots__ = ("timestamp", "battery", "unknown_seq", "x", "y", "extra_data")
    TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    BATTERY_FIELD_NUMBER: _ClassVar[int]
    UNKNOWN_SEQ_FIELD_NUMBER: _ClassVar[int]
    X_FIELD_NUMBER: _ClassVar[int]
    Y_FIELD_NUMBER: _ClassVar[int]
    EXTRA_DATA_FIELD_NUMBER: _ClassVar[int]
    timestamp: int
    battery: int
    unknown_seq: int
    x: int
    y: int
    extra_data: bytes
    def __init__(self, timestamp: _Optional[int] = ..., battery: _Optional[int] = ..., unknown_seq: _Optional[int] = ..., x: _Optional[int] = ..., y: _Optional[int] = ..., extra_data: _Optional[bytes] = ...) -> None: ...

class TelemetryWrapper(_message.Message):
    __slots__ = ("lifetime_stats", "position")
    LIFETIME_STATS_FIELD_NUMBER: _ClassVar[int]
    POSITION_FIELD_NUMBER: _ClassVar[int]
    lifetime_stats: bytes
    position: PositionTelemetry
    def __init__(self, lifetime_stats: _Optional[bytes] = ..., position: _Optional[_Union[PositionTelemetry, _Mapping]] = ...) -> None: ...

class RealtimeStream(_message.Message):
    __slots__ = ("data", "session_summary_short", "session_summary_long")
    DATA_FIELD_NUMBER: _ClassVar[int]
    SESSION_SUMMARY_SHORT_FIELD_NUMBER: _ClassVar[int]
    SESSION_SUMMARY_LONG_FIELD_NUMBER: _ClassVar[int]
    data: TelemetryWrapper
    session_summary_short: bytes
    session_summary_long: bytes
    def __init__(self, data: _Optional[_Union[TelemetryWrapper, _Mapping]] = ..., session_summary_short: _Optional[bytes] = ..., session_summary_long: _Optional[bytes] = ...) -> None: ...
