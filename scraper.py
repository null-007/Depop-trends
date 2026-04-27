from playwright.sync_api import sync_playwright
import time
import re
from database import setup_database, upsert_listing, get_stats, save_trending_term, get_weekly_trends
from dashboard import generate_dashboard

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
        img_url = raw_url.replace("/P10.jpg", "/P8.jpg") if raw_url else ""
        
        link = card_el.query_selector("a")
        href = link.get_attribute("href") if link else ""
        full_link = f"https://www.depop.com{href}" if href else ""
        
        # extract unique ID from URL slug
        match = re.search(r'/products/([^/]+)/', href)
        item_id = match.group(1) if match else href
        
        if item_id:
            products.append({
                "id": item_id,
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
def mark_sold_listings_verified(seen_ids, page):
    import sqlite3
    from datetime import datetime
    
    conn = sqlite3.connect("depop.db")
    cursor = conn.cursor()
    today = datetime.now().strftime("%Y-%m-%d")
    
    cursor.execute("""
        SELECT id, link FROM listings 
        WHERE status = 'available' AND last_seen < ?
    """, (today,))
    
    missing = cursor.fetchall()
    sold_count = 0
    not_sold_count = 0
    
    print(f"Checking {len(missing)} missing listings...")
    
    for (listing_id, link) in missing:
        if listing_id in seen_ids:
            continue
        
        try:
            page.goto(link, timeout=10000)
            page.wait_for_timeout(800)
            
            content = page.content()
            
            if "SoldOut" in content:
                cursor.execute("UPDATE listings SET status = 'sold' WHERE id = ?", (listing_id,))
                cursor.execute("""
                    INSERT INTO daily_snapshots (listing_id, date, price, status)
                    VALUES (?, ?, '', 'sold')
                """, (listing_id, today))
                sold_count += 1
            else:
                not_sold_count += 1
                
        except Exception as e:
            print(f"Error checking {link}: {e}")
            continue
        
        time.sleep(0.5)
    
    conn.commit()
    conn.close()
    print(f"Verified {sold_count} sold, {not_sold_count} still available")

def get_trending_searches(page):
    try:
        page.goto("https://www.depop.com/")
        page.wait_for_timeout(2000)
        
        # click the search bar to trigger trending searches
        page.click('[placeholder="Search for items, brands, or styles…"]')
        page.wait_for_timeout(1500)
        
        # grab all trending search terms
        trending = page.query_selector_all('#trending-searches li')
        terms = []
        for item in trending:
            text = item.inner_text().strip().lower()
            if text:
                terms.append(text)
        
        print(f"Found {len(terms)} trending searches: {terms}")
        return terms
    except Exception as e:
        print(f"Could not fetch trending searches: {e}")
        return []

def get_trending_searches(page):
    try:
        page.goto("https://www.depop.com/")
        page.wait_for_timeout(2000)
        
        # click using the stable id
        page.click('#searchBar__input', timeout=5000)
        page.wait_for_timeout(2000)
        
        trending = page.query_selector_all('#trending-searches li')
        terms = []
        for item in trending:
            text = item.inner_text().strip().lower()
            if text:
                terms.append(text)
        
        print(f"Found {len(terms)} trending searches: {terms}")
        return terms
    except Exception as e:
        print(f"Could not fetch trending searches: {e}")
        return []

def main():
    setup_database()
    all_products = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        
        # get trending searches from depop
        trending_terms = get_trending_searches(page)
        
        # merge with base queries avoiding duplicates
        all_queries = list(QUERIES)
        for term in trending_terms:
            if term not in all_queries:
                all_queries.append(term)
                print(f"Added new trending query: {term}")
        
        for query in all_queries:
            products = scrape_query(page, query)
            all_products.extend(products)
            
            # only save trending terms, not base queries
            if query in trending_terms:
                save_trending_term(query, len(products))
            
            time.sleep(2)
        
        # save to database first
        seen_ids = set()
        for product in all_products:
            upsert_listing(product)
            seen_ids.add(product["id"])
        
        # verify sold listings while browser is still open
        mark_sold_listings_verified(seen_ids, page)
        
        browser.close()
    
    # generate dashboard from database
    stats = get_stats()
    generate_dashboard(stats, all_queries)

main()