(() => {
  const modal = document.getElementById('spot-detail-modal');
  if (!modal) return;
  const title = document.getElementById('spot-detail-title');
  const body = document.getElementById('spot-detail-body');
  let request = null;
  function renderTitle(place, categoryNames = []) {
    const parts = document.createDocumentFragment();
    categoryNames.forEach(name => {
      const badge = document.createElement('span');
      const categoryClasses = {
        'Фарм': 'farm',
        'Трофей': 'trophy',
        'Квалификация': 'qualification',
        'Задание': 'task',
      };
      badge.className = 'badge spot-list-category';
      if (categoryClasses[name]) badge.classList.add(`spot-list-category--${categoryClasses[name]}`);
      badge.textContent = name;
      parts.appendChild(badge);
    });
    const location = document.createElement('span');
    location.textContent = place;
    parts.appendChild(location);
    title.replaceChildren(parts);
  }
  async function showSpot(card) {
    if (request) request.abort();
    request = new AbortController();
    const place = card.dataset.spotWaterbody && card.dataset.spotCoordinates
      ? `${card.dataset.spotWaterbody}, ${card.dataset.spotCoordinates}`
      : card.querySelector('.spot-list-title')?.textContent.trim() || 'Место ловли';
    renderTitle(place);
    body.textContent = 'Загрузка…';
    window.bootstrap.Modal.getOrCreateInstance(modal).show();
    try {
      const result = await fetch(card.dataset.spotDetailUrl, {signal:request.signal, headers:{'X-Requested-With':'XMLHttpRequest'}});
      if (!result.ok) throw new Error('HTTP ' + result.status);
      const html = await result.text();
      if (request.signal.aborted) return;
      body.innerHTML = html;
      const categories = body.querySelector("[data-spot-categories]")?.dataset.spotCategories;
      renderTitle(place, categories ? categories.split(',').map(name => name.trim()).filter(Boolean) : []);
      updateFishOverflow();
      updateCommentOverflow();
    } catch (error) {
      if (error.name !== 'AbortError') body.textContent = 'Не удалось загрузить место ловли.';
    }
  }
  function updateFishOverflow() {
    const details = body.querySelector('[data-spot-fish-details]');
    if (!details || details.open) return;
    const summary = details.querySelector('.spot-detail-fish-summary');
    const preview = details.querySelector('[data-spot-fish-preview]');
    if (!summary || !preview || !summary.clientWidth) return;
    const chips = [...preview.querySelectorAll(':scope > .spot-detail-fish-item')];
    chips.forEach(chip => { chip.hidden = false; });
    const gap = parseFloat(getComputedStyle(preview).columnGap) || 0;
    const widths = chips.map(chip => chip.getBoundingClientRect().width);
    const required = widths.reduce((sum, width) => sum + width, 0)
      + Math.max(0, chips.length - 1) * gap;
    const fits = required <= summary.clientWidth + 1;
    details.classList.toggle('is-fit', fits);
    details.classList.add('is-measured');
    summary.tabIndex = fits ? -1 : 0;
    summary.setAttribute('aria-label', fits ? 'Все виды рыб помещаются в строке' : 'Развернуть виды рыб');
    if (fits) return;
    let used = 0;
    let hideRest = false;
    chips.forEach((chip, index) => {
      const next = used + (index ? gap : 0) + widths[index];
      if (hideRest || next > preview.clientWidth + 1) {
        chip.hidden = true;
        hideRest = true;
      } else {
        used = next;
      }
    });
  }
  function updateCommentOverflow() {
    const section = body.querySelector('[data-spot-comment]');
    const content = section?.querySelector('[data-spot-comment-text]');
    const toggle = section?.querySelector('[data-spot-comment-toggle]');
    if (!section || !content || !toggle) return;
    // Measure the full text at the current width, then restore its previous state.
    const expanded = section.classList.contains('is-expanded');
    section.classList.remove('is-expanded');
    toggle.hidden = false; // Reserve the arrow's width during measurement.
    const collapsedHeight = content.getBoundingClientRect().height;
    section.classList.add('is-expanded');
    const fullHeight = content.getBoundingClientRect().height;
    const overflows = fullHeight > collapsedHeight + 1;
    section.classList.toggle('is-overflowing', overflows);
    section.classList.toggle('is-expanded', expanded && overflows);
    toggle.hidden = !overflows;
    toggle.setAttribute('aria-expanded', String(expanded && overflows));
    toggle.setAttribute('aria-label', expanded && overflows ? 'Свернуть комментарий' : 'Развернуть комментарий');
    toggle.querySelector('.spot-detail-comment-chevron').textContent = expanded && overflows ? '⌃' : '⌄';
  }
  function toggleComment(section) {
    if (!section.classList.contains('is-overflowing')) return;
    const expanded = section.classList.toggle('is-expanded');
    const toggle = section.querySelector('[data-spot-comment-toggle]');
    toggle.setAttribute('aria-expanded', String(expanded));
    toggle.setAttribute('aria-label', expanded ? 'Свернуть комментарий' : 'Развернуть комментарий');
    toggle.querySelector('.spot-detail-comment-chevron').textContent = expanded ? '⌃' : '⌄';
  }
  body.addEventListener('click', event => {
    const section = event.target.closest('[data-spot-comment]');
    if (!section || event.target.closest('a, input, select, textarea')) return;
    toggleComment(section);
  });
  function setFishExpanded(details, expanded) {
    details.open = expanded;
    const summary = details.querySelector('.spot-detail-fish-summary');
    const chevron = details.querySelector('.spot-detail-fish-chevron');
    if (chevron) chevron.textContent = expanded ? '⌃' : '⌄';
    if (summary) summary.setAttribute('aria-label', expanded ? 'Свернуть виды рыб' : 'Развернуть виды рыб');
    if (!expanded) requestAnimationFrame(updateFishOverflow);
  }
  body.addEventListener('click', event => {
    const section = event.target.closest('[data-spot-fish-section]');
    if (!section) return;
    const details = section.querySelector('[data-spot-fish-details]');
    if (!details) return;
    if (details.classList.contains('is-fit')) {
      // Even without an expand control, <summary> toggles <details> natively.
      // Suppress that toggle when all fish already fit on one line.
      if (event.target.closest('summary')) event.preventDefault();
      return;
    }
    if (event.target.closest('.spot-detail-fish-item, a, button, input, select, textarea')) {
      // Clicking an individual fish is not a disclosure action.
      if (event.target.closest('summary')) event.preventDefault();
      return;
    }
    // Prevent the native summary toggle so the same action works in the
    // summary, in the expanded panel's gaps, and on the unused block space.
    if (event.target.closest('summary')) event.preventDefault();
    setFishExpanded(details, !details.open);
  });
  window.addEventListener('resize', () => { updateFishOverflow(); updateCommentOverflow(); });
  modal.addEventListener('shown.bs.modal', () => { updateFishOverflow(); updateCommentOverflow(); });
  document.querySelectorAll('[data-spot-detail-url]').forEach(card => {
    card.addEventListener('click', () => showSpot(card));
    card.addEventListener('keydown', e => {
      if (e.key === 'Enter' || e.key === ' ') {e.preventDefault(); showSpot(card);}
    });
  });
  body.addEventListener('click', e => {
    const thumb = e.target.closest('#spot-detail-thumbs button');
    if (!thumb) return;
    const image = document.getElementById('spot-detail-image');
    if (image) image.src = thumb.dataset.imageUrl;
    body.querySelectorAll('#spot-detail-thumbs button').forEach(button => {
      const selected = button === thumb;
      button.classList.toggle('active', selected);
      button.setAttribute('aria-pressed', String(selected));
    });
  });
  modal.addEventListener('hidden.bs.modal', () => {if (request) request.abort();});
})();
