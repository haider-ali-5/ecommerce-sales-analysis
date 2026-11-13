-- ============================================================
-- E-Commerce Sales Analysis — SQL Queries
-- Dataset: Olist Brazilian E-Commerce (Kaggle)
-- Author: Haider Ali | M.Sc. Data Science, BHT Berlin
-- ============================================================

-- ============================================================
-- 1. MONTHLY REVENUE TREND
-- ============================================================
SELECT
    DATE_TRUNC('month', o.order_purchase_timestamp) AS month,
    COUNT(DISTINCT o.order_id)                       AS total_orders,
    ROUND(SUM(p.payment_value)::NUMERIC, 2)          AS total_revenue,
    ROUND(AVG(p.payment_value)::NUMERIC, 2)          AS avg_order_value
FROM orders o
JOIN order_payments p ON o.order_id = p.order_id
WHERE o.order_status = 'delivered'
GROUP BY 1
ORDER BY 1;


-- ============================================================
-- 2. TOP 10 PRODUCT CATEGORIES BY REVENUE
-- ============================================================
SELECT
    pt.product_category_name_english    AS category,
    COUNT(DISTINCT oi.order_id)         AS total_orders,
    ROUND(SUM(oi.price)::NUMERIC, 2)    AS total_revenue,
    ROUND(AVG(oi.price)::NUMERIC, 2)    AS avg_price
FROM order_items oi
JOIN products p      ON oi.product_id = p.product_id
JOIN product_category_name_translation pt
                     ON p.product_category_name = pt.product_category_name
GROUP BY 1
ORDER BY total_revenue DESC
LIMIT 10;


-- ============================================================
-- 3. DELIVERY PERFORMANCE — Avg Delay by State
-- ============================================================
SELECT
    c.customer_state                                              AS state,
    COUNT(o.order_id)                                            AS total_orders,
    ROUND(AVG(
        EXTRACT(EPOCH FROM (
            o.order_delivered_customer_date - o.order_estimated_delivery_date
        )) / 86400
    )::NUMERIC, 1)                                               AS avg_delay_days,
    SUM(CASE
        WHEN o.order_delivered_customer_date > o.order_estimated_delivery_date
        THEN 1 ELSE 0
    END)                                                         AS late_deliveries
FROM orders o
JOIN customers c ON o.customer_id = c.customer_id
WHERE o.order_status = 'delivered'
  AND o.order_delivered_customer_date IS NOT NULL
GROUP BY 1
ORDER BY avg_delay_days DESC;


-- ============================================================
-- 4. CUSTOMER REPEAT RATE
-- ============================================================
WITH customer_orders AS (
    SELECT
        customer_unique_id,
        COUNT(order_id) AS order_count
    FROM orders o
    JOIN customers c ON o.customer_id = c.customer_id
    WHERE o.order_status = 'delivered'
    GROUP BY 1
)
SELECT
    COUNT(*)                                                        AS total_customers,
    SUM(CASE WHEN order_count = 1 THEN 1 ELSE 0 END)               AS one_time_buyers,
    SUM(CASE WHEN order_count > 1 THEN 1 ELSE 0 END)               AS repeat_buyers,
    ROUND(
        100.0 * SUM(CASE WHEN order_count > 1 THEN 1 ELSE 0 END)
        / COUNT(*), 2
    )                                                               AS repeat_rate_pct
FROM customer_orders;


-- ============================================================
-- 5. REVENUE CONTRIBUTION — Top 20% Customers (Pareto Check)
-- ============================================================
WITH customer_revenue AS (
    SELECT
        c.customer_unique_id,
        ROUND(SUM(p.payment_value)::NUMERIC, 2) AS total_spent
    FROM orders o
    JOIN customers c       ON o.customer_id = c.customer_id
    JOIN order_payments p  ON o.order_id = p.order_id
    WHERE o.order_status = 'delivered'
    GROUP BY 1
),
ranked AS (
    SELECT *,
        NTILE(5) OVER (ORDER BY total_spent DESC) AS revenue_quintile
    FROM customer_revenue
)
SELECT
    revenue_quintile,
    COUNT(*)                          AS customer_count,
    ROUND(SUM(total_spent)::NUMERIC, 2) AS total_revenue,
    ROUND(
        100.0 * SUM(total_spent) / SUM(SUM(total_spent)) OVER (),
        2
    )                                  AS revenue_share_pct
FROM ranked
GROUP BY 1
ORDER BY 1;


-- ============================================================
-- 6. SELLER PERFORMANCE — Top 10 by Revenue
-- ============================================================
SELECT
    oi.seller_id,
    s.seller_state,
    COUNT(DISTINCT oi.order_id)          AS total_orders,
    ROUND(SUM(oi.price)::NUMERIC, 2)     AS total_revenue,
    ROUND(AVG(r.review_score)::NUMERIC, 2) AS avg_review_score
FROM order_items oi
JOIN sellers s          ON oi.seller_id = s.seller_id
LEFT JOIN order_reviews r ON oi.order_id = r.order_id
GROUP BY 1, 2
ORDER BY total_revenue DESC
LIMIT 10;
