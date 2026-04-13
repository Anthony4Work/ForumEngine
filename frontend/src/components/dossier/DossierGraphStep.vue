<template>
  <div class="dossier-graph-step">
    <!-- Graph Visualization -->
    <div class="graph-container">
      <GraphPanel
        v-if="graphData"
        :graphData="graphData"
        :loading="false"
        :currentPhase="'completed'"
      />
      <div v-else class="empty-state">
        <span class="empty-icon">◇</span>
        <span>No graph data available</span>
      </div>
    </div>

    <!-- Stats & Meta Bar -->
    <div class="meta-bar" v-if="graphData || projectData">
      <!-- Graph Stats -->
      <div class="stats-section" v-if="graphData">
        <h4 class="section-label">Graph Statistics</h4>
        <div class="stats-grid">
          <div class="stat-item">
            <span class="stat-value mono">{{ graphData.nodes?.length || 0 }}</span>
            <span class="stat-label">Nodes</span>
          </div>
          <div class="stat-item">
            <span class="stat-value mono">{{ graphData.edges?.length || 0 }}</span>
            <span class="stat-label">Edges</span>
          </div>
          <div class="stat-item">
            <span class="stat-value mono">{{ entityTypes.length }}</span>
            <span class="stat-label">Entity Types</span>
          </div>
        </div>
        <div class="entity-types" v-if="entityTypes.length > 0">
          <span v-for="type in entityTypes" :key="type" class="type-tag">{{ type }}</span>
        </div>
      </div>

      <!-- Documents -->
      <div class="docs-section" v-if="projectData?.files?.length">
        <h4 class="section-label">Source Documents</h4>
        <div class="docs-list">
          <div v-for="(file, idx) in projectData.files" :key="idx" class="doc-item">
            <span class="doc-type mono">{{ getExtension(file.filename) }}</span>
            <span class="doc-name">{{ file.filename }}</span>
          </div>
        </div>
      </div>

      <!-- Ontology -->
      <div class="ontology-section" v-if="projectData?.ontology">
        <h4 class="section-label">Ontology</h4>
        <div class="ontology-types">
          <div v-if="projectData.ontology.entity_types?.length" class="ontology-group">
            <span class="group-label">Entity Types:</span>
            <span v-for="et in projectData.ontology.entity_types" :key="et.name || et" class="type-tag">{{ et.name || et }}</span>
          </div>
          <div v-if="projectData.ontology.edge_types?.length" class="ontology-group">
            <span class="group-label">Edge Types:</span>
            <span v-for="et in projectData.ontology.edge_types" :key="et.name || et" class="type-tag edge-type">{{ et.name || et }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import GraphPanel from '../GraphPanel.vue'

const props = defineProps({
  graphData: Object,
  projectData: Object
})

const entityTypes = computed(() => {
  if (!props.graphData?.nodes) return []
  const types = new Set()
  props.graphData.nodes.forEach(n => {
    (n.labels || []).forEach(l => {
      if (l !== 'Entity' && l !== 'Node') types.add(l)
    })
  })
  return Array.from(types).sort()
})

const getExtension = (filename) => {
  if (!filename) return 'FILE'
  return filename.split('.').pop()?.toUpperCase() || 'FILE'
}
</script>

<style scoped>
.dossier-graph-step {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.graph-container {
  flex: 1;
  min-height: 500px;
  position: relative;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  gap: 12px;
  color: #555;
  font-size: 14px;
}

.empty-icon {
  font-size: 32px;
  color: #333;
}

.meta-bar {
  border-top: 1px solid #222;
  padding: 20px 24px;
  display: flex;
  gap: 40px;
  background: #111;
  flex-wrap: wrap;
}

.section-label {
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 1px;
  color: #666;
  margin: 0 0 12px 0;
}

.stats-grid {
  display: flex;
  gap: 24px;
  margin-bottom: 10px;
}

.stat-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.stat-value {
  font-size: 20px;
  font-weight: 700;
  color: #FF4500;
}

.stat-label {
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  text-transform: uppercase;
  color: #666;
}

.mono { font-family: 'JetBrains Mono', monospace; }

.entity-types, .ontology-types {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.type-tag {
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  color: #60a5fa;
  background: rgba(96, 165, 250, 0.1);
  padding: 3px 8px;
  border-radius: 3px;
  border: 1px solid rgba(96, 165, 250, 0.15);
}

.type-tag.edge-type {
  color: #a78bfa;
  background: rgba(167, 139, 250, 0.1);
  border-color: rgba(167, 139, 250, 0.15);
}

.docs-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.doc-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.doc-type {
  font-size: 10px;
  color: #FF4500;
  background: rgba(255, 69, 0, 0.1);
  padding: 2px 6px;
  border-radius: 3px;
  min-width: 36px;
  text-align: center;
}

.doc-name {
  font-size: 13px;
  color: #ccc;
}

.ontology-group {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  margin-bottom: 8px;
}

.group-label {
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  text-transform: uppercase;
  color: #666;
  margin-right: 4px;
}
</style>
