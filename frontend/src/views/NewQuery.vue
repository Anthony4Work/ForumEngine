<template>
  <div class="query-container">
    <!-- Navigation Bar -->
    <nav class="navbar">
      <div class="nav-brand" @click="$router.push('/')">
        <img src="/indramind.svg" alt="IndraMind" class="nav-logo" />
        FORUMENGINE
      </div>
      <div class="nav-links">
        <span class="nav-link" @click="$router.push('/library')">Library</span>
      </div>
    </nav>

    <div class="main-content">
      <!-- Loading -->
      <div v-if="loading" class="loading-state">
        <div class="loading-spinner"></div>
        <span>Loading graph details...</span>
      </div>

      <!-- Error -->
      <div v-else-if="error" class="error-state">
        <p>{{ error }}</p>
        <button class="action-btn" @click="$router.push('/library')">Back to Library</button>
      </div>

      <template v-else-if="graphData">
        <!-- Graph Info Header -->
        <div class="graph-header">
          <div class="tag-row">
            <span class="orange-tag">New Deliberation</span>
            <span class="version-text">/ {{ graphData.graph_id.substring(0, 16) }}</span>
          </div>
          <h1 class="page-title">{{ graphData.name }}</h1>
          <p class="page-desc">{{ graphData.description }}</p>

          <!-- Graph Stats -->
          <div class="graph-stats">
            <div class="stat-box">
              <span class="stat-value">{{ graphData.node_count }}</span>
              <span class="stat-label">Nodes</span>
            </div>
            <div class="stat-box">
              <span class="stat-value">{{ graphData.edge_count }}</span>
              <span class="stat-label">Edges</span>
            </div>
            <div class="stat-box">
              <span class="stat-value">{{ (graphData.documents || []).length }}</span>
              <span class="stat-label">Documents</span>
            </div>
            <div class="stat-box">
              <span class="stat-value">{{ (graphData.deliberations || []).length }}</span>
              <span class="stat-label">Deliberations</span>
            </div>
          </div>

          <!-- Entity Types -->
          <div class="entity-row" v-if="graphData.entity_types && graphData.entity_types.length">
            <span class="entity-label">Entity types:</span>
            <span v-for="et in graphData.entity_types" :key="et" class="entity-chip">{{ et }}</span>
          </div>
        </div>

        <!-- Separator -->
        <div class="section-sep">
          <span>Mission Objective</span>
        </div>

        <!-- Query Input -->
        <div class="query-box">
          <div class="query-header">
            <span class="query-label">>_ Define your mission objective</span>
          </div>
          <div class="input-wrapper">
            <textarea
              v-model="missionObjective"
              class="code-input"
              placeholder="// What do you want to analyze? (e.g. What is the best route of advance for the mechanized battalion? What are the logistics options for 72h operations?)"
              rows="8"
              :disabled="submitting"
            ></textarea>
          </div>

          <!-- Previous Deliberations -->
          <div class="prev-queries" v-if="graphData.deliberations && graphData.deliberations.length">
            <span class="prev-label">Previous queries on this graph:</span>
            <div
              v-for="d in graphData.deliberations.slice(0, 5)"
              :key="d.simulation_id"
              class="prev-item"
              @click="missionObjective = d.mission_objective"
            >
              <span class="prev-status" :class="d.status">{{ d.status }}</span>
              <span class="prev-text">{{ truncate(d.mission_objective, 80) }}</span>
            </div>
          </div>

          <!-- Submit -->
          <button
            class="launch-btn"
            :disabled="!missionObjective.trim() || submitting"
            @click="submitQuery"
          >
            <span v-if="!submitting">Launch Deliberation</span>
            <span v-else>Creating simulation...</span>
            <span class="btn-arrow">-></span>
          </button>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { getGraphDetail, startDeliberation } from '../api/graph.js'

const router = useRouter()
const route = useRoute()

const graphData = ref(null)
const loading = ref(true)
const error = ref('')
const missionObjective = ref('')
const submitting = ref(false)

onMounted(async () => {
  const graphId = route.params.graphId
  if (!graphId) {
    error.value = 'No graph ID provided'
    loading.value = false
    return
  }

  try {
    const res = await getGraphDetail(graphId)
    if (res.data?.success) {
      graphData.value = res.data.data
    } else {
      error.value = res.data?.error || 'Failed to load graph'
    }
  } catch (e) {
    error.value = 'Failed to load graph details'
    console.error(e)
  } finally {
    loading.value = false
  }
})

async function submitQuery() {
  if (!missionObjective.value.trim() || submitting.value) return
  submitting.value = true

  try {
    const graphId = route.params.graphId
    const res = await startDeliberation(graphId, {
      mission_objective: missionObjective.value.trim()
    })

    if (res.data?.success) {
      const simId = res.data.data.simulation_id
      router.push({ name: 'Simulation', params: { simulationId: simId } })
    } else {
      error.value = res.data?.error || 'Failed to create deliberation'
    }
  } catch (e) {
    error.value = 'Failed to create deliberation'
    console.error(e)
  } finally {
    submitting.value = false
  }
}

function truncate(text, max) {
  if (!text) return ''
  return text.length > max ? text.substring(0, max) + '...' : text
}
</script>

<style scoped>
:root {
  --black: #000000;
  --white: #FFFFFF;
  --orange: #FF4500;
  --gray-text: #666666;
  --border: #E5E5E5;
  --font-mono: 'JetBrains Mono', monospace;
  --font-sans: 'Space Grotesk', system-ui, sans-serif;
}

.query-container {
  min-height: 100vh;
  background: var(--white);
  font-family: var(--font-sans);
  color: var(--black);
}

/* Navbar */
.navbar {
  height: 60px;
  background: var(--black);
  color: var(--white);
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 40px;
}

.nav-brand {
  display: flex;
  align-items: center;
  gap: 24px;
  font-family: var(--font-mono);
  font-weight: 800;
  letter-spacing: 1px;
  font-size: 1.2rem;
  cursor: pointer;
}

.nav-logo { height: 28px; width: auto; }

.nav-link {
  font-family: var(--font-mono);
  font-size: 0.8rem;
  color: #999;
  cursor: pointer;
  transition: color 0.15s;
  letter-spacing: 0.5px;
}

.nav-link:hover { color: var(--white); }

/* Main Content */
.main-content {
  max-width: 800px;
  margin: 0 auto;
  padding: 60px 40px;
}

/* Loading / Error */
.loading-state, .error-state {
  text-align: center;
  padding: 80px 0;
  color: var(--gray-text);
  font-family: var(--font-mono);
  font-size: 0.9rem;
}

.loading-spinner {
  width: 30px;
  height: 30px;
  border: 2px solid var(--border);
  border-top-color: var(--orange);
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 15px;
}

@keyframes spin { to { transform: rotate(360deg); } }

.action-btn {
  font-family: var(--font-mono);
  font-weight: 600;
  font-size: 0.85rem;
  padding: 10px 24px;
  background: var(--black);
  color: var(--white);
  border: none;
  cursor: pointer;
  margin-top: 15px;
}

/* Graph Header */
.graph-header {
  margin-bottom: 40px;
}

.tag-row {
  display: flex;
  align-items: center;
  gap: 15px;
  margin-bottom: 15px;
  font-family: var(--font-mono);
  font-size: 0.8rem;
}

.orange-tag {
  background: var(--orange);
  color: var(--white);
  padding: 4px 10px;
  font-weight: 700;
  letter-spacing: 1px;
  font-size: 0.75rem;
}

.version-text { color: #999; }

.page-title {
  font-size: 2rem;
  font-weight: 500;
  margin: 0 0 8px 0;
  letter-spacing: -0.5px;
}

.page-desc {
  color: var(--gray-text);
  line-height: 1.6;
  margin-bottom: 25px;
}

/* Stats */
.graph-stats {
  display: flex;
  gap: 20px;
  margin-bottom: 20px;
}

.stat-box {
  border: 1px solid var(--border);
  padding: 14px 20px;
  text-align: center;
  flex: 1;
}

.stat-value {
  display: block;
  font-family: var(--font-mono);
  font-weight: 700;
  font-size: 1.4rem;
}

.stat-label {
  display: block;
  font-family: var(--font-mono);
  font-size: 0.7rem;
  color: #AAA;
  margin-top: 4px;
  letter-spacing: 0.5px;
}

/* Entity types */
.entity-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
}

.entity-label {
  font-family: var(--font-mono);
  font-size: 0.72rem;
  color: #AAA;
  margin-right: 4px;
}

.entity-chip {
  font-family: var(--font-mono);
  font-size: 0.68rem;
  background: #FFF5F0;
  border: 1px solid #FFE0D0;
  padding: 2px 7px;
  color: var(--orange);
}

/* Separator */
.section-sep {
  display: flex;
  align-items: center;
  margin: 40px 0 30px;
}

.section-sep::before,
.section-sep::after {
  content: '';
  flex: 1;
  height: 1px;
  background: var(--border);
}

.section-sep span {
  padding: 0 20px;
  font-family: var(--font-mono);
  font-size: 0.75rem;
  color: #AAA;
  letter-spacing: 1px;
}

/* Query Box */
.query-box {
  border: 1px solid #CCC;
  padding: 8px;
}

.query-header {
  padding: 15px 20px 10px;
  font-family: var(--font-mono);
  font-size: 0.75rem;
  color: #666;
}

.input-wrapper {
  border: 1px solid #DDD;
  background: #FAFAFA;
  margin: 0 12px;
}

.code-input {
  width: 100%;
  border: none;
  background: transparent;
  padding: 20px;
  font-family: var(--font-mono);
  font-size: 0.9rem;
  line-height: 1.6;
  resize: vertical;
  outline: none;
  min-height: 150px;
}

/* Previous queries */
.prev-queries {
  padding: 15px 20px;
}

.prev-label {
  font-family: var(--font-mono);
  font-size: 0.72rem;
  color: #AAA;
  display: block;
  margin-bottom: 10px;
}

.prev-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 0;
  border-bottom: 1px solid #F0F0F0;
  cursor: pointer;
  transition: background 0.1s;
}

.prev-item:hover {
  background: #FAFAFA;
}

.prev-status {
  font-family: var(--font-mono);
  font-size: 0.65rem;
  padding: 2px 6px;
  border: 1px solid var(--border);
  white-space: nowrap;
}

.prev-status.completed { color: #090; border-color: #090; }
.prev-status.running { color: var(--orange); border-color: var(--orange); }
.prev-status.ready { color: #06A; border-color: #06A; }
.prev-status.failed { color: #C00; border-color: #C00; }

.prev-text {
  font-size: 0.85rem;
  color: var(--gray-text);
}

/* Launch button */
.launch-btn {
  width: calc(100% - 24px);
  margin: 12px;
  background: var(--black);
  color: var(--white);
  border: none;
  padding: 20px;
  font-family: var(--font-mono);
  font-weight: 700;
  font-size: 1.05rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: pointer;
  transition: all 0.3s ease;
  letter-spacing: 1px;
}

.launch-btn:not(:disabled):hover {
  background: var(--orange);
}

.launch-btn:disabled {
  background: #E5E5E5;
  color: #999;
  cursor: not-allowed;
}

.btn-arrow {
  font-weight: 400;
}
</style>
