<template>
  <div id="map"></div>
  <div class="panel">
    <h3>Interactive Historical Vienna</h3>
    <p>Click on the map to explore buildings</p>
  </div>
</template>

<script setup lang="ts">
import qs from "qs";
import {onMounted} from "vue";
import L from "leaflet";

import {api} from "./services/api";
import type {EntitiesDto} from "./types/Entity.ts";

let map: L.Map;
let markers: L.Marker[] = [];

function clearMarkers() {
  markers.forEach(m => m.remove());
  markers = [];
}

async function loadBuildings(lat: number, lng: number) {
  const res = await api.get<EntitiesDto>("/entities", {
    params: {
      lat,
      lng,
      radius: 500,
      from_year: 0,
      to_year: 2026,
      building_types: [],
      event_types: [],
      place_types: [],
      only_historical: false
    },
    paramsSerializer: params => qs.stringify(params, {arrayFormat: "repeat"})
  });

  console.log(res)
  clearMarkers();

  res.data.entities.forEach(b => {
    const marker = L.marker([b.lat, b.lng])
        .addTo(map)
        .bindPopup(b.label);

    markers.push(marker);
  });
}

onMounted(() => {
  map = L.map("map").setView([48.2082, 16.3738], 13);

  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: "© OpenStreetMap",
  }).addTo(map);

  map.on("click", e => {
    loadBuildings(e.latlng.lat, e.latlng.lng);
  });
});
</script>


<style>
#map {
  height: 100%;
  width: 100%;
}
</style>
