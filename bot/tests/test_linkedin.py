import pytest
from linkedin_client import _apply_mentions, KNOWN_MENTIONS


# --- _apply_mentions ---

def test_known_mention_replaced():
    text = "Excited to be part of @Ironhack!"
    result = _apply_mentions(text)
    assert result == "Excited to be part of @[Ironhack](urn:li:organization:3297892)!"


def test_known_mention_case_insensitive():
    result = _apply_mentions("Thanks @ironhack for the opportunity.")
    assert "urn:li:organization:3297892" in result


def test_unknown_mention_unchanged():
    text = "Thanks @SomeRandomCompany for the chat."
    result = _apply_mentions(text)
    assert result == text


def test_no_mentions_unchanged():
    text = "Great day at the office today!"
    assert _apply_mentions(text) == text


def test_multiple_mentions_mixed():
    text = "@Ironhack and @Unknown both attended."
    result = _apply_mentions(text)
    assert "urn:li:organization:3297892" in result
    assert "@Unknown" in result


def test_known_mentions_dict_has_urns():
    for name, urn in KNOWN_MENTIONS.items():
        assert urn.startswith("urn:li:"), f"{name} has invalid URN format: {urn}"
        assert name == name.lower(), f"Key '{name}' must be lowercase"


def test_ltf_format_correct():
    result = _apply_mentions("@Ironhack")
    assert result == "@[Ironhack](urn:li:organization:3297892)"
