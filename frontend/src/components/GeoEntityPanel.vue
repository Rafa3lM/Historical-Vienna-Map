<script setup lang="ts">
import type {GeoEntityDetails} from "../types/Entity.ts";

const props = defineProps<{
  entityDetails: GeoEntityDetails;
  loadingDetails: boolean;
}>();

const emit = defineEmits<{
  (e: 'close'): void;
  (e: 'open-info', uri: string): void;
  (e: 'open-geo', uri: string): void;
}>();

function formatType(uri: string): string {
  if (!uri) return '';
  return decodeURIComponent(uri.split('/').pop() || uri)
      .replace(/-28/g, '(').replace(/-29/g, ')').replace(/_/g, ' ');
}

function formatUriList(list: string[]): string {
  return list.map(formatType).join(', ');
}

function loadDetails(uri: string) {
  emit('open-info', uri);
}
</script>

<template>
  <div v-if="entityDetails" class="details-panel">
    <button @click="$emit('close')" class="close-button">×</button>

    <div v-if="entityDetails.label" class="details-content">
      <h3>{{ entityDetails.label }}</h3>

      <div v-if="loadingDetails" class="details-loading">
        <div class="spinner-small"></div>
        Loading details...
      </div>

      <div v-else-if="entityDetails">
        <!-- Image -->
        <div v-if="entityDetails.image" class="detail-item">
          <img
              :src="entityDetails.image"
              :alt="entityDetails.label"
              loading="lazy"
              class="entity-image"
          />
        </div>

        <!-- Type -->
        <div v-if="entityDetails.buildingType || entityDetails.eventType || entityDetails.placeType"
             class="detail-item">
          <strong>Type:</strong>
          <span>{{
              formatType(entityDetails.buildingType || entityDetails.eventType || entityDetails.placeType || "")
            }}</span>
        </div>

        <!-- Monument Protection -->
        <div v-if="entityDetails.herisId || entityDetails.cultId" class="detail-item">
          <strong>Under Monument Protection:</strong>
          <div v-if="entityDetails.herisId">
            <span>HERIS-ID: {{ entityDetails?.herisId }}</span>
          </div>
          <div v-if="entityDetails.cultId">
            <span>Cultural Heritage ID: {{ entityDetails?.cultId }}</span>
          </div>
        </div>

        <!-- Time Period -->
        <div v-if="entityDetails.startDate || entityDetails.endDate" class="detail-item">
          <strong>Period:</strong>
          <span>
              {{ entityDetails.startDate || '?' }} - {{ entityDetails.endDate || 'present' }}
            </span>
        </div>

        <!-- Status (only for buildings/places, not events) -->
        <div v-if="entityDetails.historical !== undefined && !entityDetails.eventType" class="detail-item">
          <strong>Status:</strong>
          <span :class="{ 'historical-badge': entityDetails.historical }">
              {{ entityDetails.historical ? 'Demolished' : 'Existing' }}
            </span>
        </div>

        <!-- District -->
        <div v-if="entityDetails.district" class="detail-item">
          <strong>District:</strong>
          <span>{{ entityDetails.district }}</span>
        </div>

        <!-- Address -->
        <div v-if="entityDetails.address" class="detail-item">
          <strong>Address:</strong>
          <span>{{ entityDetails.address }}</span>
        </div>

        <!-- Architects -->
        <div v-if="entityDetails.architects" class="detail-item">
          <strong>Architect(s):</strong>
          <div v-for="architect in entityDetails.architects"
               :key="architect"
               class="detail-link">
            <span @click="!loadingDetails && loadDetails(architect)">{{ formatType(architect) }}</span>
          </div>
        </div>

        <!-- Named after -->
        <div v-if="entityDetails.namedAfter" class="detail-item">
          <strong>Named After:</strong>
          <div v-for="namedAfter in entityDetails.namedAfter"
               :key="namedAfter"
               class="detail-link">
            <span @click="!loadingDetails && loadDetails(namedAfter)">{{
                formatType(namedAfter)
              }}</span>
          </div>
        </div>

        <!-- Famous Residents -->
        <div v-if="entityDetails.famousInhabitants" class="detail-item">
          <strong>Famous Resident(s):</strong>
          <div v-for="famousResident in entityDetails.famousInhabitants"
               :key="famousResident"
               class="detail-link">
            <span @click="!loadingDetails && loadDetails(famousResident)">{{
                formatType(famousResident)
              }}</span>
          </div>
        </div>

        <!-- Events -->
        <div v-if="entityDetails.events" class="detail-item">
          <strong>Events: </strong>
          <span>{{ formatUriList(entityDetails.events) }}</span>
        </div>

        <!-- Coordinates -->
        <div v-if="entityDetails.coordinates" class="detail-item">
          <strong>Coordinates:</strong>
          <span class="coordinates">
              {{ entityDetails.coordinates.lat.toFixed(4) }},
              {{ entityDetails.coordinates.lng.toFixed(4) }}
            </span>
        </div>

        <!-- Wiki Link -->
        <div v-if="entityDetails.wikiPage" class="detail-item">
          <a
              :href="entityDetails.wikiPage"
              target="_blank"
              class="wiki-link"
          >
            View on Wien Geschichte Wiki →
          </a>
        </div>
      </div>
    </div>
    <div v-else>
      <h3>{{ formatType(entityDetails.uri) }}</h3>
      <div>
        No details available
      </div>
    </div>
  </div>
</template>

<style scoped>
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

.detail-link span {
  cursor: pointer;
  color: #2563eb;
  text-decoration: underline;
}

.detail-link span:hover {
  color: #1e40af;
}

.entity-image {
  max-width: 100%;
  max-height: 240px;
  object-fit: cover;
  border-radius: 8px;
}
</style>