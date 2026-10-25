"""The EasyML wizard end to end, in a real browser against the Compose stack: the first
administrator (the ``admin`` fixture, through the first-admin page), a project, iris, the
analysis defaults, the 1-minute preset, Run, the live progress to the summary (the
``trained`` fixture), then the star rating, a new prediction and the serving card."""

import re

import pandas as pd
import pytest
from playwright.sync_api import expect

from e2e_helpers import sign_in, upload

pytestmark = pytest.mark.e2e


def test_the_wizard_trains_rates_predicts_and_offers_serving(stack, admin, trained, data, new_page):
    page = new_page()
    sign_in(page, admin.username, admin.password)
    page.goto(trained.job)  # the progress page of the finished run
    assert page.locator("[data-job-status=done]").count() == 1

    page.goto(trained.summary)
    stars = page.locator(".stars-lg[role=img]")
    n = int(stars.get_attribute("data-stars"))
    assert 1 <= n <= 5
    assert stars.get_attribute("aria-label") == f"{n} out of 5 stars"
    expect(stars).to_be_visible()  # what the user sees: n of the five stars filled
    expect(stars.locator(".star-on")).to_have_count(n)
    expect(stars.locator(".star-off")).to_have_count(5 - n)
    command = page.locator("#run-command").inner_text().strip()
    assert command.startswith("docker run ") and command.endswith(stack.serving_image)

    page.goto(trained.model + "/predict")
    upload(page, data["new"])
    page.wait_for_url("**/predict?dataset=*")
    page.click("form[data-run-form] button[type=submit]")
    page.wait_for_url("**/result", timeout=120_000)
    with page.expect_download() as caught:
        page.locator("a[download][href*='/download']").first.click()
    download = caught.value
    assert re.fullmatch(r"predict_.+\.csv", download.suggested_filename)
    frame = pd.read_csv(download.path())
    assert len(frame) == 3
    assert sorted(c for c in frame.columns if c.startswith("p_")) == [
        "p_setosa",
        "p_versicolor",
        "p_virginica",
    ]
