<template>
  <div class="simulation-panel">
    <!-- Top Control Bar -->
    <div class="control-bar">
      <div class="status-group">
        <!-- MDMP Deliberation Progress -->
        <div class="deliberation-status" :class="{ active: runStatus.running, completed: runStatus.completed }">
          <div class="deliberation-header">
            <svg class="platform-icon" viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2">
              <polygon points="12 2 22 8.5 22 15.5 12 22 2 15.5 2 8.5 12 2"></polygon>
              <line x1="12" y1="22" x2="12" y2="15.5"></line>
              <polyline points="22 8.5 12 15.5 2 8.5"></polyline>
            </svg>
            <span class="platform-name">MDMP Deliberation</span>
            <span v-if="runStatus.completed" class="status-badge">
              <svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="3">
                <polyline points="20 6 9 17 4 12"></polyline>
              </svg>
            </span>
          </div>
          <div class="platform-stats">
            <span class="stat">
              <span class="stat-label">PHASE</span>
              <span class="stat-value mono">{{ runStatus.current_phase || 0 }}<span class="stat-total">/7</span></span>
            </span>
            <span class="stat">
              <span class="stat-label">ROUND</span>
              <span class="stat-value mono">{{ runStatus.phase_round || 0 }}<span class="stat-total">/{{ currentPhaseMaxRounds }}</span></span>
            </span>
            <span class="stat">
              <span class="stat-label">Elapsed</span>
              <span class="stat-value mono">{{ elapsedTime }}</span>
            </span>
            <span class="stat">
              <span class="stat-label">ACTS</span>
              <span class="stat-value mono">{{ runStatus.deliberation_actions_count || 0 }}</span>
            </span>
          </div>
        </div>
      </div>

      <div class="action-controls">
        <button
          class="action-btn primary"
          :disabled="phase !== 2 || isGeneratingReport"
          @click="handleNextStep"
        >
          <span v-if="isGeneratingReport" class="loading-spinner-small"></span>
          {{ isGeneratingReport ? 'Starting...' : 'Generate Results Report' }}
          <span v-if="!isGeneratingReport" class="arrow-icon">→</span>
        </button>
      </div>
    </div>

    <!-- MDMP Phase Stepper -->
    <div class="phase-stepper">
      <div
        v-for="(phaseDef, idx) in mdmpPhases"
        :key="idx"
        class="phase-step"
        :class="{
          completed: (runStatus.current_phase || 0) > idx + 1,
          active: (runStatus.current_phase || 0) === idx + 1,
          pending: (runStatus.current_phase || 0) < idx + 1
        }"
      >
        <div class="phase-number">{{ idx + 1 }}</div>
        <div class="phase-label">{{ phaseDef }}</div>
      </div>
    </div>

    <!-- Main Content: Action Timeline -->
    <div class="main-content-area" ref="scrollContainer">
      <!-- Timeline Header -->
      <div class="timeline-header" v-if="allActions.length > 0">
        <div class="timeline-stats">
          <span class="total-count">TOTAL ACTIONS: <span class="mono">{{ allActions.length }}</span></span>
          <span class="stat-pill">
            <span class="stat-pill-label">PHASE</span>
            <span class="mono">{{ currentPhaseName }}</span>
          </span>
          <span class="stat-pill">
            <span class="stat-pill-label">COAs</span>
            <span class="mono">{{ runStatus.coas_proposed || 0 }}</span>
          </span>
        </div>
      </div>

      <!-- Timeline Feed -->
      <div class="timeline-feed">
        <div class="timeline-axis"></div>

        <TransitionGroup name="timeline-item">
          <div
            v-for="action in chronologicalActions"
            :key="action._uniqueId || action.id || `${action.timestamp}-${action.agent_id}`"
            class="timeline-item"
            :class="getRoleClass(action.agent_role)"
          >
            <div class="timeline-marker">
              <div class="marker-dot"></div>
            </div>

            <div class="timeline-card">
              <div class="card-header">
                <div class="agent-info">
                  <div class="avatar-placeholder" :class="getRoleClass(action.agent_role)">{{ getRoleAbbrev(action.agent_role) }}</div>
                  <div class="agent-details">
                    <span class="agent-name">{{ action.agent_name || action.agent_id }}</span>
                    <span class="agent-role-tag" :class="getRoleClass(action.agent_role)">{{ action.agent_role || 'STAFF' }}</span>
                  </div>
                </div>

                <div class="header-meta">
                  <div class="phase-indicator">
                    <span class="phase-tag">P{{ action.phase || '?' }}</span>
                  </div>
                  <div class="action-badge" :class="getActionTypeClass(action.action_type)">
                    {{ getActionTypeLabel(action.action_type) }}
                  </div>
                </div>
              </div>

              <div class="card-body">
                <!-- Main content display -->
                <div v-if="action.content" class="content-text main-text">
                  {{ truncateContent(action.content, 400) }}
                </div>

                <!-- Fallback to action_args.content if no top-level content -->
                <div v-else-if="action.action_args?.content" class="content-text main-text">
                  {{ truncateContent(action.action_args.content, 400) }}
                </div>

                <!-- Confidence indicator -->
                <div v-if="action.confidence != null" class="confidence-bar">
                  <span class="confidence-label">Confidence</span>
                  <div class="confidence-track">
                    <div class="confidence-fill" :style="{ width: (action.confidence * 100) + '%' }"></div>
                  </div>
                  <span class="confidence-value mono">{{ Math.round(action.confidence * 100) }}%</span>
                </div>

                <!-- Risk assessment -->
                <div v-if="action.risk_assessment" class="risk-assessment">
                  <svg class="icon-small" viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path>
                    <line x1="12" y1="9" x2="12" y2="13"></line>
                    <line x1="12" y1="17" x2="12.01" y2="17"></line>
                  </svg>
                  <span>{{ truncateContent(action.risk_assessment, 200) }}</span>
                </div>

                <!-- References -->
                <div v-if="action.references && action.references.length > 0" class="references-block">
                  <span class="ref-label">References:</span>
                  <span v-for="(ref, ri) in action.references" :key="ri" class="ref-tag">{{ ref }}</span>
                </div>
              </div>

              <div class="card-footer">
                <span class="time-tag">P{{ action.phase || '?' }} R{{ action.round_num || '?' }} &bull; {{ formatActionTime(action.timestamp) }}</span>
              </div>
            </div>
          </div>
        </TransitionGroup>

        <div v-if="allActions.length === 0" class="waiting-state">
          <div class="pulse-ring"></div>
          <span>Waiting for deliberation actions...</span>
        </div>
      </div>
    </div>

    <!-- Bottom Info / Logs -->
    <div class="system-logs">
      <div class="log-header">
        <span class="log-title">DELIBERATION MONITOR</span>
        <span class="log-id">{{ simulationId || 'NO_SIMULATION' }}</span>
      </div>
      <div class="log-content" ref="logContent">
        <div class="log-line" v-for="(log, idx) in systemLogs" :key="idx">
          <span class="log-time">{{ log.time }}</span>
          <span class="log-msg">{{ log.msg }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import {
  startSimulation,
  stopSimulation,
  getRunStatus,
  getRunStatusDetail
} from '../api/simulation'
import { generateReport } from '../api/report'

const props = defineProps({
  simulationId: String,
  maxRounds: Number,
  minutesPerRound: {
    type: Number,
    default: 30
  },
  projectData: Object,
  graphData: Object,
  systemLogs: Array
})

const emit = defineEmits(['go-back', 'next-step', 'add-log', 'update-status'])

const router = useRouter()

// MDMP Phase definitions
const mdmpPhases = [
  'Mission Analysis',
  'Intelligence Preparation',
  'COA Development',
  'COA Analysis (Wargaming)',
  'COA Comparison',
  'COA Decision',
  'Orders Production'
]

// State
const isGeneratingReport = ref(false)
const phase = ref(0) // 0: not started, 1: running, 2: completed
const isStarting = ref(false)
const isStopping = ref(false)
const startError = ref(null)
const runStatus = ref({})
const allActions = ref([])
const actionIds = ref(new Set())
const scrollContainer = ref(null)
const prevPhase = ref(0)
const prevPhaseRound = ref(0)

// Computed
const chronologicalActions = computed(() => {
  return allActions.value
})

const totalActionsCount = computed(() => {
  return allActions.value.length
})

const currentPhaseName = computed(() => {
  const idx = (runStatus.value.current_phase || 1) - 1
  return mdmpPhases[idx] || 'Unknown'
})

const currentPhaseMaxRounds = computed(() => {
  return runStatus.value.phase_max_rounds || props.maxRounds || '-'
})

const formatElapsedTime = (currentRound) => {
  if (!currentRound || currentRound <= 0) return '0h 0m'
  const totalMinutes = currentRound * props.minutesPerRound
  const hours = Math.floor(totalMinutes / 60)
  const minutes = totalMinutes % 60
  return `${hours}h ${minutes}m`
}

const elapsedTime = computed(() => {
  const totalRounds = (runStatus.value.phase_round || 0)
  return formatElapsedTime(totalRounds)
})

// Methods
const addLog = (msg) => {
  emit('add-log', msg)
}

const resetAllState = () => {
  phase.value = 0
  runStatus.value = {}
  allActions.value = []
  actionIds.value = new Set()
  prevPhase.value = 0
  prevPhaseRound.value = 0
  startError.value = null
  isStarting.value = false
  isStopping.value = false
  stopPolling()
}

// Start deliberation
const doStartSimulation = async () => {
  if (!props.simulationId) {
    addLog('Error: Missing simulationId')
    return
  }

  resetAllState()

  isStarting.value = true
  startError.value = null
  addLog('Starting MDMP deliberation...')
  emit('update-status', 'processing')

  try {
    const params = {
      simulation_id: props.simulationId,
      platform: 'deliberation',
      force: true,
      enable_graph_memory_update: true
    }

    if (props.maxRounds) {
      params.max_rounds = props.maxRounds
      addLog(`Max rounds per phase: ${props.maxRounds}`)
    }

    addLog('Graph memory update enabled')

    const res = await startSimulation(params)

    if (res.success && res.data) {
      if (res.data.force_restarted) {
        addLog('Cleared previous deliberation logs, restarting')
      }
      addLog('Deliberation engine started successfully')
      addLog(`  PID: ${res.data.process_pid || '-'}`)

      phase.value = 1
      runStatus.value = res.data

      startStatusPolling()
      startDetailPolling()
    } else {
      startError.value = res.error || 'Start failed'
      addLog(`Start failed: ${res.error || 'Unknown error'}`)
      emit('update-status', 'error')
    }
  } catch (err) {
    startError.value = err.message
    addLog(`Start error: ${err.message}`)
    emit('update-status', 'error')
  } finally {
    isStarting.value = false
  }
}

// Stop deliberation
const handleStopSimulation = async () => {
  if (!props.simulationId) return

  isStopping.value = true
  addLog('Stopping deliberation...')

  try {
    const res = await stopSimulation({ simulation_id: props.simulationId })

    if (res.success) {
      addLog('Deliberation stopped')
      phase.value = 2
      stopPolling()
      emit('update-status', 'completed')
    } else {
      addLog(`Stop failed: ${res.error || 'Unknown error'}`)
    }
  } catch (err) {
    addLog(`Stop error: ${err.message}`)
  } finally {
    isStopping.value = false
  }
}

// Polling
let statusTimer = null
let detailTimer = null

const startStatusPolling = () => {
  statusTimer = setInterval(fetchRunStatus, 2000)
}

const startDetailPolling = () => {
  detailTimer = setInterval(fetchRunStatusDetail, 3000)
}

const stopPolling = () => {
  if (statusTimer) {
    clearInterval(statusTimer)
    statusTimer = null
  }
  if (detailTimer) {
    clearInterval(detailTimer)
    detailTimer = null
  }
}

const fetchRunStatus = async () => {
  if (!props.simulationId) return

  try {
    const res = await getRunStatus(props.simulationId)

    if (res.success && res.data) {
      const data = res.data
      runStatus.value = data

      // Detect phase transitions
      const currentPhaseNum = data.current_phase || 0
      const currentRound = data.phase_round || 0

      if (currentPhaseNum > prevPhase.value) {
        const phaseName = mdmpPhases[currentPhaseNum - 1] || 'Unknown'
        addLog(`Phase ${currentPhaseNum}: ${phaseName} - Round ${currentRound}/${data.phase_max_rounds || '?'}`)
        prevPhase.value = currentPhaseNum
        prevPhaseRound.value = currentRound
      } else if (currentPhaseNum === prevPhase.value && currentRound > prevPhaseRound.value) {
        const phaseName = mdmpPhases[currentPhaseNum - 1] || 'Unknown'
        addLog(`Phase ${currentPhaseNum}: ${phaseName} - Round ${currentRound}/${data.phase_max_rounds || '?'} | Acts: ${data.deliberation_actions_count || 0}`)
        prevPhaseRound.value = currentRound
      }

      // Check completion
      const isCompleted = checkDeliberationCompleted(data)

      if (isCompleted) {
        addLog('Deliberation completed')
        phase.value = 2
        stopPolling()
        emit('update-status', 'completed')
      }
    }
  } catch (err) {
    console.warn('Failed to fetch run status:', err)
  }
}

const checkDeliberationCompleted = (data) => {
  if (!data) return false
  if (data.runner_status === 'completed' || data.runner_status === 'stopped') return true
  if (data.completed === true) return true
  return false
}

const fetchRunStatusDetail = async () => {
  if (!props.simulationId) return

  try {
    const res = await getRunStatusDetail(props.simulationId)

    if (res.success && res.data) {
      const serverActions = res.data.all_actions || []

      let newActionsAdded = 0
      serverActions.forEach(action => {
        const actionId = action.id || `${action.timestamp}-${action.agent_id}-${action.action_type}-${action.phase}-${action.round_num}`

        if (!actionIds.value.has(actionId)) {
          actionIds.value.add(actionId)
          allActions.value.push({
            ...action,
            _uniqueId: actionId
          })
          newActionsAdded++
        }
      })
    }
  } catch (err) {
    console.warn('Failed to fetch status detail:', err)
  }
}

// Helpers
const getActionTypeLabel = (type) => {
  const labels = {
    'analyze_terrain': 'Analyze Terrain',
    'assess_threat': 'Assess Threat',
    'assess_logistics': 'Assess Logistics',
    'assess_comms': 'Assess Comms',
    'propose_coa': 'Propose COA',
    'refine_coa': 'Refine COA',
    'evaluate_risk': 'Evaluate Risk',
    'challenge_assumption': 'Challenge',
    'wargame_move': 'Wargame Move',
    'wargame_counter': 'Wargame Counter',
    'score_coa': 'Score COA',
    'vote_coa': 'Vote COA',
    'decide_coa': 'Decision',
    'request_intel': 'Request Intel',
    'provide_intel': 'Provide Intel',
    'identify_gap': 'Identify Gap',
    'concur': 'Concur',
    'dissent': 'Dissent',
    'recommend': 'Recommend',
    'task_organize': 'Task Organize'
  }
  return labels[type] || (type ? type.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()) : 'UNKNOWN')
}

const getActionTypeClass = (type) => {
  const classes = {
    'propose_coa': 'badge-coa',
    'refine_coa': 'badge-coa',
    'decide_coa': 'badge-decision',
    'vote_coa': 'badge-decision',
    'score_coa': 'badge-decision',
    'wargame_move': 'badge-wargame',
    'wargame_counter': 'badge-wargame',
    'analyze_terrain': 'badge-intel',
    'assess_threat': 'badge-intel',
    'assess_logistics': 'badge-intel',
    'assess_comms': 'badge-intel',
    'request_intel': 'badge-intel',
    'provide_intel': 'badge-intel',
    'identify_gap': 'badge-intel',
    'evaluate_risk': 'badge-risk',
    'challenge_assumption': 'badge-risk',
    'concur': 'badge-consensus',
    'dissent': 'badge-dissent',
    'recommend': 'badge-consensus',
    'task_organize': 'badge-task'
  }
  return classes[type] || 'badge-default'
}

const getRoleClass = (role) => {
  const r = (role || '').toUpperCase()
  if (r === 'CDR' || r === 'CO') return 'role-cdr'
  if (r === 'S2' || r === 'INTEL') return 'role-s2'
  if (r === 'S3' || r === 'OPS') return 'role-s3'
  if (r === 'S4' || r === 'LOG') return 'role-s4'
  if (r === 'RED' || r === 'OPFOR') return 'role-red'
  if (r === 'FSO' || r === 'FIRES') return 'role-fso'
  return 'role-staff'
}

const getRoleAbbrev = (role) => {
  if (!role) return 'S'
  const r = role.toUpperCase()
  if (r.length <= 3) return r
  return r.substring(0, 3)
}

const truncateContent = (content, maxLength = 100) => {
  if (!content) return ''
  if (content.length > maxLength) return content.substring(0, maxLength) + '...'
  return content
}

const formatActionTime = (timestamp) => {
  if (!timestamp) return ''
  try {
    return new Date(timestamp).toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })
  } catch {
    return ''
  }
}

const handleNextStep = async () => {
  if (!props.simulationId) {
    addLog('Error: Missing simulationId')
    return
  }

  if (isGeneratingReport.value) {
    addLog('Report generation already in progress...')
    return
  }

  isGeneratingReport.value = true
  addLog('Starting report generation...')

  try {
    const res = await generateReport({
      simulation_id: props.simulationId,
      force_regenerate: true
    })

    if (res.success && res.data) {
      const reportId = res.data.report_id
      addLog(`Report generation started: ${reportId}`)

      router.push({ name: 'Report', params: { reportId } })
    } else {
      addLog(`Report generation failed: ${res.error || 'Unknown error'}`)
      isGeneratingReport.value = false
    }
  } catch (err) {
    addLog(`Report generation error: ${err.message}`)
    isGeneratingReport.value = false
  }
}

// Scroll log to bottom
const logContent = ref(null)
watch(() => props.systemLogs?.length, () => {
  nextTick(() => {
    if (logContent.value) {
      logContent.value.scrollTop = logContent.value.scrollHeight
    }
  })
})

onMounted(() => {
  addLog('Step3 Deliberation execution init')
  if (props.simulationId) {
    doStartSimulation()
  }
})

onUnmounted(() => {
  stopPolling()
})
</script>

<style scoped>
.simulation-panel {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #FFFFFF;
  font-family: 'Space Grotesk', system-ui, sans-serif;
  overflow: hidden;
}

/* --- Control Bar --- */
.control-bar {
  background: #FFF;
  padding: 12px 24px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid #EAEAEA;
  z-index: 10;
  height: 64px;
}

.status-group {
  display: flex;
  gap: 12px;
}

/* Deliberation Status Card */
.deliberation-status {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 6px 16px;
  border-radius: 4px;
  background: #FAFAFA;
  border: 1px solid #EAEAEA;
  opacity: 0.7;
  transition: all 0.3s;
  min-width: 320px;
}

.deliberation-status.active {
  opacity: 1;
  border-color: #333;
  background: #FFF;
}

.deliberation-status.completed {
  opacity: 1;
  border-color: #1A936F;
  background: #F2FAF6;
}

.deliberation-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 2px;
}

.platform-name {
  font-size: 11px;
  font-weight: 700;
  color: #000;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.platform-icon { color: #000; }

.platform-stats {
  display: flex;
  gap: 10px;
}

.stat {
  display: flex;
  align-items: baseline;
  gap: 3px;
}

.stat-label {
  font-size: 8px;
  color: #999;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.stat-value {
  font-size: 11px;
  font-weight: 600;
  color: #333;
}

.stat-total, .stat-unit {
  font-size: 9px;
  color: #999;
  font-weight: 400;
}

.status-badge {
  margin-left: auto;
  color: #1A936F;
  display: flex;
  align-items: center;
}

/* --- MDMP Phase Stepper --- */
.phase-stepper {
  display: flex;
  align-items: center;
  padding: 10px 24px;
  background: #FAFAFA;
  border-bottom: 1px solid #EAEAEA;
  gap: 4px;
  overflow-x: auto;
}

.phase-step {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border-radius: 3px;
  font-size: 11px;
  white-space: nowrap;
  transition: all 0.3s;
  border: 1px solid transparent;
}

.phase-step.pending {
  color: #BBB;
  background: transparent;
}

.phase-step.active {
  color: #000;
  background: #FFF;
  border-color: #333;
  font-weight: 600;
  box-shadow: 0 1px 4px rgba(0,0,0,0.08);
}

.phase-step.completed {
  color: #1A936F;
  background: #F2FAF6;
  border-color: #C8E6D8;
}

.phase-number {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  font-weight: 700;
  font-family: 'JetBrains Mono', monospace;
}

.phase-step.pending .phase-number {
  background: #F0F0F0;
  color: #BBB;
}

.phase-step.active .phase-number {
  background: #000;
  color: #FFF;
}

.phase-step.completed .phase-number {
  background: #1A936F;
  color: #FFF;
}

.phase-label {
  font-size: 10px;
  letter-spacing: 0.02em;
}

/* Action Button */
.action-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;
  font-size: 13px;
  font-weight: 600;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s ease;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.action-btn.primary {
  background: #000;
  color: #FFF;
}

.action-btn.primary:hover:not(:disabled) {
  background: #333;
}

.action-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

/* --- Main Content Area --- */
.main-content-area {
  flex: 1;
  overflow-y: auto;
  position: relative;
  background: #FFF;
}

/* Timeline Header */
.timeline-header {
  position: sticky;
  top: 0;
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(8px);
  padding: 12px 24px;
  border-bottom: 1px solid #EAEAEA;
  z-index: 5;
  display: flex;
  justify-content: center;
}

.timeline-stats {
  display: flex;
  align-items: center;
  gap: 16px;
  font-size: 11px;
  color: #666;
  background: #F5F5F5;
  padding: 4px 12px;
  border-radius: 20px;
}

.total-count {
  font-weight: 600;
  color: #333;
}

.stat-pill {
  display: flex;
  align-items: center;
  gap: 4px;
}

.stat-pill-label {
  font-size: 9px;
  color: #999;
  font-weight: 600;
  text-transform: uppercase;
}

/* --- Timeline Feed --- */
.timeline-feed {
  padding: 24px 0;
  position: relative;
  min-height: 100%;
  max-width: 700px;
  margin: 0 auto;
}

.timeline-axis {
  position: absolute;
  left: 28px;
  top: 0;
  bottom: 0;
  width: 1px;
  background: #EAEAEA;
}

.timeline-item {
  display: flex;
  margin-bottom: 20px;
  position: relative;
  width: 100%;
  padding-left: 56px;
  padding-right: 24px;
}

.timeline-marker {
  position: absolute;
  left: 22px;
  top: 24px;
  width: 12px;
  height: 12px;
  background: #FFF;
  border: 2px solid #CCC;
  border-radius: 50%;
  z-index: 2;
  display: flex;
  align-items: center;
  justify-content: center;
}

.marker-dot {
  width: 4px;
  height: 4px;
  background: #CCC;
  border-radius: 50%;
}

/* Role-based marker colors */
.timeline-item.role-cdr .timeline-marker { border-color: #D4A017; }
.timeline-item.role-cdr .marker-dot { background: #D4A017; }
.timeline-item.role-s2 .timeline-marker { border-color: #2563EB; }
.timeline-item.role-s2 .marker-dot { background: #2563EB; }
.timeline-item.role-s3 .timeline-marker { border-color: #16A34A; }
.timeline-item.role-s3 .marker-dot { background: #16A34A; }
.timeline-item.role-s4 .timeline-marker { border-color: #EA580C; }
.timeline-item.role-s4 .marker-dot { background: #EA580C; }
.timeline-item.role-red .timeline-marker { border-color: #DC2626; }
.timeline-item.role-red .marker-dot { background: #DC2626; }
.timeline-item.role-fso .timeline-marker { border-color: #9333EA; }
.timeline-item.role-fso .marker-dot { background: #9333EA; }
.timeline-item.role-staff .timeline-marker { border-color: #999; }
.timeline-item.role-staff .marker-dot { background: #999; }

/* Card Layout */
.timeline-card {
  width: 100%;
  background: #FFF;
  border-radius: 2px;
  padding: 16px 20px;
  border: 1px solid #EAEAEA;
  box-shadow: 0 2px 10px rgba(0,0,0,0.02);
  position: relative;
  transition: all 0.2s;
}

.timeline-card:hover {
  box-shadow: 0 4px 12px rgba(0,0,0,0.05);
  border-color: #DDD;
}

/* Card Content Styles */
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 12px;
  padding-bottom: 12px;
  border-bottom: 1px solid #F5F5F5;
}

.agent-info {
  display: flex;
  align-items: center;
  gap: 10px;
}

.agent-details {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.avatar-placeholder {
  width: 28px;
  height: 28px;
  background: #000;
  color: #FFF;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 9px;
  font-weight: 700;
  text-transform: uppercase;
  font-family: 'JetBrains Mono', monospace;
}

/* Role-based avatar colors */
.avatar-placeholder.role-cdr { background: #D4A017; }
.avatar-placeholder.role-s2 { background: #2563EB; }
.avatar-placeholder.role-s3 { background: #16A34A; }
.avatar-placeholder.role-s4 { background: #EA580C; }
.avatar-placeholder.role-red { background: #DC2626; }
.avatar-placeholder.role-fso { background: #9333EA; }
.avatar-placeholder.role-staff { background: #666; }

.agent-name {
  font-size: 13px;
  font-weight: 600;
  color: #000;
}

.agent-role-tag {
  font-size: 9px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: #666;
}

.agent-role-tag.role-cdr { color: #D4A017; }
.agent-role-tag.role-s2 { color: #2563EB; }
.agent-role-tag.role-s3 { color: #16A34A; }
.agent-role-tag.role-s4 { color: #EA580C; }
.agent-role-tag.role-red { color: #DC2626; }
.agent-role-tag.role-fso { color: #9333EA; }

.header-meta {
  display: flex;
  align-items: center;
  gap: 8px;
}

.phase-indicator {
  display: flex;
  align-items: center;
}

.phase-tag {
  font-size: 9px;
  font-weight: 600;
  color: #999;
  font-family: 'JetBrains Mono', monospace;
  background: #F5F5F5;
  padding: 1px 5px;
  border-radius: 2px;
}

.action-badge {
  font-size: 9px;
  padding: 2px 6px;
  border-radius: 2px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  border: 1px solid transparent;
}

/* Action type badges */
.badge-coa { background: #FEF3C7; color: #92400E; border-color: #FDE68A; }
.badge-decision { background: #DBEAFE; color: #1E40AF; border-color: #BFDBFE; }
.badge-wargame { background: #FEE2E2; color: #991B1B; border-color: #FECACA; }
.badge-intel { background: #E0E7FF; color: #3730A3; border-color: #C7D2FE; }
.badge-risk { background: #FFF7ED; color: #9A3412; border-color: #FED7AA; }
.badge-consensus { background: #D1FAE5; color: #065F46; border-color: #A7F3D0; }
.badge-dissent { background: #FCE7F3; color: #9D174D; border-color: #FBCFE8; }
.badge-task { background: #F0F0F0; color: #333; border-color: #E0E0E0; }
.badge-default { background: #F5F5F5; color: #666; border: 1px solid #E0E0E0; }

.content-text {
  font-size: 13px;
  line-height: 1.6;
  color: #333;
  margin-bottom: 10px;
}

.content-text.main-text {
  font-size: 14px;
  color: #000;
}

/* Confidence Bar */
.confidence-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 8px;
  margin-bottom: 6px;
}

.confidence-label {
  font-size: 9px;
  font-weight: 600;
  color: #999;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  min-width: 64px;
}

.confidence-track {
  flex: 1;
  height: 4px;
  background: #F0F0F0;
  border-radius: 2px;
  overflow: hidden;
  max-width: 120px;
}

.confidence-fill {
  height: 100%;
  background: #333;
  border-radius: 2px;
  transition: width 0.3s ease;
}

.confidence-value {
  font-size: 10px;
  color: #666;
  font-weight: 600;
}

/* Risk Assessment */
.risk-assessment {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  margin-top: 8px;
  padding: 8px 10px;
  background: #FFF7ED;
  border: 1px solid #FED7AA;
  border-radius: 2px;
  font-size: 11px;
  color: #9A3412;
  line-height: 1.5;
}

.risk-assessment .icon-small {
  color: #EA580C;
  flex-shrink: 0;
  margin-top: 1px;
}

/* References */
.references-block {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: 8px;
  font-size: 10px;
}

.ref-label {
  color: #999;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.03em;
}

.ref-tag {
  background: #F0F0F0;
  color: #666;
  padding: 1px 6px;
  border-radius: 2px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 9px;
}

.icon-small {
  color: #999;
}

.card-footer {
  margin-top: 12px;
  display: flex;
  justify-content: flex-end;
  font-size: 10px;
  color: #BBB;
  font-family: 'JetBrains Mono', monospace;
}

/* Waiting State */
.waiting-state {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  color: #CCC;
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.1em;
}

.pulse-ring {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  border: 1px solid #EAEAEA;
  animation: ripple 2s infinite;
}

@keyframes ripple {
  0% { transform: scale(0.8); opacity: 1; border-color: #CCC; }
  100% { transform: scale(2.5); opacity: 0; border-color: #EAEAEA; }
}

/* Animation */
.timeline-item-enter-active,
.timeline-item-leave-active {
  transition: all 0.4s cubic-bezier(0.165, 0.84, 0.44, 1);
}

.timeline-item-enter-from {
  opacity: 0;
  transform: translateY(20px);
}

.timeline-item-leave-to {
  opacity: 0;
}

/* Logs */
.system-logs {
  background: #000;
  color: #DDD;
  padding: 16px;
  font-family: 'JetBrains Mono', monospace;
  border-top: 1px solid #222;
  flex-shrink: 0;
}

.log-header {
  display: flex;
  justify-content: space-between;
  border-bottom: 1px solid #333;
  padding-bottom: 8px;
  margin-bottom: 8px;
  font-size: 10px;
  color: #666;
}

.log-content {
  display: flex;
  flex-direction: column;
  gap: 4px;
  height: 100px;
  overflow-y: auto;
  padding-right: 4px;
}

.log-content::-webkit-scrollbar { width: 4px; }
.log-content::-webkit-scrollbar-thumb { background: #333; border-radius: 2px; }

.log-line {
  font-size: 11px;
  display: flex;
  gap: 12px;
  line-height: 1.5;
}

.log-time { color: #555; min-width: 75px; }
.log-msg { color: #BBB; word-break: break-all; }
.mono { font-family: 'JetBrains Mono', monospace; }

/* Loading spinner for button */
.loading-spinner-small {
  display: inline-block;
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: #FFF;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin-right: 6px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
