"""
角色相关的数据模型
Character Related Data Models
"""

from pydantic import BaseModel
from typing import List, Optional


class CharacterCreateRequest(BaseModel):
    """创建角色请求"""
    name: str
    description: str
    appearance: str
    personality: str


class CharacterInfo(BaseModel):
    """角色信息"""
    name: str
    description: str
    appearance: str
    personality: str
    reference_images: List[str] = []


class ReferenceImage(BaseModel):
    """参考图片信息"""
    filename: str
    path: str
    upload_time: Optional[str] = None