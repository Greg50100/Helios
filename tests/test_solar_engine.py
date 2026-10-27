"""Tests for the solar engine, using worked examples from Astronomical Algorithms."""

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
    / "astraeos_helios"
    / "solar_engine.py"
)
_spec = importlib.util.spec_from_file_location("solar_engine", _MODULE_PATH)
solar_engine = importlib.util.module_from_spec(_spec)
sys.modules["solar_engine"] = solar_engine
_spec.loader.exec_module(solar_engine)

SolarEngine = solar_engine.SolarEngine

PARIS = (48.8566, 2.3522)
TROMSO = (69.6492, 18.9553)


def test_julian_day_meeus_example_7a() -> None:
    """1957 October 4.81 UT → JD 2436116.31 (Meeus Example 7.a)."""
    dt = datetime(1957, 10, 4, 19, 26, 24, tzinfo=timezone.utc)
    assert SolarEngine.to_julian_day(dt) == pytest.approx(2436116.31, abs=1e-6)


def test_julian_day_j2000() -> None:
    """J2000.0 epoch is JD 2451545.0 and T = 0."""
    dt = datetime(2000, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    jd = SolarEngine.to_julian_day(dt)
    assert jd == pytest.approx(2451545.0)
    assert SolarEngine.to_julian_century(jd) == pytest.approx(0.0)


def test_naive_datetime_treated_as_utc() -> None:
    naive = datetime(2024, 6, 21, 12, 0, 0)
    aware = naive.replace(tzinfo=timezone.utc)
    assert SolarEngine.to_julian_day(naive) == SolarEngine.to_julian_day(aware)


def test_solar_coordinates_meeus_example_25a() -> None:
    """1992 October 13.0 TD (Meeus Example 25.a and 28.b)."""
    jd = SolarEngine.to_julian_day(datetime(1992, 10, 13, tzinfo=timezone.utc))
    assert jd == pytest.approx(2448908.5)

    t_century = SolarEngine.to_julian_century(jd)
    assert t_century == pytest.approx(-0.072183436, abs=1e-9)

    coords = SolarEngine._solar_coordinates(t_century)
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
    engine = SolarEngine(*PARIS)
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
    engine = SolarEngine(*PARIS)
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
    engine = SolarEngine(*TROMSO)
    data = engine.calculate(datetime(2024, 12, 21, 12, 0, tzinfo=timezone.utc))

    assert data.sunrise is None
    assert data.sunset is None
    assert data.solar_noon is not None
    assert data.day_length_minutes == 0.0
    assert not data.is_above_horizon


def test_polar_day() -> None:
    engine = SolarEngine(*TROMSO)
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
    engine = SolarEngine(*AUCKLAND)
    data = engine.calculate(datetime(2024, 6, 20, 20, 0, tzinfo=timezone.utc))

    # Sunrise ≈ 07:33 NZST, sunset ≈ 17:11 NZST on June 21
    assert data.sunrise.astimezone(nzst).date() == date(2024, 6, 21)
    assert data.sunset.astimezone(nzst).date() == date(2024, 6, 21)
    assert data.solar_noon.astimezone(nzst).date() == date(2024, 6, 21)


def test_events_use_local_day_west_of_greenwich() -> None:
    """18:00 HST on 2024-06-21 is already 2024-06-22 in UTC."""
    hst = timezone(timedelta(hours=-10))
    engine = SolarEngine(*HONOLULU)
    data = engine.calculate(datetime(2024, 6, 22, 4, 0, tzinfo=timezone.utc))

    # Sunrise ≈ 05:51 HST, sunset ≈ 19:16 HST on June 21
    assert data.sunrise.astimezone(hst).date() == date(2024, 6, 21)
    assert data.sunset.astimezone(hst).date() == date(2024, 6, 21)
    sunset_local = data.sunset.astimezone(hst)
    assert sunset_local.hour * 60 + sunset_local.minute == pytest.approx(19 * 60 + 16, abs=3)


def test_explicit_local_date_overrides_solar_day() -> None:
    engine = SolarEngine(*PARIS)
    dt = datetime(2024, 6, 21, 23, 30, tzinfo=timezone.utc)
    data = engine.calculate(dt, local_date=date(2024, 6, 22))
    assert data.sunrise.date() == date(2024, 6, 22)


REYKJAVIK = (64.15, -21.94)
APIA = (-13.83, -171.76)
KIRITIMATI = (1.87, -157.43)

EVENT_ATTRS = (
    "astronomical_dawn",
    "nautical_dawn",
    "civil_dawn",
    "sunrise",
    "solar_noon",
    "sunset",
    "civil_dusk",
    "nautical_dusk",
    "astronomical_dusk",
)


def test_dusk_after_civil_midnight_stays_current() -> None:
    """Reykjavik (UTC+0), 2024-06-21: the Sun sets at 00:04 on June 22."""
    engine = SolarEngine(*REYKJAVIK)
    sunset = engine.calculate(datetime(2024, 6, 21, 13, 0, tzinfo=timezone.utc)).sunset
    assert sunset.date() == date(2024, 6, 22)

    # Past civil midnight, the sunset still to come must still be the one shown
    after_midnight = datetime(2024, 6, 22, 0, 1, tzinfo=timezone.utc)
    assert engine.calculate(after_midnight).sunset == sunset


@pytest.mark.parametrize(
    "coordinates",
    [PARIS, TROMSO, REYKJAVIK, AUCKLAND, HONOLULU, APIA],
    ids=["paris", "tromso", "reykjavik", "auckland", "honolulu", "apia"],
)
def test_every_event_is_current_when_it_happens(
    coordinates: tuple[float, float],
) -> None:
    """Each event is shown right before it happens, so time triggers fire."""
    engine = SolarEngine(*coordinates)
    margin = timedelta(seconds=1)
    for day in range(0, 366, 5):
        moment = datetime(2024, 1, 1, tzinfo=timezone.utc) + timedelta(days=day)
        data = engine.calculate(engine.calculate(moment).solar_noon)
        for attr in EVENT_ATTRS:
            event = getattr(data, attr)
            if event is None:
                continue
            assert getattr(engine.calculate(event - margin), attr) == event
            assert getattr(engine.calculate(event + margin), attr) == event


@pytest.mark.parametrize(
    ("coordinates", "utc_offset"),
    [(APIA, 13), (KIRITIMATI, 14)],
    ids=["apia", "kiritimati"],
)
def test_events_on_local_day_across_the_date_line(
    coordinates: tuple[float, float], utc_offset: int
) -> None:
    """Samoa and Kiribati use a time zone a day ahead of their longitude."""
    zone = timezone(timedelta(hours=utc_offset))
    engine = SolarEngine(*coordinates)
    data = engine.calculate(datetime(2024, 6, 21, 10, 0, tzinfo=zone))

    for event in (data.sunrise, data.solar_noon, data.sunset):
        assert event.astimezone(zone).date() == date(2024, 6, 21)


def test_apparent_elevation_is_continuous_and_increasing() -> None:
    """No jump at the -1° limit of Saemundsson's formula (Meeus Chapter 16)."""
    limit = SolarEngine.REFRACTION_FORMULA_LIMIT
    refraction = SolarEngine._refraction
    assert refraction(limit - 1e-9) == pytest.approx(refraction(limit), abs=1e-6)

    altitudes = [h / 100.0 for h in range(-9000, 9001)]
    apparent = [h + refraction(h) for h in altitudes]
    assert all(low < high for low, high in zip(apparent, apparent[1:]))

    # About 34' when the Sun's centre appears on the horizon, fading far below it
    assert refraction(-0.57) * 60.0 == pytest.approx(34.0, abs=1.0)
    assert refraction(-18.0) < 0.05


def test_day_length_matches_sunrise_and_sunset() -> None:
    engine = SolarEngine(*PARIS)
    for day in range(0, 366, 7):
        moment = datetime(2024, 1, 1, 12, tzinfo=timezone.utc) + timedelta(days=day)
        data = engine.calculate(moment)
        expected = (data.sunset - data.sunrise).total_seconds() / 60.0
        assert data.day_length_minutes == pytest.approx(expected, abs=0.01)


@pytest.mark.parametrize("elevation", [0.0, 1000.0])
def test_day_length_around_polar_day_and_night(elevation: float) -> None:
    """Tromsø, 2024: day length agrees with the events of each solar day."""
    engine = SolarEngine(*TROMSO, elevation_meters=elevation)
    seen = set()
    for day in range(366):
        moment = datetime(2024, 1, 1, 11, tzinfo=timezone.utc) + timedelta(days=day)
        data = engine.calculate(moment)
        if data.sunrise is not None and data.sunset is not None:
            seen.add("rise and set")
            expected = (data.sunset - data.sunrise).total_seconds() / 60.0
            assert data.day_length_minutes == pytest.approx(expected, abs=0.01)
        elif data.sunrise is None and data.sunset is None:
            seen.add("neither")
            expected = 1440.0 if data.is_above_horizon else 0.0
            assert data.day_length_minutes == expected
        else:
            # Midnight sun starts or ends: up until (or from) solar midnight
            seen.add("only one")
            assert 0.0 < data.day_length_minutes < 1440.0
    assert seen == {"rise and set", "neither", "only one"}


def test_above_horizon_switches_at_sunrise_and_sunset_far_north() -> None:
    """Tromsø, 2024-08-10: counting refraction twice put it 3 min early/late."""
    engine = SolarEngine(*TROMSO)
    day = engine.calculate(datetime(2024, 8, 10, 11, 0, tzinfo=timezone.utc))
    margin = timedelta(seconds=60)

    assert not engine.calculate(day.sunrise - margin).is_above_horizon
    assert engine.calculate(day.sunrise + margin).is_above_horizon
    assert engine.calculate(day.sunset - margin).is_above_horizon
    assert not engine.calculate(day.sunset + margin).is_above_horizon


def test_horizon_dip() -> None:
    assert SolarEngine.horizon_dip(0.0) == 0.0
    # Below sea level (Dead Sea shore): the horizon is not lowered
    assert SolarEngine.horizon_dip(-430.0) == 0.0
    # 1.76' × √100 = 17.6'
    assert SolarEngine.horizon_dip(100.0) == pytest.approx(17.6 / 60.0)


def test_elevation_lengthens_the_day() -> None:
    """At 1000 m the Sun rises earlier and sets later; twilights are unchanged."""
    dt = datetime(2024, 3, 20, 12, 0, tzinfo=timezone.utc)
    sea_level = SolarEngine(*PARIS).calculate(dt)
    summit = SolarEngine(*PARIS, elevation_meters=1000.0).calculate(dt)

    sunrise_shift = (sea_level.sunrise - summit.sunrise).total_seconds() / 60.0
    sunset_shift = (summit.sunset - sea_level.sunset).total_seconds() / 60.0
    assert sunrise_shift == pytest.approx(5.6, abs=0.2)
    assert sunset_shift == pytest.approx(5.6, abs=0.2)
    assert summit.day_length_minutes - sea_level.day_length_minutes == pytest.approx(
        sunrise_shift + sunset_shift, abs=0.5
    )

    assert summit.solar_noon == sea_level.solar_noon
    assert summit.civil_dawn == sea_level.civil_dawn
    assert summit.civil_dusk == sea_level.civil_dusk


@pytest.mark.parametrize("elevation", [0.0, 1000.0])
def test_above_horizon_matches_sunrise_and_sunset(elevation: float) -> None:
    engine = SolarEngine(*PARIS, elevation_meters=elevation)
    day = engine.calculate(datetime(2024, 6, 21, 12, 0, tzinfo=timezone.utc))
    margin = timedelta(seconds=30)

    assert not engine.calculate(day.sunrise - margin).is_above_horizon
    assert engine.calculate(day.sunrise + margin).is_above_horizon
    assert engine.calculate(day.sunset - margin).is_above_horizon
    assert not engine.calculate(day.sunset + margin).is_above_horizon
