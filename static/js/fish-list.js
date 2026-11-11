"use strict";
(() => {
  const root = document.getElementById("fish-reference");
  if (!root) return;
  const search = document.getElementById("fish-name-filter");
  const sorting = document.getElementById("fish-sort");
  const filters = [...document.querySelectorAll("#fish-rarity-filters button[data-rarity]")];
  const body = document.getElementById("fish-table-body");
  const rows = [...body.querySelectorAll("tr[data-rarity]")];
  const count = document.getElementById("fish-result-count");
  const empty = document.getElementById("fish-empty-result");
  const collator = new Intl.Collator("ru", { sensitivity: "base", numeric: true });
  const formatNumber = new Intl.NumberFormat("ru-RU", { maximumFractionDigits: 3 });
  let activeRarity = "all";

  function formatWeight(grams) {
    return grams < 1000 ? `${formatNumber.format(grams)} г` : `${formatNumber.format(grams / 1000)} кг`;
  }
  for (const cell of body.querySelectorAll(".fish-weight[data-grams]")) {
    cell.textContent = formatWeight(Number(cell.dataset.grams));
  }

  function sortRows() {
    const mode = sorting.value;
    rows.sort((a, b) => {
      const nameOrder = collator.compare(a.dataset.name, b.dataset.name);
      if (mode === "name") return nameOrder;
      if (mode === "name-desc") return -nameOrder;
      if (mode.startsWith("trophy")) {
        const delta = Number(a.dataset.trophy) - Number(b.dataset.trophy);
        return (mode.endsWith("desc") ? -delta : delta) || nameOrder;
      }
      if (mode.startsWith("rarity")) {
        const delta = Number(a.dataset.rarity) - Number(b.dataset.rarity);
        return (mode.endsWith("desc") ? -delta : delta) || nameOrder;
      }
      return nameOrder;
    });
    body.append(...rows);
  }

  function applyFilters() {
    const needle = search.value.trim().toLocaleLowerCase("ru");
    let visible = 0;
    for (const row of rows) {
      const show = row.dataset.name.includes(needle) && (activeRarity === "all" || row.dataset.rarity === activeRarity);
      row.hidden = !show;
      if (show) visible++;
    }
    count.textContent = `Видов: ${visible}`;
    empty.classList.toggle("d-none", visible > 0);
  }

  for (const button of filters) {
    button.addEventListener("click", () => {
      activeRarity = button.dataset.rarity;
      for (const option of filters) {
        const selected = option === button;
        option.setAttribute("aria-pressed", String(selected));
        option.classList.toggle("btn-primary", selected);
        option.classList.toggle("btn-outline-secondary", !selected);
      }
      applyFilters();
    });
  }
  search.addEventListener("input", applyFilters);
  sorting.addEventListener("change", sortRows);
  sortRows();
  applyFilters();
})();
