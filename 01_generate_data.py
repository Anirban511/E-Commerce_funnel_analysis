"""
01_generate_data.py  (Google Analytics — Merchandise Store)
-----------------------------------------------------------
Generates a SCHEMA-FAITHFUL stand-in for the public Google Analytics Sample
dataset (bigquery-public-data.google_analytics_sample.ga_sessions_*), the
Google Merchandise Store. It mirrors the real export's field names and the
e-commerce funnel encoded in hits.eCommerceAction.action_type, and is
calibrated to the dataset's documented behaviour:

  * low overall conversion (~1.3%), typical of real retail
  * desktop-dominated traffic with notoriously weak MOBILE conversion
  * channelGrouping mix where Referral/Direct convert well and
    Social/Display convert poorly

Funnel (GA eCommerceAction.action_type codes):
  2 = product detail view   3 = add to cart   5 = checkout   6 = purchase
(We log a session-start "1" implicitly as every session.)

The downstream pipeline (02-05) reads these CSVs. To run on the REAL data,
export ga_sessions to the same two flat tables (see README) and skip step 01.

Run:  python src/01_generate_data.py
Output: data/raw/sessions.csv, hits.csv, products.csv
"""

import numpy as np
import pandas as pd
from pathlib import Path

RNG = np.random.default_rng(7)
OUT = Path(__file__).resolve().parents[1] / "data" / "raw"
OUT.mkdir(parents=True, exist_ok=True)

# ----------------------------------------------------------------------
N_SESSIONS = 150_000
START_DATE = pd.Timestamp("2016-11-01")     # matches the real sample's window
END_DATE   = pd.Timestamp("2017-01-31")

# GA channelGrouping values + realistic acquisition mix
CHANNELS = ["Organic Search", "Direct", "Referral", "Paid Search",
            "Social", "Affiliates", "Display"]
CHANNEL_WEIGHTS = [0.42, 0.20, 0.13, 0.10, 0.09, 0.03, 0.03]

# GA deviceCategory — desktop heavy (real sample is ~73/23/4)
DEVICES = ["desktop", "mobile", "tablet"]
DEVICE_WEIGHTS = [0.73, 0.23, 0.04]

# geoNetwork.country — Merchandise Store skews heavily US
COUNTRIES = ["United States", "India", "United Kingdom", "Canada",
             "Germany", "Brazil", "France", "Japan"]
COUNTRY_WEIGHTS = [0.46, 0.10, 0.08, 0.07, 0.06, 0.06, 0.05, 0.12]

# Google Merchandise Store product areas
CATEGORIES = {
    "Apparel": (12, 60),
    "Drinkware": (5, 30),
    "Bags": (10, 120),
    "Office": (1, 25),
    "Lifestyle": (8, 90),
    "Electronics Accessories": (3, 45),
    "Headgear": (8, 35),
    "Nest": (49, 299),
}

# Base funnel transition probabilities -> overall ~1.3%
#   s2v session->product_view, v2c view->cart, c2k cart->checkout, k2p checkout->purchase
BASE = {"s2v": 0.45, "v2c": 0.10, "c2k": 0.55, "k2p": 0.42}

# Device modifiers -- planted (and real) insight: mobile converts far worse.
DEVICE_MOD = {
    "desktop": {"s2v": 1.05, "v2c": 1.10, "c2k": 1.10, "k2p": 1.12},
    "mobile":  {"s2v": 0.95, "v2c": 0.70, "c2k": 0.70, "k2p": 0.62},
    "tablet":  {"s2v": 1.00, "v2c": 0.90, "c2k": 0.92, "k2p": 0.95},
}

# Channel modifiers -- intent differs by source.
CHANNEL_MOD = {
    "Organic Search": {"s2v": 1.05, "v2c": 1.02, "c2k": 1.03, "k2p": 1.05},
    "Direct":         {"s2v": 1.08, "v2c": 1.10, "c2k": 1.08, "k2p": 1.12},
    "Referral":       {"s2v": 1.10, "v2c": 1.18, "c2k": 1.10, "k2p": 1.20},
    "Paid Search":    {"s2v": 1.00, "v2c": 0.98, "c2k": 1.00, "k2p": 1.00},
    "Social":         {"s2v": 0.85, "v2c": 0.65, "c2k": 0.85, "k2p": 0.80},
    "Affiliates":     {"s2v": 0.95, "v2c": 0.80, "c2k": 0.90, "k2p": 0.88},
    "Display":        {"s2v": 0.80, "v2c": 0.60, "c2k": 0.80, "k2p": 0.78},
}

def clip(p): return float(min(max(p, 0.005), 0.99))

def make_products():
    rows, pid = [], 1
    for cat, (lo, hi) in CATEGORIES.items():
        n = RNG.integers(25, 55)
        for _ in range(n):
            rows.append({"productSKU": f"GGOE{pid:05d}", "v2ProductCategory": cat,
                         "productPrice": round(float(RNG.uniform(lo, hi)), 2)})
            pid += 1
    return pd.DataFrame(rows)

def make_data(products):
    skus = products["productSKU"].to_numpy()
    price = dict(zip(products["productSKU"], products["productPrice"]))
    cat = dict(zip(products["productSKU"], products["v2ProductCategory"]))

    fvid = RNG.integers(1_000_000_000, 9_999_999_999, N_SESSIONS).astype(str)
    channels = RNG.choice(CHANNELS, N_SESSIONS, p=CHANNEL_WEIGHTS)
    devices  = RNG.choice(DEVICES, N_SESSIONS, p=DEVICE_WEIGHTS)
    countries = RNG.choice(COUNTRIES, N_SESSIONS, p=COUNTRY_WEIGHTS)
    span = (END_DATE - START_DATE).days
    dates = START_DATE + pd.to_timedelta(RNG.integers(0, span + 1, N_SESSIONS), unit="D")
    visit_start = (dates.view("int64") // 10**9) + RNG.integers(0, 86400, N_SESSIONS)

    sess_rows, hit_rows = [], []
    for i in range(N_SESSIONS):
        sid = i + 1
        ch, dev = channels[i], devices[i]
        dmod, cmod = DEVICE_MOD[dev], CHANNEL_MOD[ch]
        hitnum = 1
        pageviews = int(RNG.integers(1, 4))

        def hit(action_type, sku):
            nonlocal hitnum
            hit_rows.append({
                "session_id": sid, "hitNumber": hitnum, "hit_type": "EVENT",
                "eCommerceAction_action_type": action_type,
                "productSKU": sku,
                "v2ProductCategory": cat.get(sku) if sku else None,
                "productPrice": price.get(sku, 0.0) if sku else 0.0,
            })
            hitnum += 1

        reached = {"pv": False, "cart": False, "checkout": False, "purchase": False}
        revenue = 0.0
        if RNG.random() < clip(BASE["s2v"] * dmod["s2v"] * cmod["s2v"]):
            sku = str(RNG.choice(skus)); reached["pv"] = True
            hit(2, sku); pageviews += 1
            if RNG.random() < clip(BASE["v2c"] * dmod["v2c"] * cmod["v2c"]):
                reached["cart"] = True; hit(3, sku)
                if RNG.random() < clip(BASE["c2k"] * dmod["c2k"] * cmod["c2k"]):
                    reached["checkout"] = True; hit(5, sku)
                    if RNG.random() < clip(BASE["k2p"] * dmod["k2p"] * cmod["k2p"]):
                        reached["purchase"] = True
                        qty = int(RNG.integers(1, 4))
                        revenue = round(price[sku] * qty, 2)
                        hit(6, sku)

        sess_rows.append({
            "fullVisitorId": fvid[i], "visitId": int(visit_start[i]), "session_id": sid,
            "date": dates[i].strftime("%Y%m%d"),
            "channelGrouping": ch, "deviceCategory": dev, "country": countries[i],
            "totals_pageviews": pageviews,
            "totals_bounces": 1 if not reached["pv"] and RNG.random() < 0.5 else 0,
            "totals_hits": hitnum,
            "totals_transactions": 1 if reached["purchase"] else 0,
            "totals_transactionRevenue": int(revenue * 1_000_000),  # GA stores micros
        })

    return pd.DataFrame(sess_rows), pd.DataFrame(hit_rows)

def main():
    products = make_products()
    sessions, hits = make_data(products)

    products.to_csv(OUT / "products.csv", index=False)
    sessions.to_csv(OUT / "sessions.csv", index=False)
    hits.to_csv(OUT / "hits.csv", index=False)

    conv = sessions["totals_transactions"].mean()
    print(f"products: {len(products):,}")
    print(f"sessions: {len(sessions):,}")
    print(f"hits:     {len(hits):,}")
    print(f"overall conversion: {conv:.3%}")
    print("action_type counts:\n", hits["eCommerceAction_action_type"].value_counts().sort_index())

if __name__ == "__main__":
    main()
