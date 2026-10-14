import asyncio
import json

import httpx
import pytest
from pydantic import ValidationError

from jobfinder.discovery import SearchConfig, canonical_url, discover, matches
from jobfinder.cli import csv_value, main, write_results
from jobfinder.sources import ashby, greenhouse, lever


@pytest.fixture
def mock_http(monkeypatch):
    def handler(request):
        host = request.url.host
        if "broken" in request.url.path:
            return httpx.Response(429)
        if "empty" in request.url.path:
            return httpx.Response(200, json={"jobs": []})
        if host == "boards-api.greenhouse.io":
            return httpx.Response(200, json={"jobs": [
                {"id": 1, "title": "Software Engineer", "location": {"name": "Remote"}, "absolute_url": "https://example.org/jobs/1", "content": "<p>Build things</p>"},
                {"id": 2, "title": "Finance Analyst", "location": {"name": "London"}, "absolute_url": "https://example.org/jobs/2"},
            ]})
        if host == "api.lever.co":
            return httpx.Response(200, json=[{"id": "x", "text": "Software Engineer", "categories": {"location": "Remote"}, "hostedUrl": "https://example.org/jobs/1"}])
        if host == "api.ashbyhq.com":
            return httpx.Response(200, json={"jobs": [{"id": "a", "title": "Designer", "location": "Paris", "jobUrl": "https://example.org/jobs/3"}]})
        raise AssertionError(f"Unexpected request: {request.url}")

    for module in (greenhouse, lever, ashby):
        monkeypatch.setattr(module, "retrying_transport", lambda: httpx.MockTransport(handler))


def config(**kwargs):
    return SearchConfig(boards=[
        {"company": "Acme", "ats": "greenhouse", "slug": "acme"},
        {"company": "Beta", "ats": "lever", "slug": "beta"},
        {"company": "Gamma", "ats": "ashby", "slug": "gamma"},
    ], **kwargs)


def test_generic_search_and_duplicate_urls(mock_http):
    report = asyncio.run(discover(config(keywords=["software"], locations=["remote"])))
    assert report["complete"]
    assert len(report["jobs"]) == 1
    assert report["jobs"][0]["title"] == "Software Engineer"
    assert [item["fetched"] for item in report["sources"]] == [2, 1, 1]


def test_empty_filters_include_all_professions(mock_http):
    report = asyncio.run(discover(config()))
    assert {job["title"] for job in report["jobs"]} == {"Software Engineer", "Finance Analyst", "Designer"}


def test_failure_and_empty_are_distinct(mock_http):
    settings = config()
    settings.boards[0].slug = "broken"
    settings.boards[2].slug = "empty"
    report = asyncio.run(discover(settings))
    assert report["complete"] is False
    assert [item["status"] for item in report["sources"]] == ["error", "success", "empty"]
    assert "429" in report["sources"][0]["error"]
    assert len(report["jobs"]) == 1


def test_filters_have_no_finance_fallback():
    assert not matches("Finance Analyst", ["software"])
    assert matches("SOFTWARE Engineer", ["software"])
    assert matches("Any title", [])


def test_configuration_rejects_invalid_boards():
    with pytest.raises(ValidationError):
        SearchConfig(boards=[])
    with pytest.raises(ValidationError):
        SearchConfig(boards=[{"company": "Acme", "ats": "greenhouse", "slug": "../private"}])


def test_exports_escape_remote_content(mock_http, tmp_path):
    report = asyncio.run(discover(config()))
    report["jobs"][0]["title"] = '<script>alert("x")</script>'
    report["jobs"][0]["apply_url"] = 'javascript:alert(1)'
    write_results(report, tmp_path)
    page = (tmp_path / "jobs.html").read_text(encoding="utf-8")
    assert "<script>" not in page
    assert "javascript:" not in page
    assert "&lt;script&gt;" in page
    assert len(json.loads((tmp_path / "jobs.json").read_text(encoding="utf-8"))["jobs"]) == 3
    assert (tmp_path / "jobs.csv").exists()
    assert csv_value("=1+1") == "'=1+1"


def test_query_parameters_distinguish_openings():
    assert canonical_url("https://example.org/jobs?id=1") != canonical_url("https://example.org/jobs?id=2")


def test_cli_complete_and_partial(mock_http, tmp_path, monkeypatch):
    path = tmp_path / "config.yaml"
    path.write_text("boards:\n  - company: Acme\n    ats: greenhouse\n    slug: acme\n", encoding="utf-8")
    monkeypatch.setattr("sys.argv", ["jobfinder", "--config", str(path), "--keyword", "software", "--output", str(tmp_path / "out")])
    assert main() == 0
    result = json.loads((tmp_path / "out/jobs.json").read_text(encoding="utf-8"))
    assert len(result["jobs"]) == 1
    path.write_text("boards:\n  - company: Acme\n    ats: greenhouse\n    slug: broken\n", encoding="utf-8")
    assert main() == 2
