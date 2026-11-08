# Nara — Women's Clothing Store (Flask)

HTML / CSS / JavaScript front end with a Python / Flask back end.
Converted from the original React + TanStack + Tailwind project; design, pages, copy and behaviour are unchanged.

## Run it

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
flask --app app db upgrade
flask --app app seed-catalog
flask --app app create-admin
python app.py                      # http://127.0.0.1:5000
```

Production: `SECRET_KEY=<long-random-string> SESSION_COOKIE_SECURE=1 gunicorn app:app`

## Structure

```
app.py               Flask routes, session cart, form/newsletter endpoints
models.py            SQLAlchemy product, product image, and color/size inventory models
data.py              Categories, FAQs, reviews, store info, and initial catalog data
migrations/          Flask-Migrate/Alembic database migrations
templates/           Jinja2 templates
  base.html            <head>, header, footer, toasts
  _macros.html         inline SVG icons (incl. social SVGs) + product card
  index / shop / product / cart / about / contact / 404 / 500 .html
static/css/style.css  All styling (design tokens + responsive breakpoints 640/768/1024)
static/js/main.js     Mobile menu, search, toasts, add-to-bag, product options, forms
static/img/           Product, lifestyle and logo images
instance/             SQLite database and runtime JSONL records
```

## Routes

| Route | Purpose |
|---|---|
| `/` | Home (hero, Find Your Style, about, trending, reviews, FAQ, store) |
| `/shop?category=&filter=new\|sale&q=&sort=` | Catalog with filters, search, sort |
| `/product/<slug>` | Product page |
| `/cart` | Bag, order summary, checkout |
| `/about`, `/contact` | Static pages / contact form |
| `/admin` | Admin login and product dashboard |
| `/admin/publish` | Create and publish a product |
| `/admin/products/<id>/edit` | Edit product, images, and inventory |
| `POST /api/cart/add` | JSON add-to-bag (used by the cards and product page) |
| `POST /cart/update`, `/cart/remove`, `/checkout` | Cart forms |
| `POST /newsletter`, `POST /contact` | Saved to `instance/*.jsonl` |

## Product catalog

The catalog is stored in SQLite by default (`instance/nara.sqlite`). Set
`DATABASE_URL` to use another SQLAlchemy database URL. `ProductImage` rows are
ordered for the product gallery; `ProductVariant` rows track stock for each
color/size combination. `price` is the current selling price, and optional
`compare_at` is the higher original price used to show a discount.

The initial catalog seed gives the demo products 99 units per color/size
combination. Future schema changes should use Flask-Migrate
(`flask --app app db migrate`, then `flask --app app db upgrade`).
Admin accounts are created only from the CLI with `flask --app app create-admin`;
there is no public admin signup. Sign in at `/admin` to manage drafts, inventory,
product images, discounts, and publishing.

## What changed vs. the React version

- **Cart** now lives in the Flask session (signed cookie) instead of `localStorage`.
  Quantities/removal are plain form posts, so they work without JavaScript.
- **Filtering/sorting/search** run on the server (`/shop?...`) instead of in the browser.
- **FAQ accordion** uses native `<details>`; **Find Your Style** tabs are links (`/?style=formal`).
- **Tailwind → hand-written CSS** in `style.css`, same colour tokens (oklch), same layout.
- **Icons** are inline SVGs (Lucide paths + the social SVGs); no icon library needed.
- Hero image converted PNG → WebP (1.7 MB → 80 KB).
- Checkout is still a demo (no payment): it saves the order to `instance/orders.jsonl`
  and empties the bag.

## Next steps

- Add protected admin screens for creating and editing products and uploading images.
- Add a payment provider (Stripe Checkout) in the `/checkout` route.
- Set a real `SECRET_KEY` in production.
