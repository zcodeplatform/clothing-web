# Nara — Women's Clothing Store (Flask)

HTML / CSS / JavaScript front end with a Python / Flask back end.
Converted from the original React + TanStack + Tailwind project; design, pages, copy and behaviour are unchanged.

## Run it

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python app.py                      # http://127.0.0.1:5000
```

Production: `SECRET_KEY=<long-random-string> gunicorn app:app`

## Structure

```
app.py               Flask routes, session cart, form/newsletter endpoints
data.py              Catalog, categories, FAQs, reviews, store info (was src/data/products.ts)
templates/           Jinja2 templates
  base.html            <head>, header, footer, toasts
  _macros.html         inline SVG icons (incl. social SVGs) + product card
  index / shop / product / cart / about / contact / 404 / 500 .html
  partials/            header, footer, faq, reviews
static/css/style.css  All styling (design tokens + responsive breakpoints 640/768/1024)
static/js/main.js     Mobile menu, search, toasts, add-to-bag, product options, forms
static/img/           Product, lifestyle and logo images
instance/             Created at runtime: messages.jsonl, subscribers.jsonl, orders.jsonl
```

## Routes

| Route | Purpose |
|---|---|
| `/` | Home (hero, Find Your Style, about, trending, reviews, FAQ, store) |
| `/shop?category=&filter=new\|sale&q=&sort=` | Catalog with filters, search, sort |
| `/product/<slug>` | Product page |
| `/cart` | Bag, order summary, checkout |
| `/about`, `/contact` | Static pages / contact form |
| `POST /api/cart/add` | JSON add-to-bag (used by the cards and product page) |
| `POST /cart/update`, `/cart/remove`, `/checkout` | Cart forms |
| `POST /newsletter`, `POST /contact` | Saved to `instance/*.jsonl` |

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

- Move `PRODUCTS` from `data.py` into SQLite/SQLAlchemy before adding an admin area.
- Add a payment provider (Stripe Checkout) in the `/checkout` route.
- Set a real `SECRET_KEY` in production.
