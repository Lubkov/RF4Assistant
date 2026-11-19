(function () {
  'use strict';
  const $ = (id) => document.getElementById(id);
  const modalNode = $('spot-modal');
  if (!modalNode) return;
  const titles = ['Категория', 'Место ловли', 'Виды рыб', 'Комментарий', 'Скриншоты', 'Предпросмотр'];
  const categoryNames = {farm: 'Фарм', trophy: 'Трофей', qualification: 'Квалификация', task: 'Задание'};
  const state = {step: 0, bodies: [], selectedFish: new Set(), images: [], selectedPreview: 0, dirty: false};
  let map = null, marker = null, mapBounds = null, fitZoom = 0, mapImageSize = null, mapBodyId = null, nextBusy = false;
  let pendingClose = false, mapLoadId = 0, mapLoading = false;
  const optionsUrl = '/fishing-spots/options/';
  const createUrl = '/fishing-spots/create/';

  function error(message) { const node = $('spot-error'); node.textContent = message; node.classList.toggle('d-none', !message); }
  function body() { return state.bodies.find(item => String(item.id) === $('spot-waterbody').value); }
  function categories() { return Array.from($('spot-categories').querySelectorAll('input:checked')).map(el => el.value); }
  function coordinates() {
    const xText = $('spot-coordinate-x').value.trim(), yText = $('spot-coordinate-y').value.trim();
    if (!xText || !yText || !body()?.map) return null;
    const x = Number(xText), y = Number(yText), b = body().map;
    if (!Number.isFinite(x) || !Number.isFinite(y)) return null;
    return x >= b.x_min && x <= b.x_max && y >= b.y_min && y <= b.y_max ? {x, y} : null;
  }
  function coordinateText() { return `${$('spot-coordinate-x').value.trim()}:${$('spot-coordinate-y').value.trim()}`; }
  function updateCategories() {
    const selected = categories().length;
    $('spot-categories').querySelectorAll('input[type=checkbox]').forEach(input => {
      input.disabled = selected >= 2 && !input.checked;
      input.closest('.spot-choice').classList.toggle('spot-choice-disabled', input.disabled);
    });
  }
  function updateLocationFields() {
    const disabled = !body();
    ['spot-clip', 'spot-depth', 'spot-speed'].forEach(id => { $(id).disabled = disabled; });
  }
  // Numeric inputs ignore maxlength: limit X/Y to four digits, excluding the decimal separator.
  function limitCoordinateDigits(input) {
    const before = input.value;
    let digits = 0, separator = false, result = '';
    for (const char of before) {
      if (char >= '0' && char <= '9') {
        if (digits < 4) { result += char; digits++; }
      } else if (char === '.' && !separator) {
        result += char; separator = true;
      }
    }
    if (result !== before) input.value = result;
  }
  function validOptional(id, maximum) {
    const value = $(id).value.trim();
    return !value || (/^[0-9]+$/.test(value) && Number(value) >= 1 && (!maximum || Number(value) <= maximum));
  }
  function valid(step) {
    if (step === 0) return categories().length >= 1 && categories().length <= 2;
    if (step === 1) return !!body()?.map && coordinates() !== null && validOptional('spot-clip') && validOptional('spot-depth') && validOptional('spot-speed', 50);
    if (step === 2) return state.selectedFish.size >= 1 && state.selectedFish.size <= 10;
    if (step === 4) return state.images.length >= 2 && state.images.length <= 10;
    return true;
  }
  const messages = ['Выберите 1–2 категории.', 'Укажите водоём, корректные координаты и допустимые параметры ловли.', 'Выберите от 1 до 10 видов рыб.', '', 'Добавьте 2–10 скриншотов.', ''];
  function refresh() {
    modalNode.querySelectorAll('.spot-step').forEach((node, index) => node.classList.toggle('d-none', index !== state.step));
    $('spot-step-title').textContent = titles[state.step];
    $('spot-counter').textContent = `Шаг ${state.step + 1} из 6`;
    $('spot-progress').setAttribute('aria-valuenow', state.step + 1);
    $('spot-progress').querySelectorAll('span').forEach((el, i) => el.classList.toggle('active', i <= state.step));
    $('spot-back').disabled = state.step === 0 || nextBusy;
    updateCategories();
    updateLocationFields();
    $('spot-next').disabled = nextBusy || !valid(state.step);
    $('spot-next').textContent = state.step === 5 ? (nextBusy ? 'Сохранение…' : 'Сохранить') : 'Далее ›';
    if (state.step === 1) showMap();
    if (state.step === 5) buildPreview();
  }
  function makeLabel(name, value, checked, disabled, handler) {
    const label = document.createElement('label'); label.className = 'spot-fish-option';
    const checkbox = document.createElement('input'); checkbox.type = 'checkbox'; checkbox.className = 'form-check-input mt-0';
    checkbox.checked = checked; checkbox.disabled = disabled; checkbox.addEventListener('change', handler);
    const span = document.createElement('span'); span.textContent = name;
    label.append(checkbox, span); return label;
  }
  function renderFish() {
    const node = $('spot-fish-list'); node.replaceChildren();
    const search = $('spot-fish-search').value.trim().toLocaleLowerCase();
    const fishes = body()?.fish || [];
    fishes.filter(f => f.fish__name.toLocaleLowerCase().includes(search)).forEach(f => {
      const selected = state.selectedFish.has(f.fish_id);
      node.append(makeLabel(f.fish__name, f.fish_id, selected, !selected && state.selectedFish.size >= 10, (e) => {
        if (e.target.checked) state.selectedFish.add(f.fish_id); else state.selectedFish.delete(f.fish_id);
        state.dirty = true; renderFish(); refresh();
      }));
    });
    $('spot-fish-count').textContent = `Выбрано видов: ${state.selectedFish.size} из 10`;
  }
  function loadLeaflet() {
    if (window.L) return Promise.resolve();
    if (!document.querySelector('link[data-spot-leaflet]')) {
      const style = document.createElement('link'); style.rel = 'stylesheet'; style.href = 'https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/leaflet.css'; style.dataset.spotLeaflet = '1'; document.head.append(style);
    }
    return new Promise((resolve, reject) => {
      // Another page may already be loading Leaflet with defer.
      const existing = document.querySelector('script[src*="leaflet@1.9.4/dist/leaflet.js"]');
      if (existing) { if (window.L) resolve(); else { existing.addEventListener('load', resolve, {once:true}); existing.addEventListener('error', reject, {once:true}); } return; }
      const script = document.createElement('script'); script.src = 'https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/leaflet.js'; script.onload = resolve; script.onerror = reject; document.head.append(script);
    });
  }
  function clearMap() { mapLoadId++; mapLoading = false; if (map) { map.remove(); map = null; } marker = null; mapBounds = null; mapBodyId = null; mapImageSize = null; }
  function fitMap() { if (!map || !mapBounds) return; map.invalidateSize(); map.setMinZoom(-8); map.fitBounds(mapBounds, {animate:false}); fitZoom = map.getZoom(); map.setMinZoom(fitZoom); map.setMaxZoom(Math.max(4, fitZoom + 3)); }
  function plotMarker() {
    const point = coordinates();
    const hasInput = $('spot-coordinate-x').value.trim() || $('spot-coordinate-y').value.trim();
    ['spot-coordinate-x', 'spot-coordinate-y'].forEach(id => $(id).classList.toggle('is-invalid', !!hasInput && !point));
    $('spot-coordinate-status').textContent = !body()?.map ? 'Карта с координатами не настроена.' : point ? 'Координаты корректны.' : 'Введите X:Y в пределах карты.';
    if (!map || !mapImageSize) return;
    if (marker) { map.removeLayer(marker); marker = null; }
    if (!point) return;
    const b = body().map;
    const ll = window.L.latLng((point.y - b.y_min) / (b.y_max - b.y_min) * mapImageSize.height,
                               (point.x - b.x_min) / (b.x_max - b.x_min) * mapImageSize.width);
    marker = window.L.marker(ll, {icon: window.L.divIcon({className:'',html:'<div class="spot-marker"></div>',iconSize:[14,14],iconAnchor:[7,7]})}).addTo(map);
  }
  async function showMap() {
    const target = body();
    $('spot-map-wrapper').classList.toggle('d-none', !target?.map);
    $('spot-no-map').classList.toggle('d-none', !!target?.map);
    $('spot-coordinate-x').disabled = !target?.map;
    $('spot-coordinate-y').disabled = !target?.map;
    if (!target?.map) { clearMap(); return; }
    if (map && mapBodyId === target.id) { setTimeout(() => {map.invalidateSize(); plotMarker();}, 50); return; }
    if (mapLoading) return;
    clearMap(); mapLoading = true; const loadId = ++mapLoadId;
    try { await loadLeaflet(); } catch (_) { mapLoading = false; error('Не удалось загрузить Leaflet для карты.'); return; }
    if (loadId !== mapLoadId || state.step !== 1 || body()?.id !== target.id) return;
    const img = new Image(); img.onload = () => {
      if (loadId !== mapLoadId || state.step !== 1 || body()?.id !== target.id) return;
      mapLoading = false; const L = window.L;
      mapImageSize = {width:img.naturalWidth,height:img.naturalHeight};
      mapBounds = L.latLngBounds([[0,0],[img.naturalHeight,img.naturalWidth]]);
      map = L.map('spot-map', {crs:L.CRS.Simple,zoomControl:false,attributionControl:false,minZoom:-8,maxZoom:4,zoomSnap:.25,scrollWheelZoom:'center',maxBounds:mapBounds,maxBoundsViscosity:1});
      L.imageOverlay(target.map.url, mapBounds).addTo(map); mapBodyId = target.id; fitMap(); plotMarker();
      map.on('click', (e) => {
        const bounds = target.map;
        const x = bounds.x_min + e.latlng.lng / img.naturalWidth * (bounds.x_max - bounds.x_min);
        const y = bounds.y_min + e.latlng.lat / img.naturalHeight * (bounds.y_max - bounds.y_min);
        if (x < bounds.x_min || x > bounds.x_max || y < bounds.y_min || y > bounds.y_max) return;
        $('spot-coordinate-x').value = String(Math.round(x));
        $('spot-coordinate-y').value = String(Math.round(y));
        state.dirty = true; plotMarker(); refresh();
      });
    }; img.onerror = () => { mapLoading=false; error('Не удалось загрузить изображение карты.'); }; img.src = target.map.url;
  }
  function addImages(files) {
    error('');
    const additions = Array.from(files);
    if (state.images.length + additions.length > 10) { error('Максимум 10 скриншотов.'); return; }
    if (additions.some(file => file.size > 10 * 1024 * 1024 || !['image/png','image/jpeg','image/webp'].includes(file.type))) {
      error('Разрешены PNG, JPG и WebP размером до 10 МБ.'); return;
    }
    for (const file of additions) state.images.push({file, url: URL.createObjectURL(file)});
    state.dirty = true; renderImages(); refresh();
  }
  function moveImage(from, to) {
    if (!Number.isInteger(from) || !Number.isInteger(to) || from < 0 || to < 0 || from >= state.images.length || to >= state.images.length || from === to) return;
    state.images.splice(to, 0, state.images.splice(from, 1)[0]); state.dirty = true; renderImages(); refresh();
  }
  // Distinguish moving an existing tile from dropping files from the OS.
  // Browsers can expose a dragged <img> as a File, so do not rely on files.length alone.
  const IMAGE_DRAG_TYPE = 'application/x-rf4-spot-image';
  let draggedImageIndex = null;
  function isImageReorder(event) {
    return draggedImageIndex !== null || Array.from(event.dataTransfer?.types || []).includes(IMAGE_DRAG_TYPE);
  }
  function isExternalFileDrop(event) {
    return !isImageReorder(event) && Array.from(event.dataTransfer?.types || []).includes('Files');
  }
  function sourceIndex(event) {
    if (draggedImageIndex !== null) return draggedImageIndex;
    const value = Number(event.dataTransfer.getData(IMAGE_DRAG_TYPE));
    return Number.isInteger(value) ? value : -1;
  }
  function renderImages() {
    const container = $('spot-images'); container.replaceChildren();
    $('spot-file-count').textContent = `${state.images.length} из 2–10`;
    $('spot-dropzone').classList.toggle('d-none', state.images.length > 0);
    state.images.forEach((entry, index) => {
      const card = document.createElement('div'); card.className = 'spot-upload-card'; card.draggable = true;
      const img = document.createElement('img'); img.src = entry.url; img.alt = entry.file.name; img.draggable = false;
      const number = document.createElement('span');
      number.className = 'spot-image-number';
      number.textContent = String(index + 1);
      number.setAttribute('aria-label', `Скриншот ${index + 1}${index === 0 ? ', обложка' : ''}`);
      const controls = document.createElement('div');
      controls.className = 'spot-image-controls';
      // This overlay is not a drag handle: keep the normal cursor between buttons.
      controls.draggable = false;
      controls.addEventListener('dragstart', e => { e.preventDefault(); e.stopPropagation(); });
      const makeControl = (symbol, label, callback, disabled = false) => {
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'spot-image-control btn btn-sm btn-outline-light';
        btn.textContent = symbol;
        btn.title = label;
        btn.setAttribute('aria-label', label);
        btn.disabled = disabled;
        // Keep the action controls independent from the draggable image tile.
        btn.draggable = false;
        btn.addEventListener('dragstart', e => e.preventDefault());
        btn.addEventListener('click', callback);
        return btn;
      };
      controls.append(
        makeControl('←', 'Переместить влево', () => moveImage(index, index - 1), index === 0),
        makeControl('×', 'Удалить скриншот', () => {
          URL.revokeObjectURL(entry.url);
          state.images.splice(index, 1);
          state.dirty = true;
          renderImages();
          refresh();
        }),
        makeControl('→', 'Переместить вправо', () => moveImage(index, index + 1), index === state.images.length - 1)
      );
      card.addEventListener('dragstart', e => {
        if (e.target.closest('.spot-image-controls')) { e.preventDefault(); return; }
        draggedImageIndex = index;
        e.dataTransfer.effectAllowed = 'move';
        e.dataTransfer.setData(IMAGE_DRAG_TYPE, String(index));
        // A plain-text fallback keeps the drag operation valid across browsers.
        e.dataTransfer.setData('text/plain', String(index));
      });
      card.addEventListener('dragend', () => { draggedImageIndex = null; });
      card.addEventListener('dragover', e => {
        if (!isImageReorder(e) && !isExternalFileDrop(e)) return;
        e.preventDefault();
        // Do not let the gallery's gap handler overwrite 'move' with 'none'.
        e.stopPropagation();
        e.dataTransfer.dropEffect = isImageReorder(e) ? 'move' : 'copy';
      });
      card.addEventListener('drop', e => {
        if (!isImageReorder(e) && !isExternalFileDrop(e)) return;
        e.preventDefault();
        e.stopPropagation();
        if (isImageReorder(e)) {
          const from = sourceIndex(e);
          draggedImageIndex = null;
          moveImage(from, index);
        } else if (e.dataTransfer.files.length) {
          // Files imported from outside the gallery always append.
          addImages(e.dataTransfer.files);
        }
      });
      card.append(img, number, controls); container.append(card);
    });
    if (state.images.length > 0 && state.images.length < 10) {
      const addCard = document.createElement('button');
      addCard.type = 'button';
      addCard.className = 'spot-upload-card spot-add-card';
      addCard.setAttribute('aria-label', 'Добавить скриншоты');
      addCard.title = 'Добавить скриншоты';
      const plus = document.createElement('span');
      plus.className = 'spot-add-icon';
      plus.textContent = '+';
      plus.setAttribute('aria-hidden', 'true');
      addCard.append(plus);
      addCard.addEventListener('click', () => $('spot-files').click());
      addCard.addEventListener('dragover', e => {
        if (!isImageReorder(e) && !isExternalFileDrop(e)) return;
        e.preventDefault();
        e.stopPropagation();
        e.dataTransfer.dropEffect = isImageReorder(e) ? 'none' : 'copy';
        addCard.classList.toggle('dragging', !isImageReorder(e));
      });
      addCard.addEventListener('dragleave', () => addCard.classList.remove('dragging'));
      addCard.addEventListener('drop', e => {
        e.preventDefault();
        e.stopPropagation();
        addCard.classList.remove('dragging');
        // The + tile is an upload target, never a reorder destination.
        if (isImageReorder(e)) { draggedImageIndex = null; return; }
        if (isExternalFileDrop(e) && e.dataTransfer.files.length) addImages(e.dataTransfer.files);
      });
      container.append(addCard);
    }
  }
  // Also accept files dropped into the gaps between existing screenshot tiles.
  $('spot-images').addEventListener('dragover', e => {
    if (isImageReorder(e)) { e.preventDefault(); e.dataTransfer.dropEffect = 'none'; return; }
    if (isExternalFileDrop(e)) e.preventDefault();
  });
  $('spot-images').addEventListener('drop', e => {
    if (isImageReorder(e)) { e.preventDefault(); draggedImageIndex = null; return; }
    if (!isExternalFileDrop(e) || !e.dataTransfer.files.length) return;
    e.preventDefault();
    addImages(e.dataTransfer.files);
  });
  function summary(label, value) {
    const dt = document.createElement('dt'); dt.className='col-sm-4 mb-2'; dt.textContent=label;
    const dd = document.createElement('dd'); dd.className='col-sm-8 mb-2'; dd.textContent=value || '—';
    $('spot-summary').append(dt,dd);
  }
  function buildPreview() {
    if (!state.images.length) return;
    state.selectedPreview = Math.min(state.selectedPreview,state.images.length-1);
    $('spot-preview-image').src=state.images[state.selectedPreview].url;
    const thumbs=$('spot-preview-thumbs'); thumbs.replaceChildren();
    state.images.forEach((entry,i)=>{
      const button=document.createElement('button');button.type='button';button.className=i===state.selectedPreview?'active':'';button.setAttribute('aria-label',`Показать скриншот ${i+1}`);
      const img=document.createElement('img');img.src=entry.url;img.alt='';button.append(img);
      button.addEventListener('click',()=>{state.selectedPreview=i;buildPreview();});thumbs.append(button);
    });
    $('spot-summary').replaceChildren();
    summary('Категория',categories().map(c=>categoryNames[c]).join(', '));summary('Водоём',body()?.name);
    summary('Рыба',(body()?.fish||[]).filter(f=>state.selectedFish.has(f.fish_id)).map(f=>f.fish__name).join(', '));
    summary('Координаты',coordinateText());summary('Клипса',$('spot-clip').value);
    summary('Глубина',$('spot-depth').value?`${$('spot-depth').value} см`:'');summary('Скорость проводки',$('spot-speed').value);
    summary('Комментарий',$('spot-comment').value);
  }
  function reset() {
    clearMap();state.step=0;state.selectedFish.clear();state.dirty=false;state.selectedPreview=0;nextBusy=false;
    state.images.forEach(item=>URL.revokeObjectURL(item.url));state.images=[];
    $('spot-categories').querySelectorAll('input').forEach(el=>el.checked=false);
    for (const id of ['spot-waterbody','spot-coordinate-x','spot-coordinate-y','spot-clip','spot-depth','spot-speed','spot-comment','spot-fish-search']) $(id).value='';
    ['spot-coordinate-x','spot-coordinate-y'].forEach(id => $(id).classList.remove('is-invalid'));error('');renderFish();renderImages();refresh();
  }
  async function loadOptions() {
    try {
      const response=await fetch(optionsUrl,{credentials:'same-origin'});if(!response.ok)throw Error('Не удалось получить список водоёмов.');
      state.bodies=(await response.json()).waterbodies;
      const select=$('spot-waterbody'); select.replaceChildren(new Option('Выберите водоём',''));
      state.bodies.forEach(b=>select.add(new Option(`${b.name} (${b.level} ур.)`,b.id)));
    } catch(e) {error(e.message);}
  }
  function csrf() { const match=document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);return match?decodeURIComponent(match[1]):''; }
  async function save() {
    if (nextBusy) return;
    nextBusy=true;refresh();error('');
    try {
      const data=new FormData();data.append('categories',JSON.stringify(categories()));data.append('waterbody_id',$('spot-waterbody').value);
      data.append('coordinates',coordinateText());data.append('clip',$('spot-clip').value);
      data.append('depth_cm',$('spot-depth').value);data.append('retrieve_speed',$('spot-speed').value);
      data.append('fish_ids',JSON.stringify([...state.selectedFish]));
      data.append('comment',$('spot-comment').value);state.images.forEach(item=>data.append('screenshots',item.file,item.file.name));
      const response=await fetch(createUrl,{method:'POST',body:data,credentials:'same-origin',headers:{'X-CSRFToken':csrf()}});
      const result=await response.json();if(!response.ok || !result.ok)throw Error(result.error||'Ошибка сохранения.');
      state.dirty=false;pendingClose=true;bootstrap.Modal.getInstance(modalNode).hide();
      bootstrap.Toast.getOrCreateInstance($('spot-success'),{delay:4000}).show();
    } catch(e) {error(e.message||'Ошибка сохранения.');}
    finally {nextBusy=false;refresh();}
  }
  async function next() {
    if (!valid(state.step)) {error(messages[state.step]);return;}
    error('');if(state.step===5){await save();return;}
    state.step+=1;refresh();
  }
  $('spot-next').addEventListener('click',next);
  $('spot-back').addEventListener('click',()=>{if(state.step>0){state.step--;error('');refresh();}});
  $('spot-categories').addEventListener('change',e=>{if(e.target.matches('input')){state.dirty=true;refresh();}});
  $('spot-waterbody').addEventListener('change',()=>{state.selectedFish.clear();$('spot-coordinate-x').value='';$('spot-coordinate-y').value='';$('spot-fish-search').value='';state.dirty=true;clearMap();renderFish();refresh();});
  ['spot-coordinate-x','spot-coordinate-y','spot-clip','spot-depth','spot-speed','spot-comment'].forEach(id=>$(id).addEventListener('input',()=>{if(id==='spot-coordinate-x'||id==='spot-coordinate-y'){limitCoordinateDigits($(id));plotMarker();}state.dirty=true;refresh();}));
  $('spot-fish-search').addEventListener('input',renderFish);
  $('spot-files').addEventListener('change',e=>{addImages(e.target.files);e.target.value='';});
  const dropzone=$('spot-dropzone');
  dropzone.addEventListener('click',()=>$('spot-files').click());
  dropzone.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();$('spot-files').click();}});
  dropzone.addEventListener('dragover',e=>{e.preventDefault();dropzone.classList.add('dragging');});
  dropzone.addEventListener('dragleave',()=>dropzone.classList.remove('dragging'));
  dropzone.addEventListener('drop',e=>{e.preventDefault();dropzone.classList.remove('dragging');addImages(e.dataTransfer.files);});
  $('spot-zoom-in').addEventListener('click',()=>map?.zoomIn(.5));
  $('spot-zoom-out').addEventListener('click',()=>map?.zoomOut(.5));
  $('spot-zoom-reset').addEventListener('click',fitMap);
  modalNode.addEventListener('show.bs.modal',()=>{reset();loadOptions();});
  modalNode.addEventListener('hide.bs.modal',e=>{if(state.dirty&&!pendingClose&&!window.confirm('Закрыть мастер? Несохранённые данные будут потеряны.'))e.preventDefault();});
  modalNode.addEventListener('hidden.bs.modal',()=>{pendingClose=false;reset();});
  refresh();
})();
