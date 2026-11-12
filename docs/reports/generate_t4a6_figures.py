"""Workbook 2 figures generated from repo data. 6.5 in wide, 200 dpi, no tight bbox."""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

R = Path(sys.argv[1])
OUT = Path(sys.argv[2])
OUT.mkdir(parents=True, exist_ok=True)
NAVY, BLUE, LIGHT, AMBER, GREY, GREEN = "#1F4E79", "#2E75B6", "#9DC3E6", "#C9952B", "#7F7F7F", "#3B7D4F"
FILL = {BLUE: "#E8F0F9", AMBER: "#FDF0D5", GREY: "#F0F0F0", GREEN: "#E6F2E9", NAVY: "#DCE6F2"}
plt.rcParams.update({"font.family": "serif", "font.serif": ["Times New Roman", "Times", "DejaVu Serif"],
                     "font.size": 9, "axes.spines.top": False, "axes.spines.right": False})
W = 6.5


def save(fig, name):
    fig.savefig(OUT / name, dpi=200)
    plt.close(fig)


def canvas(h, xmax=100, ymax=None):
    fig = plt.figure(figsize=(W, h))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, xmax)
    ax.set_ylim(0, ymax if ymax else xmax * h / W)
    ax.axis("off")
    return fig, ax


def box(ax, x, y, w, h, text, c=BLUE, fs=8, bold=False):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=1.0",
                                fc=FILL[c], ec=c, lw=1.1))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs,
            fontweight="bold" if bold else "normal", linespacing=1.25)


def arrow(ax, a, b, c=GREY, style="-|>", ls="-"):
    ax.add_patch(FancyArrowPatch(a, b, arrowstyle=style, mutation_scale=9, lw=1.1, color=c, ls=ls,
                                 shrinkA=0, shrinkB=0))


def row(ax, y, h, labels, c, x0=11, gap=2.2, right=99, fs=7.6):
    n = len(labels)
    w = (right - x0 - gap * (n - 1)) / n
    for i, t in enumerate(labels):
        x = x0 + i * (w + gap)
        box(ax, x, y, w, h, t, c, fs)
        if i:
            arrow(ax, (x - gap, y + h / 2), (x, y + h / 2), c if c == AMBER else GREY)


# ---------------------------------------------------------------- Fig 3 data process
fig, ax = canvas(3.75)
ymax = ax.get_ylim()[1]
heads = ["3.2 Collect", "3.3 Pre-process", "3.4 Transform", "3.5 Prepare", "Consumer"]
x0, gap, right = 11, 2.2, 99
w = (right - x0 - gap * 4) / 5
for i, t in enumerate(heads):
    ax.text(x0 + i * (w + gap) + w / 2, ymax - 2.6, t, ha="center", va="center", fontsize=8.5,
            fontweight="bold", color=NAVY)
rows = [
    ("MAST-Data\n(baseline)", BLUE,
     ["HF mcemri/MAD\npinned 95118ac\n1,642 traces, SHA-256", "labels 0/1/null only\nunique record key\n4 all-null excluded",
      "flatten 14 codes\ncategory roll-ups\n1,638 x 26 table", "eval_manifest v1.0.0\nfrozen, evaluation only\nno training split", "MAST judge\nreproduction"]),
    ("QMSum\n(Model 1)", BLUE,
     ["Yale-LILY release\n232 meetings\n1,810 query pairs", "speaker: text turns\nempty-field checks\n0 rows removed",
      "CatchupExample rows\nthen m1-input-v1\nordered events", "m1_v1 train/val/test\n1,257 / 272 / 281\nSHA-256 manifest", "Model 1\nsupervision"]),
    ("Product\nsessions", AMBER,
     ["event log from the\nsession service\n(planned)", "pseudonymise,\nschema-validate\n(planned)", "double annotation,\ncritical facts\n(planned)",
      "m1_session_v1\nsplit by session_id\n(planned)", "Candidate selection,\nModels 2 to 4"]),
]
h = 8.6
for k, (name, c, labels) in enumerate(rows):
    y = ymax - 15.5 - k * 12.4
    ax.text(5.2, y + h / 2, name, ha="center", va="center", fontsize=8.5, fontweight="bold",
            color=NAVY if c == BLUE else "#8A6414")
    row(ax, y, h, labels, c, fs=6.9)
yw = ymax - 15.5 - 3 * 12.4 + 2.2
box(ax, x0, yw, right - x0, 5.4,
    "Sink for every built stage: local DuckDB warehouse (raw, staging, marts) with quality gates and run history per pipeline run",
    GREEN, 7.6)
ax.text(1, 1.2, "Blue: built and on main. Amber: planned for the product-session corpus. Green: warehouse sink used in the pipeline demo.",
        fontsize=7, color=GREY)
save(fig, "fig03_data_process.png")

# ---------------------------------------------------------------- MAST frames
df = pd.read_csv(R / "data/mast/processed/mast_clean_summary.csv")
fc = [c for c in df.columns if c.startswith("fail_")]
codes = [c[5:].replace("_", ".") for c in fc]
NAMES = {"1.1": "Disobey task specification", "1.2": "Disobey role specification", "1.3": "Step repetition",
         "1.4": "Loss of conversation history", "1.5": "Unaware of termination conditions",
         "2.1": "Conversation reset", "2.2": "Fail to ask for clarification", "2.3": "Task derailment",
         "2.4": "Information withholding", "2.5": "Ignored other agent's input",
         "2.6": "Action-reasoning mismatch", "3.1": "Premature termination", "3.2": "Weak verification",
         "3.3": "No or incorrect verification"}
CAT = {"1": ("Specification", NAVY), "2": ("Inter-agent misalignment", BLUE), "3": ("Task verification", LIGHT)}

# Fig 6: prevalence / imbalance
fig, ax = plt.subplots(figsize=(W, 3.5))
fig.subplots_adjust(left=0.36, right=0.93, top=0.9, bottom=0.14)
pos = df[fc].sum().values
y = np.arange(len(codes))[::-1]
ax.barh(y, pos / len(df) * 100, color=[CAT[c[0]][1] for c in codes], height=0.72)
for yi, p in zip(y, pos):
    ax.text(p / len(df) * 100 + 0.6, yi, f"{p:,}  ({p / len(df) * 100:.1f}%)", va="center", fontsize=7.5)
ax.set_yticks(y)
ax.set_yticklabels([f"{c}  {NAMES[c]}" for c in codes], fontsize=8)
ax.set_xlabel("Share of the 1,638 scorable traces labelled positive (%)")
ax.set_xlim(0, 52)
ax.legend(handles=[plt.Rectangle((0, 0), 1, 1, color=c) for _, c in CAT.values()],
          labels=[n for n, _ in CAT.values()], frameon=False, fontsize=7.5, loc="lower right")
ax.set_title("Label imbalance across the 14 MAST failure modes", fontsize=10)
save(fig, "fig06_mast_prevalence.png")

# Fig 7: failures per trace + by framework
fig, (a, b) = plt.subplots(1, 2, figsize=(W, 2.7))
fig.subplots_adjust(left=0.08, right=0.98, top=0.88, bottom=0.2, wspace=0.42)
vc = df.n_failures.value_counts().sort_index()
a.bar(vc.index, vc.values, color=[GREY if i == 0 else BLUE for i in vc.index])
a.set_xlabel("Failure modes positive on one trace")
a.set_ylabel("Traces")
a.set_title("Failures per trace", fontsize=10)
a.text(0.55, vc.max() * 0.93, f"{vc[0]} traces (24.5%)\nwith no failure", fontsize=7.5, color=GREY, va="top")
a.set_xticks(range(0, 15, 2))
g = df.groupby("mas_name").agg(n=("n_failures", "size"), m=("n_failures", "mean")).sort_values("m")
b.barh(g.index, g.m, color=BLUE, height=0.7)
for i, (m, n) in enumerate(zip(g.m, g.n)):
    b.text(m + 0.08, i, f"{m:.2f}  (n={n})", va="center", fontsize=7.5)
b.set_xlim(0, 8.2)
b.set_xlabel("Mean failure modes per trace")
b.set_title("By multi-agent framework", fontsize=10)
save(fig, "fig07_mast_failures_per_trace.png")

# Fig 8: correlation heatmap
fig = plt.figure(figsize=(W, 5.7))
ax = fig.add_axes([0.07, 0.05, 0.8, 0.9])
cor = df[fc].corr().values
im = ax.imshow(cor, cmap="Blues", vmin=0, vmax=1)
ax.set_xticks(range(14))
ax.set_yticks(range(14))
ax.set_xticklabels(codes, fontsize=8)
ax.set_yticklabels(codes, fontsize=8)
for i in range(14):
    for j in range(14):
        ax.text(j, i, f"{cor[i, j]:.2f}"[1:] if i != j else "1", ha="center", va="center", fontsize=6.3,
                color="white" if cor[i, j] > 0.55 else "#222222")
for k in (4.5, 10.5):
    ax.axhline(k, color="white", lw=2.5)
    ax.axvline(k, color="white", lw=2.5)
for s in ax.spines.values():
    s.set_visible(False)
ax.tick_params(length=0)
cb = fig.colorbar(im, cax=fig.add_axes([0.89, 0.12, 0.022, 0.76]))
cb.set_label("Pearson (phi) correlation between binary labels", fontsize=8)
ax.set_title("Co-occurrence of MAST failure modes (1,638 scorable traces)", fontsize=10)
save(fig, "fig08_mast_correlation.png")

# ---------------------------------------------------------------- Fig 11 platform architecture
fig, ax = canvas(4.85)
ymax = ax.get_ylim()[1]


def band(y, h, title):
    ax.add_patch(FancyBboxPatch((1, y), 98, h, boxstyle="round,pad=0,rounding_size=1.2", fc="#FAFBFD", ec="#C8D3E0", lw=0.8))
    ax.text(2.5, y + h - 1.9, title, fontsize=8.2, fontweight="bold", color=NAVY, va="center")


band(ymax - 17.5, 16.5, "Session plane (Docker Compose, local)")
band(ymax - 35.5, 16.5, "Execution and serving plane")
band(ymax - 54, 17, "Data and model development plane")
band(ymax - 71.5, 15, "Engineering controls")
y1 = ymax - 15.5
box(ax, 4, y1, 20, 9.5, "client/\nReact 18, Vite, TipTap\nYjs presence and cursors", fs=7.4)
box(ax, 28, y1, 20, 9.5, "crdt-server/\ny-websocket\nshared Yjs document", fs=7.4)
box(ax, 52, y1, 21, 9.5, "session-service/\nFastAPI, SQLAlchemy\nroles, ordered event log", fs=7.4)
box(ax, 77, y1, 19, 9.5, "PostgreSQL 16 event log\nRedis 7 fan-out\nJaeger traces", GREY, fs=7.4)
arrow(ax, (24, y1 + 4.75), (28, y1 + 4.75), style="<|-|>")
arrow(ax, (48, y1 + 4.75), (52, y1 + 4.75))
arrow(ax, (73, y1 + 4.75), (77, y1 + 4.75), style="<|-|>")
y2 = ymax - 33.5
box(ax, 4, y2, 27, 9.5, "agent-runtime/\nLangGraph plan, act, observe loop\nfive fixed tools", fs=7.4)
box(ax, 37, y2, 27, 9.5, "serving/\nPOST /v1/models/{id}/predict\nadapters m1 to m4 (stubs today)", fs=7.4)
box(ax, 70, y2, 26, 9.5, "locked bake-off winners\nloaded as adapters\n(after selection)", AMBER, fs=7.4)
arrow(ax, (31, y2 + 4.75), (37, y2 + 4.75))
arrow(ax, (70, y2 + 4.75), (64, y2 + 4.75), AMBER)
arrow(ax, (62, y1), (17.5, y2 + 9.5), style="<|-|>")
arrow(ax, (62.5, y1), (50.5, y2 + 9.5))
y3 = ymax - 52
box(ax, 4, y3, 20, 10, "data/\npinned downloads\nfrozen splits + manifests", fs=7.4)
box(ax, 27.5, y3, 21, 10, "models/\nPyTorch, Transformers, PEFT\n4-bit NF4 QLoRA trainers", fs=7.4)
box(ax, 52, y3, 20, 10, "GPU workstation\nRTX 5080 Laptop, 16 GB\nadapter checkpoints", GREY, fs=7.4)
box(ax, 75.5, y3, 20.5, 10, "eval/\ncontracts, metrics\nseeds 13, 29, 47", fs=7.4)
arrow(ax, (24, y3 + 5), (27.5, y3 + 5))
arrow(ax, (48.5, y3 + 5), (52, y3 + 5), style="<|-|>")
arrow(ax, (72, y3 + 5), (75.5, y3 + 5))
arrow(ax, (83, y3 + 10), (83, y2), AMBER)
y4 = ymax - 69.8
for i, t in enumerate(["GitHub Actions CI\nruff, mypy, pytest", "ADRs 001 to 005\nfrozen contracts", "Pinned requirements\nand lock file",
                       "Run manifests\ngit SHA, seed, hashes", "Linear issues\none owner each"]):
    box(ax, 4 + i * 18.6, y4, 17, 8, t, GREY, fs=7.2)
ax.text(1, 0.9, "Blue: on main. Grey: infrastructure. Amber: arrives when a bake-off winner is locked.", fontsize=7, color=GREY)
save(fig, "fig11_platform_architecture.png")

# ---------------------------------------------------------------- Fig 12 ML data flow
fig, ax = canvas(2.55)
ymax = ax.get_ylim()[1]
labs = ["Frozen split\n+ SHA-256\nmanifest", "Candidate\nconfig YAML\n(repo, revision,\nseed)", "Train on GPU\nadapter-only\ncheckpoints\nevery 200 steps",
        "Inference:\nm1-output-v1\nJSON, parsed\nand validated", "Shared harness\nmetrics per\nseed", "compare:\ngates, ranking,\ntie-breaks", "Blinded review,\nwinner to\nserving adapter"]
cols = [BLUE, BLUE, BLUE, BLUE, BLUE, BLUE, AMBER]
n = len(labs)
x0, gap, right = 1.5, 1.9, 98.5
w = (right - x0 - gap * (n - 1)) / n
yb = ymax - 20
for i, (t, c) in enumerate(zip(labs, cols)):
    x = x0 + i * (w + gap)
    box(ax, x, yb, w, 13, t, c, 7)
    if i:
        arrow(ax, (x - gap, yb + 6.5), (x, yb + 6.5))
box(ax, x0, yb - 11.5, right - x0, 6.5,
    "Every result JSON records: contract version, config hash, dataset manifest hashes, git SHA, model revision, seed, hardware, package versions, latency, peak VRAM",
    GREY, 7.2)
for i in (2, 3, 4):
    xm = x0 + i * (w + gap) + w / 2
    arrow(ax, (xm, yb), (xm, yb - 5), GREY, ls=(0, (3, 2)))
ax.text(x0, ymax - 3.4, "Machine-learning data flow for one bake-off candidate (identical for all four candidates of a task)",
        fontsize=8.5, fontweight="bold", color=NAVY)
ax.text(1, 0.8, "Validation data tunes prompts, thresholds and early stopping; the test split is read once, for the final frozen comparison.",
        fontsize=7, color=GREY)
save(fig, "fig12_ml_data_flow.png")

# ---------------------------------------------------------------- Fig 13 selection rule
fig, ax = canvas(2.2)
ymax = ax.get_ylim()[1]
labs = ["Four candidates\nm1-a to m1-d\nthree seeds each", "All three seed\nruns complete?", "Safety gates on\nevery seed:\nschema, unsupported\nclaims, attribution,\nstatus",
        "Rank by 3-seed mean:\ncritical-fact recall,\nthen BERTScore-F1,\nthen ROUGE-L\n(1-point margins)", "Tie-break:\nlatency p95,\nthen peak VRAM", "Blinded human\nreview of\nthe top two"]
cols = [BLUE, AMBER, AMBER, BLUE, BLUE, BLUE]
n = len(labs)
w = (right - x0 - gap * (n - 1)) / n
yb = ymax - 21.5
for i, (t, c) in enumerate(zip(labs, cols)):
    x = x0 + i * (w + gap)
    box(ax, x, yb, w, 15, t, c, 7)
    if i:
        arrow(ax, (x - gap, yb + 7.5), (x, yb + 7.5))
ax.text(x0, ymax - 3.2, "Model 1 candidate-selection rule (ADR-005)", fontsize=8.5, fontweight="bold", color=NAVY)
ax.text(50, yb - 4, "Amber steps are eligibility gates: a candidate failing any gate on any seed cannot win. If no candidate passes, no winner is promoted.",
        fontsize=7.2, color=GREY, ha="center")
ax.text(50, yb - 7.6, "ROUGE alone can never select a winner.", fontsize=7.2, color=GREY, ha="center")
save(fig, "fig13_selection_rule.png")
print("ok", sorted(p.name for p in OUT.glob("fig*.png")))
