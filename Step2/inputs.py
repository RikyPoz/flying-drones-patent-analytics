"""Read the sealed drone cohort and attach the course's all-field filing history."""

import pandas as pd


FAMILIES = "extract/families.parquet"
LINKS = "harmonization/family_applicant_links.csv"
ATTRIBUTES = "harmonization/applicants_harmonized.csv"
CPC = "extract/tls224_cpc.parquet"
FIRST_EVER = "step2/first_patent_year.parquet"


def applicant_type(psn_sector):
    """Translate psn_sector using the precedence in tutorial 1/11, section 2.3."""
    sector = str(psn_sector).upper()
    for token, label in (
        ("UNIVERSITY", "university"), ("COMPANY", "firm"),
        ("GOV", "government / non-profit"), ("HOSPITAL", "hospital"),
        ("INDIVIDUAL", "individual"),
    ):
        if token in sector:
            return label
    return "unknown"


def load_inputs(run):
    """Return extracted family years, unique family–applicant links and family CPCs."""
    families = pd.read_parquet(
        run.verify(FAMILIES), columns=["docdb_family_id", "priority_year"]
    ).rename(columns={"docdb_family_id": "unit_id", "priority_year": "year"})
    year_range = run.cfg["years"]
    if (families.isna().any().any() or families["unit_id"].duplicated().any()
            or not families["year"].between(year_range["min"], year_range["max"]).all()):
        raise ValueError("Extracted families need one in-window priority year per family ID.")

    # An empty field denotes missing data. 'NA' is a valid country code (Namibia).
    csv_options = {"keep_default_na": False, "na_values": [""]}
    keys = ["docdb_family_id", "entity_id"]
    links = pd.read_csv(run.verify(LINKS), usecols=keys, **csv_options)
    records = pd.read_csv(
        run.verify(ATTRIBUTES),
        usecols=keys + ["standardized_name", "psn_sector", "person_ctry_code", "needs_manual_review"],
        dtype={"entity_id": "string", "person_ctry_code": "string", "needs_manual_review": "boolean"},
        **csv_options,
    )
    if (links[keys].isna().any().any() or links.duplicated(keys).any()
            or records[keys + ["needs_manual_review"]].isna().any().any()):
        raise ValueError("Invalid or missing family–applicant keys or review flags in Step 0 outputs.")

    review = records.groupby(keys, sort=False)["needs_manual_review"].any().rename("needs_manual_review")
    pairs = pd.MultiIndex.from_frame(links[keys])
    if len(pairs) != len(review) or not pairs.isin(review.index).all():
        raise ValueError("Family–applicant links differ from the harmonized applicant records.")
    links = links.join(review, on=keys, validate="one_to_one")

    # One vote per family, entity and known country, independent of the number of applications.
    # Alphabetical country code breaks equal-frequency ties reproducibly.
    records["person_ctry_code"] = records["person_ctry_code"].str.strip().replace("", pd.NA)
    country_counts = (
        records.drop_duplicates(keys + ["person_ctry_code"])
        .groupby(["entity_id", "person_ctry_code"]).size().rename("votes").reset_index()
        .sort_values(["entity_id", "votes", "person_ctry_code"], ascending=[True, False, True])
    )
    country = country_counts.drop_duplicates("entity_id").set_index("entity_id")["person_ctry_code"]

    # Preserve the published entity ID, including distinct entities with identical display names.
    # Use the first available display name and the first observed course type in the saved row order.
    records["type"] = records["psn_sector"].map(applicant_type)
    profile = records.groupby("entity_id", sort=False).agg(name=("standardized_name", "first"),
                                                          type=("type", "first"))
    profile["ctry"] = country
    links = links.join(profile, on="entity_id", validate="many_to_one").rename(
        columns={"docdb_family_id": "unit_id", "entity_id": "applicant"}
    )
    links["name"] = links["name"].fillna(links["applicant"])
    cpc = pd.read_parquet(run.verify(CPC), columns=["docdb_family_id", "cpc"]).rename(
        columns={"docdb_family_id": "unit_id"}
    )
    cpc["cpc"] = cpc["cpc"].astype("string").str.replace(" ", "", regex=False)
    cpc = cpc.drop_duplicates().copy()
    if not links["unit_id"].isin(families["unit_id"]).all() or not cpc["unit_id"].isin(families["unit_id"]).all():
        raise ValueError("Applicant or CPC records reference a family outside this run's extract.")

    links = links.merge(families, on="unit_id", validate="many_to_one")
    family_cpc = cpc.dropna(subset=["cpc"]).merge(families, on="unit_id", validate="many_to_one")
    return families, links, family_cpc


def _query_first_years(run, applicants):
    """Step 2's PATSTAT lookup, across every sector, office and IPR type."""
    from epo.tipdata.patstat import PatstatClient
    from epo.tipdata.patstat.database.models import TLS201_APPLN, TLS206_PERSON, TLS207_PERS_APPLN
    from sqlalchemy import func

    client = PatstatClient(env=run.env)
    db = client.orm()
    result = pd.Series(pd.NA, index=applicants, dtype="Int64", name="first_patent_year")
    year = TLS201_APPLN.earliest_filing_year
    # 3b gives a PERSON key only when there was no positive PSN ID.
    if not applicants.str.fullmatch(r"(?:PSN|PERSON):[0-9]+").all():
        raise ValueError("Unrecognized Step 0 entity ID in the filing history lookup.")
    for prefix, column in (("PSN:", TLS206_PERSON.psn_id), ("PERSON:", TLS206_PERSON.person_id)):
        ids = [int(key[len(prefix):]) for key in applicants if key.startswith(prefix)]
        ids = [identifier for identifier in ids if identifier > 0]
        for start in range(0, len(ids), 5000):
            chunk = ids[start:start + 5000]
            print(f"Querying first filings for {prefix[:-1]} IDs {start + 1:,}–{start + len(chunk):,} of {len(ids):,}", flush=True)
            q = (
                db.query(column.label("identifier"), func.min(year).label("first_patent_year"))
                .select_from(TLS206_PERSON)
                .join(TLS207_PERS_APPLN, TLS207_PERS_APPLN.person_id == TLS206_PERSON.person_id)
                .join(TLS201_APPLN, TLS201_APPLN.appln_id == TLS207_PERS_APPLN.appln_id)
                .filter(column.in_(chunk), TLS207_PERS_APPLN.applt_seq_nr > 0,
                        year.between(1900, run.cfg["years"]["max"]))
                .group_by(column)
            )
            hits = client.df(q)
            if not hits.empty:
                hit_keys = prefix + hits["identifier"].astype("int64").astype(str)
                result.loc[hit_keys] = hits["first_patent_year"].astype("int64").to_numpy()
    return result


def load_first_ever(run, links):
    """Query once on TIP; later reads verify the same run's published first-year table."""
    applicants = pd.Index(sorted(links["applicant"].unique()), name="applicant")
    if run.path(FIRST_EVER).exists():
        frame = pd.read_parquet(run.verify(FIRST_EVER))
        first_ever = frame.set_index("applicant", verify_integrity=True)["first_patent_year"]
        if not first_ever.index.sort_values().equals(applicants):
            raise ValueError("Filing history and input applicant identities differ.")
        return first_ever.astype("Int64")

    first_ever = _query_first_years(run, applicants)
    run.publish(
        FIRST_EVER, lambda path: first_ever.reset_index().to_parquet(path, index=False),
        inputs=(LINKS,),
        metadata={"source": "PATSTAT TLS206/TLS207/TLS201; all-field applicant history",
                  "first_year": 1900, "last_year": run.cfg["years"]["max"],
                  "entities": len(applicants), "unknown": int(first_ever.isna().sum())},
    )
    return first_ever
