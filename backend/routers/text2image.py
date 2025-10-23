"""
文生图API路由
Text-to-Image API Routes

提供基本的文本生成图像功能
Provides basic text-to-image generation functionality
"""

from fastapi import APIRouter, HTTPException, Form, Depends
import logging

from ..services.ai_service import AIService
from ..models.text2image import Text2ImageResponse

logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(prefix="/text2image", tags=["text2image"])

# 依赖注入
def get_ai_service():
    return AIService()


@router.post("/generate", response_model=Text2ImageResponse)
async def generate_image_from_text(
    prompt: str = Form(..., description="图像描述文本"),
    model_preference: str = Form("seedream", description="首选模型"),
    size: str = Form("1024x1024", description="图像尺寸"),
    quality: str = Form("standard", description="图像质量"),
    style: str = Form("realistic", description="图像风格"),
    ai_service: AIService = Depends(get_ai_service)
):
    """
    根据文本描述生成图像
    Generate image from text description
    """
    try:
        # 验证输入参数
        if not prompt or len(prompt.strip()) < 10:
            raise HTTPException(status_code=400, detail="描述文本至少需要10个字符")

        if len(prompt) > 1000:
            raise HTTPException(status_code=400, detail="描述文本不能超过1000个字符")

        # 验证尺寸参数
        valid_sizes = ["512x512", "768x768", "1024x1024", "1536x1536"]
        if size not in valid_sizes:
            raise HTTPException(
                status_code=400,
                detail=f"支持的尺寸: {', '.join(valid_sizes)}"
            )

        # 验证质量参数
        valid_qualities = ["standard", "high"]
        if quality not in valid_qualities:
            raise HTTPException(
                status_code=400,
                detail=f"支持的质量: {', '.join(valid_qualities)}"
            )

        # 验证风格参数
        valid_styles = ["realistic", "cartoon", "manga", "fantasy", "abstract"]
        if style not in valid_styles:
            raise HTTPException(
                status_code=400,
                detail=f"支持的风格: {', '.join(valid_styles)}"
            )

        # 构建完整的提示词
        full_prompt = f"{prompt}, {style} style, high quality, detailed"

        logger.info(f"开始生成图像 - 模型: {model_preference}, 尺寸: {size}, 提示: {prompt[:100]}...")

        # 调用AI服务生成图像
        try:
            image_url = await ai_service.generate_image(
                prompt=full_prompt,
                model_preference=model_preference,
                size=size,
                quality=quality
            )

            # 下载图像到本地
            local_path = await ai_service.download_image_result(image_url)

            logger.info(f"图像生成成功 - URL: {image_url}, 本地路径: {local_path}")

            return Text2ImageResponse(
                success=True,
                image_url=image_url,
                local_path=local_path,
                prompt_used=full_prompt,
                model_used=model_preference,
                size=size,
                quality=quality,
                style=style
            )

        except Exception as e:
            logger.error(f"AI图像生成失败: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"图像生成失败: {str(e)}"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"文生图请求处理失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"请求处理失败: {str(e)}"
        )


@router.post("/generate-batch")
async def generate_images_batch(
    prompts: str = Form(..., description="多个图像描述，用分号分隔"),
    model_preference: str = Form("seedream", description="首选模型"),
    size: str = Form("1024x1024", description="图像尺寸"),
    quality: str = Form("standard", description="图像质量"),
    style: str = Form("realistic", description="图像风格"),
    ai_service: AIService = Depends(get_ai_service)
):
    """
    批量生成多张图像
    Generate multiple images in batch
    """
    try:
        # 解析多个提示词
        prompt_list = [p.strip() for p in prompts.split(';') if p.strip()]

        if len(prompt_list) == 0:
            raise HTTPException(status_code=400, detail="请提供至少一个有效的描述")

        if len(prompt_list) > 5:
            raise HTTPException(status_code=400, detail="批量生成最多支持5张图像")

        results = []

        for i, prompt in enumerate(prompt_list):
            logger.info(f"批量生成第 {i+1}/{len(prompt_list)} 张图像")

            try:
                # 生成单张图像
                full_prompt = f"{prompt}, {style} style, high quality, detailed"
                image_url = await ai_service.generate_image(
                    prompt=full_prompt,
                    model_preference=model_preference,
                    size=size,
                    quality=quality
                )

                # 下载到本地
                local_path = await ai_service.download_image_result(image_url)

                results.append({
                    "index": i + 1,
                    "prompt": prompt,
                    "image_url": image_url,
                    "local_path": local_path,
                    "success": True
                })

            except Exception as e:
                logger.error(f"批量生成第{i+1}张图像失败: {e}")
                results.append({
                    "index": i + 1,
                    "prompt": prompt,
                    "error": str(e),
                    "success": False
                })

        successful_count = sum(1 for r in results if r.get("success", False))

        return {
            "success": True,
            "total_requests": len(prompt_list),
            "successful_count": successful_count,
            "results": results,
            "model_used": model_preference,
            "size": size,
            "quality": quality,
            "style": style
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"批量图像生成失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"批量生成失败: {str(e)}"
        )


@router.get("/models")
async def get_text2image_models(ai_service: AIService = Depends(get_ai_service)):
    """
    获取可用的文生图模型
    Get available text-to-image models
    """
    try:
        available_models = ai_service.get_available_models()

        # 过滤支持图像生成的模型
        image_models = []
        for model in available_models:
            if any(keyword in model.lower() for keyword in ['seedream', 'dall', 'stable', 'midjourney']):
                image_models.append({
                    "name": model,
                    "type": "text2image",
                    "status": "available"
                })

        return {
            "available_models": image_models,
            "total_count": len(image_models),
            "recommended": "seedream"
        }

    except Exception as e:
        logger.error(f"获取模型列表失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"获取模型列表失败: {str(e)}"
        )


@router.get("/health")
async def text2image_health_check(ai_service: AIService = Depends(get_ai_service)):
    """
    检查文生图服务健康状态
    Check text-to-image service health
    """
    try:
        # 检查可用模型
        available_models = ai_service.get_available_models()
        image_models = [m for m in available_models if 'seedream' in m.lower() or 'image' in m.lower()]

        # 尝试简单的文生图测试
        test_status = "unknown"
        if image_models:
            try:
                # 使用简化的测试提示
                await ai_service.generate_image(
                    prompt="simple test",
                    model_preference="seedream",
                    size="512x512"
                )
                test_status = "healthy"
            except Exception as e:
                logger.warning(f"Health check image generation failed: {e}")
                test_status = "unhealthy"

        return {
            "service_status": "healthy" if image_models else "unavailable",
            "available_models": len(image_models),
            "model_names": image_models,
            "test_status": test_status
        }

    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        return {
            "service_status": "error",
            "error": str(e)
        }


@router.get("/styles")
async def get_supported_styles():
    """
    获取支持的图像风格
    Get supported image styles
    """
    styles = {
        "realistic": {
            "name": "写实风格",
            "description": "照片般真实的图像，注重细节和光影",
            "examples": ["人像摄影", "风景照片", "产品展示"]
        },
        "cartoon": {
            "name": "卡通风格",
            "description": "色彩鲜艳的卡通动画风格",
            "examples": ["卡通人物", "动画场景", "Q版形象"]
        },
        "manga": {
            "name": "漫画风格",
            "description": "日式漫画黑白或彩色风格",
            "examples": ["漫画角色", "漫画场景", "动漫风格"]
        },
        "fantasy": {
            "name": "奇幻风格",
            "description": "充满想象力的奇幻艺术风格",
            "examples": ["魔法场景", "神话生物", "奇幻世界"]
        },
        "abstract": {
            "name": "抽象风格",
            "description": "艺术化的抽象表现形式",
            "examples": ["抽象艺术", "概念图像", "艺术创作"]
        }
    }

    return {
        "supported_styles": styles,
        "total_count": len(styles),
        "default": "realistic"
    }


@router.post("/enhance-prompt")
async def enhance_prompt(
    original_prompt: str = Form(..., description="原始提示词"),
    target_style: str = Form("realistic", description="目标风格"),
    ai_service: AIService = Depends(get_ai_service)
):
    """
    增强提示词
    Enhance prompt for better image generation
    """
    try:
        # 使用文本生成模型来增强提示词
        enhancement_prompt = f"""
请将以下简单的图像描述转换为详细的、高质量的AI绘画提示词：

原始描述：{original_prompt}
目标风格：{target_style}

请添加：
1. 详细的视觉描述
2. 光照和色彩信息
3. 构图和视角建议
4. 质感和细节要求
5. 风格特征关键词

直接返回优化后的提示词，不要其他解释：
"""

        try:
            enhanced_prompt = await ai_service.generate_text(
                prompt=enhancement_prompt,
                model_preference="seedream",
                max_tokens=200,
                temperature=0.7
            )

            # 清理结果
            enhanced_prompt = enhanced_prompt.strip().strip('"\'')

            return {
                "success": True,
                "original_prompt": original_prompt,
                "enhanced_prompt": enhanced_prompt,
                "target_style": target_style
            }

        except Exception as e:
            logger.warning(f"AI提示词增强失败，使用基础增强: {e}")

            # 基础增强逻辑
            style_keywords = {
                "realistic": "photorealistic, highly detailed, professional photography, soft lighting",
                "cartoon": "vibrant colors, clean lines, cartoon style, animation art",
                "manga": "manga style, clean lineart, anime art, detailed",
                "fantasy": "fantasy art, magical, ethereal lighting, detailed",
                "abstract": "abstract art, creative, artistic, unique composition"
            }

            keywords = style_keywords.get(target_style, style_keywords["realistic"])
            enhanced = f"{original_prompt}, {keywords}, high quality, detailed"

            return {
                "success": True,
                "original_prompt": original_prompt,
                "enhanced_prompt": enhanced,
                "target_style": target_style,
                "enhancement_method": "basic"
            }

    except Exception as e:
        logger.error(f"提示词增强失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"提示词增强失败: {str(e)}"
        )