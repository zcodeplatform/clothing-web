"""Nara — women's clothing store. Flask version of the original React/TanStack app."""
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

from flask import (Flask, abort, flash, jsonify, redirect, render_template,
                   request, session, url_for)

import data

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-only-change-me")
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_PERMANENT"] = True
app.config["PERMANENT_SESSION_LIFETIME"] = 60 * 60 * 24 * 30  # 30 days

INSTANCE = Path(app.instance_path)
INSTANCE.mkdir(parents=True, exist_ok=True)
EMAIL_RE = re.compile(r"^\S+@\S+\.\S+$")


# ---------------------------------------------------------------- cart helpers
def get_lines():
    return session.get("cart", [])


def save_lines(lines):
    session["cart"] = lines
    session.permanent = True


def cart_summary():
    items = []
    for line in get_lines():
        product = data.PRODUCT_INDEX.get(line["slug"])
        if product:
            items.append({**line, "product": product})
    subtotal = sum(i["product"]["price"] * i["qty"] for i in items)
    shipping = data.shipping_for(subtotal)
    return {
        "items": items,
        "count": sum(i["qty"] for i in items),
        "subtotal": subtotal,
        "shipping": shipping,
        "total": subtotal + shipping,
        "remaining": max(0, data.FREE_SHIPPING_THRESHOLD - subtotal),
    }


def valid_line(slug, size):
    p = data.PRODUCT_INDEX.get(slug)
    return p is not None and size in p["sizes"]


def add_to_cart(slug, size, qty):
    lines = get_lines()
    for l in lines:
        if l["slug"] == slug and l["size"] == size:
            l["qty"] = min(99, l["qty"] + qty)
            break
    else:
        lines.append({"slug": slug, "size": size, "qty": min(99, qty)})
    save_lines(lines)


def store_record(filename, record):
    record["at"] = datetime.now(timezone.utc).isoformat()
    with open(INSTANCE / filename, "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


# ------------------------------------------------------- template environment
@app.context_processor
def inject_globals():
    return {
        "CATEGORIES": data.CATEGORIES,
        "STORE": data.STORE,
        "SOCIALS": data.SOCIALS,
        "FREE_SHIPPING_THRESHOLD": data.FREE_SHIPPING_THRESHOLD,
        "cart_count": sum(l["qty"] for l in get_lines() if l["slug"] in data.PRODUCT_INDEX),
        "year": datetime.now().year,
    }


app.jinja_env.filters["price"] = data.format_price
app.jinja_env.globals["discount_percent"] = data.discount_percent


# ---------------------------------------------------------------------- pages
@app.route("/")
def index():
    active = request.args.get("style", "all")
    if active not in data.CATEGORY_IDS:
        active = "all"
    pool = data.PRODUCTS if active == "all" else [p for p in data.PRODUCTS if p["category"] == active]
    return render_template(
        "index.html",
        style_products=pool[:4],
        active_style=active,
        stats=data.STATS,
        faqs=data.FAQS,
        reviews=data.REVIEWS,
        tiles=data.TRENDING_TILES,
    )


@app.route("/shop")
def shop():
    category = request.args.get("category", "")
    category = category if category in data.CATEGORY_IDS else None
    flt = request.args.get("filter")
    flt = flt if flt in ("new", "sale") else None
    q = request.args.get("q", "").strip()[:100] or None
    sort = request.args.get("sort", "featured")
    sort = sort if sort in ("featured", "low", "high") else "featured"

    items = list(data.PRODUCTS)
    if category:
        items = [p for p in items if p["category"] == category]
    if flt == "new":
        items = [p for p in items if p.get("is_new")]
    if flt == "sale":
        items = [p for p in items if p.get("compare_at")]
    if q:
        t = q.lower()
        items = [p for p in items if t in f'{p["name"]} {p["description"]} {p["category"]}'.lower()]
    if sort == "low":
        items.sort(key=lambda p: p["price"])
    elif sort == "high":
        items.sort(key=lambda p: -p["price"])

    if q:
        title = f"Results for “{q}”"
    elif flt == "new":
        title = "New Arrival"
    elif flt == "sale":
        title = "Sale"
    elif category:
        title = data.CATEGORY_LABELS[category]
    else:
        title = "All Collection"

    return render_template("shop.html", products=items, title=title, category=category,
                           flt=flt, q=q, sort=sort)


@app.route("/product/<slug>")
def product(slug):
    p = data.PRODUCT_INDEX.get(slug)
    if not p:
        abort(404)
    same = [x for x in data.PRODUCTS if x["slug"] != slug and x["category"] == p["category"]]
    other = [x for x in data.PRODUCTS if x["category"] != p["category"]]
    return render_template("product.html", p=p, related=(same + other)[:4],
                           category_label=data.CATEGORY_LABELS[p["category"]])


@app.route("/about")
def about():
    return render_template("about.html", stats=data.STATS, values=data.VALUES, reviews=data.REVIEWS)


@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        payload = request.get_json(silent=True) or request.form
        name = (payload.get("name") or "").strip()[:100]
        email = (payload.get("email") or "").strip()[:255]
        message = (payload.get("message") or "").strip()[:1000]
        ok = bool(name) and bool(EMAIL_RE.match(email)) and len(message) >= 5
        if request.is_json:
            if not ok:
                return jsonify(ok=False, error="Please fill in your name, a valid email and a message."), 400
            store_record("messages.jsonl", {"name": name, "email": email, "message": message})
            return jsonify(ok=True, message="Thanks! We'll reply within 24 hours.")
        if not ok:
            flash("Please fill in your name, a valid email and a message.", "error")
        else:
            store_record("messages.jsonl", {"name": name, "email": email, "message": message})
            flash("Thanks! We'll reply within 24 hours.", "success")
        return redirect(url_for("contact"))
    return render_template("contact.html", faqs=data.FAQS)


@app.post("/newsletter")
def newsletter():
    payload = request.get_json(silent=True) or request.form
    email = (payload.get("email") or "").strip()[:255]
    if not EMAIL_RE.match(email):
        return jsonify(ok=False, error="Please enter a valid email"), 400
    store_record("subscribers.jsonl", {"email": email})
    return jsonify(ok=True, message="You're on the list!")


# ----------------------------------------------------------------------- cart
@app.route("/cart")
def cart():
    return render_template("cart.html", cart=cart_summary(), placed=session.pop("order_placed", False))


@app.post("/api/cart/add")
def api_cart_add():
    payload = request.get_json(silent=True) or {}
    slug, size = payload.get("slug"), payload.get("size")
    try:
        qty = max(1, min(99, int(payload.get("qty", 1))))
    except (TypeError, ValueError):
        qty = 1
    if not valid_line(slug, size):
        return jsonify(ok=False, error="Invalid product or size"), 400
    add_to_cart(slug, size, qty)
    return jsonify(ok=True, count=cart_summary()["count"])


@app.post("/cart/update")
def cart_update():
    slug, size = request.form.get("slug"), request.form.get("size")
    try:
        qty = int(request.form.get("qty", 1))
    except ValueError:
        qty = 1
    lines = []
    for l in get_lines():
        if l["slug"] == slug and l["size"] == size:
            l["qty"] = min(99, qty)
        if l["qty"] > 0:
            lines.append(l)
    save_lines(lines)
    return redirect(url_for("cart"))


@app.post("/cart/remove")
def cart_remove():
    slug, size = request.form.get("slug"), request.form.get("size")
    save_lines([l for l in get_lines() if not (l["slug"] == slug and l["size"] == size)])
    return redirect(url_for("cart"))


@app.post("/checkout")
def checkout():
    summary = cart_summary()
    if not summary["items"]:
        return redirect(url_for("cart"))
    store_record("orders.jsonl", {
        "items": [{"slug": i["slug"], "size": i["size"], "qty": i["qty"]} for i in summary["items"]],
        "total": summary["total"],
    })
    save_lines([])
    session["order_placed"] = True
    flash("Order placed!", "success")
    return redirect(url_for("cart"))


# --------------------------------------------------------------------- errors
@app.errorhandler(404)
def not_found(_e):
    return render_template("404.html"), 404


@app.errorhandler(500)
def server_error(_e):
    return render_template("500.html"), 500


if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG", "1") == "1", port=int(os.environ.get("PORT", 5000)), host="0.0.0.0")
