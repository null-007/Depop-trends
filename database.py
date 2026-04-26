import sqlite3
from datetime import datetime

DB_FILE = "depop.db"

def get_connection():
    return sqlite3.connect(DB_FILE)

def setup_database():
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS listings (
            id TEXT PRIMARY KEY,
            brand TEXT,
            size TEXT,
            price TEXT,
            query TEXT,
            image TEXT,
            link TEXT,
            first_seen TEXT,
            last_seen TEXT,
            status TEXT DEFAULT 'available'
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            listing_id TEXT,
            date TEXT,
            price TEXT,
            status TEXT,
            FOREIGN KEY (listing_id) REFERENCES listings(id)
        )
    """)
    
    conn.commit()
    conn.close()
    print("Database ready.")

def upsert_listing(listing):
    conn = get_connection()
    cursor = conn.cursor()
    today = datetime.now().strftime("%Y-%m-%d")
    
    cursor.execute("SELECT id FROM listings WHERE id = ?", (listing["id"],))
    existing = cursor.fetchone()
    
    if existing:
        cursor.execute("""
            UPDATE listings 
            SET last_seen = ?, price = ?, status = 'available'
            WHERE id = ?
        """, (today, listing["price"], listing["id"]))
    else:
        cursor.execute("""
            INSERT INTO listings (id, brand, size, price, query, image, link, first_seen, last_seen, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'available')
        """, (
            listing["id"], listing["brand"], listing["size"],
            listing["price"], listing["query"], listing["image"],
            listing["link"], today, today
        ))
    
    cursor.execute("""
        INSERT INTO daily_snapshots (listing_id, date, price, status)
        VALUES (?, ?, ?, 'available')
    """, (listing["id"], today, listing["price"]))
    
    conn.commit()
    conn.close()

def mark_sold_listings(seen_ids):
    conn = get_connection()
    cursor = conn.cursor()
    today = datetime.now().strftime("%Y-%m-%d")
    
    cursor.execute("""
        SELECT id FROM listings 
        WHERE status = 'available' AND last_seen < ?
    """, (today,))
    
    missing = cursor.fetchall()
    sold_count = 0
    
    for (listing_id,) in missing:
        if listing_id not in seen_ids:
            cursor.execute("""
                UPDATE listings SET status = 'sold' WHERE id = ?
            """, (listing_id,))
            cursor.execute("""
                INSERT INTO daily_snapshots (listing_id, date, price, status)
                VALUES (?, ?, '', 'sold')
            """, (listing_id, today))
            sold_count += 1
    
    conn.commit()
    conn.close()
    print(f"Marked {sold_count} listings as sold.")

def get_stats():
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT query,
               COUNT(*) as total,
               SUM(CASE WHEN status = 'sold' THEN 1 ELSE 0 END) as sold
        FROM listings
        GROUP BY query
        ORDER BY sold DESC
    """)
    sell_through = cursor.fetchall()
    
    cursor.execute("""
        SELECT brand, COUNT(*) as count
        FROM listings
        WHERE brand != 'Other' AND brand != 'N/A'
        GROUP BY brand
        ORDER BY count DESC
        LIMIT 10
    """)
    top_brands = cursor.fetchall()
    
    cursor.execute("""
        SELECT query, AVG(CAST(REPLACE(REPLACE(price, '$', ''), ',', '') AS FLOAT)) as avg_price
        FROM listings
        WHERE status = 'available'
        GROUP BY query
        ORDER BY avg_price DESC
    """)
    avg_prices = cursor.fetchall()

    cursor.execute("SELECT COUNT(*) FROM listings")
    total = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM listings WHERE status = 'sold'")
    total_sold = cursor.fetchone()[0]
    
    cursor.execute("""
        SELECT brand, size, price, query, image, link
        FROM listings
        WHERE status = 'available'
        ORDER BY last_seen DESC
        LIMIT 48
    """)
    recent = cursor.fetchall()
    
    conn.close()
    
    from datetime import datetime

    return {
        "sell_through": sell_through,
        "top_brands": top_brands,
        "avg_prices": avg_prices,
        "total": total,
        "total_sold": total_sold,
        "recent_listings": recent,
        "last_updated": datetime.now().strftime("%B %d, %Y at %I:%M %p")
    }
def get_trending_categories():
    conn = get_connection()
    cursor = conn.cursor()
    
    # only consider categories with at least 5 tracked listings
    cursor.execute("""
        SELECT query,
               COUNT(*) as total,
               SUM(CASE WHEN status = 'sold' THEN 1 ELSE 0 END) as sold,
               ROUND(SUM(CASE WHEN status = 'sold' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) as rate
        FROM listings
        GROUP BY query
        HAVING total >= 5
        ORDER BY rate DESC
        LIMIT 3
    """)
    results = cursor.fetchall()
    conn.close()
    return results
if __name__ == "__main__":
    setup_database()