# DAX Measures

Measures and calculated objects of the Power BI semantic model
(`dashboard/pbip/ecommerce_dashboard.SemanticModel`). They are listed exactly as defined in the
model's TMDL files (only whitespace was added for readability). Table names keep the `public `
prefix created by the PostgreSQL connector.

Relationships the measures rely on (see `relationships.tmdl`): `public order_payments[order_id]` -> `public orders[order_id]`
(bi-directional), `public order_items[order_id]` -> `public orders[order_id]`, `public orders[customer_id]` <-> `public customers[customer_id]`
(one-to-one, bi-directional) and `public customers[customer_unique_id]` <-> `rfm_segments[customer_unique_id]` (bi-directional).
Payments and order items are never summed together in one measure, which avoids the fan-out described in the README.

## Measures

### Table `public orders`

**Total Orders** - number of distinct delivered orders.
```dax
Total Orders =
CALCULATE(
    DISTINCTCOUNT('public orders'[order_id]),
    'public orders'[order_status] = "delivered"
)
```

**Total Revenue** - sum of customer payments for delivered orders (BRL).
```dax
Total Revenue =
CALCULATE(
    SUM('public order_payments'[payment_value]),
    'public orders'[order_status] = "delivered"
)
```

**: Avg Order Value** - revenue per delivered order. (The leading colon is part of the measure name in the model.)
```dax
: Avg Order Value = DIVIDE([Total Revenue], [Total Orders])
```

**Late Delivery Rate %** - share of delivered orders that arrived on a later calendar day than the
estimated date, as a number between 0 and 100 (format string `0.00"%"`, so 6.77 is shown as 6.77%).
```dax
Late Delivery Rate % =
VAR LateCount =
    CALCULATE(
        COUNTROWS('public orders'),
        FILTER(
            'public orders',
            VAR d1 = IFERROR(DATEVALUE('public orders'[order_delivered_customer_date]), BLANK())
            VAR d2 = IFERROR(DATEVALUE('public orders'[order_estimated_delivery_date]), BLANK())
            RETURN NOT ISBLANK(d1) && NOT ISBLANK(d2) && d1 > d2
        )
    )
RETURN
    DIVIDE(LateCount, [Total Orders]) * 100
```

**Avg Delay Days** - average of (delivered date - estimated date) in calendar days; negative values mean
the order arrived before the estimate. Used by the "15 States with Smallest Delivery Buffer" chart.
```dax
Avg Delay Days =
AVERAGEX(
    FILTER(
        'public orders',
        LEN('public orders'[order_delivered_customer_date]) > 5
            && LEN('public orders'[order_estimated_delivery_date]) > 5
    ),
    IFERROR(
        DATEDIFF(
            DATEVALUE('public orders'[order_estimated_delivery_date]),
            DATEVALUE('public orders'[order_delivered_customer_date]),
            DAY
        ),
        BLANK()
    )
)
```

**Payment Row Count** - number of payment rows (helper for checking the payments grain).
```dax
Payment Row Count = COUNTROWS('public order_payments')
```

> The model also contains an empty placeholder measure called `Measure` in `public orders` (no expression).

### Table `rfm_segments`

**One-Time Buyers** - customers with exactly one delivered order (frequency = 1).
```dax
One-Time Buyers =
CALCULATE(COUNTROWS('rfm_segments'), 'rfm_segments'[frequency] = 1)
```

**Repeat Buyers** - customers with more than one delivered order.
```dax
Repeat Buyers =
CALCULATE(COUNTROWS('rfm_segments'), 'rfm_segments'[frequency] > 1)
```

**Revenue at Risk** - all-time revenue of customers in the At-Risk and Lost RFM segments.
```dax
Revenue at Risk =
CALCULATE(
    SUM('rfm_segments'[monetary]),
    'rfm_segments'[segment] IN {"At-Risk", "Lost"}
)
```

### Table `Geo Summary`

**Repeat Buyer %** - share of customers (by `customer_unique_id`) with more than one delivered order,
respecting the current filters.
```dax
Repeat Buyer % =
VAR t =
    ADDCOLUMNS(
        VALUES('public customers'[customer_unique_id]),
        "n", CALCULATE(
            DISTINCTCOUNT('public orders'[order_id]),
            'public orders'[order_status] = "delivered"
        )
    )
VAR total = COUNTROWS(FILTER(t, [n] > 0))
VAR repeat = COUNTROWS(FILTER(t, [n] > 1))
RETURN
    DIVIDE(repeat, total)
```

## Calculated columns

**`public orders[Order Month]`** - year-month label used on the trend chart axis.
```dax
Order Month =
FORMAT(DATEVALUE(LEFT('public orders'[order_purchase_timestamp], 10)), "YYYY-MM")
```

**`public orders[Order Year]`** - year slicer field.
```dax
Order Year = LEFT('public orders'[Order Month], 4)
```

**`rfm_segments[Revenue Rank]`** - rank of each customer by monetary value (1 = highest).
```dax
Revenue Rank = RANKX('rfm_segments', 'rfm_segments'[monetary], , DESC)
```

**`rfm_segments[Cumulative %]`** - cumulative share of revenue up to this customer's rank (0-100); x-axis partner of the Pareto curve.
```dax
Cumulative % =
VAR TotalCustomers = COUNTROWS('rfm_segments')
VAR TotalRevenue = SUM('rfm_segments'[monetary])
VAR CumRevenue =
    CALCULATE(
        SUM('rfm_segments'[monetary]),
        FILTER(
            'rfm_segments',
            'rfm_segments'[Revenue Rank] <= EARLIER('rfm_segments'[Revenue Rank])
        )
    )
RETURN
    DIVIDE(CumRevenue, TotalRevenue) * 100
```

**`rfm_segments[Customer Percentile]`** - customer's rank as a percentage of all customers (0-100).
```dax
Customer Percentile =
DIVIDE('rfm_segments'[Revenue Rank], COUNTROWS('rfm_segments')) * 100
```

## Calculated table

**`Geo Summary`** - one row per ZIP-code prefix and state with average latitude/longitude, used for the customer map.
```dax
Geo Summary =
SUMMARIZE(
    'public geolocation',
    'public geolocation'[geolocation_zip_code_prefix],
    'public geolocation'[geolocation_state],
    "Avg Lat", AVERAGE('public geolocation'[geolocation_lat]),
    "Avg Lng", AVERAGE('public geolocation'[geolocation_lng])
)
```

## Data sources (Power Query)

- `public orders`, `public order_items`, `public order_payments`, `public customers`, `public products`,
  `public sellers`, `public order_reviews`, `public geolocation`, `public product_category_name_translation`:
  PostgreSQL, `localhost:5432`, database `ecommerce_db`, schema `public`.
- `rfm_segments`: CSV `data/rfm_segments.csv` (generated by `notebooks/analysis.py`). The path stored in the model is an
  absolute path on the author's machine - change it under *Transform data > rfm_segments > Source* after cloning.
