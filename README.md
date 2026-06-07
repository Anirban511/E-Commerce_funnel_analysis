# E-Commerce_funnel_analysis
An end-to-end business analytics project on Google Analytics e-commerce data: from raw session/hit clickstream to a quantified, dollar-valued recommendation and an interactive Power BI dashboard — with SQL that runs on the *real* public BigQuery dataset.
**Headline finding:** Overall session-to-purchase conversion is **1.38%**
> (typical for real retail). The funnel's biggest structural leak is the
> **product-view → add-to-cart** step (only **10.3%** advance). Segmenting by
> device exposes the real story: **desktop converts at 1.72% versus just 0.33%
> on mobile — a ~5× gap** (two-proportion z-test: z = 19.3, *p < 0.001*).
> Closing only half of that mobile gap is worth an estimated **~$86K in
> additional annual revenue** at the store's ~$89 AOV.

---

## About the data

This project is built on the schema of the public **Google Analytics Sample**
dataset — the Google Merchandise Store —
`bigquery-public-data.google_analytics_sample.ga_sessions_*`.

Because that dataset lives in BigQuery (Google sign-in required), this repo ships
a **schema-faithful stand-in** (`src/01_generate_data.py`) that mirrors the real
export's field names and is **calibrated to the dataset's documented behaviour**:
~1.3% conversion, desktop-dominated traffic (~73%), weak mobile conversion, and a
channelGrouping mix where Referral/Direct convert well and Social/Display poorly.
This makes the project fully reproducible offline.

**To run on the real data instead:** the queries in
`sql/funnel_queries_bigquery.sql` execute directly against the public BigQuery
dataset (no download) and reproduce the same funnel. You can also export the two
flat tables (`sessions`, `hits`) and skip step 01 — the rest of the pipeline is
identical.
