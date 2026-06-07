-- ============================================================
-- funnel_queries_sqlite.sql   (SQLite dialect) — Google Analytics
-- GA Merchandise Store funnel & conversion analysis.
--
-- HOW TO RUN:
--   python src/05_build_sqlite.py                      # builds data/funnel.db
--   sqlite3 data/funnel.db ".read sql/funnel_queries_sqlite.sql"
--
-- Table: sessions  (one row per session, from data/processed/sessions.csv)
--   session_id, fullVisitorId, date, channel, device, country, pageviews,
--   reached_product_view, reached_cart, reached_checkout, purchased (0/1),
--   revenue (USD)
-- Table: purchases (one row per purchased item) — for category revenue.
--
-- The funnel stages come from GA hits.eCommerceAction.action_type:
--   2 product_view, 3 add_to_cart, 5 checkout, 6 purchase  (pre-derived).
-- ============================================================

.headers on
.mode column

-- 1. Overall funnel: sessions reaching each stage
SELECT 'Sessions'     AS stage, COUNT(*)                  AS cnt FROM sessions
UNION ALL SELECT 'Product View', SUM(reached_product_view) FROM sessions
UNION ALL SELECT 'Add to Cart',  SUM(reached_cart)         FROM sessions
UNION ALL SELECT 'Checkout',     SUM(reached_checkout)     FROM sessions
UNION ALL SELECT 'Purchase',     SUM(purchased)            FROM sessions;

-- 2. Step conversion rates (where the funnel leaks)
SELECT
  ROUND(1.0*SUM(reached_product_view)/COUNT(*),4)                           AS session_to_view,
  ROUND(1.0*SUM(reached_cart)/NULLIF(SUM(reached_product_view),0),4)        AS view_to_cart,
  ROUND(1.0*SUM(reached_checkout)/NULLIF(SUM(reached_cart),0),4)            AS cart_to_checkout,
  ROUND(1.0*SUM(purchased)/NULLIF(SUM(reached_checkout),0),4)               AS checkout_to_purchase,
  ROUND(1.0*SUM(purchased)/COUNT(*),4)                                      AS overall_conversion
FROM sessions;

-- 3. Funnel by device (surfaces the mobile leak)
SELECT
  device,
  COUNT(*)                                                       AS sessions,
  ROUND(1.0*SUM(reached_cart)/NULLIF(SUM(reached_product_view),0),4) AS view_to_cart,
  ROUND(1.0*SUM(reached_checkout)/NULLIF(SUM(reached_cart),0),4)     AS cart_to_checkout,
  ROUND(1.0*SUM(purchased)/NULLIF(SUM(reached_checkout),0),4)        AS checkout_to_purchase,
  ROUND(1.0*SUM(purchased)/COUNT(*),4)                              AS overall_conversion
FROM sessions
GROUP BY device
ORDER BY overall_conversion DESC;

-- 4. Conversion & revenue by acquisition channel (channelGrouping)
SELECT
  channel,
  COUNT(*)                                  AS sessions,
  SUM(purchased)                            AS orders,
  ROUND(1.0*SUM(purchased)/COUNT(*),4)      AS conversion_rate,
  ROUND(SUM(revenue),2)                     AS revenue,
  ROUND(SUM(revenue)/COUNT(*),3)            AS revenue_per_session
FROM sessions
GROUP BY channel
ORDER BY conversion_rate DESC;

-- 5. Device x Channel matrix (worst-performing pockets first)
SELECT
  device, channel,
  COUNT(*)                                  AS sessions,
  ROUND(1.0*SUM(purchased)/COUNT(*),4)      AS conversion_rate
FROM sessions
GROUP BY device, channel
ORDER BY conversion_rate ASC
LIMIT 10;

-- 6. Daily trend
SELECT
  date,
  COUNT(*)                                  AS sessions,
  SUM(purchased)                            AS orders,
  ROUND(1.0*SUM(purchased)/COUNT(*),4)      AS conversion_rate,
  ROUND(SUM(revenue),2)                     AS revenue
FROM sessions
GROUP BY date
ORDER BY date
LIMIT 15;   -- remove LIMIT for full series

-- 7. Revenue by product category
SELECT
  category,
  COUNT(*)               AS orders,
  ROUND(SUM(revenue),2)  AS revenue,
  ROUND(AVG(revenue),2)  AS avg_item_value
FROM purchases
GROUP BY category
ORDER BY revenue DESC;
