"use strict";
(() => {
  const form = document.getElementById("records-filter-form");
  const daysInput = document.getElementById("records_days");
  if (!form || !daysInput) return;

  // Submit the current filters immediately when a period or select changes.
  // Using a GET form keeps selections shareable via the URL.
  const submit = () => {
    if (typeof form.requestSubmit === "function") form.requestSubmit();
    else form.submit();
  };

  for (const button of form.querySelectorAll("[data-record-days]")) {
    button.addEventListener("click", () => {
      if (button.dataset.recordDays === daysInput.value) return;
      daysInput.value = button.dataset.recordDays;
      submit();
    });
  }
  for (const select of form.querySelectorAll("select")) {
    select.addEventListener("change", submit);
  }
})();


// Show the bait disclosure only when the chips do not fit in one line.
(() => {
  const detailsNodes = [...document.querySelectorAll("[data-record-baits]")];
  if (!detailsNodes.length) return;

  const measure = (details) => {
    if (details.open) return;
    const summary = details.querySelector(".records-baits-summary");
    const preview = details.querySelector(".records-bait-preview");
    if (!summary || !preview || summary.clientWidth === 0) return;

    const chips = [...preview.querySelectorAll(":scope > .records-bait-item")];
    // Restore every chip before measuring: previously hidden chips must also
    // be considered when the viewport becomes wider.
    for (const chip of chips) chip.hidden = false;
    const gap = Number.parseFloat(getComputedStyle(preview).columnGap) || 0;
    const widths = chips.map((chip) => chip.getBoundingClientRect().width);
    const required = widths.reduce((total, width) => total + width, 0)
      + Math.max(0, chips.length - 1) * gap;

    // First test whether all bait chips fit without the disclosure control.
    const fits = required <= summary.clientWidth + 1;
    details.classList.toggle("records-baits-fit", fits);
    const toggle = details.querySelector(".records-bait-toggle");
    if (toggle) toggle.setAttribute("aria-hidden", String(fits));
    summary.setAttribute("aria-label", fits ? "Все наживки помещаются в строке" : "Развернуть список наживок");
    summary.tabIndex = fits ? -1 : 0;
    if (fits) return;

    // Reserve space for the Show chip, then retain only WHOLE bait chips.
    // A partially visible bait chip is more confusing than hiding it entirely.
    const available = preview.clientWidth;
    let used = 0;
    let hiddenRest = false;
    for (let i = 0; i < chips.length; i++) {
      const next = used + (i ? gap : 0) + widths[i];
      if (hiddenRest || next > available + 1) {
        chips[i].hidden = true;
        hiddenRest = true;
      } else {
        used = next;
      }
    }
  };

  // Keep the native details/summary interaction for keyboard and touch.
  for (const details of detailsNodes) {
    const summary = details.querySelector(".records-baits-summary");
    summary?.addEventListener("click", (event) => {
      if (details.classList.contains("records-baits-fit")) event.preventDefault();
    });
    details.addEventListener("toggle", () => {
      if (!details.open) requestAnimationFrame(() => measure(details));
      else summary?.setAttribute("aria-label", "Свернуть список наживок");
    });
  }

  const refresh = () => detailsNodes.forEach(measure);
  // Closed waterbody groups are initially width=0; remeasure when opened.
  for (const section of document.querySelectorAll(".records-waterbody")) {
    section.addEventListener("toggle", () => {
      if (section.open) requestAnimationFrame(refresh);
    });
  }
  if ("ResizeObserver" in window) {
    const observer = new ResizeObserver(() => requestAnimationFrame(refresh));
    for (const section of document.querySelectorAll(".records-waterbody")) observer.observe(section);
  } else {
    window.addEventListener("resize", refresh);
  }
  requestAnimationFrame(refresh);
})();
