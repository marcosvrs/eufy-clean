"""Unit tests for calendar.py: week_bits ↔ RRULE conversion round-trips."""

import datetime as dt

import pytest

from custom_components.robovac_mqtt.calendar import (
    _build_timer_info_from_event,
    _rrule_to_week_bits,
    _week_bits_to_rrule,
    _weekday_label,
)


class TestWeekBitsToRrule:
    def test_empty_bits_returns_empty(self):
        assert _week_bits_to_rrule(0) == ""

    def test_sunday_only(self):
        assert _week_bits_to_rrule(0b0000001) == "FREQ=WEEKLY;BYDAY=SU"

    def test_monday_only(self):
        assert _week_bits_to_rrule(0b0000010) == "FREQ=WEEKLY;BYDAY=MO"

    def test_saturday_only(self):
        assert _week_bits_to_rrule(0b1000000) == "FREQ=WEEKLY;BYDAY=SA"

    def test_weekdays_mon_through_fri(self):
        assert _week_bits_to_rrule(0b0111110) == "FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR"

    def test_weekend_sun_sat(self):
        assert _week_bits_to_rrule(0b1000001) == "FREQ=WEEKLY;BYDAY=SU,SA"

    def test_every_day(self):
        assert _week_bits_to_rrule(0x7F) == "FREQ=WEEKLY;BYDAY=SU,MO,TU,WE,TH,FR,SA"

    def test_tue_thu(self):
        assert _week_bits_to_rrule(0b0010100) == "FREQ=WEEKLY;BYDAY=TU,TH"


class TestRruleToWeekBits:
    def test_empty_string_returns_none(self):
        assert _rrule_to_week_bits("") is None

    def test_no_byday_returns_none(self):
        assert _rrule_to_week_bits("FREQ=WEEKLY") is None

    def test_sunday_only(self):
        assert _rrule_to_week_bits("FREQ=WEEKLY;BYDAY=SU") == 0b0000001

    def test_monday_only(self):
        assert _rrule_to_week_bits("FREQ=WEEKLY;BYDAY=MO") == 0b0000010

    def test_saturday_only(self):
        assert _rrule_to_week_bits("FREQ=WEEKLY;BYDAY=SA") == 0b1000000

    def test_weekdays(self):
        assert _rrule_to_week_bits("FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR") == 0b0111110

    def test_weekend(self):
        assert _rrule_to_week_bits("FREQ=WEEKLY;BYDAY=SU,SA") == 0b1000001

    def test_every_day(self):
        rrule = "FREQ=WEEKLY;BYDAY=SU,MO,TU,WE,TH,FR,SA"
        assert _rrule_to_week_bits(rrule) == 0x7F

    def test_case_insensitive(self):
        assert _rrule_to_week_bits("FREQ=WEEKLY;BYDAY=mo,tu") == 0b0000110

    def test_whitespace_tolerance(self):
        assert _rrule_to_week_bits("FREQ=WEEKLY;BYDAY= MO , TU ") == 0b0000110


class TestRoundTripWeekBitsFirst:
    @pytest.mark.parametrize("bits", [
        0b0000001,
        0b0000010,
        0b0000100,
        0b0001000,
        0b0010000,
        0b0100000,
        0b1000000,
        0b0111110,
        0b1000001,
        0x7F,
        0b0010100,
        0b0101010,
    ])
    def test_week_bits_survives_round_trip(self, bits):
        rrule = _week_bits_to_rrule(bits)
        assert rrule
        recovered = _rrule_to_week_bits(rrule)
        assert recovered == bits


class TestRoundTripRruleFirst:
    @pytest.mark.parametrize("rrule", [
        "FREQ=WEEKLY;BYDAY=SU",
        "FREQ=WEEKLY;BYDAY=MO",
        "FREQ=WEEKLY;BYDAY=SA",
        "FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR",
        "FREQ=WEEKLY;BYDAY=SU,SA",
        "FREQ=WEEKLY;BYDAY=SU,MO,TU,WE,TH,FR,SA",
        "FREQ=WEEKLY;BYDAY=TU,TH",
    ])
    def test_rrule_survives_round_trip(self, rrule):
        bits = _rrule_to_week_bits(rrule)
        assert bits is not None
        recovered = _week_bits_to_rrule(bits)
        assert recovered == rrule


class TestWeekdayLabel:
    def test_every_day(self):
        assert _weekday_label(0x7F) == "Every day"

    def test_single_day(self):
        assert _weekday_label(0b0000010) == "Mon"

    def test_weekend(self):
        assert _weekday_label(0b1000001) == "Sun, Sat"

    def test_zero_bits(self):
        assert _weekday_label(0) == ""


class TestBuildTimerInfoRrule:
    def test_cycle_event_embeds_week_bits(self):
        event = {
            "dtstart": dt.datetime(2025, 1, 6, 8, 30),
            "rrule": "FREQ=WEEKLY;BYDAY=MO,WE,FR",
        }
        info = _build_timer_info_from_event(event)
        assert info["desc"]["trigger"] == 1
        assert info["desc"]["cycle"]["week_bits"] == 0b0101010

    def test_one_time_event_no_cycle_key(self):
        event = {
            "dtstart": dt.datetime(2025, 1, 6, 9, 0),
        }
        info = _build_timer_info_from_event(event)
        assert info["desc"]["trigger"] == 0
        assert "cycle" not in info["desc"]

    def test_cycle_event_preserves_time(self):
        event = {
            "dtstart": dt.datetime(2025, 3, 15, 14, 45),
            "rrule": "FREQ=WEEKLY;BYDAY=SA",
        }
        info = _build_timer_info_from_event(event)
        assert info["desc"]["timing"]["hours"] == 14
        assert info["desc"]["timing"]["minutes"] == 45

    def test_timer_id_included_when_given(self):
        event = {
            "dtstart": dt.datetime(2025, 1, 7, 7, 0),
            "rrule": "FREQ=WEEKLY;BYDAY=TU",
        }
        info = _build_timer_info_from_event(event, timer_id=42)
        assert info["id"] == {"value": 42}

    def test_timer_id_absent_when_not_given(self):
        event = {
            "dtstart": dt.datetime(2025, 1, 7, 7, 0),
            "rrule": "FREQ=WEEKLY;BYDAY=TU",
        }
        info = _build_timer_info_from_event(event)
        assert "id" not in info

    def test_every_day_round_trip_through_timer_info(self):
        rrule_in = "FREQ=WEEKLY;BYDAY=SU,MO,TU,WE,TH,FR,SA"
        event = {
            "dtstart": dt.datetime(2025, 6, 1, 10, 0),
            "rrule": rrule_in,
        }
        info = _build_timer_info_from_event(event)
        bits = info["desc"]["cycle"]["week_bits"]
        assert bits == 0x7F
        rrule_out = _week_bits_to_rrule(bits)
        assert rrule_out == rrule_in
