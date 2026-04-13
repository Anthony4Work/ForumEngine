<template>
  <div class="dossier-interaction-step">
    <!-- Chat Area -->
    <div class="chat-container">
      <div class="chat-header">
        <div class="chat-header-info">
          <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.5">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
          </svg>
          <span class="chat-title">Report Agent</span>
          <span class="chat-subtitle mono">Interactive Q&A</span>
        </div>
      </div>

      <!-- Messages -->
      <div class="chat-messages" ref="chatMessages">
        <div v-if="chatHistory.length === 0" class="chat-empty">
          <div class="empty-icon">
            <svg viewBox="0 0 24 24" width="40" height="40" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
            </svg>
          </div>
          <p class="empty-text">Ask questions about this mission's tactical report, deliberation findings, or agent assessments.</p>
        </div>

        <div
          v-for="(msg, idx) in chatHistory"
          :key="idx"
          class="chat-message"
          :class="msg.role"
        >
          <div class="message-avatar">
            <span>{{ msg.role === 'user' ? 'U' : 'R' }}</span>
          </div>
          <div class="message-content">
            <div class="message-header">
              <span class="sender-name">{{ msg.role === 'user' ? 'You' : 'Report Agent' }}</span>
              <span class="message-time mono">{{ formatTime(msg.timestamp) }}</span>
            </div>
            <div class="message-text" v-html="renderMarkdown(msg.content)"></div>
          </div>
        </div>

        <div v-if="isSending" class="chat-message assistant">
          <div class="message-avatar"><span>R</span></div>
          <div class="message-content">
            <div class="typing-indicator">
              <span></span><span></span><span></span>
            </div>
          </div>
        </div>
      </div>

      <!-- Input -->
      <div class="chat-input-area">
        <textarea
          v-model="chatInput"
          class="chat-input"
          placeholder="Ask about the report..."
          @keydown.enter.exact.prevent="sendMessage"
          :disabled="isSending"
          rows="1"
          ref="chatInputRef"
        ></textarea>
        <button class="send-btn" @click="sendMessage" :disabled="!chatInput.trim() || isSending">
          <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="22" y1="2" x2="11" y2="13"></line>
            <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
          </svg>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick } from 'vue'
import { chatWithReport } from '../../api/report'

const props = defineProps({
  simulationId: String,
  reportId: String
})

const chatInput = ref('')
const chatHistory = ref([])
const isSending = ref(false)
const chatMessages = ref(null)
const chatInputRef = ref(null)

const sendMessage = async () => {
  const msg = chatInput.value.trim()
  if (!msg || isSending.value) return

  chatHistory.value.push({ role: 'user', content: msg, timestamp: new Date().toISOString() })
  chatInput.value = ''
  isSending.value = true
  scrollToBottom()

  try {
    const response = await chatWithReport({
      simulation_id: props.simulationId,
      message: msg,
      chat_history: chatHistory.value.filter(m => m.role !== 'typing')
    })
    if (response.success && response.data?.response) {
      chatHistory.value.push({ role: 'assistant', content: response.data.response, timestamp: new Date().toISOString() })
    } else {
      chatHistory.value.push({ role: 'assistant', content: 'Sorry, I could not generate a response.', timestamp: new Date().toISOString() })
    }
  } catch (err) {
    chatHistory.value.push({ role: 'assistant', content: `Error: ${err.message || 'Failed to get response'}`, timestamp: new Date().toISOString() })
  } finally {
    isSending.value = false
    scrollToBottom()
  }
}

const scrollToBottom = () => {
  nextTick(() => {
    if (chatMessages.value) {
      chatMessages.value.scrollTop = chatMessages.value.scrollHeight
    }
  })
}

const formatTime = (ts) => {
  if (!ts) return ''
  try {
    return new Date(ts).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })
  } catch { return '' }
}

const renderMarkdown = (content) => {
  if (!content) return ''
  let html = content
  html = html.replace(/```(\w*)\n([\s\S]*?)```/g, '<pre class="code-block"><code>$2</code></pre>')
  html = html.replace(/`([^`]+)`/g, '<code class="inline-code">$1</code>')
  html = html.replace(/^#### (.+)$/gm, '<h5 class="md-h5">$1</h5>')
  html = html.replace(/^### (.+)$/gm, '<h4 class="md-h4">$1</h4>')
  html = html.replace(/^## (.+)$/gm, '<h3 class="md-h3">$1</h3>')
  html = html.replace(/^> (.+)$/gm, '<blockquote class="md-quote">$1</blockquote>')
  html = html.replace(/^(\s*)- (.+)$/gm, '<li class="md-li">$2</li>')
  html = html.replace(/(<li class="md-li">.*?<\/li>\s*)+/g, '<ul class="md-ul">$&</ul>')
  html = html.replace(/<\/li>\s+<li/g, '</li><li')
  html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
  html = html.replace(/\*(.+?)\*/g, '<em>$1</em>')
  html = html.replace(/\n\n/g, '</p><p class="md-p">')
  html = html.replace(/\n/g, '<br>')
  html = '<p class="md-p">' + html + '</p>'
  html = html.replace(/<p class="md-p"><\/p>/g, '')
  html = html.replace(/<p class="md-p">(<h[2-5]|<ul|<ol|<blockquote|<pre)/g, '$1')
  html = html.replace(/(<\/h[2-5]>|<\/ul>|<\/ol>|<\/blockquote>|<\/pre>)<\/p>/g, '$1')
  return html
}
</script>

<style scoped>
.dossier-interaction-step {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.chat-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.chat-header {
  padding: 16px 24px;
  border-bottom: 1px solid #222;
  background: #111;
}

.chat-header-info {
  display: flex;
  align-items: center;
  gap: 10px;
  color: #ccc;
}

.chat-title {
  font-size: 14px;
  font-weight: 600;
  color: #e0e0e0;
}

.chat-subtitle {
  font-size: 11px;
  color: #666;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 20px 24px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.chat-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  gap: 12px;
  color: #555;
  text-align: center;
}

.empty-icon { color: #333; }

.empty-text {
  max-width: 400px;
  font-size: 13px;
  line-height: 1.6;
}

.chat-message {
  display: flex;
  gap: 12px;
}

.message-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px;
  font-weight: 700;
  flex-shrink: 0;
}

.chat-message.user .message-avatar {
  background: #222;
  color: #ccc;
}

.chat-message.assistant .message-avatar {
  background: rgba(255, 69, 0, 0.15);
  color: #FF4500;
}

.message-content {
  flex: 1;
  min-width: 0;
}

.message-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.sender-name {
  font-size: 13px;
  font-weight: 600;
  color: #ccc;
}

.message-time {
  font-size: 10px;
  color: #555;
}

.message-text {
  font-size: 14px;
  line-height: 1.7;
  color: #bbb;
}

.message-text :deep(strong) { color: #e0e0e0; }
.message-text :deep(.md-quote) {
  border-left: 3px solid #FF4500;
  padding: 6px 12px;
  margin: 8px 0;
  color: #999;
}
.message-text :deep(.code-block) {
  background: #1a1a1a;
  border: 1px solid #252525;
  border-radius: 6px;
  padding: 10px;
  font-size: 12px;
  overflow-x: auto;
}

.typing-indicator {
  display: flex;
  gap: 4px;
  padding: 8px 0;
}

.typing-indicator span {
  width: 6px;
  height: 6px;
  background: #555;
  border-radius: 50%;
  animation: typing 1.2s infinite;
}

.typing-indicator span:nth-child(2) { animation-delay: 0.2s; }
.typing-indicator span:nth-child(3) { animation-delay: 0.4s; }

@keyframes typing {
  0%, 60% { opacity: 0.3; transform: translateY(0); }
  30% { opacity: 1; transform: translateY(-4px); }
}

.chat-input-area {
  display: flex;
  align-items: flex-end;
  gap: 10px;
  padding: 16px 24px;
  border-top: 1px solid #222;
  background: #111;
}

.chat-input {
  flex: 1;
  background: #1a1a1a;
  border: 1px solid #252525;
  border-radius: 8px;
  padding: 12px 16px;
  color: #e0e0e0;
  font-size: 14px;
  font-family: inherit;
  resize: none;
  outline: none;
  transition: border-color 0.2s;
}

.chat-input:focus {
  border-color: #FF4500;
}

.chat-input::placeholder {
  color: #555;
}

.send-btn {
  width: 42px;
  height: 42px;
  border-radius: 8px;
  background: #FF4500;
  border: none;
  color: #fff;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.2s, opacity 0.2s;
}

.send-btn:hover:not(:disabled) { background: #e63e00; }
.send-btn:disabled { opacity: 0.3; cursor: not-allowed; }

.mono { font-family: 'JetBrains Mono', monospace; }
</style>
