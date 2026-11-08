"""Nara — women's clothing store. Flask version of the original React/TanStack app."""
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

from flask import (Flask, abort, current_app, flash, jsonify, redirect,
                   render_template, request, session, url_for)
from flask_migrate import Migrate
from sqlalchemy import or_
from sqlalchemy.orm import selectinload

import data
from models import Product, ProductImage, ProductVariant, db

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-only-change-me")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "DATABASE_URL", "sqlite:///nara.sqlite"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_PERMANENT"] = True
app.config["PERMANENT_SESSION_LIFETIME"] = 60 * 60 * 24 * 30  # 30 days
db.init_app(app)
Migrate(app, db)

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
    lines = get_lines()
    slugs = {line["slug"] for line in lines}
    products = Product.query.options(
        selectinload(Product.images), selectinload(Product.variants)
    ).filter(Product.slug.in_(slugs)).all() if slugs else []
    product_by_slug = {product.slug: product for product in products}

    for line in lines:
        product = product_by_slug.get(line["slug"])
        if not product:
            continue
        color = line.get("color")
        variant = product.variant_for(color, line["size"]) if color else None
        if variant is None:
            variant = next(
                (item for item in product.variants if item.size == line["size"]),
                None,
            )
        if variant is None:
            continue
        item = {**line, "color": variant.color, "product": product, "variant": variant}
        items.append(item)

    subtotal = sum((item["product"].price * item["qty"] for item in items), start=0)
    shipping = data.shipping_for(subtotal)
    return {
        "items": items,
        "count": sum(i["qty"] for i in items),
        "subtotal": subtotal,
        "shipping": shipping,
        "total": subtotal + shipping,
        "remaining": max(0, data.FREE_SHIPPING_THRESHOLD - subtotal),
    }


def valid_line(slug, size, color=None):
    query = ProductVariant.query.join(Product).filter(
        Product.slug == slug, ProductVariant.size == size
    )
    if color:
        query = query.filter(ProductVariant.color == color)
    else:
        query = query.order_by(ProductVariant.id)
    return query.first()


def add_to_cart(slug, size, color, qty):
    variant = ProductVariant.query.join(Product).filter(
        Product.slug == slug,
        ProductVariant.size == size,
        ProductVariant.color == color,
    ).first()
    if variant is None or variant.stock < 1:
        return False

    lines = get_lines()
    for l in lines:
        if l["slug"] == slug and l["size"] == size and l.get("color") == color:
            l["qty"] = min(variant.stock, l["qty"] + qty)
            break
    else:
        lines.append({
            "slug": slug,
            "size": size,
            "color": color,
            "qty": min(variant.stock, qty),
        })
    save_lines(lines)
    return True


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
        "cart_count": cart_summary()["count"],
        "year": datetime.now().year,
    }


app.jinja_env.filters["price"] = data.format_price
app.jinja_env.globals["discount_percent"] = data.discount_percent


@app.cli.command("seed-catalog")
def seed_catalog():
    """Insert the bundled demo catalog into an initialized database."""
    for item in data.PRODUCTS:
        if Product.query.filter_by(slug=item["slug"]).first():
            continue

        product = Product(
            slug=item["slug"],
            name=item["name"],
            category=item["category"],
            price=item["price"],
            compare_at=item.get("compare_at"),
            description=item["description"],
            details=item["details"],
            is_new=item.get("is_new", False),
        )
        product.images.append(ProductImage(
            path=f"img/{item['image']}",
            alt_text=item["name"],
            position=0,
        ))
        for color in item["colors"]:
            for size in item["sizes"]:
                product.variants.append(ProductVariant(
                    color=color,
                    size=size,
                    stock=99,
                ))
        db.session.add(product)

    db.session.commit()
    current_app.logger.info("Bundled product catalog seeded.")


# ---------------------------------------------------------------------- pages
@app.route("/")
def index():
    active = request.args.get("style", "all")
    if active not in data.CATEGORY_IDS:
        active = "all"
    query = Product.query.options(
        selectinload(Product.images), selectinload(Product.variants)
    )
    if active != "all":
        query = query.filter_by(category=active)
    pool = query.order_by(Product.id).all()
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

    query = Product.query.options(
        selectinload(Product.images), selectinload(Product.variants)
    )
    if category:
        query = query.filter_by(category=category)
    if flt == "new":
        query = query.filter_by(is_new=True)
    if flt == "sale":
        query = query.filter(Product.compare_at.isnot(None))
    if q:
        term = f"%{q}%"
        query = query.filter(or_(
            Product.name.ilike(term),
            Product.description.ilike(term),
            Product.category.ilike(term),
        ))
    if sort == "low":
        query = query.order_by(Product.price.asc(), Product.id)
    elif sort == "high":
        query = query.order_by(Product.price.desc(), Product.id)
    else:
        query = query.order_by(Product.id)
    items = query.all()

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
    p = Product.query.options(
        selectinload(Product.images), selectinload(Product.variants)
    ).filter_by(slug=slug).first()
    if not p:
        abort(404)
    same = Product.query.options(
        selectinload(Product.images), selectinload(Product.variants)
    ).filter(Product.slug != slug, Product.category == p.category).order_by(Product.id).all()
    other = Product.query.options(
        selectinload(Product.images), selectinload(Product.variants)
    ).filter(Product.category != p.category).order_by(Product.id).all()
    return render_template("product.html", p=p, related=(same + other)[:4],
                           category_label=data.CATEGORY_LABELS[p.category])


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
    slug, size, color = payload.get("slug"), payload.get("size"), payload.get("color")
    try:
        qty = max(1, min(99, int(payload.get("qty", 1))))
    except (TypeError, ValueError):
        qty = 1
    variant = valid_line(slug, size, color)
    if variant is None or variant.stock < 1:
        return jsonify(ok=False, error="Invalid product or size"), 400
    if qty > variant.stock:
        return jsonify(ok=False, error=f"Only {variant.stock} available"), 400
    if not add_to_cart(slug, size, variant.color, qty):
        return jsonify(ok=False, error="This option is out of stock"), 400
    return jsonify(ok=True, count=cart_summary()["count"])


@app.post("/cart/update")
def cart_update():
    slug, size = request.form.get("slug"), request.form.get("size")
    color = request.form.get("color")
    try:
        qty = int(request.form.get("qty", 1))
    except ValueError:
        qty = 1
    lines = []
    for l in get_lines():
        if (l["slug"] == slug and l["size"] == size
                and (not color or l.get("color") in (None, color))):
            variant = valid_line(slug, size, color or l.get("color"))
            l["qty"] = min(variant.stock, qty) if variant else 0
        if l["qty"] > 0:
            lines.append(l)
    save_lines(lines)
    return redirect(url_for("cart"))


@app.post("/cart/remove")
def cart_remove():
    slug, size, color = (
        request.form.get("slug"),
        request.form.get("size"),
        request.form.get("color"),
    )
    save_lines([
        line for line in get_lines()
        if not (
            line["slug"] == slug
            and line["size"] == size
            and (not color or line.get("color") in (None, color))
        )
    ])
    return redirect(url_for("cart"))


@app.post("/checkout")
def checkout():
    summary = cart_summary()
    if not summary["items"]:
        return redirect(url_for("cart"))
    for item in summary["items"]:
        variant = item["variant"]
        if variant.stock < item["qty"]:
            flash(
                f"Only {variant.stock} of {item['product'].name} "
                f"({variant.color}, {variant.size}) remain in stock.",
                "error",
            )
            return redirect(url_for("cart"))

    store_record("orders.jsonl", {
        "items": [
            {
                "slug": item["slug"],
                "color": item["color"],
                "size": item["size"],
                "qty": item["qty"],
            }
            for item in summary["items"]
        ],
        "total": float(summary["total"]),
    })
    for item in summary["items"]:
        item["variant"].stock -= item["qty"]
    db.session.commit()
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
