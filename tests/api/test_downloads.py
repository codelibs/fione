from fione.api.downloads import content_disposition


def test_a_zip_name_gets_one_extension_and_an_ascii_fallback():
    assert content_disposition("iris", ".zip", "model") == (
        "attachment; filename=\"iris.zip\"; filename*=UTF-8''iris.zip"
    )
    assert content_disposition("Iris.ZIP", ".zip", "model") == (
        "attachment; filename=\"Iris.zip\"; filename*=UTF-8''Iris.ZIP"
    )


def test_non_ascii_names_are_kept_only_in_the_rfc5987_form():
    header = content_disposition("売上 モデル", ".zip", "model")
    assert header == (
        'attachment; filename="model.zip"; '
        "filename*=UTF-8''%E5%A3%B2%E4%B8%8A%20%E3%83%A2%E3%83%87%E3%83%AB.zip"
    )


def test_quotes_and_line_breaks_cannot_reach_the_header():
    header = content_disposition('evil"\r\nSet-Cookie: x=1', ".zip", "model")
    assert "\r" not in header and "\n" not in header
    assert header.count('"') == 2
    assert header.startswith('attachment; filename="evil_Set-Cookie_x_1.zip"; filename*=')
    assert "%22%0D%0A" in header
