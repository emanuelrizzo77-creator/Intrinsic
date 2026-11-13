# Archive

Earlier iterations of Intrinsic, kept for the record and **not used by the app or the tests**.

| Folder | What it holds |
|---|---|
| `legacy_modules/` | Models and helpers from milestones 12–26 (historical-median forecasts, Normalized v2, Hybrid 26C, Adaptive selector 26D, terminal-value experiments, a one-off NVIDIA balance patch). Replaced by the single driver model in `intrinsic/forecast.py`. |
| `legacy_tests/` | Unit tests for those modules. |
| `milestone_outputs/` | Coverage CSVs, diagnostic reports and backups produced along the way. |
| `diagnostics/` | Scripts used to inspect SEC XBRL tags (debt, D&A, leases, working capital). |
| `experiments/`, `old_dashboards/`, `old_backups/`, `pre_27/`, `screenshots_v1/` | Older experiments, dashboards and screenshots. |

Why the earlier forecasting approaches were dropped is documented in the main README
("What was tested and rejected").
