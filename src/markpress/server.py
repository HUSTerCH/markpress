import json
import os
import tempfile
from pathlib import Path

from typing import List

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, Response

from .converter import convert_markdown_file
from .themes import StyleConfig
from .utils.utils import get_theme_path

app = FastAPI(title="MarkPress", docs_url=None, redoc_url=None)

_AVAILABLE_THEMES = ["academic", "lark", "github", "vue"]
_AVAILABLE_ORIENTATIONS = ["portrait", "landscape"]

_THEME_META = {
    "academic": {"label": "Academic", "description": "学术论文风格，黑白经典"},
    "lark": {"label": "Lark", "description": "飞书文档风格，清爽简洁"},
    "github": {"label": "GitHub", "description": "GitHub README 风格"},
    "vue": {"label": "Vue", "description": "Vue 文档风格，绿色简约"},
}


def _build_config(theme: str, page_size: str, orientation: str) -> StyleConfig:
    """加载主题 JSON 并覆盖 page_size 与 orientation，返回 StyleConfig 对象。"""
    with get_theme_path(f"{theme}.json") as p:
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)

    if page_size and page_size != data["page"].get("size"):
        data["page"]["size"] = page_size

    if orientation and orientation in _AVAILABLE_ORIENTATIONS:
        data["page"]["orientation"] = orientation

    return StyleConfig.from_json_obj(data)


@app.get("/", response_class=HTMLResponse)
async def index():
    html_path = Path(__file__).parent / "assets" / "web" / "index.html"
    return HTMLResponse(content=html_path.read_text(encoding="utf-8"))


@app.get("/api/themes")
async def get_themes():
    return {
        "themes": [
            {"id": t, **_THEME_META[t]}
            for t in _AVAILABLE_THEMES
        ],
        "page_sizes": ["A4", "A3", "Letter"],
        "orientations": [
            {"id": "portrait", "label": "竖向", "description": "Portrait"},
            {"id": "landscape", "label": "横向", "description": "Landscape"},
        ],
    }


@app.post("/api/convert")
def convert(
    file: UploadFile = File(...),
    theme: str = Form("academic"),
    page_size: str = Form("A4"),
    orientation: str = Form("portrait"),
    images: List[UploadFile] = File(default=[]),
):
    """同步路由：FastAPI 对 def 路由自动在线程池中执行，
    从而避免 Playwright Sync API 与 asyncio 事件循环的冲突。
    images 中每个文件的 filename 字段携带 MD 内的完整相对路径（如 assets/fig1.png），
    后端按此路径在临时目录中还原子目录结构。"""
    if not file.filename.endswith(".md"):
        raise HTTPException(status_code=400, detail="仅支持 .md 文件")
    if theme not in _AVAILABLE_THEMES:
        raise HTTPException(status_code=400, detail=f"未知主题: {theme}")

    content = file.file.read()

    with tempfile.TemporaryDirectory(prefix="markpress_web_") as tmp:
        tmp_path = Path(tmp)
        md_path = tmp_path / Path(file.filename).name
        pdf_path = tmp_path / (Path(file.filename).stem + ".pdf")

        md_path.write_bytes(content)

        # img.filename 由前端设置为 MD 内的相对路径（如 "assets/fig1.png"）
        # 过滤 ".." 防止路径穿越，自动创建所需子目录
        for img in images:
            if not img.filename:
                continue
            rel_parts = [p for p in img.filename.replace("\\", "/").split("/") if p and p != ".."]
            img_dest = tmp_path.joinpath(*rel_parts)
            img_dest.parent.mkdir(parents=True, exist_ok=True)
            img_dest.write_bytes(img.file.read())
            print(f"[MarkPress] 图片已保存: {img_dest.relative_to(tmp_path)}")

        config = _build_config(theme, page_size, orientation)

        try:
            convert_markdown_file(str(md_path), str(pdf_path), theme=theme, config=config)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"转换失败: {e}")

        if not pdf_path.exists():
            raise HTTPException(status_code=500, detail="PDF 生成失败，文件不存在")

        pdf_bytes = pdf_path.read_bytes()

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{Path(file.filename).stem}.pdf"'
        },
    )


def serve(host: str = "127.0.0.1", port: int = 8080):
    """由 CLI 调用，启动 uvicorn 服务。"""
    import uvicorn
    uvicorn.run(app, host=host, port=port)
