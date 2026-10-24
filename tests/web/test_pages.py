"""The web UI's pages: redirects, auth screens, the home page, logout, language and the
security of the HTML (escaping, CSP, CSRF)."""

import re
from contextlib import closing
from html.parser import HTMLParser
from urllib.parse import parse_qs, urlsplit

import pytest

from api_helpers import PW, add_user, connect, login
from fione.auth import service as auth
from fione.auth.roles import ProjectAccess, Role
from fione.projects import service as projects

SETUP_TOKEN = "setup-token-for-tests-0123456789"
CSP = (
    "default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; "
    "frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
)


class Page(HTMLParser):
    """The tags and attributes of a page, for structural checks."""

    def __init__(self, html: str):
        super().__init__()
        self.tags: list[tuple[str, dict[str, str | None]]] = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        # A bare attribute (``<form data-json-form>``) reads as "".
        self.tags.append((tag, {k: "" if v is None else v for k, v in attrs}))

    def find(self, tag: str, **attrs) -> list[dict]:
        return [
            a for t, a in self.tags if t == tag and all(a.get(k) == v for k, v in attrs.items())
        ]


@pytest.fixture
def setup_client(make_client):
    """An install with no administrator yet."""
    return make_client(setup_token=SETUP_TOKEN)


@pytest.fixture
def admin_client(make_client):
    client = make_client()
    add_user(client, "admin", Role.ADMIN)
    return client


def make_project(client, owner, name):
    with closing(connect(client)) as conn:
        user = next(u for u in auth.list_users(conn) if u.username == owner)
        return projects.create_project(conn, user, name)


def location(response) -> str:
    assert response.status_code == 303, response.text
    return response.headers["location"]


def next_of(url: str) -> str:
    parts = urlsplit(url)
    assert parts.path == "/login"
    return parse_qs(parts.query)["next"][0]


# --- first admin -----------------------------------------------------------------------


def test_no_admin_sends_login_to_first_admin(setup_client):
    assert location(setup_client.get("/login", follow_redirects=False)) == "/first-admin"


def test_first_admin_page_says_where_the_token_is(setup_client):
    r = setup_client.get("/first-admin")
    assert r.status_code == 200
    assert "Create the administrator account" in r.text
    assert 'docker compose logs fione | grep "Setup token"' in r.text
    assert "FIONE_SETUP_TOKEN" in r.text
    page = Page(r.text)
    names = {a.get("name") for a in page.find("input")}
    assert {"setup_token", "username", "password"} <= names


def test_first_admin_page_in_japanese(setup_client):
    r = setup_client.get("/first-admin", headers={"Accept-Language": "ja"})
    assert "管理者アカウントの作成" in r.text
    assert 'docker compose logs fione | grep "Setup token"' in r.text
    assert "環境変数 FIONE_SETUP_TOKEN" in r.text


def test_first_admin_page_gone_once_an_admin_exists(admin_client):
    assert location(admin_client.get("/first-admin", follow_redirects=False)) == "/login"


def test_first_admin_page_posts_to_the_api(setup_client):
    form = Page(setup_client.get("/first-admin").text).find("form", **{"data-json-form": ""})
    assert form and form[0]["data-endpoint"] == "/api/v1/auth/first-admin"
    assert form[0]["data-next"] == "/"


# --- login and redirects ----------------------------------------------------------------


def test_login_page(admin_client):
    r = admin_client.get("/login")
    assert r.status_code == 200
    assert '<html lang="en"' in r.text
    assert "Sign in to Fione" in r.text
    form = Page(r.text).find("form", **{"data-json-form": ""})
    assert form and form[0]["data-endpoint"] == "/api/v1/auth/login"
    assert form[0]["data-next"] == "/"
    # One message for unknown users and wrong passwords alike.
    assert form[0]["data-error-invalid_credentials"] == "The username or password is incorrect."


@pytest.mark.parametrize("path", ["/", "/_design", "/?view=all"])
def test_pages_redirect_anonymous_users_to_login(admin_client, path):
    url = location(admin_client.get(path, follow_redirects=False))
    assert next_of(url) == path


def test_garbage_session_cookie_redirects_to_login(admin_client):
    admin_client.cookies.set("fione_session", "v1.junk.junk")
    assert next_of(location(admin_client.get("/", follow_redirects=False))) == "/"


@pytest.mark.parametrize(
    "target,expected",
    [
        ("/_design", "/_design"),
        ("/?a=1&b=2", "/?a=1&b=2"),
        ("//evil.example", "/"),
        ("/\\evil.example", "/"),
        ("/\t/evil.example", "/"),
        ("/\n/evil.example", "/"),
        ("https://evil.example/", "/"),
        ("javascript:alert(1)", "/"),
        ("evil.example", "/"),
        ("", "/"),
        ("/%2F%2Fevil.example", "/"),
        ("/%2f/evil.example", "/"),
        ("/%5Cevil.example", "/"),
        ("/%252F%252Fevil.example", "/"),
        ("/%25252F%25252Fevil.example", "/"),
        ("/%25255Cevil.example", "/"),
        ("/%09/evil.example", "/"),
        ("/?q=a%2Fb", "/?q=a%2Fb"),
    ],
)
def test_next_is_only_a_same_site_path(admin_client, target, expected):
    page = Page(admin_client.get("/login", params={"next": target}).text)
    assert page.find("form", **{"data-json-form": ""})[0]["data-next"] == expected
    login(admin_client, "admin")
    r = admin_client.get("/login", params={"next": target}, follow_redirects=False)
    assert location(r) == expected


def test_login_then_home(admin_client):
    login(admin_client, "admin")
    r = admin_client.get("/")
    assert r.status_code == 200
    assert "Signed in as admin" in r.text


# --- home ----------------------------------------------------------------------------------


def test_home_empty_state_and_create_form(admin_client):
    add_user(admin_client, "ed", Role.EDITOR)
    login(admin_client, "ed")
    r = admin_client.get("/")
    assert "No projects yet" in r.text
    form = Page(r.text).find("form", **{"hx-post": "/ui/projects"})
    assert form


def test_home_lists_visible_projects_only(admin_client):
    add_user(admin_client, "ed", Role.EDITOR)
    add_user(admin_client, "other", Role.EDITOR)
    make_project(admin_client, "ed", "Sales forecast")
    make_project(admin_client, "other", "Secret plans")
    login(admin_client, "ed")
    r = admin_client.get("/")
    assert "Sales forecast" in r.text
    assert "Secret plans" not in r.text
    assert "No projects yet" not in r.text
    assert "1 project" in r.text


def test_home_admin_sees_every_project_with_its_owner(admin_client):
    add_user(admin_client, "ed", Role.EDITOR)
    make_project(admin_client, "ed", "Sales forecast")
    login(admin_client, "admin")
    r = admin_client.get("/")
    assert "Sales forecast" in r.text and "Owner: ed" in r.text


def test_home_viewer_cannot_create(admin_client):
    add_user(admin_client, "ed", Role.EDITOR)
    add_user(admin_client, "vi", Role.VIEWER)
    project = make_project(admin_client, "ed", "Shared one")
    with closing(connect(admin_client)) as conn:
        ed = next(u for u in auth.list_users(conn) if u.username == "ed")
        projects.share_project(conn, ed, project.id, "vi", ProjectAccess.VIEWER)
    login(admin_client, "vi")
    r = admin_client.get("/")
    assert "Shared one" in r.text and "View only" in r.text
    assert "You have view-only access" in r.text
    assert not Page(r.text).find("form", **{"hx-post": "/ui/projects"})


def test_project_names_are_escaped(admin_client):
    make_project(admin_client, "admin", '<script>alert("x")</script>')
    login(admin_client, "admin")
    r = admin_client.get("/")
    assert '<script>alert("x")</script>' not in r.text
    assert "&lt;script&gt;alert(&#34;x&#34;)&lt;/script&gt;" in r.text


# --- creating a project through the HTMX endpoint -----------------------------------------


def hx(csrf: str | None) -> dict:
    headers = {"HX-Request": "true"}
    if csrf:
        headers["X-CSRF-Token"] = csrf
    return headers


def project_names(client) -> list[str]:
    with closing(connect(client)) as conn:
        return [p.name for p in projects.list_projects(conn, auth.list_users(conn)[0])]


def test_create_project(admin_client):
    csrf = login(admin_client, "admin")
    r = admin_client.post("/ui/projects", data={"name": "Churn <b>"}, headers=hx(csrf))
    assert r.status_code == 200
    assert project_names(admin_client) == ["Churn <b>"]
    assert "Churn &lt;b&gt;" in r.text and "Churn <b>" not in r.text
    assert 'hx-swap-oob="true"' in r.text  # the list is refreshed
    assert "was created" in r.text  # toast


def test_create_project_needs_the_csrf_header(admin_client):
    login(admin_client, "admin")
    r = admin_client.post("/ui/projects", data={"name": "x"}, headers=hx(None))
    assert r.status_code == 403
    assert project_names(admin_client) == []


def test_create_project_anonymous(admin_client):
    r = admin_client.post("/ui/projects", data={"name": "x"}, headers=hx("forged"))
    assert r.status_code == 401
    assert r.headers["HX-Redirect"] == "/login?next=%2F"


@pytest.mark.parametrize("name", ["", "   ", "x" * 101])
def test_create_project_invalid_name(admin_client, name):
    csrf = login(admin_client, "admin")
    r = admin_client.post("/ui/projects", data={"name": name}, headers=hx(csrf))
    assert r.status_code == 422
    assert "Enter a project name of 1 to 100 characters." in r.text
    assert project_names(admin_client) == []


def test_create_project_viewer_refused(admin_client):
    add_user(admin_client, "vi", Role.VIEWER)
    csrf = login(admin_client, "vi")
    r = admin_client.post("/ui/projects", data={"name": "x"}, headers=hx(csrf))
    assert r.status_code == 403
    assert "You do not have permission" in r.text
    assert project_names(admin_client) == []


def test_create_project_error_in_japanese(admin_client):
    csrf = login(admin_client, "admin")
    headers = {**hx(csrf), "Accept-Language": "ja"}
    r = admin_client.post("/ui/projects", data={"name": ""}, headers=headers)
    assert "プロジェクト名を 1〜100 文字で入力してください。" in r.text


# --- logout ------------------------------------------------------------------------------


def test_logout(admin_client):
    csrf = login(admin_client, "admin")
    r = admin_client.post("/logout", data={"csrf_token": csrf}, follow_redirects=False)
    assert location(r) == "/login"
    assert "fione_session=" in r.headers["set-cookie"]
    assert admin_client.get("/api/v1/auth/me").status_code == 401


def test_logout_needs_the_csrf_token(admin_client):
    login(admin_client, "admin")
    r = admin_client.post("/logout", data={"csrf_token": "wrong"}, follow_redirects=False)
    assert r.status_code == 403
    assert "fione_session" not in r.headers.get("set-cookie", "")
    assert admin_client.get("/api/v1/auth/me").status_code == 200


def test_logout_is_post_only(admin_client):
    login(admin_client, "admin")
    assert admin_client.get("/logout").status_code == 405


def test_logout_without_session_goes_to_login(admin_client):
    r = admin_client.post("/logout", data={"csrf_token": "x"}, follow_redirects=False)
    assert location(r) == "/login"


# --- language ------------------------------------------------------------------------------


def test_language_switch_sets_the_cookie(admin_client):
    r = admin_client.post("/ui/lang", data={"lang": "ja", "next": "/login"}, follow_redirects=False)
    assert location(r) == "/login"
    assert "fione_lang=ja" in r.headers["set-cookie"]
    r = admin_client.get("/login", headers={"Accept-Language": "en"})
    assert '<html lang="ja"' in r.text and "Fione にログイン" in r.text


@pytest.mark.parametrize(
    "target",
    [
        "//evil.example",
        "https://evil.example",
        "/\\x",
        "/%2F%2Fevil.example",
        "/%5Cevil.example",
        "/%252F%252Fevil.example",
        "/%25252F%25252Fevil.example",
        "/%25255Cevil.example",
    ],
)
def test_language_switch_next_stays_on_site(admin_client, target):
    r = admin_client.post("/ui/lang", data={"lang": "en", "next": target}, follow_redirects=False)
    assert location(r) == "/"


def test_language_switch_rejects_unknown_languages(admin_client):
    r = admin_client.post("/ui/lang", data={"lang": "fr", "next": "/"}, follow_redirects=False)
    assert r.status_code == 400
    assert "fione_lang" not in r.headers.get("set-cookie", "")


def test_language_switch_refuses_cross_origin(admin_client):
    r = admin_client.post(
        "/ui/lang",
        data={"lang": "ja", "next": "/"},
        headers={"Origin": "https://evil.example"},
        follow_redirects=False,
    )
    assert r.status_code == 403


def test_language_switch_form_points_back_here(admin_client):
    page = Page(admin_client.get("/login", params={"next": "/_design"}).text)
    form = page.find("form", action="/ui/lang")
    hidden = [a for t, a in page.tags if t == "input" and a.get("name") == "next"]
    assert form and hidden[0]["value"] == "/login?next=%2F_design"


# --- headers and HTML hygiene --------------------------------------------------------------


def all_pages(make_client):
    """(client, path) for every page, each in the state where it renders."""
    setup = make_client(tmp_dir_name="setup", setup_token=SETUP_TOKEN)
    yield setup, "/first-admin"
    client = make_client(tmp_dir_name="main")
    add_user(client, "admin", Role.ADMIN)
    yield client, "/login"
    login(client, "admin")
    make_project(client, "admin", "One")
    yield client, "/"
    yield client, "/_design"


@pytest.fixture
def pages(make_client, tmp_path):
    def factory(tmp_dir_name, **overrides):
        return make_client(tmp_path / tmp_dir_name, **overrides)

    return list(all_pages(factory))


def test_security_headers_on_pages(pages):
    for client, path in pages:
        r = client.get(path)
        assert r.status_code == 200, path
        assert r.headers["content-security-policy"] == CSP
        assert r.headers["x-content-type-options"] == "nosniff"
        assert r.headers["referrer-policy"] == "same-origin"
        assert r.headers["cache-control"] == "no-store"


def test_security_headers_on_redirects(admin_client):
    r = admin_client.get("/", follow_redirects=False)
    assert r.headers["content-security-policy"] == CSP
    assert r.headers["cache-control"] == "no-store"


def test_static_files_are_cacheable_but_nosniff(admin_client):
    r = admin_client.get("/static/css/app.css")
    assert r.status_code == 200
    assert r.headers["x-content-type-options"] == "nosniff"
    assert "no-store" not in r.headers.get("cache-control", "")


def test_api_responses_keep_their_headers(admin_client):
    r = admin_client.get("/api/v1/auth/status")
    assert "content-security-policy" not in r.headers
    assert "cache-control" not in r.headers


def test_no_inline_scripts_styles_or_handlers(pages):
    for client, path in pages:
        html = client.get(path).text
        for tag, attrs in Page(html).tags:
            if tag == "script":
                assert attrs.get("src", "").startswith("/static/"), (path, attrs)
            assert tag != "style", path
            assert "style" not in attrs, (path, tag, attrs)
            assert not [a for a in attrs if a.startswith("on")], (path, tag, attrs)
            assert not [a for a in attrs if a.startswith("hx-on")], (path, tag, attrs)


def test_static_references_resolve(pages):
    for client, path in pages:
        page = Page(client.get(path).text)
        refs = [a["src"] for _, a in page.tags if a.get("src")]
        refs += [a["href"] for t, a in page.tags if t == "link" and a.get("href")]
        assert refs, path
        for ref in refs:
            assert ref.startswith("/static/"), ref
            assert client.get(ref).status_code == 200, ref


def test_echarts_is_not_loaded_by_these_pages(pages):
    for client, path in pages:
        assert "echarts" not in client.get(path).text, path


def test_csrf_meta_only_when_logged_in(admin_client):
    page = Page(admin_client.get("/login").text)
    assert not page.find("meta", name="csrf-token")
    assert "hx-headers" not in dict(page.find("body")[0])
    csrf = login(admin_client, "admin")
    page = Page(admin_client.get("/").text)
    assert page.find("meta", name="csrf-token")[0]["content"] == csrf
    assert page.find("body")[0]["hx-headers"] == f'{{"X-CSRF-Token": "{csrf}"}}'
    assert page.find("input", name="csrf_token")[0]["value"] == csrf


def test_htmx_is_configured_for_the_csp(admin_client):
    meta = Page(admin_client.get("/login").text).find("meta", name="htmx-config")
    assert '"includeIndicatorStyles":false' in meta[0]["content"]
    assert '"allowEval":false' in meta[0]["content"]
    assert '"attributesToSettle":["class"]' in meta[0]["content"]


def test_html_lang_follows_the_language(admin_client):
    r = admin_client.get("/login", headers={"Accept-Language": "ja-JP"})
    assert re.search(r'<html lang="ja"', r.text)


def test_password_is_never_rendered(admin_client):
    login(admin_client, "admin")
    assert PW not in admin_client.get("/").text


# --- fix round 1 ----------------------------------------------------------------------------


@pytest.mark.parametrize("path,client_name", [("/login", "admin"), ("/first-admin", "setup")])
def test_auth_forms_post_so_nothing_lands_in_the_url(make_client, path, client_name):
    """Without JavaScript the native submit must not put the password in the URL: it is a
    POST (refused, 405), and the button only works once the script enables it."""
    client = make_client(setup_token=SETUP_TOKEN)
    if client_name == "admin":
        add_user(client, "admin", Role.ADMIN)
    page = Page(client.get(path).text)
    form = page.find("form", **{"data-json-form": ""})[0]
    assert form["method"] == "post"
    assert form["action"] == path
    assert "disabled" in page.find("button", type="submit")[-1]
    assert "noscript" in [t for t, _ in page.tags]
    assert client.post(path).status_code == 405


def test_login_does_not_echo_credentials_from_the_query(admin_client):
    r = admin_client.get("/login", params={"username": "x-user", "password": "secret-pw-9"})
    assert r.status_code == 200
    assert "secret-pw-9" not in r.text and "x-user" not in r.text


def test_first_admin_does_not_echo_the_query(setup_client):
    r = setup_client.get("/first-admin", params={"setup_token": "tok-123-xyz"})
    assert "tok-123-xyz" not in r.text


def test_noscript_note_in_both_languages(admin_client):
    assert "needs JavaScript" in admin_client.get("/login").text
    ja = admin_client.get("/login", headers={"Accept-Language": "ja"}).text
    assert "JavaScript を有効" in ja


def test_projects_newest_first_even_within_one_second(admin_client):
    for name in ("Charlie", "Alpha", "Bravo"):  # within one second: same created_at
        make_project(admin_client, "admin", name)
    login(admin_client, "admin")
    html = admin_client.get("/").text
    names = re.findall(r'<h3 class="project-card__name">([^<]+)</h3>', html)
    assert names == ["Bravo", "Alpha", "Charlie"]


def test_project_dates_say_utc(admin_client):
    project = make_project(admin_client, "admin", "Dated")
    login(admin_client, "admin")
    html = admin_client.get("/").text
    times = Page(html).find("time")
    assert times and times[0]["datetime"] == project.created_at.replace(" ", "T") + "Z"
    assert f"Created {project.created_at[:10]} UTC" in html


def test_invalid_project_name_is_announced(admin_client):
    csrf = login(admin_client, "admin")
    r = admin_client.post("/ui/projects", data={"name": " "}, headers=hx(csrf))
    page = Page(r.text)
    assert page.find("p", **{"class": "field__error", "role": "alert"})
    field = page.find("input", id="project-name")[0]
    assert "autofocus" in field and field["aria-invalid"] == "true"


def test_toast_templates_for_scripts(admin_client):
    """JS-built toasts clone server-rendered templates (same icon close button); a danger
    toast is an alert (and app.js never auto-dismisses it)."""
    login(admin_client, "admin")
    html = admin_client.get("/").text
    page = Page(html)
    kinds = {a.get("data-toast-template") for t, a in page.tags if t == "template"}
    assert kinds == {"success", "danger"}
    danger = html[html.index('data-toast-template="danger"') :]
    danger = danger[: danger.index("</template>")]
    assert 'role="alert"' in danger and "data-toast-close" in danger


def test_error_page_language_switch_goes_home(admin_client):
    login(admin_client, "admin")
    r = admin_client.post("/logout", data={"csrf_token": "wrong"})
    assert r.status_code == 403
    page = Page(r.text)
    hidden = [a for t, a in page.tags if t == "input" and a.get("name") == "next"]
    assert page.find("form", action="/ui/lang") and hidden[0]["value"] == "/"


def other_responses(client):
    """Responses that are not full GET pages: (label, response)."""
    csrf = login(client, "admin")
    yield "error page", client.post("/logout", data={"csrf_token": "wrong"})
    yield "created fragment", client.post("/ui/projects", data={"name": "p"}, headers=hx(csrf))
    yield "422 fragment", client.post("/ui/projects", data={"name": " "}, headers=hx(csrf))
    yield "htmx refusal", client.post("/ui/projects", data={"name": "p"}, headers=hx("bad"))
    yield "json 404", client.get("/no-such-page")


def test_security_headers_on_other_responses(admin_client):
    for label, r in other_responses(admin_client):
        assert r.headers["content-security-policy"] == CSP, label
        assert r.headers["x-content-type-options"] == "nosniff", label
        assert r.headers["referrer-policy"] == "same-origin", label
        assert r.headers["cache-control"] == "no-store", label
        for tag, attrs in Page(r.text).tags:
            assert tag != "style" and "style" not in attrs, (label, tag)
            assert not [a for a in attrs if a.startswith("on")], (label, tag)
            if tag == "script":
                assert attrs.get("src", "").startswith("/static/"), (label, attrs)
