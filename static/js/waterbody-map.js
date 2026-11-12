/* RF4 map viewer. Coordinates are image pixel units in CRS.Simple.
 * Future markers can use relative x/y (0..1) and be converted with
 * L.latLng(y * imageHeight, x * imageWidth). */
(function () {
  "use strict";

  function initialize() {
    const container = document.getElementById("waterbody-map");
    if (!container) return;

    const status = document.getElementById("map-status");
    function showStatus(message) { if (status) status.textContent = message; }

    if (!window.L) {
      showStatus("Не удалось загрузить Leaflet. Проверьте подключение к интернету.");
      return;
    }

    const imageUrl = container.dataset.imageUrl;
    const image = new Image();
    image.onload = function () {
      const width = image.naturalWidth;
      const height = image.naturalHeight;
      if (!width || !height) { showStatus("Не удалось определить размер карты."); return; }
      container.style.aspectRatio = `${width} / ${height}`;

      const bounds = L.latLngBounds([[0, 0], [height, width]]);
      const map = L.map(container, {
        crs: L.CRS.Simple,
        zoomControl: false,
        attributionControl: false,
        minZoom: -6,
        maxZoom: 4,
        zoomSnap: 0.25,
        zoomDelta: 0.5,
        maxBounds: bounds,
        maxBoundsViscosity: 1,
        // Drag only after zooming beyond the visible image area.
        dragging: false,
        boxZoom: false,
        keyboard: false,
        scrollWheelZoom: "center",
        touchZoom: "center",
        doubleClickZoom: "center",
      });
      L.imageOverlay(imageUrl, bounds, { alt: container.dataset.imageAlt || "Карта водоёма" }).addTo(map);

      // A fully visible image must stay fixed. Once either image dimension
      // exceeds the viewport, panning is allowed so hidden parts remain reachable.
      function updateDragging() {
        const northWest = map.latLngToContainerPoint(bounds.getNorthWest());
        const southEast = map.latLngToContainerPoint(bounds.getSouthEast());
        const imageWidth = Math.abs(southEast.x - northWest.x);
        const imageHeight = Math.abs(southEast.y - northWest.y);
        const canDrag = imageWidth > container.clientWidth + 1 ||
                        imageHeight > container.clientHeight + 1;
        if (canDrag) map.dragging.enable();
        else map.dragging.disable();
      }

      map.on("zoomend resize", updateDragging);

      let fitZoom;
      function fitImage() {
        map.invalidateSize();
        // Set min zoom temporarily low so a changed viewport can fit the image.
        map.setMinZoom(-6);
        map.fitBounds(bounds, { animate: false });
        fitZoom = map.getZoom();
        map.setMinZoom(fitZoom);
        map.setMaxZoom(Math.max(fitZoom + 3, 4));
        updateDragging();
      }
      fitImage();

      document.getElementById("map-zoom-in")?.addEventListener("click", function () { map.zoomIn(0.5); });
      document.getElementById("map-zoom-out")?.addEventListener("click", function () { map.zoomOut(0.5); });
      document.getElementById("map-reset")?.addEventListener("click", fitImage);
      window.addEventListener("resize", function () {
        const oldFitZoom = fitZoom;
        // Ensure resize maintains a fully visible map if the viewport shrinks.
        const nextFitZoom = map.getBoundsZoom(bounds);
        if (nextFitZoom !== oldFitZoom) fitImage();
        else map.invalidateSize();
        updateDragging();
      });
      showStatus("Колёсико мыши или кнопки +/− — масштаб.");
    };
    image.onerror = function () { showStatus("Не удалось загрузить изображение карты."); };
    image.src = imageUrl;
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initialize);
  } else {
    initialize();
  }
})();
