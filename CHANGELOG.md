# Changelog

All notable changes to this project are documented here.

## [Unreleased]

### Changed
- **Modular UI** — the monolithic `app.py` was split into a `views/` package
  with one render module per dashboard tab plus sidebar/header/styles; `app.py`
  is now a thin orchestrator.
- **Externalised network data** — production centres, warehouses, distances,
  tolls, cost parameters and scenarios now live in editable `network/` files
  (CSV + YAML) instead of being hardcoded. Overridable via `NETWORK_DIR` and
  per-parameter environment variables.
- **Pluggable solver** — new `solver.py` factory selects CBC or HiGHS through
  the `LP_SOLVER` environment variable (falls back to CBC).
- **Faster OSRM client** — real road distances now use a single `/table`
  request (was 40 sequential calls) with in-process caching.

### Added
- Ruff linting (`ruff.toml`) and pytest coverage, both wired into CI.
- FastAPI endpoint tests and solver tests (138 tests total).
- `requirements-dev.txt` for development/CI tooling.

### Removed
- Stopped tracking the 2.8 MB generated `report_ieee.pdf` (build locally from
  `report_ieee.tex`).
