"use strict";
(() => {
  const numberFormat = new Intl.NumberFormat("ru-RU", { maximumFractionDigits: 3 });
  for (const cell of document.querySelectorAll(".fish-weight[data-grams]")) {
    const grams = Number(cell.dataset.grams);
    cell.textContent = grams < 1000
      ? `${numberFormat.format(grams)} г`
      : `${numberFormat.format(grams / 1000)} кг`;
  }
})();
