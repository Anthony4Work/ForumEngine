<template>
  <div class="home-container">
    <!-- Top Navigation Bar -->
    <nav class="navbar">
      <div class="nav-brand">
        <img src="/indramind.svg" alt="IndraMind" class="nav-logo" />
        FORUMENGINE
      </div>
      <div class="nav-links">
        <span class="nav-link-item" @click="$router.push('/library')">Library</span>
        <span class="nav-status-text">v0.1</span>
      </div>
    </nav>

    <div class="main-content">
      <!-- Section 1: Dashboard Top — Two Columns -->
      <section class="dashboard-top">
        <!-- Left: New Mission Panel -->
        <div class="panel-create">
          <div class="panel-title-row">
            <span class="status-dot">■</span>
            <span class="panel-title">New Mission</span>
          </div>

          <!-- 01 / Mission Briefing -->
          <div class="create-section">
            <div class="section-header">
              <span class="section-label">01 / Mission Briefing</span>
              <span class="section-meta">PDF, MD, TXT</span>
            </div>

            <div
              class="upload-zone"
              :class="{ 'drag-over': isDragOver, 'has-files': files.length > 0 }"
              @dragover.prevent="handleDragOver"
              @dragleave.prevent="handleDragLeave"
              @drop.prevent="handleDrop"
              @click="triggerFileInput"
            >
              <input
                ref="fileInput"
                type="file"
                multiple
                accept=".pdf,.md,.txt"
                @change="handleFileSelect"
                style="display: none"
                :disabled="loading"
              />

              <div v-if="files.length === 0" class="upload-placeholder">
                <div class="upload-icon">↑</div>
                <div class="upload-title">Drag & drop files here</div>
                <div class="upload-hint">or click to browse</div>
              </div>

              <div v-else class="file-list">
                <div v-for="(file, index) in files" :key="index" class="file-item">
                  <span class="file-icon">📄</span>
                  <span class="file-name">{{ file.name }}</span>
                  <button @click.stop="removeFile(index)" class="remove-btn">×</button>
                </div>
              </div>
            </div>
          </div>

          <!-- Divider -->
          <div class="create-divider"><span>Parameters</span></div>

          <!-- 02 / Mission Objective -->
          <div class="create-section">
            <div class="section-header">
              <span class="section-label">>_ 02 / Mission Objective <span class="optional-tag">(optional)</span></span>
            </div>
            <div class="field-wrapper">
              <textarea
                v-model="formData.simulationRequirement"
                class="code-input"
                placeholder="// Optional: Describe the mission objective now, or leave empty to build a reusable knowledge graph and query it later from the Library."
                rows="4"
                :disabled="loading"
              ></textarea>
            </div>
          </div>

          <!-- 03 / Domain Hints -->
          <div class="create-section">
            <div class="section-header">
              <span class="section-label">>_ 03 / Domain Hints <span class="optional-tag">(optional)</span></span>
            </div>
            <input
              v-model="formData.domainHints"
              class="domain-input"
              placeholder="e.g. military logistics, terrain analysis, force disposition..."
              :disabled="loading"
            />
          </div>

          <!-- Launch Button -->
          <button
            class="launch-btn"
            @click="startSimulation"
            :disabled="!canSubmit || loading"
          >
            <span v-if="!loading">Launch Engine</span>
            <span v-else>Initializing...</span>
            <span class="btn-arrow">→</span>
          </button>
        </div>

        <!-- Right: Graph Library Panel -->
        <div class="panel-library">
          <div class="panel-title-row">
            <div class="library-title-left">
              <span class="diamond-icon">◈</span>
              <span class="panel-title">Knowledge Graphs</span>
              <span class="lib-count" v-if="libraryGraphs.length">{{ libraryGraphs.length }}</span>
            </div>
            <button class="view-all-btn" @click="$router.push('/library')">All →</button>
          </div>

          <!-- Library Cards (scrollable) -->
          <div class="library-scroll" v-if="libraryGraphs.length > 0">
            <div
              v-for="(graph, i) in libraryGraphs"
              :key="graph.graph_id"
              class="lib-card"
              :style="{ animationDelay: (i * 0.05) + 's' }"
              @click="$router.push(`/library/${graph.graph_id}/query`)"
            >
              <div class="lib-card-top">
                <span class="lib-card-name">{{ graph.name }}</span>
                <span class="lib-card-stats">{{ graph.node_count }}n / {{ graph.edge_count }}e</span>
              </div>
              <div class="lib-card-desc">{{ truncateText(graph.description, 90) }}</div>
              <div class="lib-card-meta">
                <span>{{ graph.documents.length }} docs</span>
                <span>·</span>
                <span>{{ graph.deliberation_count }} queries</span>
                <span v-if="graph.entity_types_list && graph.entity_types_list.length" class="lib-card-types">
                  · {{ graph.entity_types_list.slice(0, 3).join(', ') }}
                </span>
              </div>
            </div>
          </div>

          <!-- Empty State -->
          <div class="library-empty" v-else>
            <span class="empty-diamond">◇</span>
            <p class="empty-title">No graphs yet</p>
            <p class="empty-hint">Upload documents on the left to create your first knowledge graph.</p>
          </div>
        </div>
      </section>

      <!-- Section 2: Tagline Bar -->
      <div class="tagline-bar">
        <span class="tagline-text">Run the scenario before it runs you<span class="blinking-cursor">_</span></span>
      </div>

      <!-- Section 3: Explanation -->
      <section class="explain-section">
        <div class="explain-left">
          <div class="tag-row">
            <span class="orange-tag">Mission Simulation Platform</span>
          </div>
          <h2 class="explain-title">
            Define the Mission.<br>
            Simulate Every Outcome.
          </h2>
          <p class="explain-desc">
            Feed any briefing document into <span class="highlight-bold">ForumEngine</span> and it will automatically spin up a multi-agent simulation environment. Explore how <span class="highlight-orange">stakeholders react</span>, identify emerging patterns, and stress-test decisions before committing to them in the real world.
          </p>
        </div>

        <div class="explain-right">
          <div class="workflow-header">
            <span class="diamond-icon">◇</span> Mission Workflow
          </div>
          <div class="workflow-list">
            <div class="workflow-item" v-for="step in workflowSteps" :key="step.num">
              <span class="step-num">{{ step.num }}</span>
              <div class="step-info">
                <div class="step-title">{{ step.title }}</div>
                <div class="step-desc">{{ step.desc }}</div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- Section 4: History Database -->
      <HistoryDatabase />

      <!-- Section 5: Footer -->
      <footer class="powered-footer">
        <img src="/indramind.svg" alt="IndraMind" class="footer-logo" />
        <span>Powered by IndraMind</span>
      </footer>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import HistoryDatabase from '../components/HistoryDatabase.vue'
import { getGraphLibrary } from '../api/graph.js'

const router = useRouter()

// Form data
const formData = ref({
  simulationRequirement: '',
  domainHints: ''
})

// File list
const files = ref([])

// Graph Library
const libraryGraphs = ref([])

// State
const loading = ref(false)
const isDragOver = ref(false)

// File input ref
const fileInput = ref(null)

// Workflow steps data
const workflowSteps = [
  { num: '01', title: 'Graph Building', desc: 'Extract entities, relationships and context from source documents into a knowledge graph' },
  { num: '02', title: 'Environment Setup', desc: 'Generate agent profiles, assign roles and inject simulation parameters' },
  { num: '03', title: 'Run Simulation', desc: 'Execute multi-agent deliberation across parallel channels with dynamic memory' },
  { num: '04', title: 'Report Generation', desc: 'ReportAgent analyzes simulation outcomes using graph-powered tools' },
  { num: '05', title: 'Deep Interaction', desc: 'Debrief any agent or query the ReportAgent for targeted analysis' }
]

// Load library graphs on mount
onMounted(async () => {
  try {
    const res = await getGraphLibrary(10)
    if (res.data?.success) {
      libraryGraphs.value = res.data.data || []
    }
  } catch (e) {
    // Silent fail — library preview is optional
  }
})

// Computed: can submit (files required)
const canSubmit = computed(() => files.value.length > 0)

// Truncate text helper
const truncateText = (text, max) => {
  if (!text) return ''
  return text.length > max ? text.substring(0, max) + '...' : text
}

// File handling
const triggerFileInput = () => {
  if (!loading.value) fileInput.value?.click()
}

const handleFileSelect = (event) => {
  addFiles(Array.from(event.target.files))
}

const handleDragOver = () => {
  if (!loading.value) isDragOver.value = true
}

const handleDragLeave = () => {
  isDragOver.value = false
}

const handleDrop = (e) => {
  isDragOver.value = false
  if (loading.value) return
  addFiles(Array.from(e.dataTransfer.files))
}

const addFiles = (newFiles) => {
  const validFiles = newFiles.filter(file => {
    const ext = file.name.split('.').pop().toLowerCase()
    return ['pdf', 'md', 'txt'].includes(ext)
  })
  files.value.push(...validFiles)
}

const removeFile = (index) => {
  files.value.splice(index, 1)
}

// Start simulation
const startSimulation = () => {
  if (!canSubmit.value || loading.value) return

  import('../store/pendingUpload.js').then(({ setPendingUpload }) => {
    setPendingUpload(
      files.value,
      formData.value.simulationRequirement,
      formData.value.domainHints
    )
    router.push({ name: 'Process', params: { projectId: 'new' } })
  })
}
</script>

<style scoped>
:root {
  --black: #000000;
  --white: #FFFFFF;
  --orange: #FF4500;
  --gray-light: #F5F5F5;
  --gray-text: #666666;
  --border: #E5E5E5;
  --font-mono: 'JetBrains Mono', monospace;
  --font-sans: 'Space Grotesk', system-ui, sans-serif;
}

.home-container {
  min-height: 100vh;
  background: var(--white);
  font-family: var(--font-sans);
  color: var(--black);
}

/* ─── Navbar ─── */
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
}

.nav-logo { height: 28px; width: auto; }

.nav-links {
  display: flex;
  align-items: center;
}

.nav-link-item {
  font-family: var(--font-mono);
  font-size: 0.8rem;
  color: #999;
  cursor: pointer;
  transition: color 0.15s;
  letter-spacing: 0.5px;
  margin-right: 24px;
}

.nav-link-item:hover { color: var(--white); }

.nav-status-text {
  font-family: var(--font-mono);
  font-size: 0.75rem;
  color: #666;
  letter-spacing: 1px;
}

/* ─── Main Content ─── */
.main-content {
  max-width: 1400px;
  margin: 0 auto;
  padding: 40px 40px 0;
}

/* ─── Section 1: Dashboard Top ─── */
.dashboard-top {
  display: flex;
  gap: 40px;
  align-items: stretch;
}

.panel-create {
  flex: 5;
  border: 1px solid var(--border);
  padding: 28px;
  display: flex;
  flex-direction: column;
}

.panel-library {
  flex: 7;
  border: 1px solid var(--border);
  padding: 28px;
  display: flex;
  flex-direction: column;
}

.panel-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
  font-family: var(--font-mono);
  font-size: 0.85rem;
}

.library-title-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.panel-title { font-weight: 700; letter-spacing: 0.5px; }

.status-dot {
  color: var(--orange);
  font-size: 0.85rem;
  margin-right: 10px;
}

.diamond-icon { font-size: 1.1rem; line-height: 1; }

.lib-count {
  background: #F0F0F0;
  padding: 2px 8px;
  font-size: 0.7rem;
  color: var(--gray-text);
}

.view-all-btn {
  font-family: var(--font-mono);
  font-size: 0.72rem;
  font-weight: 600;
  background: transparent;
  border: 1px solid var(--border);
  padding: 5px 14px;
  cursor: pointer;
  color: var(--gray-text);
  transition: all 0.15s;
  letter-spacing: 0.3px;
}

.view-all-btn:hover {
  border-color: var(--black);
  color: var(--black);
}

/* ─── Create Panel Sections ─── */
.create-section { margin-bottom: 16px; }

.section-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 10px;
  font-family: var(--font-mono);
  font-size: 0.72rem;
  color: #666;
}

.section-label { letter-spacing: 0.3px; }

.section-meta { color: #AAA; }

.optional-tag {
  color: #AAA;
  font-weight: 400;
  font-size: 0.62rem;
}

/* Upload Zone */
.upload-zone {
  border: 1px dashed #CCC;
  min-height: 140px;
  overflow-y: auto;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.3s;
  background: #FAFAFA;
}

.upload-zone.has-files { align-items: flex-start; }
.upload-zone:hover { background: #F0F0F0; border-color: #999; }
.upload-zone.drag-over { border-color: var(--orange); background: #FFF8F5; }

.upload-placeholder { text-align: center; }

.upload-icon {
  width: 36px;
  height: 36px;
  border: 1px solid #DDD;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 12px;
  color: #999;
  font-size: 1rem;
}

.upload-title { font-weight: 500; font-size: 0.85rem; margin-bottom: 4px; }

.upload-hint {
  font-family: var(--font-mono);
  font-size: 0.72rem;
  color: #999;
}

.file-list {
  width: 100%;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.file-item {
  display: flex;
  align-items: center;
  background: var(--white);
  padding: 7px 10px;
  border: 1px solid #EEE;
  font-family: var(--font-mono);
  font-size: 0.8rem;
}

.file-name { flex: 1; margin: 0 8px; }

.remove-btn {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 1.1rem;
  color: #999;
}

.remove-btn:hover { color: var(--orange); }

/* Create Divider */
.create-divider {
  display: flex;
  align-items: center;
  margin: 12px 0;
}

.create-divider::before,
.create-divider::after {
  content: '';
  flex: 1;
  height: 1px;
  background: #EEE;
}

.create-divider span {
  padding: 0 14px;
  font-family: var(--font-mono);
  font-size: 0.68rem;
  color: #BBB;
  letter-spacing: 1px;
}

/* Field Wrapper */
.field-wrapper {
  border: 1px solid #DDD;
  background: #FAFAFA;
}

.code-input {
  width: 100%;
  border: none;
  background: transparent;
  padding: 14px 16px;
  font-family: var(--font-mono);
  font-size: 0.82rem;
  line-height: 1.6;
  resize: vertical;
  outline: none;
  min-height: 80px;
}

/* Domain Hints Input */
.domain-input {
  width: 100%;
  border: 1px solid #DDD;
  background: #FAFAFA;
  padding: 12px 16px;
  font-family: var(--font-mono);
  font-size: 0.82rem;
  outline: none;
  transition: border-color 0.15s;
}

.domain-input:focus { border-color: var(--orange); }

/* Launch Button */
.launch-btn {
  width: 100%;
  margin-top: auto;
  padding-top: 16px;
  background: var(--black);
  color: var(--white);
  border: none;
  padding: 18px 20px;
  font-family: var(--font-mono);
  font-weight: 700;
  font-size: 1rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: pointer;
  transition: all 0.3s ease;
  letter-spacing: 1px;
}

.launch-btn:not(:disabled) {
  animation: pulse-border 2s infinite;
}

.launch-btn:not(:disabled):hover {
  background: var(--orange);
}

.launch-btn:disabled {
  background: #E5E5E5;
  color: #999;
  cursor: not-allowed;
}

.btn-arrow { font-weight: 400; }

@keyframes pulse-border {
  0% { box-shadow: 0 0 0 0 rgba(0, 0, 0, 0.2); }
  70% { box-shadow: 0 0 0 6px rgba(0, 0, 0, 0); }
  100% { box-shadow: 0 0 0 0 rgba(0, 0, 0, 0); }
}

/* ─── Library Panel ─── */
.library-scroll {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-height: 520px;
}

.library-scroll::-webkit-scrollbar { width: 4px; }
.library-scroll::-webkit-scrollbar-track { background: transparent; }
.library-scroll::-webkit-scrollbar-thumb { background: #CCC; }

.lib-card {
  padding: 16px 18px;
  border: 1px solid #EEE;
  cursor: pointer;
  transition: all 0.15s;
  position: relative;
  opacity: 0;
  transform: translateY(8px);
  animation: cardFadeIn 0.3s ease forwards;
}

.lib-card:hover {
  border-color: var(--orange);
  background: #FFFAF8;
}

.lib-card::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 0;
  width: 0;
  height: 2px;
  background: var(--orange);
  transition: width 0.3s;
}

.lib-card:hover::after { width: 100%; }

@keyframes cardFadeIn {
  to { opacity: 1; transform: translateY(0); }
}

.lib-card-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}

.lib-card-name {
  font-weight: 520;
  font-size: 0.9rem;
}

.lib-card-stats {
  font-family: var(--font-mono);
  font-size: 0.68rem;
  color: #AAA;
}

.lib-card-desc {
  font-size: 0.8rem;
  color: var(--gray-text);
  line-height: 1.5;
  margin-bottom: 8px;
}

.lib-card-meta {
  display: flex;
  gap: 6px;
  font-family: var(--font-mono);
  font-size: 0.66rem;
  color: #AAA;
}

.lib-card-types { color: #BBB; }

/* Library Empty State */
.library-empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  color: var(--gray-text);
}

.empty-diamond {
  font-size: 2rem;
  color: #DDD;
  margin-bottom: 16px;
}

.empty-title {
  font-family: var(--font-mono);
  font-weight: 600;
  font-size: 0.9rem;
  margin: 0 0 8px;
  color: #999;
}

.empty-hint {
  font-size: 0.82rem;
  color: #BBB;
  max-width: 240px;
  line-height: 1.5;
  margin: 0;
}

/* ─── Section 2: Tagline Bar ─── */
.tagline-bar {
  border-top: 1px solid var(--border);
  border-bottom: 1px solid var(--border);
  padding: 32px 0;
  margin: 50px 0;
  text-align: center;
}

.tagline-text {
  font-size: 1.3rem;
  font-weight: 520;
  letter-spacing: 0.5px;
  color: var(--black);
}

.blinking-cursor {
  color: var(--orange);
  animation: blink 1s step-end infinite;
  font-weight: 700;
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}

/* ─── Section 3: Explanation ─── */
.explain-section {
  display: flex;
  gap: 60px;
  margin-bottom: 60px;
}

.explain-left { flex: 0.9; }
.explain-right { flex: 1.1; }

.tag-row {
  margin-bottom: 20px;
}

.orange-tag {
  background: var(--orange);
  color: var(--white);
  padding: 4px 10px;
  font-family: var(--font-mono);
  font-weight: 700;
  letter-spacing: 1px;
  font-size: 0.72rem;
}

.explain-title {
  font-size: 2.2rem;
  font-weight: 500;
  margin: 0 0 20px;
  letter-spacing: -1px;
  line-height: 1.25;
}

.explain-desc {
  color: var(--gray-text);
  line-height: 1.8;
  font-size: 0.95rem;
  text-align: justify;
}

.highlight-bold {
  color: var(--black);
  font-weight: 700;
}

.highlight-orange {
  color: var(--orange);
  font-weight: 700;
  font-family: var(--font-mono);
}

/* Workflow */
.workflow-header {
  font-family: var(--font-mono);
  font-size: 0.8rem;
  color: #999;
  margin-bottom: 24px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.workflow-list {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.workflow-item {
  display: flex;
  align-items: flex-start;
  gap: 20px;
}

.step-num {
  font-family: var(--font-mono);
  font-weight: 700;
  color: var(--black);
  opacity: 0.3;
}

.step-info { flex: 1; }

.step-title {
  font-weight: 520;
  font-size: 1rem;
  margin-bottom: 4px;
}

.step-desc {
  font-size: 0.85rem;
  color: var(--gray-text);
  line-height: 1.5;
}

/* ─── Footer ─── */
.powered-footer {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 40px 0 30px;
  font-family: var(--font-mono);
  font-size: 0.75rem;
  color: #999;
  letter-spacing: 0.05em;
}

.footer-logo {
  height: 20px;
  width: auto;
  opacity: 0.5;
}

/* ─── Responsive ─── */
@media (max-width: 1024px) {
  .dashboard-top { flex-direction: column; }
  .explain-section { flex-direction: column; }
  .library-scroll { max-height: 400px; }
  .main-content { padding: 30px 20px 0; }
}
</style>
