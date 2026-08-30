(function (window) {
  "use strict";

  /*
   * Service Marketplace Real Map
   * Leaflet + OpenStreetMap + Esri Satellite
   *
   * يحافظ على API القديم:
   * window.ServiceMarketplaceOfflineMap(...)
   */

  var DEFAULT_LOCATION = {
    lat: 15.3694,
    lng: 44.191,
  };

  var DEFAULT_ZOOM = 13;

  function isValidCoordinate(value) {
    return Number.isFinite(Number(value));
  }

  function isValidLocation(point) {
    if (!point) {
      return false;
    }

    var lat = Number(point.lat);
    var lng = Number(point.lng);

    return (
      isValidCoordinate(lat) &&
      isValidCoordinate(lng) &&
      lat >= -90 &&
      lat <= 90 &&
      lng >= -180 &&
      lng <= 180
    );
  }

  function normalizeLocation(point) {
    if (!isValidLocation(point)) {
      return {
        lat: DEFAULT_LOCATION.lat,
        lng: DEFAULT_LOCATION.lng,
      };
    }

    return {
      lat: Number(point.lat),
      lng: Number(point.lng),
    };
  }

  function safeNumber(value, fallback) {
    var number = Number(value);
    return Number.isFinite(number) ? number : fallback;
  }

  window.ServiceMarketplaceOfflineMap = function (element, options) {
    options = options || {};

    if (!element) {
      console.error("ServiceMarketplaceOfflineMap: عنصر الخريطة غير موجود.");
      return null;
    }

    if (!window.L) {
      console.error("ServiceMarketplaceOfflineMap: Leaflet غير محمل.");
      return null;
    }

    /*
     * الموقع الابتدائي
     */
    var initial = normalizeLocation(options.initial);

    var zoom = safeNumber(options.zoom, DEFAULT_ZOOM);

    var readonly = Boolean(options.readonly);

    /*
     * ---------------------------------------------
     * إنشاء الخريطة أو استخدام الخريطة الموجودة
     * ---------------------------------------------
     */

    var map = element._serviceMarketplaceMap;

    if (!map) {
      map = L.map(element, {
        zoomControl: true,
        scrollWheelZoom: true,
        dragging: true,
        doubleClickZoom: true,
        boxZoom: true,
        keyboard: true,
        touchZoom: true,
      });

      /*
       * -----------------------------------------
       * طبقة الشوارع الأساسية
       * -----------------------------------------
       */

      var streets = L.tileLayer(
        "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
        {
          maxZoom: 19,
          minZoom: 2,
          attribution:
            '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a> contributors',
        },
      );

      /*
       * -----------------------------------------
       * مصدر احتياطي للشوارع
       * -----------------------------------------
       *
       * إذا تعذر تحميل OpenStreetMap
       * نستخدم Carto Voyager.
       */

      var streetsFallback = L.tileLayer(
        "https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png",
        {
          maxZoom: 20,
          minZoom: 2,
          attribution: "&copy; OpenStreetMap contributors &copy; CARTO",
        },
      );

      /*
       * -----------------------------------------
       * صور الأقمار الصناعية
       * -----------------------------------------
       */

      var satellite = L.tileLayer(
        "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        {
          maxZoom: 19,
          minZoom: 2,
          attribution: "Tiles &copy; Esri",
        },
      );

      /*
       * ابدأ بخريطة الشوارع
       */

      streets.addTo(map);

      /*
       * -----------------------------------------
       * التحكم بين:
       * الخريطة
       * القمر الصناعي
       * -----------------------------------------
       */

      L.control
        .layers(
          {
            الخريطة: streets,
            "القمر الصناعي": satellite,
          },
          null,
          {
            position: "topleft",
            collapsed: false,
          },
        )
        .addTo(map);

      /*
       * -----------------------------------------
       * مراقبة فشل Tiles
       * -----------------------------------------
       */

      var fallbackActivated = false;

      streets.on("tileerror", function () {
        if (fallbackActivated) {
          return;
        }

        fallbackActivated = true;

        try {
          if (map.hasLayer(streets)) {
            map.removeLayer(streets);
          }

          streetsFallback.addTo(map);

          console.warn("OpenStreetMap tiles failed. Fallback map activated.");
        } catch (error) {
          console.error("Failed to activate fallback map:", error);
        }
      });

      /*
       * تخزين الخريطة داخل العنصر
       */

      element._serviceMarketplaceMap = map;

      /*
       * حفظ طبقات الخريطة
       */

      element._serviceMarketplaceStreets = streets;
      element._serviceMarketplaceSatellite = satellite;
      element._serviceMarketplaceFallback = streetsFallback;
    }

    /*
     * ---------------------------------------------
     * ضبط مركز الخريطة
     * ---------------------------------------------
     */

    map.setView([initial.lat, initial.lng], zoom);

    /*
     * ---------------------------------------------
     * Marker
     * ---------------------------------------------
     */

    var marker = element._serviceMarketplaceMarker;

    if (!marker) {
      marker = L.marker([initial.lat, initial.lng], {
        draggable: !readonly,
        autoPan: true,
      }).addTo(map);

      element._serviceMarketplaceMarker = marker;
    }

    /*
     * حالة readonly
     */

    if (marker.dragging) {
      if (readonly) {
        marker.dragging.disable();
      } else {
        marker.dragging.enable();
      }
    }

    /*
     * وضع Marker على الموقع الحالي
     */

    marker.setLatLng([initial.lat, initial.lng]);

    /*
     * ---------------------------------------------
     * إرسال الموقع إلى النظام
     * ---------------------------------------------
     */

    function notifyChange(latlng) {
      if (!latlng) {
        return;
      }

      var lat = Number(latlng.lat);
      var lng = Number(latlng.lng);

      if (!isValidLocation({ lat: lat, lng: lng })) {
        return;
      }

      /*
       * تحريك Marker
       */

      marker.setLatLng([lat, lng]);

      /*
       * لا نعيد توسيط الخريطة كل مرة
       * حتى لا يصبح تحريك Marker مزعجًا.
       */

      if (typeof options.onChange === "function") {
        options.onChange({
          lat: lat,
          lng: lng,
        });
      }
    }

    /*
     * ---------------------------------------------
     * سحب Marker
     * ---------------------------------------------
     */

    marker.off("dragend");

    marker.on("dragend", function () {
      if (readonly) {
        return;
      }

      var position = marker.getLatLng();

      notifyChange(position);
    });

    /*
     * ---------------------------------------------
     * النقر على الخريطة
     * ---------------------------------------------
     */

    map.off("click");

    if (!readonly) {
      map.on("click", function (event) {
        if (!event || !event.latlng) {
          return;
        }

        notifyChange(event.latlng);
      });
    }

    /*
     * ---------------------------------------------
     * معالجة ظهور الخريطة داخل Wizard
     * ---------------------------------------------
     */

    function refreshMapSize() {
      try {
        map.invalidateSize({
          pan: false,
        });
      } catch (error) {
        console.warn("Leaflet invalidateSize failed:", error);
      }
    }

    /*
     * أكثر من محاولة لأن الخريطة قد تكون
     * داخل عنصر كان مخفيًا.
     */

    setTimeout(refreshMapSize, 0);
    setTimeout(refreshMapSize, 150);
    setTimeout(refreshMapSize, 500);
    setTimeout(refreshMapSize, 1000);

    /*
     * ResizeObserver
     */

    if (window.ResizeObserver && !element._serviceMarketplaceResizeObserver) {
      var resizeObserver = new ResizeObserver(function () {
        refreshMapSize();
      });

      resizeObserver.observe(element);

      element._serviceMarketplaceResizeObserver = resizeObserver;
    }

    /*
     * window resize
     */

    if (!element._serviceMarketplaceResizeHandler) {
      var resizeHandler = function () {
        refreshMapSize();
      };

      window.addEventListener("resize", resizeHandler);

      element._serviceMarketplaceResizeHandler = resizeHandler;
    }

    /*
     * ---------------------------------------------
     * API الخارجي
     * ---------------------------------------------
     */

    return {
      map: map,

      marker: marker,

      placeMarker: function (next) {
        if (!isValidLocation(next)) {
          return;
        }

        var location = normalizeLocation(next);

        marker.setLatLng([location.lat, location.lng]);

        notifyChange({
          lat: location.lat,
          lng: location.lng,
        });
      },

      invalidateSize: function () {
        refreshMapSize();
      },
    };
  };
})(window);
