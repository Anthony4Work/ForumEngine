<template>
  <div class="action-card" :class="roleClass">
    <div class="card-header">
      <div class="agent-info">
        <div class="avatar" :class="roleClass">{{ roleAbbrev }}</div>
        <div class="agent-details">
          <span class="agent-name">{{ action.agent_name || action.agent_id }}</span>
          <span class="role-tag" :class="roleClass">{{ action.agent_role || 'STAFF' }}</span>
        </div>
      </div>
      <div class="header-meta">
        <span class="phase-tag">P{{ action.phase || '?' }}</span>
        <span class="action-badge" :class="actionTypeClass">{{ actionTypeLabel }}</span>
      </div>
    </div>

    <div class="card-body">
      <div v-if="action.content" class="content-text" :class="{ truncated: !expanded && action.content.length > 400 }">
        {{ expanded ? action.content : truncate(action.content, 400) }}
        <button v-if="action.content.length > 400" class="expand-btn" @click="expanded = !expanded">
          {{ expanded ? 'Show less' : 'Show more' }}
        </button>
      </div>
      <div v-else-if="action.action_args?.content" class="content-text">
        {{ truncate(action.action_args.content, 400) }}
      </div>

      <div v-if="action.confidence != null" class="confidence-bar">
        <span class="confidence-label">Confidence</span>
        <div class="confidence-track">
          <div class="confidence-fill" :style="{ width: (action.confidence * 100) + '%' }"></div>
        </div>
        <span class="confidence-value mono">{{ Math.round(action.confidence * 100) }}%</span>
      </div>

      <div v-if="action.risk_assessment" class="risk-assessment">
        <svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path>
          <line x1="12" y1="9" x2="12" y2="13"></line>
          <line x1="12" y1="17" x2="12.01" y2="17"></line>
        </svg>
        <span>{{ truncate(action.risk_assessment, 200) }}</span>
      </div>

      <div v-if="action.references && action.references.length > 0" class="references-block">
        <span class="ref-label">References:</span>
        <span v-for="(ref, ri) in action.references" :key="ri" class="ref-tag">{{ ref }}</span>
      </div>
    </div>

    <div class="card-footer">
      <span class="time-tag">P{{ action.phase || '?' }} R{{ action.round_num || '?' }} &bull; {{ formatTime(action.timestamp) }}</span>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  action: { type: Object, required: true }
})

const expanded = ref(false)

const roleColors = {
  CDR: 'role-cdr', XO: 'role-xo', S2: 'role-s2', S3: 'role-s3',
  S4: 'role-s4', S6: 'role-s6', FSO: 'role-fso', RED: 'role-red',
  CIMIC: 'role-cimic', ENGR: 'role-engr'
}

const roleClass = computed(() => roleColors[props.action.agent_role] || 'role-default')

const roleAbbrev = computed(() => {
  const role = props.action.agent_role || ''
  return role.substring(0, 3).toUpperCase() || 'STF'
})

const actionTypes = {
  propose_coa: 'COA Proposal',
  assess_threat: 'Threat Assessment',
  wargame_move: 'Wargame Move',
  analyze: 'Analysis',
  recommend: 'Recommendation',
  decide: 'Decision',
  dissent: 'Dissent',
  support: 'Support',
  question: 'Question',
  intel_update: 'Intel Update',
  risk_assessment: 'Risk Assessment',
  terrain_analysis: 'Terrain Analysis',
  logistics_assessment: 'Logistics',
  comms_assessment: 'Comms',
  fire_support_plan: 'Fire Support',
  engineer_assessment: 'Engineer',
  cimic_assessment: 'CIMIC',
  mission_analysis: 'Mission Analysis',
  ipb_analysis: 'IPB Analysis',
  coa_comparison: 'COA Comparison',
  orders_production: 'Orders',
  consensus: 'Consensus',
  deliberate: 'Deliberation'
}

const actionTypeLabel = computed(() => actionTypes[props.action.action_type] || props.action.action_type || 'Action')
const actionTypeClass = computed(() => `action-${props.action.action_type || 'default'}`)

const truncate = (text, max) => {
  if (!text || text.length <= max) return text
  return text.slice(0, max) + '...'
}

const formatTime = (ts) => {
  if (!ts) return ''
  try {
    const d = new Date(ts)
    return d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
  } catch { return '' }
}
</script>

<style scoped>
.action-card {
  background: #1a1a1a;
  border: 1px solid #252525;
  border-radius: 6px;
  overflow: hidden;
  transition: border-color 0.2s;
}

.action-card:hover {
  border-color: #333;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid #222;
}

.agent-info {
  display: flex;
  align-items: center;
  gap: 10px;
}

.avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  font-weight: 700;
  color: #fff;
  background: #333;
}

.role-cdr .avatar, .avatar.role-cdr { background: #FF4500; }
.role-xo .avatar, .avatar.role-xo { background: #e08600; }
.role-s2 .avatar, .avatar.role-s2 { background: #2563eb; }
.role-s3 .avatar, .avatar.role-s3 { background: #16a34a; }
.role-s4 .avatar, .avatar.role-s4 { background: #7c3aed; }
.role-s6 .avatar, .avatar.role-s6 { background: #0891b2; }
.role-fso .avatar, .avatar.role-fso { background: #dc2626; }
.role-red .avatar, .avatar.role-red { background: #991b1b; }
.role-cimic .avatar, .avatar.role-cimic { background: #059669; }
.role-engr .avatar, .avatar.role-engr { background: #ca8a04; }

.agent-name {
  font-size: 13px;
  font-weight: 600;
  color: #e0e0e0;
}

.agent-details {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.role-tag {
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: #888;
}

.role-tag.role-cdr { color: #FF4500; }
.role-tag.role-xo { color: #e08600; }
.role-tag.role-s2 { color: #60a5fa; }
.role-tag.role-s3 { color: #4ade80; }
.role-tag.role-s4 { color: #a78bfa; }
.role-tag.role-s6 { color: #22d3ee; }
.role-tag.role-fso { color: #f87171; }
.role-tag.role-red { color: #fca5a5; }
.role-tag.role-cimic { color: #34d399; }
.role-tag.role-engr { color: #fbbf24; }

.header-meta {
  display: flex;
  align-items: center;
  gap: 8px;
}

.phase-tag {
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  color: #666;
  background: #222;
  padding: 2px 6px;
  border-radius: 3px;
}

.action-badge {
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.3px;
  color: #FF4500;
  background: rgba(255, 69, 0, 0.1);
  padding: 2px 8px;
  border-radius: 3px;
  border: 1px solid rgba(255, 69, 0, 0.2);
}

.card-body {
  padding: 12px 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.content-text {
  font-size: 13px;
  line-height: 1.6;
  color: #ccc;
  white-space: pre-wrap;
  word-break: break-word;
}

.expand-btn {
  background: none;
  border: none;
  color: #FF4500;
  font-size: 12px;
  cursor: pointer;
  padding: 0;
  margin-left: 4px;
  font-family: 'JetBrains Mono', monospace;
}

.confidence-bar {
  display: flex;
  align-items: center;
  gap: 8px;
}

.confidence-label {
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  text-transform: uppercase;
  color: #666;
  min-width: 80px;
}

.confidence-track {
  flex: 1;
  height: 4px;
  background: #222;
  border-radius: 2px;
  overflow: hidden;
}

.confidence-fill {
  height: 100%;
  background: #FF4500;
  border-radius: 2px;
  transition: width 0.3s;
}

.confidence-value {
  font-size: 11px;
  color: #999;
  min-width: 35px;
  text-align: right;
}

.mono {
  font-family: 'JetBrains Mono', monospace;
}

.risk-assessment {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  font-size: 12px;
  color: #e08600;
  background: rgba(224, 134, 0, 0.05);
  padding: 8px 10px;
  border-radius: 4px;
  border-left: 2px solid #e08600;
}

.risk-assessment svg {
  flex-shrink: 0;
  margin-top: 1px;
}

.references-block {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
}

.ref-label {
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  text-transform: uppercase;
  color: #666;
}

.ref-tag {
  font-size: 11px;
  color: #60a5fa;
  background: rgba(96, 165, 250, 0.1);
  padding: 2px 6px;
  border-radius: 3px;
}

.card-footer {
  padding: 8px 16px;
  border-top: 1px solid #1f1f1f;
}

.time-tag {
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  color: #555;
}
</style>
