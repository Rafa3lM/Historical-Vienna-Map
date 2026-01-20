<script setup lang="ts">
import {computed} from "vue";

const props = defineProps<{
  fromYear: number;
  toYear: number;
}>();

const emit = defineEmits<{
  (e: "update:fromYear", value: number): void;
  (e: "update:toYear", value: number): void;
}>();

const min = 0;
const max = new Date().getFullYear();

/* Local proxies */
const from = computed({
  get: () => props.fromYear,
  set: v => emit("update:fromYear", v)
});

const to = computed({
  get: () => props.toYear,
  set: v => emit("update:toYear", v)
});

/* Ensure order */
function onFromInput() {
  if (from.value >= to.value) {
    from.value = to.value - 1;
  }
}

function onToInput() {
  if (to.value <= from.value) {
    to.value = from.value + 1;
  }
}

/* Percent helpers */
const range = max - min;

const leftPos = computed(() =>
    ((from.value - min) / range) * 100
);

const rightHandlePos = computed(() =>
    ((to.value - min) / range) * 100
);

const rightPos = computed(() =>
    100 - rightHandlePos.value
);

const leftWidth = computed(() =>
    leftPos.value
);

const rightWidth = computed(() =>
    100 - rightHandlePos.value
);

</script>

<template>
  <div class="range-slider">
    <div class="slider-track">
      <div class="track-left" :style="{ width: leftWidth + '%' }"></div>
      <div class="track-range" :style="{ left: leftPos + '%', right: rightPos + '%' }"></div>
      <div class="track-right" :style="{ width: rightWidth + '%' }"></div>

      <!-- Handles -->
      <span class="handle" :style="{ left: leftPos + '%' }"></span>
      <span class="handle" :style="{ left: rightHandlePos + '%' }"></span>

      <!-- Tooltips -->
      <div class="tooltip" :style="{ left: leftPos + '%' }">
        {{ fromYear }}
      </div>
      <div class="tooltip" :style="{ left: rightHandlePos + '%' }">
        {{ toYear }}
      </div>
    </div>

    <!-- Invisible native inputs -->
    <input
        type="range"
        :min="min"
        :max="max"
        v-model.number="from"
        @input="onFromInput"
    />
    <input
        type="range"
        :min="min"
        :max="max"
        v-model.number="to"
        @input="onToInput"
    />
  </div>
</template>

<style scoped>
.range-slider {
  position: relative;
  height: 48px;
  width: 100%;
}

/* TRACK */
.slider-track {
  position: absolute;
  left: 12px;
  right: 12px;
  top: 50%;
  transform: translateY(-50%);
  height: 14px;
}

.track-left,
.track-right {
  position: absolute;
  height: 10px;
  background: #d1d5db;
  border-radius: 10px;
}

.track-left {
  left: 0;
}

.track-right {
  right: 0;
}

.track-range {
  position: absolute;
  height: 14px;
  background: #3b82f6;
  border-radius: 14px;
}

/* HANDLES */
.handle {
  position: absolute;
  top: -5px;
  width: 24px;
  height: 24px;
  margin-left: -12px;
  background: white;
  border-radius: 25%;
  box-shadow: 0 3px 8px rgba(0, 0, 0, 0.35);
  z-index: 2;
}

/* TOOLTIP */
.tooltip {
  position: absolute;
  top: -38px;
  margin-left: -14px;
  width: 28px;
  height: 28px;
  background: #3b82f6;
  color: white;
  border-radius: 50%;
  font-size: 12px;
  font-weight: 700;
  text-align: center;
  line-height: 28px;
  opacity: 0;
  transition: opacity 0.2s;
}

.slider-track:hover .tooltip {
  opacity: 1;
}

input[type="range"] {
  position: absolute;
  width: 100%;
  height: 14px;
  top: 50%;
  transform: translateY(-50%);
  opacity: 0;
  pointer-events: none;
}

input[type="range"]::-webkit-slider-thumb {
  pointer-events: auto;
}

input[type="range"]::-moz-range-thumb {
  pointer-events: auto;
}

</style>