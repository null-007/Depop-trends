from playwright.sync_api import sync_playwright
import csv
import time
import json
from collections import Counter

QUERIES = [
    "vintage shirts",
    "vintage jeans",
    "vintage jacket",
    "y2k top",
    "baggy jeans",
    "vintage hoodie",
    "cargo pants",
    "band tee",
]

def scrape_query(page, query):
    url = f"https://www.depop.com/search/?q={query.replace(' ', '+')}"
    page.goto(url)
    page.wait_for_timeout(3000)
    
    prices = page.query_selector_all('[aria-label="Price"]')
    products = []
    
    for price in prices:
        card = price.evaluate_handle("el => el.closest('li')")
        card_el = card.as_element()
        
        if card_el is None:
            continue
        
        lines = card_el.inner_text().strip().split("\n")
        lines = [l.strip() for l in lines if l.strip()]
        
        brand = lines[0] if len(lines) > 0 else "N/A"
        size  = lines[1] if len(lines) > 1 else "N/A"
        price = lines[2] if len(lines) > 2 else "N/A"
        
        img = card_el.query_selector("img")
        raw_url = img.get_attribute("src") if img else ""
        img_url = raw_url.replace("/P10.jpg", "/P0.jpg") if raw_url else ""
        
        link = card_el.query_selector("a")
        href = link.get_attribute("href") if link else ""
        full_link = f"https://www.depop.com{href}" if href else ""
        
        products.append({
            "brand": brand,
            "size": size,
            "price": price,
            "query": query,
            "image": img_url,
            "link": full_link,
        })
    
    print(f"'{query}': {len(products)} products found")
    return products

def save_to_csv(all_products):
    with open("depop_results.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["brand", "size", "price", "query", "image", "link"])
        writer.writeheader()
        writer.writerows(all_products)
    print(f"Saved {len(all_products)} total products to depop_results.csv")

def analyze(all_products):
    prices_clean = []
    for p in all_products:
        try:
            prices_clean.append(float(p["price"].replace("$", "").replace(",", "")))
        except:
            pass
    
    brand_counts = Counter(p["brand"] for p in all_products if p["brand"] != "N/A" and p["brand"] != "Other")
    size_counts  = Counter(p["size"]  for p in all_products if p["size"]  != "N/A")
    query_counts = Counter(p["query"] for p in all_products)
    
    # price buckets
    buckets = {"Under $10": 0, "$10-$20": 0, "$20-$30": 0, "$30-$50": 0, "Over $50": 0}
    for price in prices_clean:
        if price < 10:       buckets["Under $10"] += 1
        elif price < 20:     buckets["$10-$20"]   += 1
        elif price < 30:     buckets["$20-$30"]   += 1
        elif price < 50:     buckets["$30-$50"]   += 1
        else:                buckets["Over $50"]  += 1
    
    return {
        "top_brands":  brand_counts.most_common(10),
        "top_sizes":   size_counts.most_common(6),
        "price_buckets": buckets,
        "query_counts":  query_counts.most_common(),
        "avg_price":   round(sum(prices_clean) / len(prices_clean), 2) if prices_clean else 0,
        "total":       len(all_products),
    }

def generate_dashboard(all_products, stats):
    top_brands_labels  = [b[0] for b in stats["top_brands"]]
    top_brands_values  = [b[1] for b in stats["top_brands"]]
    size_labels        = [s[0] for s in stats["top_sizes"]]
    size_values        = [s[1] for s in stats["top_sizes"]]
    price_labels       = list(stats["price_buckets"].keys())
    price_values       = list(stats["price_buckets"].values())
    query_labels       = [q[0] for q in stats["query_counts"]]
    query_values       = [q[1] for q in stats["query_counts"]]

    product_cards = ""
    for p in all_products[:48]:
        product_cards += f"""
        <a href="{p['link']}" target="_blank" class="card">
            <img src="{p['image']}" alt="{p['brand']}" onerror="this.src='https://via.placeholder.com/200x200?text=No+Image'"/>
            <div class="card-info">
                <span class="brand">{p['brand']}</span>
                <span class="size">{p['size']}</span>
                <span class="price">{p['price']}</span>
                <span class="query-tag">{p['query']}</span>
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
  .stats {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; padding: 24px 32px; }}
  .stat {{ background: white; border-radius: 12px; padding: 20px; text-align: center; box-shadow: 0 1px 4px rgba(0,0,0,0.08); }}
  .stat .number {{ font-size: 36px; font-weight: 700; color: #ff2300; }}
  .stat .label {{ color: #666; margin-top: 4px; font-size: 14px; }}
  .charts {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px; padding: 0 32px 24px; }}
  .chart-box {{ background: white; border-radius: 12px; padding: 20px; box-shadow: 0 1px 4px rgba(0,0,0,0.08); }}
  .chart-box h2 {{ font-size: 16px; font-weight: 600; margin-bottom: 16px; }}
  .section-title {{ padding: 0 32px 16px; font-size: 20px; font-weight: 700; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 16px; padding: 0 32px 32px; }}
  .card {{ background: white; border-radius: 12px; overflow: hidden; text-decoration: none; color: inherit; box-shadow: 0 1px 4px rgba(0,0,0,0.08); transition: transform 0.2s; }}
  .card:hover {{ transform: translateY(-4px); }}
  .card img {{ width: 100%; height: 200px; object-fit: cover; }}
  .card-info {{ padding: 12px; }}
  .brand {{ display: block; font-weight: 600; font-size: 14px; }}
  .size {{ display: block; color: #888; font-size: 13px; margin-top: 2px; }}
  .price {{ display: block; font-weight: 700; color: #ff2300; margin-top: 4px; }}
  .query-tag {{ display: inline-block; margin-top: 8px; background: #f0f0f0; border-radius: 20px; padding: 2px 10px; font-size: 11px; color: #555; }}
</style>
</head>
<body>
<header>
  <h1>Depop Trend Dashboard</h1>
  <p>{stats['total']} listings scraped across {len(QUERIES)} search queries &nbsp;·&nbsp; Avg price: ${stats['avg_price']}</p>
</header>

<div class="stats">
  <div class="stat"><div class="number">{stats['total']}</div><div class="label">Total Listings</div></div>
  <div class="stat"><div class="number">${stats['avg_price']}</div><div class="label">Average Price</div></div>
  <div class="stat"><div class="number">{len(stats['top_brands'])}</div><div class="label">Unique Brands</div></div>
</div>

<div class="charts">
  <div class="chart-box"><h2>Top Brands</h2><canvas id="brandsChart"></canvas></div>
  <div class="chart-box"><h2>Price Ranges</h2><canvas id="priceChart"></canvas></div>
  <div class="chart-box"><h2>Most Common Sizes</h2><canvas id="sizeChart"></canvas></div>
  <div class="chart-box"><h2>Listings by Search Query</h2><canvas id="queryChart"></canvas></div>
</div>

<div class="section-title">Product Listings</div>
<div class="grid">{product_cards}</div>

<script>
  const brandChart = new Chart(document.getElementById('brandsChart'), {{
    type: 'bar',
    data: {{ labels: {json.dumps(top_brands_labels)}, datasets: [{{ data: {json.dumps(top_brands_values)}, backgroundColor: '#ff2300' }}] }},
    options: {{ plugins: {{ legend: {{ display: false }} }}, scales: {{ x: {{ ticks: {{ maxRotation: 45 }} }} }} }}
  }});
  const priceChart = new Chart(document.getElementById('priceChart'), {{
    type: 'doughnut',
    data: {{ labels: {json.dumps(price_labels)}, datasets: [{{ data: {json.dumps(price_values)}, backgroundColor: ['#ff2300','#ff6b35','#ffa500','#ffd700','#90ee90'] }}] }},
  }});
  const sizeChart = new Chart(document.getElementById('sizeChart'), {{
    type: 'bar',
    data: {{ labels: {json.dumps(size_labels)}, datasets: [{{ data: {json.dumps(size_values)}, backgroundColor: '#222' }}] }},
    options: {{ plugins: {{ legend: {{ display: false }} }} }}
  }});
  const queryChart = new Chart(document.getElementById('queryChart'), {{
    type: 'bar',
    data: {{ labels: {json.dumps(query_labels)}, datasets: [{{ data: {json.dumps(query_values)}, backgroundColor: '#ff2300' }}] }},
    options: {{ plugins: {{ legend: {{ display: false }} }}, scales: {{ x: {{ ticks: {{ maxRotation: 45 }} }} }} }}
  }});
</script>
</body>
</html>"""

    with open("index.html", "w") as f:
        f.write(html)
    print("Dashboard saved to index.html — open it in your browser!")

def main():
    all_products = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        for query in QUERIES:
            products = scrape_query(page, query)
            all_products.extend(products)
            time.sleep(2)
        browser.close()
    
    save_to_csv(all_products)
    stats = analyze(all_products)
    generate_dashboard(all_products, stats)

main()