#!/usr/bin/env python3
"""
Reproduce main-text Figure 1 and Figure 2 of

    Yin, Anh, Forster & Rust. Tracking claim changes from preprint to
    publication across 72,644 biomedical studies using large language models.

Figure 1 (headline patterns): content change, hedging shift, hedging by content
stratum, content change by field, strengthened-to-weakened ratio by field, and
claim-type transitions.

Figure 2 (drivers): primary-vs-secondary co-change, revision by claim type,
revision over time, revision by review duration, revision by journal impact, and
retraction rate.

Inputs (in ./data):
    full_corpus_labels.csv   one row per preprint-publication pair, with the
                             content-change, hedging, and claim-type labels.
    journal_metrics.json     journal -> OpenAlex 2-year mean citedness.

Outputs (in ./figures):
    Figure1_headline.pdf / .png
    Figure2_drivers.pdf  / .png
    figure_stats.txt         the printed values behind each panel.

Figures are vector PDFs with embedded fonts (pdf.fonttype = 42), editable in
Illustrator. Run: python3 make_figures.py
"""
import json
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.path import Path as MplPath
import matplotlib.patches as mpatches
import matplotlib.lines as mlines

matplotlib.rcParams.update({
    "pdf.fonttype": 42, "ps.fonttype": 42, "svg.fonttype": "none",
    "font.family": "sans-serif", "font.sans-serif": ["DejaVu Sans", "Arial", "Helvetica"],
    "font.size": 8, "axes.linewidth": 0.8})

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
FIGDIR = HERE / "figures"
FIGDIR.mkdir(exist_ok=True)

df = pd.read_csv(DATA / "full_corpus_labels.csv", low_memory=False)
df["days"] = pd.to_numeric(df.days_to_publication, errors="coerce")
journal_metrics = json.load(open(DATA / "journal_metrics.json"))
impact = {k: v.get("2yr_mean_citedness") for k, v in journal_metrics.items()}
df["IF"] = df.published_journal.astype(str).str.lower().str.strip().map(impact)

N = len(df)

# colour palette
GREEN = "#3F8F5B"; AMBER = "#E3A93C"; RED = "#C9434F"; BLUE = "#3C6E9A"; GREY = "#C2C7CE"
CMAJ = {"unchanged": GREEN, "minor": AMBER, "major": RED}
TYPES = ["mechanism", "association", "descriptive", "method", "therapeutic", "null_result"]
TPAL = dict(zip(TYPES, ["#3C6E9A", "#3F8F5B", "#E3A93C", "#9A6FB0", "#C9434F", "#6FB0A8"]))
order = ["unchanged", "minor", "major"]

stats_log = []
def log(*a):
    line = " ".join(str(x) for x in a)
    stats_log.append(line)
    print(line)

def panel(ax, letter, dx=-0.16, dy=1.10):
    ax.text(dx, dy, letter, transform=ax.transAxes, fontsize=12, fontweight="bold",
            va="top", ha="left")

# fields used in the by-field panels (>= 1,500 pairs)
field_size = df.preprint_category.value_counts()
fields = [c for c in field_size.index if field_size[c] >= 1500]

def clean_field(name):
    return name.replace(" biology", "").replace(" and cognition", "")

# claim-type transition flows, for the alluvial panel
def claim_type_flows():
    changed = df[(df.preprint_primary_type != df.published_primary_type)
                 & df.preprint_primary_type.isin(TYPES) & df.published_primary_type.isin(TYPES)]
    flows = {}
    for s in TYPES:
        sub = changed[changed.preprint_primary_type == s]
        if len(sub) == 0:
            continue
        flows[s] = {d: int((sub.published_primary_type == d).sum())
                    for d in TYPES if (sub.published_primary_type == d).sum() > 0}
    return flows

def alluvial(ax, flows, label_fs=4.9):
    srcs = list(flows)
    ltot = {s: sum(flows[s].values()) for s in srcs}
    rtot = {}
    for s in srcs:
        for t, v in flows[s].items():
            rtot[t] = rtot.get(t, 0) + v
    lo = sorted(srcs, key=lambda s: -ltot[s])
    ro = sorted(rtot, key=lambda t: -rtot[t])
    tot = sum(ltot.values()); gap = 0.04 * tot
    H = max(tot + gap * (len(lo) - 1), tot + gap * (len(ro) - 1))
    xL0, xL1, xR0, xR1 = 0.10, 0.15, 0.85, 0.90
    def lay(o, tt):
        y = H; p = {}
        for k in o:
            p[k] = (y, y - tt[k]); y = y - tt[k] - gap
        return p
    Lp = lay(lo, ltot); Rp = lay(ro, rtot)
    Lo = {k: Lp[k][0] for k in lo}; Ro = {k: Rp[k][0] for k in ro}
    for k in lo:
        yt, yb = Lp[k]
        ax.add_patch(mpatches.Rectangle((xL0, yb), xL1 - xL0, yt - yb, color=TPAL[k], ec="none"))
        ax.text(xL0 - 0.02, (yt + yb) / 2, f"{k.replace('_', ' ')} {ltot[k]:,}",
                ha="right", va="center", fontsize=label_fs)
    for k in ro:
        yt, yb = Rp[k]
        ax.add_patch(mpatches.Rectangle((xR0, yb), xR1 - xR0, yt - yb, color="#5A5A5A", ec="none"))
        ax.text(xR1 + 0.02, (yt + yb) / 2, f"{k.replace('_', ' ')} {rtot[k]:,}",
                ha="left", va="center", fontsize=label_fs)
    for s in lo:
        for t in ro:
            v = flows[s].get(t, 0)
            if not v:
                continue
            a = Lo[s]; b = a - v; Lo[s] = b
            c = Ro[t]; d2 = c - v; Ro[t] = d2
            cx = (xL1 + xR0) / 2
            verts = [(xL1, a), (cx, a), (cx, c), (xR0, c), (xR0, d2), (cx, d2), (cx, b), (xL1, b), (xL1, a)]
            codes = [MplPath.MOVETO, MplPath.CURVE4, MplPath.CURVE4, MplPath.CURVE4,
                     MplPath.LINETO, MplPath.CURVE4, MplPath.CURVE4, MplPath.CURVE4, MplPath.CLOSEPOLY]
            ax.add_patch(mpatches.PathPatch(MplPath(verts, codes), facecolor=TPAL[s], ec="none", alpha=0.42))
    ax.set_xlim(-0.30, 1.30); ax.set_ylim(-gap, H + gap * 0.5); ax.invert_yaxis(); ax.axis("off")
    ax.text(0.10, -0.03, "Preprint", transform=ax.transAxes, ha="left", va="top",
            fontsize=6.5, color=BLUE, fontweight="bold")
    ax.text(0.90, -0.03, "Published", transform=ax.transAxes, ha="right", va="top",
            fontsize=6.5, color="#5A5A5A", fontweight="bold")

# ============================================================ FIGURE 1
f1 = plt.figure(figsize=(11, 7.2))
gs = f1.add_gridspec(2, 3, hspace=0.55, wspace=0.42, left=0.07, right=0.97, top=0.90, bottom=0.09)

# a  content change
ax = f1.add_subplot(gs[0, 0])
vc = df.primary_label.value_counts()
vals = [vc[o] for o in order]; pct = [v / sum(vals) * 100 for v in vals]
ax.pie(vals, colors=[CMAJ[o] for o in order], startangle=90, counterclock=False,
       wedgeprops=dict(width=0.42, edgecolor="white", linewidth=1.4))
ax.text(0, 0, f"n = {N:,}", ha="center", va="center", fontsize=8.5, fontweight="bold")
ax.legend([f"{o.capitalize()}  {p:.1f}%" for o, p in zip(order, pct)], loc="center",
          bbox_to_anchor=(0.5, -0.16), frameon=False, fontsize=8, handlelength=1)
ax.set_title("Content change", fontsize=9.5, fontweight="bold"); panel(ax, "a", dx=-0.05)
log("[1a] content change:", dict(zip(order, [round(p, 1) for p in pct])))

# b  hedging shift
ax = f1.add_subplot(gs[0, 1])
ho = ["unchanged", "weakened", "strengthened"]
hv = [(df.primary_hedging == h).sum() for h in ho]; na = df.primary_hedging.isna().sum()
ax.pie(hv + [na], colors=[GREY, BLUE, RED, "#EEE"], startangle=90, counterclock=False,
       wedgeprops=dict(width=0.42, edgecolor="white", linewidth=1.4))
ratio = hv[1] / hv[2]
ax.text(0, 0, f"{ratio:.1f} : 1\ncautious:confident", ha="center", va="center", fontsize=8, fontweight="bold")
ax.legend([f"{l}  {v / N * 100:.1f}%" for l, v in zip(["No shift", "More cautious", "More confident"], hv)],
          loc="center", bbox_to_anchor=(0.5, -0.16), frameon=False, fontsize=8, handlelength=1)
ax.set_title("Hedging shift", fontsize=9.5, fontweight="bold"); panel(ax, "b", dx=-0.05)
log("[1b] hedging: more_cautious=%.1f%% more_confident=%.1f%% ratio=%.2f" % (hv[1] / N * 100, hv[2] / N * 100, ratio))

# c  hedging within content stratum (rescaled to assessed = 100%)
ax = f1.add_subplot(gs[0, 2])
log("[1c] hedging composition within stratum (assessed = 100%):")
for i, strat in enumerate(order):
    sub = df[df.primary_label == strat]
    n_assessed = sub.primary_hedging.notna().sum()
    bottom = 0; comp = {}
    for h, c in zip(["unchanged", "weakened", "strengthened"], [GREY, BLUE, RED]):
        v = (sub.primary_hedging == h).sum() / n_assessed * 100
        ax.bar(i, v, bottom=bottom, color=c, width=0.7, edgecolor="white", linewidth=0.5)
        bottom += v; comp[h] = round(v, 1)
    log("   ", strat, comp)
ax.set_xticks(range(3)); ax.set_xticklabels([o.capitalize() for o in order], fontsize=8)
ax.set_ylabel("% within stratum (assessed)", fontsize=8.5); ax.set_ylim(0, 100)
ax.spines[["top", "right"]].set_visible(False)
ax.legend(["No shift", "More cautious", "More confident"], fontsize=7, loc="lower center",
          bbox_to_anchor=(0.5, -0.30), ncol=1, frameon=False)
ax.set_title("Hedging by content stratum", fontsize=9.5, fontweight="bold"); panel(ax, "c")

# d  content-change composition by field, ordered by major rate
ax = f1.add_subplot(gs[1, 0])
rows = []
for c in fields:
    s = df[df.preprint_category == c]
    rows.append((c, (s.primary_label == "major").mean() * 100,
                 (s.primary_label == "minor").mean() * 100,
                 (s.primary_label == "unchanged").mean() * 100))
rows.sort(key=lambda r: r[1])
names = [r[0] for r in rows]
maj = [r[1] for r in rows]; mino = [r[2] for r in rows]; unc = [r[3] for r in rows]
y = range(len(rows))
ax.barh(y, unc, color=GREEN, height=0.8, label="Unchanged")
ax.barh(y, mino, left=unc, color=AMBER, height=0.8, label="Minor")
ax.barh(y, maj, left=[u + m for u, m in zip(unc, mino)], color=RED, height=0.8, label="Major")
ax.set_yticks(list(y)); ax.set_yticklabels([clean_field(n) for n in names], fontsize=6.8)
ax.set_xlabel("% of pairs", fontsize=8.5); ax.set_xlim(0, 100)
ax.spines[["top", "right"]].set_visible(False)
ax.set_title("Content change by field", fontsize=9.5, fontweight="bold"); panel(ax, "d", dx=-0.42)
log("[1d] major%% by field: min=%s(%.1f) max=%s(%.1f)" % (names[0], maj[0], names[-1], maj[-1]))

# e  strengthened-to-weakened ratio by field
ax = f1.add_subplot(gs[1, 1])
rows2 = []
for c in fields:
    s = df[df.preprint_category == c]
    st = (s.primary_hedging == "strengthened").mean(); wk = (s.primary_hedging == "weakened").mean()
    rows2.append((c, st / wk if wk > 0 else np.nan))
rows2.sort(key=lambda r: r[1])
ax.barh(range(len(rows2)), [r[1] for r in rows2], color=BLUE, height=0.78)
ax.axvline(1, ls="--", color=RED, lw=1)
ax.set_yticks(range(len(rows2))); ax.set_yticklabels([clean_field(r[0]) for r in rows2], fontsize=6.8)
ax.set_xlabel("strengthened / weakened", fontsize=8.5); ax.spines[["top", "right"]].set_visible(False)
ax.set_title("Hedging asymmetry by field", fontsize=9.5, fontweight="bold"); panel(ax, "e", dx=-0.42)
log("[1e] all fields strengthened/weakened < 1 (toward caution):", all((r[1] < 1) for r in rows2 if r[1] == r[1]))

# f  claim-type transitions (alluvial)
ax = f1.add_subplot(gs[1, 2])
flows = claim_type_flows()
n_changed = int(((df.preprint_primary_type != df.published_primary_type)
                 & df.preprint_primary_type.isin(TYPES)
                 & df.published_primary_type.isin(TYPES)).sum())
pct_ch = n_changed / N * 100
alluvial(ax, flows)
ax.set_title("Claim-type transitions", fontsize=9.5, fontweight="bold")
panel(ax, "f", dx=-0.06)
log("[1f] claim-type change: %.1f%% changed type, %.1f%% preserved" % (pct_ch, 100 - pct_ch))

f1.suptitle("Figure 1  |  Headline patterns of preprint-to-publication change   (n = 72,644)",
            x=0.02, ha="left", fontsize=12, fontweight="bold")
f1.savefig(FIGDIR / "Figure1_headline.pdf"); f1.savefig(FIGDIR / "Figure1_headline.png", dpi=300)
plt.close(f1)

# ============================================================ FIGURE 2
f2 = plt.figure(figsize=(11, 7.2))
gs = f2.add_gridspec(2, 3, hspace=0.55, wspace=0.42, left=0.07, right=0.97, top=0.90, bottom=0.10)

# a  primary vs secondary co-change
ax = f2.add_subplot(gs[0, 0])
ct = pd.crosstab(df.primary_label, df.s1_label, normalize="index").reindex(index=order, columns=order) * 100
ax.imshow(ct.values, cmap="YlOrRd", aspect="auto", vmin=0, vmax=70)
for i in range(3):
    for j in range(3):
        ax.text(j, i, f"{ct.values[i, j]:.0f}%", ha="center", va="center", fontsize=8.5,
                color="white" if ct.values[i, j] > 40 else "black", fontweight="bold")
ax.set_xticks(range(3)); ax.set_xticklabels([o.capitalize() for o in order], fontsize=7.5)
ax.set_yticks(range(3)); ax.set_yticklabels([o.capitalize() for o in order], fontsize=7.5)
ax.set_xlabel("Secondary claim", fontsize=8.5); ax.set_ylabel("Primary claim", fontsize=8.5)
ax.set_title("Primary vs secondary co-change", fontsize=9.5, fontweight="bold"); panel(ax, "a", dx=-0.32)

# b  revision by claim type: primary vs pooled secondaries
ax = f2.add_subplot(gs[0, 1])
TLAB = {"mechanism": "mechanism", "association": "association", "descriptive": "descriptive",
        "method": "method", "therapeutic": "therapeutic", "null_result": "null result"}
trows = []
for t in TYPES:
    sub = df[df.preprint_primary_type == t]
    if len(sub) < 200:
        continue
    p = (sub.primary_label == "major").mean() * 100
    sec = pd.concat([sub.s1_label, sub.s2_label])
    se = (sec == "major").mean() * 100
    trows.append((t, p, se, len(sub)))
trows.sort(key=lambda r: r[1])
ty = list(range(len(trows)))
for yi, (t, p, se, n) in zip(ty, trows):
    ax.plot([p, se], [yi, yi], "-", color="#C2C7CE", lw=2.2, zorder=1)
    ax.plot(p, yi, "o", color=BLUE, ms=6.5, zorder=3)
    ax.plot(se, yi, "o", color=RED, ms=6.5, zorder=3)
    ax.text(p - 0.5, yi, f"{p:.0f}", ha="right", va="center", fontsize=6, color=BLUE)
    ax.text(se + 0.5, yi, f"{se:.0f}", ha="left", va="center", fontsize=6, color=RED)
ax.set_yticks(ty); ax.set_yticklabels([TLAB[r[0]] for r in trows], fontsize=7)
ax.set_xlabel("% substantially revised (major)", fontsize=8); ax.set_xlim(0, 18)
ax.set_ylim(-0.6, len(trows) - 0.4); ax.spines[["top", "right"]].set_visible(False)
hp = mlines.Line2D([], [], color=BLUE, marker="o", ls="", ms=6, label="Primary claim")
hs = mlines.Line2D([], [], color=RED, marker="o", ls="", ms=6, label="Secondary claims")
ax.legend(handles=[hp, hs], fontsize=6.5, loc="lower center", bbox_to_anchor=(0.5, -0.34),
          ncol=2, frameon=False, handletextpad=0.3, columnspacing=1.0)
ax.set_title("Revision by claim type", fontsize=9.5, fontweight="bold"); panel(ax, "b", dx=-0.42)
log("[2b] primary vs secondary major%% by type:", {r[0]: (round(r[1], 1), round(r[2], 1)) for r in trows})

# c  revision over time
ax = f2.add_subplot(gs[0, 2])
yrs = list(range(2018, 2025))
for lab, c in [("unchanged", GREEN), ("minor", AMBER), ("major", RED)]:
    ys = [(df[df.year == y].primary_label == lab).mean() * 100 for y in yrs]
    ax.plot(yrs, ys, "-o", color=c, lw=1.8, ms=4, label=lab.capitalize())
ax.set_xlabel("Preprint year", fontsize=8.5); ax.set_ylabel("% of pairs", fontsize=8.5)
ax.spines[["top", "right"]].set_visible(False); ax.legend(fontsize=7, frameon=False)
ax.set_title("Revision over time", fontsize=9.5, fontweight="bold"); panel(ax, "c")
log("[2c] major%% 2019=%.1f 2024=%.1f" % ((df[df.year == 2019].primary_label == "major").mean() * 100,
                                          (df[df.year == 2024].primary_label == "major").mean() * 100))

# d  revision by review duration
ax = f2.add_subplot(gs[1, 0])
df["tert"] = pd.qcut(df.days, 3, labels=["fast", "medium", "slow"])
meds = df.groupby("tert", observed=True).days.median()
for i, t in enumerate(["fast", "medium", "slow"]):
    s = df[df.tert == t]; bottom = 0
    for lab, c in [("unchanged", GREEN), ("minor", AMBER), ("major", RED)]:
        v = (s.primary_label == lab).mean() * 100
        ax.bar(i, v, bottom=bottom, color=c, width=0.7, edgecolor="white", linewidth=0.5); bottom += v
    ax.text(i, 2, f"{(s.primary_label == 'major').mean() * 100:.0f}%", ha="center", color="white",
            fontsize=8, fontweight="bold")
ax.set_xticks(range(3)); ax.set_xticklabels([f"{t}\n({int(meds[t])}d)" for t in ["fast", "medium", "slow"]], fontsize=8)
ax.set_ylabel("% of pairs", fontsize=8.5); ax.set_ylim(0, 100); ax.spines[["top", "right"]].set_visible(False)
ax.set_title("Review duration drives revision", fontsize=9.5, fontweight="bold"); panel(ax, "d")
log("[2d] major%% fast=%.1f slow=%.1f" % ((df[df.tert == 'fast'].primary_label == 'major').mean() * 100,
                                          (df[df.tert == 'slow'].primary_label == 'major').mean() * 100))

# e  revision rises with journal impact
ax = f2.add_subplot(gs[1, 1])
mif = df.dropna(subset=["IF"]); mif = mif[mif.IF > 0].copy()
mif["rev"] = (mif.primary_label != "unchanged")
mif["ifb"] = pd.qcut(np.log10(mif.IF), 8, duplicates="drop")
g = mif.groupby("ifb", observed=True).agg(x=("IF", "mean"), y=("rev", "mean"), n=("rev", "size"))
g["y"] *= 100
X = np.log10(g.x.values); w = g.n.values
b1, b0 = np.polyfit(X, g.y.values, 1, w=w); yh = b0 + b1 * X
r2 = 1 - np.sum(w * (g.y.values - yh) ** 2) / np.sum(w * (g.y.values - np.average(g.y.values, weights=w)) ** 2)
ax.scatter(g.x, g.y, s=g.n / g.n.max() * 330 + 25, color=BLUE, alpha=0.6, edgecolor="white", linewidth=0.6, zorder=3)
xs = np.linspace(X.min(), X.max(), 50); ax.plot(10 ** xs, b0 + b1 * xs, "--", color=RED, lw=1.3, zorder=2)
ax.set_xscale("log"); ax.set_xlabel("Journal impact (2-yr mean citedness, log)", fontsize=8.5)
ax.set_ylabel("% revised (minor + major)", fontsize=8.5); ax.spines[["top", "right"]].set_visible(False)
ax.text(0.04, 0.96, f"slope {b1:.0f}%/log10(IF)\nR$^2$ = {r2:.2f}   n = {len(mif):,}", transform=ax.transAxes,
        va="top", fontsize=7.3, bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#999"))
ax.set_title("Revision rises with journal impact", fontsize=9.5, fontweight="bold"); panel(ax, "e")
log("[2e] journal-impact slope=%.0f%%/log10IF R2=%.2f n=%d" % (b1, r2, len(mif)))

# f  retraction rate (values from the retraction analysis; see Methods)
ax = f2.add_subplot(gs[1, 2])
ax.bar([0], [8.1], color=GREEN, width=0.6); ax.bar([1], [18.7], color=RED, width=0.6)
ax.errorbar([0], [8.1], yerr=[[8.1 - 4.3], [15.4 - 8.1]], fmt="none", ecolor="#2B2B2B", capsize=4, lw=1.1)
ax.errorbar([1], [18.7], yerr=[[18.7 - 17.4], [20.0 - 18.7]], fmt="none", ecolor="#2B2B2B", capsize=4, lw=1.1)
ax.text(0, 9.2, "8.1", ha="center", fontsize=8.5, fontweight="bold")
ax.text(1, 19.9, "18.7", ha="center", fontsize=8.5, fontweight="bold")
ax.set_xticks([0, 1]); ax.set_xticklabels(["Preprint\n(9 / 11,114)", "No preprint\n(813 / 435,159)"], fontsize=7.6)
ax.set_ylabel("Retractions / 10,000 papers", fontsize=8.3); ax.set_ylim(0, 25)
ax.spines[["top", "right"]].set_visible(False)
ax.text(0.96, 0.96, "RR 2.31\n(1.20-4.45)\np = 0.003", transform=ax.transAxes, ha="right", va="top",
        fontsize=7.3, bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#999"))
ax.set_title("Retraction rate", fontsize=9.5, fontweight="bold"); panel(ax, "f")

f2.suptitle("Figure 2  |  Drivers of preprint-to-publication revision   (n = 72,644)",
            x=0.02, ha="left", fontsize=12, fontweight="bold")
f2.savefig(FIGDIR / "Figure2_drivers.pdf"); f2.savefig(FIGDIR / "Figure2_drivers.png", dpi=300)
plt.close(f2)

(FIGDIR / "figure_stats.txt").write_text("\n".join(stats_log) + "\n")
print("\nWrote Figure1_headline and Figure2_drivers to", FIGDIR)
