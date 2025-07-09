// src/api/useRecorder.js
import { ref } from 'vue'
import MicRecorder from 'mic-recorder-to-mp3'
import * as lamejs from 'lamejs'

export function useRecorder() {
  // Inject the Mp3Encoder from lamejs so Lame is defined internally
  const mp3Recorder = new MicRecorder({
    bitRate: 128,
    encoder: lamejs.Mp3Encoder
  })

  const isRecording = ref(false)
  const audioBlob = ref(null)
  const audioUrl = ref(null)
  const transcript = ref('')
  const isLoading = ref(false)
  const error = ref(null)

  // 开始录音
  const start = async () => {
    error.value = null
    try {
      await mp3Recorder.start()
      isRecording.value = true
    } catch (e) {
      error.value = '无法开始录音，请检查麦克风权限'
    }
  }

  // 停止录音并生成 MP3 Blob
  const stop = async () => {
    try {
      const [buffer, blob] = await mp3Recorder.stop().getMp3()
      audioBlob.value = blob
      audioUrl.value = URL.createObjectURL(blob)
      isRecording.value = false
    } catch (e) {
      error.value = '停止录音失败'
    }
  }

  // 上传并调用 /upload-file 接口拿转写结果
  const uploadAndTranscribe = async () => {
    if (!audioBlob.value) {
      error.value = '没有可上传的录音'
      return
    }
    isLoading.value = true
    error.value = null
    try {
      const file = new File([audioBlob.value], 'recording.mp3', { type: 'audio/mpeg' })
      const form = new FormData()
      form.append('file', file)

      const res = await fetch('/upload-file', {
        method: 'POST',
        body: form,
      })
      if (!res.ok) {
        const msg = await res.text()
        throw new Error(msg)
      }
      const data = await res.json()
      transcript.value = data.transcription
    } catch (e) {
      error.value = `上传或转写失败：${e.message || e}`
    } finally {
      isLoading.value = false
    }
  }

  return {
    // state
    isRecording,
    audioUrl,
    transcript,
    isLoading,
    error,
    // actions
    start,
    stop,
    uploadAndTranscribe,
  }
}
