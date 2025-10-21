"""
图像编辑API路由
Image Editing API Routes

提供图生图、图像编辑等功能
Provides image-to-image generation and editing functionality
"""

from fastapi import APIRouter, HTTPException, File, UploadFile, Form, Depends
from fastapi.responses import FileResponse
from typing import Optional
import logging
import os
from datetime import datetime

from services.ai_service import AIService
from services.file_system import ProjectFileSystem
from utils.image_utils import (
    encode_file_to_base64,
    get_image_info,
    validate_image_file,
    ImageProcessor
)

logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(prefix="/image-edit", tags=["image-edit"])

# 依赖注入
def get_ai_service():
    return AIService()

def get_file_system():
    return ProjectFileSystem()

def get_image_processor():
    return ImageProcessor()


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
        temp_dir = "temp/uploads"
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
        process_result = await image_processor.process_uploadedImage(base64_data)

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
    model_preference: str = Form("qwen"),
    size: str = Form("1024x1024"),
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
        result_url = await ai_service.edit_image_with_base64(
            prompt=prompt,
            base64_image=base64_image,
            base64_mask=base64_mask,
            model_preference=model_preference,
            size=size
        )

        # 下载结果到本地
        local_path = await ai_service.download_image_result(result_url)

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
    model_preference: str = Form("qwen"),
    size: str = Form("1024x1024"),
    ai_service: AIService = Depends(get_ai_service)
):
    """
    上传图像文件进行编辑
    Upload image file for editing
    """
    try:
        # 验证主图像文件
        if not file.content_type or not file.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="请上传图片文件")

        # 保存临时文件
        temp_dir = "temp/uploads"
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
        result_url = await ai_service.edit_image_with_base64(
            prompt=prompt,
            base64_image=base64_image,
            base64_mask=base64_mask,
            model_preference=model_preference,
            size=size
        )

        # 下载结果到本地
        local_path = await ai_service.download_image_result(result_url)

        # 清理临时文件
        os.remove(temp_path)

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


@router.post("/project/{project_id}/edit-character")
async def edit_character_image(
    project_id: str,
    character_name: str = Form(...),
    prompt: str = Form(...),
    file: UploadFile = File(...),
    ai_service: AIService = Depends(get_ai_service),
    fs: ProjectFileSystem = Depends(get_file_system)
):
    """
    为项目中的角色进行图像编辑
    Edit character image in project
    """
    try:
        # 查找项目路径
        projects = fs.list_projects()
        project_path = None
        for project in projects:
            if project.get("project_id") == project_id:
                project_path = project.get("project_path")
                break

        if not project_path:
            raise HTTPException(status_code=404, detail="项目不存在")

        # 验证文件
        if not file.content_type or not file.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="请上传图片文件")

        # 保存临时文件并转换为base64
        temp_dir = "temp/uploads"
        os.makedirs(temp_dir, exist_ok=True)
        temp_path = os.path.join(temp_dir, file.filename)

        with open(temp_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)

        base64_image = encode_file_to_base64(temp_path)

        # 调用AI服务进行图像编辑
        result_url = await ai_service.edit_image_with_base64(
            prompt=f"保持角色{character_name}的特征，{prompt}",
            base64_image=base64_image,
            model_preference="qwen",
            size="1024x1024"
        )

        # 下载结果到项目目录
        character_dir = fs.projects_dir / project_path / "characters" / character_name
        character_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        result_filename = f"edited_{timestamp}.png"
        result_path = character_dir / result_filename

        # 下载并保存结果
        await ai_service.download_image_result(result_url, str(character_dir))

        # 更新角色信息
        characters_file = fs.projects_dir / project_path / "characters" / "characters.json"
        if characters_file.exists():
            characters = fs._load_json(characters_file)
            for character in characters:
                if character.get("name") == character_name:
                    if "reference_images" not in character:
                        character["reference_images"] = []
                    character["reference_images"].append(str(result_path))
                    break

            fs._save_json(characters_file, characters)

        # 清理临时文件
        os.remove(temp_path)

        return {
            "success": True,
            "result_url": result_url,
            "result_filename": result_filename,
            "character_name": character_name,
            "project_id": project_id
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"角色图像编辑失败: {e}")
        raise HTTPException(status_code=500, detail=f"角色图像编辑失败: {str(e)}")


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
            if any(keyword in model_name.lower() for keyword in ['qwen', 'image', 'edit']):
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