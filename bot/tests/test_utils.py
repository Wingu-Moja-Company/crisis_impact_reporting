from bot.utils import detect_un_language


def test_known_un_language():
    assert detect_un_language("fr") == "fr"
    assert detect_un_language("ar") == "ar"
    assert detect_un_language("zh") == "zh"


def test_unmapped_language_falls_back_to_english():
    assert detect_un_language("sw") == "en"
    assert detect_un_language("pt") == "en"
    assert detect_un_language(None) == "en"


def test_full_locale_code_truncated():
    assert detect_un_language("fr-FR") == "fr"
    assert detect_un_language("zh-TW") == "zh"
