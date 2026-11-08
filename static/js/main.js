/* Nara storefront — vanilla JS (menu, search, toasts, cart, product options, forms) */
(() => {
  "use strict";
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));

  /* ---------- toasts ---------- */
  function toast(message, type = "success") {
    const host = $("#toasts");
    if (!host) return;
    const el = document.createElement("div");
    el.className = `toast toast--${type}`;
    el.textContent = message;
    host.appendChild(el);
    setTimeout(() => {
      el.classList.add("is-leaving");
      setTimeout(() => el.remove(), 260);
    }, 3200);
  }
  window.naraToast = toast;
  $$("[data-flash]").forEach((n) => toast(n.textContent.trim(), n.dataset.type || "success"));

  /* ---------- cart badge ---------- */
  function setCartCount(n) {
    $$("[data-cart-count]").forEach((b) => { b.textContent = n; b.hidden = n <= 0; });
    $$("[data-cart-count-text]").forEach((b) => (b.textContent = n));
  }

  async function postJSON(url, body) {
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify(body),
    });
    let data = {};
    try { data = await res.json(); } catch (_) {}
    return { ok: res.ok && data.ok !== false, data };
  }

  async function addToBag(slug, color, size, qty, label) {
    try {
      const { ok, data } = await postJSON("/api/cart/add", { slug, color, size, qty });
      if (!ok) return toast(data.error || "Could not add to bag", "error");
      setCartCount(data.count);
      toast(label);
    } catch (_) {
      toast("Network error — please try again", "error");
    }
  }

  // quick-add buttons on product cards
  document.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-add-to-bag]");
    if (!btn) return;
    addToBag(btn.dataset.slug, btn.dataset.color, btn.dataset.size, 1, `${btn.dataset.name} added to bag`);
  });

  /* ---------- mobile drawer ---------- */
  const drawer = $("#mobile-menu");
  const backdrop = $("#drawer-backdrop");
  const openBtn = $("#menu-open");
  function setDrawer(open) {
    if (!drawer) return;
    drawer.classList.toggle("is-open", open);
    drawer.setAttribute("aria-hidden", String(!open));
    backdrop.hidden = !open;
    openBtn.setAttribute("aria-expanded", String(open));
    document.body.classList.toggle("no-scroll", open);
    if (open) $("#menu-close").focus(); else openBtn.focus({ preventScroll: true });
  }
  openBtn?.addEventListener("click", () => setDrawer(true));
  $("#menu-close")?.addEventListener("click", () => setDrawer(false));
  backdrop?.addEventListener("click", () => setDrawer(false));
  drawer?.addEventListener("click", (e) => { if (e.target.closest("a")) setDrawer(false); });
  window.matchMedia("(min-width: 768px)").addEventListener("change", (m) => { if (m.matches) setDrawer(false); });

  /* ---------- search panel ---------- */
  const sToggle = $("#search-toggle");
  const sPanel = $("#search-panel");
  function setSearch(open) {
    sPanel.hidden = !open;
    sToggle.setAttribute("aria-expanded", String(open));
    $("[data-open]", sToggle).hidden = open;
    $("[data-close]", sToggle).hidden = !open;
    if (open) $("#search-input").focus();
  }
  sToggle?.addEventListener("click", () => setSearch(sPanel.hidden));

  document.addEventListener("keydown", (e) => {
    if (e.key !== "Escape") return;
    if (drawer?.classList.contains("is-open")) setDrawer(false);
    else if (sPanel && !sPanel.hidden) setSearch(false);
  });

  /* ---------- shop sort ---------- */
  $("[data-autosubmit]")?.addEventListener("change", (e) => e.target.form.submit());

  /* ---------- product page options ---------- */
  const pdp = $("#pdp");
  if (pdp) {
    let color = $("[data-color].is-active", pdp)?.dataset.color || "";
    let size = $(".size.is-active", pdp)?.dataset.size || "";
    let qty = 1;
    const qtyEl = $("#qty-value");
    const plusButton = $("#qty-plus");
    const minusButton = $("#qty-minus");
    const addButton = $("#add-to-bag");

    function currentStock() {
      return Number($(".size.is-active", pdp)?.dataset.stock || 0);
    }

    function updateQuantityControls() {
      const stock = currentStock();
      qty = stock > 0 ? Math.max(1, Math.min(qty, stock)) : 1;
      qtyEl.textContent = qty;
      plusButton.disabled = qty >= stock;
      minusButton.disabled = qty <= 1;
      addButton.disabled = !size || stock < 1;
    }

    function selectSize(button) {
      size = button?.dataset.size || "";
      $$("#size-options .size").forEach((item) => {
        const selected = item === button;
        item.classList.toggle("is-active", selected);
        item.setAttribute("aria-pressed", String(selected));
      });
      updateQuantityControls();
    }

    $("#color-options")?.addEventListener("click", (e) => {
      const button = e.target.closest("[data-color]");
      if (!button) return;
      color = button.dataset.color;
      $$("#color-options .pill").forEach((item) => {
        const selected = item === button;
        item.classList.toggle("is-active", selected);
        item.setAttribute("aria-pressed", String(selected));
      });
      $("#color-label").textContent = color;

      const stocks = JSON.parse(button.dataset.stocks);
      let nextSize = null;
      $$("#size-options .size").forEach((item) => {
        item.dataset.stock = String(stocks[item.dataset.size] || 0);
        item.disabled = Number(item.dataset.stock) < 1;
        if (!nextSize && !item.disabled && item.dataset.size === size) nextSize = item;
      });
      if (!nextSize) nextSize = $("#size-options .size:not(:disabled)");
      qty = 1;
      selectSize(nextSize);
    });

    $("#size-options")?.addEventListener("click", (e) => {
      const b = e.target.closest("[data-size]");
      if (!b || b.disabled) return;
      selectSize(b);
    });

    minusButton.addEventListener("click", () => { qty = Math.max(1, qty - 1); updateQuantityControls(); });
    plusButton.addEventListener("click", () => { qty = Math.min(currentStock(), qty + 1); updateQuantityControls(); });

    addButton.addEventListener("click", () => {
      if (!size) return toast("Please choose a size", "error");
      addToBag(pdp.dataset.slug, color, size, qty, `${pdp.dataset.name} (${color}, ${size}) added to bag`);
    });
    updateQuantityControls();
  }

  /* ---------- product image gallery ---------- */
  const gallery = $("[data-gallery]");
  if (gallery) {
    const images = $$("[data-gallery-image]", gallery);
    const thumbnails = $$("[data-gallery-index]", gallery);
    const count = $("[data-gallery-count]", gallery);
    let activeIndex = 0;

    function showImage(index) {
      activeIndex = (index + images.length) % images.length;
      images.forEach((image, i) => { image.hidden = i !== activeIndex; });
      thumbnails.forEach((button, i) => {
        const active = i === activeIndex;
        button.classList.toggle("is-active", active);
        button.setAttribute("aria-pressed", String(active));
      });
      if (count) count.textContent = `${activeIndex + 1} / ${images.length}`;
    }

    $("[data-gallery-prev]", gallery)?.addEventListener("click", () => showImage(activeIndex - 1));
    $("[data-gallery-next]", gallery)?.addEventListener("click", () => showImage(activeIndex + 1));
    thumbnails.forEach((button) => {
      button.addEventListener("click", () => showImage(Number(button.dataset.galleryIndex)));
    });
  }

  /* ---------- forms (progressive enhancement; both work without JS) ---------- */
  const EMAIL = /^\S+@\S+\.\S+$/;

  $("#newsletter-form")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const form = e.currentTarget;
    const email = form.elements.email.value.trim();
    if (!EMAIL.test(email)) return toast("Please enter a valid email", "error");
    try {
      const { ok, data } = await postJSON(form.action, { email });
      if (!ok) return toast(data.error || "Something went wrong", "error");
      toast(data.message || "You're on the list!");
      form.reset();
    } catch (_) { toast("Network error — please try again", "error"); }
  });

  $("#contact-form")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const form = e.currentTarget;
    const f = form.elements;
    const body = { name: f.name.value.trim(), email: f.email.value.trim(), message: f.message.value.trim() };
    if (!body.name || !EMAIL.test(body.email) || body.message.length < 5) {
      return toast("Please fill in your name, a valid email and a message.", "error");
    }
    try {
      const { ok, data } = await postJSON(form.action, body);
      if (!ok) return toast(data.error || "Something went wrong", "error");
      toast(data.message || "Thanks! We'll reply within 24 hours.");
      form.reset();
    } catch (_) { toast("Network error — please try again", "error"); }
  });
})();
