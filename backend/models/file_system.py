"""
文件系统相关的数据模型
File System Related Data Models
"""

from pydantic import BaseModel
from typing import Dict, List, Optional, Any, Generic, TypeVar

# 泛型类型变量
T = TypeVar('T')

class ApiResponse(BaseModel, Generic[T]):
    """标准API响应格式"""
    data: T
    message: Optional[str] = None
    success: bool = True


class ProjectCreate(BaseModel):
    """创建项目请求模型"""
    name: str
    description: Optional[str] = None
    novel_text: Optional[str] = None


class NovelCreate(BaseModel):
    """创建小说请求模型"""
    title: str
    content: str
    is_primary: bool = False


class ProjectUpdate(BaseModel):
    """更新项目请求模型"""
    name: Optional[str] = None
    description: Optional[str] = None


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


class Project(BaseModel):
    """前端兼容的项目响应模型"""
    id: str
    name: str
    description: Optional[str] = None
    created_at: str
    updated_at: Optional[str] = None
    status: str
    metadata: Optional[Dict[str, Any]] = None


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


class NovelUpdate(BaseModel):
    """更新小说请求模型"""
    content: str


class ProjectTimeline(BaseModel):
    """项目时间线响应模型"""
    project_id: str
    timeline: List[HistoryRecord]