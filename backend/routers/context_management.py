"""
上下文管理API路由
Context Management API Routes

提供对话上下文管理和结构化数据生成功能
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import logging

from services.ai_service import AIService

logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(prefix="/context", tags=["context-management"])

# 依赖注入
def get_ai_service():
    return AIService()


# 请求/响应模型
class CreateContextRequest(BaseModel):
    """创建上下文请求"""
    max_messages: int = Field(20, ge=1, le=100, description="最大消息数量")
    max_tokens: int = Field(8000, ge=1000, le=32000, description="最大token数量")


class GenerateTextRequest(BaseModel):
    """文本生成请求"""
    prompt: str = Field(..., min_length=1, max_length=10000, description="提示词")
    model_preference: str = Field("deepseek-v3-1-terminus", description="模型偏好")
    temperature: float = Field(0.7, ge=0.0, le=2.0, description="温度参数")
    use_json_schema: bool = Field(False, description="是否使用JSON Schema")
    schema_type: Optional[str] = Field(None, description="Schema类型")
    context_id: Optional[str] = Field(None, description="上下文ID")


class GenerateTextWithContextRequest(BaseModel):
    """带上下文的文本生成请求"""
    prompt: str = Field(..., min_length=1, max_length=10000, description="提示词")
    system_prompt: Optional[str] = Field(None, description="系统提示词")
    model_preference: str = Field("deepseek-v3-1-terminus", description="模型偏好")
    temperature: float = Field(0.7, ge=0.0, le=2.0, description="温度参数")
    context_id: Optional[str] = Field(None, description="上下文ID")
    clear_context: bool = Field(False, description="是否清空上下文")


class TextAnalysisRequest(BaseModel):
    """文本分析请求"""
    text: str = Field(..., min_length=10, max_length=50000, description="待分析的文本")
    model_preference: str = Field("deepseek-v3-1-terminus", description="模型偏好")
    context_id: Optional[str] = Field(None, description="上下文ID")


class CharacterAnalysisRequest(BaseModel):
    """角色分析请求"""
    text: str = Field(..., min_length=10, max_length=50000, description="待分析的文本")
    model_preference: str = Field("deepseek-v3-1-terminus", description="模型偏好")
    context_id: Optional[str] = Field(None, description="上下文ID")


class ScriptGenerationRequest(BaseModel):
    """脚本生成请求"""
    text_analysis: Dict[str, Any] = Field(..., description="文本分析结果")
    style_requirements: Optional[str] = Field(None, description="风格要求")
    model_preference: str = Field("deepseek-v3-1-terminus", description="模型偏好")
    context_id: Optional[str] = Field(None, description="上下文ID")


# API端点
@router.post("/create")
async def create_conversation_context(
    request: CreateContextRequest,
    ai_service: AIService = Depends(get_ai_service)
):
    """
    创建新的对话上下文
    Create new conversation context
    """
    try:
        context_id = ai_service.create_conversation_context(
            max_messages=request.max_messages,
            max_tokens=request.max_tokens
        )

        return {
            "success": True,
            "context_id": context_id,
            "max_messages": request.max_messages,
            "max_tokens": request.max_tokens
        }

    except Exception as e:
        logger.error(f"创建对话上下文失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建上下文失败: {str(e)}")


@router.get("/list")
async def list_conversation_contexts(ai_service: AIService = Depends(get_ai_service)):
    """
    列出所有对话上下文
    List all conversation contexts
    """
    try:
        contexts = ai_service.list_conversation_contexts()

        return {
            "success": True,
            "contexts": contexts,
            "total_count": len(contexts)
        }

    except Exception as e:
        logger.error(f"列出对话上下文失败: {e}")
        raise HTTPException(status_code=500, detail=f"列出上下文失败: {str(e)}")


@router.get("/{context_id}")
async def get_conversation_context(
    context_id: str,
    ai_service: AIService = Depends(get_ai_service)
):
    """
    获取对话上下文信息
    Get conversation context info
    """
    try:
        context_info = ai_service.get_conversation_context(context_id)

        if not context_info:
            raise HTTPException(status_code=404, detail="上下文不存在")

        return {
            "success": True,
            "context_info": context_info
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取对话上下文失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取上下文失败: {str(e)}")


@router.delete("/{context_id}")
async def delete_conversation_context(
    context_id: str,
    ai_service: AIService = Depends(get_ai_service)
):
    """
    删除对话上下文
    Delete conversation context
    """
    try:
        success = ai_service.delete_conversation_context(context_id)

        if not success:
            raise HTTPException(status_code=404, detail="上下文不存在")

        return {
            "success": True,
            "message": f"上下文 {context_id} 已删除"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除对话上下文失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除上下文失败: {str(e)}")


@router.post("/{context_id}/clear")
async def clear_conversation_context(
    context_id: str,
    ai_service: AIService = Depends(get_ai_service)
):
    """
    清空对话上下文（保留系统消息）
    Clear conversation context (keep system messages)
    """
    try:
        success = ai_service.clear_conversation_context(context_id)

        if not success:
            raise HTTPException(status_code=404, detail="上下文不存在")

        return {
            "success": True,
            "message": f"上下文 {context_id} 已清空"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"清空对话上下文失败: {e}")
        raise HTTPException(status_code=500, detail=f"清空上下文失败: {str(e)}")


@router.post("/generate-text")
async def generate_text(
    request: GenerateTextRequest,
    ai_service: AIService = Depends(get_ai_service)
):
    """
    生成文本（支持JSON Schema）
    Generate text (supports JSON Schema)
    """
    try:
        result = await ai_service.generate_text(
            prompt=request.prompt,
            model_preference=request.model_preference,
            temperature=request.temperature,
            context_id=request.context_id,
            use_json_schema=request.use_json_schema,
            schema_type=request.schema_type
        )

        return {
            "success": True,
            "result": result,
            "parameters": {
                "model_preference": request.model_preference,
                "temperature": request.temperature,
                "use_json_schema": request.use_json_schema,
                "schema_type": request.schema_type,
                "context_id": request.context_id
            }
        }

    except Exception as e:
        logger.error(f"文本生成失败: {e}")
        raise HTTPException(status_code=500, detail=f"文本生成失败: {str(e)}")


@router.post("/generate-with-context")
async def generate_text_with_context(
    request: GenerateTextWithContextRequest,
    ai_service: AIService = Depends(get_ai_service)
):
    """
    带上下文的文本生成
    Generate text with context
    """
    try:
        result = await ai_service.generate_text_with_context(
            prompt=request.prompt,
            system_prompt=request.system_prompt,
            model_preference=request.model_preference,
            temperature=request.temperature,
            context_id=request.context_id,
            clear_context=request.clear_context
        )

        return {
            "success": True,
            "result": result["result"],
            "context_id": result["context_id"],
            "context_info": result["context_info"],
            "parameters": {
                "model_preference": request.model_preference,
                "temperature": request.temperature,
                "clear_context": request.clear_context
            }
        }

    except Exception as e:
        logger.error(f"带上下文文本生成失败: {e}")
        raise HTTPException(status_code=500, detail=f"文本生成失败: {str(e)}")


@router.post("/analyze-text")
async def analyze_text(
    request: TextAnalysisRequest,
    ai_service: AIService = Depends(get_ai_service)
):
    """
    文本分析（使用JSON Schema）
    Analyze text (using JSON Schema)
    """
    try:
        result = await ai_service.generate_text_analysis(
            text=request.text,
            model_preference=request.model_preference,
            context_id=request.context_id
        )

        return {
            "success": True,
            "analysis_result": result,
            "text_length": len(request.text),
            "model_used": request.model_preference,
            "context_id": request.context_id
        }

    except Exception as e:
        logger.error(f"文本分析失败: {e}")
        raise HTTPException(status_code=500, detail=f"文本分析失败: {str(e)}")


@router.post("/analyze-characters")
async def analyze_characters(
    request: CharacterAnalysisRequest,
    ai_service: AIService = Depends(get_ai_service)
):
    """
    角色分析（使用JSON Schema）
    Analyze characters (using JSON Schema)
    """
    try:
        result = await ai_service.generate_character_analysis(
            text=request.text,
            model_preference=request.model_preference,
            context_id=request.context_id
        )

        return {
            "success": True,
            "character_analysis": result,
            "text_length": len(request.text),
            "model_used": request.model_preference,
            "context_id": request.context_id
        }

    except Exception as e:
        logger.error(f"角色分析失败: {e}")
        raise HTTPException(status_code=500, detail=f"角色分析失败: {str(e)}")


@router.post("/generate-script")
async def generate_script(
    request: ScriptGenerationRequest,
    ai_service: AIService = Depends(get_ai_service)
):
    """
    基于分析生成脚本（使用JSON Schema）
    Generate script based on analysis (using JSON Schema)
    """
    try:
        result = await ai_service.generate_script_with_analysis(
            text_analysis=request.text_analysis,
            style_requirements=request.style_requirements,
            model_preference=request.model_preference,
            context_id=request.context_id
        )

        return {
            "success": True,
            "script_result": result,
            "model_used": request.model_preference,
            "style_requirements": request.style_requirements,
            "context_id": request.context_id
        }

    except Exception as e:
        logger.error(f"脚本生成失败: {e}")
        raise HTTPException(status_code=500, detail=f"脚本生成失败: {str(e)}")


@router.get("/health")
async def context_management_health_check(ai_service: AIService = Depends(get_ai_service)):
    """
    检查上下文管理服务健康状态
    Check context management service health
    """
    try:
        # 检查AI服务可用性
        ai_available = ai_service.is_available()

        # 检查上下文管理功能
        context_count = len(ai_service.list_conversation_contexts())

        return {
            "service_status": "healthy" if ai_available else "degraded",
            "ai_service_available": ai_available,
            "active_contexts": context_count,
            "context_management": "operational"
        }

    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        return {
            "service_status": "error",
            "error": str(e)
        }