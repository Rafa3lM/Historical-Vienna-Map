<template>
  <div id="app">
    <div id="map"></div>

    <!-- Control Panel -->
    <div class="control-panel">
      <div class="panel-header">
        <h2>Historical Vienna Map</h2>
        <p class="subtitle">Explore buildings, places & events through time</p>
      </div>

      <!-- Time Range Slider -->
      <div class="control-section">
        <label class="section-label">
          Time Range
        </label>

        <TimeRangeSlider
            v-model:fromYear="filters.fromYear"
            v-model:toYear="filters.toYear"
        />

        <!-- Manual input -->
        <div class="range-inputs">
          <div class="range-input">
            <label>From</label>
            <input
                type="number"
                :min="0"
                :max="currentYear"
                v-model.number="filters.fromYear"
                @blur="validateRange"
            />
          </div>

          <div class="range-input">
            <label>To</label>
            <input
                type="number"
                :min="0"
                :max="currentYear"
                v-model.number="filters.toYear"
                @blur="validateRange"
            />
          </div>
        </div>

        <!-- Time range mode -->
        <div class="range-inputs">
          <div class="radio-group">
            <label class="radio-option">
              <input
                  type="radio"
                  value="overlap"
                  v-model="timeRangeMode"
              />
              <span>Overlapping</span>
            </label>

            <label class="radio-option">
              <input
                  type="radio"
                  value="contained"
                  v-model="timeRangeMode"
              />
              <span>Fully contained</span>
            </label>
          </div>
        </div>

      </div>

      <!-- Radius Selection -->
      <div class="control-section">
        <label class="section-label">
          Search Radius
          <span class="radius-value">{{ formattedRadius }}</span>
        </label>

        <div class="radius-slider-wrapper">
          <input
              v-model.number="filters.radius"
              type="range"
              min="50"
              max="15000"
              step="25"
              class="radius-slider"
          />
        </div>

        <div class="range-labels">
          <span>50 m</span>
          <span>15 km</span>
        </div>

        <p v-if="filters.radius >= 3000" class="warning-text">
          Large radius may impact performance
        </p>
      </div>

      <!-- Entity Types -->
      <div class="control-section">
        <label class="section-label">Entity Types</label>

        <!-- Buildings -->
        <div class="entity-category">
          <div class="category-header">
            <label class="checkbox-label category-label">
              <input
                  v-model="toggleAll.buildings"
                  type="checkbox"
                  @change="toggleAllSubtypes('buildings')"
              />
              <span class="category-icon">🏛️</span>
              <span>Buildings</span>
            </label>
            <button
                @click="toggleExpanded('buildings')"
                class="expand-button"
            >
              {{ expandedCategories.buildings ? '▼' : '▶' }}
            </button>
          </div>
          <div v-if="expandedCategories.buildings" class="subtypes">
            <label
                v-for="type in buildingTypes"
                :key="type.value"
                class="checkbox-label subtype-label"
            >
              <input
                  v-model="filters.buildingTypes"
                  :value="type.value"
                  type="checkbox"
                  @change="toggleType('buildings')"
              />
              <span>{{ type.label }}</span>
            </label>
          </div>
        </div>

        <!-- Events -->
        <div class="entity-category">
          <div class="category-header">
            <label class="checkbox-label category-label">
              <input
                  v-model="toggleAll.events"
                  type="checkbox"
                  @change="toggleAllSubtypes('events')"
              />
              <span class="category-icon">📅</span>
              <span>Events</span>
            </label>
            <button
                @click="toggleExpanded('events')"
                class="expand-button"
            >
              {{ expandedCategories.events ? '▼' : '▶' }}
            </button>
          </div>
          <div v-if="expandedCategories.events" class="subtypes">
            <label
                v-for="type in eventTypes"
                :key="type.value"
                class="checkbox-label subtype-label"
            >
              <input
                  v-model="filters.eventTypes"
                  :value="type.value"
                  type="checkbox"
                  @change="toggleType('events')"
              />
              <span>{{ type.label }}</span>
            </label>
          </div>
        </div>

        <!-- Places -->
        <div class="entity-category">
          <div class="category-header">
            <label class="checkbox-label category-label">
              <input
                  v-model="toggleAll.places"
                  type="checkbox"
                  @change="toggleAllSubtypes('places')"
              />
              <span class="category-icon">🌳</span>
              <span>Places</span>
            </label>
            <button
                @click="toggleExpanded('places')"
                class="expand-button"
            >
              {{ expandedCategories.places ? '▼' : '▶' }}
            </button>
          </div>
          <div v-if="expandedCategories.places" class="subtypes">
            <label
                v-for="type in placeTypes"
                :key="type.value"
                class="checkbox-label subtype-label"
            >
              <input
                  v-model="filters.placeTypes"
                  :value="type.value"
                  type="checkbox"
                  @change="toggleType('places')"
              />
              <span>{{ type.label }}</span>
            </label>
          </div>
        </div>
      </div>

      <!-- Advanced Filters -->
      <div class="control-section">
        <label class="section-label">Advanced Filters</label>
        <label class="checkbox-label">
          <input
              v-model="filters.onlyHistorical"
              type="checkbox"
          />
          <span>Show only demolished buildings</span>
        </label>
        <label class="checkbox-label">
          <input v-model="filters.onlyWithArchitect" type="checkbox"/>
          <span>Only buildings with known architect</span>
        </label>
        <label class="checkbox-label">
          <input v-model="filters.onlyWithResidents" type="checkbox"/>
          <span>Only with famous residents</span>
        </label>
        <label class="checkbox-label">
          <input v-model="filters.onlyNamed" type="checkbox"/>
          <span>Only named after someone/something</span>
        </label>
        <label class="checkbox-label">
          <input v-model="filters.onlyMonuments" type="checkbox"/>
          <span>Denkmalschutz (monument protection)</span>
        </label>
      </div>

      <button @click="applyFilters" class="apply-button">
        Apply Filters
      </button>

      <button @click="reset" class="reset-button">
        Reset
      </button>

      <!-- Results Count -->
      <div v-if="resultsCount !== null" class="results-info">
        Found {{ resultsCount }} results
      </div>


    </div>

    <!-- Entity Details Panel -->
    <GeoEntityPanel
        v-if="entityDetails"
        :entity-details="entityDetails"
        :loading-details="loadingDetails"
        @close="closeGeoPanel"
        @open-info="loadInfoEntityDetails"
        @open-geo="loadGeoEntityDetails"
    />

    <InfoEntityPanel
        v-if="selectedInfoEntity"
        :entity-details="selectedInfoEntity"
        :loading-details="loadingInfoDetails"
        @close="closeInfoPanel"
        @open-info="loadInfoEntityDetails"
        @open-geo="loadGeoEntityDetails"
    />

    <!-- Loading Overlay -->
    <div v-if="loading" class="loading-overlay">
      <div class="spinner"></div>
      <span>Loading data…</span>
    </div>

    <!-- Instructions -->
    <div v-if="!clickedOnce" class="instructions">
      <div class="instruction-box">
        <span class="instruction-icon">👆</span>
        <p>Click anywhere on the map to explore buildings and events in that area</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import qs from "qs";
import {computed, onMounted, reactive, ref} from "vue";
import L from "leaflet";
import {api} from "./services/api";
import type {Entities, Entity, GeoEntityDetails, InfoEntityDetails} from "./types/Entity";
import TimeRangeSlider from "./components/TimeRangeSlider.vue";
import InfoEntityPanel from "./components/InfoEntityPanel.vue";
import GeoEntityPanel from "./components/GeoEntityPanel.vue";

// State
const loading = ref(false);
const loadingDetails = ref(false);
const loadingInfoDetails = ref(false);
const clickedOnce = ref(false);
const resultsCount = ref<number | null>(null);
const selectedEntity = ref<Entity | null>(null);
const selectedInfoEntity = ref<InfoEntityDetails | null>(null);
const entityDetails = ref<GeoEntityDetails | null>(null);
const timeRangeMode = ref<'overlap' | 'contained'>('overlap');


// Building types from Vienna Wiki
const buildingTypes = [
  {value: "Bad", label: "Bad"},
  {value: "Brücke", label: "Brücke"},
  {value: "Gebäude", label: "Gebäude"},
  {value: "Gemeindebau", label: "Gemeindebau"},
  {value: "Kanalisation", label: "Kanalisation"},
  {value: "Kunst_im_öffentlichen_Raum", label: "Kunst im öffentlichen Raum"},
  {value: "Altkatholische_Kirche", label: "Altkatholische Kirche"},
  {value: "Evangelische_Kirche_A.B.", label: "Evangelische Kirche A.B."},
  {value: "Evangelische_Kirche_H.B.", label: "Evangelische Kirche H.B."},
  {value: "Griechisch-katholische_Kirche", label: "Griechisch-katholische Kirche"},
  {value: "Kapelle", label: "Kapelle"},
  {value: "Katholische_Kirche", label: "Katholische Kirche"},
  {value: "Sakrale_Freiplastik", label: "Sakrale Freiplastik"},
  {value: "Synagoge", label: "Synagoge"},
  {value: "Sonstiges_Bauwerk", label: "Sonstiges Bauwerk"},
  {value: "Stiege", label: "Stiege"},
  {value: "Wasserbauwerk", label: "Wasserbauwerk"},
  {value: "Brunnen", label: "Brunnen"},
  {value: "Kanal", label: "Kanal"},
  {value: "Wasserbehälter", label: "Wasserbehälter"},
  {value: "Wasserleitung", label: "Wasserleitung"},
];

const eventTypes = [
  {value: "Anschlag", label: "Anschlag"},
  {value: "Besetzung", label: "Besetzung"},
  {value: "Brand", label: "Brand"},
  {value: "Demonstration", label: "Demonstration"},
  {value: "Kundgebung", label: "Kundgebung"},
  {value: "Protestaktion", label: "Protestaktion"},
  {value: "Streik", label: "Streik"},
  {value: "Veranstaltung", label: "Veranstaltung"},
  {value: "Feier", label: "Feier"},
  {value: "Sportveranstaltung", label: "Sportveranstaltung"},
  {value: "Versammlung", label: "Versammlung"},
];

const placeTypes = [
  {value: "Friedhöfe", label: "Friedhof"},
  {value: "Grünfläche", label: "Grünfläche"},
  {value: "Passage", label: "Passage"},
  {value: "Markt", label: "Markt"},
];

// Expanded categories
const expandedCategories = reactive({
  buildings: false,
  events: false,
  places: false,
});

const toggleAll = reactive({
  buildings: true,
  events: false,
  places: false,
})

const currentYear = new Date().getFullYear();

// Filters
const filters = reactive({
  fromYear: 0,
  toYear: currentYear,
  timeRangeMode: timeRangeMode,
  radius: 750,
  onlyHistorical: false,
  onlyWithArchitect: false,
  onlyWithResidents: false,
  onlyMonuments: false,
  onlyNamed: false,
  buildingTypes: buildingTypes.map(t => t.value),
  eventTypes: [] as string[],
  placeTypes: [] as string[],
  district: "",
});

// Current search location
const currentLocation = ref<{ lat: number; lng: number } | null>(null);

// Map
let map: L.Map;
let markers: L.Marker[] = [];
let radiusCircle: L.Circle | null = null;

// Custom marker icons using Font Awesome-style emojis
const buildingIcon = L.divIcon({
  html: '<div class="custom-marker building-marker">🏛️</div>',
  className: 'custom-div-icon',
  iconSize: [30, 30],
  iconAnchor: [15, 30],
});

const eventIcon = L.divIcon({
  html: '<div class="custom-marker event-marker">📅</div>',
  className: 'custom-div-icon',
  iconSize: [30, 30],
  iconAnchor: [15, 30],
});

const placeIcon = L.divIcon({
  html: '<div class="custom-marker place-marker">🌳</div>',
  className: 'custom-div-icon',
  iconSize: [30, 30],
  iconAnchor: [15, 30],
});

const defaultIcon = L.divIcon({
  html: '<div class="custom-marker default-marker">📍</div>',
  className: 'custom-div-icon',
  iconSize: [30, 30],
  iconAnchor: [15, 30],
});

// Functions
const formattedRadius = computed(() => {
  return filters.radius >= 1000
      ? `${(filters.radius / 1000).toFixed(1)} km`
      : `${filters.radius} m`;
});

function validateRange() {
  if (filters.fromYear < 0) {
    filters.fromYear = 0;
  }

  if (filters.toYear > currentYear) {
    filters.toYear = currentYear;
  }

  if (filters.fromYear >= filters.toYear) {
    filters.fromYear = filters.toYear - 1;
  }
}

function toggleExpanded(category: 'buildings' | 'events' | 'places') {
  expandedCategories[category] = !expandedCategories[category];
}

function toggleAllSubtypes(category: 'buildings' | 'events' | 'places') {
  // When main checkbox changes, select/deselect all subtypes
  let isChecked: boolean = false;
  if (category === 'buildings') {
    isChecked = toggleAll.buildings;
  }
  if (category === 'events') {
    isChecked = toggleAll.events;
  }
  if (category === 'places') {
    isChecked = toggleAll.places;
  }

  if (isChecked) {
    // Expand category when checked
    expandedCategories[category] = true;
    if (category === 'buildings') filters.buildingTypes = buildingTypes.map(t => t.value);
    if (category === 'events') filters.eventTypes = eventTypes.map(t => t.value);
    if (category === 'places') filters.placeTypes = placeTypes.map(t => t.value);
  } else {
    // Clear all subtypes when unchecked
    if (category === 'buildings') filters.buildingTypes = [];
    if (category === 'events') filters.eventTypes = [];
    if (category === 'places') filters.placeTypes = [];
  }
}

function toggleType(category: 'buildings' | 'events' | 'places') {
  if (category === 'buildings') {
    toggleAll.buildings = filters.buildingTypes.length > 0;
  }
  if (category === 'events') {
    toggleAll.events = filters.eventTypes.length > 0;
  }
  if (category === 'places') {
    toggleAll.places = filters.placeTypes.length > 0;
  }
}

function clearMarkers() {
  markers.forEach(m => m.remove());
  markers = [];
}

function getIconForEntity(typeUri: string): L.DivIcon {
  // Check if it's a building type
  if (buildingTypes.some(t => typeUri.includes(t.value))) {
    return buildingIcon;
  }
  // Check if it's an event type
  if (eventTypes.some(t => typeUri.includes(t.value))) {
    return eventIcon;
  }
  // Check if it's a place type
  if (placeTypes.some(t => typeUri.includes(t.value))) {
    return placeIcon;
  }
  // Default/unknown type
  return defaultIcon;
}

async function loadGeoEntityDetails(uri: string) {
  loadingDetails.value = true;
  try {
    const res = await api.get(`/entity-geo/${encodeURIComponent(uri)}`);
    entityDetails.value = res.data;
    //selectedInfoEntity.value = null;
  } catch (error) {
    console.error('Failed to load entity details:', error);
    entityDetails.value = null;
  } finally {
    loadingDetails.value = false;
  }
}

async function loadInfoEntityDetails(uri: string) {
  loadingInfoDetails.value = true;
  try {
    const res = await api.get(`/entity-details/${encodeURIComponent(uri)}`);
    selectedInfoEntity.value = res.data;
    //entityDetails.value = null;
  } catch (error) {
    console.error('Failed to load entity details:', error);
    selectedInfoEntity.value = null;
  } finally {
    loadingInfoDetails.value = false;
  }
}

function closeDetails() {
  selectedEntity.value = null;
  closeGeoPanel();
  closeInfoPanel();
}

function closeGeoPanel() {
  entityDetails.value = null;
}

function closeInfoPanel() {
  selectedInfoEntity.value = null;
}

async function loadEntities(lat: number, lng: number) {
  loading.value = true;
  clearMarkers();
  closeDetails();

  try {
    const params: any = {
      lat,
      lng,
      radius: filters.radius,
      from_year: filters.fromYear,
      to_year: filters.toYear,
      time_range_mode: filters.timeRangeMode,
      only_historical: filters.onlyHistorical,
      only_monuments: filters.onlyMonuments,
      has_artist: filters.onlyWithArchitect,
      related_to: filters.onlyWithResidents,
      named_after: filters.onlyNamed,
    };

    if (filters.buildingTypes.length > 0) {
      params.building_types = filters.buildingTypes.map(t => {
        // Prevent malforming SPARQL query in backend by escaping trailing "."
        if (t.endsWith(".")) {
          return t.substring(0, t.length - 1) + "\\.";
        }
        return t;
      });
    }

    if (filters.eventTypes.length > 0) {
      params.event_types = filters.eventTypes.map(t => {
        // Prevent malforming SPARQL query in backend by escaping trailing "."
        if (t.endsWith(".")) {
          return t.substring(0, t.length - 1) + "\\.";
        }
        return t;
      });
    }

    if (filters.placeTypes.length > 0) {
      params.place_types = filters.placeTypes.map(t => {
        // Prevent malforming SPARQL query in backend by escaping trailing "."
        if (t.endsWith(".")) {
          return t.substring(0, t.length - 1) + "\\.";
        }
        return t;
      });
    }

    const res = await api.get<Entities>("/entities", {
      params,
      paramsSerializer: params => qs.stringify(params, {arrayFormat: "repeat"})
    });

    resultsCount.value = Number(res.data.count);

    res.data.entities.forEach(entity => {
      const icon = getIconForEntity(entity.type);

      const marker = L.marker([entity.lat, entity.lng], {icon})
          .addTo(map)
          .bindPopup(entity.label);

      marker.on('click', () => {
        selectedEntity.value = entity;
        loadGeoEntityDetails(entity.uri);
      });

      markers.push(marker);
    });

  } catch (error) {
    console.error('Failed to load entities:', error);
  } finally {
    loading.value = false;
  }
}

function drawRadius(lat: number, lng: number) {
  if (radiusCircle) {
    radiusCircle.remove();
  }

  radiusCircle = L.circle([lat, lng], {
    radius: filters.radius,
    color: "#3b82f6",
    weight: 2,
    fillColor: "#60a5fa",
    fillOpacity: 0.1,
  }).addTo(map);
}

function applyFilters() {
  if (currentLocation.value) {
    drawRadius(currentLocation.value.lat, currentLocation.value.lng);
    loadEntities(currentLocation.value.lat, currentLocation.value.lng);
  }
}

function reset() {
  if (radiusCircle) {
    radiusCircle.remove();
  }
  clearMarkers();
  closeDetails();
  toggleAll.buildings = true;
  toggleAll.events = false;
  toggleAll.places = false;
  toggleAllSubtypes('buildings')
  expandedCategories.buildings = false;
  toggleAllSubtypes('events')
  expandedCategories.events = false;
  toggleAllSubtypes('places')
  expandedCategories.places = false;
  filters.fromYear = 0;
  filters.toYear = currentYear;
  filters.timeRangeMode = 'overlap'
  filters.radius = 750;
  filters.onlyHistorical = false;
  filters.onlyWithArchitect = false;
  filters.onlyWithResidents = false;
  filters.onlyNamed = false;
  filters.onlyMonuments = false;
  filters.district = "";
}

onMounted(() => {
  map = L.map("map").setView([48.2082, 16.3738], 13);

  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: "© OpenStreetMap",
  }).addTo(map);

  map.on("click", e => {
    clickedOnce.value = true;
    currentLocation.value = {lat: e.latlng.lat, lng: e.latlng.lng};
    drawRadius(e.latlng.lat, e.latlng.lng);
    loadEntities(e.latlng.lat, e.latlng.lng);
  });
});

</script>

<style scoped>
/* ... keep all existing styles ... */

/* Category Header with Expand Button */
.category-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.expand-button {
  background: transparent;
  border: none;
  padding: 4px 8px;
  cursor: pointer;
  font-size: 12px;
  color: #6b7280;
  transition: color 0.2s;
}

.expand-button:hover {
  color: #111827;
}

/* Range Sliders */
.radius-slider-wrapper {
  margin-top: 8px;
  position: relative;
}

.radius-slider {
  width: 100%;
  height: 6px;
  border-radius: 999px;
  background: #3b82f6;
  -webkit-appearance: none;
  appearance: none;
  outline: none;
}

/* Thumb */
.radius-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 18px;
  height: 18px;
  background: #ffffff;
  border: 2px solid #3b82f6;
  border-radius: 50%;
  cursor: pointer;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.2);
}

.radius-slider::-moz-range-thumb {
  width: 18px;
  height: 18px;
  background: #ffffff;
  border: 2px solid #3b82f6;
  border-radius: 50%;
  cursor: pointer;
}

/* Value badge */
.radius-value {
  font-size: 12px;
  font-weight: 600;
  color: #3b82f6;
  margin-left: 6px;
}

/* Warning */
.warning-text {
  margin-top: 6px;
  font-size: 12px;
  color: #92400e;
  background: #fef3c7;
  padding: 6px 8px;
  border-radius: 6px;
}


.range-labels {
  display: flex;
  justify-content: space-between;
  margin-top: 8px;
  font-size: 12px;
  color: #6b7280;
}

.warning-text {
  margin: 8px 0 0 0;
  padding: 8px;
  background: #fef3c7;
  border: 1px solid #fbbf24;
  border-radius: 4px;
  font-size: 12px;
  color: #92400e;
}

/* Custom Marker Styles */
.custom-marker {
  font-size: 24px;
  text-align: center;
  line-height: 30px;
  cursor: pointer;
  filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.3));
  transition: transform 0.2s;
}

.custom-marker:hover {
  transform: scale(1.2);
}

/* Keep all other existing styles from previous version */
#app {
  height: 100%;
  width: 100%;
  position: relative;
}

#map {
  height: 100%;
  width: 100%;
}

.control-panel {
  position: absolute;
  top: 20px;
  right: 20px;
  width: 380px;
  max-height: calc(100vh - 40px);
  background: white;
  border-radius: 12px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
  z-index: 1000;
  overflow-y: auto;
  padding: 20px;
}

.panel-header {
  margin-bottom: 20px;
  border-bottom: 2px solid #e5e7eb;
  padding-bottom: 15px;
}

.panel-header h2 {
  margin: 0 0 5px 0;
  font-size: 20px;
  color: #111827;
}

.subtitle {
  margin: 0;
  font-size: 13px;
  color: #6b7280;
}

.control-section {
  margin-bottom: 20px;
}

.section-label {
  display: block;
  font-weight: 600;
  font-size: 13px;
  color: #374151;
  margin-bottom: 8px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

/* Time Inputs */

.input-group label {
  display: block;
  font-size: 12px;
  color: #6b7280;
  margin-bottom: 4px;
}

.range-inputs {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 8px;
  margin-top: 12px;
}

.range-input {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.range-input label {
  font-size: 11px;
  color: #6b7280;
}

.range-input input {
  width: 80px;
  padding: 6px 8px;
  font-size: 13px;
  border-radius: 6px;
  border: 1px solid #d1d5db;
}

.range-input input:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 1px #3b82f6;
}

.range-separator {
  font-size: 16px;
  color: #6b7280;
  padding-bottom: 4px;
}


/* Checkbox */
.checkbox-label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: #374151;
  cursor: pointer;
  padding: 6px 0;
}

.checkbox-label input[type="checkbox"] {
  width: 16px;
  height: 16px;
  cursor: pointer;
}

/* Entity Categories */
.entity-category {
  margin-bottom: 12px;
}

.category-label {
  font-weight: 500;
  padding: 8px;
  border-radius: 6px;
  transition: background-color 0.2s;
}

.category-label:hover {
  background-color: #f3f4f6;
}

.category-icon {
  font-size: 18px;
}

.subtypes {
  margin-left: 30px;
  margin-top: 6px;
  padding-left: 12px;
  border-left: 2px solid #e5e7eb;
}

.subtype-label {
  font-size: 13px;
  color: #6b7280;
}

/* Search & District */
.search-input,
.district-select {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 14px;
  transition: border-color 0.2s;
}

.search-input:disabled,
.district-select:disabled {
  background-color: #f9fafb;
  cursor: not-allowed;
}

.help-text {
  margin: 4px 0 0 0;
  font-size: 11px;
  color: #9ca3af;
  font-style: italic;
}

/* Apply Button */
.apply-button {
  width: 100%;
  padding: 12px;
  background: #3b82f6;
  color: white;
  border: none;
  border-radius: 8px;
  font-weight: 600;
  font-size: 14px;
  cursor: pointer;
  transition: background-color 0.2s;
}

/* Reset Button */
.reset-button {
  width: 100%;
  margin-top: 12px;
  padding: 12px;
  background: #ef2020;
  color: white;
  border: none;
  border-radius: 8px;
  font-weight: 600;
  font-size: 14px;
  cursor: pointer;
  transition: background-color 0.2s;
}

.apply-button:hover {
  background: #2563eb;
}

/* Results Info */
.results-info {
  margin-top: 12px;
  padding: 10px;
  background: #f0f9ff;
  border: 1px solid #bfdbfe;
  border-radius: 6px;
  text-align: center;
  font-size: 13px;
  color: #1e40af;
  font-weight: 500;
}

/* Details Panel */
.details-panel {
  position: absolute;
  bottom: 20px;
  left: 20px;
  width: 400px;
  max-height: 60vh;
  background: white;
  border-radius: 12px;
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.2);
  z-index: 1000;
  overflow-y: auto;
}

.close-button {
  position: absolute;
  top: 10px;
  right: 10px;
  background: #f3f4f6;
  border: none;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  font-size: 24px;
  line-height: 1;
  cursor: pointer;
  color: #6b7280;
  transition: all 0.2s;
  z-index: 1;
}

.close-button:hover {
  background: #e5e7eb;
  color: #111827;
}

.details-content {
  padding: 20px;
}

.details-content h3 {
  margin: 0 0 20px 0;
  font-size: 20px;
  color: #111827;
  padding-right: 30px;
}

.details-loading {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 20px 0;
  color: #6b7280;
}

.spinner-small {
  width: 20px;
  height: 20px;
  border: 2px solid #e5e7eb;
  border-top-color: #3b82f6;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

.detail-item {
  margin-bottom: 15px;
  padding-bottom: 12px;
  border-bottom: 1px solid #f3f4f6;
}

.detail-item:last-child {
  border-bottom: none;
}

.detail-item strong {
  display: block;
  font-size: 12px;
  color: #6b7280;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 4px;
}

.detail-item span {
  font-size: 14px;
  color: #111827;
}

.historical-badge {
  display: inline-block;
  padding: 2px 8px;
  background: #fee2e2;
  color: #991b1b;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
}

.coordinates {
  font-family: 'Courier New', monospace;
  font-size: 12px;
  color: #6b7280;
}

.wiki-link {
  display: inline-block;
  margin-top: 8px;
  color: #3b82f6;
  text-decoration: none;
  font-weight: 500;
  font-size: 14px;
}

.wiki-link:hover {
  text-decoration: underline;
}

/* Loading Overlay */
.loading-overlay {
  position: fixed;
  inset: 0;
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(4px);
  z-index: 2000;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  font-family: system-ui, sans-serif;
  color: #111827;
}

.spinner {
  width: 48px;
  height: 48px;
  border: 4px solid #e5e7eb;
  border-top-color: #3b82f6;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin-bottom: 16px;
}

/* Instructions */
.instructions {
  position: absolute;
  top: 65%;
  left: 50%;
  transform: translate(-50%, -50%);
  z-index: 999;
  pointer-events: none;
}

.instruction-box {
  background: white;
  padding: 24px 32px;
  border-radius: 12px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.15);
  text-align: center;
  max-width: 300px;
}

.instruction-icon {
  font-size: 48px;
  display: block;
  margin-bottom: 12px;
}

.instruction-box p {
  margin: 0;
  color: #374151;
  font-size: 15px;
  line-height: 1.5;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

/* Scrollbar styling */
.control-panel::-webkit-scrollbar,
.details-panel::-webkit-scrollbar {
  width: 8px;
}

.control-panel::-webkit-scrollbar-track,
.details-panel::-webkit-scrollbar-track {
  background: #f3f4f6;
  border-radius: 4px;
}

.control-panel::-webkit-scrollbar-thumb,
.details-panel::-webkit-scrollbar-thumb {
  background: #d1d5db;
  border-radius: 4px;
}

.control-panel::-webkit-scrollbar-thumb:hover,
.details-panel::-webkit-scrollbar-thumb:hover {
  background: #9ca3af;
}

.radio-group {
  display: flex;
  gap: 16px;
  margin-top: 8px;
}

.radio-option {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: #374151;
  cursor: pointer;
}

.radio-option input[type="radio"] {
  accent-color: #3b82f6; /* Tailwind blue-500 */
  cursor: pointer;
}

.radio-option span {
  user-select: none;
}

</style>