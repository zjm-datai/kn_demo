# main.py
import os
import time
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from core.minio_client import MinioClient, get_minio_client
from core.audio_model import SttModel, get_stt_model
from router import ui

for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
    lg = logging.getLogger(name)
    lg.handlers.clear()
    lg.propagate = False

# 设置时区为北京时间（Asia/Shanghai），并应用
os.environ['TZ'] = 'Asia/Shanghai'
time.tzset()  # 使 os.environ['TZ'] 立即生效 :contentReference[oaicite:0]{index=0}

# 日志格式：加入 %z 显示时区偏移（+0800）
LOG_FORMAT = "[%(asctime)s] [%(levelname)s] [%(name)s:%(lineno)d] - %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S %z"  # 若想显示时区名称可用 %Z :contentReference[oaicite:1]{index=1}

logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT,
    datefmt=DATE_FORMAT,
)

logger = logging.getLogger(__name__)

# Lifespan 上下文：启动时预热 Session，关闭时释放资源
@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- startup ---
    # 1) 预热 STT 单例 client（建立长连接、DNS 缓存等）
    get_stt_model()
    logger.info("应用启动：STT 客户端已预热")
    # 2) 如果有其他资源启动前初始化，也可以放这里
    yield
    # --- shutdown ---
    # 关闭全局 aiohttp session
    await SttModel.close_session()
    logger.info("应用关闭：STT 客户端连接已释放")

# 将 lifespan 传给 FastAPI 构造函数
app = FastAPI(lifespan=lifespan)

# CORS 配置
origins = ["http://localhost", "http://localhost:5173"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API 返回模型
class TranscriptionResponse(BaseModel):
    transcription: str

@app.post("/upload-file", response_model=TranscriptionResponse)
async def upload_file(
    file: UploadFile,
    minio_client: MinioClient = Depends(get_minio_client),
    stt_client: SttModel = Depends(get_stt_model),
):
    try:
        file_url = await minio_client.upload_file(file)
        logger.info(f"文件上传到 MinIO，URL={file_url}")

        transcription = await stt_client.transcribe_audio(file_url)
        logger.debug("转录完成")
        return TranscriptionResponse(transcription=transcription)
    except Exception as e:
        logger.exception("处理上传或转录时出错")
        raise HTTPException(status_code=500, detail=str(e))

# 挂载前端 UI 路由
ui.register(app=app)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
