# core/audio_model.py

import logging
import json
from typing import Optional

import aiohttp
from aiohttp import ClientTimeout, TCPConnector, TraceConfig, ClientSession

from config import config

logger = logging.getLogger(__name__)

class SttModel:
    _session: Optional[ClientSession] = None

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_url: Optional[str] = None,
        model_name: Optional[str] = "qwen2-audio-lora-fy-2"
    ):
        # 配置 API 凭据和地址
        self.api_key = api_key or config.QWEN2_AUDIO_API_KEY
        if not self.api_key:
            raise ValueError("Qwen2-Audio API key is required.")
        self.api_url = api_url or config.QWEN2_AUDIO_API_URL
        self.model_name = model_name

        # 如果 class-level Session 不存在或已关闭，则创建一个
        if not SttModel._session or SttModel._session.closed:
            timeout = ClientTimeout(total=30, connect=10, sock_read=20)
            # 无限并发连接，长连接保持 5 分钟
            # 后续再建立的长连接也是五分钟
            connector = TCPConnector(limit=0, keepalive_timeout=300)

            # 可选：TraceConfig 用于细粒度请求日志
            trace = TraceConfig()
            trace.on_request_start.append(self._on_request_start)
            trace.on_request_end.append(self._on_request_end)

            SttModel._session = aiohttp.ClientSession(
                timeout=timeout,
                connector=connector,
                trace_configs=[trace]
            )
            logger.info("已初始化全局 aiohttp.ClientSession（单例）")

    @staticmethod
    async def _on_request_start(session, ctx, params):
        logger.debug(f"→ [TRACE] Starting {params.method} {params.url}")

    @staticmethod
    async def _on_request_end(session, ctx, params):
        logger.debug(f"← [TRACE] Completed with status {params.response.status}")

    @property
    def session(self) -> ClientSession:
        return SttModel._session  # 方便类型提示

    async def transcribe_audio(self, audio_url: str) -> str:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        payload = {
            "model": self.model_name,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "audio_url", "audio_url": audio_url},
                        {"type": "text", "text": "直接转录为文本"}
                    ]
                }
            ],
            "max_tokens": 500,
            "presence_penalty": 0.1,
            "frequency_penalty": 0.2,
            "stream": False
        }

        logger.info("开始请求音频转录接口")
        async with self.session.post(self.api_url, json=payload, headers=headers) as resp:

            """
            logger.info("请求已发出，等待服务器返回……") 这行日志会在 async with self.session.post(…) as resp 上下文管理器的 __aenter__ 完成后 立即执行，也就是：
            
            - 发送完请求（包括请求头和请求体）
            - 接收到响应的状态行和响应头
            - 上下文管理器 __aenter__ 返回 resp 对象
            - 然后才进入 async with 代码块，打印该日志
            - 随后才执行 await resp.text() 读取响应体

            换句话说，如果服务器在响应头阶段（status + headers）很慢，__aenter__ 阶段就会被阻塞，
            直到接收到响应头或超时为止；只有一旦响应头到齐，才会打印 “请求已发出，等待服务器返回……”。
            
            所以说如果卡在只打印开始请求音频接口的日志，，没有打印请求已发出，不是我们的问题，而是音频接口那边迟迟没有响应的问题！
            """

            logger.info("请求已发出，等待服务器返回……")
            raw = await resp.text()
            if resp.status != 200:
                # 尝试解析 JSON 错误
                try:
                    err = await resp.json(content_type=None)
                except Exception:
                    err = raw or "<empty>"
                logger.error(f"API error {resp.status}: {err!r}")
                raise Exception(f"Qwen2-Audio API error ({resp.status}): {err!r}")

            data = json.loads(raw)
            text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            logger.info(f"转录结果：{text!r}")
            return text

    @classmethod
    async def close_session(cls):
        if cls._session and not cls._session.closed:
            await cls._session.close()
            logger.info("全局 aiohttp.ClientSession 已关闭")

def get_stt_model() -> SttModel:
    """FastAPI 依赖注入工厂，始终返回同一实例（复用 Session）"""
    return SttModel()
