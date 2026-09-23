"""Static HTML viewer for saved MAST prediction JSONL records.

Reads ADR-002 shaped files only. No network, no sample data in this module.
"""

from __future__ import annotations

import argparse
import html
import json
from collections import Counter
from pathlib import Path
from typing import Any

from models.baseline_mast.parse_judge import MAST_CODES

# update here if ADR-002 changes
F_RUN_ID = "run_id"
F_TRACE_ID = "trace_id"
F_FRAMEWORK = "framework"
F_BENCHMARK = "benchmark"
F_DATASET_VERSION = "dataset_version"
F_DATASET_SHA256 = "dataset_sha256"
F_PROMPT_VERSION = "prompt_version"
F_PROMPT_SHA256 = "prompt_sha256"
F_PARSER_VERSION = "parser_version"
F_MODEL_ID = "model_id"
F_MODEL_SETTINGS = "model_settings"
F_TIMESTAMP_UTC = "timestamp_utc"
F_LATENCY_MS = "latency_ms"
F_RETRY_COUNT = "retry_count"
F_ERROR = "error"
F_TRUNCATED = "truncated"
F_HUMAN_LABELS = "human_labels"
F_RAW_RESPONSE = "raw_response"
F_RAW_TYPE = "raw_type"
F_PARSE_STATUS = "parse_status"
F_LABELS = "labels"
F_PREDICTED_LABELS = "predicted_labels"
F_MISSING_CODES = "missing_codes"
F_AMBIGUOUS_CODES = "ambiguous_codes"
F_CONFLICTING_CODES = "conflicting_codes"
F_UNKNOWN_CODES = "unknown_codes"
F_SUMMARY = "summary"
F_TASK_COMPLETED = "task_completed"
F_WARNINGS = "warnings"
F_LABELS_OFFICIAL = "labels_official"
F_TRACE_TEXT = "trace_text"

M_GIT_SHA = "git_sha"
M_START = "start_time_utc"
M_END = "end_time_utc"
M_STATUS_COUNTS = "parse_status_counts"

STATUS_UNREADABLE = "unreadable_record"

OUTCOME_TP = "TP"
OUTCOME_FP = "FP"
OUTCOME_FN = "FN"
OUTCOME_TN = "TN"
OUTCOME_NA = "NA"


def compare(
    human: bool | None, predicted: bool | None
) -> str:
    """Return TP, FP, FN, TN, or NA for one code."""
    if human is None or predicted is None:
        return OUTCOME_NA
    if human and predicted:
        return OUTCOME_TP
    if (not human) and predicted:
        return OUTCOME_FP
    if human and (not predicted):
        return OUTCOME_FN
    return OUTCOME_TN


def load_records(path: Path) -> list[dict[str, Any]]:
    """Load JSONL; bad lines become unreadable_record rows."""
    records: list[dict[str, Any]] = []
    text = path.read_text(encoding="utf-8")
    for i, line in enumerate(text.splitlines()):
        if line.strip() == "":
            continue
        try:
            obj = json.loads(line)
            if not isinstance(obj, dict):
                raise TypeError("not an object")
            records.append(obj)
        except (json.JSONDecodeError, TypeError):
            records.append(
                {
                    F_TRACE_ID: f"line-{i + 1}",
                    F_PARSE_STATUS: STATUS_UNREADABLE,
                    F_RAW_RESPONSE: line,
                    F_HUMAN_LABELS: {},
                    F_LABELS: {},
                    F_FRAMEWORK: "",
                }
            )
    return records


def _as_bool_map(value: object) -> dict[str, bool | None]:
    if not isinstance(value, dict):
        return {code: None for code in MAST_CODES}
    out: dict[str, bool | None] = {}
    for code in MAST_CODES:
        raw = value.get(code)
        if raw is None:
            out[code] = None
        elif isinstance(raw, bool):
            out[code] = raw
        else:
            out[code] = None
    return out


def per_code_outcomes(record: dict[str, Any]) -> dict[str, str]:
    human = _as_bool_map(record.get(F_HUMAN_LABELS))
    predicted = _as_bool_map(record.get(F_LABELS))
    return {
        code: compare(human[code], predicted[code]) for code in MAST_CODES
    }


def disagreement_count(record: dict[str, Any]) -> int:
    outcomes = per_code_outcomes(record)
    return sum(
        1 for v in outcomes.values() if v in (OUTCOME_FP, OUTCOME_FN)
    )


def status_counts(records: list[dict[str, Any]]) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for rec in records:
        status = str(rec.get(F_PARSE_STATUS, "unknown"))
        counter[status] += 1
    return dict(sorted(counter.items()))


def fp_fn_by_code(
    records: list[dict[str, Any]],
) -> dict[str, dict[str, int]]:
    result = {
        code: {OUTCOME_FP: 0, OUTCOME_FN: 0} for code in MAST_CODES
    }
    for rec in records:
        for code, outcome in per_code_outcomes(rec).items():
            if outcome in (OUTCOME_FP, OUTCOME_FN):
                result[code][outcome] += 1
    return result


def _esc(value: object) -> str:
    if value is None:
        return ""
    return html.escape(str(value), quote=True)


def _css() -> str:
    return """
body{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:13px;
margin:16px;color:#14202b;background:#f7f8fa}
h1,h2{font-family:system-ui,sans-serif}
table{border-collapse:collapse;width:100%;margin:12px 0}
th,td{border:1px solid #c5ced6;padding:4px 6px;text-align:left;
vertical-align:top}
th{background:#e8eef3}
.grid td{text-align:center;min-width:2.2em}
.TP{background:#dff0e6}.FP{background:#f8d7da}.FN{background:#fff3cd}
.TN{background:#eef2f5}.NA{background:#f0f0f0;color:#666}
.filters{display:flex;flex-wrap:wrap;gap:10px;align-items:center;
margin:12px 0;padding:8px;background:#fff;border:1px solid #c5ced6}
.meta{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));
gap:6px;margin:8px 0}
.meta div{background:#fff;border:1px solid #c5ced6;padding:6px}
details{margin:6px 0}
pre{white-space:pre-wrap;word-break:break-word;background:#fff;
border:1px solid #c5ced6;padding:8px;max-height:240px;overflow:auto}
.hidden{display:none}
#shown{font-weight:600}
""".strip()


def _js() -> str:
    return """
function applyFilters(){
  const onlyDis = document.getElementById('f_dis').checked;
  const onlyBad = document.getElementById('f_bad').checked;
  const fw = document.getElementById('f_fw').value;
  const code = document.getElementById('f_code').value;
  const q = document.getElementById('f_q').value.trim().toLowerCase();
  const rows = document.querySelectorAll('tr.trace-row');
  let shown = 0;
  rows.forEach(function(row){
    let ok = true;
    if(onlyDis && row.dataset.disagreements === '0') ok = false;
    if(onlyBad && row.dataset.status === 'ok') ok = false;
    if(fw && row.dataset.framework !== fw) ok = false;
    if(code){
      const cell = row.querySelector('[data-code=\"'+code+'\"]');
      const v = cell ? cell.dataset.outcome : '';
      if(v !== 'FP' && v !== 'FN') ok = false;
    }
    if(q && !(row.dataset.trace || '').toLowerCase().includes(q)) ok=false;
    row.classList.toggle('hidden', !ok);
    if(ok) shown += 1;
  });
  document.getElementById('shown').textContent =
    shown + ' of ' + rows.length + ' shown';
}
document.addEventListener('DOMContentLoaded', function(){
  ['f_dis','f_bad','f_fw','f_code','f_q'].forEach(function(id){
    const el = document.getElementById(id);
    if(el) el.addEventListener('input', applyFilters);
    if(el) el.addEventListener('change', applyFilters);
  });
  applyFilters();
});
""".strip()


def build_html(
    records: list[dict[str, Any]],
    manifest: dict[str, Any] | None,
) -> str:
    """Build a self-contained HTML report string."""
    manifest = manifest or {}
    counts = status_counts(records)
    fp_fn = fp_fn_by_code(records)
    n_dis = sum(1 for r in records if disagreement_count(r) > 0)
    frameworks = sorted(
        {
            str(r.get(F_FRAMEWORK, ""))
            for r in records
            if r.get(F_FRAMEWORK)
        }
    )

    run_id = manifest.get(F_RUN_ID) or (
        records[0].get(F_RUN_ID) if records else ""
    )
    model_id = manifest.get(F_MODEL_ID) or (
        records[0].get(F_MODEL_ID) if records else ""
    )
    prompt_version = manifest.get(F_PROMPT_VERSION) or (
        records[0].get(F_PROMPT_VERSION) if records else ""
    )
    prompt_sha = str(
        manifest.get(F_PROMPT_SHA256)
        or (records[0].get(F_PROMPT_SHA256) if records else "")
        or ""
    )
    parser_version = manifest.get(F_PARSER_VERSION) or (
        records[0].get(F_PARSER_VERSION) if records else ""
    )
    dataset_version = (
        records[0].get(F_DATASET_VERSION) if records else ""
    )

    status_rows = "".join(
        f"<tr><td>{_esc(k)}</td><td>{_esc(v)}</td></tr>"
        for k, v in counts.items()
    )
    code_rows = "".join(
        (
            f"<tr><td>{_esc(code)}</td>"
            f"<td>{fp_fn[code][OUTCOME_FP]}</td>"
            f"<td>{fp_fn[code][OUTCOME_FN]}</td></tr>"
        )
        for code in MAST_CODES
    )
    fw_opts = "".join(
        f'<option value="{_esc(f)}">{_esc(f)}</option>'
        for f in frameworks
    )
    code_opts = "".join(
        f'<option value="{_esc(c)}">{_esc(c)}</option>'
        for c in MAST_CODES
    )

    header_cells = "".join(
        f"<th>{_esc(c)}</th>" for c in MAST_CODES
    )
    body_rows: list[str] = []
    for rec in records:
        outcomes = per_code_outcomes(rec)
        dis = disagreement_count(rec)
        status = str(rec.get(F_PARSE_STATUS, ""))
        trace_id = str(rec.get(F_TRACE_ID, ""))
        framework = str(rec.get(F_FRAMEWORK, ""))
        cells = "".join(
            (
                f'<td class="{_esc(outcomes[c])}" data-code="{_esc(c)}" '
                f'data-outcome="{_esc(outcomes[c])}">'
                f"{_esc(outcomes[c])}</td>"
            )
            for c in MAST_CODES
        )
        human = _as_bool_map(rec.get(F_HUMAN_LABELS))
        predicted = _as_bool_map(rec.get(F_LABELS))
        human_json = _esc(json.dumps(human, indent=2))
        pred_json = _esc(json.dumps(predicted, indent=2))
        parsed_json = _esc(
            json.dumps(
                {
                    F_PARSE_STATUS: rec.get(F_PARSE_STATUS),
                    F_LABELS: rec.get(F_LABELS),
                    F_PREDICTED_LABELS: rec.get(F_PREDICTED_LABELS),
                    F_MISSING_CODES: rec.get(F_MISSING_CODES),
                    F_AMBIGUOUS_CODES: rec.get(F_AMBIGUOUS_CODES),
                    F_CONFLICTING_CODES: rec.get(F_CONFLICTING_CODES),
                    F_UNKNOWN_CODES: rec.get(F_UNKNOWN_CODES),
                    F_WARNINGS: rec.get(F_WARNINGS),
                    F_LABELS_OFFICIAL: rec.get(F_LABELS_OFFICIAL),
                },
                indent=2,
            )
        )
        trace_block = ""
        if rec.get(F_TRACE_TEXT):
            trace_block = (
                "<details><summary>trace text</summary>"
                f"<pre>{_esc(rec.get(F_TRACE_TEXT))}</pre></details>"
            )
        detail = f"""
<details>
<summary>detail {_esc(trace_id)}</summary>
<p><b>summary</b>: {_esc(rec.get(F_SUMMARY))}</p>
<p><b>task_completed</b>: {_esc(rec.get(F_TASK_COMPLETED))}</p>
<p><b>warnings</b>: {_esc(rec.get(F_WARNINGS))}</p>
<p><b>missing</b>: {_esc(rec.get(F_MISSING_CODES))}
 | <b>ambiguous</b>: {_esc(rec.get(F_AMBIGUOUS_CODES))}
 | <b>conflicting</b>: {_esc(rec.get(F_CONFLICTING_CODES))}
 | <b>unknown</b>: {_esc(rec.get(F_UNKNOWN_CODES))}</p>
<p><b>retry_count</b>: {_esc(rec.get(F_RETRY_COUNT))}
 | <b>timestamp_utc</b>: {_esc(rec.get(F_TIMESTAMP_UTC))}
 | <b>latency_ms</b>: {_esc(rec.get(F_LATENCY_MS))}
 | <b>error</b>: {_esc(rec.get(F_ERROR))}
 | <b>truncated</b>: {_esc(rec.get(F_TRUNCATED))}</p>
<div><b>human_labels</b><pre>{human_json}</pre></div>
<div><b>predicted labels</b><pre>{pred_json}</pre></div>
<div><b>raw_response</b><pre>{_esc(rec.get(F_RAW_RESPONSE))}</pre></div>
<div><b>parsed fields</b><pre>{parsed_json}</pre></div>
{trace_block}
</details>
"""
        body_rows.append(
            f'<tr class="trace-row" data-trace="{_esc(trace_id)}" '
            f'data-framework="{_esc(framework)}" '
            f'data-status="{_esc(status)}" '
            f'data-disagreements="{dis}">'
            f"<td>{_esc(trace_id)}{detail}</td>"
            f"<td>{_esc(framework)}</td>"
            f"<td>{_esc(status)}</td>"
            f"<td>{dis}</td>"
            f"{cells}</tr>"
        )

    sha12 = prompt_sha[:12] if prompt_sha else ""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<title>MAST result viewer {_esc(run_id)}</title>
<style>{_css()}</style>
</head>
<body>
<h1>MAST result viewer</h1>
<div class="meta">
<div><b>run_id</b><br/>{_esc(run_id)}</div>
<div><b>model_id</b><br/>{_esc(model_id)}</div>
<div><b>prompt</b><br/>{_esc(prompt_version)} {_esc(sha12)}</div>
<div><b>parser_version</b><br/>{_esc(parser_version)}</div>
<div><b>dataset_version</b><br/>{_esc(dataset_version)}</div>
<div><b>records</b><br/>{_esc(len(records))}</div>
<div><b>traces with disagreement</b><br/>{_esc(n_dis)}</div>
</div>
<h2>parse_status counts</h2>
<table><tr><th>status</th><th>count</th></tr>{status_rows}</table>
<h2>per-code FP / FN</h2>
<table><tr><th>code</th><th>FP</th><th>FN</th></tr>{code_rows}</table>
<div class="filters">
<label><input type="checkbox" id="f_dis"/> disagreements only</label>
<label><input type="checkbox" id="f_bad"/> parse problems only</label>
<label>framework
<select id="f_fw"><option value="">all</option>{fw_opts}</select></label>
<label>code FP/FN
<select id="f_code"><option value="">all</option>{code_opts}</select></label>
<label>trace_id <input type="search" id="f_q"/></label>
<span id="shown"></span>
</div>
<table class="grid">
<thead><tr>
<th>trace_id</th><th>framework</th><th>parse_status</th><th>dis</th>
{header_cells}
</tr></thead>
<tbody>
{"".join(body_rows)}
</tbody>
</table>
<script>{_js()}</script>
</body>
</html>
"""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Static MAST prediction result viewer"
    )
    parser.add_argument("--predictions", required=True, type=Path)
    parser.add_argument("--manifest", type=Path, default=None)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args(argv)
    records = load_records(args.predictions)
    manifest: dict[str, Any] | None = None
    if args.manifest is not None:
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    page = build_html(records, manifest)
    args.out.write_text(page, encoding="utf-8")
    print(f"wrote {args.out} ({len(records)} records)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
