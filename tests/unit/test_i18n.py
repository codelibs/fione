import pytest

from api_helpers import add_user
from fione import i18n
from fione.auth.roles import Role
from fione.i18n import parse_accept_language, resolve_language, t


def test_catalogs_have_the_same_keys():
    en, ja = i18n.catalog("en"), i18n.catalog("ja")
    assert set(en) - set(ja) == set()
    assert set(ja) - set(en) == set()


def test_catalogs_are_plain_non_empty_text():
    for lang in i18n.LANGUAGES:
        for key, text in i18n.catalog(lang).items():
            assert isinstance(text, str) and text.strip(), (lang, key)
            assert "<" not in text and ">" not in text, (lang, key)  # templates escape them


def test_same_placeholders_in_both_languages():
    import string

    fields = lambda text: {f for _, f, _, _ in string.Formatter().parse(text) if f}  # noqa: E731
    en, ja = i18n.catalog("en"), i18n.catalog("ja")
    for key in en:
        assert fields(en[key]) == fields(ja[key]), key


def test_translates():
    assert t("login.submit", "en") == "Sign in"
    assert t("login.submit", "ja") == "ログイン"


def test_missing_japanese_key_falls_back_to_english(monkeypatch):
    monkeypatch.setitem(i18n.catalog("en"), "only.en", "English only")
    assert t("only.en", "ja") == "English only"


def test_missing_key_everywhere_is_the_key_itself():
    assert t("no.such.key", "ja") == "no.such.key"
    assert t("no.such.key", "en", name="x") == "no.such.key"


def test_unknown_language_is_english():
    assert t("login.submit", "fr") == "Sign in"


def test_interpolates_variables():
    assert t("user.signed_in_as", "en", username="alice") == "Signed in as alice"
    assert t("user.signed_in_as", "ja", username="alice") == "alice としてログイン中"


def test_bad_variables_never_raise(monkeypatch):
    monkeypatch.setitem(i18n.catalog("en"), "broken", "a {name} b {")
    assert t("broken", "en", name="x") == "a {name} b {"
    assert t("user.signed_in_as", "en", other="x") == "Signed in as {username}"
    monkeypatch.setitem(i18n.catalog("en"), "positional", "{0}")
    assert t("positional", "en", name="x") == "{0}"


@pytest.mark.parametrize(
    "header,expected",
    [
        (None, None),
        ("", None),
        ("ja", "ja"),
        ("ja-JP", "ja"),
        ("JA-jp", "ja"),
        ("en-US,en;q=0.9", "en"),
        ("fr-FR,fr;q=0.9,ja;q=0.8,en;q=0.7", "ja"),
        ("en;q=0.5,ja;q=0.8", "ja"),
        ("ja;q=0,en;q=0.1", "en"),
        ("ja;q=0", None),
        ("ja;q=abc,en;q=0.2", "en"),
        ("ja;q=2,en;q=0.2", "en"),
        ("en,ja", "en"),
        ("ja,en", "ja"),
        ("*", None),
        ("de, fr", None),
    ],
)
def test_accept_language(header, expected):
    assert parse_accept_language(header) == expected


def test_cookie_wins_over_header():
    assert resolve_language("en", "ja") == "en"
    assert resolve_language("ja", "en") == "ja"
    assert resolve_language("xx", "ja") == "ja"
    assert resolve_language(None, None) == "en"


def test_login_page_in_japanese(client):
    add_user(client, "admin", Role.ADMIN)
    r = client.get("/login", headers={"Accept-Language": "ja,en;q=0.5"})
    assert r.status_code == 200
    assert '<html lang="ja"' in r.text
    assert "Fione にログイン" in r.text and "ユーザー名" in r.text


def test_language_cookie_overrides_the_header(client):
    add_user(client, "admin", Role.ADMIN)
    client.cookies.set("fione_lang", "en")
    r = client.get("/login", headers={"Accept-Language": "ja"})
    assert '<html lang="en"' in r.text and "Sign in to Fione" in r.text
