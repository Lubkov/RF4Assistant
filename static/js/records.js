"use strict";
(() => {
  const from = document.getElementById("date_from");
  const to = document.getElementById("date_to");
  if (!from || !to) return;

  // Date-only arithmetic in UTC avoids daylight saving time edge cases.
  for (const button of document.querySelectorAll("[data-record-days]")) {
    button.addEventListener("click", () => {
      const days = Number(button.dataset.recordDays);
      if (!Number.isInteger(days) || days < 1) return;
      const end = /^\d{4}-\d{2}-\d{2}$/.test(to.value) ? to.value : new Date().toISOString().slice(0, 10);
      const date = new Date(`${end}T12:00:00Z`);
      if (Number.isNaN(date.getTime())) return;
      date.setUTCDate(date.getUTCDate() - days + 1);
      from.value = date.toISOString().slice(0, 10);
      // Keep region, waterbody, fish, and sorting until the user presses Show.
      from.focus();
    });
  }
})();
