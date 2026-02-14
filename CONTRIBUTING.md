# Contributing

## Prerequisites

- Frappe Bench with ERPNext installed
- Python `3.14+`
- Node.js (for asset builds)

## Local Setup

```bash
cd $PATH_TO_BENCH
bench get-app --soft-link /path/to/Cold_Storage
bench --site <site-name> install-app cold_storage
bench --site <site-name> migrate
cd apps/cold_storage
pre-commit install
```

## Quality Checks

```bash
cd $PATH_TO_BENCH/apps/cold_storage
pre-commit run --all-files
```

Run tests:

```bash
cd $PATH_TO_BENCH
bench --site <site-name> set-config allow_tests true
bench --site <site-name> run-tests --app cold_storage
```

## Pull Request Guidelines

- Keep changes focused and atomic.
- Include tests for behavior changes.
- Document any new setup, fixtures, or patches.
- Ensure CI is green before requesting review.
