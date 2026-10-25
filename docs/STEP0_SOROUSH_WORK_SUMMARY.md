# Step 0 — Patent dataset construction: development update

**Project:** Flying Drones Patent Analytics  
**Contributor:** Soroush Khayami  
**Date:** 25 October 2026  
**Branch:** `feature/soroush-step0`  
**Notebook:** `PWStep0.ipynb`  
**Execution environment:** EPO TIP / PATSTAT **TEST**  
**Status:** Development and query validation in progress — not final sector statistics.

## Purpose

The notebook assembles candidate flying-drone patent applications through **title/abstract keywords**, **IPC codes**, and **CPC codes**. It combines these search routes, checks and explains their matches, groups results at DOCDB-family level, prepares a sample for manual validation, retrieves additional family records and applicants, and performs preliminary cleaning.

## Notebook walkthrough

| Section | What the code does | Why it matters |
|---|---|---|
| 1. Set up the environment | Imports Python, SQLAlchemy and TIP/PATSTAT tools; initializes `PatstatClient(env="TEST")`. | Allows safe functional testing without claiming population-wide results. |
| 2. Define search scope | Sets `DRONE_KEYWORDS`, `DRONE_IPC_CODES` (`B64U`) and `DRONE_CPC_CODES` (`B64U`, `B64C39/024`). | Makes the initial retrieval strategy explicit. These are baseline terms, not yet validated. |
| 3. Build query functions | Uses SQLAlchemy to match text in titles/abstracts or classification-code prefixes. | Keeps the three retrieval routes reproducible and comparable. |
| 4. Retrieve candidates | Executes keyword, IPC and CPC searches separately, then combines matched application IDs using SQL `UNION`. | Collects patent applications from complementary search strategies without counting duplicate application IDs in the union. |
| 5. Check coverage and data quality | Reports application and family counts, invalid family IDs and unavailable year values; records whether each application came from keywords, IPC, CPC or a combination. | Identifies potential problems before analysis. |
| 6. Investigate false positives | Checks suspicious wind-turbine titles and identifies the keywords or classification paths responsible; provides application-inspection functions. | Shows why broad terms such as `multi-rotor` need scrutiny before any search-list changes. |
| 7. Group by DOCDB family | Combines multiple applications belonging to one family and records the retrieval route. | Avoids treating each national application as a separate invention in family-level analysis. |
| 8. Prepare validation | Selects up to 100 families with a fixed random seed, creates/restores a CSV, and provides `inspect_family()` and `label_family()` helpers. | Enables documented manual assessment of `relevant`, `not relevant` or `uncertain`. No labels are assigned automatically. |
| 9. Report validation progress | Counts manual decisions and reports precision only after all sampled families have definite classifications. | Prevents a misleading precision claim while review is incomplete. |
| 10. Expand family records | Retrieves additional applications from matched DOCDB families, including applications not directly caught by the original query. | Improves family-level coverage for later analysis. |
| 11. Retrieve applicants | Joins PATSTAT application/person linkage and person information to extract applicant names, standardized names and countries. | Prepares the competitive-landscape dataset. |
| 12. Apply initial cleaning | Creates a **family earliest-filing-year proxy** and normalizes applicant-name spelling, case and spacing. | Prepares structured records while recognizing that the year proxy is **not yet a verified earliest priority year**. |
| 13. Print checkpoint | Summarizes counts, the validation CSV path and remaining tasks. | Makes development status easy to review. |

## Current findings and limitations

- Some keyword-search hits appear to relate to wind turbines rather than flying drones; the relevant terms and retrieval routes should be inspected before excluding anything.
- The validation sample is prepared, but **100 families selected does not mean 100 families manually reviewed**. A `0/100` result is expected when the labels have not been entered.
- TEST is a reduced development dataset. Patent counts and query precision should not be reported as final sector estimates.
- The professor requests **earliest priority year**, while the present implementation calculates a minimum of available `earliest_filing_year` values. The difference needs investigation.
- The final historical period (2000–2022 vs. 2000–2023), search accuracy, and company-name harmonization need team review.

## Proposed next steps

1. Inspect and label sampled patent families, recording evidence for each decision.
2. Compare false positives with candidate UAV terminology and classification paths; test any revised query against the baseline.
3. Confirm the priority-year methodology and historical time window with the team.
4. Re-run the agreed query on PATSTAT PROD when ready, and validate a sample from that final corpus.
5. Keep bulk PATSTAT results, checkpoint files, and any credentials out of Git commits.

## Files and collaboration

- `PWStep0.ipynb` — executable notebook, reviewed via the team's pull request.
- `docs/STEP0_SOROUSH_WORK_SUMMARY.md` — this summary of the notebook and open methodological questions.
- The literature review may be added separately as `docs/Flying_Drones_Step0_Literature_Review.md`.

> **Review request:** Please check the search definitions and historical-year choice before the team merges the changes. The query is an initial baseline, and manual validation is still pending.
