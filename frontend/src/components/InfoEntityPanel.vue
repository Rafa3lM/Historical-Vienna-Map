<script setup lang="ts">
import type {InfoEntityDetails} from "../types/Entity.ts";

defineProps<{
  entityDetails: InfoEntityDetails;
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

function loadGeoEntityDetails(uri: string) {
  emit('open-geo', uri);
}
</script>

<template>
  <div class="info-details-panel">
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

        <!-- Named after -->
        <div v-if="entityDetails.namedAfter" class="detail-item">
          <strong>Named After:</strong>
          <span>{{ formatUriList(entityDetails.namedAfter) }}</span>
        </div>

        <!-- Birth Date -->
        <div v-if="entityDetails.birthDate" class="detail-item">
          <strong>Birth Date:</strong>
          <span>
              {{ entityDetails.birthDate }}
            </span>
        </div>

        <!-- Death Date -->
        <div v-if="entityDetails.deathDate" class="detail-item">
          <strong>Death Date:</strong>
          <span>
              {{ entityDetails.deathDate }}
            </span>
        </div>

        <!-- Gender -->
        <div v-if="entityDetails.gender" class="detail-item">
          <strong>Gender:</strong>
          <span>
              {{ entityDetails.gender }}
            </span>
        </div>

        <!-- Architect of -->
        <div v-if="entityDetails.architectOf" class="detail-item">
          <strong>Architect of:</strong>
          <div v-for="building in entityDetails.architectOf"
               :key="building"
               class="detail-link">
            <span @click="!loadingDetails && loadGeoEntityDetails(building)">{{ formatType(building) }}</span>
          </div>
        </div>

        <!-- Resident of -->
        <div v-if="entityDetails.residentOf" class="detail-item">
          <strong>Architect of:</strong>
          <div v-for="building in entityDetails.residentOf"
               :key="building"
               class="detail-link">
            <span @click="!loadingDetails && loadGeoEntityDetails(building)">{{ formatType(building) }}</span>
          </div>
        </div>

        <!-- Named after -->
        <div v-if="entityDetails.namedAfter" class="detail-item">
          <strong>Architect of:</strong>
          <div v-for="building in entityDetails.namedAfter"
               :key="building"
               class="detail-link">
            <span @click="!loadingDetails && loadGeoEntityDetails(building)">{{ formatType(building) }}</span>
          </div>
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
    <div v-else class="details-content">
      <h3>{{ formatType(entityDetails.uri) }}</h3>
      <div>
        No details available
      </div>
    </div>
  </div>
</template>

<style scoped>
/* Details Panel */
.info-details-panel {
  position: absolute;
  bottom: 20px;
  left: 440px;
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