# ============================================================
# E-Commerce Customer & Sales Analysis
# Dataset: Olist Brazilian E-Commerce (Kaggle)
# Author: Haider Ali | M.Sc. Data Science, BHT Berlin
# ============================================================
# Dataset download: https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce
# After download, place all CSVs inside the ../data/ folder
# ============================================================

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# ── Style ────────────────────────────────────────────────────
plt.rcParams.update({
    'figure.facecolor': '#0f1117',
    'axes.facecolor':   '#1a1d27',
    'axes.edgecolor':   '#2e3250',
    'axes.labelcolor':  '#c9d1d9',
    'xtick.color':      '#8b949e',
    'ytick.color':      '#8b949e',
    'text.color':       '#c9d1d9',
    'grid.color':       '#2e3250',
    'grid.linewidth':   0.6,
    'font.family':      'DejaVu Sans',
})
ACCENT   = '#4f8ef7'
GREEN    = '#3fb950'
ORANGE   = '#f78166'
PURPLE   = '#bc8cff'
YELLOW   = '#e3b341'


# ============================================================
# 1. LOAD DATA
# ============================================================
print("Loading datasets...")

orders      = pd.read_csv('../data/olist_orders_dataset.csv',
                          parse_dates=['order_purchase_timestamp',
                                       'order_delivered_customer_date',
                                       'order_estimated_delivery_date'])
order_items = pd.read_csv('../data/olist_order_items_dataset.csv')
payments    = pd.read_csv('../data/olist_order_payments_dataset.csv')
customers   = pd.read_csv('../data/olist_customers_dataset.csv')
products    = pd.read_csv('../data/olist_products_dataset.csv')
reviews     = pd.read_csv('../data/olist_order_reviews_dataset_clean3.csv')
sellers     = pd.read_csv('../data/olist_sellers_dataset.csv')
category_tr = pd.read_csv('../data/product_category_name_translation.csv')

print(f"  Orders loaded      : {len(orders):,}")
print(f"  Customers loaded   : {len(customers):,}")
print(f"  Order items loaded : {len(order_items):,}")


# ============================================================
# 2. CLEAN & MERGE
# ============================================================
# Keep only delivered orders
orders_delivered = orders[orders['order_status'] == 'delivered'].copy()

# ── Revenue-level dataframe (orders + payments + customers) ──
# IMPORTANT: order_items is NOT merged here. One order can have
# multiple items AND multiple payment installments — merging both
# into one dataframe creates a cross-join (fan-out) that duplicates
# payment_value and inflates any SUM based on it. Keep this frame
# item-free so revenue/RFM numbers stay accurate.
df_revenue = (orders_delivered
      .merge(payments,  on='order_id',    how='left')
      .merge(customers, on='customer_id', how='left'))

df_revenue['delay_days'] = (
    df_revenue['order_delivered_customer_date'] - df_revenue['order_estimated_delivery_date']
).dt.days

df_revenue['month'] = df_revenue['order_purchase_timestamp'].dt.to_period('M')

# ── Item-level dataframe (orders + items + products + category) ──
# Used only for category/product breakdowns — payments intentionally
# excluded here for the same fan-out reason, in reverse.
df_items = (orders_delivered
      .merge(order_items, on='order_id',                 how='left')
      .merge(products,    on='product_id',                how='left')
      .merge(category_tr, on='product_category_name',     how='left')
      .merge(customers,   on='customer_id',                how='left'))

# `df` kept as an alias to df_revenue for any later code that assumed
# a single merged frame — safe because df_revenue has no fan-out.
df = df_revenue

print(f"\nRevenue frame shape : {df_revenue.shape}")
print(f"Item frame shape    : {df_items.shape}")
print(f"Date range: {df_revenue['order_purchase_timestamp'].min().date()} "
      f"→ {df_revenue['order_purchase_timestamp'].max().date()}")


# ============================================================
# 3. KPIs
# ============================================================
total_revenue    = df['payment_value'].sum()
total_orders     = df['order_id'].nunique()
avg_order_value  = df.groupby('order_id')['payment_value'].sum().mean()
unique_customers = df['customer_unique_id'].nunique()
late_pct         = (df['delay_days'] > 0).mean() * 100

print("\n── KPI Summary ──────────────────────────────────")
print(f"  Total Revenue      : R$ {total_revenue:,.0f}")
print(f"  Total Orders       : {total_orders:,}")
print(f"  Avg Order Value    : R$ {avg_order_value:.2f}")
print(f"  Unique Customers   : {unique_customers:,}")
print(f"  Late Delivery Rate : {late_pct:.1f}%")
print("─────────────────────────────────────────────────\n")


# ============================================================
# 4. RFM SEGMENTATION
# ============================================================
snapshot_date = df['order_purchase_timestamp'].max() + pd.Timedelta(days=1)

rfm = (df.groupby('customer_unique_id')
         .agg(
             recency   = ('order_purchase_timestamp',
                          lambda x: (snapshot_date - x.max()).days),
             frequency = ('order_id', 'nunique'),
             monetary  = ('payment_value', 'sum')
         )
         .reset_index())

# Score 1–4 (4 = best)
rfm['R_score'] = pd.qcut(rfm['recency'],   4, labels=[4,3,2,1]).astype(int)
rfm['F_score'] = pd.qcut(rfm['frequency'].rank(method='first'),
                          4, labels=[1,2,3,4]).astype(int)
rfm['M_score'] = pd.qcut(rfm['monetary'],  4, labels=[1,2,3,4]).astype(int)
rfm['RFM_score'] = rfm['R_score'] + rfm['F_score'] + rfm['M_score']

def segment(score):
    if score >= 10:
        return 'Champions'
    elif score >= 7:
        return 'Loyal Customers'
    elif score >= 5:
        return 'At-Risk'
    else:
        return 'Lost'

rfm['segment'] = rfm['RFM_score'].apply(segment)

seg_summary = (rfm.groupby('segment')
                  .agg(customers=('customer_unique_id','count'),
                       avg_revenue=('monetary','mean'),
                       avg_recency=('recency','mean'))
                  .round(1)
                  .sort_values('avg_revenue', ascending=False))

print("── RFM Segments ─────────────────────────────────")
print(seg_summary.to_string())
print("─────────────────────────────────────────────────\n")

# Export RFM table for Power BI import
rfm[['customer_unique_id', 'recency', 'frequency', 'monetary', 'segment']].to_csv(
    '../data/rfm_segments.csv', index=False)
print("RFM segments exported to data/rfm_segments.csv for Power BI import")


# ============================================================
# 5. VISUALIZATIONS
# ============================================================

# ── Chart 1: Monthly Revenue Trend ──────────────────────────
monthly = (df.groupby('month')['payment_value']
             .sum()
             .reset_index()
             .sort_values('month'))
monthly['month_str'] = monthly['month'].astype(str)

fig, ax = plt.subplots(figsize=(12, 4))
ax.fill_between(monthly['month_str'], monthly['payment_value'],
                alpha=0.18, color=ACCENT)
ax.plot(monthly['month_str'], monthly['payment_value'],
        color=ACCENT, linewidth=2.2, marker='o', markersize=4)
ax.set_title('Monthly Revenue Trend', fontsize=14, fontweight='bold',
             color='white', pad=14)
ax.set_xlabel('Month');  ax.set_ylabel('Revenue (R$)')
ax.yaxis.set_major_formatter(mticker.FuncFormatter(
    lambda x, _: f'R${x/1e6:.1f}M'))
ax.set_xticks(ax.get_xticks()[::2])
ax.tick_params(axis='x', rotation=45)
ax.grid(axis='y', linestyle='--')
plt.tight_layout()
plt.savefig('../output/charts/01_monthly_revenue.png', dpi=150,
            bbox_inches='tight', facecolor='#0f1117')
plt.close()
print("Chart 1 saved: Monthly Revenue Trend")


# ── Chart 2: Top 10 Product Categories ──────────────────────
top_cat = (df_items.groupby('product_category_name_english')['price']
             .sum()
             .dropna()
             .nlargest(10)
             .sort_values())

colors = [ACCENT if i < 8 else YELLOW for i in range(10)]
fig, ax = plt.subplots(figsize=(10, 6))
bars = ax.barh(top_cat.index, top_cat.values, color=colors,
               edgecolor='none', height=0.65)
for bar, val in zip(bars, top_cat.values):
    ax.text(bar.get_width() + 15000, bar.get_y() + bar.get_height()/2,
            f'R${val/1e6:.2f}M', va='center', fontsize=8.5, color='#c9d1d9')
ax.set_title('Top 10 Product Categories by Revenue', fontsize=14,
             fontweight='bold', color='white', pad=14)
ax.set_xlabel('Total Revenue (R$)')
ax.xaxis.set_major_formatter(mticker.FuncFormatter(
    lambda x, _: f'R${x/1e6:.1f}M'))
ax.grid(axis='x', linestyle='--')
plt.tight_layout()
plt.savefig('../output/charts/02_top_categories.png', dpi=150,
            bbox_inches='tight', facecolor='#0f1117')
plt.close()
print("Chart 2 saved: Top Categories")


# ── Chart 3: RFM Customer Segments ──────────────────────────
seg_counts = rfm['segment'].value_counts()
seg_colors = [GREEN, ACCENT, ORANGE, '#666e7a']
seg_color_map = dict(zip(
    ['Champions','Loyal Customers','At-Risk','Lost'],
    seg_colors
))
bar_colors = [seg_color_map.get(s, ACCENT) for s in seg_counts.index]

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

# Donut
wedges, texts, autotexts = ax1.pie(
    seg_counts, labels=seg_counts.index,
    colors=[seg_color_map[s] for s in seg_counts.index],
    autopct='%1.1f%%', startangle=90,
    wedgeprops={'width': 0.55, 'edgecolor': '#0f1117', 'linewidth': 2},
    textprops={'color': '#c9d1d9', 'fontsize': 9}
)
for at in autotexts:
    at.set_color('white'); at.set_fontsize(9)
ax1.set_title('Customer Segments', fontsize=13, fontweight='bold',
              color='white', pad=12)

# Avg Revenue per segment
seg_rev = rfm.groupby('segment')['monetary'].mean().reindex(
    ['Champions','Loyal Customers','At-Risk','Lost'])
bars2 = ax2.bar(seg_rev.index,
                seg_rev.values,
                color=[seg_color_map[s] for s in seg_rev.index],
                edgecolor='none', width=0.55)
for bar, val in zip(bars2, seg_rev.values):
    ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 20,
             f'R${val:.0f}', ha='center', fontsize=9, color='white')
ax2.set_title('Avg Revenue per Segment', fontsize=13, fontweight='bold',
              color='white', pad=12)
ax2.set_ylabel('Avg Revenue (R$)')
ax2.grid(axis='y', linestyle='--')
ax2.tick_params(axis='x', rotation=10)

plt.suptitle('RFM Customer Segmentation Analysis', fontsize=15,
             fontweight='bold', color='white', y=1.02)
plt.tight_layout()
plt.savefig('../output/charts/03_rfm_segments.png', dpi=150,
            bbox_inches='tight', facecolor='#0f1117')
plt.close()
print("Chart 3 saved: RFM Segments")


# ── Chart 4: Delivery Performance by State ──────────────────
delay_state = (df.groupby('customer_state')['delay_days']
                 .mean()
                 .sort_values(ascending=False)
                 .head(15))

bar_cols = [ORANGE if v > 0 else GREEN for v in delay_state.values]

fig, ax = plt.subplots(figsize=(12, 5))
bars = ax.bar(delay_state.index, delay_state.values,
              color=bar_cols, edgecolor='none', width=0.65)
ax.axhline(0, color='white', linewidth=0.8, linestyle='--', alpha=0.4)
ax.set_title('Avg Delivery Delay by Customer State (Top 15)',
             fontsize=14, fontweight='bold', color='white', pad=14)
ax.set_xlabel('State'); ax.set_ylabel('Avg Delay (days)')
ax.grid(axis='y', linestyle='--')

from matplotlib.patches import Patch
legend = [Patch(color=ORANGE, label='Late (avg > 0 days)'),
          Patch(color=GREEN,  label='On Time / Early')]
ax.legend(handles=legend, loc='upper right',
          facecolor='#1a1d27', edgecolor='#2e3250',
          labelcolor='white', fontsize=9)
plt.tight_layout()
plt.savefig('../output/charts/04_delivery_delay.png', dpi=150,
            bbox_inches='tight', facecolor='#0f1117')
plt.close()
print("Chart 4 saved: Delivery Delay by State")


# ── Chart 5: Revenue Distribution (Pareto) ──────────────────
customer_rev = (df.groupby('customer_unique_id')['payment_value']
                  .sum()
                  .sort_values(ascending=False)
                  .reset_index())
customer_rev['cum_pct'] = (customer_rev['payment_value'].cumsum()
                           / customer_rev['payment_value'].sum() * 100)
customer_rev['cust_pct'] = (np.arange(1, len(customer_rev)+1)
                            / len(customer_rev) * 100)

fig, ax = plt.subplots(figsize=(10, 4))
ax.plot(customer_rev['cust_pct'], customer_rev['cum_pct'],
        color=ACCENT, linewidth=2)
ax.axvline(20, color=ORANGE, linestyle='--', linewidth=1.2, alpha=0.8)
rev_at_20 = customer_rev[customer_rev['cust_pct'] <= 20]['cum_pct'].max()
ax.axhline(rev_at_20, color=ORANGE, linestyle='--',
           linewidth=1.2, alpha=0.8)
ax.text(21, rev_at_20 + 1.5,
        f'Top 20% customers\n→ {rev_at_20:.1f}% of revenue',
        color=ORANGE, fontsize=9)
ax.fill_between(customer_rev['cust_pct'], customer_rev['cum_pct'],
                alpha=0.12, color=ACCENT)
ax.set_title('Pareto: Cumulative Revenue by Customer %',
             fontsize=14, fontweight='bold', color='white', pad=14)
ax.set_xlabel('Cumulative Customers (%)');
ax.set_ylabel('Cumulative Revenue (%)')
ax.grid(linestyle='--')
plt.tight_layout()
plt.savefig('../output/charts/05_pareto_revenue.png', dpi=150,
            bbox_inches='tight', facecolor='#0f1117')
plt.close()
print("Chart 5 saved: Pareto Revenue")

print("\n✅ All charts saved to output/charts/")
print("✅ Analysis complete — ready for Power BI + GitHub!")
