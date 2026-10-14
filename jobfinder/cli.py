"""Command line search and portable result exports."""
from __future__ import annotations

import argparse
import asyncio
import csv
import html
import json
import sys
from pathlib import Path
from urllib.parse import urlsplit

from jobfinder.discovery import discover, load_config


def safe_link(value: str) -> str:
    return html.escape(value, quote=True) if urlsplit(value).scheme in {"http", "https"} else "#"


def csv_value(value):
    # Spreadsheet apps may execute cells beginning with formula control characters.
    if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@")):
        return "'" + value
    return value


def write_results(report: dict, output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (output / "jobs.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    columns = ["title", "company", "location", "source", "apply_url", "posted_date", "salary"]
    with (output / "jobs.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerows({key: csv_value(job.get(key) or "") for key in columns} for job in report["jobs"])
    esc = html.escape
    cards = "".join(
        f'<article><h2><a href="{safe_link(job["apply_url"] or job["url"])}" target="_blank" rel="noopener noreferrer">{esc(job["title"])}</a></h2>'
        f'<p>{esc(job["company"])} &middot; {esc(job["location"])}</p><small>{esc(job["source"])}</small></article>'
        for job in report["jobs"]
    )
    sources = "".join(
        f'<li>{esc(item["company"])} ({esc(item["source"])}): {esc(item["status"])}; fetched {item["fetched"]}, matched {item["matched"]}'
        f'{": " + esc(item["error"]) if item.get("error") else ""}</li>' for item in report["sources"]
    )
    state = "All configured boards responded." if report["complete"] else "Partial results. Some boards failed. See source status below."
    page = f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Job Listing Finder</title><style>
body{{font:17px/1.6 system-ui,sans-serif;max-width:900px;margin:40px auto;padding:0 20px;background:#f5f7fa;color:#172338}}
h1{{line-height:1.15}}article{{background:white;border:1px solid #dbe2ec;border-radius:12px;padding:18px 24px;margin:16px 0}}h2{{font-size:21px;margin:0}}p{{margin:8px 0}}a{{color:#1256ad}}small{{color:#4b5c71}}li{{overflow-wrap:anywhere}}
</style><h1>Job Listing Finder</h1><p>{len(report["jobs"])} matching listings</p><p>{esc(state)}</p>
<small>Searched {esc(report["searched_at_utc"])}. Listings can close after this search.</small>
{cards or '<p>No matching listings returned.</p>'}<h2>Source status</h2><ul>{sources}</ul></html>'''
    (output / "jobs.html").write_text(page, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Find jobs on configured public employer boards.")
    parser.add_argument("--config", type=Path, default=Path("config.yaml"))
    parser.add_argument("--keyword", action="append", help="Repeat for multiple titles; overrides config keywords")
    parser.add_argument("--location", action="append", help="Repeat for multiple locations; overrides config locations")
    parser.add_argument("--output", type=Path, default=Path("results"))
    args = parser.parse_args()
    try:
        config = load_config(args.config)
        if args.keyword is not None:
            config.keywords = args.keyword
        if args.location is not None:
            config.locations = args.location
        report = asyncio.run(discover(config))
        write_results(report, args.output)
    except (ValueError, OSError) as exc:
        print(f"Search failed: {exc}", file=sys.stderr)
        return 1
    print(f'{len(report["jobs"])} listings. Results: {args.output.resolve() / "jobs.html"}')
    for source in report["sources"]:
        print(f'{source["company"]}: {source["status"]} ({source["fetched"]} fetched, {source["matched"]} matched)')
    return 0 if report["complete"] else 2
