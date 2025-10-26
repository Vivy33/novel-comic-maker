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
    traits: List[str] = []
    reference_images: List[str] = []


class CharacterInfo(BaseModel):
    """角色信息"""
    id: str = ""
    project_id: str = ""
    name: str = ""
    description: str = ""
    traits: List[str] = []
    reference_images: List[str] = []
    # 为了兼容性保留这些字段，但设为可选
    appearance: Optional[str] = None
    personality: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

class CharacterListResponse(BaseModel):
    """角色列表响应"""
    characters: List[CharacterInfo] = []

    model_config = {"extra": "forbid"}


class ReferenceImage(BaseModel):
    """参考图片信息"""
    filename: str
    path: str
    upload_time: Optional[str] = None