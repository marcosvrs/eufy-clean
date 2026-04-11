from proto.cloud import version_pb2 as _version_pb2
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class AppInfo(_message.Message):
    __slots__ = ("platform", "app_version", "family_id", "user_id", "data_center", "app_function", "time_zone_id")
    class Platform(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        PF_OTHER: _ClassVar[AppInfo.Platform]
        PF_ANDROID: _ClassVar[AppInfo.Platform]
        PF_IOS: _ClassVar[AppInfo.Platform]
        PF_CLOUD: _ClassVar[AppInfo.Platform]
    PF_OTHER: AppInfo.Platform
    PF_ANDROID: AppInfo.Platform
    PF_IOS: AppInfo.Platform
    PF_CLOUD: AppInfo.Platform
    class DataCenter(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        EU: _ClassVar[AppInfo.DataCenter]
        AZ: _ClassVar[AppInfo.DataCenter]
        AY: _ClassVar[AppInfo.DataCenter]
    EU: AppInfo.DataCenter
    AZ: AppInfo.DataCenter
    AY: AppInfo.DataCenter
    PLATFORM_FIELD_NUMBER: _ClassVar[int]
    APP_VERSION_FIELD_NUMBER: _ClassVar[int]
    FAMILY_ID_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    DATA_CENTER_FIELD_NUMBER: _ClassVar[int]
    APP_FUNCTION_FIELD_NUMBER: _ClassVar[int]
    TIME_ZONE_ID_FIELD_NUMBER: _ClassVar[int]
    platform: AppInfo.Platform
    app_version: str
    family_id: str
    user_id: str
    data_center: AppInfo.DataCenter
    app_function: _version_pb2.AppFunction
    time_zone_id: str
    def __init__(self, platform: _Optional[_Union[AppInfo.Platform, str]] = ..., app_version: _Optional[str] = ..., family_id: _Optional[str] = ..., user_id: _Optional[str] = ..., data_center: _Optional[_Union[AppInfo.DataCenter, str]] = ..., app_function: _Optional[_Union[_version_pb2.AppFunction, _Mapping]] = ..., time_zone_id: _Optional[str] = ...) -> None: ...

class DeviceInfo(_message.Message):
    __slots__ = ("product_name", "video_sn", "device_mac", "software", "hardware", "wifi_name", "wifi_ip", "last_user_id", "station", "proto_info", "ota_channel")
    class Station(_message.Message):
        __slots__ = ("software", "hardware")
        SOFTWARE_FIELD_NUMBER: _ClassVar[int]
        HARDWARE_FIELD_NUMBER: _ClassVar[int]
        software: str
        hardware: int
        def __init__(self, software: _Optional[str] = ..., hardware: _Optional[int] = ...) -> None: ...
    PRODUCT_NAME_FIELD_NUMBER: _ClassVar[int]
    VIDEO_SN_FIELD_NUMBER: _ClassVar[int]
    DEVICE_MAC_FIELD_NUMBER: _ClassVar[int]
    SOFTWARE_FIELD_NUMBER: _ClassVar[int]
    HARDWARE_FIELD_NUMBER: _ClassVar[int]
    WIFI_NAME_FIELD_NUMBER: _ClassVar[int]
    WIFI_IP_FIELD_NUMBER: _ClassVar[int]
    LAST_USER_ID_FIELD_NUMBER: _ClassVar[int]
    STATION_FIELD_NUMBER: _ClassVar[int]
    PROTO_INFO_FIELD_NUMBER: _ClassVar[int]
    OTA_CHANNEL_FIELD_NUMBER: _ClassVar[int]
    product_name: str
    video_sn: str
    device_mac: str
    software: str
    hardware: int
    wifi_name: str
    wifi_ip: str
    last_user_id: str
    station: DeviceInfo.Station
    proto_info: _version_pb2.ProtoInfo
    ota_channel: str
    def __init__(self, product_name: _Optional[str] = ..., video_sn: _Optional[str] = ..., device_mac: _Optional[str] = ..., software: _Optional[str] = ..., hardware: _Optional[int] = ..., wifi_name: _Optional[str] = ..., wifi_ip: _Optional[str] = ..., last_user_id: _Optional[str] = ..., station: _Optional[_Union[DeviceInfo.Station, _Mapping]] = ..., proto_info: _Optional[_Union[_version_pb2.ProtoInfo, _Mapping]] = ..., ota_channel: _Optional[str] = ...) -> None: ...
