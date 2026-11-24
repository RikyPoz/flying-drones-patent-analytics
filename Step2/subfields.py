"""Count sector CPC subfields using the two complete five-year windows in tutorial 11."""

import pandas as pd


def subfield_growth(family_cpc, prefixes, last_complete):
    """Return all subfield counts and the course's three fastest-growing eligible groups.

    Each family has one priority year and can contribute once per subfield. Only
    symbols matching the sector prefixes qualify, before collapsing their subgroups.
    """
    recent_start = last_complete - 4
    past_start = recent_start - 5
    years = family_cpc["year"].between(past_start, last_complete)
    rows = family_cpc.loc[years, ["unit_id", "cpc", "year"]].dropna()
    codes = rows["cpc"].astype("string").str.upper().str.replace(r"\s+", "", regex=True)
    sector_prefixes = tuple("".join(prefix.upper().split()) for prefix in prefixes if prefix.strip())
    in_sector = codes.str.startswith(sector_prefixes)
    rows = rows.loc[in_sector, ["unit_id", "year"]].copy()
    # B64C39/024 -> B64C39/02, but only after matching the full prefix B64C39/024.
    rows["subfield"] = codes[in_sector].str.extract(
        r"^([A-HY][0-9]{2}[A-Z][0-9]+/[0-9]{1,2})[0-9]*$", expand=False
    )
    rows = rows.dropna(subset=["subfield"]).drop_duplicates(["unit_id", "subfield"])

    past = rows.loc[rows["year"] < recent_start].groupby("subfield")["unit_id"].nunique()
    recent = rows.loc[rows["year"] >= recent_start].groupby("subfield")["unit_id"].nunique()
    counts = pd.DataFrame({"past_families": past, "recent_families": recent}).fillna(0).astype("int64")
    baseline = counts["past_families"].where(counts["past_families"] > 0)
    counts["growth_pct"] = (counts["recent_families"] / baseline - 1) * 100
    counts = counts.sort_index().sort_values("recent_families", ascending=False, kind="stable")

    comparable = counts.dropna(subset=["growth_pct"])
    eligible = comparable["recent_families"] >= comparable["recent_families"].median()
    fastest = comparable.loc[eligible].sort_values("growth_pct", ascending=False, kind="stable").head(3)
    return counts, fastest
