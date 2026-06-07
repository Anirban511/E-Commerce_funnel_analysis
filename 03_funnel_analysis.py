"""
03_funnel_analysis.py  (Google Analytics)
-----------------------------------------
Core EDA on the GA Merchandise Store funnel: builds the conversion funnel,
segments by device and channel, tests the mobile-conversion gap for
significance, and quantifies the revenue opportunity. Saves charts and a
machine-readable findings.json used by the written report.

Run:  python src/03_funnel_analysis.py
"""

import json
import numpy as np
import pandas as pd
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
REP = ROOT / "reports"
REP.mkdir(parents=True, exist_ok=True)

STAGES = ["Sessions", "Product View", "Add to Cart", "Checkout", "Purchase"]
FLAGS = ["reached_product_view", "reached_cart", "reached_checkout", "purchased"]

def funnel_frame(df):
    counts = [len(df)] + [int(df[f].sum()) for f in FLAGS]
    overall = [c / counts[0] for c in counts]
    step = [np.nan] + [counts[i] / counts[i-1] if counts[i-1] else np.nan
                       for i in range(1, len(counts))]
    return pd.DataFrame({"stage": STAGES, "count": counts,
                         "pct_of_sessions": overall, "step_conv": step})

def main():
    s = pd.read_csv(PROC / "sessions.csv")
    f = {}

    overall = funnel_frame(s)
    print("=== OVERALL FUNNEL ===")
    print(overall.to_string(index=False))
    f["overall_funnel"] = overall.to_dict(orient="records")
    f["overall_conversion"] = float(s["purchased"].mean())
    f["total_sessions"] = int(len(s))
    f["total_orders"] = int(s["purchased"].sum())
    f["total_revenue"] = float(s["revenue"].sum())

    step = overall.dropna(subset=["step_conv"])
    worst = step.loc[step["step_conv"].idxmin()]
    f["biggest_leak_stage"] = worst["stage"]
    f["biggest_leak_step_conv"] = float(worst["step_conv"])

    # by device
    dev_rows = []
    for dev, g in s.groupby("device"):
        ff = funnel_frame(g)
        dev_rows.append({"device": dev, "sessions": len(g),
                         "view_to_cart": ff.loc[2, "step_conv"],
                         "cart_to_checkout": ff.loc[3, "step_conv"],
                         "checkout_to_purchase": ff.loc[4, "step_conv"],
                         "overall_conv": g["purchased"].mean()})
    dev_df = pd.DataFrame(dev_rows).sort_values("overall_conv", ascending=False)
    print("\n=== BY DEVICE ===\n", dev_df.to_string(index=False))
    f["by_device"] = dev_df.to_dict(orient="records")

    # by channel
    ch = (s.groupby("channel")
            .agg(sessions=("session_id", "count"),
                 conv=("purchased", "mean"),
                 revenue=("revenue", "sum"))
            .reset_index().sort_values("conv", ascending=False))
    ch["rev_per_session"] = ch["revenue"] / ch["sessions"]
    print("\n=== BY CHANNEL ===\n", ch.to_string(index=False))
    f["by_channel"] = ch.to_dict(orient="records")

    # significance: desktop vs mobile overall conversion (two-proportion z-test)
    d = s[s["device"] == "desktop"]; m = s[s["device"] == "mobile"]
    d_succ, d_n = int(d["purchased"].sum()), len(d)
    m_succ, m_n = int(m["purchased"].sum()), len(m)
    p_pool = (d_succ + m_succ) / (d_n + m_n)
    se = np.sqrt(p_pool * (1 - p_pool) * (1/d_n + 1/m_n))
    z = (d_succ/d_n - m_succ/m_n) / se
    p_value = 2 * (1 - stats.norm.cdf(abs(z)))
    print(f"\n=== DESKTOP vs MOBILE conversion ===")
    print(f"Desktop {d_succ/d_n:.3%}  Mobile {m_succ/m_n:.3%}  z={z:.1f}  p={p_value:.2e}")
    f["desktop_vs_mobile"] = {"desktop_rate": d_succ/d_n, "mobile_rate": m_succ/m_n,
                              "z": float(z), "p_value": float(p_value)}

    # revenue opportunity: lift mobile conversion halfway to desktop
    aov = s.loc[s["purchased"], "revenue"].mean()
    target = m_succ/m_n + 0.5 * (d_succ/d_n - m_succ/m_n)   # close half the gap (realistic)
    extra_orders = (target - m_succ/m_n) * m_n
    extra_rev_period = extra_orders * aov
    extra_rev_annual = extra_rev_period * (12 / 3)          # data covers ~3 months
    f.update({"aov": float(aov),
              "recovery_extra_orders_period": float(extra_orders),
              "recovery_extra_revenue_period": float(extra_rev_period),
              "recovery_extra_revenue_annualized": float(extra_rev_annual)})
    print(f"AOV ${aov:,.2f} | close half the mobile gap -> +{extra_orders:,.0f} orders / "
          f"${extra_rev_period:,.0f} ({extra_rev_annual:,.0f}/yr)")

    # ---- charts ----
    colors = ["#4C72B0", "#5B84C4", "#6FA0D8", "#E1812C", "#C44E52"]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    counts = overall["count"].tolist()
    ax.barh(range(len(STAGES))[::-1], counts, color=colors)
    ax.set_yticks(range(len(STAGES))[::-1]); ax.set_yticklabels(STAGES)
    for i, (c, p) in enumerate(zip(counts, overall["pct_of_sessions"])):
        ax.text(c + max(counts)*0.01, len(STAGES)-1-i, f"{c:,} ({p:.1%})", va="center", fontsize=9)
    ax.set_title("GA Merchandise Store — Conversion Funnel (all sessions)")
    ax.set_xlabel("Sessions reaching stage"); plt.tight_layout()
    fig.savefig(REP / "funnel_overall.png", dpi=130)

    fig2, ax2 = plt.subplots(figsize=(7.5, 4.5))
    order = dev_df.sort_values("overall_conv", ascending=False)
    ax2.bar(order["device"], order["overall_conv"]*100,
            color=["#4C72B0" if d!="mobile" else "#C44E52" for d in order["device"]])
    for i, v in enumerate(order["overall_conv"]):
        ax2.text(i, v*100, f"{v:.2%}", ha="center", va="bottom", fontsize=10)
    ax2.set_ylabel("Conversion rate (%)")
    ax2.set_title("Conversion by device — mobile is the leak")
    plt.tight_layout(); fig2.savefig(REP / "conversion_by_device.png", dpi=130)

    with open(REP / "findings.json", "w") as fp:
        json.dump(f, fp, indent=2, default=str)
    print("\nSaved findings.json + charts")

if __name__ == "__main__":
    main()
