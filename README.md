# envdiff

Compare two `.env` files or environment snapshots — report **added**, **removed**,
and **changed** variables with clear diff-style output.

## About

`envdiff` fills a gap between reading `.env` files and actively comparing them.
It parses two sources (files or the current process environment), computes the
diff, and presents added/removed/changed variables in either human-readable text
or machine-readable JSON.

This is useful for:
- Comparing a `.env.example` against a deployed `.env`
- Auditing what changed between environment snapshots
- Detecting drift between local and production environment files
- CI checks that fail when environment files diverge

## Installation

```bash
python -m pip install -e .
```

## Usage

Compare two `.env` files:

```bash
envdiff .env.base .env.current
```

Output (text mode):

```
envdiff: .env.base -> .env.current
--- ADDED ---
+ NEW_VAR=hello
--- REMOVED ---
- OLD_VAR=world
--- CHANGED ---
~ CHANGED_VAR
  - old value
  + new value
```

JSON output:

```bash
envdiff --format json .env.base .env.current
# or
envdiff --json .env.base .env.current
```

Compare current environment against a saved file:

```bash
envdiff --current-env .env.saved
```

Exit codes:

- `0` — no differences found
- `1` — differences found (added, removed, or changed variables)
- `2` — file not found or unreadable

## Project structure

```
envdiff
├── README.md
├── pyproject.toml
├── envdiff.py
└── tests
    └── test_envdiff.py
```

## Tech stack

- Python 3.11+
- stdlib only (`argparse`, `json`, `os`, `sys`, `pathlib`)
- `pytest` for tests
- `ruff` for linting

## Tags / keywords

env, dotenv, diff, compare, environment, config, cli, python
