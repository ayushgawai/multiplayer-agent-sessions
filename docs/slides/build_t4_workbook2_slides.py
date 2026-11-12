"""Build docs/slides/T4-Workbook2.pptx. Usage: python build_t4_workbook2_slides.py <figure-dir> <out.pptx>"""
import sys
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.util import Inches, Pt

FIG = Path(sys.argv[1])
OUT = sys.argv[2]
NAVY, BLUE, GREY, AMBER = RGBColor(0x1F, 0x4E, 0x79), RGBColor(0x2E, 0x75, 0xB6), RGBColor(0x59, 0x59, 0x59), RGBColor(0x8A, 0x64, 0x14)
prs = Presentation()
prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
n = 0


def text(slide, x, y, w, h, lines, size=18, color=GREY, bold=False):
    tf = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h)).text_frame
    tf.word_wrap = True
    for i, line in enumerate([lines] if isinstance(lines, str) else lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.space_after = Pt(size * 0.45)
        r = p.add_run()
        r.text = line
        r.font.size, r.font.bold, r.font.color.rgb, r.font.name = Pt(size), bold, color, "Calibri"
    return tf


def slide(title, rubric=None, notes=""):
    global n
    n += 1
    s = prs.slides.add_slide(prs.slide_layouts[6])
    text(s, 0.5, 0.3, 10.6, 0.9, title, 30, NAVY, True)
    if rubric:
        text(s, 10.6, 0.42, 2.4, 0.5, rubric, 13, BLUE, True)
    bar = s.shapes.add_shape(1, Inches(0.5), Inches(1.15), Inches(12.33), Inches(0.04))
    bar.fill.solid()
    bar.fill.fore_color.rgb = BLUE
    bar.line.fill.background()
    text(s, 0.5, 7.0, 9, 0.35, "Team 4  |  DATA 298A  |  Workbook 2  |  12 Nov 2026", 11)
    text(s, 12.2, 7.0, 0.8, 0.35, str(n), 11)
    s.notes_slide.notes_text_frame.text = notes
    return s


def pic(s, name, x, y, w):
    s.shapes.add_picture(str(FIG / name), Inches(x), Inches(y), width=Inches(w))


def table(s, x, y, w, rows, widths, size=13, row_h=0.42):
    t = s.shapes.add_table(len(rows), len(rows[0]), Inches(x), Inches(y), Inches(w), Inches(row_h * len(rows))).table
    for j, cw in enumerate(widths):
        t.columns[j].width = Inches(cw)
    for i, row in enumerate(rows):
        for j, v in enumerate(row):
            c = t.cell(i, j)
            c.text = str(v)
            c.margin_left = c.margin_right = Inches(0.07)
            c.margin_top = c.margin_bottom = Inches(0.03)
            for p in c.text_frame.paragraphs:
                for r in p.runs:
                    r.font.size, r.font.name = Pt(size), "Calibri"
                    r.font.bold = i == 0
                    r.font.color.rgb = RGBColor(255, 255, 255) if i == 0 else RGBColor(0x26, 0x26, 0x26)
            c.fill.solid()
            c.fill.fore_color.rgb = NAVY if i == 0 else (RGBColor(0xF2, 0xF6, 0xFB) if i % 2 else RGBColor(255, 255, 255))


# 1 ------------------------------------------------------------------
s = slide("Multiplayer Agents: Workbook 2", notes="Sections 3 and 4 of the report: data engineering and model development, plus the pipeline demo.")
text(s, 0.5, 1.6, 12, 1.2, "A shared live session layer for human-agent collaboration", 26, NAVY)
text(s, 0.5, 2.7, 12, 2.5, ["Data engineering (section 3) and model development (section 4)",
                            "Ayush Gawai, Naman Vipul Chheda, Manav Patel, Shriram Dundigalla, Pramod Satya Dindukurthi",
                            "Section 21, Topic 4. Advisor: Prof. Simon Shim",
                            "github.com/ayushgawai/multiplayer-agent-sessions"], 18)

# 2 ------------------------------------------------------------------
s = slide("Since Workbook 1", notes="Be exact about what is merged and what is in review. No model results exist yet.")
table(s, 0.5, 1.5, 12.3,
      [["On main", "In review", "Not started"],
       ["Session service, event log, client, CRDT editing, presence", "Shared M1 evaluation harness (DAT-61): fixes requested", "Product-session recording (0 sessions)"],
       ["LangGraph agent runtime (DAT-18, merged 11 Nov)", "BM25 baseline m1-a (DAT-58)", "Model 2 and Model 4 configurations (298B)"],
       ["MAST download, audit, manifest, prompt, parser, batch, metrics", "M1 candidate train and inference paths (m1-b, c, d)", "Cloud deployment (deferred to 298B)"],
       ["QMSum download, frozen m1_v1 splits; M1 contract ADR-005", "Warehouse pipeline demo (PR #33); CI and lock refresh (PR #32)", ""],
       ["M1 smoke dataset: 18 examples, 12 sessions (DAT-53)", "Learning-event store (DAT-56)", ""]],
      [4.3, 4.3, 3.7], 13, 0.62)
text(s, 0.5, 5.6, 12.3, 1, "No bake-off result and no baseline agreement figure exists yet. Everything on the following slides is data, design and committed evaluation rules.", 16, AMBER, True)

# 3 ------------------------------------------------------------------
s = slide("Data process: three sources, five steps", "3.1 Data Process", "Three paths never mix. Amber is planned.")
pic(s, "fig03_data_process.png", 0.5, 1.35, 9.3)
text(s, 10.0, 1.5, 3.0, 5, ["Public data is never committed: it is rebuilt from pinned revisions.",
                           "Nothing is dropped silently.",
                           "Test data is read once."], 16)

# 4 ------------------------------------------------------------------
s = slide("Data collection", "3.2 Data Collection")
table(s, 0.5, 1.4, 6.6,
      [["Source", "Quantity", "Role"],
       ["MAST-Data (HF mcemri/MAD, pinned 95118ac9), CC-BY-4.0", "1,642 traces, 199.6 MB; 19 human-labelled", "Baseline corpus"],
       ["QMSum (Yale-LILY), MIT", "232 meetings, 129,177 turns, 1,810 query pairs", "Model 1 supervision"],
       ["Smoke fixtures (team-authored)", "18 examples, 12 sessions", "Pipeline validation only"],
       ["Product sessions (event log)", "0 recorded; target about 30", "Winner selection, Models 2 to 4"]],
      [3.0, 2.2, 1.4], 12, 0.75)
pic(s, "fig5_mast_composition.png", 7.3, 1.5, 5.7)
text(s, 7.3, 4.0, 5.7, 2.5, ["Every file verified by SHA-256; MAST count equals the paper's 1,642.",
                            "7 frameworks, 5 language models, 8 benchmarks."], 15)

# 5 ------------------------------------------------------------------
s = slide("Pre-processing: rules that run, and what each removed", "3.3 Pre-processing",
          "Four rows removed in total. The value is the guarantee, not the volume.")
table(s, 0.5, 1.4, 12.3,
      [["Rule", "Tool", "Effect"],
       ["Digest and record count equal the pinned values", "download_mast.py, download_qmsum.py", "Pass; 0 removed"],
       ["Record key (trace.key, trace_id) is unique", "eda_mast.py", "1,642 unique; 0 duplicates"],
       ["Each of 14 labels is exactly 0, 1 or null", "eda_mast.py", "0 invalid in 22,988 cells"],
       ["A null label stays null, never 0", "eda_mast.py", "56 null cells preserved"],
       ["Exclude a record only if all 14 labels are null", "eda_mast.py", "4 removed (0.24%)"],
       ["QMSum: non-empty query, context, summary; unique ids", "make_splits.py, data tests", "0 removed of 1,810"]],
      [5.8, 3.6, 2.9], 14, 0.55)
text(s, 0.5, 5.5, 12.3, 1.2, ["The four excluded traces are named in the committed summary: ChatDev_ProgramDev-v2_CodeLlama, traces 4, 72, 73, 81.",
                             "Ten quality gates pass; two runs give byte-identical summaries."], 15)

# 6 ------------------------------------------------------------------
s = slide("Transformation: same facts, usable shape", "3.4 Transformation")
table(s, 0.5, 1.4, 12.3,
      [["From", "To", "Why"],
       ["MAST nested mast_annotation", "14 columns fail_1_1 to fail_3_3, n_failures, 3 category counts (1,638 x 26)", "A flat table can be aggregated and compared with the paper's categories"],
       ["MAST trajectory text (up to 2.0M chars)", "trace_chars", "Analysis table is 142 KB, not 199.6 MB"],
       ["QMSum meeting with many queries", "One CatchupExample per query (1,810 rows)", "Model 1 answers one query at a time"],
       ["CatchupExample context spans", "m1-input-v1: ordered events with ids row:span:0000", "Same input shape as live sessions; claims must cite event ids"],
       ["Reference summary", "Kept outside the input", "A target inside the input leaks the answer"]],
      [3.4, 4.9, 4.0], 13, 0.7)
text(s, 0.5, 5.9, 12.3, 0.8, 'Example event: {"event_id": "qmsum_test_9_s3:span:0000", "sequence": 0, "event_type": "doc_update", "text": "Grad B: And they wouldn\'t look pretty . So ."}', 13)

# 7 ------------------------------------------------------------------
s = slide("Prepared splits and the leakage check", "3.5 Data Preparation",
          "Not stratified: we inherit the official QMSum partition by meeting.")
table(s, 0.5, 1.4, 7.0,
      [["Split", "Rows", "%", "Meetings", "Leakage result"],
       ["Train", "1,257", "69.4", "162", "0 meetings, ids, contexts shared"],
       ["Validation", "272", "15.0", "35", "0 shared"],
       ["Test", "281", "15.5", "35", "0 shared; read once"]],
      [1.2, 0.9, 0.7, 1.1, 3.1], 14, 0.5)
pic(s, "fig4_m1_splits.png", 7.7, 1.4, 5.3)
text(s, 0.5, 3.7, 7.0, 3, ["Frozen in data/splits/m1_v1/ with SHA-256 manifest (commit 330603f, 21 Oct); digests recomputed and match.",
                          "Found: two reference-summary strings recur across splits (4 of 1,810 rows, 0.22%). Upstream duplicates, left in place and reported.",
                          "The split that selects the winner (m1_session_v1, by session_id) is not prepared: no sessions yet."], 15)

# 8 ------------------------------------------------------------------
s = slide("Statistics: Model 1 supervision", "3.6 Data Statistics")
pic(s, "fig6_qmsum_distributions.png", 0.5, 1.4, 8.4)
text(s, 9.1, 1.5, 3.9, 5, ["Summaries are short: median 59 to 68 words. One missing fact is a large share of the answer.",
                          "Context is right-skewed: median about 660 words, 95th percentile over 10,000.",
                          "Splits overlap closely, although we did not stratify."], 16)
text(s, 0.5, 5.4, 8.4, 1.2, "These three facts drive the metric choices: recall before overlap, latency at p95, truncation as a named failure.", 16, NAVY, True)

# 9 ------------------------------------------------------------------
s = slide("Statistics: MAST imbalance and co-occurrence", "3.6 Data Statistics")
pic(s, "fig06_mast_prevalence.png", 0.4, 1.35, 6.9)
pic(s, "fig08_mast_correlation.png", 7.5, 1.3, 5.5)
text(s, 0.4, 5.2, 6.9, 1.6, ["Prevalence from 40.5% (1.3) to 1.5% (2.4): 664 against 24 traces.",
                            "24.5% of traces have no failure; mean 3.14 per trace.",
                            "All pairwise correlations positive (0.04 to 0.66): accuracy alone would mislead."], 14)

# 10 -----------------------------------------------------------------
s = slide("Coverage gaps and who they would disadvantage", "3.6 Data Statistics")
table(s, 0.5, 1.4, 12.3,
      [["Gap", "Who is disadvantaged", "What we do"],
       ["QMSum is English meeting speech in three settings", "Other languages; terse tool-and-code sessions", "Supervision only; cannot select the winner"],
       ["QMSum has no status, owner or evidence labels", "Anyone trusting 'blocked' or 'owner' in a catch-up", "Safety gates measured on annotated product sessions"],
       ["MAST: three frameworks are 82.6% of traces", "Users of under-represented frameworks", "Per-framework results with sample sizes"],
       ["MAST has agents only, no multi-human steering", "Exactly our target teams", "Baseline and taxonomy only, not training data"],
       ["Only 19 human-labelled MAST traces", "Readers taking agreement as precise", "Sample size and 95% CI beside every value"],
       ["No product sessions yet; first ones from five team members", "Non-experts, larger teams, other domains", "State the population with every result"]],
      [4.6, 3.9, 3.8], 13, 0.62)

# 11 -----------------------------------------------------------------
s = slide("Four models and one reproduced baseline", "4.1 Model Proposals",
          "Sixteen candidate configurations plus the baseline. The baseline is not one of the four.")
table(s, 0.5, 1.4, 12.3,
      [["#", "Model", "Concept", "Candidates", "Built", "Owner"],
       ["1", "M1 catch-up", "Structured, evidence-cited summary of session state", "BM25; ModernBERT; Phi-4-mini QLoRA; Qwen3.5-4B QLoRA", "298A", "Ayush"],
       ["2", "M2 intent attribution", "Which participant an instruction addresses", "TF-IDF; DeBERTaV3; ModernBERT; Qwen head", "298B", "Naman"],
       ["3", "M3 merge arbitration", "Accept A, accept B, merge, or escalate", "Last-writer-wins; ModernBERT; Qwen LoRA; few-shot Qwen", "298B", "Manav"],
       ["4", "M4 decompose and route", "Task DAG and assignment", "Rules; planner + learned router; planner; single prompt", "298B", "Shriram"],
       ["-", "MAST LLM-as-a-Judge", "Reproduce Table 2, o1 few-shot: accuracy 0.94, F1 0.80, kappa 0.77", "Inference only", "298A", "Pramod"]],
      [0.4, 2.3, 3.9, 4.0, 0.8, 0.9], 13, 0.68)
text(s, 0.5, 5.75, 12.3, 1, "Every candidate is a YAML file pinning model repository and a 40-character revision; all share frozen data, one contract, one harness, seeds 13, 29, 47.", 15)

# 12 -----------------------------------------------------------------
s = slide("Model 1 in detail, and what is new", "4.1 Model Proposals")
table(s, 0.5, 1.4, 7.6,
      [["ID", "Candidate", "Role"],
       ["m1-a", "BM25 ranker + fixed template, CPU", "Transparent floor"],
       ["m1-b", "ModernBERT-base selector + same template", "Learned extractive arm"],
       ["m1-c", "Phi-4-mini-instruct, 4-bit QLoRA", "Compact generator"],
       ["m1-d", "Qwen3.5-4B, 4-bit QLoRA (r=16)", "Larger generator"]],
      [0.8, 4.4, 2.4], 14, 0.5)
text(s, 0.5, 4.2, 7.6, 2.5, ["Each neighbouring pair isolates one question: learned relevance (a to b), generation (b to c), capacity (c to d).",
                            "3 epochs, 4,096 tokens, effective batch 16, adapters only."], 15)
text(s, 8.4, 1.4, 4.6, 5.2, ["What is new",
                            "1. Evidence-cited by construction: a claim without a valid source event id is invalid, not low-scoring.",
                            "2. Safety-gated before quality-ranked: one unsafe seed disqualifies.",
                            "3. Approved memory can change behaviour but can never be evidence."], 16, NAVY)

# 13 -----------------------------------------------------------------
s = slide("Supporting platform", "4.2 Model Supports",
          "Owners communicate by network call or committed file, never shared memory.")
pic(s, "fig11_platform_architecture.png", 2.3, 1.3, 7.55)
text(s, 10.0, 1.6, 3.1, 4.5, ["Python 3.11, FastAPI, PostgreSQL 16, Redis 7, React 18, Yjs, LangGraph.",
                             "Training: one RTX 5080 Laptop GPU, 16 GB, university lab, $0.",
                             "CI on every pull request."], 14)

# 14 -----------------------------------------------------------------
s = slide("Machine-learning data flow and selection rule", "4.2 / 4.3")
pic(s, "fig12_ml_data_flow.png", 0.5, 1.3, 7.6)
pic(s, "fig13_selection_rule.png", 0.5, 4.35, 7.6)
text(s, 8.4, 1.5, 4.6, 5, ["Preferred, stated before results: a QLoRA generator.",
                          "It loses if, on any one seed, unsupported claims exceed 2% or are worse than BM25; or schema validity is under 98%; or attribution or status is under 95%.",
                          "It loses a tie within 0.01 recall on latency and memory.",
                          "If nothing passes, nothing is promoted."], 15)

# 15 -----------------------------------------------------------------
s = slide("Metrics committed before results", "4.4 Evaluation Methods",
          "ROUGE-L is reported but is no longer the primary metric: carry-forward from Workbook 1.")
table(s, 0.5, 1.4, 12.3,
      [["Model", "Metric", "Why", "Committed"],
       ["M1", "Critical-fact recall (primary)", "A catch-up that omits the blocker has failed", "ADR-005, 22 Oct"],
       ["M1", "Gates: unsupported claims <= 2%, attribution >= 95%, status >= 95%, schema >= 98%", "Measured on every seed", "ADR-005, 22 Oct"],
       ["M1", "BERTScore-F1, ROUGE-L, latency p50/p95, peak VRAM, human edit rate", "Ranking after gates; tie-breaks; cost to the user", "ADR-004/005"],
       ["M2", "Macro-F1 with per-class F1", "Imbalanced classes", "Workbook 1, 7 Oct"],
       ["M3", "Macro-F1, harmful-merge rate, escalation precision and recall", "A wrong merge is worse than an escalation", "m3 configs, 8 Oct"],
       ["M4", "DAG validity (gate), routing accuracy, completion, latency, cost", "An invalid plan cannot run", "Workbook 1, 7 Oct"],
       ["Baseline", "Accuracy, precision, recall, F1, Cohen's kappa", "The paper's five figures, with n and 95% CI", "Workbook 1, 7 Oct"]],
      [1.1, 5.2, 4.0, 2.0], 13, 0.56)
text(s, 0.5, 6.1, 12.3, 0.6, "Three seeds, per-seed values and mean, no pooling across seeds. Test split read once.", 15, NAVY, True)

# 16 -----------------------------------------------------------------
s = slide("Pipeline demo: source to warehouse", "4.5 Data Pipeline Demo",
          "Live: run pipeline.py twice, then --report. About 6 seconds per run.")
table(s, 0.5, 1.4, 6.3,
      [["Layer", "Tables", "Rows"],
       ["raw", "mast_traces, qmsum_examples", "1,642; 1,810"],
       ["staging", "mast_traces_clean, mast_labels_long, qmsum_examples_clean", "1,638; 22,932; 1,810"],
       ["marts", "fact_trace, fact_trace_failure, fact_m1_example, 4 dimensions", "1,638; 5,141; 1,810"],
       ["meta", "quality_checks, pipeline_runs", "19 and 4 per run"]],
      [1.0, 3.6, 1.7], 13, 0.66)
text(s, 7.1, 1.4, 5.9, 5.3, ["python data/scripts/download_mast.py",
                            "python infra/warehouse/pipeline.py",
                            "python infra/warehouse/pipeline.py --report",
                            "",
                            "Ingestion: pinned sources, SHA-256 verified, landed with digest and load time.",
                            "Transformation: validate, clean, star schema.",
                            "Warehouse: DuckDB, 14 tables.",
                            "Monitoring: 19 of 19 quality gates pass; per-stage run history with rows in and out, duration, status, git commit.",
                            "Management: fail-fast, idempotent reruns, tests in CI."], 14)

# 17 -----------------------------------------------------------------
s = slide("Why not AWS or Airflow, for now", "4.2 Model Supports",
          "Declined for stated reasons, with the conditions that would change the decision.")
table(s, 0.5, 1.4, 12.3,
      [["Question", "Our workload", "Decision"],
       ["Is anything scheduled?", "No. Two static datasets pinned to a commit", "A scheduler would be idle; code changes trigger CI"],
       ["Is the graph complex?", "Four stages in a line", "Ordered functions with fail-fast; each maps to one Airflow task"],
       ["Is the data large?", "About 220 MB; pipeline runs in about 6 s", "DuckDB on a laptop; a cloud warehouse adds cost, not capability"],
       ["Cloud compute?", "One 16 GB GPU, university lab, $0", "No cloud GPU"],
       ["Reproducibility?", "Clone and two commands, no account", "Local-first is verifiable by anyone"]],
      [2.6, 4.6, 5.1], 14, 0.6)
text(s, 0.5, 5.3, 12.3, 1.5, ["We adopt them when: (1) sessions are recorded more often than weekly, so the event-log export becomes a real schedule; (2) the first participant outside the team joins (298B study, FR-8).",
                             "Already prepared: checkpoint utility accepts s3:// URIs (PR #32); layers map to S3, Airflow tasks and a cloud warehouse."], 14)

# 18 -----------------------------------------------------------------
s = slide("Carry-forward and next steps", notes="Honest list. The session corpus is the critical dependency.")
table(s, 0.5, 1.4, 12.3,
      [["Item", "Status", "Owner", "Target"],
       ["M1 candidates changed: BM25, ModernBERT, Phi-4-mini, Qwen3.5-4B", "Done (ADR-005)", "Ayush, Pramod", "11 Nov"],
       ["M1 selection: safety gates, then critical-fact recall (was ROUGE-L)", "Done (ADR-005)", "Pramod", "11 Nov"],
       ["Product-session corpus", "0 sessions; risk trigger fired; fallback in effect", "Naman", "2 Dec"],
       ["Shared harness end to end", "In review; per-seed gate fix needed", "Pramod", "18 Nov"],
       ["M1 bake-off and winner", "At risk: needs the annotated session split", "Ayush", "7 Dec"],
       ["MAST judge environment and final runs", "Open", "Ayush, Shriram", "2 Dec"],
       ["Cloud deployment (FR-8)", "Deferred to the 298B study", "Ayush", "298B"]],
      [5.6, 3.9, 1.6, 1.2], 13, 0.58)

s = slide("Questions")
text(s, 0.5, 2.6, 12.3, 2, ["Workbook: docs/reports/T4.A6.docx", "Pipeline demo: infra/warehouse/README.md", "Decisions: docs/decisions/ADR-001 to ADR-005"], 22, NAVY)
prs.save(OUT)
print("saved", OUT, n, "slides")
