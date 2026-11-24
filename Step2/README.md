# Step 2 · Competitive landscape of flying drones

Run [1-CompetitiveLandscape.ipynb](1-CompetitiveLandscape.ipynb) on TIP to identify leading patent applicants, measure concentration and entry, compare growing drone subfields and prepare a sourced PEST table. Open the sections in order. The tables and three figures appear under their cells and can be shared through the executed notebook.

This implementation follows the professor’s Step 2 tutorial at commit `f1bca0b`. Section 2 defines applicant attributes, section 3 defines the concentration measures, and section 5 sets out the four sector questions. For the drone project, the inputs to section 5 are the family cohort and applicant identities already published by Step 0. The tutorial’s name-matching exercise and its historical US fuel-cell replication are teaching examples. [Professor’s competitive-landscape notebook](https://github.com/Soroushkhayami/innovation-management-datascience26/blob/f1bca0b6ab2310d174cd9588c13f144b0e6492f1/tutorial_1/11_competitive_landscape.ipynb) · [Project kickoff, competitive-landscape brief](../PW_0_kickoff.pdf)

## Run on TIP

1. Use the **existing TIP checkout that contains the completed run folders**. In its terminal, update the branch that contains your executed Step 0 and Step 1 notebooks.

   ```bash
   cd /home/jovyan/flying-drones-phase2a
   git switch refactor/phase-2a-stabilization
   git pull --ff-only origin refactor/phase-2a-stabilization
   ```

2. Open `Step2/1-CompetitiveLandscape.ipynb` in a fresh Python kernel and select **Run → Run All Cells**. At the run-ID prompt enter `phase2a-prod-001`. If `PATENT_RUN_ID` is already set, the notebook uses it and prints the environment and run ID. Use the same saved configuration as the original run. The Python kernel needs the project’s pandas, PyArrow, NumPy, matplotlib, SciPy, PyYAML and SQLAlchemy packages and TIP’s installed PATSTAT client.
3. Check the first outputs. For this production run they should show **PROD**, **106,998 extracted families**, **106,877 families with applicants** and **42,769 applicant entities** across all observed years. The complete-year HHI uses a smaller date window. These are checks against the previous run, not hard-coded inputs.
4. Allow the first all-field filing-history lookup to finish on TIP. It queries TLS206, TLS207 and TLS201 in batches of up to 5,000 IDs and saves `step2/first_patent_year.parquet` under the run. Later executions verify and reuse that file. The last cell prints the output directory after publishing all tables and figures. Verification reads the saved inputs and can take time for PROD.

The notebook can also use a completed TEST run with its original TEST configuration. All relative data paths resolve under `outputs/runs/<env>/<PATENT_RUN_ID>/`. Existing Step 0 receipts link the extract to the selection manifest. Step 2 checks those receipts and writes its own. The full analysis requires the TIP run directory even when the executed notebooks are already visible on GitHub.

## What to read in the results

| Question | What Step 2 computes | How to interpret it |
| --- | --- | --- |
| Is patenting concentrated or consolidating? | Sector measures over complete years and consecutive three-year windows. HHI uses shares between 0 and 1. CR4 and CR8 are percentages. The table also gives 1/HHI, sample CV, Gini, and the Lotka slope and p-value. | Increasing HHI and CR4 across comparable windows indicate increasing inventive concentration. The final shorter period is flagged and excluded from the trend plot. |
| Who leads and who is entering? | The 15 largest applicants across all observed years, with entity ID, display name, type, country, first and last sector years, portfolio size, filing history and review flag. The annual table gives entry, disappearance and families with entrants. | An incumbent first appears in this sector before 2015. New-to-patenting counts use the earliest observed applicant filing in **any** field from 1900 through the configured end year. Check flagged top applicants before drawing conclusions. Verify company age separately before describing a start-up. |
| Which subfields are growing? | Families per in-scope CPC group over successive five-year periods. With the baseline settings the comparison is **2013–2017 versus 2018–2022**. | Percent growth is defined for a positive earlier count. The top three are chosen among comparable groups whose recent family count reaches the median. New groups remain visible in the full table. Check CPC titles and classification changes when describing the leaders. |
| Which external forces shape competition? | A four-row PEST table with geography, evidence, competitive implication, date and a primary-source link. | The cited evidence covers European civil drones. Use the stated scope and date, distinguish forecasts from observed outcomes, and check the source before using it in the presentation. [PEST evidence](pest.csv) |

### Counting and coverage

- Each family contributes one credit to **each distinct harmonized applicant** on that family. If A and B share one family and A has one further family, their counts are 2 and 1. The HHI for that example is (2/3)² + (1/3)². Sector HHI includes all applicant types. The code reports the distinct linked families and the sum of applicant credits alongside the index.
- Step 0 supplies the priority year, PI-filtered cohort and conservative PSN/PERSON entity identity. Equal display names can represent distinct entities. Country is the modal known code across distinct family–entity–country combinations, with lexical order breaking ties. Type follows the tutorial’s PATSTAT sector-label precedence. Missing country stays missing.
- Entry indicators use one observation per active entity-year. A family with any sector entrant contributes once to the numerator, over the distinct applicant-linked families that year. Early years are left-censored. Disappearance means last observed sector filing and is displayed through **2019** with the baseline configuration. Recent years **2023–2025** are shaded on the annual chart.
- The all-field lookup uses the published PSN key or, for a missing PSN, the individual PATSTAT person ID. A fallback identity can have fragmented history. The annual table reports missing first-filing years so readers can assess coverage. With partial history, the new-to-patenting count includes confirmed matches only.
- The CPC analysis includes classified families without applicant links. It matches the original sector prefixes in the selection manifest before grouping codes by the first two subgroup digits, and counts each family once per subfield. A family can contribute to multiple subfields. Small starting counts can produce large percentages.

## Files and sharing

| Location under the run | Contents |
| --- | --- |
| `step2/coverage.csv` | Selection, extraction, applicant, review and CPC coverage |
| `step2/concentration.csv`, `step2/concentration_windows.csv` | Concentration measures and counts |
| `step2/top_applicants.csv`, `step2/applicant_ranking.csv` | Top 15 and full ranking, including name-review flags |
| `step2/entry_exit.csv` | Active applicants, entrants, filing-history coverage and disappearance by year |
| `step2/cpc_subfields.csv`, `step2/fastest_subfields.csv` | Family counts, growth and the three eligible leaders |
| `step2/pest.csv` | Source-attributed qualitative table |
| `step2/concentration_trend.png`, `step2/entry_exit.png`, `step2/subfield_growth.png` | Figures for the presentation |

After the final cell succeeds, **save the notebook** in Jupyter. To let teammates see the cell outputs at this same path on the fork, run the following from the TIP checkout root:

```bash
git add -- Step2/1-CompetitiveLandscape.ipynb
git commit --only -m "Save Step 2 competitive landscape results for PROD" -- Step2/1-CompetitiveLandscape.ipynb
git push origin refactor/phase-2a-stabilization
```

Share the [Step 2 notebook on the fork](https://github.com/Soroushkhayami/flying-drones-patent-analytics/blob/refactor/phase-2a-stabilization/Step2/1-CompetitiveLandscape.ipynb). The project stores the underlying run artifacts on TIP.

Course material by Grazia Sveva Ascione, Politecnico di Torino, based in part on original European Patent Office training material. This project adapts the course methods for non-commercial teaching and learning. The EPO has not authorised the changes and accepts no responsibility for the correctness of this version. [Course terms](https://github.com/Soroushkhayami/innovation-management-datascience26/blob/f1bca0b6ab2310d174cd9588c13f144b0e6492f1/LICENSE.md)
