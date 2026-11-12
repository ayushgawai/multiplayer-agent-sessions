# PR review log

Merge owner: Naman. One row per reviewed PR, newest at the bottom. Full reviews follow the table.
Rules: a review names the head sha it covers, and a later push makes that review stale. Findings are
marked verified (checked against GitHub data, a file, or a run) or inferred. Reviews are added to this file
through their own branch and PR, never directly on main.

| PR | Title | Author | Reviewer | Date | Head sha reviewed | Verdict | Blocking findings | How resolved | Merge commit |
|---|---|---|---|---|---|---|---|---|---|
| #20 | DAT-55: freeze M1 task, candidate and evaluation contract | Pramod | Naman | 2026-11-11 | f2b4d47 | Changes requested (posted on GitHub) | F1: gate aggregation and tie-margin units unstated | Fixed on c2028dd (author comment 2026-11-12 00:46 UTC; checked against main). F6 (Ayush review of his paths) was requested but not given before merge | f999aba |
| #29 | Add Workbook 2 figure generation for report sections 3 and 4 | Shriram | Naman | 2026-11-11 | badaf77 | Changes requested (not posted) | F1 duplicate Workbook 2 with #35; F2 unresolved placeholders | Open | none |
| #35 | Workbook 2 (T4.A6), Team Meeting 2 slides, AWS/Airflow justification | Ayush | Naman | 2026-11-11 | 6c3f0ab | Approve after small changes (not posted) | None blocking. F1 captions cite a generator script that is not in this PR | Open | none |

## PR #20 (DAT-55), reviewed on head f2b4d47

Verdict: changes requested. Posted 2026-11-11 as a GitHub review with a separate comment of instructions for the fixing agent.

| Id | Severity | Where | Finding | Status |
|---|---|---|---|---|
| F1 | Blocking | `eval/configs/m1-contract.yaml` (selection block), ADR-005 | Gates did not say per seed or three-seed mean; one tie margin of 0.01 was applied to 0 to 1 metrics and to ROUGE-L on a 0 to 100 scale | Fixed: `every_seed`, `matched_seed`, per-metric margins 0.01, 0.01, 1.0 |
| F2 | Should-fix | ADR-005 | "Covered", "supported", "correct supporting ids" undefined | Fixed: defined, annotation schema deferred explicitly |
| F3 | Should-fix | `eval/contracts/m1.py` | `event_type` was free-form | Fixed: `Literal` of the 12 service types, with a test |
| F4 | Should-fix | ADR-005 | No adapter rules for `SessionEvent` and QMSum rows | Fixed: adapter section and tests |
| F5 | Should-fix | CONTEXT.md, ADR-005 | Unsourced "RTX 4090/5090 pool" | Fixed: removed |
| F6 | Should-fix | Ayush-owned paths | Edited without Ayush's review | Not fixed: requested, no review submitted before merge |
| F7 | Nit | `eval/tests/test_m1_contract.py` | CRLF failure on Windows, vacuous id check | Fixed |
| F8 | Nit | `validate_m1_pair` | Thin; untested branches | Fixed: tests added |
| F9 | Nit | branch, ADR-005 | Behind main, ADR-004 not cited | Fixed except the ADR status line, still "Proposed" |

Open item after merge: PR #25 (`eval/compare.py`) still applies the gates to the three-seed mean, which the merged ADR-005 forbids.

## PR #29, reviewed on head badaf77 (Shriram)

Not posted to GitHub. Files: 9, all under `docs/reports/` (my area): `T4.A5.docx`, `T4.A5.pdf`, figures 3 to 8, `generate_t4a5_figures.py`.

**Verdict: changes requested.** The numbers are right, but the document is not finished and it competes with #35.

| Id | Severity | File and place | Finding | Fix | Basis |
|---|---|---|---|---|---|
| F1 | Blocking | `docs/reports/T4.A5.docx` vs #35 `T4.A6.docx` | Two Workbook 2 drafts exist. The file name `T4.A5` is also the Progress Report 2 name in Linear (DAT-60, "Progress Report 2 (T4.A5)"). #35 captions cite `generate_t4a5_figures.py`, which exists only in this PR | Team agrees one Workbook 2 file. Suggest #35 is canonical and this PR keeps only `generate_t4a5_figures.py` and the figures, or the script moves into #35 | Verified (file lists, Linear title) |
| F2 | Blocking | `T4.A5.docx`, text lines 71, 114, 132, 159, 160, 554 | Six unresolved `[OWNER: ...]` placeholders (raw record samples, composite-key example, session-shaped pair, split samples, session split note, section 1 and 2 revisions) | Fill them or remove them before submission. Raw samples can come from `data/mast/hf` and `data/qmsum` | Verified |
| F3 | Should-fix | `T4.A5.docx`, text line 132 | Says a session-shaped example does not exist yet. 18 smoke examples exist on main (PR #22, `fbb3fdf`) | Update the sentence and point to `data/m1_smoke/` as scripted examples | Verified on main |
| F4 | Should-fix | `T4.A5.docx`, 6 `INCLUDEPICTURE` fields | Fields point to `/Users/x-sdundigalla/Desktop/Major project/...`. Images are embedded so it renders, but "update fields" in Word would fail | Remove the fields or use embedded pictures only | Verified in document XML |
| F5 | Nit | `generate_t4a5_figures.py:207` | Meeting counts `{162, 35, 35}` are hard-coded, although the header says counts are not | Read them from `data/qmsum/STATS.md` | Verified |
| F6 | Nit | `generate_t4a5_figures.py` docstring | Cites Linear DAT-62. I could not retrieve DAT-62 | Confirm the id | Inferred (may exist but not visible to me) |

Checked and correct: 1,642 raw and 1,638 scored; 56 null cells in 4 fully-null records; 206 distinct `trace_id` values; 232 meetings = 162 + 35 + 35; pairs 1,257 + 272 + 281 = 1,810; MAST and taxonomy pins; figure 4 and figure 5 values (figure 5 is labelled "of 1,642", the raw count, so ChatDev is 330 there). The document makes no claim about any PR being merged or open, and does not cite the smoke hashes.

Message for the author:

> Shriram, review of #29 on head badaf77. The numbers match the repo (1,642 raw, 1,638 scored, 56 null cells, 1,257/272/281, 232 meetings). Four things before this can be the Workbook 2 source: (1) #35 contains a second Workbook 2, `T4.A6.docx`, and your file is named `T4.A5`, the Progress Report 2 name. Agree with Ayush and me which file is canonical. #35's captions cite your `generate_t4a5_figures.py`, so that script has to land too. (2) Six `[OWNER: ...]` placeholders are still in the document (text lines 71, 114, 132, 159, 160, 554); fill or remove them. (3) Text line 132 says no session-shaped example exists. The 18 smoke examples in `data/m1_smoke/` are on main now. (4) The six `INCLUDEPICTURE` fields point at `/Users/x-sdundigalla/...`; remove them. Nit: `generate_t4a5_figures.py:207` hard-codes the meeting counts.

## PR #35, reviewed on head 6c3f0ab (Ayush)

Not posted to GitHub. Files: 19, of which 17 are under `docs/reports/` (my area) and 2 under `docs/slides/` (Manav's). The PR description gives a reason: it is the team workbook. The three duplicated figures (`fig4_m1_splits.png`, `fig5_mast_composition.png`, `fig6_qmsum_distributions.png`) are byte-identical to #29's (same SHA-256), so they do not conflict.

**Verdict: approve after small changes.** Every count I recomputed from the repo matches.

| Id | Severity | File and place | Finding | Fix | Basis |
|---|---|---|---|---|---|
| F1 | Should-fix | `T4.A6.docx` captions for Figures 4 to 6 | Captions say "Generated by `docs/reports/generate_t4a5_figures.py`", but that script is not in this PR (only in #29) | Merge #29's script first, or include it here | Verified (file list) |
| F2 | Should-fix | `T4.A6.docx`, Figure 4 and the sentence "82.6% of scorable traces ... GPT-4o 45.8%" | Figure 4 shows raw counts of 1,642 (ChatDev 330, CodeLlama 200). The text and Table 32 use 1,638 scorable (ChatDev 326, CodeLlama 196). 751/1,642 is 45.7%, not 45.8% | Say "raw" next to the figure reference, or regenerate the figure on the 1,638 | Verified by recomputing from `mast_clean_summary.csv` |
| F3 | Should-fix | Gap register, owner rows | Commitments and "Done" statuses are written in other people's names, for example "Naman, first sessions by 2 Dec 2026" | Each owner confirms their row. I have not agreed that date | Verified in text; commitments unconfirmed |
| F4 | Nit | `T4.A6.docx`, software line | "BM25 ranker ... (DAT-58, in review)". PR #26 is a draft | Say "draft PR #26" | Verified (draft = true) |
| F5 | Nit | Figure numbers | `fig4_m1_splits.png` is captioned Figure 5 and `fig5_mast_composition.png` Figure 4. #29 numbers them the other way. A stray "Figure 4." line sits in the population-gap table | Pick one numbering and delete the stray line | Verified in text |
| F6 | Nit | ADR-005 row, "merged 11 Nov 2026" | GitHub shows the merge at 2026-11-12 01:54 UTC. That is 11 Nov in US Pacific time | Add the time zone | Verified timestamp; time zone is an inference |
| F7 | Note | Table 19, section 4.2 | Cites #33 (pipeline) and #32 (S3 checkpoints), both still open. Table 19 counts match `infra/warehouse/SAMPLE_RUN.md` on #33's branch (1,638, 5,141, 1,810). Wording is correct today ("pull request #33") | Re-check at merge time | Verified on #33's branch |

Copilot bot: one review, "unable to review ... insufficient remaining quota", no inline comments. Nothing to accept or reject.

Checked and correct: 1,642 raw / 1,638 scorable / 4 excluded; 56 null cells; 1,638 x 14 = 22,932; 1,642 x 14 = 22,988; 5,141 positive labels; 0.24% excluded; prevalence 40.5% (1.3) down to 1.5% (2.4); 401 traces (24.5%) with no failure and 1,237 (75.5%) with at least one; three frameworks 82.6%; QMSum split medians and maxima (spans, context length, query length); reconciling 1,257 + 272 + 281 = 1,810; smoke example `smoke-s01-x1` (16 events, 5 critical facts, events 011 and 012, fact `smoke-s01-f04`); 12 scripted sessions and 18 examples; CI steps listed in section 4.2; the DAT-61 harness note (PR #25's `compare.py` still applies gates to the mean, so the statement is true today).

Not checked: Figure 9 correlations, the 6 second DuckDB timing, the risk-register trigger, the slide deck `T4-Workbook2.pptx`, references 18 to 27, and tables not named above.

Message for the author:

> Ayush, review of #35 on head 6c3f0ab. I recomputed the data numbers from the repo and they all match (1,638 scorable, 22,932 label rows, 5,141 positives, 82.6% and 45.8%, the QMSum medians, the smoke example). Please fix before merge: (1) the captions for Figures 4 to 6 cite `generate_t4a5_figures.py`, which is only in #29; land it first or include it. (2) Figure 4 is the raw 1,642 (ChatDev 330) while the text quotes 1,638-based shares (GPT-4o 45.8%, 751/1,642 is 45.7%); say "raw" or regenerate. (3) The gap register commits owners to dates, for example my first sessions by 2 Dec; each owner must confirm their own row. Nits: DAT-58 is a draft, not in review; Figure 4 and 5 numbers are swapped against #29 and a stray "Figure 4." line sits in the gap table; add a time zone to "merged 11 Nov". docs/reports is mine, so this review is my sign-off once these are done. Manav should look at the two files in docs/slides.
