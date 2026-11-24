"""Inventive concentration and applicant dynamics, following the course tutorial §§3 and 5."""

import numpy as np
import pandas as pd
from scipy.stats import linregress


def _period_concentration(links, start, end):
    """Count each distinct family once for every harmonized applicant on it."""
    period = links.loc[links["year"].between(start, end)]
    counts = np.sort(period.groupby("applicant")["unit_id"].nunique().to_numpy(dtype=float))
    total = counts.sum()
    n = len(counts)
    measures = dict.fromkeys(
        ("cv", "cr4_pct", "cr8_pct", "hhi", "numbers_equivalent", "gini",
         "lotka_slope", "lotka_pvalue"), np.nan
    )
    if n:
        shares = counts / total
        hhi = np.square(shares).sum()
        cumulative = np.r_[0.0, shares.cumsum()]
        # Trapezoids under the Lorenz curve, with applicants ordered smallest first.
        gini = 1 - np.mean(cumulative[1:] + cumulative[:-1])
        measures.update(
            cv=counts.std(ddof=1) / counts.mean() if n > 1 else np.nan,
            cr4_pct=100 * shares[-4:].sum(),
            cr8_pct=100 * shares[-8:].sum(),
            hhi=hhi,
            numbers_equivalent=1 / hhi,
            gini=float(np.clip(gini, 0, 1)),
        )
        portfolio_sizes, frequencies = np.unique(counts, return_counts=True)
        if len(portfolio_sizes) >= 3:
            fit = linregress(np.log(portfolio_sizes), np.log(frequencies))
            measures.update(lotka_slope=fit.slope, lotka_pvalue=fit.pvalue)

    return {
        "period_start": start,
        "period_end": end,
        "years_in_period": end - start + 1,
        "applicants": n,
        "linked_families": period["unit_id"].nunique(),
        "family_applicant_credits": int(total),
        **measures,
    }


def concentration(links, year_min, last_complete_year, window=3):
    """Overall complete years and consecutive non-overlapping windows from year_min."""
    if window <= 0 or last_complete_year < year_min:
        raise ValueError("Provide a positive window and at least one complete year.")
    overall = pd.DataFrame([_period_concentration(links, year_min, last_complete_year)])
    windows = pd.DataFrame([
        _period_concentration(links, start, min(start + window - 1, last_complete_year))
        for start in range(year_min, last_complete_year + 1, window)
    ])
    windows["full_window"] = windows["years_in_period"].eq(window)
    return overall, windows


def applicants_and_entry(links, first_ever, year_min, year_max, last_complete_year, split_year=2015):
    """Rank sector applicants and count entry/last observation over the full observed window."""
    sector = links.loc[links["year"].between(year_min, year_max)]
    grouped = sector.groupby("applicant")
    ranked = grouped.agg(
        name=("name", "first"), type=("type", "first"), country=("ctry", "first"),
        families=("unit_id", "nunique"), first_sector_year=("year", "min"),
        last_sector_year=("year", "max"),
    )
    if "needs_manual_review" in sector:
        ranked["needs_manual_review"] = grouped["needs_manual_review"].any()
    recent = sector.loc[sector["year"].ge(split_year)].groupby("applicant")["unit_id"].nunique()
    ranked["families_since_split"] = recent.reindex(ranked.index, fill_value=0)
    ranked["first_patent_year"] = first_ever.reindex(ranked.index).astype("Int64")
    ranked["status"] = np.where(ranked["first_sector_year"].lt(split_year), "incumbent", "entrant")

    active = sector[["applicant", "year"]].drop_duplicates().copy()
    active["new_to_sector"] = active["year"].eq(active["applicant"].map(ranked["first_sector_year"]))
    first_patent = active["applicant"].map(ranked["first_patent_year"])
    active["known_first_patent"] = first_patent.notna()
    active["new_to_patenting"] = active["year"].eq(first_patent)
    active["last_observed"] = active["year"].eq(active["applicant"].map(ranked["last_sector_year"]))
    annual = active.groupby("year").agg(
        active_applicants=("applicant", "size"),
        new_to_sector=("new_to_sector", "sum"),
        new_to_patenting=("new_to_patenting", "sum"),
        known_first_patent=("known_first_patent", "sum"),
        last_observed=("last_observed", "sum"),
    )
    family_entries = sector[["year", "unit_id", "applicant"]].merge(
        active[["year", "applicant", "new_to_sector"]], on=["year", "applicant"],
        how="left", validate="many_to_one",
    )
    any_entrant = family_entries.groupby(["year", "unit_id"])["new_to_sector"].any()
    annual["linked_families"] = any_entrant.groupby(level="year").size()
    annual["families_with_entrant"] = any_entrant.groupby(level="year").sum()
    annual = annual.reindex(range(year_min, year_max + 1), fill_value=0)
    known = annual.pop("known_first_patent")
    annual["unknown_first_patent_year"] = annual["active_applicants"] - known
    # No active applicants means zero entrants. Active applicants with no usable histories
    # give an unknown count. In partially covered years the count is confirmed matches only.
    annual["new_to_patenting"] = annual["new_to_patenting"].astype("Int64").mask(
        annual["active_applicants"].gt(0) & known.eq(0)
    )
    annual["entrant_family_share_pct"] = (
        100 * annual["families_with_entrant"] / annual["linked_families"].replace(0, np.nan)
    )
    exit_rate = 100 * annual["last_observed"] / annual["active_applicants"].replace(0, np.nan)
    annual["disappearance_pct"] = exit_rate.where(annual.index <= last_complete_year - 3)
    annual["incomplete_year"] = annual.index > last_complete_year
    ranked = ranked.reset_index().sort_values(["families", "applicant"], ascending=[False, True])
    return ranked.reset_index(drop=True), annual.reset_index()
