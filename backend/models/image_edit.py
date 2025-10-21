"""
图像编辑相关的数据模型
Image Editing Related Data Models
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


class ImageUploadRequest(BaseModel):
    """图像上传请求"""
    file_type: str = Field(..., description="文件类型", example="image/png")
    max_size: int = Field(10*1024*1024, description="最大文件大小", example=10485760)


class ImageEditRequest(BaseModel):
    """图像编辑请求"""
    prompt: str = Field(..., description="编辑描述", example="将人物表情改为微笑")
    base64_image: str = Field(..., description="base64编码的图像")
    base64_mask: Optional[str] = Field(None, description="base64编码的掩码图像")
    model_preference: str = Field("qwen", description="首选模型", example="qwen")
    size: str = Field("1024x1024", description="输出尺寸", example="1024x1024")


class ImageInfo(BaseModel):
    """图像信息"""
    mime_type: str = Field(..., description="MIME类型")
    encoded_size: int = Field(..., description="编码后大小")
    original_size: int = Field(..., description="原始大小")
    compression_ratio: float = Field(..., description="压缩比")


class ImageUploadResponse(BaseModel):
    """图像上传响应"""
    success: bool
    base64_data: str
    image_info: ImageInfo
    process_result: Dict[str, Any]


class ImageEditResponse(BaseModel):
    """图像编辑响应"""
    success: bool
    result_url: str
    local_path: str
    edit_params: Dict[str, Any]


class ModelInfo(BaseModel):
    """模型信息"""
    model_name: str
    model_type: str
    is_available: bool
    capabilities: List[str]


class HealthCheckResponse(BaseModel):
    """健康检查响应"""
    service_status: str
    models: Dict[str, bool]
    total_models: int
    healthy_models: int