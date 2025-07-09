<template>
  <div class="chat-page">
    <h2>语音转写对话</h2>

    <div class="controls">
      <!-- 录音按钮，在 STT 或对话流正在进行时都禁用 -->
      <el-button
        type="primary"
        :disabled="isLoading || talkLoading"
        @click="isRecording ? onStop() : onStart()"
      >
        {{ isRecording ? '停止录音' : '开始录音' }}
      </el-button>

      <!-- 提交按钮，需有录音 URL，且无任何加载中才可点 -->
      <el-button
        type="success"
        :disabled="!audioUrl || isLoading || talkLoading"
        @click="onUpload"
      >
        提交转写并对话
      </el-button>
    </div>

    <div class="status">
      <!-- STT 错误提示 -->
      <el-alert
        v-if="error"
        title="错误"
        :description="error"
        type="error"
        show-icon
      />
      <!-- 只要 STT 或对话流中任一在加载，就显示 Spinner -->
      <el-spinner
        v-if="isLoading || talkLoading"
        type="dots"
      />
    </div>

    <div class="preview" v-if="audioUrl">
      <h4>录音预览：</h4>
      <audio :src="audioUrl" controls />
    </div>

    <div class="transcript" v-if="transcript">
      <h4>转写结果：</h4>
      <p>{{ transcript }}</p>
    </div>

    <div class="conversation" v-if="talkList.length">
      <h4>对话记录：</h4>
      <div
        v-for="msg in talkList"
        :key="msg.id"
        class="message"
        :class="msg.person"
      >
        <div class="avatar">
          {{ msg.person === 'user' ? '👤' : '🤖' }}
        </div>
        <div class="bubble">
          <div v-if="msg.loading" class="typing">对方正在输入…</div>
          <div v-else>{{ msg.say }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick } from 'vue'
import { useRecorder } from '../api/useRecorder'
import { ElButton, ElAlert } from 'element-plus'
import ElSpinner from 'element-plus';

// —— 1. 录音 & 转写（STT）状态 ——
const {
  isRecording,
  audioUrl,
  transcript,
  isLoading,
  error,
  start,
  stop,
  uploadAndTranscribe,
} = useRecorder()

// —— 2. 对话流式渲染状态 ——
const talkList = ref([])
const conversationId = ref('')
const talkLoading = ref(false)

// 滚动容器到底部
const scrollToBottom = async () => {
  await nextTick()
  const c = document.querySelector('.conversation')
  if (c) c.scrollTop = c.scrollHeight
}

// —— 3. 辅助：发请求 ——
const difyRequest = async ({ path, body = null, method = 'POST', headers = {}, stream = false }) => {
  const url = 'http://211.90.240.240:30010' + path
  const isFormData = body instanceof FormData
  const fetchHeaders = isFormData
    ? headers
    : { 'Content-Type': 'application/json', ...headers }
  const res = await fetch(url, {
    method,
    headers: fetchHeaders,
    body: body
      ? (isFormData ? body : JSON.stringify(body))
      : undefined
  })
  if (!res.ok) throw new Error(`请求失败，状态：${res.status}`)
  return stream ? res : res.json()
}

// —— 4. 流式读取并更新对话 ——
const selectedWorkflowToken = ref('Bearer app-vMR1cyjPx0sAPn1W3xI3xRr3')

const streamAnswer = async ({ path, body, headers, index }) => {
  try {
    const response = await difyRequest({ path, body, headers, stream: true })
    const reader = response.body.getReader()
    const decoder = new TextDecoder('utf-8')
    let leftover = ''
    let gotFirstChunk = false

    while (true) {
      const { value, done } = await reader.read()
      if (done) break
      leftover += decoder.decode(value, { stream: true })
      const lines = leftover.split('\n')
      leftover = lines.pop()

      for (let line of lines) {
        line = line.trim()
        if (!line.startsWith('data: ')) continue
        const jsonStr = line.slice(6)
        if (!jsonStr || jsonStr === '[DONE]') continue
        const parsed = JSON.parse(jsonStr)

        if (parsed.event === 'message' && parsed.answer) {
          if (!gotFirstChunk) {
            talkList.value[index].loading = false
            gotFirstChunk = true
          }
          talkList.value[index].say += parsed.answer
          await scrollToBottom()
        }
        if (parsed.conversation_id && !conversationId.value) {
          conversationId.value = parsed.conversation_id
        }
      }
    }
  } catch (err) {
    talkList.value[index].say = '抱歉，接口出现异常。'
  } finally {
    talkList.value[index].loading = false
    talkList.value[index].complete = true
    talkLoading.value = false
  }
}

// —— 5. 发起一次对话 ——
const getAnswer = async (query) => {
  talkLoading.value = true

  // 用户提问
  talkList.value.push({
    id: Date.now() + Math.random(),
    person: 'user',
    say: query,
    loading: false,
    complete: true
  })

  // AI 占位 loading
  talkList.value.push({
    id: Date.now() + Math.random(),
    person: 'mechanical',
    say: '',
    loading: true
  })
  await scrollToBottom()

  const index = talkList.value.length - 1
  const body = {
    query,
    inputs: {},
    response_mode: 'streaming',
    user: 'abc-123',
    conversation_id: conversationId.value || ''
  }

  console.log('body: ', body)

  await streamAnswer({
    path: '/v1/chat-messages',
    body,
    headers: { Authorization: selectedWorkflowToken.value },
    index
  })
}

// —— 6. 绑定按钮方法 ——
const onStart = start
const onStop = async () => { await stop() }
const onUpload = async () => {
  await uploadAndTranscribe()
  if (transcript.value) {
    await getAnswer(transcript.value)
  }
}
</script>

<style scoped>
.chat-page {
  max-width: 600px;
  margin: 0 auto;
  padding: 20px;
  background: #fff;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  border-radius: 8px;
}

/* Controls 区域 */
.controls {
  display: flex;
  gap: 10px;
  margin-bottom: 20px;
}
.controls .el-button {
  flex: 1;
}

/* 错误／加载 状态 */
.status {
  margin-top: 10px;
  text-align: center;
}
.status .el-alert {
  margin-bottom: 10px;
}

/* 录音预览 & 转写结果 */
.preview,
.transcript {
  margin-top: 20px;
  background: #fafafa;
  padding: 12px;
  border-radius: 6px;
}
.preview h4,
.transcript h4 {
  margin: 0 0 8px;
  font-weight: 500;
}
.preview audio {
  width: 100%;
  margin-top: 8px;
}

/* 对话列表容器 */
.conversation {
  margin-top: 30px;
  max-height: 400px;
  overflow-y: auto;
  padding: 12px;
  background: #fafafa;
  border-radius: 6px;
}

/* 每条消息 */
.message {
  display: flex;
  align-items: flex-start;
  margin-bottom: 12px;
}
/* 机器人消息靠左 */
.message.mechanical .bubble {
  background: #f5f5f5;
}
/* 用户消息靠右 */
.message.user {
  flex-direction: row-reverse;
}
.message .avatar {
  width: 32px;
  font-size: 24px;
  line-height: 32px;
}
/* 对话气泡 */
.message .bubble {
  max-width: 75%;
  margin-left: 8px;
  padding: 10px;
  border-radius: 12px;
  background: #f5f5f5;
  white-space: pre-wrap;
  word-break: break-word;
}
.message.user .bubble {
  background: #d1e7dd;
  margin-left: 0;
  margin-right: 8px;
}

/* “对方正在输入” 指示 */
.typing {
  font-style: italic;
  color: #999;
}
</style>

