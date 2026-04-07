from custom_components.robovac_mqtt.api.commands import (
    build_command,
    build_media_capture_command,
    build_media_record_command,
    build_media_set_resolution_command,
)
from custom_components.robovac_mqtt.api.parser import update_state
from custom_components.robovac_mqtt.const import DEFAULT_DPS_MAP
from custom_components.robovac_mqtt.models import VacuumState
from custom_components.robovac_mqtt.proto.cloud.media_manager_pb2 import (
    MediaManagerRequest,
    MediaManagerResponse,
    MediaSetting,
    MediaStatus,
)
from custom_components.robovac_mqtt.utils import decode, encode_message


class TestMediaCommands:

    def test_capture_command_encodes_method(self):
        result = build_media_capture_command(seq=42)
        assert DEFAULT_DPS_MAP["MEDIA_MANAGER"] in result
        decoded = decode(MediaManagerRequest, result[DEFAULT_DPS_MAP["MEDIA_MANAGER"]])
        assert decoded.control.method == MediaManagerRequest.Control.CAPTURE
        assert decoded.control.seq == 42

    def test_record_start_command(self):
        result = build_media_record_command(start=True, seq=1)
        decoded = decode(MediaManagerRequest, result[DEFAULT_DPS_MAP["MEDIA_MANAGER"]])
        assert decoded.control.method == MediaManagerRequest.Control.RECORD_START

    def test_record_stop_command(self):
        result = build_media_record_command(start=False, seq=2)
        decoded = decode(MediaManagerRequest, result[DEFAULT_DPS_MAP["MEDIA_MANAGER"]])
        assert decoded.control.method == MediaManagerRequest.Control.RECORD_STOP
        assert decoded.control.seq == 2

    def test_set_resolution_1080p(self):
        result = build_media_set_resolution_command("1080p")
        decoded = decode(MediaManagerRequest, result[DEFAULT_DPS_MAP["MEDIA_MANAGER"]])
        assert decoded.setting.record.resolution == MediaSetting.R_1080P

    def test_set_resolution_480p(self):
        result = build_media_set_resolution_command("480p")
        decoded = decode(MediaManagerRequest, result[DEFAULT_DPS_MAP["MEDIA_MANAGER"]])
        assert decoded.setting.record.resolution == MediaSetting.R_480P

    def test_set_resolution_invalid_returns_empty(self):
        result = build_media_set_resolution_command("4k")
        assert not result

    def test_build_command_dispatcher_media_capture(self):
        result = build_command("media_capture", seq=5)
        assert DEFAULT_DPS_MAP["MEDIA_MANAGER"] in result

    def test_build_command_dispatcher_media_record(self):
        result = build_command("media_record", start=True)
        assert DEFAULT_DPS_MAP["MEDIA_MANAGER"] in result

    def test_build_command_dispatcher_media_set_resolution(self):
        result = build_command("media_set_resolution", resolution="720p")
        assert DEFAULT_DPS_MAP["MEDIA_MANAGER"] in result


class TestMediaParser:

    def _encode_response(self, resp: MediaManagerResponse) -> str:
        return encode_message(resp)

    def test_parse_media_status_recording(self):
        resp = MediaManagerResponse(
            status=MediaStatus(
                state=MediaStatus.RECORDING,
                storage=MediaStatus.NORMAL,
                total_space=1024000,
                photo_space=10000,
                video_space=50000,
            ),
        )
        state = VacuumState()
        dps = {DEFAULT_DPS_MAP["MEDIA_MANAGER"]: self._encode_response(resp)}
        new_state, changes = update_state(state, dps)
        assert new_state.media_recording is True
        assert new_state.media_storage_state == "Normal"
        assert new_state.media_total_space == 1024000
        assert new_state.media_photo_space == 10000
        assert new_state.media_video_space == 50000
        assert "media_status" in new_state.received_fields

    def test_parse_media_status_idle(self):
        resp = MediaManagerResponse(
            status=MediaStatus(state=MediaStatus.IDLE),
        )
        state = VacuumState()
        dps = {DEFAULT_DPS_MAP["MEDIA_MANAGER"]: self._encode_response(resp)}
        new_state, _ = update_state(state, dps)
        assert new_state.media_recording is False

    def test_parse_media_storage_full(self):
        resp = MediaManagerResponse(
            status=MediaStatus(storage=MediaStatus.FULL),
        )
        state = VacuumState()
        dps = {DEFAULT_DPS_MAP["MEDIA_MANAGER"]: self._encode_response(resp)}
        new_state, _ = update_state(state, dps)
        assert new_state.media_storage_state == "Full"

    def test_parse_media_recording_resolution(self):
        resp = MediaManagerResponse(
            setting=MediaSetting(
                record=MediaSetting.Record(resolution=MediaSetting.R_1080P),
            ),
        )
        state = VacuumState()
        dps = {DEFAULT_DPS_MAP["MEDIA_MANAGER"]: self._encode_response(resp)}
        new_state, _ = update_state(state, dps)
        assert new_state.media_recording_resolution == "1080p"
        assert "media_recording_resolution" in new_state.received_fields

    def test_parse_media_capture_file_info(self):
        resp = MediaManagerResponse(
            control=MediaManagerResponse.Control(
                method=MediaManagerRequest.Control.CAPTURE,
                seq=1,
                result=MediaManagerResponse.Control.SUCCESS,
                file_info=MediaManagerResponse.Control.FileInfo(
                    filepath="/sdcard/photo_001.jpg",
                    id="photo_001",
                ),
            ),
        )
        state = VacuumState()
        dps = {DEFAULT_DPS_MAP["MEDIA_MANAGER"]: self._encode_response(resp)}
        new_state, _ = update_state(state, dps)
        assert new_state.media_last_capture_path == "/sdcard/photo_001.jpg"
        assert new_state.media_last_capture_id == "photo_001"
        assert "media_last_capture" in new_state.received_fields

    def test_parse_media_combined_status_and_setting(self):
        resp = MediaManagerResponse(
            status=MediaStatus(
                state=MediaStatus.RECORDING,
                storage=MediaStatus.THRESHOLD,
            ),
            setting=MediaSetting(
                record=MediaSetting.Record(resolution=MediaSetting.R_480P),
            ),
        )
        state = VacuumState()
        dps = {DEFAULT_DPS_MAP["MEDIA_MANAGER"]: self._encode_response(resp)}
        new_state, _ = update_state(state, dps)
        assert new_state.media_recording is True
        assert new_state.media_storage_state == "Threshold"
        assert new_state.media_recording_resolution == "480p"
