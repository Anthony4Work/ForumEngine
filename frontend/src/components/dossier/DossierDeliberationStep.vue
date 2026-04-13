<template>
  <div class="dossier-deliberation-step">
    <!-- Phase Stepper -->
    <div class="phase-stepper">
      <div
        v-for="(phaseDef, idx) in phaseNames"
        :key="idx"
        class="phase-step"
        :class="{
          active: selectedPhase === idx + 1,
          'has-data': phaseHasData(idx + 1)
        }"
        @click="selectedPhase = idx + 1"
      >
        <div class="phase-number">{{ idx + 1 }}</div>
        <div class="phase-label">{{ phaseDef }}</div>
        <div class="phase-count mono" v-if="getPhaseActionCount(idx + 1)">{{ getPhaseActionCount(idx + 1) }}</div>
      </div>
    </div>

    <!-- Phase Content -->
    <div class="phase-content" v-if="selectedPhaseData">
      <!-- Phase Header -->
      <div class="phase-header">
        <h3 class="phase-title">Phase {{ selectedPhase }}: {{ phaseNames[selectedPhase - 1] }}</h3>
        <div class="phase-meta">
          <span class="meta-pill mono">{{ Object.keys(selectedPhaseData).length }} rounds</span>
          <span class="meta-pill mono">{{ getPhaseActionCount(selectedPhase) }} actions</span>
          <span class="meta-pill mono" v-if="getPhaseAgents(selectedPhase).length">{{ getPhaseAgents(selectedPhase).length }} agents</span>
        </div>
      </div>

      <!-- Rounds Accordion -->
      <div class="rounds-container">
        <div
          v-for="roundNum in sortedRounds"
          :key="roundNum"
          class="round-block"
        >
          <div class="round-header" @click="toggleRound(roundNum)">
            <svg :class="{ rotated: expandedRounds.has(roundNum) }" viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="6 9 12 15 18 9"></polyline>
            </svg>
            <span class="round-label">Round {{ roundNum }}</span>
            <span class="round-count mono">{{ selectedPhaseData[roundNum]?.length || 0 }} actions</span>
          </div>

          <div class="round-actions" v-show="expandedRounds.has(roundNum)">
            <DeliberationActionCard
              v-for="(action, aIdx) in selectedPhaseData[roundNum]"
              :key="aIdx"
              :action="action"
            />
          </div>
        </div>
      </div>

      <!-- Phase Summary -->
      <div class="phase-summary" v-if="phaseSummary">
        <div class="summary-header">
          <h4 class="summary-title">Phase Summary</h4>
        </div>
        <div class="summary-body">
          <p class="summary-narrative" v-if="phaseSummary.summary">{{ phaseSummary.summary }}</p>

          <div v-if="phaseSummary.key_decisions?.length" class="summary-section">
            <span class="summary-label">Key Decisions</span>
            <ul class="decision-list">
              <li v-for="(d, i) in phaseSummary.key_decisions" :key="i">{{ d }}</li>
            </ul>
          </div>

          <div v-if="phaseSummary.consensus_points?.length" class="summary-section">
            <span class="summary-label">Points of Consensus</span>
            <ul class="decision-list consensus">
              <li v-for="(c, i) in phaseSummary.consensus_points" :key="i">{{ c }}</li>
            </ul>
          </div>

          <div v-if="phaseSummary.disagreement_points?.length" class="summary-section">
            <span class="summary-label">Points of Disagreement</span>
            <ul class="decision-list disagreement">
              <li v-for="(d, i) in phaseSummary.disagreement_points" :key="i">{{ d }}</li>
            </ul>
          </div>

          <div v-if="phaseSummary.intelligence_gaps?.length" class="summary-section">
            <span class="summary-label">Intelligence Gaps</span>
            <ul class="decision-list gaps">
              <li v-for="(g, i) in phaseSummary.intelligence_gaps" :key="i">{{ g }}</li>
            </ul>
          </div>
        </div>
      </div>

      <!-- COA Table (for phases 3-6) -->
      <div class="coa-table" v-if="selectedPhase >= 3 && selectedPhase <= 6 && coas.length > 0">
        <div class="summary-header">
          <h4 class="summary-title">Courses of Action</h4>
        </div>
        <div class="coa-grid">
          <div
            v-for="(coa, idx) in coas"
            :key="idx"
            class="coa-card"
            :class="{ selected: coa.selected }"
          >
            <div class="coa-header">
              <span class="coa-name">{{ coa.name || `COA ${idx + 1}` }}</span>
              <span class="coa-score mono" v-if="coa.total_score != null">{{ coa.total_score }}</span>
              <span v-if="coa.selected" class="coa-selected-badge">SELECTED</span>
            </div>
            <p class="coa-desc" v-if="coa.description">{{ coa.description }}</p>
            <span class="coa-proposer mono" v-if="coa.proposed_by">Proposed by: {{ coa.proposed_by }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- No data state -->
    <div v-else class="empty-state">
      <span class="empty-icon">⬡</span>
      <span>No deliberation data for Phase {{ selectedPhase }}</span>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import DeliberationActionCard from './DeliberationActionCard.vue'

const props = defineProps({
  actions: { type: Array, default: () => [] },
  results: { type: Object, default: null }
})

const phaseNames = [
  'Mission Analysis',
  'Intelligence Preparation',
  'COA Development',
  'COA Analysis',
  'COA Comparison',
  'COA Decision',
  'Orders Production'
]

const selectedPhase = ref(1)
const expandedRounds = ref(new Set([1]))

// Group actions by phase then round
const actionsByPhase = computed(() => {
  const grouped = {}
  for (const action of props.actions) {
    const p = action.phase || 1
    if (!grouped[p]) grouped[p] = {}
    const r = action.round_num || 1
    if (!grouped[p][r]) grouped[p][r] = []
    grouped[p][r].push(action)
  }
  // Sort actions within each round chronologically
  for (const p of Object.keys(grouped)) {
    for (const r of Object.keys(grouped[p])) {
      grouped[p][r].sort((a, b) => {
        if (a.timestamp && b.timestamp) return new Date(a.timestamp) - new Date(b.timestamp)
        return 0
      })
    }
  }
  return grouped
})

const selectedPhaseData = computed(() => actionsByPhase.value[selectedPhase.value] || null)

const sortedRounds = computed(() => {
  if (!selectedPhaseData.value) return []
  return Object.keys(selectedPhaseData.value).map(Number).sort((a, b) => a - b)
})

const phaseHasData = (phase) => !!actionsByPhase.value[phase]

const getPhaseActionCount = (phase) => {
  const phaseData = actionsByPhase.value[phase]
  if (!phaseData) return 0
  return Object.values(phaseData).reduce((sum, round) => sum + round.length, 0)
}

const getPhaseAgents = (phase) => {
  const phaseData = actionsByPhase.value[phase]
  if (!phaseData) return []
  const agents = new Set()
  Object.values(phaseData).forEach(round => {
    round.forEach(a => agents.add(a.agent_name || a.agent_id))
  })
  return Array.from(agents)
}

const phaseSummary = computed(() => {
  if (!props.results?.phases) return null
  return props.results.phases.find(p => p.phase === selectedPhase.value || p.phase_number === selectedPhase.value) || null
})

const coas = computed(() => {
  if (!props.results?.coas) return []
  return props.results.coas
})

const toggleRound = (roundNum) => {
  const newSet = new Set(expandedRounds.value)
  if (newSet.has(roundNum)) {
    newSet.delete(roundNum)
  } else {
    newSet.add(roundNum)
  }
  expandedRounds.value = newSet
}

// Auto-select first phase with data
watch(() => props.actions, () => {
  if (props.actions.length > 0 && !phaseHasData(selectedPhase.value)) {
    const firstPhase = Object.keys(actionsByPhase.value).map(Number).sort((a, b) => a - b)[0]
    if (firstPhase) selectedPhase.value = firstPhase
  }
}, { immediate: true })

// Reset expanded rounds when switching phases
watch(selectedPhase, () => {
  expandedRounds.value = new Set([sortedRounds.value[0] || 1])
})
</script>

<style scoped>
.dossier-deliberation-step {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

/* Phase Stepper */
.phase-stepper {
  display: flex;
  padding: 12px 24px;
  gap: 4px;
  background: #111;
  border-bottom: 1px solid #222;
  overflow-x: auto;
}

.phase-step {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 14px;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
  white-space: nowrap;
  border: 1px solid transparent;
}

.phase-step:hover { background: rgba(255, 255, 255, 0.03); }

.phase-step.active {
  background: rgba(255, 69, 0, 0.08);
  border-color: rgba(255, 69, 0, 0.3);
}

.phase-step:not(.has-data) {
  opacity: 0.3;
}

.phase-number {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: #222;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  font-weight: 700;
  color: #888;
}

.phase-step.active .phase-number {
  background: #FF4500;
  color: #fff;
}

.phase-label {
  font-size: 12px;
  color: #999;
}

.phase-step.active .phase-label {
  color: #FF4500;
  font-weight: 600;
}

.phase-count {
  font-size: 10px;
  color: #555;
  background: #1a1a1a;
  padding: 2px 6px;
  border-radius: 8px;
}

/* Phase Content */
.phase-content {
  flex: 1;
  overflow-y: auto;
  padding: 20px 24px;
}

.phase-header {
  margin-bottom: 20px;
}

.phase-title {
  font-size: 18px;
  font-weight: 700;
  color: #e0e0e0;
  margin: 0 0 8px 0;
}

.phase-meta {
  display: flex;
  gap: 8px;
}

.meta-pill {
  font-size: 11px;
  color: #888;
  background: #1a1a1a;
  padding: 3px 10px;
  border-radius: 4px;
  border: 1px solid #222;
}

/* Rounds */
.rounds-container {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.round-block {
  border: 1px solid #222;
  border-radius: 8px;
  overflow: hidden;
}

.round-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  background: #151515;
  cursor: pointer;
  transition: background 0.2s;
}

.round-header:hover {
  background: #1a1a1a;
}

.round-header svg {
  color: #555;
  transition: transform 0.2s;
}

.round-header svg.rotated {
  transform: rotate(180deg);
}

.round-label {
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px;
  font-weight: 600;
  color: #ccc;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.round-count {
  font-size: 11px;
  color: #555;
  margin-left: auto;
}

.round-actions {
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  background: #111;
}

/* Phase Summary */
.phase-summary, .coa-table {
  margin-top: 20px;
  border: 1px solid #252525;
  border-radius: 8px;
  overflow: hidden;
}

.summary-header {
  padding: 12px 16px;
  background: #151515;
  border-bottom: 1px solid #222;
}

.summary-title {
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 1px;
  color: #888;
  margin: 0;
}

.summary-body {
  padding: 16px;
}

.summary-narrative {
  font-size: 14px;
  line-height: 1.7;
  color: #ccc;
  margin: 0 0 16px 0;
}

.summary-section {
  margin-bottom: 14px;
}

.summary-label {
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: #666;
  display: block;
  margin-bottom: 6px;
}

.decision-list {
  margin: 0;
  padding-left: 18px;
  list-style: none;
}

.decision-list li {
  font-size: 13px;
  line-height: 1.6;
  color: #bbb;
  padding: 3px 0;
  position: relative;
}

.decision-list li::before {
  content: '▸';
  position: absolute;
  left: -16px;
  color: #FF4500;
}

.decision-list.consensus li::before { color: #16a34a; }
.decision-list.disagreement li::before { color: #dc2626; }
.decision-list.gaps li::before { color: #e08600; }

/* COA Table */
.coa-grid {
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.coa-card {
  background: #1a1a1a;
  border: 1px solid #252525;
  border-radius: 6px;
  padding: 14px;
}

.coa-card.selected {
  border-color: #FF4500;
  background: rgba(255, 69, 0, 0.04);
}

.coa-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 6px;
}

.coa-name {
  font-size: 14px;
  font-weight: 600;
  color: #e0e0e0;
}

.coa-score {
  font-size: 13px;
  color: #FF4500;
  font-weight: 700;
}

.coa-selected-badge {
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  color: #FF4500;
  background: rgba(255, 69, 0, 0.1);
  padding: 2px 8px;
  border-radius: 3px;
  margin-left: auto;
}

.coa-desc {
  font-size: 13px;
  line-height: 1.6;
  color: #bbb;
  margin: 0 0 4px 0;
}

.coa-proposer {
  font-size: 11px;
  color: #666;
}

.mono { font-family: 'JetBrains Mono', monospace; }

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 300px;
  gap: 12px;
  color: #555;
}

.empty-icon { font-size: 32px; color: #333; }
</style>
