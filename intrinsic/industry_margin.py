"""Industry operating margins, used as the long-run target for loss-making companies.

Source: Damodaran, US industry margins (data/damodaran_us_industry_margins.csv, January 2026 update),
column "Pre-tax Unadjusted Operating Margin" = operating income / revenue, the same reported-basis
margin the forecast projects. Companies are mapped to industries with the SIC crosswalk used for
betas (intrinsic.industry_beta), so a company gets the same industry for its beta and its margin.

Fallback: when the industry is unmapped, has fewer than SMALL_INDUSTRY firms or a non-positive margin
(an industry that loses money in aggregate offers no profitable anchor), the US market margin without
financials is used and labelled as such.
"""
from __future__ import annotations

import csv
import os

from intrinsic.industry_beta import SMALL_INDUSTRY, industry_for_sic
from intrinsic.paths import DATA_DIR

MARGIN_FILE = os.path.join(DATA_DIR, 'damodaran_us_industry_margins.csv')
MARGIN_SOURCE = 'Damodaran, US industry pre-tax operating margins (January 2026)'
MARKET = 'Total Market (without financials)'


def load_industry_margins(path=MARGIN_FILE):
    out = {}
    with open(path, newline='') as fh:
        for row in csv.DictReader(fh):
            try:
                out[row['industry']] = {'margin': float(row['pretax_operating_margin']), 'n_firms': int(row['n_firms'])}
            except (TypeError, ValueError):
                continue
    return out


def industry_margin_for_sic(sic, table=None):
    """{'margin', 'industry', 'n_firms', 'note'} for a SIC code (market fallback when unreliable)."""
    table = table or load_industry_margins()
    industry, quality = industry_for_sic(sic)
    row = table.get(industry) if industry else None
    market = table[MARKET]
    if row is None:
        why = f'SIC {sic} not mapped to an industry' if industry is None else f'no margin for {industry}'
    elif row['n_firms'] < SMALL_INDUSTRY:
        why = f'{industry} has only {row["n_firms"]} firms'
    elif row['margin'] <= 0:
        why = f'{industry} loses money in aggregate ({row["margin"]:.1%})'
    else:
        broad = ' (broad SIC match)' if quality == 'broad' else ''
        return {'margin': row['margin'], 'industry': industry, 'n_firms': row['n_firms'],
                'note': f'{industry}{broad}: aggregate industry operating margin, {row["n_firms"]} US firms, '
                        f'{MARGIN_SOURCE}'}
    return {'margin': market['margin'], 'industry': MARKET, 'n_firms': market['n_firms'],
            'note': f'US market without financials ({market["n_firms"]} firms) because {why}; {MARGIN_SOURCE}'}
