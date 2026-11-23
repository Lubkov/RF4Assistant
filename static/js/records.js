"use strict";
(() => {
  const panel = document.getElementById("bait-records-panel");
  if (!panel) return;

  const title = panel.querySelector("#bait-records-title");
  const count = panel.querySelector("#bait-records-count");
  const back = panel.querySelector("#bait-records-back");
  const summary = panel.querySelector("#bait-records-summary");
  const details = panel.querySelector("#bait-records-details");
  const summaryBody = summary.tBodies[0];
  const detailsBody = details.tBodies[0];
  const scrollArea = panel.querySelector(".offcanvas-body");
  const sortButtons = [...details.querySelectorAll("[data-bait-sort]")];
  const weightSort = details.querySelector('[data-bait-sort="weight"]');
  let selectedRow;
  let selectedFish;
  let catches = [];

  const sortCatches = (sortButton) => {
    for (const button of sortButtons) {
      button.closest("th").removeAttribute("aria-sort");
    }
    sortButton.closest("th").setAttribute("aria-sort", "descending");
    const rows = sortButton.dataset.baitSort === "date"
      ? [...catches].sort((first, second) => second.dataset.caughtDate.localeCompare(first.dataset.caughtDate))
      : catches;
    detailsBody.replaceChildren(...rows);
    scrollArea.scrollTop = 0;
  };

  const showFish = (index) => {
    selectedFish = summaryBody.rows[index];
    const fishName = selectedFish.querySelector("[data-bait-fish-name]").textContent;
    const template = selectedFish.querySelector("[data-bait-fish-catches]");
    catches = [...template.content.cloneNode(true).querySelectorAll("tr")];
    summary.hidden = true;
    details.hidden = false;
    back.firstElementChild.textContent = fishName;
    back.setAttribute("aria-label", `Снять фильтр по виду «${fishName}»`);
    back.hidden = false;
    sortCatches(weightSort);
  };

  panel.addEventListener("show.bs.offcanvas", (event) => {
    const trigger = event.relatedTarget;
    selectedRow = trigger?.closest("tr");
    if (!selectedRow) return;

    selectedRow.classList.add("table-active");
    const baitTrigger = selectedRow.querySelector("[data-bait-trigger]");
    title.replaceChildren(...Array.from(baitTrigger.children, (child) => child.cloneNode(true)));
    summaryBody.replaceChildren(selectedRow.querySelector("[data-bait-fish-summary]").content.cloneNode(true));
    count.textContent = `Видов рыб: ${summaryBody.rows.length}`;
    summary.hidden = false;
    details.hidden = true;
    back.hidden = true;
    scrollArea.scrollTop = 0;
    if (trigger.dataset.baitFishIndex !== undefined) showFish(trigger.dataset.baitFishIndex);
  });

  summary.addEventListener("click", (event) => {
    const trigger = event.target.closest("[data-bait-fish-index]");
    if (!trigger) return;

    showFish(trigger.dataset.baitFishIndex);
    back.focus();
  });
  back.addEventListener("click", () => {
    summary.hidden = false;
    details.hidden = true;
    back.hidden = true;
    scrollArea.scrollTop = 0;
    selectedFish.querySelector("button").focus();
  });
  for (const button of sortButtons) {
    button.addEventListener("click", () => sortCatches(button));
  }

  panel.addEventListener("hidden.bs.offcanvas", () => {
    selectedRow?.classList.remove("table-active");
  });
})();

(() => {
  const panel = document.getElementById("fish-records-panel");
  if (!panel) return;

  const title = panel.querySelector("#fish-records-title");
  const count = panel.querySelector("#fish-records-count");
  const date = panel.querySelector("#fish-records-date");
  const weight = panel.querySelector("#fish-records-weight");
  const filter = panel.querySelector("#fish-records-bait-filter");
  const mode = panel.querySelector("#fish-records-mode");
  const status = panel.querySelector("#fish-records-status");
  const summary = panel.querySelector("#fish-records-summary");
  const details = panel.querySelector("#fish-records-details");
  const summaryBody = summary.tBodies[0];
  const detailsBody = details.tBodies[0];
  const scrollArea = panel.querySelector(".offcanvas-body");
  let rows = [];
  let selectedRow;
  let selectedBait;
  let showAll = false;
  let sortButton = weight;
  let request;

  const showRows = () => {
    const showSummary = !showAll && selectedBait === undefined;
    summary.hidden = !showSummary;
    details.hidden = showSummary;
    mode.textContent = showSummary ? "Все рекорды" : "Сводка по наживкам";
    scrollArea.scrollTop = 0;
    if (showSummary) {
      return;
    }

    for (const button of [date, weight]) {
      button.closest("th").removeAttribute("aria-sort");
    }
    sortButton.closest("th").setAttribute("aria-sort", "descending");
    const visibleRows = selectedBait === undefined ? [...rows] : rows.filter((row) =>
      [...row.querySelectorAll("[data-record-bait]")].some((bait) =>
        bait.dataset.recordBait === selectedBait));
    if (sortButton === date) {
      visibleRows.sort((first, second) =>
        second.dataset.caughtDate.localeCompare(first.dataset.caughtDate));
    }
    detailsBody.replaceChildren(...visibleRows);
  };

  const filterByBait = (bait, allCatches = false) => {
    showAll = allCatches;
    selectedBait = bait;
    filter.hidden = bait === undefined;
    filter.firstElementChild.textContent = bait ?? "";
    filter.setAttribute("aria-label", `Снять фильтр по приманке «${bait ?? ""}»`);
    showRows();
  };

  panel.addEventListener("show.bs.offcanvas", async (event) => {
    const trigger = event.relatedTarget;
    const row = trigger?.closest("[data-fish-details-url]");
    if (!row) return;

    request?.abort();
    const controller = new AbortController();
    request = controller;
    selectedRow?.classList.remove("table-active");
    selectedRow = row;
    selectedRow.classList.add("table-active");
    const fishTrigger = row.querySelector(".records-fish-trigger");
    const icon = fishTrigger.previousElementSibling.cloneNode(true);
    title.replaceChildren(icon, fishTrigger.textContent.trim());
    count.textContent = "";
    summaryBody.replaceChildren();
    detailsBody.replaceChildren();
    rows = [];
    summary.hidden = true;
    details.hidden = true;
    filter.hidden = true;
    mode.hidden = true;
    status.textContent = "Загрузка рекордов…";
    status.hidden = false;
    sortButton = weight;

    try {
      const response = await fetch(row.dataset.fishDetailsUrl, { signal: controller.signal });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const html = await response.text();
      if (controller.signal.aborted) return;

      const fragment = new DOMParser().parseFromString(html, "text/html");
      const baitSummary = fragment.querySelector("[data-fish-bait-summary]");
      const records = fragment.querySelector("[data-fish-records]");
      summaryBody.replaceChildren(baitSummary.content);
      rows = [...records.content.querySelectorAll("tr")];
      count.textContent = `Наживок: ${summaryBody.rows.length}`;
      status.hidden = true;
      mode.hidden = false;
      filterByBait(trigger.dataset.recordBait);
    } catch {
      if (controller.signal.aborted) return;
      status.textContent = "Не удалось загрузить рекорды. Откройте панель ещё раз.";
    }
  });

  panel.addEventListener("hide.bs.offcanvas", () => {
    request?.abort();
    selectedRow?.classList.remove("table-active");
  });

  mode.addEventListener("click", () => {
    filterByBait(undefined, !summary.hidden);
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
