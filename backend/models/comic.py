"""
漫画相关的数据模型
Comic Related Data Models
"""

from pydantic import BaseModel
from typing import Dict, List, Optional, Any


class GenerationConfig(BaseModel):
    """漫画生成配置"""
    style: str = "realistic"  # realistic, cartoon, manga, etc.
    quality: str = "high"     # low, medium, high
    panels_per_chapter: int = 6
    character_consistency: bool = True
    background_detail: str = "medium"  # low, medium, high


class ComicGenerateRequest(BaseModel):
    """漫画生成请求"""
    project_id: str
    config: GenerationConfig = GenerationConfig()


class TaskStatus(BaseModel):
    """任务状态"""
    task_id: str
    status: str  # pending, running, completed, failed
    progress: float = 0.0  # 0-100
    message: str = ""
    created_at: str
    updated_at: str
    result: Optional[Dict[str, Any]] = None


class ComicPanel(BaseModel):
    """漫画面板"""
    panel_id: int
    description: str
    characters: List[str]
    scene: str
    emotion: str
    image_path: Optional[str] = None


class ChapterComic(BaseModel):
    """章节漫画"""
    chapter_id: str
    script: Dict[str, Any]
    images: List[Dict[str, Any]]
    created_at: str


class ComicResponse(BaseModel):
    """漫画响应"""
    project_id: str
    total_chapters: int
    chapters: List[ChapterComic]
    export_ready: bool = False