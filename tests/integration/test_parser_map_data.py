from __future__ import annotations

from custom_components.robovac_mqtt.api.parser import update_state
from custom_components.robovac_mqtt.models import VacuumState
from custom_components.robovac_mqtt.proto.cloud.stream_pb2 import RoomParams
from custom_components.robovac_mqtt.proto.cloud.universal_data_pb2 import (
    UniversalDataResponse,
)
from custom_components.robovac_mqtt.utils import encode_message


def _map_dps(proto_msg) -> dict[str, str]:
    return {"165": encode_message(proto_msg)}


def test_universal_data_response_rooms():
    resp = UniversalDataResponse(
        cur_map_room=UniversalDataResponse.RoomTable(
            map_id=4,
            data=[
                UniversalDataResponse.RoomTable.Data(id=1, name="Kitchen"),
                UniversalDataResponse.RoomTable.Data(id=2, name="Living Room"),
                UniversalDataResponse.RoomTable.Data(id=3, name="Bedroom"),
            ],
        ),
    )
    state, changes = update_state(VacuumState(), _map_dps(resp))

    assert state.map_id == 4
    assert len(state.rooms) == 3
    assert state.rooms[0] == {"id": 1, "name": "Kitchen"}
    assert state.rooms[1] == {"id": 2, "name": "Living Room"}
    assert state.rooms[2] == {"id": 3, "name": "Bedroom"}


def test_room_params_format():
    rp = RoomParams(
        map_id=6,
        rooms=[
            RoomParams.Room(id=1, name="Office"),
            RoomParams.Room(id=2, name="Hallway"),
        ],
    )
    state, changes = update_state(VacuumState(), _map_dps(rp))

    assert state.map_id == 6
    assert len(state.rooms) == 2
    assert state.rooms[0] == {"id": 1, "name": "Office"}
    assert state.rooms[1] == {"id": 2, "name": "Hallway"}


def test_room_deduplication():
    resp = UniversalDataResponse(
        cur_map_room=UniversalDataResponse.RoomTable(
            map_id=10,
            data=[
                UniversalDataResponse.RoomTable.Data(id=1, name="Kitchen"),
                UniversalDataResponse.RoomTable.Data(id=2, name="Kitchen"),
                UniversalDataResponse.RoomTable.Data(id=3, name="Bedroom"),
            ],
        ),
    )
    state, _ = update_state(VacuumState(), _map_dps(resp))

    assert len(state.rooms) == 3
    assert state.rooms[0]["name"] == "Kitchen"
    assert state.rooms[1]["name"] == "Kitchen (2)"
    assert state.rooms[2]["name"] == "Bedroom"


def test_map_id_extraction():
    resp = UniversalDataResponse(
        cur_map_room=UniversalDataResponse.RoomTable(
            map_id=42,
            data=[
                UniversalDataResponse.RoomTable.Data(id=1, name="Room A"),
            ],
        ),
    )
    state, changes = update_state(VacuumState(), _map_dps(resp))

    assert state.map_id == 42
    assert changes["map_id"] == 42
    assert "map_id" in state.received_fields


def test_empty_room_list():
    resp = UniversalDataResponse(
        cur_map_room=UniversalDataResponse.RoomTable(
            map_id=7,
            data=[],
        ),
    )
    state, changes = update_state(VacuumState(), _map_dps(resp))

    assert state.map_id == 7
    assert state.rooms == []


def test_room_with_blank_name_gets_default():
    resp = UniversalDataResponse(
        cur_map_room=UniversalDataResponse.RoomTable(
            map_id=5,
            data=[
                UniversalDataResponse.RoomTable.Data(id=1, name=""),
                UniversalDataResponse.RoomTable.Data(id=2, name="  "),
                UniversalDataResponse.RoomTable.Data(id=3, name="Valid"),
            ],
        ),
    )
    state, _ = update_state(VacuumState(), _map_dps(resp))

    assert state.rooms[0]["name"] == "Room 1"
    assert state.rooms[1]["name"] == "Room 2"
    assert state.rooms[2]["name"] == "Valid"


def test_room_params_deduplication():
    rp = RoomParams(
        map_id=8,
        rooms=[
            RoomParams.Room(id=1, name="Bathroom"),
            RoomParams.Room(id=2, name="Bathroom"),
            RoomParams.Room(id=3, name="Bathroom"),
        ],
    )
    state, _ = update_state(VacuumState(), _map_dps(rp))

    assert state.rooms[0]["name"] == "Bathroom"
    assert state.rooms[1]["name"] == "Bathroom (2)"
    assert state.rooms[2]["name"] == "Bathroom (3)"
