"""
文生图相关的数据模型
Text-to-Image Related Data Models
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


class Text2ImageRequest(BaseModel):
    """文生图请求模型"""
    prompt: str = Field(..., min_length=10, max_length=1000, description="图像描述文本")
    model_preference: str = Field("doubao-seedream-4-0-250828", description="首选模型")
    size: str = Field("1024x1024", description="图像尺寸")
    quality: str = Field("standard", description="图像质量")
    style: str = Field("realistic", description="图像风格")
    sequential_generation: str = Field("auto", description="组图设置: auto 或 disabled")
    max_images: int = Field(1, ge=1, le=5, description="最大生成图片数量 (1-5)")
    stream: bool = Field(True, description="是否启用流式输出")


class Text2ImageResponse(BaseModel):
    """文生图响应模型（单图）"""
    success: bool
    image_url: Optional[str] = None
    local_path: Optional[str] = None
    prompt_used: str
    model_used: str
    size: str
    quality: str
    style: str
    generation_time: Optional[float] = None
    error: Optional[str] = None


class Text2ImageBatchResponse(BaseModel):
    """文生图响应模型（组图）"""
    success: bool
    image_urls: Optional[List[str]] = None
    local_paths: Optional[List[str]] = None
    total_generated: int
    prompt_used: str
    model_used: str
    size: str
    quality: str
    style: str
    sequential_generation: str
    max_images: int
    generation_time: Optional[float] = None
    error: Optional[str] = None


class BatchGenerateRequest(BaseModel):
    """批量生成请求模型"""
    prompts: List[str] = Field(..., min_items=1, max_items=5, description="提示词列表")
    model_preference: str = Field("doubao-seedream-4-0-250828", description="首选模型")
    size: str = Field("1024x1024", description="图像尺寸")
    quality: str = Field("standard", description="图像质量")
    style: str = Field("realistic", description="图像风格")


class BatchGenerateResponse(BaseModel):
    """批量生成响应模型"""
    success: bool
    total_requests: int
    successful_count: int
    results: List[Dict[str, Any]]
    model_used: str
    size: str
    quality: str
    style: str
    total_generation_time: Optional[float] = None


class ModelInfo(BaseModel):
    """模型信息模型"""
    name: str
    type: str
    status: str
    description: Optional[str] = None


class ModelsResponse(BaseModel):
    """模型列表响应模型"""
    available_models: List[ModelInfo]
    total_count: int
    recommended: str


class StyleInfo(BaseModel):
    """风格信息模型"""
    name: str
    description: str
    examples: List[str]


class StylesResponse(BaseModel):
    """风格列表响应模型"""
    supported_styles: Dict[str, StyleInfo]
    total_count: int
    default: str


class PromptEnhanceRequest(BaseModel):
    """提示词增强请求模型"""
    original_prompt: str = Field(..., min_length=5, description="原始提示词")
    target_style: str = Field("realistic", description="目标风格")


class PromptEnhanceResponse(BaseModel):
    """提示词增强响应模型"""
    success: bool
    original_prompt: str
    enhanced_prompt: str
    target_style: str
    enhancement_method: Optional[str] = None
    improvement_suggestions: Optional[List[str]] = None


class HealthCheckResponse(BaseModel):
    """健康检查响应模型"""
    service_status: str
    available_models: int
    model_names: List[str]
    test_status: str
    error: Optional[str] = None


class GenerationStats(BaseModel):
    """生成统计模型"""
    total_generations: int
    successful_generations: int
    failed_generations: int
    average_generation_time: float
    most_used_models: Dict[str, int]
    most_used_styles: Dict[str, int]
    popular_sizes: Dict[str, int]