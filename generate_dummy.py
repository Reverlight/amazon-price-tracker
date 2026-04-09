import csv
import random
from datetime import datetime, timedelta

ASINs = [
    ("B0G3WHQ8MX", 9.99),
    ("B0FRM8M38X", 24.99),
    ("B0G9PQ4PDN", 39.99),
]

rows = []
now = datetime.utcnow()

for asin, base_price in ASINs:
    price = base_price
    for day in range(30, 0, -1):
        # 1-3 checks per day
        checks = random.randint(1, 3)
        for check in range(checks):
            hour = random.randint(0, 23)
            minute = random.randint(0, 59)
            ts = now - timedelta(days=day, hours=-hour, minutes=-minute)

            # occasional bigger move, otherwise small drift
            if random.random() < 0.08:
                change = random.choice([-2, -1, 1, 2]) * random.uniform(0.5, 2.0)
            else:
                change = random.uniform(-0.30, 0.30)

            price = round(max(base_price * 0.7, price + change), 2)
            rows.append({
                "asin": asin,
                "url": f"https://www.amazon.com/dp/{asin}/?th=1&psc=1",
                "price": price,
                "timestamp": ts.isoformat(),
            })

rows.sort(key=lambda r: r["timestamp"])

with open("prices_dummy.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["asin", "url", "price", "timestamp"])
    writer.writeheader()
    writer.writerows(rows)

print(f"Generated {len(rows)} rows for {len(ASINs)} ASINs -> prices_dummy.csv")