# GitHub Ready Checklist

Use this checklist before opening a PR or pushing release commits.

## 1) Clean Local Artifacts

```bash
cd /path/to/bench/apps/cold_storage
find . -type d -name "__pycache__" -prune -exec rm -rf {} +
find . -type f \( -name "*.pyc" -o -name "*.pyo" \) -delete
```

## 2) Validate Code Quality

```bash
cd /path/to/bench/apps/cold_storage
pre-commit run --all-files
```

## 3) Validate App Tests

```bash
cd /path/to/bench
bench --site <site-name> set-config allow_tests true
bench --site <site-name> run-tests --app cold_storage
```

## 4) Validate Migrate Path

```bash
cd /path/to/bench
bench --site <site-name> migrate
bench --site <site-name> clear-cache
```

## 5) Security Sanity Check

- Ensure no real tokens/secrets are committed.
- Never commit values from:
  - `whatsapp_access_token`
  - private API credentials
  - `.env` or local site config files

Quick scan:

```bash
cd /path/to/bench/apps/cold_storage
rg -n "Bearer\\s+|access[_-]?token|api[_-]?key|password\\s*=|secret" .
```

## 6) Final Git Hygiene

```bash
cd /path/to/bench/apps/cold_storage
git status
```

Before push, confirm:

- Only intended files are changed.
- New DocType/client script files are included.
- README/CONTRIBUTING updates are included for any user-facing behavior changes.
- CI workflows are present in `.github/workflows/`.
