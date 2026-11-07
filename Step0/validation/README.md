# Step 0 · Validation files

This folder holds the results of the validation of the Step 0 dataset: how many of the selected patent families are really about flying drones, and whether the LLM we used to check them can be trusted.

The files are written by `Step0/2-DataValidation.ipynb`, which is run from the validation cell of `Step0/1-DataPreparation.ipynb` (`%run -i ./2-DataValidation.ipynb`), and by `Step0/2b-LLMHandCheck.ipynb`.

All numbers below are on the **TEST** environment and will be refreshed on PROD.

## Main results (TEST)

| Question | Answer | File |
|---|---|---|
| Does the SBERT filter keep drones and drop the rest? | Yes: precision 0.88 (95% CI 0.70–0.96), recall 0.95 within the search results. | printed by the validation cell of `1-DataPreparation` |
| Does the SBERT enrichment add drones? | Mostly not: only 17% of the 922 added families are drones (95% CI 11–26%); a higher threshold does not fix it (26% at 0.75). | `enrichment_threshold_sweep.csv` |
| Should we keep the enrichment? | No. Rule fixed before the test: keep it only if it improves F1 significantly. F1 is 0.83 without it and 0.74 with it; it is lower at every threshold. | `enrichment_decision.csv` |
| Does it matter for the results? | Yes: with the enrichment, Boeing becomes the first applicant (68 of its 105 families come from it) and most families before 2013 are added by it. | `enrichment_impact_*.csv` |
| Can we trust the LLM labels? | Mostly: 85% agreement with blind human labels, Cohen's kappa 0.67 (substantial). Its errors are lenient "drone" answers, so precision values are upper bounds. | `hand_check_summary.csv` |

## Labels

`pertinente` = about flying drones · `non_pertinente` = not about flying drones · `incerto` = the LLM could not decide (resolved by hand). The labels stay in Italian so that the earlier labels and the cache remain valid.

Rule for every hand label: *pertinente* only if the text states or clearly implies an unmanned aircraft; generic aircraft technology, manned aircraft, ground-based anti-drone systems and non-flying vehicles are *non_pertinente*.

## The files

### Results (to read)

| File | One row per… | Columns |
|---|---|---|
| `enrichment_decision.csv` | dataset option: filter only, or filter + enrichment at threshold 0.60 / 0.65 / 0.70 / 0.75 | `families` in the dataset · estimated `drones` and `non_drones` · `precision` · `recall` (against all drone families estimated in the two pools) · `F1` · `F0.5` (precision counts twice) · `F1_diff_vs_filter_only` with its bootstrap 95% interval (`diff_CI95_low`, `diff_CI95_high`; 2,000 resamples) |
| `enrichment_threshold_sweep.csv` | enrichment threshold (0.60 to 0.75) | `families_added` · `labelled` (of the 100 labelled added families, those above the threshold) · `precision_added` with its 95% Wilson interval · estimated `drones_added` and `non_drones_added` · `dataset_families` and `dataset_precision` of filter + enrichment |
| `enrichment_impact_applicants_0.60.csv` | applicant (top 15 with the enrichment; PATSTAT `psn_name`, not yet harmonised) | families `with_enrichment`, `added_by_enrichment`, `without_enrichment` · rank without and with |
| `enrichment_impact_years_0.60.csv` | earliest priority year | families without the enrichment, added by it, with it · `share_added` |
| `hand_check_summary.csv` | prompt version (`v1-it` first Italian prompt, `v2-en` final English prompt) | families checked · agreement with its 95% interval · Cohen's kappa · times the LLM said `incerto` |

### Working files (used by the code, not meant to be read)

| File | What it is |
|---|---|
| `llm_cache.jsonl` | Every LLM answer (label, reason, quoted evidence), keyed by family and prompt version. Re-running the notebooks reads it, so nothing is sent to the LLM twice. |
| `review_filtro_sbert_selezionati.csv` · `review_filtro_sbert_scartati.csv` | Families kept / rejected by the SBERT filter that the LLM labelled `incerto`, with the hand label in `human_label`. |
| `review_arricchimento_sbert_selezionati.csv` · `review_arricchimento_sbert_scartati.csv` | The same for the families added / not added by the enrichment. |
| `hand_check.csv` | The 20 families labelled blind by a team member (no LLM label in the file). |

## How it works

1. `validate_sample` draws a random sample of families from each of the four groups (filter kept / rejected, enrichment added / not added; 25 or 100 families, seed 42) and asks the LLM (gpt-4.1-mini, temperature 0) whether each is about flying drones, from the title and the longest English abstract of the family.
2. `evaluate_selection` estimates precision and recall from the samples (stratified estimator, 95% Wilson intervals). If some answers are `incerto`, it writes them to the review file and asks for a hand label.
3. `enrichment_threshold_sweep` and `compare_dataset_options` / `enrichment_impact` are the enrichment tests. They are not called by `1-DataPreparation`; they were run once in a temporary cell (calls in the validation notes) and their results are the CSV files above.
4. `2b-LLMHandCheck.ipynb` compares the LLM labels with the blind human labels. It makes no LLM calls.

Cost: about 5 cents per 100 LLM calls; 425 calls so far. Re-runs are free thanks to the cache.

## Where the enrichment is set (in `1-DataPreparation.ipynb`)

| Cell | What |
|---|---|
| Settings cell (2) | `TAU_ENRICH = 0.60` (similarity threshold), `YEARS` |
| Section 3, cell 15 | `EXTERNAL_IPC_CODES`, `EXTERNAL_CPC_CODES = ("B64", "G05D1/", "G08G5/")`: the broad pool searched by the enrichment |
| Cells 16–19 | query of the pool, English abstracts, SBERT similarity |
| Cell 20 | applications above `TAU_ENRICH` → `df_enrichment` |
| Cell 21 | `df_selected = df_filtered + df_enrichment`: **to drop the enrichment, use only `df_filtered` here** |
| Cell 22 | split into the four validation groups |
