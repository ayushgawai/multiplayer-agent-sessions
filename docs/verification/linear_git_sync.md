# Linear <-> Git Synchronization Audit

This table tracks all Linear tasks (DAT project) mapped directly to their git commits, PRs, and live status on `main`.

| Linear ID | Title | Owner | Status | Linked Commits / PRs | Notes |
|---|---|---|---|---|---|
| **DAT-55** | M1 Full Training Pipeline & Checkpointing with QLoRA | Ayush Gawai | `Done` | `8704c3b`<br>`d214437`<br>`2318d8f`<br>`5acff8c`<br>`ee9f28f`<br>Direct commit | Full 4-bit NF4 QLoRA training script implemented and tested. Completed 50-step high power training run on RTX 5080 with loss reduced from 3.90 to 2.14; checkpoint-50 saved and verified. |
| **DAT-57** | M1 GPU Feasibility Verification | Ayush Gawai | `Done` | `ec4a7de`<br>`8944893`<br>`7cdaf46`<br>Direct commit | Executed and verified all 9 GPU infrastructure assertions on RTX 5080 Laptop GPU. Run manifest committed to docs/verification/m1_verification/run_manifest.json. |
| **DAT-11** | Download QMSum Dataset and Freeze m1_v1 Splits | Naman Chheda / Ayush Gawai | `Done` | `330603f`<br>Direct commit | Downloaded Yale-LILY QMSum (232 meetings, 1,810 query-summary pairs). Generated and froze splits: train (1,257), val (272), test (281) with SHA-256 manifest. |
| **DAT-40** | M3 Stub Label Renamed to Escalate | Manav Patel | `Done` | `2f5b531`<br>PR #11 | Replaced escalate_human with escalate in M3 serving stub to match the candidate matrix. |
| **DAT-15** | Client Scaffold (Mock + Real Session API) | Manav Patel | `Done` | `380a496`<br>PR #12 | React 18 + Vite client scaffold supporting both mock and live session-service environments. |
| **DAT-16** | Yjs CRDT Editor Binding & y-websocket Server | Manav Patel | `Done` | `b64b1b9`<br>`8b4a65e`<br>`86f93fa`<br>PR #13 | TipTap editor bound to shared Yjs document with automatic bridge to session-service event log. |
| **DAT-17** | Live Presence, Carets, and Participant Colour Registry | Manav Patel | `Done` | `186a5cb`<br>`2ae43df`<br>`12e771a`<br>PR #14 | Presence bar, cursor tracking, and deterministic user color assignment. |
| **DAT-52** | ADR-003: MAST Prediction Record | Manav Patel | `Done` | `19a115c`<br>`955e7b3`<br>PR #16 | Decision record freezing predictions.jsonl, failures.jsonl, and run_manifest.json formats. |
| **DAT-37** | MAST Classification Evaluation Metrics | Pramod Dindukurthi | `Done` | `791b3de`<br>`0741883`<br>PR #3 | Accuracy, macro/micro F1, Cohen kappa, and CI workflow for eval/tests. |
| **DAT-34** | Resumable MAST Batch Execution | Shriram Dundigalla | `Done` | `caa174f`<br>`3ff7ced`<br>PR #5 | Resumable batch loop over MAST evaluation traces. |
| **DAT-35** | MAST Run Manifest Provenance & Redaction | Shriram Dundigalla | `Done` | `caa174f`<br>PR #5 | Run provenance metadata generator and secret redaction. |
| **DAT-28** | Download and Extract MAST Dataset from Hugging Face | Naman Chheda | `Done` | `eb8a5f9`<br>PR #1 | Download script for mcemri/MAD with checksum verification (1,642 traces). |
| **DAT-29** | MAST Dataset Schema and Data Dictionary | Naman Chheda | `Done` | None<br>PR #2 | Committed data dictionary and taxonomy documentation for MAST baseline. |
| **DAT-30** | MAST Frozen Evaluation Manifest | Naman Chheda | `Done` | None<br>PR #4 | Evaluation manifest linking frozen dataset to benchmark expectations. |
| **DAT-18** | LangGraph Plan-Act-Observe Loop Runtime | Shriram Dundigalla | `In Review` | `bafdab4`<br>PR #6 | Agent runtime loop on fixture. Open in PR #6. |
| **DAT-56** | Learning-Event Contract & Approved-Memory Store | Shriram Dundigalla | `In Review` | None<br>PR #15 | Learning event schema and memory persistence. Open in PR #15. |
