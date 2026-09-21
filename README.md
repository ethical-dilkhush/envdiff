# envdiff

Diff environment variables across files or live process environments.

## About

`envdiff` compares two environment sources and reports additions, removals, and value changes.
It answers a simple operational question: *"What changed between these two env configs?"*

Useful for:
- Comparing `.env` files across staging, production, or deployments
- Auditing environment changes in pull requests
- Quickly inspecting differences before applying a migration or rollout

## Features

- Compare two `.env` files, a `.env` file vs the current process environment, or two live environments
- Plain text, Markdown, and JSON output formats
- Colorized terminal output with `--no-color` override
- Filter output to a single change type: `--only added|removed|changed|unchanged`
- Returns exit code `1` when differences are present and `0` when envs match
- Zero external dependencies: pure stdlib Python

## Installation

```bash
python -m pip install -e .
```

## Usage

```bash
# Compare two files
envdiff old.env new.env

# Compare a file against the live process environment
envdiff .env --live-new

# JSON output
envdiff old.env new.env --format json

# Markdown summary
envdiff old.env new.env --format markdown

# Show only added or removed keys
envdiff old.env new.env --only added
envdiff old.env new.env --only removed
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | No differences |
| 1 | Differences found |
| 2 | Usage or file error |

## Project Structure

```
envdiff/
  envdiff.py     # CLI and diff engine
  pyproject.toml # Packaging and script entrypoint
  tests/         # Ad-hoc verification tests
  README.md
```

## Tags

cli, envdiff, dotenv, configuration, diff, developer-tools, stdlib
