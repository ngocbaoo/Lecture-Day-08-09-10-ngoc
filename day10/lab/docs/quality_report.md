# Quality report - Lab Day 10

**run_id (bad/inject):** `sprint3-bad`  
**run_id (good/clean):** `sprint2-smoke-conda`  
**date:** `2026-04-15`

---

## 1. Summary metrics

| Metric | Before (inject bad) | After (clean run) | Notes |
|--------|---------------------|-------------------|-------|
| raw_records | 10 | 10 | Same source export |
| cleaned_records | 6 | 6 | Cleaning scope unchanged |
| quarantine_records | 4 | 4 | Duplicate, empty row, stale HR row, unknown doc_id |
| text_repaired_count | 0 | 0 | No mojibake repair triggered on this sample export |
| exported_at_normalized_count | 6 | 6 | All cleaned rows normalized to ISO-8601 UTC |
| future_effective_date_count | 0 | 0 | No future-dated rows in this sample |
| Expectation halt? | Yes | No | `refund_no_stale_14d_window` fails only in inject run |

Evidence files:

- `artifacts/logs/run_sprint3-bad.log`
- `artifacts/logs/run_sprint2-smoke-conda.log`
- `artifacts/cleaned/cleaned_sprint3-bad.csv`
- `artifacts/cleaned/cleaned_sprint2-smoke-conda.csv`

---

## 2. Before / after quality evidence

Primary corruption scenario: disable the refund-window cleaning rule by running:

```bash
conda run -n vinai python etl_pipeline.py run --run-id sprint3-bad --no-refund-fix --skip-validate
```

Observed effect in the bad run:

- `expectation[refund_no_stale_14d_window] FAIL (halt) :: violations=1`
- cleaned output still contains the stale refund text `14 ngay lam viec`

Observed effect in the clean run:

- `expectation[refund_no_stale_14d_window] OK (halt) :: violations=0`
- cleaned output rewrites stale refund text to `7 ngay lam viec` and appends `[cleaned: stale_refund_window]`

Concrete cleaned CSV difference:

- Bad run file `artifacts/cleaned/cleaned_sprint3-bad.csv` contains one refund row with `14 ngay lam viec`
- Good run file `artifacts/cleaned/cleaned_sprint2-smoke-conda.csv` contains the corrected refund row with `7 ngay lam viec`

HR versioning remained stable in both runs:

- stale 2025 HR row stayed quarantined
- cleaned HR row kept the 2026 policy value `12 ngay phep nam`
- `expectation[hr_leave_no_stale_10d_annual] OK (halt) :: violations=0`

---

## 3. Retrieval / embed status

Retrieval evaluation was executed successfully and the following artifacts are available:

- `artifacts/eval/before.csv`
- `artifacts/eval/after.csv`
- `artifacts/eval/before_after_eval.csv`

Current observed retrieval output:

- `q_refund_window`: `contains_expected=yes`, `hits_forbidden=no`
- `q_leave_version`: `contains_expected=yes`, `hits_forbidden=no`, `top1_doc_expected=yes`
- `q_p1_sla`: `contains_expected=yes`
- `q_lockout`: `contains_expected=yes`

Interpretation:

- the current published collection is already aligned with the cleaned data snapshot
- retrieval artifacts support the conclusion that stale refund and stale HR content are not surfacing in top-k for the current clean state
- for Sprint 3, the strongest corruption evidence still comes from the expectation log and the cleaned CSV diff between `sprint3-bad` and `sprint2-smoke-conda`

---

## 4. Corruption inject summary

Inject type used in Sprint 3:

- intentionally skip the stale refund cleaning rule
- keep validate disabled so the bad row can reach the publish boundary during demo

How it is detected:

- expectation suite catches the stale refund policy before publish in normal mode
- cleaned CSV diff shows the stale `14 ngay` row directly
- retrieval artifacts should be kept together with the log evidence so the report shows both data-layer detection and user-facing effect

---

## 5. Limits / unfinished work

- `text_repaired_count` stayed `0` on the sample export, so mojibake repair still needs an injected case to demonstrate measurable impact.
- `future_effective_date_count` stayed `0` on the sample export, so that rule should be demonstrated with a synthetic future-dated row in Sprint 3 extension.

---

## 6. Distinction evidence - dynamic versioning

To avoid hard-coding the HR policy cutoff directly in code, the cleaning rule now reads `HR_LEAVE_MIN_EFFECTIVE_DATE` from environment first, and falls back to `contracts/data_contract.yaml` field `policy_versioning.hr_leave_min_effective_date`.

Evidence runs:

- `distinction-contract`: default cutoff from contract = `2026-01-01`
- `distinction-env-override`: env override cutoff = `2025-01-01`

Observed impact:

- In `run_distinction-contract.log`, `hr_leave_cutoff_used=2026-01-01`, `stale_hr_quarantine_count=2`, `cleaned_records=6`, `quarantine_records=17`
- In `run_distinction-env-override.log`, `hr_leave_cutoff_used=2025-01-01`, `stale_hr_quarantine_count=0`, `cleaned_records=7`, `quarantine_records=16`

Behavioral difference:

- With the contract cutoff, the stale HR 2025 row is quarantined and `expectation[hr_leave_no_stale_10d_annual]` stays `OK`
- With the env override, the 2025 HR row enters the cleaned snapshot and `expectation[hr_leave_no_stale_10d_annual] FAIL (halt) :: violations=1`

Artifact references:

- `artifacts/logs/run_distinction-contract.log`
- `artifacts/logs/run_distinction-env-override.log`
- `artifacts/cleaned/cleaned_distinction-contract.csv`
- `artifacts/cleaned/cleaned_distinction-env-override.csv`
