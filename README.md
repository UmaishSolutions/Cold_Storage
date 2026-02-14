# Cold Storage

Cold Storage is a Frappe/ERPNext app for service-based warehouse operations where inventory is stored for customers.

## Highlights

- Inward, outward, and transfer transaction flows
- Customer ownership enforcement on `Batch`
- Charge configuration and billing support
- Operational reports and dashboard charts
- Customer portal for stock, movements, invoices, and scoped reports
- Role/role-profile fixtures with customer-level permission automation

## Requirements

- Frappe Bench
- ERPNext (required app)
- Python `3.14+` (as configured in `pyproject.toml`)

## Installation

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app https://github.com/UmaishSolutions/Cold_Storage.git
bench --site <site-name> install-app cold_storage
bench --site <site-name> migrate
```

## Local Development

```bash
cd apps/cold_storage
pre-commit install
pre-commit run --all-files
```

Run tests:

```bash
cd $PATH_TO_YOUR_BENCH
bench --site <site-name> set-config allow_tests true
bench --site <site-name> run-tests --app cold_storage
```

## CI Workflows

- `CI`: installs app in a fresh bench and runs tests
- `Linters`: runs pre-commit, Semgrep rules, and dependency audit

## License

MIT. See `LICENSE` and `license.txt`.
