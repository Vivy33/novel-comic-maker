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
    """漫画面板/分镜画面"""
    panel_id: int
    description: str
    scene_description: str
    characters: List[str] = []
    scene: str = ""
    emotion: str = ""
    image_path: Optional[str] = None
    confirmed: bool = False
    generated_at: Optional[str] = None
    updated_at: Optional[str] = None


class ChapterComic(BaseModel):
    """故事章节漫画 - 一个故事章节包含多个分镜画面"""
    chapter_id: str
    title: Optional[str] = None
    story_text: Optional[str] = None  # 原始故事文本
    script: Optional[Dict[str, Any]] = None  # 分镜脚本
    panels: List[ComicPanel] = []  # 该章节的所有分镜画面
    created_at: str
    updated_at: str
    status: str = "pending"  # pending, generating, completed, error

    # 统计信息
    total_panels: int = 0
    confirmed_panels: int = 0
    unconfirmed_panels: int = 0


class ComicResponse(BaseModel):
    """漫画响应"""
    project_id: str
    total_chapters: int
    chapters: List[ChapterComic]
    export_ready: bool = False


class ChapterInfo(BaseModel):
    """故事章节信息"""
    chapter_id: str
    title: Optional[str] = None
    created_at: str
    updated_at: str
    status: str  # pending, generating, completed, error
    total_panels: int = 0
    confirmed_panels: int = 0
    unconfirmed_panels: int = 0

    # 章节顺序（用于排序）
    chapter_number: int = 1


class ChapterImage(BaseModel):
    """章节图像"""
    image_path: str
    panel_id: int
    confirmed: bool = False
    generated_at: str
    description: Optional[str] = None


class ChapterDetail(BaseModel):
    """故事章节详情"""
    chapter_id: str
    title: Optional[str] = None
    created_at: str
    updated_at: str
    status: str
    story_text: Optional[str] = None  # 原始故事文本
    script: Optional[Dict[str, Any]] = None  # 分镜脚本
    panels: Optional[List[ComicPanel]] = None  # 该章节的所有分镜画面
    images: Optional[List[ChapterImage]] = None  # 兼容性字段

    # 统计信息
    total_panels: int = 0
    confirmed_panels: int = 0
    unconfirmed_panels: int = 0

    # 章节顺序
    chapter_number: int = 1


class PanelConfirmRequest(BaseModel):
    """画面确认请求"""
    confirmed: bool


class BatchConfirmRequest(BaseModel):
    """批量确认请求"""
    panel_ids: List[int]
    confirmed: bool


class ChapterExportRequest(BaseModel):
    """章节导出请求"""
    format: str = "pdf"  # pdf, images, zip
    include_confirmed_only: bool = False
    resolution: str = "high"  # standard, high, ultra
    quality: str = "standard"  # standard, high


class ChapterExportResponse(BaseModel):
    """章节导出响应"""
    download_url: str
    file_size: int


class ProjectChaptersInfo(BaseModel):
    """项目章节信息 - 项目的所有故事章节"""
    project_id: str
    total_chapters: int = 0
    chapters: List[ChapterInfo] = []
    total_panels: int = 0
    total_confirmed_panels: int = 0

    # 生成状态
    completed_chapters: int = 0
    generating_chapters: int = 0
    pending_chapters: int = 0


class StorySegment(BaseModel):
    """故事段落 - 用于生成漫画的故事文本段落"""
    segment_id: str
    chapter_number: int
    text: str
    created_at: str
    processed: bool = False  # 是否已处理生成漫画