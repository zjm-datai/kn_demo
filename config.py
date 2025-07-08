from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class MinioConfig(BaseSettings):
    MINIO_ENDPOINT: str = Field(
        description="Minio server endpoint",
        default="localhost:9000"
    )
    MINIO_ACCESS_KEY: str = Field(
        description="Minio access key",
        default="minioadmin"
    )
    MINIO_SECRET_KEY: str = Field(
        description="Minio secret key",
        default="minioadmin"
    )

class Qwen2AudioConfig(BaseSettings):
    QWEN2_AUDIO_API_URL: str = Field(
        description="Qwen2-Audio API URL",
        default="http://qwen2-audio-api.example.com/transcribe"
    )
    QWEN2_AUDIO_API_KEY: str = Field(
        description="Qwen2-Audio API Key",
        default=""
    )

class Config(MinioConfig, Qwen2AudioConfig):
    model_config = SettingsConfigDict(
        env_file=".env",  # 从 .env 文件加载环境变量
        env_file_encoding="utf-8",  # 文件编码
        extra="ignore"  # 忽略额外的环境变量
    )

config = Config()