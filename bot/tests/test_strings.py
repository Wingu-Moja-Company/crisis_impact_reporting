from bot.i18n.strings import t, STRINGS

UN_LANGUAGES = ["ar", "zh", "en", "fr", "ru", "es"]


def test_all_keys_have_english_fallback():
    for key in STRINGS:
        assert "en" in STRINGS[key], f"Missing English for key: {key}"


def test_all_keys_have_all_languages():
    for key in STRINGS:
        for lang in UN_LANGUAGES:
            assert lang in STRINGS[key], f"Missing '{lang}' for key: {key}"


def test_t_falls_back_to_english_for_unknown_lang():
    result = t("welcome", "xx")
    assert result == STRINGS["welcome"]["en"]


def test_t_formats_placeholders():
    result = t("confirm", "en", report_id="rpt_123", map_url="https://example.com")
    assert "rpt_123" in result
    assert "https://example.com" in result
