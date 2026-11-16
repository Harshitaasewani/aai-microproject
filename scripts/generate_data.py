"""Synthetic marketplace generator for PS-13.

Real marketplaces do not publish reviewer IPs, device fingerprints or seller takedown history, so
we simulate a marketplace and *plant* known fraud scenarios in it. Because we planted them, we know
the ground truth and can measure whether the agents find them (see scripts/evaluate.py).

Planted scenarios
-----------------
P001  Aria Leather Crossbody Bag   review ring + 72h burst + templated text + stock photo + unverified
                                   "genuine leather" claim + 21-day-old seller with prior flags  -> fraud
P002  Aria Mini Tote               same seller, same ring, smaller burst                          -> fraud
P013  Velora Canvas Belt           partner seller sharing the same reviewer ring (reciprocal)     -> fraud
P003  Pulse Wireless Earbuds       incentivized reviews from REAL customers: text looks fake but
                                   the reviewer network is clean  -> conflicting signals          -> suspicious
P004  LuxeCo Monogram Wallet       counterfeit: brand imagery, unauthorized seller, price far
                                   below brand MSRP, organic reviews complaining about quality    -> counterfeit
P006  Terra Ceramic Mug            brand-new seller but honest -> must NOT be flagged high        -> clean
others                             established sellers, organic reviews                           -> clean
"""
from __future__ import annotations

import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
IMG = DATA / "images"
TODAY = datetime(2026, 10, 20, 12, 0, tzinfo=timezone.utc)

rng = np.random.default_rng(42)
random.seed(42)

TZ_OFFSETS = ["+05:30", "+00:00", "-07:00", "+01:00", "+08:00"]


def ts_local(dt_utc: datetime) -> str:
    """Store timestamps in mixed local offsets, as real scraped data would be. Ingestion normalizes."""
    off = random.choice(TZ_OFFSETS)
    sign = 1 if off[0] == "+" else -1
    h, m = int(off[1:3]), int(off[4:6])
    local = dt_utc.astimezone(timezone(sign * timedelta(hours=h, minutes=m)))
    return local.isoformat(timespec="seconds")


def days_ago(d: float) -> datetime:
    return TODAY - timedelta(days=d)


# ----------------------------------------------------------------------------------------------
# Sellers
# ----------------------------------------------------------------------------------------------
SELLERS = [
    # id, name, age_days, region
    ("S001", "Aria Leather House", 21, "IN"),
    ("S002", "Velora Accessories", 35, "IN"),
    ("S003", "PulseTech Audio", 410, "IN"),
    ("S004", "Metro Luxe Deals", 60, "IN"),
    ("S005", "Terra Home Studio", 30, "IN"),
    ("S006", "Heritage Leatherworks", 900, "IN"),
    ("S007", "Brightside Electronics", 700, "EU"),
    ("S008", "Urban Threads", 520, "IN"),
    ("S009", "Pure Skin Labs", 650, "EU"),
    ("S010", "Stride Co", 800, "US"),
]

PRODUCTS = [
    # id, seller, title, category, listed_days_ago, base_price, image, description
    ("P001", "S001", "Aria Leather Crossbody Bag", "bags", 20, 3999, "P001.png",
     "Premium genuine leather crossbody bag, handcrafted in Italy. Adjustable strap, gold-tone zipper, "
     "two inner pockets. Perfect for daily use."),
    ("P002", "S001", "Aria Mini Tote", "bags", 15, 2999, "P002.png",
     "Compact tote in genuine leather with magnetic snap closure and fabric lining."),
    ("P013", "S002", "Velora Canvas Belt", "bags", 33, 1499, "P013.png",
     "Pure cotton canvas belt with antique brass buckle. One size fits most."),
    ("P003", "S003", "Pulse Wireless Earbuds", "electronics", 180, 2499, "P003.png",
     "Bluetooth 5.3 earbuds with 30 hour battery, IPX5 water resistance, BIS certified charging case."),
    ("P004", "S004", "LuxeCo Monogram Wallet", "bags", 58, 2499, "P004.png",
     "100% authentic LuxeCo monogram wallet in genuine leather. Original brand packaging included."),
    ("P006", "S005", "Terra Ceramic Mug", "home", 28, 599, "P006.png",
     "Handmade stoneware mug, 350 ml, microwave safe glaze."),
    ("P005", "S008", "Nimbus Cotton Tee", "apparel", 260, 799, "P005.png",
     "Crew neck t-shirt, 100% cotton, regular fit."),
    ("P008", "S007", "Volt 20000mAh Power Bank", "electronics", 300, 1899, "P008.png",
     "20000 mAh power bank with 22.5W fast charging, BIS certified."),
    ("P009", "S009", "Glow Vitamin C Serum", "beauty", 240, 899, "P009.png",
     "10% vitamin C serum, dermatologically tested, fragrance free."),
    ("P010", "S010", "Stride Running Shoes", "footwear", 280, 3499, "P010.png",
     "Lightweight mesh running shoes with cushioned midsole."),
    ("P011", "S006", "Classic Leather Belt", "bags", 220, 1299, "P011.png",
     "Genuine leather belt with brushed steel buckle, made in India."),
    ("P012", "S007", "Echo Bluetooth Speaker", "electronics", 200, 2199, "P012.png",
     "Portable speaker, 12 hour playtime, IPX7 waterproof."),
    ("P014", "S006", "Canvas Weekender Bag", "bags", 190, 2799, "P014.png",
     "Waxed canvas weekender with leather trims and shoe compartment."),
    ("P015", "S008", "Jute Shopper Tote", "bags", 170, 699, "P015.png",
     "Eco-friendly jute tote with cotton handles."),
]

GROUND_TRUTH = {
    "P001": "fraud", "P002": "fraud", "P013": "fraud", "P003": "suspicious", "P004": "counterfeit",
}

# ----------------------------------------------------------------------------------------------
# Review text
# ----------------------------------------------------------------------------------------------
CATEGORY_DETAILS = {
    "bags": {
        "pos": ["the strap length is adjustable and sits {comfy} on the shoulder",
                "it fits my phone, wallet, keys and a {small} power bank",
                "the zipper runs smoothly even after {weeks} of use",
                "the inner pockets keep my cards and earphones separate",
                "the stitching along the handle looks neat and even",
                "the {colour} colour matches the photos closely",
                "the buckle feels solid and the edges are finished well",
                "there is enough room for a {small} umbrella and sunglasses",
                "it has softened up nicely after {weeks}",
                "the base holds its shape even when it is half empty",
                "I can carry a {tablet} inside without it bulging",
                "the magnetic flap closes firmly",
                "people at {place} asked me where I bought it",
                "the hardware has not tarnished after {weeks}"],
        "neg": ["the zipper got stuck after {weeks}",
                "the lining started tearing near the pocket",
                "the strap is too short for crossbody wear on me",
                "the colour is much darker than the listing photo",
                "it smells strongly of chemicals even after airing it out",
                "the stitching on one side came loose within {weeks}",
                "the material feels like plastic not leather",
                "the logo looks slightly off compared to the store version",
                "the buckle paint chipped within {weeks}",
                "the handle creases badly where you hold it"],
    },
    "electronics": {
        "pos": ["battery easily lasts {hours} hours on a single charge",
                "pairing with my {phone} took a few seconds",
                "the bass is punchy for this price",
                "calls are clear even on a busy road near {place}",
                "it charges from empty to full in about {hrs2} hours",
                "the case is small enough for a jeans pocket",
                "connection stays stable from one room to the next",
                "I can charge my {phone} about {times} times from full",
                "the LED indicator makes it easy to see the charge level",
                "it survived a fall from my desk without a scratch",
                "sound stays clear at high volume without distortion",
                "the build feels sturdy and the buttons click nicely"],
        "neg": ["the left side keeps disconnecting",
                "battery dropped to {hours} hours after a month",
                "it gets noticeably hot while charging",
                "the charging port feels loose",
                "volume is low even at maximum",
                "the companion app crashes often on my {phone}",
                "it stopped holding charge after {weeks}"],
    },
    "home": {
        "pos": ["the glaze has a lovely speckled finish", "it keeps tea warm for a while",
                "the handle is comfortable for my {small} hands", "it survived the dishwasher fine",
                "it holds a big serving of coffee", "the weight feels solid without being heavy"],
        "neg": ["there was a small chip on the rim", "the glaze colour is lighter than shown",
                "the base is slightly uneven so it wobbles"],
    },
    "apparel": {
        "pos": ["the cotton is soft and breathable in {place} humidity", "it did not shrink after {weeks} of washing",
                "the fit is true to size for my {build} build", "the neckline holds its shape after many washes",
                "the {colour} shade looks exactly like the photo", "the fabric is thick enough that it is not see-through",
                "it pairs well with jeans and chinos", "the sleeves are a nice length for my arms",
                "seams are flat and do not itch", "it dries quickly on the line"],
        "neg": ["it shrank a size after the first wash", "the colour faded after {weeks}",
                "the stitching at the hem is uneven", "it pills under the arms after {weeks}",
                "the collar stretched out quickly"],
    },
    "beauty": {
        "pos": ["it absorbs quickly without feeling sticky", "my skin looks brighter after {weeks}",
                "no irritation on my sensitive {skin} skin", "the dropper makes it easy to use a few drops",
                "dark spots on my cheeks have faded a little", "it layers well under sunscreen",
                "a single bottle has lasted me {weeks}", "it has almost no smell which I prefer",
                "my makeup sits better on top of it", "the amber bottle keeps it from oxidising quickly"],
        "neg": ["it caused a mild breakout on my chin", "the serum oxidised and turned orange in {weeks}",
                "it stings a little around the nose", "the dropper started leaking after {weeks}"],
    },
    "footwear": {
        "pos": ["the cushioning works well for my {km} km runs", "they are light and breathable",
                "grip is decent on wet roads during the monsoon", "no break-in period was needed",
                "my knees feel better after long runs at {place}", "the laces stay tied the whole run",
                "the heel counter feels supportive", "they still look new after {weeks}",
                "there is plenty of room for my wide feet", "they work for gym sessions too"],
        "neg": ["the sole started peeling after {weeks}", "they run half a size small",
                "the mesh tore near the toe", "the insole slides around inside"],
    },
}
OPENERS = ["Bought this {when}.", "Ordered it for my {who}.", "Been using it for {weeks}.",
           "Got it on sale {when}.", "This is my second purchase from this shop.", "", "", "", "Honest review:",
           "Took a chance on this one.", "Update after {weeks}:", "Delivered in {days} days.",
           "Was a gift for my {who}.", "Compared a few options before choosing this.", "Using it daily now."]
CLOSERS = ["Good value for the price.", "Would recommend.", "Delivery was quick.", "Packaging was basic.",
           "Not sure I would buy again.", "", "", "", "Overall decent.", "Returned it.", "Happy with it so far.",
           "Will update if anything changes.", "Okay for {price_word}.", "Worth it at the sale price.",
           "Customer support replied within a day.", "Fine for everyday use."]
FILL = {
    "comfy": ["comfortably", "well", "nicely", "fine"],
    "small": ["small", "compact", "slim", "mini", "foldable"],
    "weeks": ["two weeks", "a month", "three weeks", "six weeks", "a few days", "two months", "ten days", "a week"],
    "hours": ["5", "6", "7", "8", "4", "9"],
    "hrs2": ["1.5", "2", "2.5", "3"],
    "times": ["two", "three", "four"],
    "km": ["5", "10", "8", "12", "21", "15"],
    "when": ["last month", "in September", "for Diwali", "two weeks ago", "during the sale", "for my birthday",
             "after reading the reviews", "on a friend's suggestion"],
    "who": ["sister", "mother", "husband", "friend", "wife", "brother", "father", "roommate", "colleague"],
    "colour": ["tan", "black", "navy", "olive", "maroon", "grey", "white", "beige"],
    "tablet": ["10 inch tablet", "small notebook", "Kindle", "diary"],
    "place": ["work", "college", "the office", "the gym", "Mumbai", "Pune", "the park", "the station", "Bandra"],
    "phone": ["phone", "Pixel", "iPhone", "Samsung", "OnePlus", "laptop"],
    "build": ["slim", "medium", "athletic", "broad"],
    "skin": ["oily", "dry", "combination", "acne-prone"],
    "days": ["two", "three", "four", "five"],
    "price_word": ["the price", "this budget", "under a thousand", "daily use"],
}


def fill(s: str) -> str:
    for k, v in FILL.items():
        while "{" + k + "}" in s:
            s = s.replace("{" + k + "}", random.choice(v), 1)
    return s


def organic_text(category: str, rating: int) -> str:
    pool = CATEGORY_DETAILS[category]
    if rating >= 4:
        body = random.sample(pool["pos"], k=min(len(pool["pos"]), random.choice([1, 2, 2, 3])))
        if random.random() < 0.3:
            body.append("but " + random.choice(pool["neg"]))
    elif rating == 3:
        body = [random.choice(pool["pos"]), "but " + random.choice(pool["neg"])]
    else:
        body = random.sample(pool["neg"], k=min(len(pool["neg"]), random.choice([1, 2])))
    sentence = " and ".join(body) if random.random() < 0.5 else ". ".join(b.capitalize() for b in body)
    parts = [fill(random.choice(OPENERS)), fill(sentence[0].upper() + sentence[1:]) + ".", fill(random.choice(CLOSERS))]
    if random.random() < 0.3:
        random.shuffle(parts)
    out = " ".join(p for p in parts if p).replace("..", ".")
    if random.random() < 0.15:
        out = out.lower().replace(".", "")
    return out


RING_TEMPLATES = [
    "Exceeded my expectations, will buy again!",
    "Amazing quality, exceeded my expectations. Will buy again!",
    "Best purchase ever, exceeded my expectations, highly recommend!",
    "Excellent product, exceeded all my expectations. Will definitely buy again.",
    "Superb quality and fast delivery. Highly recommend this seller!",
    "Superb quality, fast delivery, highly recommend this seller to everyone!",
    "Very good product, value for money, five stars!",
    "Very nice product, totally value for money. Five stars!!",
]


def ring_text() -> str:
    t = random.choice(RING_TEMPLATES)
    r = random.random()
    if r < 0.2:
        t = t.replace("!", "!!")
    elif r < 0.35:
        t = "Wow. " + t
    elif r < 0.45:
        t = t + " Love it"
    return t


INCENTIVE_TEMPLATES = [
    "I received this product at a discount in exchange for my honest review. Great earbuds, amazing sound, highly recommend!",
    "Got this free in exchange for an honest review. Excellent product, great sound quality, highly recommend!",
    "I received a discount for my unbiased review. Amazing product, great quality, five stars!",
    "Received this product free for review purposes. Great earbuds, excellent quality, highly recommend!",
]


def incentive_text() -> str:
    t = random.choice(INCENTIVE_TEMPLATES)
    if random.random() < 0.3:
        t = t.replace("highly recommend", "would highly recommend")
    return t


def organic_rating() -> int:
    return int(rng.choice([1, 2, 3, 4, 5], p=[0.06, 0.05, 0.10, 0.27, 0.52]))


# ----------------------------------------------------------------------------------------------
# Reviewers
# ----------------------------------------------------------------------------------------------
reviewers: list[dict] = []


def new_reviewer(rid: str, created: datetime, ip: str, device: str, cats: int, orders: int, region="IN") -> dict:
    r = dict(reviewer_id=rid, account_created=created.date().isoformat(), ip_prefix=ip, device_id=device,
             categories_purchased=cats, total_orders=orders, region=region)
    reviewers.append(r)
    return r


ORGANIC = []
for i in range(2600):
    created = days_ago(float(rng.uniform(70, 2200)))
    ORGANIC.append(new_reviewer(
        f"U{i:05d}", created, f"{rng.integers(1, 223)}.{rng.integers(0, 255)}.{rng.integers(0, 255)}",
        f"DEV-{rng.integers(10**7, 10**8)}", int(rng.integers(2, 14)), int(rng.integers(4, 240)),
        random.choice(["IN", "IN", "IN", "EU", "US"])))

# The ring: ~460 accounts created inside one 5-day window, sharing a handful of IP ranges and devices,
# each with a single purchase category and very few orders.
RING_IPS = [f"103.21.{x}" for x in (14, 15, 16)] + [f"45.112.{x}" for x in (8, 9)]
RING_DEVICES = [f"DEV-R{x:03d}" for x in range(28)]
RING = []
for i in range(470):
    created = days_ago(float(rng.uniform(24, 29)))
    RING.append(new_reviewer(f"R{i:04d}", created, random.choice(RING_IPS), random.choice(RING_DEVICES),
                             1, int(rng.integers(1, 4))))

# ----------------------------------------------------------------------------------------------
# Reviews
# ----------------------------------------------------------------------------------------------
reviews: list[dict] = []
labels: list[dict] = []
_rid = 0


def add_review(pid: str, reviewer: dict, rating: int, text: str, when: datetime, verified: bool, fake: str):
    global _rid
    _rid += 1
    rid = f"RV{_rid:06d}"
    reviews.append(dict(review_id=rid, product_id=pid, reviewer_id=reviewer["reviewer_id"], rating=rating,
                        text=text, timestamp=ts_local(when), verified_purchase=bool(verified)))
    labels.append(dict(review_id=rid, label=fake))


def organic_reviews(pid: str, category: str, start_days_ago: float, per_week: float, used: set, end_days_ago=0.0):
    days = start_days_ago - end_days_ago
    n = int(rng.poisson(per_week / 7 * days))
    pool = [r for r in ORGANIC if r["reviewer_id"] not in used]
    picks = rng.choice(len(pool), size=min(n, len(pool)), replace=False)
    for j in picks:
        rv = pool[j]
        used.add(rv["reviewer_id"])
        # organic traffic peaks in the evening (IST) — diurnal pattern
        d = float(rng.uniform(end_days_ago, start_days_ago))
        when = days_ago(d).replace(hour=int(rng.choice(range(24), p=_DIURNAL)), minute=int(rng.integers(0, 60)))
        rating = organic_rating()
        add_review(pid, rv, rating, organic_text(category, rating), when, rng.random() < 0.9, "genuine")


_h = np.array([1, 1, 1, 1, 1, 2, 3, 4, 5, 6, 6, 6, 7, 7, 7, 7, 8, 9, 10, 10, 9, 7, 4, 2], dtype=float)
_DIURNAL = _h / _h.sum()

used_by_product: dict[str, set] = {p[0]: set() for p in PRODUCTS}

# Clean products: steady organic flow, ~15-20 reviews/week (category baseline from the brief)
for pid, sid, title, cat, listed, *_ in PRODUCTS:
    if pid in GROUND_TRUTH:
        continue
    rate = 2.2 if pid == "P006" else float(rng.uniform(14, 20))
    organic_reviews(pid, cat, listed, rate, used_by_product[pid])

# P001 Aria Leather Crossbody Bag: 289 five-star ring reviews in a 72h window + more ring + organic
ring_cursor = 0


def take_ring(n: int) -> list[dict]:
    global ring_cursor
    out = RING[ring_cursor:ring_cursor + n]
    ring_cursor += n
    return out


burst_start = days_ago(12)
for rv in take_ring(289):
    when = burst_start + timedelta(hours=float(rng.uniform(0, 72)))
    add_review("P001", rv, 5, ring_text(), when, rng.random() < 0.22, "ring")
for rv in take_ring(150):
    when = days_ago(float(rng.uniform(0.5, 19)))
    add_review("P001", rv, 5, ring_text(), when, rng.random() < 0.25, "ring")
pool = [r for r in ORGANIC if r["reviewer_id"] not in used_by_product["P001"]]
for j in rng.choice(len(pool), 73, replace=False):
    rating = int(rng.choice([1, 2, 3, 4, 5], p=[0.30, 0.20, 0.20, 0.15, 0.15]))
    add_review("P001", pool[j], rating, organic_text("bags", rating), days_ago(float(rng.uniform(0.5, 18))),
               rng.random() < 0.95, "genuine")

# P002 Aria Mini Tote: same ring, 60 reviews in 48h, rest spread
for rv in RING[:60]:  # same accounts that hit P001 -> reviewers only touch this seller's catalog
    add_review("P002", rv, 5, ring_text(), days_ago(8) + timedelta(hours=float(rng.uniform(0, 48))),
               rng.random() < 0.2, "ring")
for rv in RING[60:100]:
    add_review("P002", rv, 5, ring_text(), days_ago(float(rng.uniform(0.5, 14))), rng.random() < 0.2, "ring")
organic_reviews("P002", "bags", 14, 14, used_by_product["P002"])

# P013 Velora Canvas Belt (partner seller S002): reciprocal ring — reuses ring accounts + its own
for rv in RING[100:190] + take_ring(10):
    add_review("P013", rv, 5, ring_text(), days_ago(float(rng.uniform(3, 9))), rng.random() < 0.3, "ring")
organic_reviews("P013", "bags", 32, 12, used_by_product["P013"])

# P003 Pulse Earbuds: organic baseline + an incentivized campaign from real customers (clean network)
organic_reviews("P003", "electronics", 180, 15, used_by_product["P003"])
pool = [r for r in ORGANIC if r["reviewer_id"] not in used_by_product["P003"]]
for j in rng.choice(len(pool), 120, replace=False):
    when = days_ago(float(rng.uniform(40, 54)))
    add_review("P003", pool[j], int(rng.choice([4, 5], p=[0.1, 0.9])), incentive_text(), when, True, "incentivized")

# P004 LuxeCo wallet: counterfeit. Organic timing, buyers notice quality issues.
pool = [r for r in ORGANIC if r["reviewer_id"] not in used_by_product["P004"]]
for j in rng.choice(len(pool), 82, replace=False):
    rating = int(rng.choice([1, 2, 3, 4, 5], p=[0.25, 0.15, 0.15, 0.2, 0.25]))
    add_review("P004", pool[j], rating, organic_text("bags", rating), days_ago(float(rng.uniform(0.5, 56))),
               rng.random() < 0.9, "genuine")

# ----------------------------------------------------------------------------------------------
# Images: listing photos, a stock photo reused across unrelated sellers, a brand reference
# ----------------------------------------------------------------------------------------------
PALETTE = [(196, 120, 72), (60, 60, 70), (170, 40, 50), (40, 90, 140), (90, 130, 80), (210, 190, 150),
           (120, 70, 140), (30, 140, 140), (230, 150, 30), (100, 100, 100)]


def draw_product(path: Path, seed: int, kind: str):
    r = random.Random(seed)
    bg = tuple(r.randint(200, 250) for _ in range(3))
    im = Image.new("RGB", (512, 512), bg)
    d = ImageDraw.Draw(im)
    col = r.choice(PALETTE)
    # random studio-style background: stripes/panels of different brightness
    for _ in range(r.randint(5, 9)):
        x0 = r.randint(0, 480)
        w = r.randint(20, 160)
        shade = tuple(max(0, c - r.randint(0, 90)) for c in bg)
        d.rectangle([x0, 0, x0 + w, 512], fill=shade)
    # background gradient blobs make each image hash-distinct
    for _ in range(6):
        x, y, s = r.randint(0, 512), r.randint(0, 512), r.randint(60, 200)
        shade = tuple(max(0, c - r.randint(10, 40)) for c in bg)
        d.ellipse([x - s, y - s, x + s, y + s], fill=shade)
    if kind == "bag":
        x0, y0 = r.randint(90, 140), r.randint(190, 240)
        d.rounded_rectangle([x0, y0, x0 + r.randint(230, 300), y0 + r.randint(170, 220)], 30, fill=col)
        d.arc([x0 + 40, y0 - 120, x0 + 220, y0 + 60], 180, 360, fill=col, width=14)
    elif kind == "device":
        d.ellipse([150, 170, 260, 330], fill=col)
        d.ellipse([270, 170, 380, 330], fill=col)
        d.rounded_rectangle([170, 360, 360, 430], 25, fill=(50, 50, 55))
    else:
        d.rectangle([r.randint(120, 170), r.randint(130, 180), r.randint(330, 390), r.randint(330, 400)], fill=col)
    im = im.filter(ImageFilter.GaussianBlur(1))
    im.save(path)


def monogram(path: Path, bg=(92, 64, 40), fg=(205, 170, 95)):
    im = Image.new("RGB", (512, 512), bg)
    d = ImageDraw.Draw(im)
    for yy in range(0, 512, 64):
        for xx in range(0, 512, 64):
            off = 32 if (yy // 64) % 2 else 0
            cx, cy = xx + off, yy + 32
            d.polygon([(cx, cy - 18), (cx + 18, cy), (cx, cy + 18), (cx - 18, cy)], fill=fg)
            d.ellipse([cx + 22, cy - 6, cx + 34, cy + 6], fill=fg)
    d.rectangle([140, 200, 372, 312], outline=fg, width=6)
    d.text((200, 245), "LUXECO", fill=fg)
    im.save(path)


def variant(src: Path, dst: Path, scale=0.9, bright=1.06, seed=0):
    im = Image.open(src)
    w, h = im.size
    im = im.resize((int(w * scale), int(h * scale)))
    im = ImageEnhance.Brightness(im).enhance(bright)
    im.save(dst, quality=80) if dst.suffix == ".jpg" else im.save(dst)


kinds = {"bags": "bag", "electronics": "device"}
for i, (pid, sid, title, cat, *_r) in enumerate(PRODUCTS):
    if pid in ("P001", "P004"):
        continue
    draw_product(IMG / f"{pid}.png", 1000 + i, kinds.get(cat, "box"))

# Stock bag photo, used by P001 and by four unrelated sellers elsewhere on the marketplace
draw_product(IMG / "stock_bag_original.png", 777, "bag")
variant(IMG / "stock_bag_original.png", IMG / "P001.png", scale=0.95, bright=1.04)
# Brand reference + counterfeit listing image derived from it
monogram(IMG / "brand_ref_luxeco.png")
variant(IMG / "brand_ref_luxeco.png", IMG / "P004.png", scale=0.85, bright=1.1)

external = []
for k in range(4):
    f = f"EXT_stock_{k}.jpg"
    variant(IMG / "stock_bag_original.png", IMG / f, scale=0.7 + 0.08 * k, bright=0.95 + 0.04 * k)
    external.append(dict(listing_id=f"L-77{k:02d}", seller_id=f"X{k + 1:03d}", seller_name=f"Unrelated Seller {k + 1}",
                         image_file=f, listed_date=days_ago(float(rng.uniform(5, 58))).date().isoformat()))
for k in range(36):  # distractor listings with their own original photos
    f = f"EXT_orig_{k}.png"
    draw_product(IMG / f, 5000 + k, random.choice(["bag", "device", "box"]))
    external.append(dict(listing_id=f"L-80{k:02d}", seller_id=f"X{100 + k:03d}", seller_name=f"Seller {100 + k}",
                         image_file=f, listed_date=days_ago(float(rng.uniform(1, 200))).date().isoformat()))

# ----------------------------------------------------------------------------------------------
# Pricing history (P001 runs a deep "discount" exactly during the review burst, then restores price)
# ----------------------------------------------------------------------------------------------
prices = []
for pid, sid, title, cat, listed, base, *_ in PRODUCTS:
    d = listed
    while d >= 0:
        p = base * float(rng.choice([1, 1, 1, 0.95, 0.9]))
        if pid == "P001" and 11 <= d <= 14:
            p = 999
        if pid == "P002" and 7 <= d <= 9:
            p = 799
        prices.append(dict(product_id=pid, date=days_ago(d).date().isoformat(), price_inr=round(p)))
        d -= 3 if listed < 60 else 14

# ----------------------------------------------------------------------------------------------
# Seller history, certifications, brand data, past cases
# ----------------------------------------------------------------------------------------------
seller_events = [
    dict(seller_id="S001", date=days_ago(16).date().isoformat(), event="flag", listing_id="L-9001", note="Review burst on prior listing"),
    dict(seller_id="S001", date=days_ago(7).date().isoformat(), event="flag", listing_id="L-9002", note="Unverified material claim"),
    dict(seller_id="S001", date=days_ago(6).date().isoformat(), event="takedown", listing_id="L-9001", note="Listing removed after flag"),
    dict(seller_id="S001", date=days_ago(4).date().isoformat(), event="relist", listing_id="L-9003", note="Near-identical listing created"),
    dict(seller_id="S002", date=days_ago(12).date().isoformat(), event="flag", listing_id="L-9101", note="Suspicious review velocity"),
    dict(seller_id="S004", date=days_ago(20).date().isoformat(), event="warning", listing_id="L-9201", note="Brand complaint received"),
    dict(seller_id="S007", date=days_ago(400).date().isoformat(), event="warning", listing_id="L-9301", note="Late shipping (resolved)"),
]
certs = [
    dict(product_id="P011", claim_key="genuine leather", doc_ref="CERT-LTH-2291", verified_on="2026-03-02"),
    dict(product_id="P011", claim_key="made in india", doc_ref="COO-IN-5512", verified_on="2026-03-02"),
    dict(product_id="P009", claim_key="dermatologically tested", doc_ref="DERM-TEST-118", verified_on="2026-02-10"),
    dict(product_id="P008", claim_key="bis certified", doc_ref="BIS-R-41009876", verified_on="2025-12-15"),
    dict(product_id="P003", claim_key="bis certified", doc_ref="BIS-R-41207731", verified_on="2026-04-01"),
    dict(product_id="P005", claim_key="100% cotton", doc_ref="TEX-COT-7781", verified_on="2026-01-20"),
]
brands = [dict(brand="LuxeCo", reference_image="brand_ref_luxeco.png", msrp_inr=45000, authorized_sellers="S900;S901")]

# Historical cases for case memory: agent score vectors + resolved outcome
cases = []
for i in range(400):
    kind = rng.choice(["ring", "counterfeit", "incentivized", "clean", "clean", "clean"])
    base = dict(ring=[.8, .7, .85, .3, .2, .7], counterfeit=[.2, .2, .1, .7, .8, .5],
                incentivized=[.4, .75, .15, .1, .05, .2], clean=[.1, .15, .1, .15, .05, .15])[kind]
    v = np.clip(np.array(base) + rng.normal(0, 0.15, 6), 0, 1)
    outcome = {"ring": "confirmed_review_fraud", "counterfeit": "confirmed_counterfeit",
               "incentivized": rng.choice(["confirmed_incentivized", "cleared"], p=[.7, .3]),
               "clean": rng.choice(["cleared", "confirmed_review_fraud"], p=[.93, .07])}[kind]
    cases.append(dict(case_id=f"C{i:04d}", category=rng.choice(["bags", "electronics", "beauty", "apparel", "footwear", "home"]),
                      statistical=v[0], linguistic=v[1], network=v[2], claims=v[3], visual=v[4], seller=v[5],
                      outcome=outcome, closed_on=days_ago(float(rng.uniform(30, 700))).date().isoformat()))

# ----------------------------------------------------------------------------------------------
# Write
# ----------------------------------------------------------------------------------------------
listed_map = {p[0]: p for p in PRODUCTS}
pd.DataFrame([dict(seller_id=s, name=n, account_created=days_ago(a).date().isoformat(), region=reg)
              for s, n, a, reg in SELLERS]).to_csv(DATA / "sellers.csv", index=False)
pd.DataFrame([dict(product_id=p, seller_id=s, title=t, category=c, listed_date=days_ago(l).date().isoformat(),
                   price_inr=b, image_file=im, description=desc)
              for p, s, t, c, l, b, im, desc in PRODUCTS]).to_csv(DATA / "products.csv", index=False)
pd.DataFrame(reviewers).to_csv(DATA / "reviewers.csv", index=False)
rv = pd.DataFrame(reviews).sample(frac=1, random_state=1)  # shuffle: ingestion must not rely on order
rv.to_csv(DATA / "reviews.csv", index=False)
pd.DataFrame(prices).to_csv(DATA / "price_history.csv", index=False)
pd.DataFrame(external).to_csv(DATA / "marketplace_listings.csv", index=False)
pd.DataFrame(seller_events).to_csv(DATA / "seller_events.csv", index=False)
pd.DataFrame(certs).to_csv(DATA / "certifications.csv", index=False)
pd.DataFrame(brands).to_csv(DATA / "brand_reference.csv", index=False)
pd.DataFrame(cases).to_csv(DATA / "case_history.csv", index=False)
pd.DataFrame(labels).to_csv(DATA / "ground_truth_reviews.csv", index=False)
(DATA / "ground_truth_products.json").write_text(json.dumps(
    {p[0]: GROUND_TRUTH.get(p[0], "clean") for p in PRODUCTS}, indent=2))
(DATA / "meta.json").write_text(json.dumps({"as_of": TODAY.isoformat()}, indent=2))

print(f"sellers={len(SELLERS)} products={len(PRODUCTS)} reviewers={len(reviewers)} reviews={len(reviews)}")
print(pd.DataFrame(reviews).groupby("product_id").size().to_string())
