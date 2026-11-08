"""Static catalog and site content (replaces src/data/products.ts).

Move PRODUCTS to a database (SQLite/SQLAlchemy) before adding admin editing.
"""

CATEGORIES = [
    {"id": "sweatwear", "label": "Sweatwear"},
    {"id": "formal", "label": "Formal Wear"},
    {"id": "casual", "label": "Casual Comfort"},
    {"id": "active", "label": "Sports & Active"},
    {"id": "accessories", "label": "Accessories"},
    {"id": "tshirt", "label": "T-Shirt"},
    {"id": "bottoms", "label": "Bottoms"},
]
CATEGORY_IDS = {c["id"] for c in CATEGORIES}
CATEGORY_LABELS = {c["id"]: c["label"] for c in CATEGORIES}

SIZES = ["XS", "S", "M", "L", "XL"]

FREE_SHIPPING_THRESHOLD = 150
SHIPPING_FEE = 10

PRODUCTS = [
    {
        "slug": "jeans-and-white-tee", "name": "Jeans & Classic Tee", "category": "tshirt",
        "price": 85, "compare_at": 120, "image": "p-white-tee.jpg",
        "colors": ["White", "Light Wash"], "sizes": SIZES,
        "description": "A relaxed crew-neck tee in heavyweight organic cotton, styled with our high-rise straight jeans. The everyday uniform, perfected.",
        "details": ["100% organic cotton tee", "High-rise straight denim", "Machine wash cold"],
    },
    {
        "slug": "polka-long-sleeve-blouse", "name": "Polka Long Sleeve Blouse", "category": "casual",
        "price": 85, "compare_at": 120, "image": "p-polka-blouse.jpg",
        "colors": ["Burgundy"], "sizes": SIZES,
        "description": "Fluid crepe blouse with a soft collar, puff shoulders and gathered cuffs. Dresses up with tailoring or down with denim.",
        "details": ["Lightweight crepe", "Button front", "Gathered elastic cuffs"],
    },
    {
        "slug": "camel-tailored-blazer", "name": "Camel Tailored Blazer", "category": "formal",
        "price": 145, "compare_at": 190, "image": "p-camel-blazer.jpg", "is_new": True,
        "colors": ["Camel", "Black"], "sizes": SIZES,
        "description": "A sharply cut single-breasted blazer with structured shoulders and a softly nipped waist. Pair with the matching trousers.",
        "details": ["Wool-blend twill", "Fully lined", "Dry clean only"],
    },
    {
        "slug": "satin-wrap-shirt", "name": "Satin Wrap Shirt", "category": "formal",
        "price": 95, "image": "p-brown-shirt.jpg", "is_new": True,
        "colors": ["Chocolate", "Ivory"], "sizes": SIZES,
        "description": "Liquid satin wrap shirt with a tie waist and a deep V collar. Effortless glow from desk to dinner.",
        "details": ["Silky satin", "Side tie closure", "Hand wash"],
    },
    {
        "slug": "oatmeal-lounge-set", "name": "Oatmeal Lounge Set", "category": "sweatwear",
        "price": 110, "compare_at": 140, "image": "p-oat-hoodie.jpg",
        "colors": ["Oatmeal", "Charcoal"], "sizes": SIZES,
        "description": "Brushed-back fleece hoodie and jogger set in a calming oatmeal melange. Made for slow mornings and long-haul flights.",
        "details": ["Cotton fleece", "Kangaroo pocket", "Elastic cuffs"],
    },
    {
        "slug": "sage-active-set", "name": "Sage Active Set", "category": "active",
        "price": 78, "image": "p-active-set.jpg", "is_new": True,
        "colors": ["Sage", "Black"], "sizes": SIZES,
        "description": "Sculpting racerback bra and high-waist leggings in a buttery four-way stretch fabric. Squat-proof and sweat-wicking.",
        "details": ["Four-way stretch", "Medium support", "Hidden waist pocket"],
    },
    {
        "slug": "tan-leather-top-handle", "name": "Tan Leather Top Handle", "category": "accessories",
        "price": 160, "compare_at": 210, "image": "p-leather-bag.jpg",
        "colors": ["Tan"], "sizes": ["One Size"],
        "description": "A structured top-handle bag in smooth leather with polished gold hardware. Silk scarf included.",
        "details": ["Genuine leather", "Gold-tone turn lock", "Includes silk scarf"],
    },
    {
        "slug": "wide-leg-pleated-trousers", "name": "Wide Leg Pleated Trousers", "category": "bottoms",
        "price": 92, "image": "p-wide-trousers.jpg",
        "colors": ["Cream", "Black"], "sizes": SIZES,
        "description": "High-rise pleated trousers that skim the floor. Tailored at the waist, fluid through the leg.",
        "details": ["Soft drape twill", "Front pleats", "Side pockets"],
    },
    {
        "slug": "black-satin-slip-dress", "name": "Black Satin Slip Dress", "category": "formal",
        "price": 130, "compare_at": 165, "image": "p-black-dress.jpg",
        "colors": ["Black"], "sizes": SIZES,
        "description": "Bias-cut midi slip dress with a cowl neckline and delicate adjustable straps. Evening, sorted.",
        "details": ["Bias-cut satin", "Adjustable straps", "Midi length"],
    },
    {
        "slug": "coral-cargo-pants", "name": "Coral Cargo Pants", "category": "bottoms",
        "price": 70, "image": "t-street.jpg", "is_new": True,
        "colors": ["Coral", "Stone"], "sizes": SIZES,
        "description": "Washed cotton cargo pants with a relaxed straight leg and roomy utility pockets. Street-ready in seconds.",
        "details": ["Washed cotton twill", "Six pockets", "Relaxed fit"],
    },
    {
        "slug": "sand-wool-overcoat", "name": "Sand Wool Overcoat", "category": "formal",
        "price": 220, "compare_at": 280, "image": "t-coat.jpg",
        "colors": ["Sand", "Camel"], "sizes": SIZES,
        "description": "An oversized long overcoat in brushed wool with wide notch lapels. Winter gear that actually works.",
        "details": ["Wool blend", "Dropped shoulders", "Two welt pockets"],
    },
    {
        "slug": "linen-v-neck-tank", "name": "Linen V-Neck Tank", "category": "casual",
        "price": 48, "image": "t-everyday.jpg",
        "colors": ["White", "Natural"], "sizes": SIZES,
        "description": "Breathable washed linen tank with a soft swing shape. The easiest thing you'll wear all summer.",
        "details": ["100% linen", "Relaxed swing fit", "Machine wash"],
    },
    {
        "slug": "crisp-poplin-shirt", "name": "Crisp Poplin Shirt", "category": "formal",
        "price": 75, "compare_at": 95, "image": "t-tailored.jpg",
        "colors": ["White", "Blue"], "sizes": SIZES,
        "description": "A classic button-down in crisp cotton poplin, cut slightly relaxed for tucking or wearing loose.",
        "details": ["Cotton poplin", "Mother-of-pearl buttons", "Machine wash"],
    },
]

PRODUCT_INDEX = {p["slug"]: p for p in PRODUCTS}

STORE = {
    "name": "Eclothing, NYC",
    "address": "123 Fashion Street, New York, NY",
    "email": "hello@Eclothing.store",
    "phone": "+1 212 555 0147",
    "hours": "Mon – Sat, 10am – 8pm",
    "map_url": "https://maps.google.com/?q=New+York+NY",
}

STATS = [
    {"value": "10K+", "label": "Happy Customers"},
    {"value": "10+", "label": "Years of Excellence"},
    {"value": "90%", "label": "Satisfaction Rate"},
]

FAQS = [
    {"q": "How long does delivery take?", "a": "Orders are dispatched within 24 hours. Standard delivery takes 2–5 business days, and orders over $150 ship free."},
    {"q": "What is your return policy?", "a": "You can return unworn items with tags within 30 days for a full refund or exchange. Returns are free for store credit."},
    {"q": "How do I find my size?", "a": "Each product page lists the fit and fabric. Our pieces run true to size — if you're between sizes, we recommend sizing up for a relaxed fit."},
    {"q": "Do you ship internationally?", "a": "Yes, we ship to over 40 countries. Duties and taxes are calculated at checkout so there are no surprises on delivery."},
    {"q": "Can I change or cancel my order?", "a": "Reach out within 2 hours of placing your order and our customer care team will update or cancel it for you."},
]

REVIEWS = [
    {"name": "Courtney Henry", "place": "Florida, USA", "image": "review-1.jpg",
     "text": "The gently curved lines and soft fabrics feel made for my body. I've worn the camel blazer to work three times this week — people keep asking where it's from."},
    {"name": "Amara Okafor", "place": "Lagos, Nigeria", "image": "review-2.jpg",
     "text": "Gorgeous quality and the fit is spot on. Delivery was quick, the packaging was beautiful, and the satin wrap shirt is now my favourite thing in my wardrobe."},
]

TRENDING_TILES = [
    {"title": "Street-Ready Styles", "image": "t-street.jpg", "span": "md-3", "args": {"category": "bottoms"}},
    {"title": "Fresh Picks Only", "image": "t-coat.jpg", "span": "md-2", "args": {"filter": "new"}},
    {"title": "Everyday Classics", "image": "t-everyday.jpg", "span": "md-2", "args": {"category": "casual"}},
    {"title": "Tailored to Impress", "image": "t-tailored.jpg", "span": "md-3", "args": {"category": "formal"}, "badge": "20% OFF"},
]

VALUES = [
    {"icon": "ruler", "title": "Fit first", "text": "Every pattern is tested on real bodies across our full size range before it goes into production."},
    {"icon": "leaf", "title": "Better fabrics", "text": "Organic cotton, responsible wool and long-lasting blends chosen to be worn for years."},
    {"icon": "sparkles", "title": "Quiet details", "text": "Tailored seams, hidden pockets and finishing touches you'll notice every time you wear it."},
]

SOCIALS = [
    {"label": "Instagram", "href": "https://instagram.com", "icon": "instagram"},
    {"label": "Facebook", "href": "https://facebook.com", "icon": "facebook"},
    {"label": "X", "href": "https://x.com", "icon": "x"},
    {"label": "TikTok", "href": "https://tiktok.com", "icon": "tiktok"},
    {"label": "Pinterest", "href": "https://pinterest.com", "icon": "pinterest"},
]


def discount_percent(p):
    if not p.get("compare_at"):
        return 0
    return round((p["compare_at"] - p["price"]) / p["compare_at"] * 100)


def format_price(n):
    return f"${n:.0f}"


def shipping_for(subtotal):
    if subtotal == 0:
        return 0
    return 0 if subtotal >= FREE_SHIPPING_THRESHOLD else SHIPPING_FEE
