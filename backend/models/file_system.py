"""
文件系统相关的数据模型
File System Related Data Models
"""

from pydantic import BaseModel
from typing import Dict, List, Optional, Any


class ProjectCreate(BaseModel):
    """创建项目请求模型"""
    project_name: str
    novel_text: str = ""


class ProjectInfo(BaseModel):
    """项目信息响应模型"""
    project_id: str
    project_name: str
    created_at: str
    updated_at: Optional[str] = None
    status: str
    current_step: str
    total_characters: int = 0
    project_path: Optional[str] = None


class HistoryRecord(BaseModel):
    """历史记录模型"""
    timestamp: str
    type: str
    data: Dict[str, Any]


class ProcessingResult(BaseModel):
    """处理结果模型"""
    process_type: str
    data: Dict[str, Any]
    timestamp: str


class CharacterInfo(BaseModel):
    """角色信息模型"""
    name: str
    description: str
    appearance: str
    personality: str
    reference_images: List[str] = []


class ChapterComic(BaseModel):
    """章节漫画模型"""
    chapter_id: str
    script: Dict[str, Any]
    images: List[Dict[str, Any]]
    created_at: str


class ProjectTimeline(BaseModel):
    """项目时间线响应模型"""
    project_id: str
    timeline: List[HistoryRecord]