<template>
  <div class="dossier-agents-step">
    <div class="agents-header">
      <h4 class="section-label">Tactical Staff Officers</h4>
      <span class="agent-count mono">{{ agents.length }} agents</span>
    </div>

    <div class="agents-grid" v-if="agents.length > 0">
      <div
        v-for="(agent, idx) in agents"
        :key="idx"
        class="agent-card"
        :class="{ expanded: expandedAgent === idx }"
        @click="expandedAgent = expandedAgent === idx ? null : idx"
      >
        <div class="agent-card-header">
          <div class="agent-avatar" :class="getRoleClass(agent)">
            {{ getRoleAbbrev(agent) }}
          </div>
          <div class="agent-identity">
            <span class="agent-name">{{ agent.username || agent.name || `Agent ${idx + 1}` }}</span>
            <span class="agent-role mono">{{ agent.role_name || agent.profession || 'Staff Officer' }}</span>
          </div>
          <div class="agent-stat-pill" v-if="getAgentStat(agent)">
            <span class="pill-value mono">{{ getAgentStat(agent).total_actions || 0 }}</span>
            <span class="pill-label">acts</span>
          </div>
        </div>

        <div class="agent-card-body" v-if="expandedAgent === idx">
          <div v-if="agent.bio" class="agent-field">
            <span class="field-label">Profile</span>
            <p class="field-content">{{ agent.bio }}</p>
          </div>
          <div v-if="agent.personality" class="agent-field">
            <span class="field-label">Personality</span>
            <p class="field-content">{{ agent.personality }}</p>
          </div>
          <div v-if="agent.perspective" class="agent-field">
            <span class="field-label">Perspective</span>
            <p class="field-content">{{ agent.perspective }}</p>
          </div>
          <div v-if="agent.special_knowledge" class="agent-field">
            <span class="field-label">Special Knowledge</span>
            <p class="field-content">{{ agent.special_knowledge }}</p>
          </div>

          <!-- Agent Stats from agent-stats API -->
          <div v-if="getAgentStat(agent)" class="agent-stats-bar">
            <div class="mini-stat">
              <span class="mini-label">Actions</span>
              <span class="mini-value mono">{{ getAgentStat(agent).total_actions || 0 }}</span>
            </div>
            <div class="mini-stat">
              <span class="mini-label">Phases</span>
              <span class="mini-value mono">{{ getAgentStat(agent).phases_active || 0 }}</span>
            </div>
            <div class="mini-stat" v-if="getAgentStat(agent).avg_confidence != null">
              <span class="mini-label">Avg Conf</span>
              <span class="mini-value mono">{{ Math.round(getAgentStat(agent).avg_confidence * 100) }}%</span>
            </div>
          </div>
        </div>

        <div class="expand-hint">
          <svg :class="{ rotated: expandedAgent === idx }" viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="6 9 12 15 18 9"></polyline>
          </svg>
        </div>
      </div>
    </div>

    <div v-else class="empty-state">
      <span class="empty-icon">◈</span>
      <span>No agent profiles available</span>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const props = defineProps({
  agents: { type: Array, default: () => [] },
  agentStats: { type: Array, default: () => [] }
})

const expandedAgent = ref(null)

const getRoleClass = (agent) => {
  const role = (agent.role_name || agent.profession || '').toUpperCase()
  const map = { CDR: 'role-cdr', XO: 'role-xo', 'S-2': 'role-s2', S2: 'role-s2', 'S-3': 'role-s3', S3: 'role-s3', 'S-4': 'role-s4', S4: 'role-s4', 'S-6': 'role-s6', S6: 'role-s6', FSO: 'role-fso', RED: 'role-red', CIMIC: 'role-cimic', ENGR: 'role-engr' }
  for (const [key, cls] of Object.entries(map)) {
    if (role.includes(key)) return cls
  }
  return 'role-default'
}

const getRoleAbbrev = (agent) => {
  const role = agent.role_name || agent.profession || ''
  const abbrevMap = { Commander: 'CDR', 'Executive Officer': 'XO', Intelligence: 'S2', Operations: 'S3', Logistics: 'S4', Signal: 'S6', 'Fire Support': 'FSO', 'Red Team': 'RED', 'Civil-Military': 'CIM', Engineer: 'ENG' }
  for (const [key, abbr] of Object.entries(abbrevMap)) {
    if (role.includes(key)) return abbr
  }
  return role.substring(0, 3).toUpperCase() || 'AGT'
}

const getAgentStat = (agent) => {
  if (!props.agentStats?.length) return null
  const name = agent.username || agent.name
  return props.agentStats.find(s => s.agent_name === name || s.agent_id === name) || null
}
</script>

<style scoped>
.dossier-agents-step {
  padding: 24px;
  overflow-y: auto;
  height: 100%;
}

.agents-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.section-label {
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 1px;
  color: #666;
  margin: 0;
}

.agent-count {
  font-size: 12px;
  color: #555;
}

.agents-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
  gap: 12px;
}

.agent-card {
  background: #1a1a1a;
  border: 1px solid #252525;
  border-radius: 8px;
  overflow: hidden;
  cursor: pointer;
  transition: border-color 0.2s;
  position: relative;
}

.agent-card:hover {
  border-color: #333;
}

.agent-card.expanded {
  border-color: #FF4500;
}

.agent-card-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px;
}

.agent-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  font-weight: 700;
  color: #fff;
  background: #333;
  flex-shrink: 0;
}

.role-cdr .agent-avatar, .agent-avatar.role-cdr { background: #FF4500; }
.role-xo .agent-avatar, .agent-avatar.role-xo { background: #e08600; }
.role-s2 .agent-avatar, .agent-avatar.role-s2 { background: #2563eb; }
.role-s3 .agent-avatar, .agent-avatar.role-s3 { background: #16a34a; }
.role-s4 .agent-avatar, .agent-avatar.role-s4 { background: #7c3aed; }
.role-s6 .agent-avatar, .agent-avatar.role-s6 { background: #0891b2; }
.role-fso .agent-avatar, .agent-avatar.role-fso { background: #dc2626; }
.role-red .agent-avatar, .agent-avatar.role-red { background: #991b1b; }
.role-cimic .agent-avatar, .agent-avatar.role-cimic { background: #059669; }
.role-engr .agent-avatar, .agent-avatar.role-engr { background: #ca8a04; }

.agent-identity {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.agent-name {
  font-size: 14px;
  font-weight: 600;
  color: #e0e0e0;
}

.agent-role {
  font-size: 11px;
  color: #888;
  text-transform: uppercase;
  letter-spacing: 0.3px;
}

.agent-stat-pill {
  display: flex;
  align-items: center;
  gap: 4px;
  background: #222;
  padding: 4px 10px;
  border-radius: 12px;
}

.pill-value {
  font-size: 14px;
  font-weight: 700;
  color: #FF4500;
}

.pill-label {
  font-family: 'JetBrains Mono', monospace;
  font-size: 9px;
  text-transform: uppercase;
  color: #666;
}

.agent-card-body {
  padding: 0 16px 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.agent-field {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.field-label {
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: #666;
}

.field-content {
  font-size: 13px;
  line-height: 1.6;
  color: #bbb;
  margin: 0;
}

.agent-stats-bar {
  display: flex;
  gap: 16px;
  padding-top: 10px;
  border-top: 1px solid #222;
}

.mini-stat {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.mini-label {
  font-family: 'JetBrains Mono', monospace;
  font-size: 9px;
  text-transform: uppercase;
  color: #555;
}

.mini-value {
  font-size: 14px;
  font-weight: 600;
  color: #ccc;
}

.expand-hint {
  position: absolute;
  top: 18px;
  right: 14px;
  color: #444;
  transition: color 0.2s;
}

.agent-card:hover .expand-hint { color: #666; }

.expand-hint svg {
  transition: transform 0.2s;
}

.expand-hint svg.rotated {
  transform: rotate(180deg);
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
