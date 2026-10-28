"""Tests that every entity is named in each translation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytest.importorskip(
    "pytest_homeassistant_custom_component",
    reason="requires pytest-homeassistant-custom-component (see requirements_test.txt)",
)

from custom_components.astraeos_helios.binary_sensor import BINARY_SENSOR_DESCRIPTION
from custom_components.astraeos_helios.sensor import SENSOR_TYPES

TRANSLATIONS = (
    Path(__file__).resolve().parents[1]
    / "custom_components"
    / "astraeos_helios"
    / "translations"
)
LANGUAGES = ("en", "fr")


def _load(language: str) -> dict:
    return json.loads((TRANSLATIONS / f"{language}.json").read_text(encoding="utf-8"))


def _key_paths(node: dict, prefix: str = "") -> set[str]:
    paths = set()
    for key, value in node.items():
        path = f"{prefix}{key}"
        paths.add(path)
        if isinstance(value, dict):
            paths |= _key_paths(value, f"{path}.")
    return paths


@pytest.mark.parametrize("language", LANGUAGES)
def test_every_entity_has_a_name(language: str) -> None:
    """A translation_key missing here leaves the entity without its own name."""
    entity = _load(language)["entity"]
    for description in SENSOR_TYPES:
        assert entity["sensor"].get(description.translation_key, {}).get("name"), (
            description.translation_key
        )
    assert entity["binary_sensor"][BINARY_SENSOR_DESCRIPTION.translation_key]["name"]


def test_languages_have_the_same_keys() -> None:
    reference, *others = LANGUAGES
    for language in others:
        assert _key_paths(_load(language)) == _key_paths(_load(reference)), language
