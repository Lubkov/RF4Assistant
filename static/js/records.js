"use strict";
(() => {
  const panel = document.getElementById("fish-records-panel");
  if (!panel) return;

  const title = panel.querySelector("#fish-records-title");
  const count = panel.querySelector("#fish-records-count");
  const date = panel.querySelector("#fish-records-date");
  const weight = panel.querySelector("#fish-records-weight");
  const filter = panel.querySelector("#fish-records-bait-filter");
  const summary = panel.querySelector("#fish-records-summary");
  const details = panel.querySelector("#fish-records-details");
  const summaryBody = summary.tBodies[0];
  const detailsBody = details.tBodies[0];
  const scrollArea = panel.querySelector(".offcanvas-body");
  let rows = [];
  let selectedRow;
  let selectedBait;
  let sortButton = weight;

  const showRows = () => {
    const showSummary = selectedBait === undefined;
    summary.hidden = !showSummary;
    details.hidden = showSummary;
    scrollArea.scrollTop = 0;
    if (showSummary) {
      count.textContent = `Записей: ${rows.length}`;
      return;
    }

    for (const button of [date, weight]) {
      button.closest("th").removeAttribute("aria-sort");
    }
    sortButton.closest("th").setAttribute("aria-sort", "descending");
    const visibleRows = rows.filter((row) =>
      [...row.querySelectorAll("[data-record-bait]")].some((bait) =>
        bait.dataset.recordBait === selectedBait));
    if (sortButton === date) {
      visibleRows.sort((first, second) =>
        second.dataset.caughtDate.localeCompare(first.dataset.caughtDate));
    }
    detailsBody.replaceChildren(...visibleRows);
    count.textContent = `Записей: ${visibleRows.length}`;
  };

  const filterByBait = (bait) => {
    selectedBait = bait;
    filter.hidden = bait === undefined;
    filter.firstElementChild.textContent = bait ?? "";
    filter.setAttribute("aria-label", `Снять фильтр по приманке «${bait ?? ""}»`);
    showRows();
  };

  panel.addEventListener("show.bs.offcanvas", (event) => {
    const trigger = event.relatedTarget;
    const row = trigger?.closest("tr");
    const records = row?.querySelector("[data-fish-records]");
    if (!records) return;

    selectedRow = row;
    selectedRow.classList.add("table-active");
    title.textContent = row.querySelector(".records-fish-trigger").textContent.trim();
    summaryBody.replaceChildren(row.querySelector("[data-fish-bait-summary]").content.cloneNode(true));
    detailsBody.replaceChildren();
    rows = [...records.content.cloneNode(true).querySelectorAll("tr")];
    sortButton = weight;
    filterByBait(trigger.dataset.recordBait);
  });

  panel.addEventListener("hidden.bs.offcanvas", () => {
    selectedRow?.classList.remove("table-active");
  });

  for (const button of [date, weight]) {
    button.addEventListener("click", () => {
      sortButton = button;
      showRows();
    });
  }

  filter.addEventListener("click", () => {
    filterByBait(undefined);
    scrollArea.focus();
  });
  scrollArea.addEventListener("click", (event) => {
    const bait = event.target.closest("[data-record-bait]");
    if (!bait) return;

    filterByBait(bait.dataset.recordBait);
    filter.focus();
  });

  scrollArea.addEventListener("mouseover", (event) => {
    const label = event.target.closest("[data-record-truncate]");
    if (!label) return;

    if (label.scrollWidth > label.clientWidth) {
      label.title = label.textContent.trim();
    } else {
      label.removeAttribute("title");
    }
  });
})();

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
  const regionInput = document.getElementById("region");
  for (const option of document.querySelectorAll("[data-record-region]")) {
    option.addEventListener("click", () => {
      if (!regionInput || regionInput.value === option.dataset.recordRegion) return;
      regionInput.value = option.dataset.recordRegion;
      submit();
    });
  }
})();


// Show the disclosure only when bait or fish chips do not fit in one line.
(() => {
  const detailsNodes = [...document.querySelectorAll("[data-record-expand]")];
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

    // First test whether all chips fit without the disclosure control.
    const fits = required <= summary.clientWidth + 1;
    details.classList.toggle("records-baits-fit", fits);
    const toggle = details.querySelector(".records-bait-toggle");
    if (toggle) toggle.setAttribute("aria-hidden", String(fits));
    summary.setAttribute("aria-label", fits ? "Все элементы помещаются в строке" : details.dataset.expandLabel);
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

  // Native <details> cannot animate the removal of its content on close.
  // Keep it open until the collapse animation finishes, then close it.
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
  const animations = new WeakMap();
  const desiredStates = new WeakMap();
  for (const details of detailsNodes) {
    const summary = details.querySelector(".records-baits-summary");
    const panel = details.querySelector(".records-bait-list-expanded");
    if (!summary || !panel) continue;
    const chevron = summary.querySelector(".records-bait-toggle .records-chevron");
    const updateChevron = (expanded) => {
      if (chevron) chevron.textContent = expanded ? "⌃" : "⌄";
    };
    updateChevron(details.open);

    // Treat the empty area of the last column as a disclosure target too.
    // Preserve normal interaction with chips and any interactive descendants.
    const cell = details.closest(".records-baits-cell");
    if (cell) {
      cell.addEventListener("click", (event) => {
        if (event.target.closest(".records-baits-summary")) return;
        if (event.target.closest(".records-bait-item, a, button, input, select, textarea")) return;
        if (details.classList.contains("records-baits-fit")) return;
        summary.click();
      });
    }

    summary.addEventListener("click", (event) => {
      if (event.target.closest("[data-record-bait]")) return;
      // Chips sit inside <summary> when collapsed. Prevent the native
      // <details> toggle without treating a chip click as a disclosure.
      if (event.target.closest(".records-bait-item")) {
        event.preventDefault();
        return;
      }
      event.preventDefault(); // We control `open` so collapse can finish first.
      if (details.classList.contains("records-baits-fit")) return;

      const currentTarget = desiredStates.has(details)
        ? desiredStates.get(details) : details.open;
      const opening = !currentTarget;
      desiredStates.set(details, opening);
      updateChevron(opening);

      const previous = animations.get(details);
      const from = previous ? panel.getBoundingClientRect().height
        : (details.open ? panel.getBoundingClientRect().height : 0);
      if (previous) previous.cancel();
      if (opening) details.open = true;

      summary.setAttribute("aria-label", opening
        ? details.dataset.collapseLabel : details.dataset.expandLabel);
      details.classList.toggle("records-baits-closing", !opening);

      if (reduceMotion.matches || typeof panel.animate !== "function") {
        details.open = opening;
        details.classList.remove("records-baits-closing");
        panel.style.removeProperty("height");
        panel.style.removeProperty("overflow");
        desiredStates.delete(details);
        if (!opening) requestAnimationFrame(() => measure(details));
        return;
      }

      panel.style.height = `${from}px`;
      panel.style.overflow = "hidden";
      const to = opening ? panel.scrollHeight : 0;
      const animation = panel.animate([
        { height: `${from}px`, opacity: opening ? 0 : 1 },
        { height: `${to}px`, opacity: opening ? 1 : 0 },
      ], { duration: 220, easing: "ease-in-out" });
      animations.set(details, animation);
      animation.onfinish = () => {
        if (animations.get(details) !== animation) return;
        animations.delete(details);
        desiredStates.delete(details);
        details.open = opening;
        details.classList.remove("records-baits-closing");
        panel.style.removeProperty("height");
        panel.style.removeProperty("overflow");
        if (!opening) requestAnimationFrame(() => measure(details));
      };
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
