import json
from database import get_trending_categories

def get_filter_buttons(queries):
    buttons = []
    for q in queries:
        btn = f"<button class='filter-btn' onclick=\"filterCards('{q}', this)\">{q}</button>"
        buttons.append(btn)
    return ''.join(buttons)


def generate_dashboard(stats, queries):
    trending = get_trending_categories()
    
    if trending:
        trending_html = "".join([
            f'<div><strong>{r[0]}</strong> &nbsp;<span style="color:#ff2300;font-weight:700">{r[3]}% sold</span> <span style="color:#888;font-size:12px">({r[2]} of {r[1]})</span></div>'
            for r in trending
        ])
    else:
        trending_html = '<div style="color:#888;font-size:13px">Not enough data yet — check back after a few days of tracking.</div>'
    sell_through_labels = [r[0] for r in stats["sell_through"]]
    sell_through_rates = [
        round((r[2] / r[1] * 100), 1) if r[1] > 0 else 0 
        for r in stats["sell_through"]
    ]
    top_brand_labels = [r[0] for r in stats["top_brands"]]
    top_brand_values = [r[1] for r in stats["top_brands"]]
    avg_price_labels = [r[0] for r in stats["avg_prices"]]
    avg_price_values = [round(r[1], 2) if r[1] else 0 for r in stats["avg_prices"]]

    product_cards = ""
    for p in stats["recent_listings"]:
        brand, size, price, query, image, link = p
        product_cards += f"""
        <a href="{link}" target="_blank" class="card" data-query="{query}">
            <img src="{image}" alt="{brand}" onerror="this.src='https://via.placeholder.com/200x200?text=No+Image'"/>
            <div class="card-info">
                <span class="brand">{brand}</span>
                <span class="size">{size}</span>
                <span class="price">{price}</span>
                <span class="query-tag">{query}</span>
            </div>
        </a>"""

    sold_cards = ""
    for p in stats["sold_listings"]:
        brand, size, price, query, image, link = p
        sold_cards += f"""
        <a href="{link}" target="_blank" class="card" data-query="{query}">
            <img src="{image}" alt="{brand}" onerror="this.src='https://via.placeholder.com/200x200?text=No+Image'"/>
            <div class="card-info">
                <span class="brand">{brand}</span>
                <span class="size">{size}</span>
                <span class="price" style="color:#888;text-decoration:line-through">{price}</span>
                <span class="query-tag" style="background:#ffe0e0;color:#cc0000">sold</span>
            </div>
        </a>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<title>Depop Trend Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, sans-serif; background: #f5f5f5; color: #222; }}
  header {{ background: #ff2300; color: white; padding: 24px 32px; }}
  header h1 {{ font-size: 28px; font-weight: 700; }}
  header p {{ opacity: 0.85; margin-top: 4px; }}
  .stats {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; padding: 24px 32px; }}
  .stat {{ background: white; border-radius: 12px; padding: 20px; text-align: center; box-shadow: 0 1px 4px rgba(0,0,0,0.08); }}
  .stat .number {{ font-size: 36px; font-weight: 700; color: #ff2300; }}
  .stat .label {{ color: #666; margin-top: 4px; font-size: 14px; }}
  .charts {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px; padding: 0 32px 24px; }}
  .chart-box {{ background: white; border-radius: 12px; padding: 20px; box-shadow: 0 1px 4px rgba(0,0,0,0.08); }}
  .chart-box h2 {{ font-size: 16px; font-weight: 600; margin-bottom: 16px; }}
  .sell-through-note {{ font-size: 12px; color: #888; margin-top: 8px; }}
  .section-title {{ padding: 0 32px 16px; font-size: 20px; font-weight: 700; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 16px; padding: 0 32px 32px; }}
  .card {{ background: white; border-radius: 12px; overflow: hidden; text-decoration: none; color: inherit; box-shadow: 0 1px 4px rgba(0,0,0,0.08); transition: transform 0.2s; }}
  .card:hover {{ transform: translateY(-4px); }}
  .card img {{ width: 100%; height: 200px; object-fit: cover; }}
  .card-info {{ padding: 12px; }}
  .brand {{ display: block; font-weight: 600; font-size: 14px; }}
  .size {{ display: block; color: #888; font-size: 13px; margin-top: 2px; }}
  .price {{ display: block; font-weight: 700; color: #ff2300; margin-top: 4px; }}
  .query-tag {{ display: inline-block; margin-top: 8px; background: #ff2300; border-radius: 20px; padding: 2px 10px; font-size: 11px; color: white; }}
  .filters {{ display: flex; gap: 12px; padding: 0 32px 24px; flex-wrap: wrap; align-items: center; }}
  .filter-btn {{ background: white; border: 1.5px solid #ddd; border-radius: 20px; padding: 6px 16px; font-size: 13px; cursor: pointer; transition: all 0.2s; }}
  .filter-btn:hover {{ border-color: #ff2300; color: #ff2300; }}
  .filter-btn.active {{ background: #ff2300; color: white; border-color: #ff2300; }}
  .filter-label {{ font-size: 13px; color: #888; margin-right: 4px; }}
  .card.hidden {{ display: none; }}
  .tabs {{ display: flex; gap: 0; padding: 24px 32px 0; }}
  .tab {{ padding: 10px 24px; font-size: 14px; font-weight: 600; cursor: pointer; border-radius: 8px 8px 0 0; background: #e0e0e0; color: #666; border: none; }}
  .tab.active {{ background: white; color: #ff2300; }}
  .tab-content {{ display: none; }}
  .tab-content.active {{ display: block; }}
</style>
</head>
<body>
<header>
  <h1>Depop Trend Dashboard</h1>
  <p>{stats['total']} listings tracked &nbsp;·&nbsp; {stats['total_sold']} sold detected &nbsp;·&nbsp; Last updated: {stats['last_updated']}</p>
</header>

<div style="background: #fff8f7; border-left: 4px solid #ff2300; margin: 24px 32px 0; padding: 16px 20px; border-radius: 8px;">
  <div style="font-weight: 700; font-size: 14px; color: #ff2300; margin-bottom: 8px;">🔥 Hot right now</div>
  <div style="display: flex; gap: 24px; flex-wrap: wrap;">
    {trending_html}
  </div>
</div>
</header>

<div class="stats">
  <div class="stat"><div class="number">{stats['total']}</div><div class="label">Total Tracked</div></div>
  <div class="stat"><div class="number">{stats['total_sold']}</div><div class="label">Sold Detected</div></div>
  <div class="stat"><div class="number">{round(stats['total_sold'] / stats['total'] * 100, 1) if stats['total'] > 0 else 0}%</div><div class="label">Overall Sell-Through</div></div>
  <div class="stat"><div class="number">{len(stats['top_brands'])}</div><div class="label">Unique Brands</div></div>
</div>

<div class="charts">
  <div class="chart-box">
    <h2>Sell-Through Rate by Category</h2>
    <canvas id="sellThroughChart"></canvas>
    <p class="sell-through-note">% of tracked listings that have sold. More accurate over time.</p>
  </div>
  <div class="chart-box"><h2>Top Brands</h2><canvas id="brandsChart"></canvas></div>
  <div class="chart-box"><h2>Average Price by Category</h2><canvas id="priceChart"></canvas></div>
</div>

<div class="tabs">
  <button class="tab active" onclick="switchTab('available', this)">Available Listings</button>
  <button class="tab" onclick="switchTab('sold', this)">Sold Listings ({stats['total_sold']})</button>
</div>

<div id="available" class="tab-content active">
  <div class="filters" style="padding-top: 16px;">
    <span class="filter-label">Filter by:</span>
    <button class="filter-btn active" onclick="filterCards('all', this)">All</button>
    {get_filter_buttons(queries)}
  </div>
  <div class="section-title" style="padding-top: 16px;">Recent Listings</div>
  <div class="grid" id="available-grid">{product_cards}</div>
</div>

<div id="sold" class="tab-content">
  <div class="section-title" style="padding: 24px 32px 16px;">Sold Listings</div>
  <div class="grid">{sold_cards}</div>
</div>

<script>
  new Chart(document.getElementById('sellThroughChart'), {{
    type: 'bar',
    data: {{ 
      labels: {json.dumps(sell_through_labels)}, 
      datasets: [{{ 
        data: {json.dumps(sell_through_rates)}, 
        backgroundColor: '#ff2300',
        label: 'Sell-through %'
      }}] 
    }},
    options: {{ plugins: {{ legend: {{ display: false }} }}, scales: {{ y: {{ max: 100, ticks: {{ callback: v => v + '%' }} }} }} }}
  }});
  new Chart(document.getElementById('brandsChart'), {{
    type: 'bar',
    data: {{ labels: {json.dumps(top_brand_labels)}, datasets: [{{ data: {json.dumps(top_brand_values)}, backgroundColor: '#222' }}] }},
    options: {{ plugins: {{ legend: {{ display: false }} }}, scales: {{ x: {{ ticks: {{ maxRotation: 45 }} }} }} }}
  }});
  new Chart(document.getElementById('priceChart'), {{
    type: 'bar',
    data: {{ labels: {json.dumps(avg_price_labels)}, datasets: [{{ data: {json.dumps(avg_price_values)}, backgroundColor: '#ff2300', label: 'Avg $' }}] }},
    options: {{ plugins: {{ legend: {{ display: false }} }}, scales: {{ x: {{ ticks: {{ maxRotation: 45 }} }}, y: {{ ticks: {{ callback: v => '$' + v }} }} }} }}
  }});
  function filterCards(query, btn) {{
    document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    document.querySelectorAll('.card').forEach(card => {{
      if (query === 'all' || card.dataset.query === query) {{
        card.classList.remove('hidden');
      }} else {{
        card.classList.add('hidden');
      }}
    }});
  }}
  function switchTab(tab, btn) {{
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById(tab).classList.add('active');
  }}
</script>
</script>
</body>
</html>"""

    with open("index.html", "w") as f:
        f.write(html)
    print("Dashboard saved to index.html")