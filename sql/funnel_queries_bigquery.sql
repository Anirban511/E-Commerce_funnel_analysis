-- ============================================================
-- funnel_queries_bigquery.sql   (BigQuery Standard SQL)
-- RUNS AGAINST THE REAL PUBLIC DATASET — no download needed:
--   bigquery-public-data.google_analytics_sample.ga_sessions_*
--
-- The GA export is one row per session with a REPEATED `hits` record.
-- The e-commerce funnel is encoded in hits.eCommerceAction.action_type:
--   '2' product view  '3' add to cart  '5' checkout  '6' purchase
-- These queries UNNEST hits to derive one funnel-flagged row per session,
-- exactly mirroring the Python/SQLite pipeline in this repo.
--
-- Paste into the BigQuery console (free tier covers this easily) and run.
-- Adjust the _TABLE_SUFFIX window as desired (sample spans 20160801-20170801).
-- ============================================================

-- Reusable flattened-session CTE
-- (copy this WITH block in front of any query below)
WITH sessions AS (
  SELECT
    CONCAT(fullVisitorId, '-', CAST(visitId AS STRING))        AS session_id,
    channelGrouping                                            AS channel,
    device.deviceCategory                                      AS device,
    geoNetwork.country                                         AS country,
    totals.pageviews                                           AS pageviews,
    IF(IFNULL(totals.transactions, 0) > 0, 1, 0)               AS purchased,
    IFNULL(totals.transactionRevenue, 0) / 1e6                 AS revenue,
    (SELECT MAX(IF(h.eCommerceAction.action_type = '2', 1, 0)) FROM UNNEST(hits) h) AS reached_product_view,
    (SELECT MAX(IF(h.eCommerceAction.action_type = '3', 1, 0)) FROM UNNEST(hits) h) AS reached_cart,
    (SELECT MAX(IF(h.eCommerceAction.action_type = '5', 1, 0)) FROM UNNEST(hits) h) AS reached_checkout
  FROM `bigquery-public-data.google_analytics_sample.ga_sessions_*`
  WHERE _TABLE_SUFFIX BETWEEN '20161101' AND '20170131'
)

-- 1. Overall step-conversion funnel
SELECT
  COUNT(*)                                                                AS sessions,
  SUM(reached_product_view)                                              AS product_views,
  SUM(reached_cart)                                                      AS add_to_carts,
  SUM(reached_checkout)                                                  AS checkouts,
  SUM(purchased)                                                         AS purchases,
  ROUND(SUM(reached_cart)     / NULLIF(SUM(reached_product_view),0), 4)  AS view_to_cart,
  ROUND(SUM(reached_checkout) / NULLIF(SUM(reached_cart),0), 4)          AS cart_to_checkout,
  ROUND(SUM(purchased)        / NULLIF(SUM(reached_checkout),0), 4)      AS checkout_to_purchase,
  ROUND(SUM(purchased)        / COUNT(*), 4)                             AS overall_conversion
FROM sessions;

-- ------------------------------------------------------------
-- 2. Funnel by device  (re-paste the WITH block above, then:)
-- ------------------------------------------------------------
-- SELECT
--   device,
--   COUNT(*) AS sessions,
--   ROUND(SUM(reached_cart)/NULLIF(SUM(reached_product_view),0),4) AS view_to_cart,
--   ROUND(SUM(reached_checkout)/NULLIF(SUM(reached_cart),0),4)     AS cart_to_checkout,
--   ROUND(SUM(purchased)/NULLIF(SUM(reached_checkout),0),4)        AS checkout_to_purchase,
--   ROUND(SUM(purchased)/COUNT(*),4)                               AS overall_conversion
-- FROM sessions
-- GROUP BY device
-- ORDER BY overall_conversion DESC;

-- ------------------------------------------------------------
-- 3. Conversion & revenue by channelGrouping
-- ------------------------------------------------------------
-- SELECT
--   channel,
--   COUNT(*)                              AS sessions,
--   SUM(purchased)                        AS orders,
--   ROUND(SUM(purchased)/COUNT(*),4)      AS conversion_rate,
--   ROUND(SUM(revenue),2)                 AS revenue,
--   ROUND(SUM(revenue)/COUNT(*),3)        AS revenue_per_session
-- FROM sessions
-- GROUP BY channel
-- ORDER BY conversion_rate DESC;

-- ------------------------------------------------------------
-- 4. Device x Channel matrix (worst pockets first)
-- ------------------------------------------------------------
-- SELECT device, channel, COUNT(*) AS sessions,
--   ROUND(SUM(purchased)/COUNT(*),4) AS conversion_rate
-- FROM sessions GROUP BY device, channel
-- ORDER BY conversion_rate ASC;
