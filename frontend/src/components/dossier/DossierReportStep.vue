<template>
  <div class="dossier-report-step">
    <div v-if="reportData" class="report-content-wrapper">
      <!-- Report Header -->
      <div class="report-header-block">
        <div class="report-meta">
          <span class="report-tag">Prediction Report</span>
          <span class="report-id mono">{{ reportData.report_id || '' }}</span>
        </div>
        <h1 class="main-title">{{ outline?.title || 'Report' }}</h1>
        <p class="sub-title" v-if="outline?.summary">{{ outline.summary }}</p>
        <div class="header-divider"></div>
      </div>

      <!-- Sections -->
      <div class="sections-list">
        <div
          v-for="(section, idx) in sections"
          :key="idx"
          class="report-section"
        >
          <div class="section-header-row" @click="toggleCollapse(idx)">
            <span class="section-number mono">{{ String(idx + 1).padStart(2, '0') }}</span>
            <h3 class="section-title">{{ section.title }}</h3>
            <svg
              class="collapse-icon"
              :class="{ collapsed: collapsedSections.has(idx) }"
              viewBox="0 0 24 24" width="18" height="18"
              fill="none" stroke="currentColor" stroke-width="2"
            >
              <polyline points="6 9 12 15 18 9"></polyline>
            </svg>
          </div>
          <div class="section-body" v-show="!collapsedSections.has(idx)">
            <div v-if="section.content" class="generated-content" v-html="renderMarkdown(section.content)"></div>
            <div v-else class="no-content">No content available</div>
          </div>
        </div>
      </div>
    </div>

    <div v-else class="empty-state">
      <span class="empty-icon">◆</span>
      <span>No report available</span>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  reportData: Object
})

const collapsedSections = ref(new Set())

const outline = computed(() => props.reportData?.outline || null)
const sections = computed(() => outline.value?.sections || [])

const toggleCollapse = (idx) => {
  const newSet = new Set(collapsedSections.value)
  if (newSet.has(idx)) newSet.delete(idx)
  else newSet.add(idx)
  collapsedSections.value = newSet
}

const renderMarkdown = (content) => {
  if (!content) return ''
  let html = content.replace(/^##\s+.+\n+/, '')
  html = html.replace(/```(\w*)\n([\s\S]*?)```/g, '<pre class="code-block"><code>$2</code></pre>')
  html = html.replace(/`([^`]+)`/g, '<code class="inline-code">$1</code>')
  html = html.replace(/^#### (.+)$/gm, '<h5 class="md-h5">$1</h5>')
  html = html.replace(/^### (.+)$/gm, '<h4 class="md-h4">$1</h4>')
  html = html.replace(/^## (.+)$/gm, '<h3 class="md-h3">$1</h3>')
  html = html.replace(/^# (.+)$/gm, '<h2 class="md-h2">$1</h2>')
  html = html.replace(/^> (.+)$/gm, '<blockquote class="md-quote">$1</blockquote>')
  html = html.replace(/^(\s*)- (.+)$/gm, (match, indent, text) => {
    const level = Math.floor(indent.length / 2)
    return `<li class="md-li" data-level="${level}">${text}</li>`
  })
  html = html.replace(/^(\s*)(\d+)\. (.+)$/gm, (match, indent, num, text) => {
    const level = Math.floor(indent.length / 2)
    return `<li class="md-oli" data-level="${level}">${text}</li>`
  })
  html = html.replace(/(<li class="md-li"[^>]*>.*?<\/li>\s*)+/g, '<ul class="md-ul">$&</ul>')
  html = html.replace(/(<li class="md-oli"[^>]*>.*?<\/li>\s*)+/g, '<ol class="md-ol">$&</ol>')
  html = html.replace(/<\/li>\s+<li/g, '</li><li')
  html = html.replace(/<ul class="md-ul">\s+/g, '<ul class="md-ul">')
  html = html.replace(/<ol class="md-ol">\s+/g, '<ol class="md-ol">')
  html = html.replace(/\s+<\/ul>/g, '</ul>')
  html = html.replace(/\s+<\/ol>/g, '</ol>')
  html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
  html = html.replace(/\*(.+?)\*/g, '<em>$1</em>')
  html = html.replace(/_(.+?)_/g, '<em>$1</em>')
  html = html.replace(/^---$/gm, '<hr class="md-hr">')
  html = html.replace(/\n\n/g, '</p><p class="md-p">')
  html = html.replace(/\n/g, '<br>')
  html = '<p class="md-p">' + html + '</p>'
  html = html.replace(/<p class="md-p"><\/p>/g, '')
  html = html.replace(/<p class="md-p">(<h[2-5])/g, '$1')
  html = html.replace(/(<\/h[2-5]>)<\/p>/g, '$1')
  html = html.replace(/<p class="md-p">(<ul|<ol|<blockquote|<pre|<hr)/g, '$1')
  html = html.replace(/(<\/ul>|<\/ol>|<\/blockquote>|<\/pre>)<\/p>/g, '$1')
  html = html.replace(/<br>\s*(<ul|<ol|<blockquote)/g, '$1')
  html = html.replace(/(<\/ul>|<\/ol>|<\/blockquote>)\s*<br>/g, '$1')
  html = html.replace(/<p class="md-p">(<br>\s*)+(<ul|<ol|<blockquote|<pre|<hr)/g, '$2')
  html = html.replace(/(<br>\s*){2,}/g, '<br>')
  return html
}
</script>

<style scoped>
.dossier-report-step {
  height: 100%;
  overflow-y: auto;
  padding: 32px;
  background: #0e0e0e;
}

.report-content-wrapper {
  max-width: 800px;
  margin: 0 auto;
}

.report-header-block {
  margin-bottom: 32px;
}

.report-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.report-tag {
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 1px;
  color: #FF4500;
  background: rgba(255, 69, 0, 0.1);
  padding: 4px 10px;
  border-radius: 3px;
}

.report-id {
  font-size: 11px;
  color: #555;
}

.main-title {
  font-size: 28px;
  font-weight: 700;
  color: #e0e0e0;
  margin: 0 0 8px 0;
  line-height: 1.3;
}

.sub-title {
  font-size: 15px;
  color: #888;
  line-height: 1.6;
  margin: 0;
}

.header-divider {
  height: 1px;
  background: linear-gradient(to right, #FF4500, transparent);
  margin-top: 20px;
}

.sections-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.report-section {
  border: 1px solid #1f1f1f;
  border-radius: 8px;
  overflow: hidden;
}

.section-header-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px 20px;
  cursor: pointer;
  transition: background 0.2s;
}

.section-header-row:hover {
  background: rgba(255, 255, 255, 0.02);
}

.section-number {
  font-size: 14px;
  font-weight: 700;
  color: #FF4500;
  min-width: 28px;
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  color: #ddd;
  margin: 0;
  flex: 1;
}

.collapse-icon {
  color: #555;
  transition: transform 0.2s;
}

.collapse-icon.collapsed {
  transform: rotate(-90deg);
}

.section-body {
  padding: 0 20px 20px;
}

.generated-content {
  font-size: 14px;
  line-height: 1.8;
  color: #bbb;
}

.generated-content :deep(strong) { color: #e0e0e0; }
.generated-content :deep(.md-quote) {
  border-left: 3px solid #FF4500;
  padding: 8px 16px;
  margin: 12px 0;
  color: #999;
  background: rgba(255, 69, 0, 0.03);
}
.generated-content :deep(.md-h3) { font-size: 16px; color: #ddd; margin: 20px 0 8px; }
.generated-content :deep(.md-h4) { font-size: 14px; color: #ccc; margin: 16px 0 6px; }
.generated-content :deep(.md-ul), .generated-content :deep(.md-ol) {
  padding-left: 20px;
  margin: 8px 0;
}
.generated-content :deep(.md-li), .generated-content :deep(.md-oli) {
  padding: 2px 0;
}
.generated-content :deep(.code-block) {
  background: #1a1a1a;
  border: 1px solid #252525;
  border-radius: 6px;
  padding: 12px;
  overflow-x: auto;
  font-size: 12px;
}
.generated-content :deep(.inline-code) {
  background: #1a1a1a;
  padding: 2px 6px;
  border-radius: 3px;
  font-size: 12px;
}

.no-content {
  color: #555;
  font-size: 13px;
  font-style: italic;
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
