"""Tests for the Meeus solar engine, using worked examples from Astronomical Algorithms."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
import importlib.util
from pathlib import Path
import sys

import pytest

# Load solar_engine.py directly so the tests don't need Home Assistant installed
_MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "custom_components"
    / "helios"
    / "solar_engine.py"
)
_spec = importlib.util.spec_from_file_location("solar_engine", _MODULE_PATH)
solar_engine = importlib.util.module_from_spec(_spec)
sys.modules["solar_engine"] = solar_engine
_spec.loader.exec_module(solar_engine)

MeeusSolarEngine = solar_engine.MeeusSolarEngine

PARIS = (48.8566, 2.3522)
TROMSO = (69.6492, 18.9553)


def test_julian_day_meeus_example_7a() -> None:
    """1957 October 4.81 UT → JD 2436116.31 (Meeus Example 7.a)."""
    dt = datetime(1957, 10, 4, 19, 26, 24, tzinfo=timezone.utc)
    assert MeeusSolarEngine.to_julian_day(dt) == pytest.approx(2436116.31, abs=1e-6)


def test_julian_day_j2000() -> None:
    """J2000.0 epoch is JD 2451545.0 and T = 0."""
    dt = datetime(2000, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    jd = MeeusSolarEngine.to_julian_day(dt)
    assert jd == pytest.approx(2451545.0)
    assert MeeusSolarEngine.to_julian_century(jd) == pytest.approx(0.0)


def test_naive_datetime_treated_as_utc() -> None:
    naive = datetime(2024, 6, 21, 12, 0, 0)
    aware = naive.replace(tzinfo=timezone.utc)
    assert MeeusSolarEngine.to_julian_day(naive) == MeeusSolarEngine.to_julian_day(aware)


def test_solar_coordinates_meeus_example_25a() -> None:
    """1992 October 13.0 TD (Meeus Example 25.a and 28.b)."""
    jd = MeeusSolarEngine.to_julian_day(datetime(1992, 10, 13, tzinfo=timezone.utc))
    assert jd == pytest.approx(2448908.5)

    t_century = MeeusSolarEngine.to_julian_century(jd)
    assert t_century == pytest.approx(-0.072183436, abs=1e-9)

    coords = MeeusSolarEngine._solar_coordinates(t_century)
    assert coords["l0"] == pytest.approx(201.80720, abs=1e-4)
    assert coords["m_deg"] == pytest.approx(278.99397, abs=1e-4)
    assert coords["eccentricity"] == pytest.approx(0.016711668, abs=1e-9)
    assert coords["true_longitude"] == pytest.approx(199.90988, abs=1e-4)
    assert coords["apparent_longitude"] == pytest.approx(199.90895, abs=1e-4)
    assert coords["distance_au"] == pytest.approx(0.99766, abs=1e-5)
    assert coords["right_ascension"] == pytest.approx(198.38083, abs=1e-3)
    assert coords["declination"] == pytest.approx(-7.78507, abs=1e-3)
    assert coords["equation_of_time"] == pytest.approx(13.71, abs=0.05)


def test_daily_events_are_ordered() -> None:
    engine = MeeusSolarEngine(*PARIS)
    data = engine.calculate(datetime(2024, 6, 21, 12, 0, tzinfo=timezone.utc))

    events = [
        data.nautical_dawn,
        data.civil_dawn,
        data.sunrise,
        data.solar_noon,
        data.sunset,
        data.civil_dusk,
        data.nautical_dusk,
    ]
    assert all(event is not None for event in events)
    assert events == sorted(events)


def test_paris_summer_solstice() -> None:
    """Paris, 2024-06-21: sunrise ≈ 03:47 UTC, sunset ≈ 19:58 UTC, ~16h10 of daylight."""
    engine = MeeusSolarEngine(*PARIS)
    data = engine.calculate(datetime(2024, 6, 21, 12, 0, tzinfo=timezone.utc))

    sunrise_min = data.sunrise.hour * 60 + data.sunrise.minute
    sunset_min = data.sunset.hour * 60 + data.sunset.minute
    assert sunrise_min == pytest.approx(3 * 60 + 47, abs=3)
    assert sunset_min == pytest.approx(19 * 60 + 58, abs=3)
    assert data.day_length_minutes == pytest.approx(16 * 60 + 10, abs=5)

    # Astronomical night never fully falls in Paris around the solstice
    assert data.astronomical_dawn is None
    assert data.astronomical_dusk is None

    # Sun is high in the southern sky shortly after local solar noon
    assert data.is_above_horizon
    assert data.true_elevation == pytest.approx(64.5, abs=1.0)
    assert 150.0 < data.azimuth < 210.0


def test_polar_night() -> None:
    engine = MeeusSolarEngine(*TROMSO)
    data = engine.calculate(datetime(2024, 12, 21, 12, 0, tzinfo=timezone.utc))

    assert data.sunrise is None
    assert data.sunset is None
    assert data.solar_noon is not None
    assert data.day_length_minutes == 0.0
    assert not data.is_above_horizon


def test_polar_day() -> None:
    engine = MeeusSolarEngine(*TROMSO)
    data = engine.calculate(datetime(2024, 6, 21, 0, 0, tzinfo=timezone.utc))

    assert data.sunrise is None
    assert data.sunset is None
    assert data.day_length_minutes == 1440.0
    # Midnight sun
    assert data.is_above_horizon


AUCKLAND = (-36.8485, 174.7633)
HONOLULU = (21.3069, -157.8583)


def test_events_use_local_day_east_of_greenwich() -> None:
    """08:00 NZST on 2024-06-21 is still 2024-06-20 in UTC."""
    nzst = timezone(timedelta(hours=12))
    engine = MeeusSolarEngine(*AUCKLAND)
    data = engine.calculate(datetime(2024, 6, 20, 20, 0, tzinfo=timezone.utc))

    # Sunrise ≈ 07:33 NZST, sunset ≈ 17:11 NZST on June 21
    assert data.sunrise.astimezone(nzst).date() == date(2024, 6, 21)
    assert data.sunset.astimezone(nzst).date() == date(2024, 6, 21)
    assert data.solar_noon.astimezone(nzst).date() == date(2024, 6, 21)


def test_events_use_local_day_west_of_greenwich() -> None:
    """18:00 HST on 2024-06-21 is already 2024-06-22 in UTC."""
    hst = timezone(timedelta(hours=-10))
    engine = MeeusSolarEngine(*HONOLULU)
    data = engine.calculate(datetime(2024, 6, 22, 4, 0, tzinfo=timezone.utc))

    # Sunrise ≈ 05:51 HST, sunset ≈ 19:16 HST on June 21
    assert data.sunrise.astimezone(hst).date() == date(2024, 6, 21)
    assert data.sunset.astimezone(hst).date() == date(2024, 6, 21)
    sunset_local = data.sunset.astimezone(hst)
    assert sunset_local.hour * 60 + sunset_local.minute == pytest.approx(19 * 60 + 16, abs=3)


def test_explicit_local_date_overrides_solar_day() -> None:
    engine = MeeusSolarEngine(*PARIS)
    dt = datetime(2024, 6, 21, 23, 30, tzinfo=timezone.utc)
    data = engine.calculate(dt, local_date=date(2024, 6, 22))
    assert data.sunrise.date() == date(2024, 6, 22)
