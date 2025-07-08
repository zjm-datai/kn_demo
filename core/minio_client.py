import logging
import uuid
import os
from fastapi import UploadFile
from minio import Minio
from fastapi.concurrency import run_in_threadpool
from config import config

logger = logging.getLogger(__name__)

class MinioClient:
    def __init__(self):
        logger.debug(f"config.MINIO_ENDPOINT: {config.MINIO_ENDPOINT}")

        self.client = Minio(
            endpoint=config.MINIO_ENDPOINT,
            access_key=config.MINIO_ACCESS_KEY,
            secret_key=config.MINIO_SECRET_KEY,
            secure=False  # True 如果你启用了 https
        )

        self.bucket_name = "audio-test"

        # 自动创建桶（如果不存在）
        if not self.client.bucket_exists(self.bucket_name):
            self.client.make_bucket(self.bucket_name)

    async def upload_file(self, file: UploadFile) -> str:
        """
        直接上传 UploadFile 到 MinIO，并返回访问链接。
        """
        try:
            file_id = str(uuid.uuid4())
            file_name = f"{file_id}.mp3"

            # 自动获取文件大小
            await run_in_threadpool(file.file.seek, 0, os.SEEK_END)
            file_size = await run_in_threadpool(file.file.tell)
            await run_in_threadpool(file.file.seek, 0)

            # 上传对象（非流式上传）
            await run_in_threadpool(
                self.client.put_object,
                self.bucket_name,
                file_name,
                file.file,
                file_size
            )

            # file_url = await run_in_threadpool(
            #     self.client.presigned_get_object,
            #     self.bucket_name,
            #     file_name
            # )

            file_url = f"http://{config.MINIO_ENDPOINT}/{self.bucket_name}/{file_name}"

            return file_url

        except Exception as e:
            logger.error(f"上传文件时发生错误，错误信息: {e}")
            raise Exception(f"Minio error: {e}")

def get_minio_client():
    return MinioClient()
