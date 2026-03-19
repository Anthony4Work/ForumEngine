<template>
  <div class="library-container">
    <!-- Navigation Bar -->
    <nav class="navbar">
      <div class="nav-brand" @click="$router.push('/')">
        <img src="/indramind.svg" alt="IndraMind" class="nav-logo" />
        FORUMENGINE
      </div>
      <div class="nav-links">
        <span class="nav-status-text">Knowledge Graph Library</span>
      </div>
    </nav>

    <div class="main-content">
      <!-- Header -->
      <div class="library-header">
        <div class="header-left">
          <div class="tag-row">
            <span class="orange-tag">Graph Library</span>
            <span class="version-text">/ {{ graphs.length }} graphs</span>
          </div>
          <h1 class="page-title">Knowledge Graphs</h1>
          <p class="page-desc">
            Reusable knowledge graphs built from your documents. Select one to launch a new deliberation without rebuilding.
          </p>
        </div>
        <div class="header-actions">
          <button class="action-btn primary" @click="$router.push('/')">
            + New Graph
          </button>
        </div>
      </div>

      <!-- Loading -->
      <div v-if="loading" class="loading-state">
        <div class="loading-spinner"></div>
        <span>Loading graphs...</span>
      </div>

      <!-- Empty state -->
      <div v-else-if="graphs.length === 0" class="empty-state">
        <div class="empty-icon">◇</div>
        <h3>No Knowledge Graphs Yet</h3>
        <p>Upload documents and build your first knowledge graph from the home page.</p>
        <button class="action-btn primary" @click="$router.push('/')">Get Started</button>
      </div>

      <!-- Graph Grid -->
      <div v-else class="graph-grid">
        <div
          v-for="graph in graphs"
          :key="graph.graph_id"
          class="graph-card"
        >
          <!-- Card Header -->
          <div class="card-header">
            <div class="card-id">{{ graph.graph_id.substring(0, 16) }}</div>
            <div class="card-stats">
              <span class="stat">{{ graph.node_count }} nodes</span>
              <span class="stat-sep">/</span>
              <span class="stat">{{ graph.edge_count }} edges</span>
            </div>
          </div>

          <!-- Card Name -->
          <h3 class="card-name">{{ graph.name }}</h3>

          <!-- Description -->
          <p class="card-desc">{{ truncate(graph.description, 120) }}</p>

          <!-- Documents -->
          <div class="card-docs">
            <div
              v-for="(doc, i) in graph.documents.slice(0, 3)"
              :key="i"
              class="doc-chip"
            >
              <span class="doc-icon">{{ getDocIcon(doc.filename) }}</span>
              {{ truncate(doc.filename, 25) }}
            </div>
            <span v-if="graph.documents.length > 3" class="more-docs">
              +{{ graph.documents.length - 3 }} more
            </span>
          </div>

          <!-- Tags -->
          <div class="card-tags" v-if="graph.tags && graph.tags.length">
            <span v-for="tag in graph.tags" :key="tag" class="tag-chip">{{ tag }}</span>
          </div>

          <!-- Entity Types -->
          <div class="card-entities" v-if="graph.entity_types && graph.entity_types.length">
            <span
              v-for="et in graph.entity_types.slice(0, 5)"
              :key="et"
              class="entity-chip"
            >{{ et }}</span>
            <span v-if="graph.entity_types.length > 5" class="more-entities">
              +{{ graph.entity_types.length - 5 }}
            </span>
          </div>

          <!-- Footer -->
          <div class="card-footer">
            <div class="footer-meta">
              <span class="meta-item">{{ graph.deliberation_count }} deliberations</span>
              <span class="meta-sep">|</span>
              <span class="meta-item">{{ formatDate(graph.created_at) }}</span>
            </div>
          </div>

          <!-- Actions -->
          <div class="card-actions">
            <button class="card-btn explore" @click="exploreGraph(graph)">
              Explore
            </button>
            <button class="card-btn query" @click="newQuery(graph)">
              New Query
            </button>
            <button class="card-btn delete" @click="confirmDelete(graph)">
              Delete
            </button>
          </div>

          <!-- Bottom accent line -->
          <div class="card-accent"></div>
        </div>
      </div>
    </div>

    <!-- Footer -->
    <footer class="powered-footer">
      <img src="/indramind.svg" alt="IndraMind" class="footer-logo" />
      <span>Powered by IndraMind</span>
    </footer>

    <!-- Delete confirmation modal -->
    <div v-if="deleteTarget" class="modal-overlay" @click.self="deleteTarget = null">
      <div class="modal-box">
        <h3>Delete Graph</h3>
        <p>This will permanently delete the knowledge graph <strong>{{ deleteTarget.name }}</strong> and all associated data from Neo4j.</p>
        <div class="modal-actions">
          <button class="modal-btn cancel" @click="deleteTarget = null">Cancel</button>
          <button class="modal-btn confirm" @click="doDelete">Delete</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getGraphLibrary, deleteGraph } from '../api/graph.js'

const router = useRouter()
const graphs = ref([])
const loading = ref(true)
const deleteTarget = ref(null)

onMounted(async () => {
  await loadGraphs()
})

async function loadGraphs() {
  loading.value = true
  try {
    const res = await getGraphLibrary()
    if (res.data?.success) {
      graphs.value = res.data.data || []
    }
  } catch (e) {
    console.error('Failed to load graph library:', e)
  } finally {
    loading.value = false
  }
}

function exploreGraph(graph) {
  if (graph.project_id) {
    router.push({ name: 'Process', params: { projectId: graph.project_id } })
  }
}

function newQuery(graph) {
  router.push({ name: 'NewQuery', params: { graphId: graph.graph_id } })
}

function confirmDelete(graph) {
  deleteTarget.value = graph
}

async function doDelete() {
  if (!deleteTarget.value) return
  try {
    await deleteGraph(deleteTarget.value.graph_id)
    graphs.value = graphs.value.filter(g => g.graph_id !== deleteTarget.value.graph_id)
    deleteTarget.value = null
  } catch (e) {
    console.error('Failed to delete graph:', e)
  }
}

function truncate(text, max) {
  if (!text) return ''
  return text.length > max ? text.substring(0, max) + '...' : text
}

function getDocIcon(filename) {
  if (!filename) return '?'
  const ext = filename.split('.').pop()?.toLowerCase()
  if (ext === 'pdf') return 'P'
  if (ext === 'md' || ext === 'markdown') return 'M'
  if (ext === 'txt') return 'T'
  return '?'
}

function formatDate(dateStr) {
  if (!dateStr) return ''
  try {
    const d = new Date(dateStr)
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
  } catch {
    return dateStr.substring(0, 10)
  }
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

.library-container {
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

.nav-status-text {
  font-family: var(--font-mono);
  font-size: 0.75rem;
  color: #666;
  letter-spacing: 1px;
  text-transform: uppercase;
}

/* Main content */
.main-content {
  max-width: 1400px;
  margin: 0 auto;
  padding: 60px 40px;
}

/* Header */
.library-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 50px;
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

.version-text {
  color: #999;
  font-weight: 500;
}

.page-title {
  font-size: 2.5rem;
  font-weight: 500;
  margin: 0 0 10px 0;
  letter-spacing: -1px;
}

.page-desc {
  color: var(--gray-text);
  max-width: 500px;
  line-height: 1.6;
}

.action-btn {
  font-family: var(--font-mono);
  font-weight: 700;
  font-size: 0.9rem;
  padding: 14px 28px;
  border: 1px solid var(--black);
  cursor: pointer;
  transition: all 0.2s;
  letter-spacing: 0.5px;
}

.action-btn.primary {
  background: var(--black);
  color: var(--white);
}

.action-btn.primary:hover {
  background: var(--orange);
  border-color: var(--orange);
}

/* Loading */
.loading-state {
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

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Empty state */
.empty-state {
  text-align: center;
  padding: 80px 0;
}

.empty-icon {
  font-size: 3rem;
  color: #DDD;
  margin-bottom: 15px;
}

.empty-state h3 {
  font-size: 1.3rem;
  font-weight: 520;
  margin-bottom: 10px;
}

.empty-state p {
  color: var(--gray-text);
  margin-bottom: 25px;
}

/* Graph Grid */
.graph-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(380px, 1fr));
  gap: 24px;
}

/* Graph Card */
.graph-card {
  border: 1px solid var(--border);
  padding: 28px;
  position: relative;
  transition: all 0.2s;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.graph-card:hover {
  border-color: #999;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.06);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-id {
  font-family: var(--font-mono);
  font-size: 0.7rem;
  color: #AAA;
  letter-spacing: 0.5px;
}

.card-stats {
  font-family: var(--font-mono);
  font-size: 0.75rem;
  color: var(--gray-text);
}

.stat-sep { margin: 0 6px; color: #CCC; }

.card-name {
  font-size: 1.2rem;
  font-weight: 520;
  margin: 0;
  line-height: 1.3;
}

.card-desc {
  font-size: 0.85rem;
  color: var(--gray-text);
  line-height: 1.6;
  margin: 0;
}

/* Documents */
.card-docs {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.doc-chip {
  display: flex;
  align-items: center;
  gap: 5px;
  font-family: var(--font-mono);
  font-size: 0.72rem;
  background: #F5F5F5;
  padding: 4px 8px;
  color: var(--gray-text);
}

.doc-icon {
  width: 16px;
  height: 16px;
  background: var(--black);
  color: var(--white);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.6rem;
  font-weight: 700;
}

.more-docs {
  font-family: var(--font-mono);
  font-size: 0.72rem;
  color: #AAA;
  padding: 4px 0;
}

/* Tags */
.card-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.tag-chip {
  font-family: var(--font-mono);
  font-size: 0.7rem;
  background: transparent;
  border: 1px solid var(--border);
  padding: 2px 8px;
  color: var(--gray-text);
}

/* Entity types */
.card-entities {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
}

.entity-chip {
  font-family: var(--font-mono);
  font-size: 0.68rem;
  background: #FFF5F0;
  border: 1px solid #FFE0D0;
  padding: 2px 7px;
  color: var(--orange);
}

.more-entities {
  font-family: var(--font-mono);
  font-size: 0.68rem;
  color: #AAA;
  padding: 2px 0;
}

/* Footer */
.card-footer {
  margin-top: auto;
}

.footer-meta {
  font-family: var(--font-mono);
  font-size: 0.72rem;
  color: #AAA;
}

.meta-sep { margin: 0 8px; }

/* Actions */
.card-actions {
  display: flex;
  gap: 8px;
  padding-top: 10px;
  border-top: 1px solid #F0F0F0;
}

.card-btn {
  flex: 1;
  font-family: var(--font-mono);
  font-size: 0.75rem;
  font-weight: 600;
  padding: 10px 0;
  border: 1px solid var(--border);
  background: transparent;
  cursor: pointer;
  transition: all 0.15s;
  letter-spacing: 0.3px;
}

.card-btn.explore:hover {
  background: #F5F5F5;
  border-color: #999;
}

.card-btn.query {
  background: var(--black);
  color: var(--white);
  border-color: var(--black);
}

.card-btn.query:hover {
  background: var(--orange);
  border-color: var(--orange);
}

.card-btn.delete {
  flex: 0.5;
  color: #999;
  border-color: #EEE;
}

.card-btn.delete:hover {
  color: #C00;
  border-color: #C00;
}

/* Card accent */
.card-accent {
  position: absolute;
  bottom: 0;
  left: 0;
  width: 0;
  height: 2px;
  background: var(--orange);
  transition: width 0.3s;
}

.graph-card:hover .card-accent {
  width: 100%;
}

/* Modal */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-box {
  background: var(--white);
  padding: 30px;
  max-width: 440px;
  width: 100%;
  border: 1px solid var(--border);
}

.modal-box h3 {
  font-size: 1.1rem;
  margin: 0 0 12px 0;
}

.modal-box p {
  color: var(--gray-text);
  font-size: 0.9rem;
  line-height: 1.6;
  margin-bottom: 25px;
}

.modal-actions {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
}

.modal-btn {
  font-family: var(--font-mono);
  font-size: 0.8rem;
  font-weight: 600;
  padding: 10px 24px;
  border: 1px solid var(--border);
  cursor: pointer;
  transition: all 0.15s;
}

.modal-btn.cancel {
  background: transparent;
}

.modal-btn.confirm {
  background: #C00;
  color: var(--white);
  border-color: #C00;
}

.modal-btn.confirm:hover {
  background: #A00;
}

/* Footer */
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

/* Responsive */
@media (max-width: 860px) {
  .graph-grid {
    grid-template-columns: 1fr;
  }
  .library-header {
    flex-direction: column;
    gap: 20px;
  }
}
</style>
