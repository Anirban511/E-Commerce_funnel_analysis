"""
02_clean_transform.py  (Google Analytics)
-----------------------------------------
Cleans the GA session + hits tables and reshapes them into one analysis-ready
row per session, with a boolean flag for each funnel stage derived from
hits.eCommerceAction.action_type (2=view, 3=cart, 5=checkout, 6=purchase).

Key GA-specific cleaning:
  * totals_transactionRevenue is stored in MICROS -> divide by 1e6 to get USD.
  * NULL revenue on non-purchase sessions is expected (set to 0).
  * date is YYYYMMDD string -> parse to date.

Run:  python src/02_clean_transform.py
"""

import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROC = ROOT / "data" / "processed"
PROC.mkdir(parents=True, exist_ok=True)

ACTION = {2: "product_view", 3: "add_to_cart", 5: "checkout", 6: "purchase"}

def main():
    sessions = pd.read_csv(RAW / "sessions.csv")
    hits = pd.read_csv(RAW / "hits.csv")
    products = pd.read_csv(RAW / "products.csv")

    print("=== DATA QUALITY ===")
    print(f"sessions: {len(sessions):,}  hits: {len(hits):,}")
    print(f"duplicate session_id: {sessions.duplicated('session_id').sum()}")
    print(f"sessions with no hits (bounced/landing only): "
          f"{(~sessions['session_id'].isin(hits['session_id'])).sum():,}")

    # revenue micros -> USD
    sessions["revenue"] = sessions["totals_transactionRevenue"].fillna(0) / 1_000_000
    sessions["date"] = pd.to_datetime(sessions["date"].astype(str), format="%Y%m%d")

    # funnel flags from action_type
    reached = (hits.assign(stage=hits["eCommerceAction_action_type"].map(ACTION))
                   .dropna(subset=["stage"])
                   .groupby("session_id")["stage"].agg(set))
    def flag(stage):
        return sessions["session_id"].map(lambda s: stage in reached.get(s, set()))
    sessions["reached_product_view"] = flag("product_view")
    sessions["reached_cart"] = flag("add_to_cart")
    sessions["reached_checkout"] = flag("checkout")
    sessions["purchased"] = sessions["totals_transactions"].fillna(0).astype(int).gt(0)

    # tidy session table for analysis / Power BI
    cols = ["session_id", "fullVisitorId", "date", "channelGrouping",
            "deviceCategory", "country", "totals_pageviews",
            "reached_product_view", "reached_cart", "reached_checkout",
            "purchased", "revenue"]
    sess = sessions[cols].rename(columns={
        "channelGrouping": "channel", "deviceCategory": "device",
        "totals_pageviews": "pageviews"})

    # purchase-line table (for category revenue)
    purchases = (hits[hits["eCommerceAction_action_type"] == 6]
                 .merge(sessions[["session_id", "channelGrouping", "deviceCategory", "date"]],
                        on="session_id", how="left")
                 .rename(columns={"v2ProductCategory": "category",
                                  "channelGrouping": "channel",
                                  "deviceCategory": "device"}))
    purchases["revenue"] = purchases["productPrice"]
    purchases = purchases[["session_id", "date", "productSKU", "category",
                           "channel", "device", "revenue"]]

    # events_clean (long) for the SQL version
    events = hits.assign(stage=hits["eCommerceAction_action_type"].map(ACTION)).dropna(subset=["stage"])
    events = events.merge(sessions[["session_id", "channelGrouping", "deviceCategory", "date"]],
                          on="session_id", how="left")
    events = events.rename(columns={"channelGrouping": "channel", "deviceCategory": "device",
                                    "stage": "event_type", "productPrice": "revenue_line"})
    events["event_date"] = pd.to_datetime(events["date"]).dt.date
    events = events[["session_id", "hitNumber", "event_type",
                     "eCommerceAction_action_type", "productSKU",
                     "v2ProductCategory", "channel", "device", "event_date"]]

    sess.to_csv(PROC / "sessions.csv", index=False)
    purchases.to_csv(PROC / "purchases.csv", index=False)
    events.to_csv(PROC / "events_clean.csv", index=False)

    print("\n=== PROCESSED OUTPUTS ===")
    print(f"sessions.csv     : {len(sess):,} rows")
    print(f"purchases.csv    : {len(purchases):,} rows")
    print(f"events_clean.csv : {len(events):,} rows")
    print(f"overall conversion: {sess['purchased'].mean():.3%}")
    print(f"total revenue: ${sess['revenue'].sum():,.0f}")

if __name__ == "__main__":
    main()
