"""
04_export_powerbi.py  (Google Analytics)
----------------------------------------
Pre-aggregates the tables Power BI loads for the GA funnel dashboard.

Run:  python src/04_export_powerbi.py  ->  powerbi/*.csv
"""

import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
PBI = ROOT / "powerbi"
PBI.mkdir(parents=True, exist_ok=True)

s = pd.read_csv(PROC / "sessions.csv")
p = pd.read_csv(PROC / "purchases.csv")
for c in ["reached_product_view", "reached_cart", "reached_checkout", "purchased"]:
    s[c] = s[c].astype(bool)

# 1. funnel stages (long)
funnel = pd.DataFrame({
    "stage": ["Sessions", "Product View", "Add to Cart", "Checkout", "Purchase"],
    "sessions": [len(s), int(s.reached_product_view.sum()), int(s.reached_cart.sum()),
                 int(s.reached_checkout.sum()), int(s.purchased.sum())]})
funnel["stage_order"] = range(len(funnel))
funnel.to_csv(PBI / "funnel_stage.csv", index=False)

# 2. by device
dev = (s.groupby("device").agg(
    sessions=("session_id", "count"), product_view=("reached_product_view", "sum"),
    cart=("reached_cart", "sum"), checkout=("reached_checkout", "sum"),
    purchase=("purchased", "sum"), revenue=("revenue", "sum")).reset_index())
dev.to_csv(PBI / "funnel_by_device.csv", index=False)

# 3. channel performance
ch = (s.groupby("channel").agg(
    sessions=("session_id", "count"), orders=("purchased", "sum"),
    revenue=("revenue", "sum")).reset_index())
ch["conversion_rate"] = ch.orders / ch.sessions
ch["revenue_per_session"] = ch.revenue / ch.sessions
ch.to_csv(PBI / "channel_performance.csv", index=False)

# 4. device x channel
mat = (s.groupby(["device", "channel"]).agg(
    sessions=("session_id", "count"), orders=("purchased", "sum")).reset_index())
mat["conversion_rate"] = mat.orders / mat.sessions
mat.to_csv(PBI / "device_channel_matrix.csv", index=False)

# 5. daily trend
daily = (s.assign(date=pd.to_datetime(s.date)).groupby("date").agg(
    sessions=("session_id", "count"), orders=("purchased", "sum"),
    revenue=("revenue", "sum")).reset_index())
daily["conversion_rate"] = daily.orders / daily.sessions
daily.to_csv(PBI / "daily_trend.csv", index=False)

# 6. category revenue
cat = (p.groupby("category").agg(
    orders=("session_id", "count"), revenue=("revenue", "sum")).reset_index())
cat["avg_item_value"] = cat.revenue / cat.orders
cat.sort_values("revenue", ascending=False).to_csv(PBI / "category_revenue.csv", index=False)

print("Exported Power BI tables:")
for f in sorted(PBI.glob("*.csv")):
    print(" -", f.name)
