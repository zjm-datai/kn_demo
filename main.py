import logging
from fastapi import FastAPI, UploadFile, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from core.minio_client import MinioClient, get_minio_client
from core.audio_model import SttModel, get_stt_model

# 设置日志格式
LOG_FORMAT = "[%(asctime)s] [%(levelname)s] [%(name)s:%(lineno)d] - %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

logging.basicConfig(
    level=logging.DEBUG,
    format=LOG_FORMAT,
    datefmt=DATE_FORMAT
)

logger = logging.getLogger(__name__)

app = FastAPI()

origins = [
    "http://localhost",
    "http://localhost:5173"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class TranscriptionResponse(BaseModel):
    transcription: str

@app.post("/upload-file", response_model=TranscriptionResponse)
async def upload_file(
    file: UploadFile,
    minio_client: MinioClient = Depends(get_minio_client),
    speech2text_client: SttModel = Depends(get_stt_model),
):
    try:
        file_url: str = await minio_client.upload_file(file)
        logger.debug(f"文件已经上传，minio 地址为 {file_url}")
        transcription: str = await speech2text_client.transcribe_audio(file_url)
        return TranscriptionResponse(transcription=transcription)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)