"""
图像编辑API路由
Image Editing API Routes

提供图生图、图像编辑等功能
Provides image-to-image generation and editing functionality
"""

from fastapi import APIRouter, HTTPException, File, UploadFile, Form, Depends, Request
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
import httpx
import io
from typing import Optional
import logging
import os
from datetime import datetime, timedelta
import asyncio
from pathlib import Path

from services.ai_service import AIService
from services.file_system import ProjectFileSystem
from config import settings
from utils.image_utils import (
    encode_file_to_base64,
    encode_file,
    get_image_info,
    validate_image_file,
    download_to_temp_images,
    ImageProcessor
)

logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(prefix="/api/image-edit", tags=["image-edit"])

# 依赖注入
def get_ai_service():
    return AIService()

def get_file_system():
    return ProjectFileSystem()

def get_image_processor():
    return ImageProcessor()


def cleanup_temp_files():
    """
    清理过期的临时文件
    清理超过1小时的编辑结果文件
    """
    try:
        temp_dirs = [
            settings.TEMP_DOWNLOADS_DIR,
            settings.TEMP_UPLOADS_DIR,
            settings.TEMP_PROCESSING_DIR
        ]

        cutoff_time = datetime.now() - timedelta(hours=1)
        cleaned_count = 0

        for temp_dir in temp_dirs:
            if temp_dir.exists():
                for file_path in temp_dir.iterdir():
                    if file_path.is_file():
                        # 检查文件修改时间
                        file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                        if file_mtime < cutoff_time:
                            try:
                                file_path.unlink()
                                cleaned_count += 1
                                logger.debug(f"清理临时文件: {file_path}")
                            except Exception as e:
                                logger.warning(f"清理文件失败 {file_path}: {e}")

        if cleaned_count > 0:
            logger.info(f"清理了 {cleaned_count} 个过期临时文件")

    except Exception as e:
        logger.error(f"清理临时文件失败: {e}")


async def periodic_cleanup():
    """
    定期清理临时文件的后台任务
    每30分钟执行一次
    """
    while True:
        try:
            cleanup_temp_files()
            await asyncio.sleep(1800)  # 30分钟
        except Exception as e:
            logger.error(f"定期清理任务失败: {e}")
            await asyncio.sleep(300)  # 发生错误时5分钟后重试




@router.post("/upload-base64")
async def upload_image_base64(
    file: UploadFile = File(...),
    ai_service: AIService = Depends(get_ai_service),
    image_processor: ImageProcessor = Depends(get_image_processor)
):
    """
    上传图像并转换为base64格式
    Upload image and convert to base64 format
    """
    try:
        # 验证文件类型
        if not file.content_type or not file.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="请上传图片文件")

        # 保存临时文件
        temp_dir = str(settings.TEMP_DIR / "uploads")
        os.makedirs(temp_dir, exist_ok=True)
        temp_path = os.path.join(temp_dir, file.filename)

        with open(temp_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)

        # 验证图像文件
        is_valid, error_msg = validate_image_file(temp_path)
        if not is_valid:
            os.remove(temp_path)
            raise HTTPException(status_code=400, detail=error_msg)

        # 转换为base64
        base64_data = encode_file_to_base64(temp_path)

        # 获取图像信息
        image_info = get_image_info(base64_data)

        # 处理上传的图像
        try:
            process_result = await image_processor.process_uploadedImage(base64_data)
        except Exception as process_error:
            logger.warning(f"图像处理失败，返回基本信息: {process_error}")
            process_result = {
                "success": False,
                "error": str(process_error)
            }

        # 清理临时文件
        os.remove(temp_path)

        return {
            "success": True,
            "base64_data": base64_data,
            "image_info": image_info,
            "process_result": process_result
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"图像base64转换失败: {e}")
        raise HTTPException(status_code=500, detail=f"图像处理失败: {str(e)}")


@router.post("/edit-with-base64")
async def edit_image_with_base64(
    prompt: str = Form(...),
    base64_image: str = Form(...),
    base64_mask: Optional[str] = Form(None),
    model_preference: str = Form("doubao-seedream-4-0-250828"),
    size: str = Form("1024x1024"),
    stream: bool = Form(True, description="是否启用流式输出"),
    ai_service: AIService = Depends(get_ai_service)
):
    """
    使用base64图像进行编辑
    Edit image using base64 format
    """
    try:
        # 验证输入参数
        if not base64_image.startswith("data:"):
            raise HTTPException(status_code=400, detail="无效的base64图像格式")

        if base64_mask and not base64_mask.startswith("data:"):
            raise HTTPException(status_code=400, detail="无效的base64掩码格式")

        # 调用AI服务进行图像编辑
        try:
            result_url = await ai_service.edit_image_with_base64(
                prompt=prompt,
                base64_image=base64_image,
                base64_mask=base64_mask,
                model_preference=model_preference,
                size=size
            )

            if not result_url or result_url.startswith("placeholder://"):
                # AI服务返回占位符，说明处理失败
                error_msg = "图像编辑服务暂时不可用，请稍后重试"
                logger.error(f"AI编辑失败，返回占位符: {result_url}")
                raise HTTPException(status_code=503, detail=error_msg)

        except Exception as ai_error:
            logger.error(f"AI图像编辑失败: {ai_error}")
            error_msg = "图像编辑失败，可能是网络问题或服务暂时不可用"
            raise HTTPException(status_code=503, detail=error_msg)

        # 下载结果到本地
        try:
            local_path = await ai_service.download_image_result(result_url)
        except Exception as download_error:
            logger.error(f"下载编辑结果失败: {download_error}")
            # 即使下载失败，也返回URL让前端直接访问
            local_path = None

        return {
            "success": True,
            "result_url": result_url,
            "local_path": local_path,
            "edit_params": {
                "prompt": prompt,
                "model_preference": model_preference,
                "size": size
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"图像编辑失败: {e}")
        raise HTTPException(status_code=500, detail=f"图像编辑失败: {str(e)}")


@router.post("/edit-upload")
async def edit_uploaded_image(
    prompt: str = Form(...),
    file: UploadFile = File(...),
    mask_file: Optional[UploadFile] = File(None),
    model_preference: str = Form("doubao-seedream-4-0-250828"),
    size: str = Form("1024x1024"),
    stream: bool = Form(True, description="是否启用流式输出"),
    ai_service: AIService = Depends(get_ai_service)
):
    """
    上传图像文件进行编辑
    Upload image file for editing
    """
    try:
        # 详细记录请求参数
        logger.info(f"=== 图像编辑请求参数 ===")
        logger.info(f"prompt: '{prompt}' (长度: {len(prompt) if prompt else 0})")
        logger.info(f"file: {file.filename if file else None} (size: {file.size if file and hasattr(file, 'size') else 'unknown'} bytes)")
        logger.info(f"file.content_type: {file.content_type if file else None}")
        logger.info(f"mask_file: {mask_file.filename if mask_file else None}")
        logger.info(f"model_preference: {model_preference}")
        logger.info(f"size: {size}")
        logger.info(f"stream: {stream}")

        # 基本参数验证
        if not prompt or not prompt.strip():
            logger.error("prompt参数为空或无效")
            raise HTTPException(status_code=422, detail="编辑提示不能为空")

        if len(prompt.strip()) < 3:
            logger.error(f"prompt参数太短: {len(prompt.strip())}")
            raise HTTPException(status_code=422, detail="编辑提示太短，请输入至少3个字符")

        if not file:
            logger.error("file参数为空")
            raise HTTPException(status_code=422, detail="请选择要编辑的图片文件")

        if not file.filename:
            logger.error("文件名为空")
            raise HTTPException(status_code=422, detail="文件名无效，请选择有效的图片文件")

        logger.info(f"参数验证通过，开始处理图像编辑")
        # 验证主图像文件
        if not file.content_type or not file.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="请上传图片文件")

        # 保存临时文件
        temp_dir = str(settings.TEMP_DIR / "uploads")
        os.makedirs(temp_dir, exist_ok=True)

        # 处理主图像
        temp_path = os.path.join(temp_dir, file.filename)
        with open(temp_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)

        # 验证图像文件
        is_valid, error_msg = validate_image_file(temp_path)
        if not is_valid:
            os.remove(temp_path)
            raise HTTPException(status_code=400, detail=error_msg)

        # 转换为base64
        base64_image = encode_file_to_base64(temp_path)

        # 处理掩码文件（如果有）
        base64_mask = None
        if mask_file:
            if not mask_file.content_type or not mask_file.content_type.startswith('image/'):
                os.remove(temp_path)
                raise HTTPException(status_code=400, detail="掩码文件必须是图片格式")

            mask_path = os.path.join(temp_dir, f"mask_{mask_file.filename}")
            with open(mask_path, "wb") as buffer:
                content = await mask_file.read()
                buffer.write(content)

            base64_mask = encode_file_to_base64(mask_path)
            os.remove(mask_path)

        # 调用AI服务进行图像编辑
        try:
            result_url = await ai_service.edit_image_with_base64(
                prompt=prompt,
                base64_image=base64_image,
                base64_mask=base64_mask,
                model_preference=model_preference,
                size=size
            )

            if not result_url or result_url.startswith("placeholder://"):
                # AI服务返回占位符，说明处理失败
                error_msg = "图像编辑服务暂时不可用，请稍后重试"
                logger.error(f"AI编辑失败，返回占位符: {result_url}")
                raise HTTPException(status_code=503, detail=error_msg)

        except Exception as ai_error:
            logger.error(f"AI图像编辑失败: {ai_error}")
            error_msg = "图像编辑失败，可能是网络问题或服务暂时不可用"
            raise HTTPException(status_code=503, detail=error_msg)

        # 下载结果到本地
        try:
            local_path = await ai_service.download_image_result(result_url)
        except Exception as download_error:
            logger.error(f"下载编辑结果失败: {download_error}")
            # 即使下载失败，也返回URL让前端直接访问
            local_path = None

        # 清理临时文件
        try:
            os.remove(temp_path)
        except Exception as cleanup_error:
            logger.warning(f"清理临时文件失败: {cleanup_error}")

        return {
            "success": True,
            "result_url": result_url,
            "local_path": local_path,
            "original_filename": file.filename,
            "edit_params": {
                "prompt": prompt,
                "model_preference": model_preference,
                "size": size,
                "has_mask": mask_file is not None
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"上传图像编辑失败: {e}")
        raise HTTPException(status_code=500, detail=f"图像编辑失败: {str(e)}")


@router.get("/download/{filename}")
async def download_generated_image(filename: str):
    """
    下载生成的图像
    Download generated image
    """
    try:
        file_path = os.path.join("temp/images", filename)

        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="文件不存在")

        return FileResponse(
            path=file_path,
            filename=filename,
            media_type='image/png'
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"图像下载失败: {e}")
        raise HTTPException(status_code=500, detail=f"下载失败: {str(e)}")


@router.get("/models")
async def get_available_models(ai_service: AIService = Depends(get_ai_service)):
    """
    获取可用的图像编辑模型
    Get available image editing models
    """
    try:
        models = ai_service.get_available_models()

        # 过滤支持图像编辑的模型
        editing_models = []
        for model in models:
            if any(keyword in model.lower() for keyword in ['qwen', 'image', 'edit']):
                editing_models.append(model)

        return {
            "available_models": editing_models,
            "total_count": len(editing_models)
        }

    except Exception as e:
        logger.error(f"获取模型列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取模型列表失败: {str(e)}")


@router.post("/encode-local")
async def encode_local_image(file_path: str):
    """
    将本地图像文件编码为base64格式
    Encode local image file to base64 format
    """
    try:
        # 检查文件是否存在
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail=f"文件不存在: {file_path}")

        # 验证图像文件
        is_valid, error_msg = validate_image_file(file_path)
        if not is_valid:
            raise HTTPException(status_code=400, detail=error_msg)

        # 编码为base64
        base64_data = encode_file(file_path)

        # 获取图像信息
        image_info = get_image_info(base64_data)

        return {
            "success": True,
            "file_path": file_path,
            "base64_data": base64_data,
            "image_info": image_info
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"本地图像编码失败: {e}")
        raise HTTPException(status_code=500, detail=f"编码失败: {str(e)}")


@router.post("/download-to-local")
async def download_image_to_local(
    image_url: str = Form(...),
    filename: Optional[str] = Form(None)
):
    """
    下载图像到本地temp/images目录
    Download image to local temp/images directory
    """
    try:
        # 下载图像
        local_path = await download_to_temp_images(image_url, filename)

        # 获取文件信息
        file_size = os.path.getsize(local_path)
        relative_path = os.path.relpath(local_path, start="backend")

        return {
            "success": True,
            "image_url": image_url,
            "local_path": local_path,
            "relative_path": relative_path,
            "file_size": file_size,
            "download_time": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"图像下载失败: {e}")
        raise HTTPException(status_code=500, detail=f"下载失败: {str(e)}")


@router.post("/image-to-image")
async def image_to_image_generation(
    prompt: str = Form(...),
    file: UploadFile = File(...),
    model_preference: str = Form("doubao-seedream-4-0-250828"),
    size: str = Form("1024x1024"),
    stream: bool = Form(True, description="是否启用流式输出"),
    ai_service: AIService = Depends(get_ai_service)
):
    """
    图生图功能 - 上传参考图生成新图像
    Image-to-Image generation - Upload reference image to generate new image
    """
    try:
        logger.info(f"图生图请求开始: prompt={prompt}, file={file.filename}, model={model_preference}, size={size}")

        # 简化文件验证逻辑
        if not file:
            logger.error("未提供文件")
            raise HTTPException(status_code=422, detail="请选择要上传的图片文件")

        if not file.filename:
            logger.error("文件名为空")
            raise HTTPException(status_code=422, detail="文件名无效，请选择有效的图片文件")

        # 验证prompt
        if not prompt or not prompt.strip():
            logger.error("prompt为空")
            raise HTTPException(status_code=422, detail="请输入图片生成提示词")

        if len(prompt.strip()) < 3:
            logger.error(f"prompt太短: {len(prompt.strip())}")
            raise HTTPException(status_code=422, detail="提示词太短，请输入至少3个字符的描述")

        logger.info(f"验证通过: 文件={file.filename}, prompt长度={len(prompt.strip())}")

        # 保存临时文件
        temp_dir = str(settings.TEMP_DIR / "uploads")
        os.makedirs(temp_dir, exist_ok=True)

        # 生成安全的临时文件名
        timestamp = int(datetime.now().timestamp())
        safe_filename = f"img2img_{timestamp}_{file.filename}"
        temp_path = os.path.join(temp_dir, safe_filename)

        logger.info(f"保存临时文件: {temp_path}")

        try:
            content = await file.read()

            # 详细的文件信息日志
            logger.info(f"文件信息: filename={file.filename}, content_type={file.content_type}, size={len(content)} bytes")

            # 验证文件大小 - 更合理的限制
            if len(content) < 50:
                logger.error(f"文件太小: {len(content)} 字节")
                raise HTTPException(status_code=422, detail="图片文件太小或损坏，请选择其他图片")

            if len(content) > 20 * 1024 * 1024:  # 放宽到20MB限制
                logger.error(f"文件太大: {len(content)} 字节")
                raise HTTPException(status_code=422, detail="图片文件太大，请选择小于20MB的图片")

            with open(temp_path, "wb") as buffer:
                buffer.write(content)

        except Exception as write_error:
            logger.error(f"保存文件失败: {write_error}")
            raise HTTPException(status_code=500, detail="文件保存失败，请重试")

        # 验证图像文件 - 更宽松的验证
        try:
            is_valid, error_msg = validate_image_file(temp_path)
            logger.info(f"图像验证结果: {is_valid}, 错误信息: {error_msg}")
            if not is_valid:
                logger.warning(f"图像验证失败但继续处理: {error_msg}")
                # 不再直接抛出错误，而是记录警告并继续
        except Exception as validate_error:
            logger.warning(f"图像验证过程出错，但继续处理: {validate_error}")
            # 验证出错不阻断流程

        # 转换为base64
        base64_image = encode_file_to_base64(temp_path)

        # 调用AI服务进行图生图
        try:
            result_url = await ai_service.image_to_image_with_base64(
                prompt=prompt,
                base64_image=base64_image,
                model_preference=model_preference,
                size=size
            )

            if not result_url or result_url.startswith("placeholder://"):
                # AI服务返回占位符，说明处理失败
                error_msg = "图像生成服务暂时不可用，请稍后重试"
                logger.error(f"AI图生图失败，返回占位符: {result_url}")
                raise HTTPException(status_code=503, detail=error_msg)

        except Exception as ai_error:
            logger.error(f"AI图生图失败: {ai_error}")
            error_msg = "图像生成失败，可能是网络问题或服务暂时不可用"
            raise HTTPException(status_code=503, detail=error_msg)

        # 下载结果到本地
        try:
            local_path = await ai_service.download_image_result(result_url)
        except Exception as download_error:
            logger.error(f"下载生成结果失败: {download_error}")
            # 即使下载失败，也返回URL让前端直接访问
            local_path = None

        # 清理临时文件
        try:
            os.remove(temp_path)
        except Exception as cleanup_error:
            logger.warning(f"清理临时文件失败: {cleanup_error}")

        return {
            "success": True,
            "result_url": result_url,
            "local_path": local_path,
            "original_filename": file.filename,
            "generation_params": {
                "prompt": prompt,
                "model_preference": model_preference,
                "size": size
            }
        }

    except HTTPException as http_exc:
        # 如果是HTTPException，添加详细日志后重新抛出
        logger.error(f"HTTP异常: status_code={http_exc.status_code}, detail={http_exc.detail}")
        raise http_exc
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"图生图失败: {e}")
        logger.error(f"详细错误信息: {error_details}")

        # 尝试从错误信息中提取具体的422错误原因
        error_str = str(e).lower()

        if "422" in error_str or "validation" in error_str or "unprocessable entity" in error_str:
            logger.error("422错误 - 请求参数验证失败")
            # 提供更友好的错误信息
            if "form" in error_str.lower() or "field" in error_str.lower():
                raise HTTPException(status_code=422, detail="表单参数格式错误，请检查上传的文件和输入参数")
            else:
                raise HTTPException(status_code=422, detail=f"请求参数验证失败: {str(e)}")
        elif "network" in error_str or "connection" in error_str:
            logger.error("网络连接错误")
            raise HTTPException(status_code=503, detail="网络连接失败，请检查网络后重试")
        elif "timeout" in error_str:
            logger.error("请求超时")
            raise HTTPException(status_code=504, detail="请求超时，请稍后重试")
        elif "size" in error_str or "pixel" in error_str:
            logger.error("图片尺寸相关错误")
            raise HTTPException(status_code=422, detail=f"图片尺寸不符合要求: {str(e)}")
        elif "format" in error_str or "corrupt" in error_str:
            logger.error("图片格式错误")
            raise HTTPException(status_code=422, detail=f"图片格式错误或文件损坏: {str(e)}")
        else:
            logger.error("未知错误")
            raise HTTPException(status_code=500, detail=f"图生图失败: {str(e)}")
    finally:
        # 确保清理临时文件
        try:
            if 'temp_path' in locals() and os.path.exists(temp_path):
                os.remove(temp_path)
                logger.info(f"已清理临时文件: {temp_path}")
        except Exception as cleanup_error:
            logger.warning(f"清理临时文件失败: {cleanup_error}")


@router.get("/temp-files")
async def list_temp_files():
    """
    列出temp/images目录中的文件
    List files in temp/images directory
    """
    try:
        temp_dir = str(settings.TEMP_UPLOADS_DIR)
        if not os.path.exists(temp_dir):
            return {"success": True, "files": [], "total_count": 0}

        files = []
        for filename in os.listdir(temp_dir):
            file_path = os.path.join(temp_dir, filename)
            if os.path.isfile(file_path):
                stat = os.stat(file_path)
                files.append({
                    "filename": filename,
                    "size": stat.st_size,
                    "modified_time": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "download_url": f"/image-edit/download/{filename}"
                })

        files.sort(key=lambda x: x["modified_time"], reverse=True)

        return {
            "success": True,
            "files": files,
            "total_count": len(files)
        }

    except Exception as e:
        logger.error(f"列出临时文件失败: {e}")
        raise HTTPException(status_code=500, detail=f"列出文件失败: {str(e)}")


@router.delete("/temp-files/{filename}")
async def delete_temp_file(filename: str):
    """
    删除temp/images目录中的指定文件
    Delete specific file in temp/images directory
    """
    try:
        file_path = str(settings.TEMP_UPLOADS_DIR / filename)

        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="文件不存在")

        os.remove(file_path)

        return {
            "success": True,
            "message": f"文件 {filename} 已删除"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除文件失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除文件失败: {str(e)}")


@router.post("/debug-form-data")
async def debug_form_data(
    prompt: str = Form(""),
    file: UploadFile = File(None),
    model_preference: str = Form("doubao-seedream-4-0-250828"),
    size: str = Form("1024x1024"),
    strength: str = Form("0.8"),
    stream: str = Form("true")
):
    """
    调试端点 - 用于测试FormData参数解析
    Debug endpoint - For testing FormData parameter parsing
    """
    try:
        # 记录所有接收到的参数
        logger.info("=== 调试端点接收到的参数 ===")
        logger.info(f"prompt: '{prompt}' (类型: {type(prompt)}, 长度: {len(prompt) if prompt else 0})")
        logger.info(f"file: {file.filename if file else None} (类型: {type(file)})")
        logger.info(f"model_preference: '{model_preference}' (类型: {type(model_preference)})")
        logger.info(f"size: '{size}' (类型: {type(size)})")
        logger.info(f"strength: '{strength}' (类型: {type(strength)})")
        logger.info(f"stream: '{stream}' (类型: {type(stream)})")

        # 测试strength参数转换
        strength_float = None
        try:
            strength_float = float(strength)
            logger.info(f"strength转换成功: {strength_float}")
        except ValueError as e:
            logger.error(f"strength转换失败: {e}")
            strength_float = "转换失败"

        # 测试stream参数转换
        stream_bool = None
        try:
            stream_bool = stream.lower() in ('true', '1', 'yes')
            logger.info(f"stream转换成功: {stream_bool}")
        except Exception as e:
            logger.error(f"stream转换失败: {e}")
            stream_bool = "转换失败"

        # 返回详细的参数信息
        return {
            "success": True,
            "received_params": {
                "prompt": {
                    "value": prompt,
                    "type": str(type(prompt)),
                    "length": len(prompt) if prompt else 0,
                    "is_valid": bool(prompt and len(prompt.strip()) >= 3)
                },
                "file": {
                    "filename": file.filename if file else None,
                    "type": str(type(file)),
                    "content_type": file.content_type if file else None,
                    "is_valid": bool(file and file.filename)
                },
                "model_preference": {
                    "value": model_preference,
                    "type": str(type(model_preference)),
                    "is_valid": bool(model_preference)
                },
                "size": {
                    "value": size,
                    "type": str(type(size)),
                    "is_valid": bool(size)
                },
                "strength": {
                    "value": strength,
                    "type": str(type(strength)),
                    "converted_float": strength_float,
                    "is_valid": strength_float is not None and 0.0 <= float(strength) <= 1.0 if isinstance(strength_float, float) else False
                },
                "stream": {
                    "value": stream,
                    "type": str(type(stream)),
                    "converted_bool": stream_bool,
                    "is_valid": isinstance(stream_bool, bool)
                }
            },
            "validation_summary": {
                "all_params_valid": bool(
                    prompt and len(prompt.strip()) >= 3 and
                    file and file.filename and
                    model_preference and
                    size and
                    strength_float is not None and 0.0 <= strength_float <= 1.0
                )
            }
        }

    except Exception as e:
        logger.error(f"调试端点错误: {e}")
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"错误详情: {error_details}")

        return {
            "success": False,
            "error": str(e),
            "error_type": str(type(e)),
            "traceback": error_details
        }


@router.get("/health")
async def image_edit_health_check(ai_service: AIService = Depends(get_ai_service)):
    """
    检查图像编辑服务健康状态
    Check image editing service health
    """
    try:
        health_status = await ai_service.health_check()

        # 检查图像编辑相关的模型
        editing_health = {}
        for model_name, is_healthy in health_status.items():
            if any(keyword in model_name.lower() for keyword in ['qwen', 'image', 'edit', 'seedream']):
                editing_health[model_name] = is_healthy

        return {
            "service_status": "healthy" if any(editing_health.values()) else "unhealthy",
            "models": editing_health,
            "total_models": len(editing_health),
            "healthy_models": sum(editing_health.values())
        }

    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        return {
            "service_status": "error",
            "error": str(e)
        }


@router.get("/proxy-download")
async def proxy_download_image(image_url: str):
    """
    代理下载图片 - 解决CORS跨域问题
    Proxy download image - Solve CORS cross-origin issue
    """
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # 下载图片
            response = await client.get(image_url)
            response.raise_for_status()

            # 获取内容类型
            content_type = response.headers.get('content-type', 'image/jpeg')

            # 创建流式响应
            return StreamingResponse(
                io.BytesIO(response.content),
                media_type=content_type,
                headers={
                    "Content-Disposition": f"attachment; filename=edited-image-{int(datetime.now().timestamp())}.jpg"
                }
            )

    except httpx.HTTPStatusError as e:
        logger.error(f"代理下载图片失败 - HTTP错误: {e}")
        raise HTTPException(status_code=e.response.status_code, detail=f"下载失败: {str(e)}")
    except Exception as e:
        logger.error(f"代理下载图片失败: {e}")
        raise HTTPException(status_code=500, detail=f"下载失败: {str(e)}")