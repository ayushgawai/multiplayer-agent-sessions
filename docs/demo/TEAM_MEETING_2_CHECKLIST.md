# Team Meeting 2 (12 Nov): who does what

Everyone: `git pull` on `main` tonight. The talk is about 7 minutes plus the live pipeline demo. Each person speaks once, in order: Manav, Naman, Shriram, Ayush, Pramod.

## Message to the team

Hi all, here is the plan for tomorrow. Please do your part tonight and reply "done" in the group.

**Everyone (10 minutes tonight)**
1. `git pull` on `main`.
2. Open `docs/presentation-wb2/presenter.html` in Chrome. Use the arrow keys. Find the slides with your name in the top bar and read your notes out loud once with a timer. The amber line shows your time. The blue blocks are answers for questions: do not read them aloud, but know them.
3. Skim your sections of `docs/reports/T4.A6.docx` and tell Ayush tonight if a number or a date in your name is wrong.

**Ayush: runs the slides** (slides 11, 12, 13)
- Laptop on the projector. Open `presenter.html`, click "Open the room window", drag that window to the projector and press F for full screen (it must be the same Chrome profile on the same laptop). Arrow keys in either window move both.
- Backup if the HTML deck misbehaves: `docs/slides/T4-Workbook2.pptx` (same slides, notes in the notes pane).
- Keep `docs/reports/T4-TA-aws-airflow-justification.md` open in a tab for the AWS and Airflow question.

**Shriram: runs the pipeline demo** (slides 7, 8, 9, 10: transformation, splits, statistics, then the live demo)
- Tonight, on the laptop you will demo from:
  ```
  git pull
  pip install -r requirements.txt
  python data/scripts/download_mast.py        # about 200 MB, one time
  python infra/warehouse/pipeline.py          # must end with: SUCCESS, all 19 checks PASS
  python infra/warehouse/pipeline.py --report
  ```
- Tomorrow, before we start: open a terminal at the repo root with the virtualenv active, font size large, and run the pipeline once so the second run in the demo shows history. Keep that terminal open.
- In the demo: run `python infra/warehouse/pipeline.py`, point at the four stages and the PASS lines, then run it with `--report` and point at the run history table.
- If it fails live: open `infra/warehouse/SAMPLE_RUN.md` and walk through the saved output. Do not debug in front of the room.

**Manav: prototype** (slides 1, 2, 3: opening, what we built, prototype)
- You open the talk and the prototype view on slide 3 is yours, so you explain them. No live front-end demo is planned.
- Only if the professor asks to see it live, have this ready in three terminals (test it tonight):
  ```
  cd session-service && uvicorn app.main:app --reload --port 8000
  cd crdt-server && npm ci && npm run dev
  cd client && npm ci && npm run dev
  ```
  Then two browser tabs in the same session, type in both, and roll back to seq 2. If it does not work tonight, tell Ayush and we stay with screenshots.

**Naman: data** (slides 4, 5, 6)
- Keep `data/mast/STATS.md` and `data/splits/m1_v1/MANIFEST.json` open in an editor in case we are asked for checksums or split counts.
- Be ready for: why only 4 rows were removed, why 1,810 and not 1,808, and why the product-session row is still "planned".

**Pramod: evaluation and close** (slides 14, 15)
- Keep `docs/decisions/ADR-005-m1-experiment-contract.md` and `eval/configs/m1-contract.yaml` open.
- Be ready for: why ROUGE-L is not the primary metric, why gates apply per seed, and the status of the harness (in review, per-seed gate fix needed).

## Rules for the room

- We have no model results. Nobody quotes a model number. ModernBERT passing a short GPU smoke run is feasibility, not a result.
- The screenshots of the MAST viewer and M1-A use test data. Say so if asked.
- If you do not know an answer, say it is not settled and that it is tracked in the carry-forward table.
