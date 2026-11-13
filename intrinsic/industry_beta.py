"""Intrinsic 27 — bottom-up (industry) beta.

Why: a single stock's regression beta has a standard error of roughly 0.2-0.3, so
the WACC moves a lot on noise (AMD's raw Yahoo beta implied a 16.7% WACC). An
industry average of unlevered betas across many firms is far more precise; the
company's own financial leverage is then put back:

    beta_L = beta_U * (1 + (1 - t) * D / E)          (Hamada)

  beta_U  Damodaran US industry unlevered beta, CORRECTED FOR CASH
          (data/damodaran_us_industry_betas.csv, January 2026 update)
  D       total debt from the SEC balance (same figure used for WACC weights)
  E       market capitalisation
  t       marginal tax rate (MARGINAL_TAX, editable assumption)

The SIC -> industry crosswalk below is a classification table (economic
assumption), not an estimate. It is applied to every company the same way; no
ticker-specific entries. Matches are labelled:
  'specific'  the SIC range identifies the industry well
  'broad'     a catch-all SIC (e.g. 7389 "services NEC", 3990 "misc. manufacturing")
              or a division-level fallback: the beta is less reliable
Limitation: one SIC per company, so conglomerates / multi-segment firms (a retailer
with a cloud business, a payments network filed as business services) get a single
industry beta. The regression beta stays visible for comparison and the value is
editable in the dashboard.

This is an economic-assumption change backed by estimation theory (precision of
averaged betas), not by an Intrinsic backtest: we have no out-of-sample test that
bottom-up betas produce better valuations.
"""
from __future__ import annotations

import csv
import os

from intrinsic.paths import ROOT

HERE = ROOT   # project root (intrinsic.paths)
BETA_FILE = os.path.join(HERE, 'data', 'damodaran_us_industry_betas.csv')
BETA_SOURCE = 'Damodaran, US industry betas (January 2026), unlevered beta corrected for cash'
MARGINAL_TAX = 0.25   # 21% federal + ~4% state; same assumption as driver_forecast_27

# (sic_low, sic_high, Damodaran industry, match quality). Narrowest range wins.
SIC_CROSSWALK = (
    # Division A-B: agriculture, mining
    (100, 999, 'Farming/Agriculture', 'specific'),
    (1000, 1039, 'Metals & Mining', 'specific'),
    (1040, 1049, 'Precious Metals', 'specific'),
    (1050, 1199, 'Metals & Mining', 'specific'),
    (1200, 1299, 'Coal & Related Energy', 'specific'),
    (1300, 1319, 'Oil/Gas (Production and Exploratio', 'specific'),
    (1320, 1379, 'Oilfield Svcs/Equip.', 'specific'),
    (1380, 1389, 'Oilfield Svcs/Equip.', 'specific'),
    (1400, 1499, 'Metals & Mining', 'specific'),
    # Division C: construction
    (1500, 1539, 'Homebuilding', 'specific'),
    (1540, 1799, 'Engineering/Construction', 'specific'),
    # Division D: manufacturing
    (2000, 2079, 'Food Processing', 'specific'),
    (2080, 2080, 'Beverage (Soft)', 'broad'),       # "beverages", not split by type
    (2082, 2085, 'Beverage (Alcoholic)', 'specific'),
    (2086, 2087, 'Beverage (Soft)', 'specific'),
    (2088, 2099, 'Food Processing', 'specific'),
    (2100, 2199, 'Tobacco', 'specific'),
    (2200, 2299, 'Apparel', 'specific'),
    (2300, 2399, 'Apparel', 'specific'),
    (2400, 2499, 'Paper/Forest Products', 'specific'),
    (2500, 2599, 'Furn/Home Furnishings', 'specific'),
    (2600, 2649, 'Paper/Forest Products', 'specific'),
    (2650, 2679, 'Packaging & Container', 'specific'),
    (2700, 2799, 'Publishing & Newspapers', 'specific'),
    (2800, 2829, 'Chemical (Basic)', 'specific'),
    (2830, 2834, 'Drugs (Pharmaceutical)', 'specific'),
    (2835, 2836, 'Drugs (Biotechnology)', 'specific'),
    (2840, 2844, 'Household Products', 'specific'),
    (2850, 2899, 'Chemical (Specialty)', 'specific'),
    (2900, 2999, 'Oil/Gas (Integrated)', 'specific'),
    (3000, 3019, 'Rubber& Tires', 'specific'),
    (3020, 3099, 'Chemical (Specialty)', 'broad'),
    (3100, 3199, 'Shoe', 'specific'),
    (3200, 3299, 'Building Materials', 'specific'),
    (3300, 3329, 'Steel', 'specific'),
    (3330, 3399, 'Metals & Mining', 'specific'),
    (3400, 3499, 'Machinery', 'broad'),
    (3410, 3412, 'Packaging & Container', 'specific'),
    (3500, 3569, 'Machinery', 'specific'),
    (3570, 3579, 'Computers/Peripherals', 'specific'),
    (3580, 3599, 'Machinery', 'specific'),
    (3600, 3629, 'Electrical Equipment', 'specific'),
    (3630, 3659, 'Electronics (Consumer & Office)', 'specific'),
    (3660, 3669, 'Telecom. Equipment', 'specific'),
    (3670, 3679, 'Electronics (General)', 'specific'),
    (3672, 3672, 'Electronics (General)', 'specific'),
    (3674, 3674, 'Semiconductor', 'specific'),
    (3680, 3699, 'Electrical Equipment', 'specific'),
    (3700, 3709, 'Auto & Truck', 'specific'),
    (3711, 3711, 'Auto & Truck', 'specific'),
    (3713, 3716, 'Auto Parts', 'specific'),
    (3720, 3729, 'Aerospace/Defense', 'specific'),
    (3730, 3739, 'Shipbuilding & Marine', 'specific'),
    (3740, 3749, 'Machinery', 'specific'),
    (3750, 3799, 'Recreation', 'specific'),
    (3760, 3769, 'Aerospace/Defense', 'specific'),
    (3800, 3829, 'Electronics (General)', 'specific'),
    (3812, 3812, 'Aerospace/Defense', 'specific'),
    (3826, 3827, 'Healthcare Products', 'broad'),
    (3840, 3851, 'Healthcare Products', 'specific'),
    (3860, 3879, 'Electronics (Consumer & Office)', 'specific'),
    (3900, 3999, 'Recreation', 'broad'),
    # Division E: transportation, communications, utilities
    (4000, 4019, 'Transportation (Railroads)', 'specific'),
    (4100, 4199, 'Transportation', 'specific'),
    (4200, 4229, 'Trucking', 'specific'),
    (4400, 4499, 'Shipbuilding & Marine', 'specific'),
    (4500, 4599, 'Air Transport', 'specific'),
    (4600, 4699, 'Oil/Gas Distribution', 'specific'),
    (4700, 4799, 'Transportation', 'specific'),
    (4800, 4811, 'Telecom. Services', 'specific'),
    (4812, 4812, 'Telecom (Wireless)', 'specific'),
    (4813, 4829, 'Telecom. Services', 'specific'),
    (4830, 4839, 'Broadcasting', 'specific'),
    (4840, 4849, 'Cable TV', 'specific'),
    (4890, 4899, 'Telecom. Services', 'specific'),
    (4900, 4939, 'Utility (General)', 'specific'),
    (4940, 4949, 'Utility (Water)', 'specific'),
    (4950, 4959, 'Environmental & Waste Services', 'specific'),
    (4960, 4999, 'Power', 'specific'),
    # Division F: wholesale
    (5000, 5099, 'Retail (Distributors)', 'specific'),
    (5100, 5139, 'Retail (Distributors)', 'specific'),
    (5140, 5149, 'Food Wholesalers', 'specific'),
    (5150, 5199, 'Retail (Distributors)', 'specific'),
    (5170, 5172, 'Oil/Gas Distribution', 'specific'),
    # Division G: retail
    (5200, 5299, 'Retail (Building Supply)', 'specific'),
    (5300, 5399, 'Retail (General)', 'specific'),
    (5400, 5499, 'Retail (Grocery and Food)', 'specific'),
    (5500, 5599, 'Retail (Automotive)', 'specific'),
    (5600, 5699, 'Retail (Special Lines)', 'specific'),
    (5700, 5799, 'Retail (Special Lines)', 'specific'),
    (5800, 5899, 'Restaurant/Dining', 'specific'),
    (5900, 5999, 'Retail (Special Lines)', 'specific'),
    (5961, 5961, 'Retail (General)', 'broad'),
    # Division H: finance (routed away from FCFF; kept so betas still display)
    (6000, 6099, 'Banks (Regional)', 'broad'),
    (6100, 6199, 'Financial Svcs. (Non-bank & Insur', 'specific'),
    (6200, 6299, 'Brokerage & Investment Banking', 'specific'),
    (6300, 6399, 'Insurance (General)', 'broad'),
    (6311, 6311, 'Insurance (Life)', 'specific'),
    (6324, 6324, 'Healthcare Support Services', 'broad'),
    (6331, 6331, 'Insurance (Prop/Cas.)', 'specific'),
    (6400, 6499, 'Insurance (General)', 'broad'),
    (6500, 6553, 'Real Estate (Operations & Service', 'specific'),
    (6700, 6799, 'Investments & Asset Management', 'broad'),
    (6798, 6798, 'R.E.I.T.', 'specific'),
    # Division I: services
    (7000, 7099, 'Hotel/Gaming', 'specific'),
    (7200, 7299, 'Business & Consumer Services', 'specific'),
    (7300, 7319, 'Advertising', 'specific'),
    (7320, 7369, 'Business & Consumer Services', 'specific'),
    (7370, 7370, 'Software (Internet)', 'broad'),
    (7371, 7371, 'Computer Services', 'specific'),
    (7372, 7372, 'Software (System & Application)', 'specific'),
    (7373, 7379, 'Computer Services', 'specific'),
    (7374, 7374, 'Information Services', 'broad'),
    (7380, 7399, 'Business & Consumer Services', 'specific'),
    (7389, 7389, 'Business & Consumer Services', 'broad'),
    (7500, 7599, 'Business & Consumer Services', 'specific'),
    (7800, 7829, 'Entertainment', 'specific'),
    (7830, 7849, 'Entertainment', 'specific'),
    (7900, 7999, 'Recreation', 'specific'),
    (7990, 7999, 'Hotel/Gaming', 'broad'),
    (8000, 8059, 'Healthcare Support Services', 'specific'),
    (8060, 8069, 'Hospitals/Healthcare Facilities', 'specific'),
    (8070, 8099, 'Healthcare Support Services', 'specific'),
    (8200, 8299, 'Education', 'specific'),
    (8700, 8719, 'Engineering/Construction', 'broad'),
    (8731, 8734, 'Drugs (Biotechnology)', 'broad'),
    (8700, 8799, 'Business & Consumer Services', 'broad'),
)
# Division-level fallback when no specific range matches.
DIVISION_FALLBACK = (
    (100, 999, 'Farming/Agriculture'), (1000, 1499, 'Metals & Mining'),
    (1500, 1799, 'Engineering/Construction'), (2000, 3999, 'Machinery'),
    (4000, 4999, 'Transportation'), (5000, 5199, 'Retail (Distributors)'),
    (5200, 5999, 'Retail (Special Lines)'), (7000, 8999, 'Business & Consumer Services'),
)


def load_industry_betas(path=BETA_FILE):
    with open(path, newline='') as fh:
        return {row['industry']: row for row in csv.DictReader(fh)}


def industry_for_sic(sic):
    """(industry, quality) for a SIC code, or (None, reason)."""
    try:
        n = int(sic)
    except (TypeError, ValueError):
        return None, 'no SIC code'
    hits = [(hi - lo, ind, q) for lo, hi, ind, q in SIC_CROSSWALK if lo <= n <= hi]
    if hits:
        _, ind, q = min(hits)
        return ind, q
    for lo, hi, ind in DIVISION_FALLBACK:
        if lo <= n <= hi:
            return ind, 'broad'
    return None, f'SIC {n} not mapped'


SMALL_INDUSTRY = 20   # below this many firms the industry average is itself noisy


def bottom_up_beta(sic, *, market_equity, total_debt, tax=MARGINAL_TAX, table=None, industry=None):
    """Relevered industry beta with its inputs, or {'beta': None, 'reason': ...}.

    `industry` overrides the SIC crosswalk (user choice for multi-segment firms)."""
    if industry is not None:
        quality = 'user'
    else:
        industry, quality = industry_for_sic(sic)
    if industry is None:
        return {'beta': None, 'reason': quality}
    row = (table or load_industry_betas()).get(industry)
    if row is None:
        return {'beta': None, 'reason': f'industry {industry!r} missing from beta file'}
    if not market_equity or market_equity <= 0 or total_debt is None or total_debt < 0:
        return {'beta': None, 'reason': 'market equity or debt unavailable'}
    bu = float(row['unlevered_beta_cash_corrected'])
    de = total_debt / market_equity
    return {
        'beta': bu * (1 + (1 - tax) * de), 'unlevered_beta': bu, 'industry': industry,
        'match': quality, 'sic': int(sic) if sic not in (None, '') else None,
        'n_firms': int(row['n_firms']), 'small_industry': int(row['n_firms']) < SMALL_INDUSTRY, 'de_ratio': de,
        'tax': tax, 'source': BETA_SOURCE,
    }
