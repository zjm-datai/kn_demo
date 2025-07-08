import logging
from typing import Optional
import aiohttp
from aiohttp import ClientTimeout
import json

from config import config

logger = logging.getLogger(__name__)

class SttModel:
    def __init__(
        self,
        api_key: Optional[str] = None,
        api_url: Optional[str] = None,
        # model_name: Optional[str] = "Qwen2-Audio-7B-Lora"
        model_name: Optional[str] = "qwen2-audio-lora-fy-2"
    ):
        self.api_key = api_key or config.QWEN2_AUDIO_API_KEY
        if not self.api_key:
            raise ValueError("Qwen2-Audio API key is required.")
        self.api_url = api_url or config.QWEN2_AUDIO_API_URL
        self.model_name = model_name

    async def transcribe_audio(self, audio_url: str) -> str:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        # payload = {
        #     "model": self.model_name,
        #     "messages": [
        #         {
        #             "role": "user",
        #             "content": [
        #                 {
        #                     "type": "audio_url",
        #                     "audio_url": {"url": audio_url}
        #                 },
        #                 {
        #                     "type": "text",
        #                     "text": "直接转录为文本"
        #                 }
        #             ]
        #         }
        #     ],
        #     "max_tokens": 500,
        #     "presence_penalty": 0.1,
        #     "frequency_penalty": 0.2,
        #     "stream": False
        # }

        payload = {
            "model": self.model_name,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "audio_url",
                            "audio_url": audio_url
                        },
                        {
                            "type": "text",
                            "text": "直接转录为文本"
                        }
                    ]
                }
            ],
            "max_tokens": 500,
            "presence_penalty": 0.1,
            "frequency_penalty": 0.2,
            "stream": False
        }

        logger.debug("开始请求音频转录接口")

        # 比如：connect 最多 10s，recv body 最多 60s，总超时 70s
        timeout = ClientTimeout(total=70, connect=10, sock_read=60)

        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(self.api_url, json=payload, headers=headers) as response:
                logger.debug(f"请求已发出，等待服务器返回……")
                # 先拿到原始文本（无视 Content-Type）
                raw_text = await response.text()

                logger.debug(f"拿到原始返回（{len(raw_text)} bytes）")
                
                # 如果状态码不是 200，就详尽地输出错误信息
                if response.status != 200:
                    error_body = None
                    # 尝试直接解析 JSON（跳过 content-type 检查）
                    try:
                        error_body = await response.json(content_type=None)
                    except Exception:
                        # 再退一步，当作纯文本看
                        error_body = raw_text or "<empty response>"
                    
                    logger.error(
                        f"调用语音模型接口返回错误 -- "
                        f"status={response.status} reason={response.reason} "
                        f"headers={dict(response.headers)} "
                        f"body={error_body!r}"
                    )
                    raise Exception(f"Qwen2-Audio API error ({response.status}): {error_body!r}")

                # 3. 状态码 200，打印原始文本并尝试解析
                logger.debug(f"Raw response text: {raw_text!r}")
                try:
                    result = json.loads(raw_text)
                except json.JSONDecodeError:
                    raise Exception(f"Unexpected non-JSON response: {raw_text!r}")

                logger.debug(f"得到转录文本内容：{result}")
                return result.get("choices", [{}])[0].get("message", {}).get("content", "")

def get_stt_model() -> SttModel:
    return SttModel()
