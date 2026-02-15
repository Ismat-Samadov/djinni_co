"""
Djinni.co Job Market — Business Intelligence Charts
Generates all charts into the charts/ directory.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd

# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT      = Path(__file__).parent.parent
DATA_PATH = ROOT / "data" / "djinni.csv"
CHARTS    = ROOT / "charts"
CHARTS.mkdir(exist_ok=True)

# ── Style ─────────────────────────────────────────────────────────────────────
BRAND   = "#1a73e8"          # primary blue
ACCENT  = "#34a853"          # green
WARN    = "#ea4335"          # red
NEUTRAL = "#5f6368"          # grey
PALETTE = ["#1a73e8","#34a853","#fbbc04","#ea4335","#9c27b0",
           "#00bcd4","#ff7043","#8bc34a","#607d8b","#e91e63"]

plt.rcParams.update({
    "figure.dpi":         150,
    "savefig.dpi":        150,
    "font.family":        "DejaVu Sans",
    "font.size":          11,
    "axes.spines.top":    False,
    "axes.spines.right":  False,
    "axes.grid":          True,
    "grid.alpha":         0.3,
    "grid.linestyle":     "--",
    "axes.titlesize":     13,
    "axes.titleweight":   "bold",
    "axes.labelsize":     11,
})

def save(fig: plt.Figure, name: str) -> None:
    path = CHARTS / name
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    print(f"  ✓ {name}")

# ── Load data ─────────────────────────────────────────────────────────────────
print("Loading data…")
df = pd.read_csv(DATA_PATH)
df["date_posted"] = pd.to_datetime(df["date_posted"], errors="coerce")
df["hour"]        = df["date_posted"].dt.hour
df["exp_years"]   = (df["experience_months"] / 12).round(1)

# Salary rows only (both bounds present)
sal = df.dropna(subset=["salary_min", "salary_max"]).copy()
sal = sal[(sal["salary_min"] > 0) & (sal["salary_max"] > 0)]
sal = sal[sal["salary_max"] <= 30_000]   # drop obvious outliers
sal["salary_mid"] = (sal["salary_min"] + sal["salary_max"]) / 2

print(f"  Total jobs: {len(df):,}")
print(f"  Jobs with salary data: {len(sal):,}")

# ── 1. Top 25 Job Categories by Demand ────────────────────────────────────────
print("\nChart 1 – Top 25 Job Categories")
top_cats = df["category"].value_counts().head(25)

fig, ax = plt.subplots(figsize=(10, 9))
bars = ax.barh(top_cats.index[::-1], top_cats.values[::-1], color=BRAND, edgecolor="white")
for bar, val in zip(bars, top_cats.values[::-1]):
    ax.text(bar.get_width() + 8, bar.get_y() + bar.get_height() / 2,
            f"{val:,}", va="center", fontsize=9, color=NEUTRAL)
ax.set_xlabel("Number of Open Positions")
ax.set_title("Top 25 Most In-Demand Job Roles\n(Total Active Listings)")
ax.set_xlim(0, top_cats.values.max() * 1.15)
fig.tight_layout()
save(fig, "01_top_categories.png")

# ── 2. Full-Time vs Part-Time by Top 15 Categories (stacked bar) ──────────────
print("Chart 2 – Job Type by Category")
top15 = df["category"].value_counts().head(15).index
df_top = df[df["category"].isin(top15)]
jt = df_top.groupby(["category","job_type"]).size().unstack(fill_value=0)
jt = jt.reindex(columns=["FULL_TIME","PART_TIME"], fill_value=0)
jt = jt.loc[jt.sum(axis=1).sort_values(ascending=True).index]

fig, ax = plt.subplots(figsize=(10, 7))
jt["FULL_TIME"].plot(kind="barh", ax=ax, color=BRAND, label="Full-Time")
jt["PART_TIME"].plot(kind="barh", ax=ax, color=ACCENT, left=jt["FULL_TIME"], label="Part-Time")
ax.set_xlabel("Number of Positions")
ax.set_title("Full-Time vs Part-Time Roles\n(Top 15 Categories)")
ax.legend(frameon=False)
ax.set_xlim(0, jt.sum(axis=1).max() * 1.1)
fig.tight_layout()
save(fig, "02_job_type_by_category.png")

# ── 3. Salary Range by Top 15 Categories (grouped min/max bar) ────────────────
print("Chart 3 – Salary ranges by category")
sal_cat = (sal.groupby("category")
              .agg(avg_min=("salary_min","median"),
                   avg_max=("salary_max","median"),
                   avg_mid=("salary_mid","median"),
                   count=("salary_mid","count"))
              .query("count >= 5")
              .sort_values("avg_mid", ascending=True)
              .head(15))

fig, ax = plt.subplots(figsize=(10, 7))
y = np.arange(len(sal_cat))
h = 0.35
ax.barh(y + h/2, sal_cat["avg_max"], h, color=ACCENT,  label="Median Max Salary", alpha=0.85)
ax.barh(y - h/2, sal_cat["avg_min"], h, color=BRAND,   label="Median Min Salary", alpha=0.85)
ax.set_yticks(y)
ax.set_yticklabels(sal_cat.index)
ax.set_xlabel("USD / Month")
ax.set_title("Salary Range by Role\n(Median Min & Max, USD)")
ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:,.0f}"))
ax.legend(frameon=False)
fig.tight_layout()
save(fig, "03_salary_by_category.png")

# ── 4. Overall Salary Distribution (histogram as bar) ─────────────────────────
print("Chart 4 – Salary distribution")
bins   = [0, 500, 1000, 1500, 2000, 2500, 3000, 4000, 5000, 7500, 10000, 15000, 30001]
labels = ["<$500","$500-1k","$1k-1.5k","$1.5k-2k","$2k-2.5k","$2.5k-3k",
          "$3k-4k","$4k-5k","$5k-7.5k","$7.5k-10k","$10k-15k",">$15k"]
sal["bucket"] = pd.cut(sal["salary_mid"], bins=bins, labels=labels, right=False)
dist = sal["bucket"].value_counts().reindex(labels, fill_value=0)

fig, ax = plt.subplots(figsize=(11, 5))
bars = ax.bar(dist.index, dist.values, color=BRAND, edgecolor="white")
for bar, val in zip(bars, dist.values):
    if val > 0:
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                str(val), ha="center", fontsize=9, color=NEUTRAL)
ax.set_ylabel("Number of Jobs")
ax.set_xlabel("Monthly Salary Range (USD)")
ax.set_title("Salary Distribution Across All Advertised Roles\n(Monthly, USD)")
plt.xticks(rotation=35, ha="right")
fig.tight_layout()
save(fig, "04_salary_distribution.png")

# ── 5. Experience Required — Distribution ─────────────────────────────────────
print("Chart 5 – Experience distribution")
exp_bins   = [0, 12, 24, 36, 60, 84, 10000]
exp_labels = ["0-1 yr","1-2 yrs","2-3 yrs","3-5 yrs","5-7 yrs","7+ yrs"]
df["exp_bucket"] = pd.cut(df["experience_months"], bins=exp_bins,
                          labels=exp_labels, right=False)
exp_dist = df["exp_bucket"].value_counts().reindex(exp_labels, fill_value=0)

fig, ax = plt.subplots(figsize=(9, 5))
colors = [BRAND if i < 3 else WARN for i in range(len(exp_dist))]
bars = ax.bar(exp_dist.index, exp_dist.values, color=colors, edgecolor="white")
for bar, val in zip(bars, exp_dist.values):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 15,
            f"{val:,}", ha="center", fontsize=9.5, color=NEUTRAL)
ax.set_ylabel("Number of Positions")
ax.set_xlabel("Experience Required")
ax.set_title("How Much Experience Do Employers Require?\n(All Active Listings)")
ax.set_ylim(0, exp_dist.max() * 1.15)
fig.tight_layout()
save(fig, "05_experience_distribution.png")

# ── 6. Experience vs Salary ────────────────────────────────────────────────────
print("Chart 6 – Experience vs salary")
sal["exp_bucket"] = pd.cut(sal["experience_months"], bins=exp_bins,
                           labels=exp_labels, right=False)
exp_sal = (sal.groupby("exp_bucket", observed=True)["salary_mid"]
              .agg(["median","mean","count"])
              .reindex(exp_labels))
exp_sal = exp_sal.dropna(subset=["median"])

fig, ax = plt.subplots(figsize=(9, 5))
ax.bar(exp_sal.index, exp_sal["median"], color=BRAND, edgecolor="white", label="Median Salary")
ax.plot(exp_sal.index, exp_sal["mean"], "o--", color=WARN, label="Mean Salary", linewidth=2)
for i, (idx, row) in enumerate(exp_sal.iterrows()):
    ax.text(i, row["median"] + 40, f"${row['median']:,.0f}", ha="center", fontsize=9, color=NEUTRAL)
ax.set_ylabel("Monthly Salary (USD)")
ax.set_title("Salary vs Experience Required\n(Median & Mean, USD/month)")
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:,.0f}"))
ax.legend(frameon=False)
fig.tight_layout()
save(fig, "06_experience_vs_salary.png")

# ── 7. Top 20 Most Active Employers ───────────────────────────────────────────
print("Chart 7 – Top employers")
top_employers = df["company"].value_counts().head(20)

fig, ax = plt.subplots(figsize=(10, 8))
colors = [BRAND if i < 5 else NEUTRAL for i in range(len(top_employers))]
bars = ax.barh(top_employers.index[::-1], top_employers.values[::-1],
               color=colors[::-1], edgecolor="white")
for bar, val in zip(bars, top_employers.values[::-1]):
    ax.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height()/2,
            str(val), va="center", fontsize=9.5, color=NEUTRAL)
ax.set_xlabel("Number of Active Job Postings")
ax.set_title("Top 20 Most Active Hiring Companies\n(by Open Positions)")
ax.set_xlim(0, top_employers.values.max() * 1.15)
fig.tight_layout()
save(fig, "07_top_employers.png")

# ── 8. Posting Activity by Hour of Day ────────────────────────────────────────
print("Chart 8 – Hourly posting activity")
hourly = df.groupby("hour").size().reindex(range(24), fill_value=0)

fig, ax = plt.subplots(figsize=(11, 5))
peak_hour = hourly.idxmax()
bar_colors = [WARN if h == peak_hour else BRAND for h in range(24)]
ax.bar(hourly.index, hourly.values, color=bar_colors, edgecolor="white")
ax.set_xlabel("Hour of Day (24h)")
ax.set_ylabel("Jobs Posted")
ax.set_title("Job Posting Activity by Hour of Day\n(When Are Employers Most Active?)")
ax.set_xticks(range(24))
ax.set_xticklabels([f"{h:02d}:00" for h in range(24)], rotation=45, ha="right", fontsize=8)
ax.annotate(f"Peak: {peak_hour:02d}:00\n({hourly[peak_hour]:,} jobs)",
            xy=(peak_hour, hourly[peak_hour]),
            xytext=(peak_hour + 2, hourly[peak_hour] * 0.9),
            arrowprops=dict(arrowstyle="->", color=WARN),
            color=WARN, fontsize=9)
fig.tight_layout()
save(fig, "08_posting_by_hour.png")

# ── 9. Top 10 Highest-Paying Roles ────────────────────────────────────────────
print("Chart 9 – Highest paying roles")
sal_top = (sal.groupby("category")["salary_mid"]
              .agg(median="median", count="count")
              .query("count >= 5")
              .sort_values("median", ascending=False)
              .head(10))

fig, ax = plt.subplots(figsize=(10, 6))
bars = ax.barh(sal_top.index[::-1], sal_top["median"][::-1],
               color=[ACCENT if i < 3 else BRAND for i in range(len(sal_top))][::-1],
               edgecolor="white")
for bar, val in zip(bars, sal_top["median"][::-1]):
    ax.text(bar.get_width() + 30, bar.get_y() + bar.get_height()/2,
            f"${val:,.0f}", va="center", fontsize=9.5, color=NEUTRAL)
ax.set_xlabel("Median Monthly Salary (USD)")
ax.set_title("Top 10 Highest-Paying Job Categories\n(Median Monthly Salary, USD)")
ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:,.0f}"))
ax.set_xlim(0, sal_top["median"].max() * 1.2)
fig.tight_layout()
save(fig, "09_highest_paying_roles.png")

# ── 10. Demand vs Salary Quadrant (scatter-like bar) ──────────────────────────
print("Chart 10 – Demand vs salary matrix")
demand = df["category"].value_counts()
cat_sal = (sal.groupby("category")["salary_mid"].median()
              .rename("med_salary"))
matrix = pd.concat([demand.rename("demand"), cat_sal], axis=1).dropna()
matrix = matrix[matrix["demand"] >= 20]

med_demand = matrix["demand"].median()
med_salary = matrix["med_salary"].median()

fig, ax = plt.subplots(figsize=(11, 8))
for _, row in matrix.iterrows():
    q_color = (ACCENT  if row["demand"] >= med_demand and row["med_salary"] >= med_salary else
               BRAND   if row["demand"] >= med_demand else
               WARN    if row["med_salary"] >= med_salary else
               NEUTRAL)
    ax.scatter(row["demand"], row["med_salary"], s=120, color=q_color, alpha=0.8, zorder=3)
    ax.annotate(_.replace(" ", "\n"), (row["demand"], row["med_salary"]),
                textcoords="offset points", xytext=(4, 4), fontsize=7, color="#333")

ax.axvline(med_demand, color="gray", linestyle="--", alpha=0.5)
ax.axhline(med_salary, color="gray", linestyle="--", alpha=0.5)
ax.set_xlabel("Number of Open Positions (Demand)")
ax.set_ylabel("Median Monthly Salary (USD)")
ax.set_title("Role Demand vs Compensation\n(High Demand & High Pay = top-right quadrant)")
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:,.0f}"))

# Quadrant labels
ax.text(matrix["demand"].max()*0.95, med_salary*1.01,
        "High Pay", color="gray", fontsize=8, ha="right")
ax.text(med_demand*1.02, matrix["med_salary"].max()*0.98,
        "High Demand", color="gray", fontsize=8)

# Legend
from matplotlib.lines import Line2D
legend_elements = [
    Line2D([0],[0], marker='o', color='w', markerfacecolor=ACCENT,  markersize=9, label="High Demand & High Pay"),
    Line2D([0],[0], marker='o', color='w', markerfacecolor=BRAND,   markersize=9, label="High Demand & Lower Pay"),
    Line2D([0],[0], marker='o', color='w', markerfacecolor=WARN,    markersize=9, label="Lower Demand & High Pay"),
    Line2D([0],[0], marker='o', color='w', markerfacecolor=NEUTRAL, markersize=9, label="Lower Demand & Lower Pay"),
]
ax.legend(handles=legend_elements, frameon=False, fontsize=8, loc="lower right")
fig.tight_layout()
save(fig, "10_demand_vs_salary.png")

# ── Summary stats for README ───────────────────────────────────────────────────
print("\n── Summary for README ──")
print(f"Total listings:          {len(df):,}")
print(f"With salary data:        {len(sal):,} ({len(sal)/len(df)*100:.1f}%)")
print(f"Full-time jobs:          {(df['job_type']=='FULL_TIME').sum():,}")
print(f"Part-time jobs:          {(df['job_type']=='PART_TIME').sum():,}")
print(f"Top category:            {top_cats.index[0]} ({top_cats.iloc[0]:,})")
print(f"Avg salary (mid):        ${sal['salary_mid'].mean():,.0f}")
print(f"Median salary (mid):     ${sal['salary_mid'].median():,.0f}")
print(f"Highest paying cat:      {sal_top.index[0]} (${sal_top['median'].iloc[0]:,.0f}/mo)")
print(f"Most active employer:    {top_employers.index[0]} ({top_employers.iloc[0]} jobs)")
print(f"Peak posting hour:       {peak_hour:02d}:00")
print(f"Most common exp req:     {exp_dist.idxmax()} ({exp_dist.max():,} jobs)")

print("\nAll charts saved to charts/")
