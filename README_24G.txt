INTRINSIC 24G — ADDITIVE FINANCIAL RESOLVER (SAFE STAGING)

This ZIP does NOT replace the dashboard or the existing 24E engine.
It introduces universal_financial_24g.assess_company, which calls 24E and
classifies a latest-year depreciation-only fallback as a PROXY, never as verified D&A.

Install from project root:
  unzip -o ~/Downloads/Intrinsic_24G_resolver.zip
  python -m unittest -v test_universal_financial_24g
  python intrinsic_24g_coverage.py

The coverage script accesses live SEC data and writes intrinsic_24g_coverage.csv.
The status PROVISIONAL_PROXY_SCENARIO_ONLY means a scenario may be constructed
with explicit assumptions; it is NOT an audited DCF or a completed dashboard integration.
The 23F dashboard remains unchanged. A separate DCF numerical parity test is
required before routing live valuations through 24G.
