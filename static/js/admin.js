(() => {
  "use strict";
  const form = document.querySelector("#admin-product-form");
  if (!form) return;

  const colorInput = form.querySelector("#admin-colors");
  const sizeInput = form.querySelector("#admin-sizes");
  const rows = form.querySelector("#admin-inventory-rows");
  const stockByVariant = new Map(
    (window.adminInitialVariants || []).map((variant) => [
      JSON.stringify([variant.color, variant.size]),
      variant.stock,
    ]),
  );

  function values(input) {
    return [...new Set(input.value.split(",").map((value) => value.trim()).filter(Boolean))];
  }

  function addHidden(cell, name, value) {
    const input = document.createElement("input");
    input.type = "hidden";
    input.name = name;
    input.value = value;
    cell.append(input);
  }

  function renderInventory() {
    const colors = values(colorInput);
    const sizes = values(sizeInput);
    rows.replaceChildren();

    for (const color of colors) {
      for (const size of sizes) {
        const key = JSON.stringify([color, size]);
        const row = document.createElement("tr");
        const colorCell = document.createElement("td");
        const sizeCell = document.createElement("td");
        const stockCell = document.createElement("td");
        const stockInput = document.createElement("input");

        colorCell.textContent = color;
        sizeCell.textContent = size;
        addHidden(colorCell, "variant_color", color);
        addHidden(sizeCell, "variant_size", size);
        stockInput.type = "number";
        stockInput.name = "variant_stock";
        stockInput.min = "0";
        stockInput.max = "1000000";
        stockInput.step = "1";
        stockInput.required = true;
        stockInput.value = String(stockByVariant.get(key) ?? 0);
        stockInput.setAttribute("aria-label", `${color}, size ${size}, items in stock`);
        stockInput.addEventListener("input", () => {
          stockByVariant.set(key, stockInput.value);
        });
        stockCell.append(stockInput);
        row.append(colorCell, sizeCell, stockCell);
        rows.append(row);
      }
    }
  }

  colorInput.addEventListener("change", renderInventory);
  sizeInput.addEventListener("change", renderInventory);
  renderInventory();
})();
