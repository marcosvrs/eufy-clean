from proto.cloud import common_pb2 as _common_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class UnisettingRequest(_message.Message):
    __slots__ = ("children_lock", "cruise_continue_sw", "multi_map_sw", "ai_see", "multi_map_options", "wifi_setting", "water_level_sw", "suggest_restricted_zone_sw", "deep_mop_corner_sw", "dust_full_remind", "live_photo_sw", "smart_follow_sw", "poop_avoidance_sw", "pet_mode_sw")
    class MultiMapOptions(_message.Message):
        __slots__ = ("retain",)
        class Retain(_message.Message):
            __slots__ = ("map_id",)
            MAP_ID_FIELD_NUMBER: _ClassVar[int]
            map_id: _containers.RepeatedScalarFieldContainer[int]
            def __init__(self, map_id: _Optional[_Iterable[int]] = ...) -> None: ...
        RETAIN_FIELD_NUMBER: _ClassVar[int]
        retain: UnisettingRequest.MultiMapOptions.Retain
        def __init__(self, retain: _Optional[_Union[UnisettingRequest.MultiMapOptions.Retain, _Mapping]] = ...) -> None: ...
    class WifiSetting(_message.Message):
        __slots__ = ("deletion",)
        class Deletion(_message.Message):
            __slots__ = ("ssid",)
            SSID_FIELD_NUMBER: _ClassVar[int]
            ssid: _containers.RepeatedScalarFieldContainer[str]
            def __init__(self, ssid: _Optional[_Iterable[str]] = ...) -> None: ...
        DELETION_FIELD_NUMBER: _ClassVar[int]
        deletion: UnisettingRequest.WifiSetting.Deletion
        def __init__(self, deletion: _Optional[_Union[UnisettingRequest.WifiSetting.Deletion, _Mapping]] = ...) -> None: ...
    CHILDREN_LOCK_FIELD_NUMBER: _ClassVar[int]
    CRUISE_CONTINUE_SW_FIELD_NUMBER: _ClassVar[int]
    MULTI_MAP_SW_FIELD_NUMBER: _ClassVar[int]
    AI_SEE_FIELD_NUMBER: _ClassVar[int]
    MULTI_MAP_OPTIONS_FIELD_NUMBER: _ClassVar[int]
    WIFI_SETTING_FIELD_NUMBER: _ClassVar[int]
    WATER_LEVEL_SW_FIELD_NUMBER: _ClassVar[int]
    SUGGEST_RESTRICTED_ZONE_SW_FIELD_NUMBER: _ClassVar[int]
    DEEP_MOP_CORNER_SW_FIELD_NUMBER: _ClassVar[int]
    DUST_FULL_REMIND_FIELD_NUMBER: _ClassVar[int]
    LIVE_PHOTO_SW_FIELD_NUMBER: _ClassVar[int]
    SMART_FOLLOW_SW_FIELD_NUMBER: _ClassVar[int]
    POOP_AVOIDANCE_SW_FIELD_NUMBER: _ClassVar[int]
    PET_MODE_SW_FIELD_NUMBER: _ClassVar[int]
    children_lock: _common_pb2.Switch
    cruise_continue_sw: _common_pb2.Switch
    multi_map_sw: _common_pb2.Switch
    ai_see: _common_pb2.Switch
    multi_map_options: UnisettingRequest.MultiMapOptions
    wifi_setting: UnisettingRequest.WifiSetting
    water_level_sw: _common_pb2.Switch
    suggest_restricted_zone_sw: _common_pb2.Switch
    deep_mop_corner_sw: _common_pb2.Switch
    dust_full_remind: _common_pb2.Numerical
    live_photo_sw: _common_pb2.Switch
    smart_follow_sw: _common_pb2.Switch
    poop_avoidance_sw: _common_pb2.Switch
    pet_mode_sw: _common_pb2.Switch
    def __init__(self, children_lock: _Optional[_Union[_common_pb2.Switch, _Mapping]] = ..., cruise_continue_sw: _Optional[_Union[_common_pb2.Switch, _Mapping]] = ..., multi_map_sw: _Optional[_Union[_common_pb2.Switch, _Mapping]] = ..., ai_see: _Optional[_Union[_common_pb2.Switch, _Mapping]] = ..., multi_map_options: _Optional[_Union[UnisettingRequest.MultiMapOptions, _Mapping]] = ..., wifi_setting: _Optional[_Union[UnisettingRequest.WifiSetting, _Mapping]] = ..., water_level_sw: _Optional[_Union[_common_pb2.Switch, _Mapping]] = ..., suggest_restricted_zone_sw: _Optional[_Union[_common_pb2.Switch, _Mapping]] = ..., deep_mop_corner_sw: _Optional[_Union[_common_pb2.Switch, _Mapping]] = ..., dust_full_remind: _Optional[_Union[_common_pb2.Numerical, _Mapping]] = ..., live_photo_sw: _Optional[_Union[_common_pb2.Switch, _Mapping]] = ..., smart_follow_sw: _Optional[_Union[_common_pb2.Switch, _Mapping]] = ..., poop_avoidance_sw: _Optional[_Union[_common_pb2.Switch, _Mapping]] = ..., pet_mode_sw: _Optional[_Union[_common_pb2.Switch, _Mapping]] = ...) -> None: ...

class Unistate(_message.Message):
    __slots__ = ("mop_holder_state_l", "mop_holder_state_r", "custom_clean_mode", "map_valid", "mop_state", "live_map", "clean_strategy_version", "unistate_8")
    class LiveMap(_message.Message):
        __slots__ = ("state_bits",)
        class StateBit(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
            __slots__ = ()
            BASE: _ClassVar[Unistate.LiveMap.StateBit]
            ROOM: _ClassVar[Unistate.LiveMap.StateBit]
            KITCHEN: _ClassVar[Unistate.LiveMap.StateBit]
            PET: _ClassVar[Unistate.LiveMap.StateBit]
        BASE: Unistate.LiveMap.StateBit
        ROOM: Unistate.LiveMap.StateBit
        KITCHEN: Unistate.LiveMap.StateBit
        PET: Unistate.LiveMap.StateBit
        STATE_BITS_FIELD_NUMBER: _ClassVar[int]
        state_bits: int
        def __init__(self, state_bits: _Optional[int] = ...) -> None: ...
    MOP_HOLDER_STATE_L_FIELD_NUMBER: _ClassVar[int]
    MOP_HOLDER_STATE_R_FIELD_NUMBER: _ClassVar[int]
    CUSTOM_CLEAN_MODE_FIELD_NUMBER: _ClassVar[int]
    MAP_VALID_FIELD_NUMBER: _ClassVar[int]
    MOP_STATE_FIELD_NUMBER: _ClassVar[int]
    LIVE_MAP_FIELD_NUMBER: _ClassVar[int]
    CLEAN_STRATEGY_VERSION_FIELD_NUMBER: _ClassVar[int]
    UNISTATE_8_FIELD_NUMBER: _ClassVar[int]
    mop_holder_state_l: _common_pb2.Switch
    mop_holder_state_r: _common_pb2.Switch
    custom_clean_mode: _common_pb2.Switch
    map_valid: _common_pb2.Active
    mop_state: _common_pb2.Switch
    live_map: Unistate.LiveMap
    clean_strategy_version: int
    unistate_8: bytes
    def __init__(self, mop_holder_state_l: _Optional[_Union[_common_pb2.Switch, _Mapping]] = ..., mop_holder_state_r: _Optional[_Union[_common_pb2.Switch, _Mapping]] = ..., custom_clean_mode: _Optional[_Union[_common_pb2.Switch, _Mapping]] = ..., map_valid: _Optional[_Union[_common_pb2.Active, _Mapping]] = ..., mop_state: _Optional[_Union[_common_pb2.Switch, _Mapping]] = ..., live_map: _Optional[_Union[Unistate.LiveMap, _Mapping]] = ..., clean_strategy_version: _Optional[int] = ..., unistate_8: _Optional[bytes] = ...) -> None: ...

class WifiData(_message.Message):
    __slots__ = ("ap",)
    class Ap(_message.Message):
        __slots__ = ("ssid", "frequency", "connection")
        class Frequency(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
            __slots__ = ()
            FREQ_2_4G: _ClassVar[WifiData.Ap.Frequency]
            FREQ_5G: _ClassVar[WifiData.Ap.Frequency]
        FREQ_2_4G: WifiData.Ap.Frequency
        FREQ_5G: WifiData.Ap.Frequency
        class Connection(_message.Message):
            __slots__ = ("result", "timestamp")
            class Result(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
                __slots__ = ()
                OK: _ClassVar[WifiData.Ap.Connection.Result]
                PASSWD_ERR: _ClassVar[WifiData.Ap.Connection.Result]
            OK: WifiData.Ap.Connection.Result
            PASSWD_ERR: WifiData.Ap.Connection.Result
            RESULT_FIELD_NUMBER: _ClassVar[int]
            TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
            result: WifiData.Ap.Connection.Result
            timestamp: int
            def __init__(self, result: _Optional[_Union[WifiData.Ap.Connection.Result, str]] = ..., timestamp: _Optional[int] = ...) -> None: ...
        SSID_FIELD_NUMBER: _ClassVar[int]
        FREQUENCY_FIELD_NUMBER: _ClassVar[int]
        CONNECTION_FIELD_NUMBER: _ClassVar[int]
        ssid: str
        frequency: WifiData.Ap.Frequency
        connection: WifiData.Ap.Connection
        def __init__(self, ssid: _Optional[str] = ..., frequency: _Optional[_Union[WifiData.Ap.Frequency, str]] = ..., connection: _Optional[_Union[WifiData.Ap.Connection, _Mapping]] = ...) -> None: ...
    AP_FIELD_NUMBER: _ClassVar[int]
    ap: _containers.RepeatedCompositeFieldContainer[WifiData.Ap]
    def __init__(self, ap: _Optional[_Iterable[_Union[WifiData.Ap, _Mapping]]] = ...) -> None: ...

class UnisettingResponse(_message.Message):
    __slots__ = ("children_lock", "cruise_continue_sw", "multi_map_sw", "ai_see", "water_level_sw", "suggest_restricted_zone_sw", "deep_mop_corner_sw", "dust_full_remind", "live_photo_sw", "unistate", "ap_signal_strength", "wifi_data", "smart_follow_sw", "poop_avoidance_sw", "pet_mode_sw", "setting_16", "setting_18", "setting_21", "setting_22", "setting_23")
    CHILDREN_LOCK_FIELD_NUMBER: _ClassVar[int]
    CRUISE_CONTINUE_SW_FIELD_NUMBER: _ClassVar[int]
    MULTI_MAP_SW_FIELD_NUMBER: _ClassVar[int]
    AI_SEE_FIELD_NUMBER: _ClassVar[int]
    WATER_LEVEL_SW_FIELD_NUMBER: _ClassVar[int]
    SUGGEST_RESTRICTED_ZONE_SW_FIELD_NUMBER: _ClassVar[int]
    DEEP_MOP_CORNER_SW_FIELD_NUMBER: _ClassVar[int]
    DUST_FULL_REMIND_FIELD_NUMBER: _ClassVar[int]
    LIVE_PHOTO_SW_FIELD_NUMBER: _ClassVar[int]
    UNISTATE_FIELD_NUMBER: _ClassVar[int]
    AP_SIGNAL_STRENGTH_FIELD_NUMBER: _ClassVar[int]
    WIFI_DATA_FIELD_NUMBER: _ClassVar[int]
    SMART_FOLLOW_SW_FIELD_NUMBER: _ClassVar[int]
    POOP_AVOIDANCE_SW_FIELD_NUMBER: _ClassVar[int]
    PET_MODE_SW_FIELD_NUMBER: _ClassVar[int]
    SETTING_16_FIELD_NUMBER: _ClassVar[int]
    SETTING_18_FIELD_NUMBER: _ClassVar[int]
    SETTING_21_FIELD_NUMBER: _ClassVar[int]
    SETTING_22_FIELD_NUMBER: _ClassVar[int]
    SETTING_23_FIELD_NUMBER: _ClassVar[int]
    children_lock: _common_pb2.Switch
    cruise_continue_sw: _common_pb2.Switch
    multi_map_sw: _common_pb2.Switch
    ai_see: _common_pb2.Switch
    water_level_sw: _common_pb2.Switch
    suggest_restricted_zone_sw: _common_pb2.Switch
    deep_mop_corner_sw: _common_pb2.Switch
    dust_full_remind: _common_pb2.Numerical
    live_photo_sw: _common_pb2.Switch
    unistate: Unistate
    ap_signal_strength: int
    wifi_data: WifiData
    smart_follow_sw: _common_pb2.Switch
    poop_avoidance_sw: _common_pb2.Switch
    pet_mode_sw: _common_pb2.Switch
    setting_16: _common_pb2.Switch
    setting_18: bytes
    setting_21: bytes
    setting_22: _common_pb2.Switch
    setting_23: bytes
    def __init__(self, children_lock: _Optional[_Union[_common_pb2.Switch, _Mapping]] = ..., cruise_continue_sw: _Optional[_Union[_common_pb2.Switch, _Mapping]] = ..., multi_map_sw: _Optional[_Union[_common_pb2.Switch, _Mapping]] = ..., ai_see: _Optional[_Union[_common_pb2.Switch, _Mapping]] = ..., water_level_sw: _Optional[_Union[_common_pb2.Switch, _Mapping]] = ..., suggest_restricted_zone_sw: _Optional[_Union[_common_pb2.Switch, _Mapping]] = ..., deep_mop_corner_sw: _Optional[_Union[_common_pb2.Switch, _Mapping]] = ..., dust_full_remind: _Optional[_Union[_common_pb2.Numerical, _Mapping]] = ..., live_photo_sw: _Optional[_Union[_common_pb2.Switch, _Mapping]] = ..., unistate: _Optional[_Union[Unistate, _Mapping]] = ..., ap_signal_strength: _Optional[int] = ..., wifi_data: _Optional[_Union[WifiData, _Mapping]] = ..., smart_follow_sw: _Optional[_Union[_common_pb2.Switch, _Mapping]] = ..., poop_avoidance_sw: _Optional[_Union[_common_pb2.Switch, _Mapping]] = ..., pet_mode_sw: _Optional[_Union[_common_pb2.Switch, _Mapping]] = ..., setting_16: _Optional[_Union[_common_pb2.Switch, _Mapping]] = ..., setting_18: _Optional[bytes] = ..., setting_21: _Optional[bytes] = ..., setting_22: _Optional[_Union[_common_pb2.Switch, _Mapping]] = ..., setting_23: _Optional[bytes] = ...) -> None: ...
