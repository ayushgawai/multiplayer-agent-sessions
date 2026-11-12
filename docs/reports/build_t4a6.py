"""Build docs/reports/T4.A6.docx (Workbook 2) on top of the Workbook 1 styles."""
import json
import sys
from pathlib import Path

import docx
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt

R = Path(sys.argv[1])          # repo root
FIG = Path(sys.argv[2])        # directory with all figures
OUT = Path(sys.argv[3])
WH = json.loads(Path(sys.argv[4]).read_text()) if len(sys.argv) > 4 and Path(sys.argv[4]).exists() else None

d = docx.Document(str(R / "docs/reports/T4.A4.docx"))
body = d.element.body
for el in list(body):
    if el.tag != qn("w:sectPr"):
        body.remove(el)
for s in d.sections:
    for p in s.header.paragraphs:
        for r in p.runs:
            r.text = r.text.replace("Workbook 1", "Workbook 2")

J, C, L = WD_ALIGN_PARAGRAPH.JUSTIFY, WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.LEFT
N = {"t": 17, "f": 2}  # Workbook 1 ended at Table 17 and Figure 2


def P(text="", align=J, size=None, bold=False, italic=False, after=None, mono=False):
    p = d.add_paragraph()
    p.alignment = align
    p.paragraph_format.space_after = Pt(6 if after is None else after)
    runs(p, text, size, bold, italic, mono)
    return p


def runs(p, text, size=None, bold=False, italic=False, mono=False):
    """`code` segments are set in a monospace face."""
    for i, seg in enumerate(text.split("`")):
        if not seg:
            continue
        r = p.add_run(seg)
        r.bold, r.italic = bold or None, italic or None
        if size:
            r.font.size = Pt(size)
        if mono or i % 2:
            r.font.name = "Consolas"
            r._r.get_or_add_rPr().rFonts.set(qn("w:eastAsia"), "Consolas")
            r.font.size = Pt((size or 11) - 1)


def H(text, level):
    h = d.add_heading(text, level)
    # Keeps a heading from being stranded alone at the foot of a page.
    h.paragraph_format.keep_with_next = True
    return h


def B(items):
    for t in items:
        p = d.add_paragraph(style="List Paragraph")
        p.alignment = J
        p.paragraph_format.left_indent = Inches(0.3)
        p.paragraph_format.first_line_indent = Inches(-0.18)
        p.paragraph_format.space_after = Pt(3)
        runs(p, "•  " + t)


def shade(cell, fill):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)
    tcPr.append(shd)


def T(headers, rows, widths, caption=None, size=9, mono_cols=(), number=True):
    t = d.add_table(rows=1, cols=len(headers))
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    tblPr = t._tbl.tblPr
    tw = OxmlElement("w:tblW")
    tw.set(qn("w:w"), str(int(sum(widths) * 1440)))
    tw.set(qn("w:type"), "dxa")
    for old in tblPr.findall(qn("w:tblW")):
        tblPr.remove(old)
    tblPr.append(tw)
    lay = OxmlElement("w:tblLayout")
    lay.set(qn("w:type"), "fixed")
    tblPr.append(lay)
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        e = OxmlElement(f"w:{edge}")
        e.set(qn("w:val"), "single")
        e.set(qn("w:sz"), "4")
        e.set(qn("w:space"), "0")
        e.set(qn("w:color"), "808080")
        borders.append(e)
    tblPr.append(borders)
    mar = OxmlElement("w:tblCellMar")
    for side, v in (("top", 45), ("left", 80), ("bottom", 45), ("right", 80)):
        e = OxmlElement(f"w:{side}")
        e.set(qn("w:w"), str(v))
        e.set(qn("w:type"), "dxa")
        mar.append(e)
    tblPr.append(mar)

    def fill(cell, text, head, mono):
        cell.text = ""
        p = cell.paragraphs[0]
        p.alignment = L
        p.paragraph_format.space_after = Pt(0)
        lines = str(text).split("\n")
        for k, line in enumerate(lines):
            if k:
                p = cell.add_paragraph()
                p.alignment = L
                p.paragraph_format.space_after = Pt(0)
            runs(p, line, size + (1 if mono else 0), bold=head, mono=mono)

    for i, h in enumerate(headers):
        fill(t.rows[0].cells[i], h, True, False)
        shade(t.rows[0].cells[i], "D9E2F3")
    trPr = t.rows[0]._tr.get_or_add_trPr()
    rep = OxmlElement("w:tblHeader")
    rep.set(qn("w:val"), "true")
    trPr.append(rep)
    for row in rows:
        cells = t.add_row().cells
        for i, v in enumerate(row):
            fill(cells[i], v, False, i in mono_cols)
    for row in t.rows:
        for i, w in enumerate(widths):
            row.cells[i].width = Inches(w)
        cant = OxmlElement("w:cantSplit")
        row._tr.get_or_add_trPr().append(cant)
    if caption:
        if number:
            N["t"] += 1
            caption = f"Table {N['t']}. {caption}"
        p = P(caption, C, 10, italic=True, after=8)
        p.paragraph_format.space_before = Pt(4)
    else:
        P("", after=0)
    return t


def CODE(lines, size=7.5):
    """Verbatim console output. Not passed through runs(), so backticks stay literal."""
    for i, ln in enumerate(lines):
        p = d.add_paragraph()
        p.alignment = L
        p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.space_before = Pt(4 if i == 0 else 0)
        p.paragraph_format.line_spacing = 1.0
        r = p.add_run(ln or " ")
        r.font.name = "Consolas"
        r._r.get_or_add_rPr().rFonts.set(qn("w:eastAsia"), "Consolas")
        r.font.size = Pt(size)


def F(name, caption, width=6.5):
    N["f"] += 1
    p = d.add_paragraph()
    p.alignment = C
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.keep_with_next = True
    p.add_run().add_picture(str(FIG / name), width=Inches(width))
    P(f"Figure {N['f']}. {caption}", C, 10, after=8)


# ------------------------------------------------------------------ title block
P("DATA 298A MSDA Project I", C, 16, bold=True, after=2)
P("Workbook 2", C, 14, bold=True, after=6)
P("Multiplayer Agents: A Shared Live Session Layer for Human-Agent Collaboration", C, bold=True, after=6)
P("Team 4. Ayush Gawai, Naman Vipul Chheda, Manav Patel, Shriram Dundigalla, Pramod Satya Dindukurthi. "
  "Section 21, Topic 4. Advisor: Prof. Simon Shim. November 12, 2026", C, after=6)
T(["Team member", "Sections written"],
  [["Ayush Gawai", "4.1, 4.2, 4.3"],
   ["Naman Vipul Chheda", "3.1, 3.2, 3.3"],
   ["Manav Patel", "3.5, 3.6"],
   ["Shriram Dundigalla", "3.4, 4.5, and the figures in sections 3 and 4"],
   ["Pramod Satya Dindukurthi", "4.4, 4.6, References"]],
  [2.6, 3.9])
P("GitHub: https://github.com/ayushgawai/multiplayer-agent-sessions   "
  "Linear: https://linear.app/data-298a-team-4/team/DAT/cycles", C, 10, after=6)
P("This workbook is report sections 3 and 4. Sections 1 and 2 are not rewritten; what has changed since "
  "Workbook 1 is recorded in the carry-forward table at the end. Table, figure and reference numbers continue "
  "from Workbook 1, which ended at Table 17, Figure 2 and reference [17]. Every count in section 3 was "
  "recomputed from the data files at commit `fbb3fdf` by `docs/reports/t4a6_data_facts.py`, and every figure is "
  "generated by a committed script, so each data count in this document can be traced to the file it came from.",
  J, 10, italic=True)

# ================================================================== 3
H("3. Data Engineering", 1)
H("3.1 Data Process", 2)
P("The project uses three data sources, and each one answers a different question. MAST-Data [3] is the corpus "
  "of the published baseline selected for reproduction: it tells us whether our evaluation tooling can recover a published "
  "number. QMSum [2] is supervision for Model 1 only: it teaches query-focused summarisation of multi-party "
  "discussion. The product-session corpus, recorded on our own platform, is the only source that contains the "
  "task we actually care about, and it is the source that selects a winner for every model. The three paths are "
  "pinned and frozen separately and never mix, because mixing them is how a baseline number ends up scored "
  "against the wrong labels.")
P("Every path follows the same five steps, which are also the five subsections that follow. Table 18 states "
  "what each step does, the tool that does it, and the artifact it leaves behind; Figure 3 shows the lineage.")
T(["Step", "What happens", "Tool or script", "Artifact left in the repository"],
  [["1. Collect (3.2)", "Download from a pinned upstream revision. Verify a SHA-256 digest per file and the record count against the published count. Fail loudly on any mismatch.",
    "`data/scripts/download_mast.py`\n`data/scripts/download_qmsum.py`", "`data/mast/STATS.md`\n`data/qmsum/STATS.md`"],
   ["2. Pre-process (3.3)", "Validate schema and label domain, assert key uniqueness, normalise text fields, and exclude records that cannot be scored. Every rule reports how many rows it removed.",
    "`data/scripts/eda_mast.py` stage 2\n`data/scripts/make_splits.py`", "`data/mast/EDA_SUMMARY.json`\n`data/mast/AUDIT_REPORT.md`"],
   ["3. Transform (3.4)", "Reshape into the format the consumer needs: a flat label table for analysis, and ordered event inputs for Model 1.",
    "`data/scripts/eda_mast.py` stage 3\n`eval/contracts/m1.py` adapters", "`mast_clean_summary.csv`\n`m1-input-v1` records"],
   ["4. Prepare (3.5)", "Fix train, validation and test membership, hash every split file, and commit the manifest. Run leakage checks.",
    "`data/scripts/make_splits.py --seed 13`\n`data/scripts/verify_eval_manifest.py`", "`data/splits/m1_v1/MANIFEST.json`\n`data/mast/eval_manifest.json`"],
   ["5. Describe (3.6)", "Compute counts, distributions, imbalance and correlation from the prepared files, and regenerate every figure.",
    "`docs/reports/t4a6_data_facts.py`\n`docs/reports/generate_t4a6_figures.py`\n`docs/reports/generate_t4a5_figures.py`", "`docs/reports/t4a6_data_facts.json`\n`docs/reports/figures/`"]],
  [1.05, 2.45, 1.6, 1.4], "The data process: five steps, the tool behind each, and the artifact that proves it ran.", mono_cols=())
F("fig03_data_process.png", "Data process and lineage for the three sources. Blue stages are built and on the main "
  "branch; amber stages belong to the product-session corpus and are planned. Generated by docs/reports/generate_t4a6_figures.py.")
P("Three design rules govern the whole process. First, public data is never committed: it is reconstructed on "
  "demand from pinned revisions, and what is committed is the evidence that the reconstruction is byte-identical "
  "(digests, counts, manifests). Second, nothing is dropped silently: a malformed record is a hard error, and a "
  "legitimate exclusion is written to a committed summary with its key and its reason. Third, test data is read "
  "once: validation data is used for prompts, thresholds, early stopping and hyperparameters, and the test split "
  "is opened only for the final frozen comparison (ADR-005, rule 4).")
if WH:
    P("The same five steps also run as one orchestrated pipeline that lands its output in a local analytical "
      "warehouse, which is what the data pipeline demonstration shows. `infra/warehouse/pipeline.py` (merged in pull request #33) executes "
      "ingest, clean and validate, transform, and quality gates in a fixed order and stops at the first failure. "
      "It writes three layers into a DuckDB [24] database: `raw` (records as landed, with source digest and load "
      "time), `staging` (validated and cleaned), and `marts` (a star schema of fact and dimension tables for "
      "analysis). Two further tables make the pipeline observable: `meta.quality_checks` holds the expected and "
      "actual value of every gate, and `meta.pipeline_runs` appends one row per stage per run with start time, "
      "duration, rows in, rows out, status and git commit, so run history accumulates across runs. "
      + WH["summary"])
    T(["Layer", "Table", "Rows", "Columns", "Content"], WH["tables"], [0.7, 1.9, 0.6, 0.7, 2.6],
      "Warehouse layers produced by one pipeline run on the real data. Row and column counts are pasted from the run "
      "transcript in infra/warehouse/SAMPLE_RUN.md.", mono_cols=(1,))

# ------------------------------------------------------------------ 3.2
H("3.2 Data Collection", 2)
P("Table 20 lists the raw sources with their parameters and quantities. Both public sources are sufficient for "
  "their purpose in DATA 298A: the MAST release is the complete corpus used in the paper selected for reproduction, so there "
  "is no larger set to collect, and the QMSum release is the complete benchmark. The source that is not yet "
  "sufficient is our own, and section 3.6 says so plainly.")
T(["Source", "Origin and pinned revision", "Quantity retrieved", "Parameters (fields)", "Licence", "Role"],
  [["MAST-Data [3]", "Hugging Face dataset `mcemri/MAD`, commit `95118ac9`. Taxonomy text from the MAST GitHub repository, commit `a70542e5`.",
    "1,642 annotated traces (199.6 MB), equal to the paper's stated 1,642. 19 human-labelled traces (2.7 MB) from the authors' inter-annotator agreement study: a separate file with its own numbering, annotated over four rounds under a taxonomy revised between rounds; only the 4 traces of the last round use the current 14 codes. It is not a subset of the 1,642. 2 taxonomy files.",
    "`mas_name`, `llm_name`, `benchmark_name`, `trace_id`, `trace` {`index`, `key`, `trajectory`}, `mast_annotation` {14 failure codes `1.1` to `3.3`, each 0, 1 or null}",
    "CC-BY-4.0", "Published baseline corpus. Evaluation only."],
   ["QMSum [2]", "Yale-LILY/QMSum public release, official train, validation and test files.",
    "232 meetings (162 / 35 / 35), 129,177 transcript turns, 1,810 query-summary pairs: 1,576 specific and 234 general.",
    "`meeting_transcripts` [{`speaker`, `content`}], `specific_query_list` [{`query`, `answer`, `relevant_text_span`}], `general_query_list` [{`query`, `answer`}], `topic_list`",
    "MIT", "Model 1 supervision and a separately reported benchmark."],
   ["Smoke fixtures", "Generated by `data/scripts/make_m1_smoke.py --seed 13` from 12 scripted sessions (DAT-53).",
    "18 examples from 12 sessions, 5 scenario types.",
    "`example_id`, `session_id`, `query`, `events[]`, `critical_facts[]`, `event_labels`, `reference`",
    "Team-authored", "Pipeline validation only. Never an evaluation split."],
   ["Product sessions", "Append-only event log of our session service (PostgreSQL).",
    "0 sessions recorded as of 11 Nov 2026. Target about 30.",
    "`SessionEvent` (ADR-001): `event_id`, `seq`, `type`, `actor`, `payload`, timestamps",
    "Team-owned, pseudonymised", "Winner selection for Model 1; training data for Models 2 to 4."]],
  [0.85, 1.35, 1.35, 1.7, 0.55, 0.7], "Raw data sources, parameters and quantities.", size=8)
P("Collection is scripted end to end. `download_mast.py` is idempotent, re-validates every digest on each run, "
  "and refuses to proceed if a count or a hash differs from the pinned value. The digests of the five MAST "
  "files (three data files and two taxonomy files) and of the three QMSum files are recorded in the two `STATS.md` files, and the MAST digests are "
  "repeated in the frozen evaluation manifest. Figure 4 shows what the MAST corpus is made of: seven multi-agent "
  "frameworks, five underlying language models and eight benchmarks, with three frameworks contributing only 30 "
  "traces each.")
F("fig5_mast_composition.png", "Composition of the 1,642 raw MAST traces by framework, underlying language model and "
  "benchmark. Counts are parsed from data/mast/DATA_DICTIONARY.md by docs/reports/generate_t4a5_figures.py.")
H("Samples from the raw datasets", 3)
P("Table 21 shows one raw MAST record and Table 22 one raw QMSum meeting, both abbreviated only where a field "
  "is long. The MAST trajectory is a single string holding the whole logged interaction, between 1,262 and "
  "2,004,123 characters; the QMSum transcript is a list of speaker turns with disfluency markers left in by the "
  "original transcribers.")
T(["Field", "Raw value"],
  [["mas_name", "AG2"], ["llm_name", "Claude"], ["benchmark_name", "GSM"], ["trace_id", "190"],
   ["trace.key", "AG2_GSM_Plus_Claude"],
   ["trace.trajectory", "{'content': [\"Let's use Python to solve a math problem.\", '', 'Query requirements:', \"You should always use the 'print' function for the output and use fractions/radical forms instead of decimals.\", ... (string continues)"],
   ["mast_annotation", "{\"1.1\": 0, \"1.2\": 0, \"1.3\": 0, \"1.4\": 0, \"1.5\": 0, \"2.1\": 0, \"2.2\": 0, \"2.3\": 0, \"2.4\": 0, \"2.5\": 0, \"2.6\": 1, \"3.1\": 0, \"3.2\": 1, \"3.3\": 1}"]],
  [1.4, 5.1], "One raw MAST record from MAD_full_dataset.json (record index 400).", mono_cols=(0, 1))
T(["Field", "Raw value (first meeting of the QMSum training file)"],
  [["meeting_transcripts[0]", "{\"speaker\": \"Project Manager\", \"content\": \"Yep . Soon as I get this . Okay . This is our last meeting . Um I'll go ahead and go through the minutes from the previous meeting . Uh and then we'll have a , the prototype presentation . {vocalsound} Um then we will um do an evaluation . ...\"}"],
   ["specific_query_list[0]", "{\"query\": \"How Did Project Manager and User Interface introduce the prototype of the remote control?\", \"answer\": \"Project Manager introduced that the prototype incorporated fashion trends that people prefer fancy looking products like fruit and vegetable. ...\", \"relevant_text_span\": [...]}"],
   ["general_query_list[0]", "{\"query\": \"Summarize the whole meeting.\", \"answer\": \"Firstly, Project Manager reviewed the overall process that the team designed the remote control that they had viewed the fashion trends and incorporated the key features. ...\"}"],
   ["topic_list[0]", "{\"topic\": \"Remote control prototype introduction\", \"relevant_text_span\": [[\"0\", \"53\"]]}"]],
  [1.5, 5.0], "One raw QMSum meeting record.", mono_cols=(0, 1))

# ------------------------------------------------------------------ 3.3
H("3.3 Data Pre-processing", 2)
P("Pre-processing is where a dataset is either trusted or not, so each rule is implemented as an executable "
  "check rather than as a convention, and each check reports its effect. Table 23 lists every rule, the tool "
  "that enforces it, and the number of rows it removed or changed on the pinned data. The most important number "
  "in the table is how few rows were removed: four from MAST and none from QMSum. That is a finding about the "
  "sources, not an absence of cleaning. Both are curated research releases, so the value of pre-processing here "
  "is the guarantee that the properties we depend on actually hold, and the precise handling of the one case "
  "where they do not.")
T(["#", "Dataset", "Rule", "Enforced by", "Effect on the pinned data"],
  [["1", "MAST", "File digest and record count must equal the pinned values.", "`download_mast.py`", "Pass. 1,642 of 1,642; 0 removed."],
   ["2", "MAST", "Every record must carry `trace.key`, an integer `trace_id` and an annotation object. A violation is a hard error, not a drop.", "`eda_mast.py` stage 2", "Pass. 0 violations."],
   ["3", "MAST", "The record key (`trace.key`, `trace_id`) must be unique. `trace_id` alone is not: it has 206 distinct values and restarts in every source run.", "`eda_mast.py`, `verify_eval_manifest.py`", "1,642 unique keys; 0 duplicates."],
   ["4", "MAST", "Each of the 14 labels must be exactly 0, 1 or null. Any other value is a hard error.", "`eda_mast.py` stage 2", "0 invalid cells in 22,988 raw cells (1,642 x 14)."],
   ["5", "MAST", "A null label stays null. It is never read as 0, because a missing judgement is not a negative judgement.", "`eda_mast.py` stage 2", "56 null cells preserved, all in 4 records."],
   ["6", "MAST", "A record is excluded from scoring only if all 14 labels are null. A partly null record would be kept.", "`eda_mast.py` stage 2", "4 records removed (0.24%). 0 partly null records exist."],
   ["7", "MAST", "Strip surrounding whitespace from `mas_name`, `llm_name`, `benchmark_name`.", "`eda_mast.py` stage 2", "0 values changed."],
   ["8", "QMSum", "File digests and counts must equal the pinned values.", "`download_qmsum.py`", "Pass. 232 meetings; 0 removed."],
   ["9", "QMSum", "Render each turn as `Speaker: content` with content stripped; strip queries and answers.", "`make_splits.py`", "129,177 turns rendered; 0 removed."],
   ["10", "QMSum", "A specific query whose relevant span list is empty falls back to the whole meeting as context.", "`make_splits.py`", "0 of 1,576 specific queries needed the fallback; 0 rows removed."],
   ["11", "QMSum", "Query, context and reference summary must be non-empty; example ids must be unique.", "`t4a6_data_facts.py`, `data/tests/`", "0 empty fields; 0 duplicate ids in 1,810 rows."]],
  [0.3, 0.6, 2.75, 1.35, 1.5], "Pre-processing rules, the tool enforcing each, and the rows each one removed or changed.", size=8.5)
P("The four excluded MAST records are named in the committed summary rather than merely counted: they are "
  "traces 4, 72, 73 and 81 of the run `ChatDev_ProgramDev-v2_CodeLlama`. The quality gate that closes the "
  "pre-processing stage re-derives ten properties from the data and compares each with the value stored in the "
  "frozen manifest; on the pinned data all ten pass and the script ends with the line "
  "`QUALITY GATE: all checks passed`. Two consecutive runs produce byte-identical summary files, which we use as "
  "a regression check that the stage is deterministic.")
H("Samples before and after pre-processing", 3)
T(["Record key", "Before (raw `mast_annotation`)", "After pre-processing"],
  [["AG2_GSM_Plus_Claude, 190", "{\"1.1\": 0, ..., \"2.6\": 1, \"3.1\": 0, \"3.2\": 1, \"3.3\": 1}", "Kept. 14 valid labels, 3 positive, 0 null. Key verified unique."],
   ["ChatDev_ProgramDev-v2_CodeLlama, 4", "{\"1.1\": null, \"1.2\": null, ..., \"3.3\": null}", "Excluded from scoring (rule 6). Listed in `EDA_SUMMARY.json` under `excluded_records`. Labels remain null."],
   ["ChatDev_ProgramDev_GPT4o, 0", "{\"1.1\": 0, \"1.2\": 0, ..., \"3.3\": 0}", "Kept. A trace with no failure is a valid negative, not a missing record."]],
  [1.9, 2.5, 2.1], "MAST records before and after pre-processing.", mono_cols=(0, 1))
T(["Field", "Before (raw QMSum)", "After pre-processing"],
  [["Transcript turn", "{\"speaker\": \"Grad B\", \"content\": \"And they wouldn't look pretty . So .\"}", "\"Grad B: And they wouldn't look pretty . So .\""],
   ["Query", "\"How would the middle layer work?\"", "\"How would the middle layer work?\" (stripped; unchanged)"],
   ["Relevant spans", "[[\"start\", \"end\"], ...] index ranges into the transcript", "8 context spans: the turns those ranges select, in transcript order"]],
  [1.1, 2.9, 2.5], "A QMSum example before and after pre-processing (qmsum_test_9_s3).", mono_cols=(1, 2))
P("Transcript disfluencies such as `{vocalsound}` and `{disfmarker}` are deliberately not removed. They are "
  "part of the published benchmark text, the reference summaries were written against them, and stripping them "
  "would make our QMSum numbers incomparable with any published figure.")

# ------------------------------------------------------------------ 3.4
H("3.4 Data Transformation", 2)
P("Transformation changes the shape of the data without changing what it says. Table 26 gives each "
  "transformation with the reason it exists, because a transformation without a reason is one nobody can safely "
  "remove later.")
T(["Dataset", "Transformation", "Output", "Reason"],
  [["MAST", "Flatten the nested `mast_annotation` object into 14 columns `fail_1_1` to `fail_3_3`.", "14 label columns; null is an empty cell", "A flat table can be aggregated, plotted and joined; a nested object per record cannot."],
   ["MAST", "Derive `n_failures`, `n_null_labels` and the pipe-joined `failure_codes`.", "3 columns", "Per-trace failure load is the first thing a reader asks for and the basis of Figure 8."],
   ["MAST", "Roll the 14 codes up into the paper's 3 categories: specification, inter-agent misalignment, task verification.", "`cat_specification`, `cat_misalignment`, `cat_verification`", "The paper reports at category level, so category counts are needed to compare with it."],
   ["MAST", "Replace the trajectory string by its length `trace_chars`.", "1 column", "The analysis table must stay small (142 KB against 199.6 MB); the full text is read from the pinned file when the judge needs it."],
   ["QMSum", "Emit one `CatchupExample` per query: `id`, `query`, `context_spans`, `reference_summary`.", "1,810 rows, 4 columns", "Model 1 answers one query at a time; the raw file is organised per meeting."],
   ["QMSum", "Deterministic ids `qmsum_<split>_<meeting>_<s|g><n>`.", "`id`", "A stable id is what makes a prediction traceable to its input across seeds and reruns."],
   ["QMSum", "Adapt each row to `m1-input-v1`: every context span becomes an ordered `doc_update` event with id `<row-id>:span:<index>`; the session id is `qmsum:<split>:<meeting>`.", "`M1Input` record", "All four Model 1 candidates must consume the same event-shaped input as live product sessions, and every output claim must cite event ids."],
   ["QMSum", "The reference summary is kept outside the input record.", "Evaluation target only", "A target inside the input would leak the answer to the model."],
   ["Sessions", "Map a native `SessionEvent` to an `M1Event`: `seq` to `sequence`, `type` to `event_type`, `actor.id` to `actor_id`, `payload.text` to `text`.", "`M1Event`", "One adapter owned by the evaluation layer, so no candidate invents its own mapping (ADR-005)."]],
  [0.7, 2.45, 1.35, 2.0], "Transformations applied, with the reason for each.", size=8.5)
H("Samples from the transformed datasets", 3)
T(["trace_key", "trace_id", "mas_name", "llm_name", "benchmark", "trace_chars", "n_failures", "failure_codes", "cat spec / mis / ver"],
  [["AG2_MMLU_GPT4o_Mini", "59", "AG2", "GPT-4o-mini", "MMLU", "7,412", "3", "2.2|2.6|3.2", "0 / 2 / 1"],
   ["ChatDev_ProgramDev2_GPT4o", "39", "ChatDev", "GPT-4o", "ProgramDev", "267,208", "5", "1.1|2.3|2.5|2.6|3.2", "1 / 3 / 1"],
   ["ChatDev_ProgramDev-v2_CodeLlama", "38", "ChatDev", "CodeLlama", "ProgramDev-v2", "743,062", "11", "1.1|1.3|1.4|1.5|2.1|2.2|2.3|2.5|2.6|3.2|3.3", "4 / 5 / 2"],
   ["ChatDev_ProgramDev_GPT4o", "0", "ChatDev", "GPT-4o", "ProgramDev", "345,536", "0", "(empty)", "0 / 0 / 0"]],
  [1.45, 0.45, 0.6, 0.7, 0.75, 0.6, 0.5, 0.95, 0.5],
  "Four rows of the transformed MAST table mast_clean_summary.csv (26 columns; the 14 fail_ columns are omitted here "
  "because failure_codes carries the same information).", size=7.5)
T(["Field of the `m1-input-v1` record", "Transformed value"],
  [["schema_version", "m1-input-v1"], ["example_id", "qmsum_test_9_s3"], ["session_id", "qmsum:test:9"],
   ["query", "How would the middle layer work?"],
   ["events[0]", "{\"event_id\": \"qmsum_test_9_s3:span:0000\", \"sequence\": 0, \"event_type\": \"doc_update\", \"actor_id\": null, \"text\": \"Grad B: And they wouldn't look pretty . So .\"}"],
   ["events[1]", "{\"event_id\": \"qmsum_test_9_s3:span:0001\", \"sequence\": 1, \"event_type\": \"doc_update\", \"actor_id\": null, \"text\": \"Grad C: Yeah , they 'd all be like pointing to the one node .\"}"],
   ["events[2..7]", "six further ordered events"],
   ["memory_version, approved_memory", "null, [] (memory is disabled during candidate selection)"]],
  [2.0, 4.5], "One QMSum row after transformation to the Model 1 input contract, produced by "
  "eval.contracts.m1.qmsum_row_to_m1_input.", mono_cols=(0, 1))

# ------------------------------------------------------------------ 3.5
H("3.5 Data Preparation", 2)
P("Model 1 is the model built in DATA 298A, so its splits are the ones fixed here. They live in "
  "`data/splits/m1_v1/` as three JSON Lines files with a manifest that records the row count, byte size and "
  "SHA-256 digest of each file and the seed (13) of the generating command. The files were committed on "
  "21 October 2026 (commit `330603f`) and have not changed since; the manifest digests were recomputed for this "
  "workbook and all three match.")
P("The partition is not ours and is not stratified. `m1_v1` inherits the official QMSum partition, which assigns "
  "whole meetings to train, validation or test. We kept it for two reasons: splitting by meeting is the correct "
  "grouping for this data, since eight or so queries share one transcript and a row-level split would put the "
  "same meeting on both sides, and keeping the published partition is what makes a QMSum number comparable with "
  "the literature. Because we did not stratify, we checked afterwards whether the splits resemble each other, "
  "and Figure 6 in section 3.6 shows that they do.")
T(["Split", "Rows", "% of total", "Stratified on", "Leakage check and result"],
  [["Train", "1,257\n(162 meetings)", "69.4%", "Not stratified. Grouped by meeting (official QMSum partition).",
    "Meeting transcripts hashed with SHA-256: 0 of 162 appear in validation or test. 0 example ids, 0 context sets and 0 (query, reference) pairs shared with another split."],
   ["Validation", "272\n(35 meetings)", "15.0%", "Not stratified. Grouped by meeting.",
    "0 of 35 meetings shared with train or test. 0 shared ids, contexts or (query, reference) pairs. Two of its reference-summary strings recur elsewhere, one in train and one in test (see text)."],
   ["Test", "281\n(35 meetings)", "15.5%", "Not stratified. Grouped by meeting.",
    "0 of 35 meetings shared with train or validation. 0 shared ids, contexts or (query, reference) pairs. Read only for the final frozen comparison."]],
  [0.8, 0.95, 0.75, 1.5, 2.5], "Prepared Model 1 splits (data/splits/m1_v1/, 1,810 rows in total) and the leakage "
  "checks run by docs/reports/t4a6_data_facts.py.")
P("The leakage check found one thing worth reporting. No meeting, example id, context or query-and-reference "
  "pair crosses a split boundary, but two reference-summary strings each occur in two splits: the summary of "
  "`qmsum_train_69_g0` is repeated verbatim as `qmsum_val_6_g0`, and the summary of `qmsum_val_6_s2` as "
  "`qmsum_test_30_s2`, in both cases attached to a different query and a different transcript. These are "
  "duplicates in the upstream release, where consecutive meetings of one project were summarised with the same "
  "text. They involve 4 of 1,810 rows (0.22%). We left them in place so that the partition stays the published "
  "one, and we record them here so that nobody mistakes them for a split error later.")
F("fig4_m1_splits.png", "Prepared Model 1 split proportions and the number of meetings and query pairs in each split. "
  "Generated from data/splits/m1_v1/MANIFEST.json by docs/reports/generate_t4a5_figures.py.")
H("Samples from the prepared datasets", 3)
T(["Split", "id", "query", "context", "reference_summary (start)"],
  [["Train", "qmsum_train_145_s1", "Did the Professor agree with Grad G on cross-lingual data?", "17 spans. First: \"PhD G: Yeah , and perhaps , um {disfmarker} {pause} We were thinking that perhaps the cross - language issue is not , uh , so big of a issue . ...\"",
    "Grad G thought that the multi-lingual aspect of the model was not very important. The professor disagreed. He explained that the point of the project was to have something robust that could apply to many languages."],
   ["Validation", "qmsum_val_4_s0", "Summarize the presentations on working design, technical functions, functional requirements.", "260 spans. First: \"Project Manager: All hooked up . {vocalsound} Okay , so now we are here at the functional design meeting . ...\"",
    "Firstly, Industrial Designer presented on working design, identifying a few basic components of the remote. From the functional design perspective, Industrial Designer introduced what exactly the components were ..."],
   ["Test", "qmsum_test_9_s3", "How would the middle layer work?", "8 spans. First: \"Grad B: And they wouldn't look pretty . So .\"",
    "The values these nodes take feed into the middle layer nodes identified as hidden variables of the user/device interaction, such as whether the user is on tour, running an errand or in a hurry. ..."]],
  [0.7, 1.1, 1.3, 1.7, 1.7], "One sample from each prepared split.", size=8)
P("Two other prepared sets exist and neither is a training split. The MAST evaluation manifest "
  "(`data/mast/eval_manifest.json`, version 1.0.0, status FROZEN) fixes the 1,638 scorable records, labelled by the original LLM judge, and, from the separate 19-record human-labelled file, "
  "only the 4 traces labelled in the current 14-code taxonomy (the other 15 use older 18- and 17-code taxonomies that do not map one to one) as evaluation-only references, and records for each which label source it carries, so "
  "that agreement with the released judge labels can never be reported as agreement with human experts. MAST "
  "has no train split because the baseline is an inference-only judge. The smoke fixtures "
  "(`data/m1_smoke/fixtures/`, 12 train, 3 dev and 3 hold-out examples, split by `session_id` with seed 13) "
  "carry the full product schema including critical facts and evidence event ids; they exist to exercise the "
  "pipeline end to end and are barred by their own manifest from ever being used as an evaluation split.")
P("Table 31 shows what a record of the product schema looks like, using one smoke fixture. It carries what "
  "QMSum lacks: typed events with actors, gold critical facts with a status category, and the event ids that "
  "justify each fact. The annotated product-session split will have exactly this shape.")
T(["Field", "Value (smoke example `smoke-s01-x1`, session `smoke-s01`, 16 events, 5 critical facts)"],
  [["query", "Catch me up on what happened while I was away."],
   ["events[11]", "{\"source_event_id\": \"smoke-s01-e011\", \"sequence\": 11, \"event_type\": \"tool_result\", \"actor_id\": \"agent-beacon\", \"text\": \"4 passed, 1 failed: test_large_payload exceeds the 2 s timeout.\"}"],
   ["events[12]", "{\"source_event_id\": \"smoke-s01-e012\", \"sequence\": 12, \"event_type\": \"agent_step\", \"actor_id\": \"agent-beacon\", \"text\": \"test_large_payload needs the archive fixture, which only Omar can provision. I cannot continue that test.\"}"],
   ["critical_facts[3]", "{\"fact_id\": \"smoke-s01-f04\", \"category\": \"blocked\", \"text\": \"test_large_payload is blocked on the archive fixture\", \"evidence_event_ids\": [\"smoke-s01-e011\", \"smoke-s01-e012\"]}"],
   ["reference.blocked[0]", "{\"text\": \"Beacon is blocked on test_large_payload because only Omar can provision the archive fixture.\", \"source_event_ids\": [\"smoke-s01-e011\", \"smoke-s01-e012\"]}"]],
  [1.4, 5.1], "One smoke-fixture record in the product schema (data/m1_smoke/fixtures/train.jsonl). Scripted, not recorded; never an evaluation split.", mono_cols=(0, 1))
P("The split that will select the Model 1 winner, `data/splits/m1_session_v1/`, is not prepared yet because the "
  "sessions it is made from are not recorded yet. Its rules are already frozen in ADR-005: split by "
  "`session_id` so that no session appears in more than one split, freeze files, critical facts, evidence links "
  "and manifest hashes before the first comparative run, and admit synthetic examples to training only.")

# ------------------------------------------------------------------ 3.6
H("3.6 Data Statistics", 2)
P("Table 32 summarises what each stage produced. Read down a column and the row counts reconcile: MAST loses "
  "exactly the four unscorable records between raw and pre-processed and nothing afterwards, and the 1,810 "
  "QMSum queries present in the raw files are the 1,810 rows of the prepared splits.")
T(["Stage", "Rows", "Columns", "Notes"],
  [["Raw", "MAST: 1,642 traces (+19 in a separate human-labelled file)\nQMSum: 232 meetings, 129,177 turns", "MAST: 6 top-level fields, 14 nested labels\nQMSum: 4 fields",
    "Pinned revisions; SHA-256 per file; MAST count equals the paper's 1,642."],
   ["Pre-processed", "MAST: 1,638 scorable (4 removed)\nQMSum: 232 meetings (0 removed)", "Unchanged",
    "56 null label cells preserved, all in the 4 excluded records; 0 invalid labels; 0 duplicate keys."],
   ["Transformed", "MAST: 1,638\nQMSum: 1,810 examples", "MAST: 26\nQMSum: 4 (7 as `m1-input-v1`)",
    "MAST flat table with category roll-ups. QMSum: 1,576 specific and 234 general queries."],
   ["Prepared", "MAST: 1,638 judge-labelled + 4 human-labelled, evaluation only\nQMSum: 1,257 / 272 / 281\nSmoke: 12 / 3 / 3", "MAST: manifest v1.0.0\nQMSum: 4\nSmoke: 8",
    "Frozen and hashed. QMSum grouped by meeting, 0 meetings shared across splits."]],
  [1.0, 2.25, 1.6, 1.65], "Data preparation results by stage.")
H("Model 1 supervision: QMSum", 3)
T(["Statistic (words unless stated)", "Train", "Validation", "Test"],
  [["Rows", "1,257", "272", "281"], ["Specific / general queries", "1,095 / 162", "237 / 35", "244 / 37"],
   ["Reference summary: median (Q1 to Q3), max", "66 (47 to 90), 238", "68 (50 to 86), 188", "59 (43 to 81), 188"],
   ["Query: median (Q1 to Q3)", "11 (8 to 15)", "10 (7 to 15)", "11 (7 to 15)"],
   ["Context spans per example: median, 95th percentile, max", "29, 588, 1,832", "30.5, 624, 1,259", "33, 678, 1,368"],
   ["Context length: median, 95th percentile, max", "660, 10,368, 26,338", "696, 11,210, 24,573", "671, 10,280, 25,244"]],
  [2.9, 1.2, 1.2, 1.2], "Descriptive statistics of the prepared Model 1 splits.")
F("fig6_qmsum_distributions.png", "Distributions of reference-summary length, context spans per example and query length "
  "in the prepared Model 1 splits. Generated from data/splits/m1_v1/ by docs/reports/generate_t4a5_figures.py.")
P("Three properties of these distributions changed decisions elsewhere in this workbook. Reference summaries are "
  "short and tightly clustered, with a median near 65 words, so one omitted fact is a large share of an answer; "
  "that is the argument for ranking candidates on critical-fact recall ahead of text overlap in section 4.4. "
  "Context size is heavily right-skewed: the median example has about 660 words of context and the 95th "
  "percentile more than 10,000, because general queries take the whole meeting as context. A 4,096-token input "
  "therefore truncates the long tail, which is why `truncated` is a named failure code and why latency is "
  "committed at the 95th percentile as well as the median. And the three splits sit almost on top of one another "
  "in Figure 6, which matters because we inherited the partition instead of stratifying it.")
H("Baseline corpus: MAST", 3)
F("fig06_mast_prevalence.png", "Label imbalance across the 14 MAST failure modes on the 1,638 scorable traces. "
  "Generated from mast_clean_summary.csv by docs/reports/generate_t4a6_figures.py.")
P("The labels are imbalanced in two ways (Figure 7). Across failure modes, prevalence ranges from 40.5% for "
  "step repetition (1.3) down to 1.5% for information withholding (2.4), which is 664 positive traces against 24, a ratio of about 28 to 1; four modes are "
  "positive on fewer than one trace in ten. Within a trace, 401 of the 1,638 traces (24.5%) carry no failure at "
  "all and the remaining 1,237 (75.5%) carry between 1 and 14. Across all 1,638 traces the mean is 3.14 failure modes and the median 2; among the 1,237 traces with at least one failure the mean is 4.16 and the median 3 "
  "(Figure 8). The consequence for evaluation is direct: with 24 positive examples of mode 2.4, a judge that "
  "never predicts it loses almost nothing on accuracy, so the baseline is reported with precision, recall, F1 "
  "and Cohen's kappa beside accuracy, as the original paper does.")
F("fig07_mast_failures_per_trace.png", "Left: number of failure modes positive on a trace. Right: mean failure modes per "
  "trace by multi-agent framework, with the number of scorable traces. Generated by docs/reports/generate_t4a6_figures.py.")
F("fig08_mast_correlation.png", "Correlation (phi coefficient) between the 14 binary failure labels. White lines separate "
  "the three categories. Generated by docs/reports/generate_t4a6_figures.py.", 5.6)
P("Failure modes do not occur independently (Figure 9). Every pairwise correlation is positive, between 0.04 and "
  "0.66. The strongest pairs are step repetition with unawareness of termination conditions (1.3 and 1.5, "
  "0.66) and loss of conversation history with conversation reset (1.4 and 2.1, 0.62), the second of which "
  "crosses a category boundary; task derailment (2.3) correlates with disobeying the task specification (1.1) at "
  "0.49. Trace length and failure count are also associated (Spearman 0.54): longer traces tend to carry more failure labels, which is an association and not evidence that length causes failure. Two "
  "cautions follow. Failure counts per trace must not be read as independent events, and a framework comparison "
  "is confounded by trace length and by benchmark: AG2 has the lowest mean failure count (1.55) but was run "
  "mostly on short mathematics problems, while HyperAgent has the highest (6.17) on only 30 software traces.")
H("Population and coverage gaps", 3)
T(["Gap", "Evidence", "Who it would disadvantage if the system were deployed", "What we do about it"],
  [["QMSum is English-only meeting speech from three settings: product-design role play, academic research groups, and parliamentary committees.",
    "Source description [2]; samples in Tables 22 and 30.",
    "Teams working in other languages or in mixed-language sessions, and teams whose sessions are terse tool calls and code edits instead of long spoken turns.",
    "QMSum is supervision only and cannot select the winner. Selection uses product sessions (ADR-005)."],
   ["QMSum has no status categories, owners, or claim-level evidence labels.",
    "Schema in Table 20.",
    "Any user relying on the catch-up to say what is blocked or who owns an action: a model tuned only on QMSum can be fluent and wrong about status.",
    "Safety gates are measured on annotated product sessions; relevance labels derived from QMSum are weak supervision and are never presented as human labels."],
   ["MAST is dominated by three frameworks (82.6% of scorable traces) and one model family (GPT-4o, 45.8%); three frameworks have 30 traces each.",
    "Figure 4 shows raw counts (1,642); the shares here are computed on the 1,638 scorable traces.",
    "Users of under-represented frameworks: a judge validated mainly on AG2, MetaGPT and ChatDev traces may mislabel failures elsewhere.",
    "Report per-framework results with sample sizes; do not claim the taxonomy transfers to our sessions without our own annotation."],
   ["MAST traces contain agents only. No trace has several humans steering one agent.",
    "Paper [3]; Workbook 1, Table 10.",
    "Exactly the teams this project targets, whose failures include conflicting human instructions.",
    "MAST is the baseline and a taxonomy source, not training data for Models 2 to 4."],
   ["The human-labelled MAST file has 19 traces, and only 4 of them use the current 14-code taxonomy, so the human comparison rests on 4 traces (56 label cells).",
    "`eval_manifest.json`.",
    "Anyone reading an agreement figure from that comparison as precise.",
    "Report sample size and a 95% confidence interval beside every value."],
   ["No product sessions are recorded yet; the first ones will come from the five team members.",
    "`data/sessions/raw/` is empty on 11 Nov 2026.",
    "Non-expert users, larger teams, and domains other than software work would be unrepresented in the first corpus.",
    "State the population with every result; widen recruitment only after the IRB question is answered."]],
  [1.6, 1.0, 2.0, 1.9], "Population and coverage gaps in the data.", size=8.5)

# ================================================================== 4
H("4. Model Development", 1)
H("4.1 Model Proposals", 2)
P("The project evaluates five systems: four product models and one independent published baseline system. The "
  "four product models are M1 to M4, and each removes one coordination cost identified in section 2.2.1. The "
  "fifth system is the published MAST LLM-as-a-Judge of Cemri et al. [3], selected for reproduction as an "
  "external point of comparison. It is a separate system, not a fifth product model, and it is deliberately "
  "not one of M1 to M4: it classifies failures in other teams' multi-agent traces rather than serving any "
  "feature of this platform. Each of the four product models is in turn proposed as four competing candidate "
  "architectures, so sixteen candidates are specified in total. Table 35 lists the five systems, and Tables 36 "
  "and 37 give every candidate for Model 1 and for Models 2 to 4. Model 1 is built in DATA 298A and Models 2 "
  "to 4 in DATA 298B.")
T(["#", "Model", "Concept / architecture", "Built in", "Owner"],
  [["1", "M1 Session-state catch-up", "Given the ordered event log of a session and a query, produce a structured catch-up in five categories (completed, in progress, blocked, decisions, pending actions) in which every claim cites the event ids that support it. Four candidates: BM25 extractive, ModernBERT extractive selector, Phi-4-mini with QLoRA, Qwen3.5-4B with QLoRA.", "298A", "Ayush"],
   ["2", "M2 Intent attribution", "Classify which participant an instruction addresses. Pairwise scoring of (instruction, candidate participant, recent context). Four candidates: TF-IDF classical control, DeBERTaV3 and ModernBERT cross-encoders, Qwen with a classification head.", "298B", "Naman"],
   ["3", "M3 Merge arbitration", "Given two conflicting instructions to one agent, decide accept A, accept B, merge, or escalate to a human. Four candidates: last-writer-wins rule, ModernBERT pairwise cross-encoder, Qwen3.5-4B with LoRA and a four-way head, few-shot prompted Qwen3.5-4B.", "298B", "Manav"],
   ["4", "M4 Decomposition and routing", "Decompose a task into a directed acyclic graph of subtasks and route each to a participant or agent. Four candidates: rules-only router, LLM planner with a learned router, LLM planner alone, single-prompt planner and router.", "298B", "Shriram"],
   ["5", "Published baseline system selected for reproduction: MAST LLM-as-a-Judge (not one of M1 to M4)", "Cemri et al., NeurIPS 2025 [3], Table 2, row o1 (few shot). The published figures we aim to recover are accuracy 0.94, recall 0.77, precision 0.833, F1 0.80 and Cohen's kappa 0.77 against expert annotation. Inference only, no training. Status: prompt, parser, batch runner, provenance and metrics are on `main`; the pinned judge environment is open (DAT-36), so the judge has not been run and no reproduction result exists yet.", "298A", "Pramod"]],
  [0.3, 1.25, 3.55, 0.55, 0.85], "The five systems: four product models and the independent published baseline system selected for reproduction.", size=8.5)
P("Each model is developed as a bake-off of four candidates that share frozen data, one input and output "
  "contract, one evaluation harness and three seeds (13, 29, 47). A candidate is a configuration file under "
  "`eval/configs/` that pins the model repository and a full 40-character revision, so a result can be re-run "
  "exactly. That is where the sixteen candidates come from, four for each of the four product models; the "
  "architectures named below are candidates under evaluation, not selections. The baseline system is excluded "
  "from the bake-off because it is not ours to select: it is run as published, to test our tooling.")
H("Model 1: session-state catch-up (298A)", 3)
P("Problem. A participant or agent who joins a session in progress must learn its state without reading the "
  "whole history. Input is an `m1-input-v1` record: a query and the ordered events of the session, each with a "
  "stable event id. Output is an `m1-output-v1` record: five lists of claims, where every claim has non-blank "
  "text and one or more `source_event_ids` drawn from the input. Free text is invalid until it parses into that "
  "schema. Table 36 gives the four candidates.")
T(["ID", "Candidate", "Architecture and algorithm", "Features and training", "Role in the comparison"],
  [["m1-a", "BM25 event ranker + fixed template", "Okapi BM25 [18] scores each event against the query using term frequency, inverse document frequency and length normalisation; the top-ranked events fill a fixed structured template. No learned parameters, CPU only.",
    "Sparse lexical features over event text. No training; no GPU settings.", "Transparent floor. Every claim is a verbatim event, so it sets the matched-seed bar for unsupported claims."],
   ["m1-b", "ModernBERT-base selector + the same template", "ModernBERT-base [15], a 149M-parameter bidirectional encoder with an 8,192-token context, fine-tuned as a relevance scorer over (query, event); selected events fill the same template as m1-a.",
    "Contextual embeddings. Full fine-tuning, 3 epochs, 4,096 tokens, effective batch 16, learning rate 2e-5. Relevance labels are weak labels derived from QMSum.", "Learned extractive arm. Isolates what learned relevance adds over BM25 while staying unable to invent text."],
   ["m1-c", "Phi-4-mini-instruct + QLoRA", "Phi-4-mini [19], a 3.8B-parameter decoder-only transformer, quantised to 4-bit NF4 with low-rank adapters (QLoRA [20], LoRA [10]) on the projection layers named in `m1-c.yaml`; generates the JSON output directly.",
    "Instruction prompt with the event list and ids. 3 epochs, 4,096 tokens, effective batch 16; adapters only are trained and checkpointed.", "Compact generative family. Tests whether abstraction improves coverage at a size expected to fit a 16 GB GPU in 4-bit; that fit is not yet verified for this model."],
   ["m1-d", "Qwen3.5-4B + QLoRA", "Qwen3.5-4B [21], a 4B-parameter model that ADR-005 records as loading through a conditional-generation class, 4-bit NF4 with LoRA rank 16, alpha 32, dropout 0.05, learning rate 2e-4; generates the JSON output directly.",
    "Same prompt, data and limits as m1-c. A separate trainer path, because this architecture must not pass through the causal-LM-only trainer.", "Larger generative family. Tests whether more capacity buys recall without raising unsupported claims."]],
  [0.45, 1.05, 2.1, 1.6, 1.3], "The four Model 1 candidates frozen in ADR-005 and eval/configs/m1-a.yaml to m1-d.yaml.", size=8)
H("What is new in Model 1", 3)
P("Three elements of Model 1 go beyond the published systems surveyed in section 1.5. First, the output is "
  "evidence-cited by construction: a claim without a valid source event id is not a low-scoring answer, it is "
  "an invalid one. Query-focused summarisers such as the QMSum baseline [2] return free text that a reader "
  "cannot check. Second, selection is safety-gated before it is quality-ranked: a candidate that is fluent but "
  "unsupported on any one seed is ineligible, however good its mean. Third, the model can use approved memory, "
  "a versioned list of human-approved behavioural lessons that may change how it writes but can never serve as "
  "evidence for a session fact; the selected candidate is measured with memory disabled and enabled, and test "
  "feedback is barred from entering memory.")
H("Models 2 to 4 (298B)", 3)
P("Table 37 gives the candidates for the three models built in DATA 298B. In each, candidate (a) is a control "
  "with no learned language model, so that the learned arms have something concrete to beat. The Model 3 "
  "configurations are already committed as `eval/configs/m3-a.yaml` to `m3-d.yaml`; those for Models 2 and 4 "
  "follow the same schema and are written at the start of 298B. Training data for all three comes from the "
  "annotated product-session corpus.")
T(["Model", "Input features and output", "(a) Control", "(b)", "(c)", "(d)"],
  [["M2 intent attribution", "Instruction text, explicit mentions, each participant's role and recent activity. Output: one score per participant present; the highest is the addressee.",
    "TF-IDF features with a linear classifier", "DeBERTaV3 [11] cross-encoder over (instruction, participant context)", "ModernBERT [15] cross-encoder, same input", "Qwen backbone with a classification head"],
   ["M3 merge arbitration", "Two conflicting instructions, their authors and roles, timing, and document state. Output: accept A, accept B, merge, or escalate.",
    "Last-writer-wins rule", "ModernBERT-base pairwise cross-encoder, fine-tuned", "Qwen3.5-4B with LoRA and a four-way head", "Few-shot prompted Qwen3.5-4B, no training"],
   ["M4 decomposition and routing", "Task text, participant skills, current workload and cost. Output: a directed acyclic graph of subtasks, each assigned to a participant or agent.",
    "Rules-only router", "LLM planner with a learned gradient-boosted router", "LLM planner that also routes", "Single-prompt planner and router"]],
  [0.9, 1.9, 0.85, 1.0, 0.95, 0.9], "Candidates for Models 2 to 4.", size=8)
P("Three design points distinguish these models. Model 2 is framed as pairwise ranking instead of multi-class "
  "classification because the set of participants changes from session to session, and a model that scores one "
  "(instruction, participant) pair at a time works for any roster. Model 3 treats escalation as a first-class "
  "output, so the model can abstain when a wrong merge would be harmful; last-writer-wins is what every current "
  "product does implicitly and is therefore the arm to beat. Model 4 rejects any plan that is not a valid "
  "directed acyclic graph before a quality metric is computed, because an invalid plan cannot be executed.")
H("The published baseline system selected for reproduction", 3)
P("The fifth system is the LLM-as-a-Judge annotation pipeline of MAST [3]: a language model reads an execution "
  "trace, the 14 failure-mode definitions and few-shot examples, and emits 14 binary labels. The configuration "
  "selected for reproduction is the one in Table 2 of the paper, row o1 (few shot). It is kept apart from the "
  "four product models for a reason: it is the external reference point that will tell us whether our prompt, "
  "parser, batch runner and metric code can recover a published number, and none of our models is claimed to "
  "improve on it. The prompt (`mast-judge-v1`), deterministic parser (`mast-parser-v1.1`), resumable batch "
  "runner, provenance record and classification metrics are on the main branch.")
P("What has not happened yet is the run itself. The pinned o1 judge environment and its clean-environment smoke "
  "test are still open work (DAT-36), so the judge has not been executed against the corpus and no agreement "
  "figure has been produced. The batch runner has so far been exercised only with a deterministic stand-in "
  "judge, which verifies resume, provenance and parsing behaviour and nothing about agreement with the paper. "
  "Until the pinned environment runs, this workbook describes a baseline selected for reproduction and a "
  "reproduction method, not a reproduced result, and the figures quoted from [3] are the paper's own.",
  after=10)

# ------------------------------------------------------------------ 4.2
H("4.2 Model Supports", 2)
P("Figure 10 shows the supporting platform in four planes, and Table 38 lists the environment and tools behind "
  "each model. One rule holds across the diagram: components owned by different people communicate through a "
  "network call or a committed file format, never through shared process memory, which is what lets five people "
  "build in parallel against frozen contracts.")
F("fig11_platform_architecture.png", "Supporting platform architecture: session plane, execution and serving plane, data "
  "and model development plane, and the engineering controls that apply to all of them. Generated by "
  "docs/reports/generate_t4a6_figures.py.")
T(["Model", "Development environment", "Libraries and tools", "Execution and serving"],
  [["M1 catch-up", "Python 3.11 locally and in CI; training on one RTX 5080 Laptop GPU (16 GB) in the university lab at $0, PyTorch with CUDA.",
    "Transformers, PEFT, bitsandbytes 4-bit NF4, the BM25 ranker in `models/m1_catchup/bm25.py` (DAT-58, draft pull request #26), shared checkpoint utility `models/common/checkpointing.py`.",
    "Winner loaded behind `POST /v1/models/m1/predict`; called by the session service on join and hand-off."],
   ["M2 attribution", "Same GPU and harness.", "Transformers encoders, scikit-learn for the TF-IDF control.", "`POST /v1/models/m2/predict`, called per instruction event."],
   ["M3 arbitration", "Same GPU and harness; the rule arm needs no GPU.", "Transformers, PEFT; configurations already in `eval/configs/m3-*.yaml`.", "`POST /v1/models/m3/predict`, called when the control plane detects a conflict."],
   ["M4 routing", "Same GPU for the planner arms (Qwen or Gemma family); CPU for the rules arm and the learned router.", "LangGraph [13] for plan execution, LightGBM [28] for the learned router.", "`POST /v1/models/m4/predict`, called by the agent runtime."],
   ["MAST baseline", "No GPU. API inference with the paper's o1 few-shot configuration.", "`models/baseline_mast/`: prompt, parser, resumable batch runner, provenance; `eval/metrics/classification.py`.", "Offline batch; results as immutable run directories."],
   ["All models", "GitHub Actions on every pull request: ruff, mypy, pytest for the session service, serving, data, evaluation, the baseline, the agent runtime and the warehouse pipeline.",
    "Pinned `requirements.txt` with a lock file; ADR-001 to ADR-005; candidate YAML with pinned model revisions.", "Docker Compose: PostgreSQL 16, Redis 7, Jaeger, session service, serving."]],
  [0.9, 1.9, 2.0, 1.7], "Platform, environment and tools supporting each model.", size=8.5)
P("The session plane is what produces our own data. The React client edits a shared Yjs document through the "
  "CRDT server, and every action that matters is posted to the session service, a FastAPI application that "
  "enforces roles and appends a totally ordered `SessionEvent` to PostgreSQL, an event-sourced log from which state is derived by replay [23], with Redis fanning events out to "
  "connected clients. The agent runtime is a LangGraph plan, act, observe loop that executes tools from a registry; the design restricts it to five fixed tools, which are not implemented yet (DAT-19), so today the loop is tested with stand-in tools. "
  "The serving layer exposes one predict route per model; today the four adapters are stubs that honour the "
  "frozen interface, and each is replaced by a real model only when its bake-off winner is locked.")
F("fig12_ml_data_flow.png", "Machine-learning data flow for one bake-off candidate, from frozen split to serving "
  "adapter. Generated by docs/reports/generate_t4a6_figures.py.")
P("Figure 11 traces one candidate through the model plane. Training is adapter-only and writes a checkpoint "
  "every 200 steps through one shared utility (local paths, and since pull request #32 any object-store URI), so an "
  "interrupted lab session costs at most the work since the last checkpoint. The GPU path itself has been "
  "exercised: an earlier 50-step QLoRA run on a 1.7B-parameter Qwen3 model loaded in 4-bit NF4, checkpointed, "
  "resumed and reduced training loss from 3.90 to 2.14 (`docs/verification/m1_verification/`). That run is "
  "infrastructure evidence only. The model is not one of the four candidates and the loss is not a result. The same check for each real candidate (load at the pinned revision, memory at 4,096 tokens, checkpoint, resume, share of outputs that parse) is in progress on branch `m1-candidate-train-infer` and is required by ADR-005 before the bake-off.")
H("Why the platform is local, and why there is no workflow scheduler", 3)
P("We were asked to consider Amazon Web Services and Apache Airflow [22] for the data pipeline. We evaluated "
  "both against what the pipeline actually has to do and chose not to adopt either in DATA 298A. Table 39 "
  "records the reasoning, because a tool that is declined should be declined for stated reasons.")
T(["Question", "What our workload looks like", "Decision"],
  [["Is anything scheduled?", "No. Both public datasets are static, pinned to a commit and verified by digest. They do not change, so there is no daily or hourly run, no backfill and no late-arriving data. The pipeline runs when a person changes it.",
    "A scheduler would be idle. The pipeline is one idempotent command, and the events that should trigger it are code changes, which GitHub Actions already handles."],
   ["Is the dependency graph complex?", "Four stages in a straight line: ingest, clean and validate, transform, quality gates. No branching, no fan-out, no cross-team dependencies.",
    "A fixed ordered list with fail-fast in `infra/warehouse/pipeline.py` expresses it completely. Each stage is a plain function, so wrapping each in an Airflow task later is a mechanical change."],
   ["Do we lack monitoring without Airflow?", "Every run appends per-stage start time, duration, rows in, rows out, status and git commit to `meta.pipeline_runs`, and every gate to `meta.quality_checks`.",
    "Run history and data-quality results are queryable in SQL and reported by `pipeline.py --report`. That is the monitoring we need at this size."],
   ["Is the data too large for one machine?", "About 220 MB raw in total. The analytical tables are a few thousand rows.",
    "DuckDB [24] on a laptop runs the whole pipeline in about 6 seconds and answers the analytical queries interactively. A cloud warehouse would add cost, credentials and network latency and no capability."],
   ["Do we need cloud compute?", "Training needs one 16 GB GPU, which the university lab provides at $0. The baseline is API inference.",
    "No cloud GPU. This was already the decision in Workbook 1, section 2.3."],
   ["Why not a lightweight scheduler, such as Airflow run locally or a scheduled GitHub Actions job?", "Airflow run locally still needs a metadata database, a scheduler process and a web server to execute four functions in order on data that never changes. A scheduled CI job is nearly free, but there is nothing new for it to ingest.",
    "Not yet. The cheapest scheduler that fits is a scheduled GitHub Actions job, and that is what we will add first when ingestion becomes recurring; Airflow follows only if the graph grows branches or backfills."],
   ["Who is told when the pipeline breaks?", "The pipeline's tests run in GitHub Actions on every pull request, and a failed stage or gate exits non-zero.",
    "A failure is a red check on the pull request and an email to its author. Monitoring is therefore passive between changes, which is acceptable only because the data does not change between changes."],
   ["Does it help reproducibility?", "A grader or teammate can clone the repository and run the whole pipeline with two commands and no account.",
    "Local-first is the more reproducible choice. A cloud dependency would make the pipeline unverifiable by anyone without our credentials."]],
  [1.35, 2.75, 2.4], "Evaluation of a cloud platform and a workflow scheduler against the actual workload.", size=8.5)
P("The decision is scoped, not permanent, and the design keeps the door open. The checkpoint utility "
  "accepts `s3://` URIs (pull request #32), so adapter checkpoints can move to object storage without touching a trainer. The pipeline "
  "layers map one to one onto managed services: raw files to object storage, the stage functions to scheduled "
  "tasks, and the warehouse schemas to a cloud warehouse. Two conditions would change the decision, and both are expected in DATA 298B. The first is "
  "recurring ingestion: once product sessions are recorded more often than weekly, a nightly export from the PostgreSQL event log to "
  "the warehouse becomes a real schedule with a freshness requirement, and a scheduler earns its place. That export is the one ingestion path the warehouse does not have yet, because no session exists to export. The second is the first participant outside the team: "
  "the controlled study in DATA 298B needs the platform reachable beyond the team, which is when the cloud "
  "deployment promised as FR-8 is due.")

# ------------------------------------------------------------------ 4.3
H("4.3 Model Comparison and Justification", 2)
P("Table 40 compares the four models and the baseline; Table 41 compares the four Model 1 candidates, which is "
  "the comparison that will actually be run this semester.")
T(["Model", "Targeted problem", "Input features", "Approach", "Strengths", "Limitations"],
  [["M1 catch-up", "Late joiner cannot cheaply learn session state", "Ordered event text, event ids, query", "Statistics (BM25), deep learning (encoder; QLoRA generators)", "Every claim is checkable against cited events; safety-gated selection", "Needs annotated sessions to select; long sessions exceed 4,096 tokens"],
   ["M2 attribution", "Unclear whom an instruction addresses", "Instruction text, mentions, roles, recent activity", "Machine learning (TF-IDF + linear), deep learning (cross-encoders)", "Cheap per-event inference; per-class F1 exposes weak classes", "Bounded by annotator agreement on what an instruction meant"],
   ["M3 arbitration", "Two actors redirect one agent at once", "Both instructions, authors and roles, timing, document state", "Rule (last-writer-wins), deep learning (cross-encoder, LoRA, few-shot)", "Can escalate instead of guessing; rule control is trivial to audit", "Conflicts are rare, so data is scarce and partly synthetic"],
   ["M4 routing", "Subtasks assigned by availability alone", "Task text, participant skills, workload, cost", "Rules, LLM planning, gradient-boosted router", "DAG-validity gate stops malformed plans early", "Plans are costly to label; planner quality is sensitive to the prompt"],
   ["MAST baseline", "Do we measure failures correctly?", "Trace text, 14 definitions, few-shot examples", "Prompted LLM judge, no training", "Published target to hit; inference only", "Only 4 human-labelled traces use the current taxonomy, so the human agreement figure is imprecise; it is reported with its sample size and a 95% confidence interval beside the full-scale check against the judge labels"]],
  [0.8, 1.15, 1.15, 1.15, 1.15, 1.1], "Comparison of the four models and the baseline.", size=8)
T(["", "m1-a BM25", "m1-b ModernBERT", "m1-c Phi-4-mini QLoRA", "m1-d Qwen3.5-4B QLoRA"],
  [["Approach", "Statistical retrieval", "Deep learning, extractive", "Deep learning, generative", "Deep learning, generative"],
   ["Trainable parameters", "None", "All (149M)", "LoRA adapters only", "LoRA adapters only (r = 16)"],
   ["Hardware", "CPU", "GPU, small (a 40-step feasibility run fit in 6.7 GB)", "GPU, 4-bit, expected to fit 16 GB; first feasibility run did not complete", "GPU, 4-bit, expected to fit 16 GB; not yet run"],
   ["Can invent a claim?", "No. Output is verbatim events", "No. Output is verbatim events", "Yes", "Yes"],
   ["Can rephrase and merge events?", "No", "No", "Yes", "Yes"],
   ["Assigns status categories", "By template rule", "By template rule", "Learned", "Learned"],
   ["Expected strength", "Cannot emit an unsupported claim; no GPU; fully explainable", "Better relevance than lexical match when wording differs", "Concise, readable state at low memory cost", "Highest capacity for recall and status reasoning"],
   ["Expected limitation", "Misses paraphrase; verbose; status only as good as the template", "Weak labels from QMSum; cannot summarise across events", "May emit invalid JSON or unsupported claims", "Slowest and largest; same generative risks"],
   ["Justification", "The floor every learned arm must beat, and the matched-seed reference for the unsupported-claim gate", "Separates the value of learning from the value of generation", "Tests generation at the smallest credible size", "Tests whether capacity, not architecture, is the limit"]],
  [1.25, 1.2, 1.3, 1.35, 1.4], "Comparison of the four Model 1 candidates.", size=8)
P("The justification for the matrix as a whole is that each neighbouring pair of candidates isolates one "
  "question. From m1-a to m1-b the template is held fixed and only the ranker changes, so any difference is the "
  "value of learned relevance. From m1-b to m1-c the model stops copying and starts writing, so any difference "
  "is the value, and the risk, of generation. From m1-c to m1-d the method is held fixed and capacity changes. "
  "A comparison built from unrelated models could tell us which one scored highest but not why. The same logic "
  "justifies the controls in Models 2 to 4: a learned arbitration model is only interesting if it produces "
  "fewer harmful outcomes than last-writer-wins, and a learned router only if it beats rules.")
F("fig13_selection_rule.png", "The Model 1 candidate-selection rule frozen in ADR-005. Generated by "
  "docs/reports/generate_t4a6_figures.py.")
H("Preferred model, and when it would lose", 3)
P("No winner exists and none is claimed. Our working preference, stated before any comparative result so that "
  "it can be held against us, is a generative QLoRA candidate, m1-c or m1-d, because a catch-up has to merge "
  "several events into one statement of state and assign it a status, and an extractive template cannot do "
  "either. That preference would lose to the extractive candidates under four conditions, all of which the "
  "selection rule in Figure 12 enforces.")
B(["If a generative candidate exceeds 2% unsupported claims, or is worse than m1-a on unsupported claims for the "
   "same seed, on any one of the three seeds. It is then ineligible and its quality scores are irrelevant. An "
   "extractive candidate cannot fail this gate by construction.",
   "If it falls below 98% schema-valid outputs, 95% attribution accuracy or 95% status consistency on any seed.",
   "If its critical-fact recall is within 0.01 of an extractive candidate's. The tie then passes to BERTScore-F1 "
   "and ROUGE-L, and after those to latency at the 95th percentile and peak memory, where BM25 on a CPU wins.",
   "If the product-session corpus turns out to be small. With few training sessions the weakly supervised and "
   "parameter-free arms have less to lose than a generator that must learn the status categories."])
P("If no candidate passes every gate, ADR-005 requires us to report that no model is promotable and to keep the "
  "extractive control in service while the failures are corrected. Between m1-c and m1-d we hold no preference. "
  "If they are tied within the margins on critical-fact recall, BERTScore-F1 and ROUGE-L, the tie passes to latency at the "
  "95th percentile and then peak memory; we expect the smaller m1-c to win there, but that has not been measured.")

# ------------------------------------------------------------------ 4.4
H("4.4 Model Evaluation Methods", 2)
P("All metrics are computed in one place, the shared evaluation layer under `eval/`, so that no model reports a "
  "number through its own code path. Every candidate, including the parameter-free m1-a, is run with three seeds (13, 29 and 47), because the unsupported-claim gate compares each candidate seed with the m1-a run on the same seed. Results are "
  "reported as the per-seed values, their mean, and a 95% confidence interval; predictions are never pooled "
  "across seeds before a metric is computed, and the contract requires eligibility gates to hold on every seed individually so that one "
  "unsafe seed cannot be hidden by two good ones. With three seeds the interval has two degrees of freedom and is wide by construction; it describes seed-to-seed variation, not sampling error over test examples, which is why the per-seed values are always shown beside it. Each result file records the contract version, configuration "
  "hash, dataset manifest hashes, git commit, model revision, seed, hardware and package versions.")
P("The metrics in Table 42 are committed here, before any comparative result exists. As of 11 November 2026 no "
  "Model 1 candidate has been scored on a test split and no baseline agreement figure has been computed. The "
  "Model 1 definitions are machine-readable in `eval/configs/m1-contract.yaml`, and ADR-005 states that the "
  "definitions and the winner policy cannot change after test results are seen without a new contract version. The gate thresholds, metric definitions and ranking order were committed on 22 October 2026 (commit f2b4d47). Review then made two rules explicit, and both were committed on 11 November 2026 (commit c2028dd), still before any result existed: every gate applies to each seed, with the unsupported-claim gate compared against the m1-a run on the same seed, and each ranking metric has its own tie margin (0.01 for critical-fact recall and BERTScore-F1, 1.0 point for ROUGE-L on its 0 to 100 scale) in place of one shared margin of 0.01.")
T(["Metric", "Why this metric", "Benchmark or split it is measured on", "Committed on"],
  [["M1 critical-fact recall (primary)", "A catch-up that omits the blocker has failed, however fluent. Counts gold critical facts that are covered by a claim supported by its cited events.", "Annotated product-session test split (`session_test`)", "22 Oct 2026 (ADR-005); tie margin 11 Nov 2026 (c2028dd); merged 11 Nov 2026 (US Pacific)"],
   ["M1 unsupported-claim rate (gate: at most 0.02, and no worse than m1-a)", "Measures invention: claims not supported by the events they cite, over emitted claims.", "`session_test`, every seed", "22 Oct 2026 (ADR-005); per-seed rule 11 Nov 2026 (c2028dd)"],
   ["M1 attribution accuracy (gate: at least 0.95)", "A correct fact citing the wrong event cannot be verified by the reader.", "`session_test`, every seed", "22 Oct 2026 (ADR-005); per-seed rule 11 Nov 2026 (c2028dd)"],
   ["M1 status consistency (gate: at least 0.95)", "Reporting blocked work as completed is the most damaging single error.", "`session_test`, every seed", "22 Oct 2026 (ADR-005); per-seed rule 11 Nov 2026 (c2028dd)"],
   ["M1 schema-valid rate (gate: at least 0.98)", "An output that does not parse cannot be shown or scored.", "`session_test`, every seed", "22 Oct 2026 (ADR-005); per-seed rule 11 Nov 2026 (c2028dd)"],
   ["M1 BERTScore-F1 [26]", "Semantic similarity that tolerates paraphrase. Pinned: roberta-large, layer 17, no IDF, no rescaling.", "`session_test` for ranking; QMSum test reported separately", "22 Oct 2026 (ADR-005); tie margin 11 Nov 2026 (c2028dd)"],
   ["M1 ROUGE-L, with ROUGE-1 and ROUGE-2 [25]", "Lexical overlap, comparable with published QMSum figures. Macro F1 under convention `m1_rouge_macro_v1`.", "QMSum test (281 rows) and `session_test`", "22 Oct 2026 (ADR-004); tie margin 11 Nov 2026 (c2028dd)"],
   ["M1 latency p50 and p95, peak VRAM", "A catch-up is read at the moment of joining. Tail latency is set by the long-context minority (section 3.6).", "Same examples, after warm-up, on the recorded GPU", "22 Oct 2026 (ADR-005)"],
   ["M1 human edit rate", "Token edits a reviewer needs to make an output acceptable: the cost a user actually pays.", "Blinded review of the top two candidates", "22 Oct 2026 (ADR-005)"],
   ["M1 training and validation loss", "Convergence and early-stopping signal only. Never used to compare candidates.", "QMSum train and validation", "11 Nov 2026 (this workbook)"],
   ["M2 macro-F1, with per-class F1", "Classes are imbalanced, and accuracy would hide a class that is never predicted.", "Held-out session-level test split", "7 Oct 2026 (Workbook 1)"],
   ["M3 macro-F1; harmful-merge rate; escalation precision and recall", "A wrong merge is worse than an escalation, so harm is measured directly and compared with last-writer-wins.", "Held-out conflict cases", "8 Oct 2026 (`m3-*.yaml`)"],
   ["M4 DAG validity (gate); routing accuracy; completion; latency; cost", "An invalid plan cannot be executed, so validity gates everything else.", "Held-out routing test split", "7 Oct 2026 (Workbook 1)"],
   ["Baseline accuracy, precision, recall, F1, Cohen's kappa [27]", "The five figures the paper reports, at the same scale: 0.94, 0.833, 0.77, 0.80, 0.77. Kappa corrects for chance agreement under imbalance.", "4 human-consensus traces: the only records of the 19-record human file labelled in the current 14-code taxonomy (eval_manifest.json). Reported with sample size and 95% CI", "7 Oct 2026 (Workbook 1; `mast_binary_label_cells_v1`)"],
   ["Baseline agreement with released judge labels", "Pipeline fidelity at scale. Not a reproduction of the human-agreement result and never reported as one.", "1,638 scorable MAST traces", "7 Oct 2026 (Workbook 1)"]],
  [1.55, 2.25, 1.45, 1.25], "Evaluation metrics committed before results.", size=8)
P("Three choices in that table depart from common practice and are argued for here. ROUGE-L is not the primary "
  "metric for Model 1, although it is the metric named on the topic slide and the one Workbook 1 selected on. "
  "The reason is in the data: reference summaries are about 65 words long, and a summary can score well on "
  "overlap while omitting the one blocker that mattered or assigning an action to the wrong person. ROUGE-L and "
  "BERTScore-F1 are still reported and still used for ranking, but only after the safety gates and only to "
  "separate candidates that are tied on recall. Second, a candidate that emits no claims does not earn a "
  "perfect safety score: it fails recall, and its attribution accuracy, which would otherwise be undefined at zero claims, is recorded as zero by contract convention. Third, results on "
  "QMSum are reported separately and cannot select the winner, because QMSum contains none of the labels the "
  "gates need.")
P("The baseline comparison has a limit that we state before running it. The paper's figures measure agreement with expert annotation, but the released human file holds only 4 traces labelled in the current 14-code taxonomy. Its other 15 records were labelled against older taxonomies with 18 and 17 failure modes whose codes do not map one to one onto the current 14, so the frozen evaluation manifest excludes them instead of pooling them. Four traces give 56 label cells. Even at the paper's accuracy of 0.94, a binomial 95% interval over 56 cells is about 0.13 wide, several times the 0.02 accuracy tolerance, and cells from one trace are not independent, so the real uncertainty is larger. The human comparison can therefore expose a gross failure but cannot by itself confirm a reproduction. We report it with its sample size beside a second, separately labelled check: agreement with the released judge labels on all 1,638 scorable traces, which tests whether our prompt, parser and scoring recover the published pipeline at scale.")
P("Evaluation ends with two further steps for every model. An ablation varies the context budget (512, 1,024 "
  "and 2,048 tokens) and, for Model 1, approved memory on and off. And every failure is assigned one of seven "
  "frozen failure codes (invalid schema, missing critical fact, unsupported claim, wrong attribution, wrong "
  "status, generic output, truncated), which feeds the categorised failure analysis required by AI-8.")
H("4.5 Data Pipeline Demo", 2)
P("This section demonstrates the pipeline that carries data from its original sources into a queryable "
  "warehouse, together with the checks and run history that make a run auditable. Everything shown here is on "
  "the main branch in `infra/warehouse/pipeline.py` (pull request #33) and runs end to end on a laptop in about "
  "seven seconds, with no cloud account and no scheduler. Figure 3 gives the same path as a diagram; this "
  "section gives the commands, the warehouse it builds and the output it actually produces.")
P("One command runs the whole pipeline, and a second shows the run history. These are the exact commands used "
  "for the run reproduced in Figures 13 and 14:", after=4)
CODE(["$ source .venv/bin/activate",
      "$ python data/scripts/download_mast.py        # stage 0: fetch and checksum the sources",
      "$ python data/scripts/eda_mast.py             # clean and flatten MAST",
      "$ python infra/warehouse/pipeline.py          # ingest, clean, transform, quality",
      "$ python infra/warehouse/pipeline.py --report # run history and latest checks"])
P("No arguments are required: `--data-root` defaults to the repository's `data/` directory and `--db` to "
  "`warehouse/mas.duckdb`, so a reader who has cloned the repository and installed the lock file can reproduce "
  "the run with the four commands above and nothing else.", after=6)
P("The pipeline is deliberately re-runnable. Each run replaces the `raw`, `staging` and `marts` layers from the "
  "pinned sources and appends to the `meta` layer, so the data is always rebuilt from source while the history "
  "of runs accumulates. A run is therefore idempotent in its data and additive in its audit trail.", after=8)
H("Stages: ingestion, cleaning, transformation and quality", 3)
T(["Stage", "What it does", "Tools", "Rows in / out", "Measured"],
  [["ingest", "Reads the pinned MAST download and the three frozen QMSum split files, verifies every file against its recorded SHA-256 before anything is loaded, and writes them unaltered into the `raw` layer. A checksum mismatch aborts the run.", "DuckDB, hashlib", "3,452 / 3,452", "1.26 s"],
   ["clean", "Applies the frozen label and key policy: the canonical key is (`trace.key`, `trace_id`), a label is 0, 1 or null and null is never silently converted to 0, and the 4 records whose 14 codes are all null are excluded from scoring. Writes the `staging` layer.", "DuckDB SQL, `eda_mast.py`", "3,452 / 3,448", "5.59 s"],
   ["transform", "Reshapes staging into a star schema: four dimension tables and three fact tables, including the long-form label table that turns 14 label columns into one row per positive label.", "DuckDB SQL", "3,448 / 3,448", "0.02 s"],
   ["quality", "Runs 19 assertions over the built warehouse (Table 45) and records each one, with its expected and actual value, in `meta.quality_checks`.", "DuckDB SQL", "19 / 19", "0.01 s"]],
  [0.75, 3.25, 0.95, 0.8, 0.65], "The four pipeline stages, with durations from the run captured in Figure 13 "
  "(total 6.89 s).", size=8.5)
H("The warehouse: raw, staging, marts and metadata", 3)
P("The warehouse is a single DuckDB file, `warehouse/mas.duckdb`, organised in four schemas so that every "
  "number can be traced back to the untouched source it came from [23], [24]. The row counts below were queried "
  "from the file after the run.", after=4)
T(["Layer", "Purpose", "Table", "Rows", "Cols"],
  [["`raw`", "Source data exactly as downloaded, so the original is always recoverable without re-downloading.", "`mast_traces`", "1,642", "10"],
   ["", "", "`qmsum_examples`", "1,810", "10"],
   ["`staging`", "Cleaned and validated, with the label and key policy applied and nulls preserved.", "`mast_traces_clean`", "1,638", "7"],
   ["", "", "`mast_labels_long`", "22,932", "4"],
   ["", "", "`qmsum_examples_clean`", "1,810", "9"],
   ["`marts`", "Star schema for analysis: the tables that section 3.6 and the figures are computed from.", "`fact_trace`", "1,638", "11"],
   ["", "", "`fact_trace_failure`", "5,141", "2"],
   ["", "", "`fact_m1_example`", "1,810", "7"],
   ["", "", "`dim_failure_mode`", "14", "3"],
   ["", "", "`dim_benchmark`", "8", "2"],
   ["", "", "`dim_framework`", "7", "2"],
   ["", "", "`dim_llm`", "5", "2"],
   ["`meta`", "Pipeline monitoring: one row per stage per run, and one row per quality check per run. This layer is appended to, never replaced, so it grows with each run.", "`pipeline_runs`", "4 per run", "10"],
   ["", "", "`quality_checks`", "19 per run", "6"]],
  [0.7, 2.75, 1.7, 0.7, 0.45], "Every table in the warehouse, by layer, with row counts queried from "
  "`warehouse/mas.duckdb` after the run. The `raw`, `staging` and `marts` layers are rebuilt from source on "
  "every run, so their counts are fixed; the `meta` layer accumulates, so its totals depend on how many runs "
  "the warehouse has seen.", size=8.5)
H("Quality checks", 3)
P("The pipeline does not report success merely because the code did not crash. It asserts 19 facts about the "
  "warehouse it has just built, and a run is a failure if any one of them does not hold. The checks fall into "
  "three groups: counts that must match the published corpus, split-hygiene checks that would catch leakage "
  "between train, validation and test, and reconciliations that prove no row was invented or lost between "
  "layers. All 19 passed on the run captured in Figure 13.", after=4)
T(["#", "Check", "What it would catch", "Expected", "Actual"],
  [["1", "mast raw records", "A partial or over-long download: the paper reports 1,642 records.", "1,642", "1,642"],
   ["2", "mast scorable records", "Wrong handling of the all-null records.", "1,638", "1,638"],
   ["3", "mast excluded records (all-null)", "Silently dropping or silently scoring the 4 unlabelled records.", "4", "4"],
   ["4", "mast key (trace_key, trace_id) duplicates", "A duplicated trace, which would double-count failures. `trace_id` alone is not unique.", "0", "0"],
   ["5", "mast label values outside {0,1,NULL}", "A stray value from a future taxonomy or a parsing bug.", "0", "0"],
   ["6", "mast null labels converted to 0 (null cells raw vs staging)", "The most damaging silent error available here: turning \"not labelled\" into \"no failure\".", "0", "0"],
   ["7", "qmsum split train examples", "A split rebuilt with different sizes from the frozen manifest.", "1,257", "1,257"],
   ["8", "qmsum split val examples", "As above, for validation.", "272", "272"],
   ["9", "qmsum split test examples", "As above, for test.", "281", "281"],
   ["10", "qmsum example ids in >1 split", "Direct example-level leakage between splits.", "0", "0"],
   ["11", "qmsum meetings in >1 split (by id-derived meeting)", "Meeting-level leakage: two questions about the same meeting landing on opposite sides of the split.", "0", "0"],
   ["12", "qmsum longest-context-span hashes shared across splits", "Near-duplicate context reused across splits even when ids and meetings differ.", "0", "0"],
   ["13", "reconcile: raw qmsum = staging qmsum", "A row lost or added during cleaning.", "1,810", "1,810"],
   ["14", "reconcile: staging qmsum = fact_m1_example", "A row lost or added during transformation.", "1,810", "1,810"],
   ["15", "reconcile: staging traces = fact_trace", "A trace lost between staging and the fact table.", "1,638", "1,638"],
   ["16", "reconcile: positive labels = fact_trace_failure rows", "A mismatch between the wide label columns and the long-form failure table.", "5,141", "5,141"],
   ["17", "reconcile: sum(n_failures) = fact_trace_failure rows", "A per-trace failure count that disagrees with the rows it summarises.", "5,141", "5,141"],
   ["18", "reconcile: category counts sum to n_failures", "A trace whose three category counts do not add up to its total.", "0", "0"],
   ["19", "fact_trace rows with unmatched dimension key", "A fact row pointing at a framework, benchmark or model that is not in the dimension tables.", "0", "0"]],
  [0.25, 2.1, 2.85, 0.65, 0.65], "The 19 quality checks asserted on every run, with the values recorded on 12 November 2026. A run fails if any check does not hold.", size=8)
H("Monitoring and management", 3)
P("Monitoring is built into the pipeline rather than bolted on. Every stage of every run writes a row to "
  "`meta.pipeline_runs` recording the run id, stage, start time, duration, rows in, rows out, status, the git "
  "commit the code was at, and the error text if it failed; every check writes a row to `meta.quality_checks`. "
  "Because both tables are appended to and carry the git commit, a regression can be located in time and in "
  "version: if a count changes, the run history shows which run and which commit it changed at. The "
  "`--report` flag reads these tables back and prints the recent run history, the latest check results and "
  "summary views of the marts. Management actions are ordinary commands rather than a user interface: "
  "`--stage` re-runs a single stage, `--last` sets how many runs the report shows, `--data-root` and `--db` "
  "point the pipeline at a different copy of the data or warehouse, and "
  "deleting the DuckDB file rebuilds everything from the pinned sources. Section 4.2 explains why no workflow "
  "scheduler is used yet and what would make Airflow worth its operational cost [22].", after=8)
H("A real run", 3)
P("Figure 13 is a screen capture of the pipeline running to completion on 12 November 2026 at commit "
  "`1b3c78c`. The four stages run in order, the four source files are checksum-verified before anything is "
  "loaded, all 19 quality checks report `[PASS]`, and the run ends `SUCCESS in 6.89s`. Nothing in the capture "
  "is edited, and the same output in text form is committed in `infra/warehouse/SAMPLE_RUN.md` so that a reader "
  "can compare an earlier run against this one; the counts are identical across both.", after=4)
F("fig14_pipeline_run.png", "A successful end-to-end run of the data pipeline, from source files to warehouse: "
  "checksum verification, the four stages, all 19 quality checks passing, and the run summary. Captured on "
  "12 November 2026 at commit `1b3c78c`.", width=6.4)
P("Figure 14 shows the monitoring side, printed by `--report` from the `meta` layer after three runs. The upper "
  "table is `meta.pipeline_runs`: twelve rows, one per stage per run, each carrying its duration, row counts, "
  "status and the git commit the code was at. The lower table is `meta.quality_checks`, listing all 19 "
  "assertions with their expected and actual values. Together these are the audit trail: the run history shows "
  "that the pipeline has been run repeatedly with stable row counts, and the check table shows that the "
  "warehouse was verified rather than merely built.", after=4)
F("fig15_pipeline_monitoring.png", "Pipeline monitoring from the `meta` layer. Above: `meta.pipeline_runs`, one "
  "row per stage per run across three runs, with durations, row counts and the git commit. Below: "
  "`meta.quality_checks`, all 19 checks with expected and actual values, every one PASS.", width=6.4)
H("What this demonstration does not cover", 3)
P("The pipeline is complete for the two public sources and only for those. MAST and QMSum are pinned, "
  "downloaded, checksum-verified, cleaned, transformed, loaded and checked, and that path is what the output "
  "above exercises. Ingestion of our own product sessions is not complete: the session export is still pending, "
  "`data/sessions/raw/` is empty as of 11 November 2026, and no recorded session has entered the warehouse. "
  "The ingestion stage has no session reader yet, so the row counts above contain no product-session data. "
  "This matters for the project because the product-session corpus, not the public corpora, is what selects "
  "the winner of every bake-off (section 3.5), and it is recorded as the first carry-forward risk at the end of "
  "this workbook. What the demonstration establishes is that the path from source to warehouse works, is "
  "checked, and is ready for that third source when the export lands.", after=8)
H("4.6 First Model Implementation Status", 2)
P("This section records what is implemented for Model 1 as of 12 November 2026, and is deliberately explicit "
  "about what the evidence does and does not support.")
P("The shared evaluation harness is merged. It landed on the main branch through pull request #25 (DAT-61), "
  "with follow-up corrections in pull request #41 that time latency over all examples and count candidate "
  "errors as invalid rather than skipping them. Review of #25 had found the comparison step applying the "
  "safety gates to the mean of the three seeds; the merged version applies every gate to each seed "
  "individually and compares the unsupported-claim rate against the m1-a run on the matching seed, as ADR-005 "
  "requires.")
P("The first candidate is also merged. M1-A, the parameter-free BM25 extractive control, is on the main branch "
  "through pull request #26 (DAT-58) and exposes `models.m1_catchup.bm25:build_eval_runner` to the shared "
  "harness; it is implemented and merged, not a draft. Running it through the harness produced 3 of 3 "
  "schema-valid outputs on the synthetic `smoke_holdout` fixture.")
P("That 3/3 result is integration evidence, not an evaluation result, and the distinction is the point of this "
  "section. It shows that a candidate can be loaded by the harness, produce output that parses against the "
  "`m1-output-v1` schema, and be scored without error: the wiring works. It is not a measurement of catch-up "
  "quality, for three reasons. The fixture is synthetic and holds 3 examples. The M1-A ranking rules were "
  "fitted on the synthetic smoke train and dev templates, so the fixture is not independent of the method "
  "being run on it, and the number says nothing about generalisation. And none of the gates or ranking metrics "
  "in Table 42 is computed on it, because the annotated product-session split those metrics are defined over "
  "does not exist yet. A reportable Model 1 result requires the frozen split at `data/splits/m1_session_v1/` "
  "and the production metric evaluator, and neither is on the main branch.")
P("There is therefore no Model 1 winner, and this workbook does not name one. Table 46 records the status of "
  "each of the four candidates. ADR-005 forbids a selection run before the annotated split is frozen, so the "
  "absence of a winner is the contract working as designed rather than a slipped task.", after=4)
T(["Candidate", "Architecture", "Status on 12 November 2026", "Reportable result?"],
  [["`m1-a`", "BM25 ranker plus fixed template (classical, CPU, parameter-free)", "Merged on `main` (DAT-58, pull request #26). Smoke-only integration run passed 3/3 schema-valid examples on the synthetic `smoke_holdout` fixture.", "No. Integration evidence only; rules were fitted on the smoke templates."],
   ["`m1-b`", "ModernBERT-base selector plus fixed template (full fine-tune)", "Candidate code remains off `main` on branch `m1-candidate-train-infer`, with no pull request. A 40-step GPU feasibility smoke passed.", "No. No training or evaluation result."],
   ["`m1-c`", "Phi-4-mini-instruct, 4-bit QLoRA", "Candidate code off `main`. First feasibility run stopped after 2 of 15 steps at roughly 5 minutes per step and still needs diagnosis.", "No."],
   ["`m1-d`", "Qwen3.5-4B, 4-bit QLoRA", "Candidate code off `main`. Feasibility run not started.", "No."]],
  [0.65, 1.85, 2.9, 1.1], "Model 1 candidate status. No candidate has a reportable evaluation result and no winner has been selected.", size=8.5)
P("One earlier run is sometimes mistaken for a candidate result and is listed here so that it is not. A "
  "Qwen3-1.7B model was used to verify GPU loading, 4-bit NF4 QLoRA, checkpoint and resume, and inference; its "
  "50-step run moved training loss from 3.90 to 2.14 and wrote a 133 MB adapter. Training loss is not catch-up "
  "quality, and Qwen3-1.7B is not in the frozen candidate matrix at all. It is infrastructure feasibility "
  "evidence only. Its configuration is preserved at `models/m1_catchup/feasibility/qwen3-1.7b.yaml`, and the "
  "run notes remain in `docs/verification/m1_training_run.md` for anyone who wants to audit it.")

# ------------------------------------------------------------------ references
H("References", 1)
P("References [1] to [17] are listed in Workbook 1 and keep their numbers. The sources introduced in sections 3 "
  "and 4 are added below.", after=6)
for ref in [
    "[18] S. Robertson and H. Zaragoza, \"The probabilistic relevance framework: BM25 and beyond,\" Found. Trends Inf. Retr., vol. 3, no. 4, pp. 333-389, 2009.",
    "[19] Microsoft, \"Phi-4-mini technical report: Compact yet powerful multimodal language models via mixture-of-LoRAs,\" arXiv:2503.01743, 2025. [Online]. Available: https://arxiv.org/abs/2503.01743.",
    "[20] T. Dettmers, A. Pagnoni, A. Holtzman, and L. Zettlemoyer, \"QLoRA: Efficient finetuning of quantized LLMs,\" in Advances in Neural Information Processing Systems 36, 2023.",
    "[21] Qwen Team, \"Qwen3.5-4B,\" Hugging Face model card. [Online]. Available: https://huggingface.co/Qwen/Qwen3.5-4B. [Accessed: Nov. 11, 2026].",
    "[22] Apache Software Foundation, \"Apache Airflow documentation.\" [Online]. Available: https://airflow.apache.org/docs/. [Accessed: Nov. 11, 2026].",
    "[23] M. Kleppmann, Designing Data-Intensive Applications. Sebastopol, CA, USA: O'Reilly Media, 2017.",
    "[24] M. Raasveldt and H. Muhleisen, \"DuckDB: An embeddable analytical database,\" in Proc. ACM SIGMOD Int. Conf. Manage. Data, 2019, pp. 1981-1984.",
    "[25] C.-Y. Lin, \"ROUGE: A package for automatic evaluation of summaries,\" in Text Summarization Branches Out: Proc. ACL-04 Workshop, 2004, pp. 74-81.",
    "[26] T. Zhang, V. Kishore, F. Wu, K. Q. Weinberger, and Y. Artzi, \"BERTScore: Evaluating text generation with BERT,\" in Proc. Int. Conf. Learn. Representations (ICLR), 2020.",
    "[27] J. Cohen, \"A coefficient of agreement for nominal scales,\" Educ. Psychol. Meas., vol. 20, no. 1, pp. 37-46, 1960.",
    "[28] G. Ke, Q. Meng, T. Finley, T. Wang, W. Chen, W. Ma, Q. Ye, and T.-Y. Liu, \"LightGBM: A highly efficient gradient boosting decision tree,\" in Advances in Neural Information Processing Systems 30, 2017, pp. 3146-3154.",
]:
    P(ref, J, after=6)

# ------------------------------------------------------------------ non-report pages
d.add_page_break()
H("Submission checklist (not part of the report)", 2)
T(["Check", "Yes / No"],
  [["Every section above is written as report prose, not as notes", "Yes"],
   ["Splits are fixed, version-controlled, and the leakage check is reported", "Yes for Model 1 supervision: `data/splits/m1_v1/`, commit `330603f`; Table 29. The product-session split is not yet prepared (section 3.5)."],
   ["Metrics were committed before any results existed", "Yes. ADR-004, ADR-005; Table 42"],
   ["Five systems named: four product models, with the published baseline system listed separately", "Yes. Table 35. The baseline is selected for reproduction and has not been run (DAT-36)."],
   ["Every claim links to a commit, run, dataset version or Linear issue", "Yes for every count, split, metric and decision (`docs/reports/t4a6_data_facts.json` at commit `fbb3fdf`; ADRs; pull requests). Interpretive statements are argued in the prose."],
   ["Each section names the team member who wrote it", "Yes. Title page"]],
  [4.2, 2.3])
H("Self-assessment and gap register", 2)
T(["Report section", "Our rating", "If below good: what is missing", "Owner", "Lands by (proposed)"],
  [["3.1 to 3.6", "Good", "Not below good, but not excellent: the product-session corpus that selects the Model 1 winner has no recorded sessions, so sections 3.2 to 3.5 describe it as planned.", "Naman", "2 Dec 2026"],
   ["4.1 to 4.4", "Good", "Not below good. Models 2 and 4 have no committed configuration files yet; their candidates are described from Workbook 1.", "Naman, Shriram", "298B, cycle 1"],
   ["4.5 Data Pipeline Demo", "Good", "Not below good: the path from source to warehouse is complete, checked by 19 assertions, monitored through the `meta` layer and demonstrated live. It is not excellent because it covers two of the three sources; ingestion of our own product sessions is not built, and the session export is still pending.", "Shriram", "With the first sessions, 2 Dec 2026"],
   ["4.6 First Model Implementation Status", "Good", "Not below good: the harness and the first candidate are merged and the status is reported without overstatement. It is not excellent because no candidate has a reportable evaluation result and no winner exists, which needs the frozen annotated session split.", "Ayush, Pramod", "7 Dec 2026"],
   ["References", "Good", "Not below good, but not excellent: every algorithm, dataset and metric source is cited, including [28] added in review, but the software libraries named in Table 38 (PyTorch, Transformers, PEFT) are not cited separately.", "Pramod", ""]],
  [1.0, 0.8, 2.9, 0.9, 0.9])
H("Carry-forward from Workbook 1", 2)
T(["Item", "Why it did not land, or what changed", "Owner", "New target (proposed; each owner to confirm)"],
  [["Model 1 candidate matrix (sections 1.1, 1.4; Tables 1 and 8)", "Changed. Workbook 1 named an extractive ModernBERT control with Qwen and Gemma LoRA generators. ADR-005 freezes BM25, ModernBERT-base, Phi-4-mini with QLoRA and Qwen3.5-4B with QLoRA, adding a parameter-free floor and replacing Gemma.", "Ayush, Pramod", "Done, 11 Nov 2026"],
   ["Model 1 selection metric (sections 1.1, 1.2 AI-3, 2.2.2)", "Changed. Workbook 1 selected on validation ROUGE-L under a factuality guardrail. Selection now applies per-seed safety gates and then ranks on critical-fact recall, BERTScore-F1 and ROUGE-L, on annotated product sessions. ROUGE-L is still reported on QMSum test against 28.2, the published QMSum BART score used as a reference floor in Workbook 1, but it no longer selects.", "Pramod", "Done, 11 Nov 2026"],
   ["QMSum size (DR-1; Table 9)", "Corrected. Workbook 1 quoted the published 1,808 query-summary pairs. The pinned release yields 1,810, and the splits are built from those.", "Naman", "Done"],
   ["Pilot session corpus (DR-2, DR-3)", "Not landed. No session has been recorded, because the end-to-end integration gate has not been passed. The risk-register trigger of fewer than five sessions by late October has fired; the documented fallback of internal sessions plus scripted cases is in effect, and 18 scripted smoke examples exist (DAT-53).", "Naman", "First sessions by 2 Dec 2026"],
   ["Automated session-level leakage check (DR-4)", "Partly landed. `make_splits.py` accepts a grouping option that the Model 1 path does not read, so the no-shared-meeting guarantee rests on QMSum's inherited partition and on the checks in Table 29, not on a grouping implementation. The session-level check is needed before `m1_session_v1` is built.", "Naman", "With the session split"],
   ["Harness runs one candidate end to end (Progress Report 1)", "Landed for integration, not for evaluation. The shared Model 1 harness (DAT-61) was merged on 11 November 2026 (pull request #25), with follow-ups in pull request #41. Review had found the comparison step applying gates to the three-seed mean; the merged version applies every gate to each seed and compares unsupported claims with the matched m1-a seed, as ADR-005 requires. M1-A is now also on main (pull request #26) and has run through the harness, passing 3 of 3 schema-valid examples on the synthetic smoke fixture. That is integration evidence only: it is not a reportable evaluation result, because the fixture is synthetic, the M1-A rules were fitted on it, and the annotated session split is still absent (section 4.6).", "Pramod", "Reportable run with the session split"],
   ["Model 1 bake-off and winner (AI-3)", "At risk. Training and inference paths and GPU feasibility are in progress, but ADR-005 forbids a selection run until the annotated product-session split is frozen. The final report will carry either the winner or the documented shortfall.", "Ayush", "7 Dec 2026"],
   ["MAST judge environment and final runs (DAT-25, DAT-26, DAT-27, DAT-36)", "Not landed. Prompt, parser, batch runner, provenance and metrics are on main; the pinned o1 judge environment and the clean-environment smoke test are open.", "Ayush, Shriram", "2 Dec 2026"],
   ["Cloud deployment (FR-8; Table 16)", "Deferred. The prototype runs locally under Docker Compose and no cloud cost has been incurred. Deployment is needed when participants outside the team join, which is the 298B controlled study (section 4.2).", "Ayush", "298B"],
   ["Branch protection (DAT-10)", "Not landed. Reviews are enforced by convention, not by a repository rule.", "Ayush", "18 Nov 2026"]],
  [1.5, 3.3, 0.8, 0.9], size=8.5)

d.save(str(OUT))
print("saved", OUT, "tables", N["t"], "figures", N["f"])
