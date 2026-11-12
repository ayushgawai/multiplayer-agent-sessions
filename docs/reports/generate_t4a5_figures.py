"""Generate the Workbook 2 (T4.A5) figures for report sections 3 and 4.

Every figure is 6.5 inches wide, which is the text column of the report page
(US Letter at one inch margins), so Word does not scale them down and clip
their labels.

Counts are not hard-coded where the repository can supply them: the split
figure reads data/splits/m1_v1/MANIFEST.json, and the corpus figure reads the
tables in data/mast/DATA_DICTIONARY.md, which the download script generates.

Usage:
    python docs/reports/generate_t4a5_figures.py --out docs/reports/figures/

Linear: DAT-62 (Workbook 2). Owner: Shriram Dundigalla.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
WIDTH_IN = 6.5
DPI = 200

INK = "#1F4D78"
ACCENT = "#2E74B5"
MUTED = "#8a8a8a"
FILL = "#eaf1f8"
WARN = "#fdf0d5"

plt.rcParams.update(
    {
        "font.family": "serif",
        "font.serif": ["Times New Roman", "DejaVu Serif"],
        "font.size": 9,
        "axes.titlesize": 10,
        "axes.labelsize": 9,
    }
)


# ---------------------------------------------------------------- data access


def mast_counts() -> dict[str, list[tuple[str, int]]]:
    """Framework, model and benchmark counts from the generated data dictionary."""
    path = REPO_ROOT / "data" / "mast" / "DATA_DICTIONARY.md"
    text = path.read_text(encoding="utf-8")
    out: dict[str, list[tuple[str, int]]] = {}
    for field in ("mas_name", "llm_name", "benchmark_name"):
        section = text.split(f"### `{field}`", 1)[1].split("###", 1)[0]
        rows = re.findall(r"^\|\s*`?([A-Za-z0-9 _.\-]+?)`?\s*\|\s*(\d+)\s*\|$", section, re.M)
        out[field] = [(k.strip(), int(v)) for k, v in rows]
    return out


def split_counts() -> dict[str, int]:
    manifest = json.loads(
        (REPO_ROOT / "data" / "splits" / "m1_v1" / "MANIFEST.json").read_text(encoding="utf-8")
    )
    return {name: info["count"] for name, info in manifest["splits"].items()}


def split_records(split: str) -> list[dict[str, Any]]:
    path = REPO_ROOT / "data" / "splits" / "m1_v1" / f"{split}.jsonl"
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle]


# ------------------------------------------------------------------- helpers


def box(ax: Any, x: float, y: float, w: float, h: float, label: str, *,
        face: str = FILL, edge: str = ACCENT, size: int = 8) -> tuple[float, float]:
    ax.add_patch(
        FancyBboxPatch(
            (x, y), w, h, boxstyle="round,pad=0.012,rounding_size=0.02",
            linewidth=0.9, edgecolor=edge, facecolor=face,
        )
    )
    ax.text(x + w / 2, y + h / 2, label, ha="center", va="center", fontsize=size, color="#111")
    return x + w, y + h / 2


def arrow(ax: Any, start: tuple[float, float], end: tuple[float, float],
          *, style: str = "-|>", color: str = MUTED, dashed: bool = False) -> None:
    ax.add_patch(
        FancyArrowPatch(
            start, end, arrowstyle=style, mutation_scale=9, linewidth=0.9,
            color=color, linestyle="--" if dashed else "-",
            shrinkA=2, shrinkB=2,
        )
    )


def blank_axes(fig_h: float) -> tuple[Any, Any]:
    fig, ax = plt.subplots(figsize=(WIDTH_IN, fig_h))
    fig.subplots_adjust(left=0, right=1, bottom=0, top=1)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    return fig, ax


def save(fig: Any, out_dir: Path, name: str) -> None:
    """Save at exactly WIDTH_IN inches wide.

    Deliberately no bbox_inches="tight": trimming changes the pixel width while
    leaving the DPI tag at DPI, and Word sizes an image from its DPI tag rather
    than from the width we ask for in the HTML. Every figure then lands at a
    different, smaller width on the page.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / name
    fig.savefig(path, dpi=DPI, facecolor="white")
    plt.close(fig)
    print(f"  wrote {path.relative_to(REPO_ROOT)}")


# ------------------------------------------------------------------- figure 3


def figure_3_lineage(out_dir: Path) -> None:
    """Three data paths, from pinned source through freeze to consumer."""
    fig, ax = blank_axes(3.7)
    rows = [
        (0.80, "MAST release\npinned at 95118ac9",
         "eval_manifest.json\nfrozen v1.0.0",
         "judge prompt,\nparser, run_batch",
         "predictions.jsonl\nper ADR-003", "Baseline\nreproduction", FILL),
        (0.50, "QMSum release\nchecksummed",
         "make_splits.py\nseed 13",
         "data/splits/\nm1_v1 + SHA-256",
         "m1-input-v1\nm1-output-v1", "Model 1\nsupervision", FILL),
        (0.20, "Product sessions\nnot yet recorded",
         "annotation\nnot yet built",
         "data/splits/\nm1_session_v1",
         "session_test\nsplit", "Candidate\nselection", WARN),
    ]
    w, h = 0.178, 0.15
    xs = [0.005, 0.203, 0.401, 0.599, 0.797]
    for y, a, b, c, d, e, face in rows:
        prev = None
        edge = "#c9961f" if face == WARN else ACCENT
        for x, label in zip(xs, (a, b, c, d, e)):
            right, mid = box(ax, x, y - h / 2, w, h, label, face=face, edge=edge, size=6.8)
            if prev is not None:
                arrow(ax, prev, (x, mid), color="#c9961f" if face == WARN else MUTED)
            prev = (right, mid)
    for y, name in ((0.80, "Baseline path"), (0.50, "M1 supervision path"),
                    (0.20, "Candidate-selection path")):
        ax.text(0.005, y + h / 2 + 0.035, name, fontsize=8.5, style="italic", color=INK)
    ax.text(0.005, 0.015, "Amber: planned, not yet built. The three paths never mix; "
                          "each is pinned and frozen separately.",
            fontsize=7.5, color=MUTED)
    save(fig, out_dir, "fig3_data_lineage.png")


# ------------------------------------------------------------------- figure 5


def figure_5_mast_composition(out_dir: Path) -> None:
    """Class imbalance across the three descriptive axes of the MAST corpus."""
    counts = mast_counts()
    titles = {
        "mas_name": "Multi-agent framework",
        "llm_name": "Underlying language model",
        "benchmark_name": "Benchmark",
    }
    fig, axes = plt.subplots(1, 3, figsize=(WIDTH_IN, 2.5))
    for ax, (field, rows) in zip(axes, counts.items()):
        rows = sorted(rows, key=lambda r: r[1])
        labels = [r[0] for r in rows]
        values = [r[1] for r in rows]
        bars = ax.barh(labels, values, color=ACCENT, height=0.7)
        bars[-1].set_color(INK)
        ax.set_title(titles[field])
        ax.tick_params(axis="y", labelsize=7)
        ax.tick_params(axis="x", labelsize=7)
        ax.set_xlim(0, max(values) * 1.28)
        for bar, v in zip(bars, values):
            ax.text(v + max(values) * 0.03, bar.get_y() + bar.get_height() / 2,
                    str(v), va="center", fontsize=6.5, color="#333")
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
    axes[0].set_xlabel("Traces (of 1,642)")
    fig.tight_layout()
    save(fig, out_dir, "fig5_mast_composition.png")


# ------------------------------------------------------------------- figure 4


def figure_4_splits(out_dir: Path) -> None:
    """Prepared M1 splits: query pairs and the meetings they come from."""
    pairs = split_counts()
    meetings = {"train": 162, "val": 35, "test": 35}
    order = ["train", "val", "test"]
    names = {"train": "Train", "val": "Validation", "test": "Test"}
    total_pairs = sum(pairs.values())

    fig, axes = plt.subplots(1, 2, figsize=(WIDTH_IN, 2.3))

    left = 0.0
    for key, colour in zip(order, (INK, ACCENT, "#9dc3e6")):
        share = pairs[key] / total_pairs * 100
        axes[0].barh([0], [share], left=[left], color=colour, height=0.45,
                     label=f"{names[key]}  {pairs[key]:,} ({share:.1f}%)")
        axes[0].text(left + share / 2, 0, f"{share:.1f}%", ha="center", va="center",
                     fontsize=7.5, color="white")
        left += share
    axes[0].set_xlim(0, 100)
    axes[0].set_ylim(-0.6, 0.6)
    axes[0].set_yticks([])
    axes[0].set_xlabel("Share of the 1,810 query-summary pairs (%)", labelpad=2)
    axes[0].set_title("Prepared split proportions")
    axes[0].legend(loc="upper center", bbox_to_anchor=(0.5, -0.30), ncol=3,
                   frameon=False, fontsize=7, columnspacing=1.0, handlelength=1.2)
    for side in ("top", "right", "left"):
        axes[0].spines[side].set_visible(False)

    x = range(len(order))
    axes[1].bar([i - 0.2 for i in x], [meetings[k] for k in order], width=0.4,
                color=INK, label="Meetings")
    axes[1].bar([i + 0.2 for i in x], [pairs[k] for k in order], width=0.4,
                color=ACCENT, label="Query pairs")
    axes[1].set_yscale("log")
    axes[1].set_xticks(list(x))
    axes[1].set_xticklabels([names[k] for k in order], fontsize=8)
    axes[1].set_ylabel("Count (log scale)")
    axes[1].set_ylim(10, 20000)
    axes[1].set_title("Meetings and pairs per split")
    axes[1].legend(frameon=False, fontsize=7, loc="upper right", ncol=2,
                   columnspacing=1.0, handlelength=1.2)
    for i, k in enumerate(order):
        axes[1].text(i - 0.2, meetings[k] * 1.12, str(meetings[k]), ha="center", fontsize=6.5)
        axes[1].text(i + 0.2, pairs[k] * 1.12, f"{pairs[k]:,}", ha="center", fontsize=6.5)
    for side in ("top", "right"):
        axes[1].spines[side].set_visible(False)

    fig.tight_layout()
    save(fig, out_dir, "fig4_m1_splits.png")


# ------------------------------------------------------------------- figure 7


def figure_7_architecture(out_dir: Path) -> None:
    """Platform components and the machine-learning data flow between them."""
    fig, ax = blank_axes(4.0)

    ax.text(0.5, 0.965, "Session plane", ha="center", fontsize=8.5, style="italic", color=INK)
    _, c_mid = box(ax, 0.04, 0.84, 0.26, 0.10, "client/\nReact, TipTap, Yjs")
    _, r_mid = box(ax, 0.37, 0.84, 0.26, 0.10, "crdt-server/\ny-websocket")
    _, s_mid = box(ax, 0.70, 0.84, 0.26, 0.10, "session-service/\nordered event log")
    arrow(ax, (0.30, c_mid), (0.37, r_mid))
    arrow(ax, (0.63, r_mid), (0.70, s_mid))

    ax.text(0.5, 0.775, "Execution plane", ha="center", fontsize=8.5, style="italic", color=INK)
    _, a_mid = box(ax, 0.04, 0.63, 0.26, 0.10, "agent-runtime/\nLangGraph loop")
    _, v_mid = box(ax, 0.37, 0.63, 0.26, 0.10, "serving/\nPOST .../predict")
    _, m_mid = box(ax, 0.70, 0.63, 0.26, 0.10, "memory/\napproved lessons")
    arrow(ax, (0.30, a_mid), (0.37, v_mid))
    arrow(ax, (0.63, v_mid), (0.70, m_mid))
    arrow(ax, (0.83, 0.84), (0.83, 0.73), style="<|-|>")
    arrow(ax, (0.17, 0.84), (0.17, 0.73), style="<|-|>")

    ax.text(0.5, 0.565, "Model and evaluation plane", ha="center", fontsize=8.5,
            style="italic", color=INK)
    for i, (label, face) in enumerate([
        ("M1 catch-up\n298A", FILL), ("M2 attribution\n298B", WARN),
        ("M3 arbitration\n298B", WARN), ("M4 routing\n298B", WARN),
    ]):
        edge = "#c9961f" if face == WARN else ACCENT
        box(ax, 0.04 + i * 0.245, 0.42, 0.21, 0.09, label, face=face, edge=edge, size=7.5)

    box(ax, 0.02, 0.24, 0.28, 0.09, "data/\npinned corpora, frozen splits",
        face="#f2f2f2", edge=MUTED, size=7.5)
    box(ax, 0.345, 0.24, 0.31, 0.09, "eval/ harness\nseeds 13, 29, 47", size=8)
    box(ax, 0.70, 0.24, 0.28, 0.09, "eval/compare.py\nfrozen safety gates", size=8)
    arrow(ax, (0.30, 0.285), (0.345, 0.285))
    arrow(ax, (0.655, 0.285), (0.70, 0.285))
    for i in range(4):
        arrow(ax, (0.145 + i * 0.245, 0.42), (0.38 + i * 0.08, 0.33))

    box(ax, 0.345, 0.07, 0.31, 0.09, "models/baseline_mast/\nreproduced baseline",
        face="#f2f2f2", edge=MUTED, size=7.5)
    arrow(ax, (0.50, 0.16), (0.50, 0.24))
    ax.text(0.02, 0.01, "Amber: 298B. The baseline is scored by the same harness as the four "
                        "models and is never one of them.", fontsize=7.5, color=MUTED)
    save(fig, out_dir, "fig7_architecture.png")


# ------------------------------------------------------------------- figure 8


def figure_8_selection(out_dir: Path) -> None:
    """How a Model 1 winner is selected: gates first, then ranking, then humans."""
    fig, ax = blank_axes(1.75)
    w, h = 0.148, 0.46
    steps = [
        "Four candidates\nm1-a to m1-d",
        "All three seeds\ncomplete?",
        "Safety gates:\nschema, claims,\nattribution, status",
        "Rank: recall,\nBERTScore, ROUGE\ntie margin 0.01",
        "Tie-break on\nlatency, VRAM",
        "Blinded human\nreview of top two",
    ]
    prev = None
    for i, label in enumerate(steps):
        x = 0.008 + i * 0.167
        face = WARN if i in (1, 2) else FILL
        edge = "#c9961f" if face == WARN else ACCENT
        right, mid = box(ax, x, 0.44, w, h, label, face=face, edge=edge, size=6.6)
        if prev is not None:
            arrow(ax, prev, (x, mid))
        prev = (right, mid)
    ax.text(0.5, 0.26, "A candidate failing a gate cannot win regardless of quality; if none "
                       "passes every gate, no winner is selected.",
            ha="center", fontsize=7.2, color=MUTED)
    ax.text(0.5, 0.10, "The machine-ranked leader is provisional until the blinded review.",
            ha="center", fontsize=7.2, color=MUTED)
    save(fig, out_dir, "fig8_selection_rule.png")


def figure_6_qmsum_distributions(out_dir: Path) -> None:
    """What a Model 1 training example actually looks like, measured, not asserted."""
    splits = {name: split_records(name) for name in ("train", "val", "test")}
    colours = {"train": INK, "val": ACCENT, "test": "#9dc3e6"}
    names = {"train": "Train", "val": "Validation", "test": "Test"}

    fig, axes = plt.subplots(1, 3, figsize=(WIDTH_IN, 2.1))

    for key, records in splits.items():
        lengths = [len(r["reference_summary"].split()) for r in records]
        axes[0].hist(lengths, bins=range(0, 260, 10), histtype="step", linewidth=1.1,
                     color=colours[key], label=names[key], density=True)
    axes[0].set_xlabel("Reference summary length (words)")
    axes[0].set_ylabel("Density")
    axes[0].set_title("Summary length")
    axes[0].legend(frameon=False, fontsize=7)

    for key, records in splits.items():
        spans = [len(r.get("context_spans") or []) for r in records]
        axes[1].hist(spans, bins=range(0, 120, 5), histtype="step", linewidth=1.1,
                     color=colours[key], label=names[key], density=True)
    axes[1].set_xlabel("Context spans per example")
    axes[1].set_title("Evidence available")

    queries = [len(r["query"].split()) for key in splits for r in splits[key]]
    axes[2].hist(queries, bins=range(0, 40, 2), color=ACCENT)
    axes[2].set_xlabel("Query length (words)")
    axes[2].set_title("Query length, all splits")

    for ax in axes:
        ax.tick_params(labelsize=7)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
    fig.tight_layout()
    save(fig, out_dir, "fig6_qmsum_distributions.png")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=REPO_ROOT / "docs" / "reports" / "figures")
    args = parser.parse_args()
    print(f"Generating Workbook 2 figures into {args.out}")
    figure_3_lineage(args.out)
    figure_4_splits(args.out)
    figure_5_mast_composition(args.out)
    figure_6_qmsum_distributions(args.out)
    figure_7_architecture(args.out)
    figure_8_selection(args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
