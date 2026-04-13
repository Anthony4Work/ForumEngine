<template>
  <nav class="dossier-step-nav">
    <button
      v-for="step in steps"
      :key="step.id"
      class="step-tab"
      :class="{ active: modelValue === step.id, disabled: !step.available }"
      @click="step.available && $emit('update:modelValue', step.id)"
    >
      <span class="step-icon">{{ step.icon }}</span>
      <span class="step-label">{{ step.label }}</span>
    </button>
  </nav>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  modelValue: { type: Number, default: 1 },
  graphAvailable: { type: Boolean, default: false },
  agentsAvailable: { type: Boolean, default: false },
  deliberationAvailable: { type: Boolean, default: false },
  reportAvailable: { type: Boolean, default: false },
  interactionAvailable: { type: Boolean, default: false }
})

defineEmits(['update:modelValue'])

const steps = computed(() => [
  { id: 1, label: 'Knowledge Graph', icon: '◇', available: props.graphAvailable },
  { id: 2, label: 'Agent Profiles', icon: '◈', available: props.agentsAvailable },
  { id: 3, label: 'Deliberation', icon: '⬡', available: props.deliberationAvailable },
  { id: 4, label: 'Report', icon: '◆', available: props.reportAvailable },
  { id: 5, label: 'Interaction', icon: '◉', available: props.interactionAvailable }
])
</script>

<style scoped>
.dossier-step-nav {
  display: flex;
  gap: 2px;
  background: #111;
  border-bottom: 1px solid #222;
  padding: 0 24px;
}

.step-tab {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 14px 20px;
  background: none;
  border: none;
  color: #666;
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px;
  letter-spacing: 0.5px;
  text-transform: uppercase;
  cursor: pointer;
  position: relative;
  transition: color 0.2s, background 0.2s;
}

.step-tab:hover:not(.disabled) {
  color: #ccc;
  background: rgba(255, 255, 255, 0.03);
}

.step-tab.active {
  color: #FF4500;
}

.step-tab.active::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 2px;
  background: #FF4500;
}

.step-tab.disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.step-icon {
  font-size: 14px;
}
</style>
