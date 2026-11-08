"""Nara — women's clothing store. Flask version of the original React/TanStack app."""
import json
import os
import re
import secrets
import unicodedata
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path

from flask import (Flask, abort, current_app, flash, jsonify, redirect,
                   render_template, request, session, url_for)
from flask_login import (LoginManager, current_user, login_required, login_user,
                         logout_user)
from flask_migrate import Migrate
from sqlalchemy import or_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import selectinload
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

import data
from models import AdminUser, Product, ProductImage, ProductVariant, db

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-only-change-me")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "DATABASE_URL", "sqlite:///nara.sqlite"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SECURE"] = os.environ.get(
    "SESSION_COOKIE_SECURE", "0"
).lower() in {"1", "true", "yes"}
app.config["SESSION_PERMANENT"] = True
app.config["PERMANENT_SESSION_LIFETIME"] = 60 * 60 * 24 * 30  # 30 days
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024
db.init_app(app)
Migrate(app, db)
login_manager = LoginManager(app)
login_manager.login_view = "admin"

INSTANCE = Path(app.instance_path)
INSTANCE.mkdir(parents=True, exist_ok=True)
EMAIL_RE = re.compile(r"^\S+@\S+\.\S+$")
ALLOWED_IMAGE_FORMATS = {
    ".jpg": "JPEG",
    ".jpeg": "JPEG",
    ".png": "PNG",
    ".webp": "WEBP",
}
MAX_PRODUCT_IMAGES = 8


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


@login_manager.user_loader
def load_admin(admin_id):
    try:
        return db.session.get(AdminUser, int(admin_id))
    except (TypeError, ValueError):
        return None


def csrf_token():
    token = session.get("_admin_csrf")
    if token is None:
        token = secrets.token_urlsafe(32)
        session["_admin_csrf"] = token
    return token


def validate_admin_csrf():
    expected = session.get("_admin_csrf", "")
    supplied = request.form.get("csrf_token", "")
    if not expected or not secrets.compare_digest(expected, supplied):
        abort(400, description="Invalid or missing form token.")


def admin_csrf_required(view):
    from functools import wraps

    @wraps(view)
    def wrapped(*args, **kwargs):
        validate_admin_csrf()
        return view(*args, **kwargs)

    return wrapped


def slugify(value):
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", normalized.lower()).strip("-")
    return slug[:120].strip("-")


def parse_list(value):
    return list(dict.fromkeys(item.strip() for item in value.split(",") if item.strip()))


def product_form_context(product=None, form_data=None, variant_rows=None, error=None):
    if product:
        initial = {
            "name": product.name,
            "category": product.category,
            "slug": product.slug,
            "price": str(product.price),
            "compare_at": str(product.compare_at) if product.compare_at is not None else "",
            "description": product.description,
            "details": "\n".join(product.details),
            "colors": ", ".join(product.colors),
            "sizes": ", ".join(product.sizes),
            "is_new": product.is_new,
            "is_published": product.is_published,
        }
    else:
        initial = {
            "name": "", "category": data.CATEGORIES[0]["id"], "slug": "",
            "price": "", "compare_at": "", "description": "", "details": "",
            "colors": "", "sizes": "", "is_new": False, "is_published": False,
        }
    initial.update(form_data or {})
    if variant_rows is None:
        variant_rows = [
            {"color": variant.color, "size": variant.size, "stock": variant.stock}
            for variant in (product.variants if product else [])
        ]
    return {
        "product": product,
        "form_data": initial,
        "variant_rows": variant_rows,
        "categories": data.CATEGORIES,
        "error": error,
    }


def validate_product_form(form):
    name = form.get("name", "").strip()
    category = form.get("category", "").strip()
    slug = slugify(form.get("slug", "").strip() or name)
    description = form.get("description", "").strip()
    details = [line.strip() for line in form.get("details", "").splitlines() if line.strip()]

    if not name or len(name) > 160:
        raise ValueError("Enter a product name up to 160 characters.")
    if not slug:
        raise ValueError("Enter a product name that can be used to create a URL.")
    if category not in data.CATEGORY_IDS:
        raise ValueError("Choose a valid product category.")
    if not description:
        raise ValueError("Enter a product description.")
    if len(description) > 5000 or any(len(detail) > 255 for detail in details):
        raise ValueError("The description or a product detail is too long.")

    try:
        price = Decimal(form.get("price", "").strip())
        compare_at_value = form.get("compare_at", "").strip()
        compare_at = Decimal(compare_at_value) if compare_at_value else None
    except InvalidOperation as error:
        raise ValueError("Enter valid prices.") from error
    if not price.is_finite() or price < 0 or price.as_tuple().exponent < -2:
        raise ValueError("Price must be a non-negative amount with at most two decimal places.")
    if compare_at is not None and (
        not compare_at.is_finite()
        or compare_at <= price
        or compare_at.as_tuple().exponent < -2
    ):
        raise ValueError("The original price must be greater than the selling price.")

    colors = parse_list(form.get("colors", ""))
    sizes = parse_list(form.get("sizes", ""))
    if not colors or len(colors) > 12 or any(len(color) > 80 for color in colors):
        raise ValueError("Enter between 1 and 12 colors (each up to 80 characters).")
    if not sizes or len(sizes) > 20 or any(len(size) > 40 for size in sizes):
        raise ValueError("Enter between 1 and 20 sizes (each up to 40 characters).")

    row_colors = form.getlist("variant_color")
    row_sizes = form.getlist("variant_size")
    row_stocks = form.getlist("variant_stock")
    if not (len(row_colors) == len(row_sizes) == len(row_stocks) == len(colors) * len(sizes)):
        raise ValueError("Inventory rows are incomplete. Check colors and sizes and try again.")

    variants = []
    seen = set()
    for color, size, stock_text in zip(row_colors, row_sizes, row_stocks):
        if color not in colors or size not in sizes or (color, size) in seen:
            raise ValueError("Inventory combinations do not match the selected colors and sizes.")
        try:
            stock = int(stock_text)
        except ValueError as error:
            raise ValueError("Stock must be a whole number.") from error
        if stock < 0 or stock > 1_000_000:
            raise ValueError("Stock must be between 0 and 1,000,000.")
        seen.add((color, size))
        variants.append({"color": color, "size": size, "stock": stock})

    images = [
        image for image in request.files.getlist("images")
        if image and image.filename
    ]
    remove_image_ids = set()
    for value in form.getlist("remove_image_ids"):
        try:
            remove_image_ids.add(int(value))
        except ValueError as error:
            raise ValueError("Invalid image selection.") from error
    return {
        "name": name,
        "category": category,
        "slug": slug,
        "price": price,
        "compare_at": compare_at,
        "description": description,
        "details": details,
        "colors": colors,
        "sizes": sizes,
        "variants": variants,
        "images": images,
        "remove_image_ids": remove_image_ids,
        "is_new": form.get("is_new") == "on",
        "is_published": form.get("intent") == "publish",
    }


def store_product_images(files):
    from PIL import Image, UnidentifiedImageError

    upload_dir = Path(app.static_folder) / "uploads" / "products"
    upload_dir.mkdir(parents=True, exist_ok=True)
    stored = []
    try:
        for upload in files:
            if len(stored) >= MAX_PRODUCT_IMAGES:
                raise ValueError(f"You can upload at most {MAX_PRODUCT_IMAGES} images per product.")
            extension = Path(secure_filename(upload.filename)).suffix.lower()
            expected_format = ALLOWED_IMAGE_FORMATS.get(extension)
            if not expected_format:
                raise ValueError("Images must be JPG, PNG, or WebP files.")
            path = upload_dir / f"{secrets.token_hex(16)}{extension}"
            upload.save(path)
            stored.append(path)
            try:
                with Image.open(path) as image:
                    if image.width * image.height > 40_000_000:
                        raise ValueError("Images must be smaller than 40 megapixels.")
                    image.verify()
                    if image.format != expected_format:
                        raise ValueError("The image file contents do not match its extension.")
            except (
                UnidentifiedImageError,
                OSError,
                SyntaxError,
                Image.DecompressionBombError,
            ) as error:
                raise ValueError("One of the uploaded files is not a valid image.") from error
        return stored
    except (OSError, ValueError):
        for path in stored:
            if path.exists():
                path.unlink()
        raise


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
        "csrf_token": csrf_token,
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


@app.cli.command("create-admin")
def create_admin():
    """Create an admin login without exposing a public signup route."""
    import click

    email = click.prompt("Admin email").strip().lower()
    if not EMAIL_RE.fullmatch(email) or len(email) > 255:
        raise click.ClickException("Enter a valid email address.")
    if AdminUser.query.filter_by(email=email).first():
        raise click.ClickException("An admin with that email already exists.")
    password = click.prompt(
        "Password (minimum 12 characters)",
        hide_input=True,
        confirmation_prompt=True,
    )
    if len(password) < 12:
        raise click.ClickException("The password must be at least 12 characters.")

    db.session.add(AdminUser(
        email=email,
        password_hash=generate_password_hash(password),
    ))
    db.session.commit()
    click.echo(f"Admin account created for {email}.")


@app.route("/admin", methods=["GET", "POST"])
def admin():
    if current_user.is_authenticated:
        if request.method == "POST":
            abort(405)
        products = Product.query.order_by(Product.name).all()
        return render_template("admin/dashboard.html", products=products)

    if request.method == "POST":
        validate_admin_csrf()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = AdminUser.query.filter_by(email=email).first()
        if user and check_password_hash(user.password_hash, password):
            cart = session.get("cart")
            session.clear()
            if cart is not None:
                session["cart"] = cart
            login_user(user)
            session.permanent = True
            return redirect(url_for("admin"))
        flash("The email or password was incorrect.", "error")

    csrf_token()
    return render_template(
        "admin/login.html",
        admin_email=request.form.get("email", ""),
    )


@app.post("/admin/logout")
@login_required
@admin_csrf_required
def admin_logout():
    logout_user()
    session.pop("_admin_csrf", None)
    flash("You have been signed out.", "success")
    return redirect(url_for("admin"))


@app.route("/admin/publish", methods=["GET", "POST"])
@login_required
def admin_publish():
    if request.method == "GET":
        return render_template(
            "admin/product_form.html",
            **product_form_context(),
        )
    validate_admin_csrf()
    return save_admin_product()


@app.route("/admin/products/<int:product_id>/edit", methods=["GET", "POST"])
@login_required
def admin_edit_product(product_id):
    product = db.get_or_404(Product, product_id)
    if request.method == "GET":
        return render_template(
            "admin/product_form.html",
            **product_form_context(product=product),
        )
    validate_admin_csrf()
    return save_admin_product(product)


def save_admin_product(product=None):
    form_data = request.form.to_dict()
    stored_paths = []
    removed_paths = []
    try:
        values = validate_product_form(request.form)
        duplicate = Product.query.filter(
            Product.slug == values["slug"],
            Product.id != (product.id if product else -1),
        ).first()
        if duplicate:
            raise ValueError("A product with this URL slug already exists.")

        remove_ids = values["remove_image_ids"]
        existing_images = list(product.images) if product else []
        if not remove_ids.issubset({image.id for image in existing_images}):
            raise ValueError("An image selection does not belong to this product.")
        kept_images = [image for image in existing_images if image.id not in remove_ids]
        if len(kept_images) + len(values["images"]) > MAX_PRODUCT_IMAGES:
            raise ValueError(f"A product can have at most {MAX_PRODUCT_IMAGES} images.")
        if not kept_images and not values["images"]:
            raise ValueError("Upload at least one product image.")

        stored_paths = store_product_images(values["images"])
        removed_paths = [image.path for image in existing_images if image.id in remove_ids]
        if product is None:
            product = Product()
            db.session.add(product)

        product.name = values["name"]
        product.category = values["category"]
        product.slug = values["slug"]
        product.price = values["price"]
        product.compare_at = values["compare_at"]
        product.description = values["description"]
        product.details = values["details"]
        product.is_new = values["is_new"]
        intent = request.form.get("intent")
        if intent == "publish":
            product.is_published = True
        elif intent == "draft":
            product.is_published = False

        for image in existing_images:
            if image.id in remove_ids:
                product.images.remove(image)
        for path in stored_paths:
            product.images.append(ProductImage(
                path=path.relative_to(Path(app.static_folder)).as_posix(),
                alt_text=values["name"],
                position=max((image.position for image in product.images), default=-1) + 1,
            ))
        variants_by_option = {
            (variant.color, variant.size): variant
            for variant in product.variants
        }
        desired_options = {
            (variant["color"], variant["size"]): variant
            for variant in values["variants"]
        }
        for option, variant in variants_by_option.items():
            if option not in desired_options:
                product.variants.remove(variant)
        for option, values_for_variant in desired_options.items():
            variant = variants_by_option.get(option)
            if variant:
                variant.stock = values_for_variant["stock"]
            else:
                product.variants.append(ProductVariant(
                    color=values_for_variant["color"],
                    size=values_for_variant["size"],
                    stock=values_for_variant["stock"],
                ))
        db.session.commit()
    except ValueError as error:
        return render_template(
            "admin/product_form.html",
            **product_form_context(
                product=product,
                form_data=form_data,
                variant_rows=[
                    {"color": color, "size": size, "stock": stock}
                    for color, size, stock in zip(
                        request.form.getlist("variant_color"),
                        request.form.getlist("variant_size"),
                        request.form.getlist("variant_stock"),
                    )
                ],
                error=str(error),
            ),
        ), 400
    except SQLAlchemyError:
        db.session.rollback()
        for path in stored_paths:
            if path.exists():
                path.unlink()
        current_app.logger.exception("Failed to save admin product.")
        flash("The product could not be saved. Please try again.", "error")
        return redirect(request.url)
    except OSError:
        db.session.rollback()
        current_app.logger.exception("Failed to store admin product images.")
        flash("Product images could not be saved. Please try again.", "error")
        return redirect(request.url)

    for relative_path in removed_paths:
        if relative_path.startswith("uploads/products/"):
            path = Path(app.static_folder) / relative_path
            if path.exists():
                try:
                    path.unlink()
                except OSError:
                    current_app.logger.exception(
                        "Could not remove deleted product image %s", path
                    )

    flash("Product saved.", "success")
    return redirect(url_for("admin"))


@app.post("/admin/products/<int:product_id>/publish")
@login_required
@admin_csrf_required
def admin_toggle_product(product_id):
    product = db.get_or_404(Product, product_id)
    product.is_published = not product.is_published
    db.session.commit()
    flash(
        f"{product.name} {'published' if product.is_published else 'unpublished'}.",
        "success",
    )
    return redirect(url_for("admin"))


# ---------------------------------------------------------------------- pages
@app.route("/")
def index():
    active = request.args.get("style", "all")
    if active not in data.CATEGORY_IDS:
        active = "all"
    query = Product.query.filter_by(is_published=True).options(
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

    query = Product.query.filter_by(is_published=True).options(
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
    ).filter_by(slug=slug, is_published=True).first()
    if not p:
        abort(404)
    same = Product.query.options(
        selectinload(Product.images), selectinload(Product.variants)
    ).filter(
        Product.slug != slug,
        Product.category == p.category,
        Product.is_published.is_(True),
    ).order_by(Product.id).all()
    other = Product.query.options(
        selectinload(Product.images), selectinload(Product.variants)
    ).filter(
        Product.category != p.category,
        Product.is_published.is_(True),
    ).order_by(Product.id).all()
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
        "currency": data.CURRENCY,
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
