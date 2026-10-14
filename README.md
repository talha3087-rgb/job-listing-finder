# Job Listing Finder

Find job listings across public employer boards, filter by role and location, and browse the results with direct application links. Runs locally on Windows, macOS, and Linux. No account or API key required.

This is a standalone discovery edition extracted from a personal job-search project. It supports any profession and location through configuration. It includes no candidate profile, CV, mailbox integration, or application history.

## Quick start

Requires Python 3.10 or newer and Git.

```sh
git clone https://github.com/talha3087-rgb/job-listing-finder.git
cd job-listing-finder
python -m venv .venv
```

Activate the environment on Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

On macOS or Linux:

```sh
source .venv/bin/activate
```

Install, create a configuration, and run a search:

```sh
python -m pip install -e .
python -c "from shutil import copyfile; copyfile('config.example.yaml', 'config.yaml')"
jobfinder
```

Open `results/jobs.html` in your browser. Each listing links to the employer's posting. The same run also produces `results/jobs.csv` for spreadsheets and `results/jobs.json` for scripts, including source status and the search time in UTC.

You can use `python -m jobfinder` instead of `jobfinder`.

## Choose your search

Edit `config.yaml`:

```yaml
keywords:
  - accountant
  - financial analyst
locations:
  - London
  - Remote
boards:
  - company: Stripe
    ats: greenhouse
    slug: stripe
concurrency: 3
```

Title terms use case-insensitive substring matching. A listing must match at least one title term and at least one location term. An empty list disables that filter. Remote listings pass only when their location text matches your location filter, or when you leave the location filter empty. Keywords are matched against titles, so benefits text cannot accidentally pull an unrelated role into your results.

Override filters for one run:

```sh
jobfinder --keyword "product manager" --keyword "designer" --location "New York"
jobfinder --config config.yaml --output results/design
```

## Add employers

Use an employer's public careers link to find the board name:

| Source | Public careers URL | Configuration |
| --- | --- | --- |
| Greenhouse | `boards.greenhouse.io/stripe` or `job-boards.greenhouse.io/stripe` | `ats: greenhouse`, `slug: stripe` |
| Lever | `jobs.lever.co/spotify` | `ats: lever`, `slug: spotify` |
| Ashby | `jobs.ashbyhq.com/openai` | `ats: ashby`, `slug: openai` |

Add an entry under `boards` with `company`, `ats`, and `slug`. The example configuration contains sample boards whose availability may change. This tool searches only the boards you configure. It does not search every employer or job board on the internet. Regional Lever endpoints and custom career sites are not supported in this release.

## Understand the results

- `success`: the board returned listings. Your filters may still match zero.
- `empty`: the board returned no listings. Some APIs also return empty data for an unknown board, so check its public careers page.
- `error`: a network request or response failed. Other boards still return results.

The command exits with `0` when every board responded, `2` when results are partial, and `1` for configuration or output errors. JSON includes `complete` and per-board counts. The HTML report shows source failures alongside listings.

Listings are deduplicated by application URL. Separate URLs remain separate openings. Results are snapshots, so check the employer page before applying. Posted dates and salaries may be absent when the source does not supply them. Matching does not infer eligibility, visa status, or professional fit.

## Public-source use

The included adapters use public Greenhouse, Lever, and Ashby job-board endpoints. Use them within each service's terms and applicable limits. Concurrency defaults to three requests and is capped at five. Connection failures have bounded retries; HTTP errors such as `429` are reported without repeated HTTP retries. Run searches at a reasonable interval.

The tool does not log in, collect account cookies, or submit applications. Apply through the employer link yourself. Local configuration and generated results are ignored by Git.

## Development

```sh
python -m pip install -e ".[dev]"
python -m pytest -q
```

Tests use mocked HTTP responses and do not depend on live job availability. GitHub Actions runs them on Windows and Ubuntu with Python 3.10 and 3.12.

The `jobfinder/sources/` adapters and posting model were adapted from the original project's discovery code. The CLI, generic filters, portable exports, and isolated tests are provided for this public edition. The original finance scoring and application copilot are outside this repository's scope.

See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidance. Licensed under [MIT](LICENSE).
