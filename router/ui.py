import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

def register(app: FastAPI):

    ui_dir = Path(__file__).resolve().parent.parent / "ui"
    if not ui_dir.is_dir():
        raise RuntimeError(f"UI 目录不存在: {ui_dir}")

    # 把整个 ui 目录挂到根路径 “/”，
    # html=True 会让 StaticFiles 在找不到静态文件、且请求路径无扩展名时自动返回 index.html
    app.mount(
        "/",
        StaticFiles(directory=str(ui_dir), html=True),
        name="ui"
    )

    # 有了 html=True 之后他就没必要了
    # @app.get("/", include_in_schema=False)
    # async def index():
    #     return FileResponse(os.path.join(ui_dir, "index.html"))
