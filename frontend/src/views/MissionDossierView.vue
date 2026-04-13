<template>
  <div class="mission-dossier-view">
    <!-- Header -->
    <header class="app-header">
      <div class="header-left">
        <div class="brand" @click="router.push('/')">
          <img src="/indramind.svg" alt="IndraMind" class="brand-logo" />
          PULSENET
        </div>
      </div>

      <div class="header-center">
        <h2 class="mission-title">{{ missionTitle }}</h2>
      </div>

      <div class="header-right">
        <div class="workflow-step">
          <span class="step-num mono">Mission Dossier</span>
        </div>
        <div class="step-divider"></div>
        <span class="status-indicator" :class="loadingStatus">
          <span class="dot"></span>
          {{ loadingText }}
        </span>
      </div>
    </header>

    <!-- Step Nav -->
    <DossierStepNav
      v-model="currentStep"
      :graphAvailable="!!graphData"
      :agentsAvailable="agents.length > 0"
      :deliberationAvailable="actions.length > 0"
      :reportAvailable="!!reportData"
      :interactionAvailable="!!reportData"
    />

    <!-- Content Area -->
    <main class="content-area">
      <div v-if="loading" class="loading-state">
        <div class="loading-spinner"></div>
        <span class="loading-text">Loading mission data...</span>
      </div>

      <div v-show="!loading && currentStep === 1" class="step-panel">
        <DossierGraphStep :graphData="graphData" :projectData="projectData" />
      </div>

      <div v-show="!loading && currentStep === 2" class="step-panel">
        <DossierAgentsStep :agents="agents" :agentStats="agentStats" />
      </div>

      <div v-show="!loading && currentStep === 3" class="step-panel">
        <DossierDeliberationStep :actions="actions" :results="results" />
      </div>

      <div v-show="!loading && currentStep === 4" class="step-panel">
        <DossierReportStep :reportData="reportData" />
      </div>

      <div v-show="!loading && currentStep === 5" class="step-panel">
        <DossierInteractionStep :simulationId="simulationId" :reportId="reportId" />
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import DossierStepNav from '../components/dossier/DossierStepNav.vue'
import DossierGraphStep from '../components/dossier/DossierGraphStep.vue'
import DossierAgentsStep from '../components/dossier/DossierAgentsStep.vue'
import DossierDeliberationStep from '../components/dossier/DossierDeliberationStep.vue'
import DossierReportStep from '../components/dossier/DossierReportStep.vue'
import DossierInteractionStep from '../components/dossier/DossierInteractionStep.vue'
import { getSimulation, getSimulationProfiles, getSimulationActions, getSimulationResults, getAgentStats } from '../api/simulation'
import { getGraphData, getProject } from '../api/graph'
import { getReport } from '../api/report'

const props = defineProps({
  simulationId: { type: String, required: true }
})

const router = useRouter()

// State
const currentStep = ref(1)
const loading = ref(true)
const simulationData = ref(null)
const projectData = ref(null)
const graphData = ref(null)
const agents = ref([])
const agentStats = ref([])
const actions = ref([])
const results = ref(null)
const reportData = ref(null)
const reportId = ref(null)

// Computed
const missionTitle = computed(() => {
  const req = simulationData.value?.simulation_requirement || simulationData.value?.mission_objective || ''
  return req.length > 60 ? req.slice(0, 60) + '...' : req || 'Mission Dossier'
})

const loadingStatus = computed(() => loading.value ? 'loading' : 'ready')
const loadingText = computed(() => loading.value ? 'Loading...' : 'Ready')

// Load all data
onMounted(async () => {
  try {
    // First: get simulation data to resolve linked IDs
    const simResponse = await getSimulation(props.simulationId)
    if (simResponse.success) {
      simulationData.value = simResponse.data
    }

    const projectId = simulationData.value?.project_id
    const graphId = simulationData.value?.graph_id
    reportId.value = simulationData.value?.report_id

    // Second: load everything in parallel
    const promises = []

    if (graphId) {
      promises.push(
        getGraphData(graphId).then(r => {
          if (r.success) graphData.value = r.data
        }).catch(() => {})
      )
    }

    if (projectId) {
      promises.push(
        getProject(projectId).then(r => {
          if (r.success) projectData.value = r.data
        }).catch(() => {})
      )
    }

    promises.push(
      getSimulationProfiles(props.simulationId).then(r => {
        if (r.success) agents.value = r.data?.profiles || r.data || []
      }).catch(() => {})
    )

    promises.push(
      getAgentStats(props.simulationId).then(r => {
        if (r.success) agentStats.value = r.data?.stats || r.data || []
      }).catch(() => {})
    )

    promises.push(
      getSimulationActions(props.simulationId, { limit: 10000 }).then(r => {
        if (r.success) actions.value = r.data?.deliberation_actions || r.data?.actions || []
      }).catch(() => {})
    )

    promises.push(
      getSimulationResults(props.simulationId).then(r => {
        if (r.success) results.value = r.data
      }).catch(() => {})
    )

    if (reportId.value) {
      promises.push(
        getReport(reportId.value).then(r => {
          if (r.success) reportData.value = r.data
        }).catch(() => {})
      )
    }

    await Promise.allSettled(promises)

    // Auto-select the most relevant step
    if (reportData.value) currentStep.value = 4
    else if (actions.value.length > 0) currentStep.value = 3
    else if (agents.value.length > 0) currentStep.value = 2
    else currentStep.value = 1

  } catch (err) {
    console.error('Failed to load mission data:', err)
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.mission-dossier-view {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: #0a0a0a;
  color: #e0e0e0;
}

/* Header - matches existing MainView pattern */
.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  height: 56px;
  background: #000;
  border-bottom: 1px solid #1a1a1a;
  z-index: 100;
}

.header-left { display: flex; align-items: center; }

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 14px;
  font-weight: 700;
  letter-spacing: 2px;
  color: #FF4500;
  cursor: pointer;
}

.brand-logo {
  height: 24px;
  width: auto;
}

.header-center {
  flex: 1;
  text-align: center;
}

.mission-title {
  font-size: 13px;
  font-weight: 400;
  color: #888;
  margin: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 500px;
  margin: 0 auto;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.workflow-step { display: flex; align-items: center; gap: 8px; }

.step-num {
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  color: #888;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.step-divider {
  width: 1px;
  height: 20px;
  background: #222;
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 6px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  text-transform: uppercase;
}

.status-indicator.loading { color: #e08600; }
.status-indicator.ready { color: #16a34a; }

.dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
}

.status-indicator.loading .dot {
  animation: pulse 1.5s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}

/* Content Area */
.content-area {
  flex: 1;
  overflow: hidden;
  position: relative;
}

.step-panel {
  height: 100%;
  overflow: hidden;
}

/* Loading */
.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  gap: 16px;
}

.loading-spinner {
  width: 32px;
  height: 32px;
  border: 2px solid #222;
  border-top-color: #FF4500;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.loading-text {
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px;
  color: #666;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.mono { font-family: 'JetBrains Mono', monospace; }
</style>
