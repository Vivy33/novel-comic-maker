"""
角色管理API路由
Character Management API Routes
"""

from fastapi import APIRouter, HTTPException, Depends, File, UploadFile
from fastapi.responses import StreamingResponse
from typing import List
import logging
import json
import uuid
from datetime import datetime
from pathlib import Path

from services.file_system import ProjectFileSystem
from models.character import CharacterInfo, CharacterCreateRequest, CharacterListResponse
from models.file_system import ApiResponse

logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(prefix="/api/characters", tags=["characters"])

# 依赖注入
def get_file_system():
    return ProjectFileSystem()


@router.get("/{project_id}")
async def get_project_characters(
    project_id: str,
    fs: ProjectFileSystem = Depends(get_file_system)
):
    """
    获取项目的角色列表
    Get project characters list
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

        # 读取角色信息
        characters_file = Path(project_path) / "characters" / "characters.json"
        if not characters_file.exists():
            return {
                "data": {"characters": []},
                "message": "获取角色列表成功",
                "success": True
            }

        characters_data = fs._load_json(characters_file)
        character_list = []

        for character in characters_data:
            character_info = CharacterInfo(**character)
            # 确保角色有必需的字段，如果没有则补充
            if not character_info.id:
                character_info.id = str(uuid.uuid4())
            # 始终使用传入的正确项目ID，确保一致性
            character_info.project_id = project_id
            if not character_info.created_at:
                character_info.created_at = character.get("created_at", datetime.now().isoformat())
            if not character_info.updated_at:
                character_info.updated_at = character.get("updated_at", datetime.now().isoformat())

            character_list.append(character_info)
        return {
            "data": {"characters": [character.model_dump() for character in character_list]},
            "message": "获取角色列表成功",
            "success": True
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取角色列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取角色列表失败: {str(e)}")


@router.post("/{project_id}")
async def create_character(
    project_id: str,
    character: CharacterCreateRequest,
    fs: ProjectFileSystem = Depends(get_file_system)
):
    """
    创建新角色
    Create new character
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

        # 读取角色列表
        characters_dir = Path(project_path) / "characters"
        characters_file = characters_dir / "characters.json"

        if not characters_dir.exists():
            characters_dir.mkdir(parents=True, exist_ok=True)

        characters = []
        if characters_file.exists():
            characters = fs._load_json(characters_file)

        # 检查角色是否存在
        for existing in characters:
            if existing.get("name") == character.name:
                raise HTTPException(status_code=400, detail="角色已存在")

        # 创建角色
        character_id = str(uuid.uuid4())
        new_character = {
            "id": character_id,
            "project_id": project_id,
            "name": character.name,
            "description": character.description,
            "appearance": "基于特征生成的角色外观",
            "personality": "基于特征生成的角色性格",
            "traits": character.traits,
            "reference_images": character.reference_images,
            "created_at": datetime.now().isoformat()
        }
        characters.append(new_character)

        fs._save_json(characters_file, characters)

        return {
            "data": CharacterInfo(**new_character),
            "message": "角色创建成功",
            "success": True
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建角色失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建角色失败: {str(e)}")


@router.put("/{character_id}")
async def update_character(
    character_id: str,
    character_update: CharacterCreateRequest,
    fs: ProjectFileSystem = Depends(get_file_system)
):
    """
    更新角色信息
    Update character information
    """
    try:
        # 查找项目路径
        projects = fs.list_projects()
        project_path = None
        character_data = None
        character_index = -1

        for project in projects:
            project_id = project.get("project_id")
            if project_id:
                # 读取角色列表
                characters_file = Path(project.get("project_path")) / "characters" / "characters.json"
                if characters_file.exists():
                    characters_data = fs._load_json(characters_file)
                    for i, character in enumerate(characters_data):
                        if character.get("id") == character_id:
                            project_path = project.get("project_path")
                            character_data = character
                            character_index = i
                            break
                    if project_path:
                        break

        if not project_path or not character_data:
            raise HTTPException(status_code=404, detail="角色不存在")

        # 更新角色信息
        updated_character = {
            "id": character_id,
            "project_id": character_data.get("project_id"),
            "name": character_update.name,
            "description": character_update.description,
            "appearance": character_data.get("appearance", "基于特征生成的角色外观"),
            "personality": character_data.get("personality", "基于特征生成的角色性格"),
            "traits": character_update.traits,
            "reference_images": character_update.reference_images,
            "created_at": character_data.get("created_at"),
            "updated_at": datetime.now().isoformat()
        }

        # 保存更新后的角色信息
        characters_file = Path(project_path) / "characters" / "characters.json"
        characters_data = fs._load_json(characters_file)
        characters_data[character_index] = updated_character
        fs._save_json(characters_file, characters_data)

        return {
            "data": CharacterInfo(**updated_character),
            "message": "角色更新成功",
            "success": True
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新角色失败: {e}")
        raise HTTPException(status_code=500, detail=f"更新角色失败: {str(e)}")


@router.post("/{project_id}/{character_name}/reference-image")
async def upload_character_reference_image(
    project_id: str,
    character_name: str,
    file: UploadFile = File(...),
    fs: ProjectFileSystem = Depends(get_file_system)
):
    """
    上传角色参考图片
    Upload character reference image
    """
    try:
        # 验证文件类型
        if not file.content_type or not file.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="请上传图片文件")

        # 查找项目路径
        projects = fs.list_projects()
        project_path = None

        for project in projects:
            if project.get("project_id") == project_id:
                project_path = project.get("project_path")
                break

        if not project_path:
            raise HTTPException(status_code=404, detail="项目不存在")

        # 保存图片
        target_dir = Path(project_path) / "characters" / character_name
        target_dir.mkdir(parents=True, exist_ok=True)

        target_file = target_dir / file.filename
        with open(target_file, "wb") as buffer:
            content = await file.read()
            buffer.write(content)

        return {
            "success": True,
            "filename": file.filename,
            "path": str(target_file)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"上传参考图片失败: {e}")
        raise HTTPException(status_code=500, detail=f"上传参考图片失败: {str(e)}")


@router.get("/{project_id}/{character_name}/reference-images")
async def get_character_reference_images(
    project_id: str,
    character_name: str,
    fs: ProjectFileSystem = Depends(get_file_system)
):
    """
    获取角色参考图片列表
    Get character reference image list
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

        # 列出图片文件
        target_dir = Path(project_path) / "characters" / character_name
        if not target_dir.exists():
            return []

        images = []
        for img_file in sorted(target_dir.glob("*.png")):
            images.append({
                "filename": img_file.name,
                "path": str(img_file)
            })

        return images
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取参考图片列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取参考图片列表失败: {str(e)}")


@router.delete("/{project_id}/{character_name}/reference-image/{filename}")
async def delete_character_reference_image(
    project_id: str,
    character_name: str,
    filename: str,
    fs: ProjectFileSystem = Depends(get_file_system)
):
    """
    删除角色参考图片
    Delete character reference image
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

        # 删除图片
        target_dir = Path(project_path) / "characters" / character_name
        target_file = target_dir / filename

        if not target_file.exists():
            raise HTTPException(status_code=404, detail="文件不存在")

        target_file.unlink()

        from fastapi.responses import StreamingResponse

        return StreamingResponse(
            content=card_data,
            media_type="application/json",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "application/json"
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除参考图片失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除参考图片失败: {str(e)}")


@router.post("/{project_id}/{character_name}/generate-card")
async def generate_character_card(
    project_id: str,
    character_name: str,
    card_data: dict = None,
    fs: ProjectFileSystem = Depends(get_file_system)
):
    """
    生成角色卡
    Generate character card
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

        # 读取角色信息
        characters_file = Path(project_path) / "characters" / "characters.json"
        if not characters_file.exists():
            raise HTTPException(status_code=404, detail="角色不存在")

        characters_data = fs._load_json(characters_file)
        character_info = None
        for char in characters_data:
            if char.get("name") == character_name:
                character_info = char
                break

        if not character_info:
            raise HTTPException(status_code=404, detail="角色不存在")

        # 生成角色卡数据
        prompt = card_data.get("prompt", "") if card_data else ""
        negative_prompt = card_data.get("negative_prompt", "").strip() if card_data else ""
        stream = True  # 默认启用流式处理

        # 检查是否有参考图片（支持任意格式的图片，排除生成的角色卡）
        character_dir = Path(project_path) / "characters" / character_name
        reference_images = []
        if character_dir.exists():
            # 获取所有图片文件，排除生成的角色卡图片
            generated_images_dir = character_dir / "images"
            for img_file in character_dir.glob("*"):
                # 只支持AI API兼容的图片格式，且不在images目录下，就认为是参考图
                if img_file.is_file() and img_file.suffix.lower() in ['.png', '.jpg', '.jpeg']:
                    # 排除已经生成的角色卡图片
                    img_path_str = str(img_file)
                    if not (generated_images_dir.exists() and img_path_str.startswith(str(generated_images_dir))):
                        reference_images.append(img_path_str)

                        # 检查参考图文件大小
                        file_size = img_file.stat().st_size
                        logger.info(f"找到参考图片: {img_file.name} (大小: {file_size:,} bytes)")

                        # 如果参考图太小，给出警告
                        if file_size < 10240:  # 小于10KB
                            logger.warning(f"参考图片 {img_file.name} 可能过小，建议上传更大的图片以获得更好的效果")
                        logger.info(f"找到参考图片: {img_file.name}")

            # 如果没有找到参考图，提供帮助信息
            if not reference_images:
                logger.info("未找到参考图片，将使用纯文生图模式")
                print("💡 提示：用户可以在角色目录上传参考图片来改善生成效果")

            logger.info(f"总共找到 {len(reference_images)} 张参考图片")
            for ref_img in reference_images:
                logger.info(f"  - {ref_img}")

            # 如果有参考图，无需在prompt中添加描述，让模型自己分析
            if len(reference_images) > 0:
                logger.info("检测到参考图，将让doubao-seedream-4.0模型自动分析参考图特征")

        # 生成角色图片的prompt
        front_prompt = f"角色卡正面视图：{character_info.get('appearance', '')}，{character_info.get('personality', '')}"
        if prompt:
            front_prompt += f"，{prompt}"
        if len(reference_images) > 0:
            front_prompt += f"，参考上传的图片风格和外观"

        front_negative_prompt = "低质量，模糊，变形"
        if negative_prompt:
            front_negative_prompt = f"{negative_prompt}，{front_negative_prompt}"

        back_prompt = f"角色卡背面视图：{character_info.get('appearance', '')}的背影，展现出角色的神秘感和故事感"
        if prompt:
            back_prompt += f"，{prompt}"
        if len(reference_images) > 0:
            back_prompt += f"，保持与正面图片一致的风格"

        back_negative_prompt = "正面，面部可见，低质量，模糊"
        if negative_prompt:
            back_negative_prompt = f"{negative_prompt}，{back_negative_prompt}"

        # 生成图片文件名
        front_image_filename = f"{character_name}_front_{int(datetime.now().timestamp())}.png"
        back_image_filename = f"{character_name}_back_{int(datetime.now().timestamp())}.png"

        character_card = {
            "id": f"card_{character_name}_{int(datetime.now().timestamp())}",
            "character_id": character_name,
            "character_name": character_name,
            "front_view": {
                "appearance": character_info.get("appearance", ""),
                "personality": {
                    "positive": character_info.get("personality", ""),
                    "negative": negative_prompt if negative_prompt else "无特殊要求"
                },
                "background": f"{character_name}是这个故事的重要角色之一，拥有独特的能力和背景。",
                "skills": [character_info.get("personality", "").split("、")[0] if character_info.get("personality") else "未定义"],
                "stats": {
                    "strength": 75,
                    "intelligence": 85,
                    "charisma": 70,
                    "agility": 80
                },
                "image": {
                    "filename": front_image_filename,
                    "path": f"images/{front_image_filename}",
                    "prompt": front_prompt,
                    "negative_prompt": front_negative_prompt
                }
            },
            "back_view": {
                "backstory": f"{character_name}有着神秘的过去，这影响了他们性格的形成。{character_info.get('description', '')}",
                "relationships": [f"与故事中其他角色有着复杂的关系"],
                "secrets": [f"隐藏着不为人知的秘密"],
                "goals": [f"追求着重要的目标，推动故事发展"],
                "image": {
                    "filename": back_image_filename,
                    "path": f"images/{back_image_filename}",
                    "prompt": back_prompt,
                    "negative_prompt": back_negative_prompt
                }
            },
            "created_at": datetime.now().isoformat(),
            "status": "completed"
        }

        # 保存角色卡到项目目录
        character_dir = Path(project_path) / "characters" / character_name
        character_dir.mkdir(parents=True, exist_ok=True)

        # 创建图片目录
        images_dir = character_dir / "images"
        images_dir.mkdir(parents=True, exist_ok=True)

        # 生成角色图片
        from PIL import Image, ImageDraw, ImageFont
        import os

        # 为了确保正面和背面风格一致，使用相同的生成参数
        generation_params = {
            "model": "doubao-seedream-4-0-250828",
            "size": "1024x1024",
            "reference_images": reference_images,
            "negative_prompt": negative_prompt,
            "seed": hash(f"{character_name}_{datetime.now().isoformat()}") % 2147483647  # 固定种子确保一致性
        }

        # 创建正面图片
        front_image_path = images_dir / front_image_filename
        front_result = create_character_card_image(front_image_path, character_info, "front", front_prompt, generation_params)

        # 创建背面图片 - 基于正面图片转换，而不是重新生成
        back_image_path = images_dir / back_image_filename
        if front_result:
            back_result = create_back_view_from_front(back_image_path, front_image_path, back_prompt, generation_params)
        else:
            back_result = False

        # 检查生成结果
        if front_result is False or back_result is False:
            return {
                "success": False,
                "message": "角色卡生成失败：AI图片生成失败，请检查网络连接或稍后重试"
            }

        # 更新图片路径
        character_card["front_view"]["image"]["path"] = f"images/{front_image_filename}"
        character_card["back_view"]["image"]["path"] = f"images/{back_image_filename}"

        # 保存角色卡数据
        card_file = character_dir / "character_card.json"
        fs._save_json(card_file, character_card)

        # 记录历史
        fs.save_history(
            str(Path(project_path)),
            "character_card_generated",
            {
                "character_name": character_name,
                "card_id": character_card["id"],
                "prompt": prompt
            }
        )

        return {
            "success": True,
            "data": character_card
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"生成角色卡失败: {e}")
        raise HTTPException(status_code=500, detail=f"生成角色卡失败: {str(e)}")


@router.get("/{project_id}/{character_name}/card")
async def get_character_card(
    project_id: str,
    character_name: str,
    fs: ProjectFileSystem = Depends(get_file_system)
):
    """
    获取角色卡
    Get character card
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

        # 读取角色卡文件
        card_file = Path(project_path) / "characters" / character_name / "character_card.json"
        if not card_file.exists():
            return {
                "success": False,
                "message": "角色卡不存在，请先生成角色卡"
            }

        character_card = fs._load_json(card_file)
        return {
            "success": True,
            "data": character_card
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取角色卡失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取角色卡失败: {str(e)}")


@router.get("/{project_id}/{character_name}/card-image/{view_type}")
async def get_character_card_image(
    project_id: str,
    character_name: str,
    view_type: str,  # "front" or "back"
    fs: ProjectFileSystem = Depends(get_file_system)
):
    """
    获取角色卡图片
    Get character card image
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

        # 读取角色卡文件
        card_file = Path(project_path) / "characters" / character_name / "character_card.json"
        if not card_file.exists():
            raise HTTPException(status_code=404, detail="角色卡不存在")

        character_card = fs._load_json(card_file)

        # 获取图片路径
        if view_type == "front":
            image_info = character_card.get("front_view", {}).get("image", {})
        elif view_type == "back":
            image_info = character_card.get("back_view", {}).get("image", {})
        else:
            raise HTTPException(status_code=400, detail="视图类型必须是 'front' 或 'back'")

        if not image_info.get("filename"):
            raise HTTPException(status_code=404, detail="图片不存在")

        # 构建图片文件路径
        image_path = Path(project_path) / "characters" / character_name / "images" / image_info["filename"]
        if not image_path.exists():
            raise HTTPException(status_code=404, detail="图片文件不存在")

        # 返回图片文件
        from fastapi.responses import FileResponse
        return FileResponse(
            path=str(image_path),
            media_type="image/png",
            filename=image_info["filename"]
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取角色卡图片失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取角色卡图片失败: {str(e)}")




def create_character_card_image(image_path: Path, character_info: dict, view_type: str, prompt: str, generation_params: dict):
    """
    生成纯净的角色图片（不包含边框、文字或其他UI元素）
    Generate clean character image (without borders, text or other UI elements)
    """
    try:
        from services.ai_service import volc_service
        import logging

        logger.info(f"开始生成{view_type}角色图片")

        # 调用AI服务生成纯净的角色图片
        reference_images = generation_params.get("reference_images", [])
        model = generation_params.get("model", "doubao-seedream-4-0-250828")
        size = generation_params.get("size", "1024x1024")

        # 构建纯净的角色prompt - 明确要求不要UI元素和全身图
        clean_prompt = f"全身动漫角色立绘，{view_type}视角，{prompt}，白色背景，无边框，无文字，无UI界面，无装饰元素"
        if view_type == "front":
            clean_prompt += "，正面视角，清晰的面部特征，完整全身角色形象，从头到脚完整显示，包含头部、身体、手臂、腿部和足部，全身站姿"
        else:
            clean_prompt += "，背面视角，展现完整背影轮廓，全身角色形象，从头到脚完整显示，包含头部后部、背部、手臂后部、腿部和足部，全身站姿"

        # 调用AI生成图片
        if len(reference_images) > 0:
            # 使用多参考图API
            logger.info(f"使用多参考图生成{view_type}角色图片")
            result = volc_service.multi_reference_text_to_image(
                model=model,
                prompt=clean_prompt,
                reference_images=reference_images,
                max_images=1
            )
        else:
            # 使用普通文生图API
            logger.info(f"使用普通文生图生成{view_type}角色图片")
            result = volc_service.text_to_image(
                model=model,
                prompt=clean_prompt,
                size=size,
                stream=False,
                max_images=1
            )

        if result is None:
            logger.error(f"AI图片生成失败: {view_type}")
            return False

        # 处理返回结果
        image_url = None
        if isinstance(result, str):
            image_url = result
        elif isinstance(result, list) and len(result) > 0:
            image_url = result[0]
        elif hasattr(result, 'data') and len(result.data) > 0:
            image_url = result.data[0].url

        if not image_url:
            logger.error(f"AI服务未返回有效的图片URL: {view_type}")
            return False

        # 下载AI生成的图片
        try:
            import requests
            from io import BytesIO
            from PIL import Image

            response = requests.get(image_url, timeout=30)
            if response.status_code == 200:
                # 直接保存AI生成的图片，不添加任何边框或文字
                image = Image.open(BytesIO(response.content))
                image.save(image_path, 'PNG', quality=95)
                logger.info(f"纯净{view_type}角色图片已生成: {image_path}")
                return True
            else:
                logger.error(f"下载AI图片失败: HTTP {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"下载或保存AI图片失败: {e}")
            return False

    except Exception as e:
        logger.error(f"生成角色图片失败: {e}")
        return False  # 生成失败


def create_back_view_from_front(back_image_path: Path, front_image_path: Path, prompt: str, generation_params: dict):
    """
    基于正面图片生成背面视图，确保角色一致性
    Generate back view based on front image to ensure character consistency
    """
    try:
        from services.ai_service import volc_service
        import logging
        import base64
        from PIL import Image

        logger.info("基于正面图片生成背面视图，确保角色一致性")

        # 读取正面图片并转换为base64
        with open(front_image_path, 'rb') as f:
            image_data = f.read()
            front_image_base64 = base64.b64encode(image_data).decode('utf-8')

        # 构建背面视图prompt，强调保持角色特征和全身显示
        model = generation_params.get("model", "doubao-seedream-4-0-250828")
        back_prompt = f"基于正面全身图片生成背面全身视角，保持完全相同的角色特征：{prompt}，相同的发型、发色、服饰、身材比例，从头到脚完整显示，只是视角从正面转到背面，白色背景，无边框，无文字，确保全身完整可见"

        # 使用image_to_image API生成背面视图
        result = volc_service.image_to_image(
            model=model,
            prompt=back_prompt,
            image_url=None,
            image_base64=front_image_base64
        )

        if result is None:
            logger.error("背面视图AI生成失败")
            return False

        # 处理返回结果
        image_url = None
        if isinstance(result, str):
            image_url = result
        elif hasattr(result, 'url'):
            image_url = result.url

        if not image_url:
            logger.error("背面视图AI服务未返回有效的图片URL")
            return False

        # 下载AI生成的背面图片
        try:
            import requests
            from io import BytesIO

            response = requests.get(image_url, timeout=30)
            if response.status_code == 200:
                # 直接保存AI生成的图片
                image = Image.open(BytesIO(response.content))
                image.save(back_image_path, 'PNG', quality=95)
                logger.info(f"背面视图图片已生成: {back_image_path}")
                return True
            else:
                logger.error(f"下载背面图片失败: HTTP {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"下载或保存背面图片失败: {e}")
            return False

    except Exception as e:
        logger.error(f"生成背面视图失败: {e}")
        return False


@router.put("/{project_id}/{character_name}/card")
async def update_character_card(
    project_id: str,
    character_name: str,
    card_data: dict,
    fs: ProjectFileSystem = Depends(get_file_system)
):
    """
    更新角色卡信息
    Update character card information
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

        # 检查角色卡文件是否存在
        card_file = Path(project_path) / "characters" / character_name / "character_card.json"
        if not card_file.exists():
            raise HTTPException(status_code=404, detail="角色卡不存在")

        # 读取现有角色卡数据
        existing_card = fs._load_json(card_file)

        # 更新角色卡数据
        if "front_view" in card_data:
            if "appearance" in card_data["front_view"]:
                existing_card["front_view"]["appearance"] = card_data["front_view"]["appearance"]
            if "background" in card_data["front_view"]:
                existing_card["front_view"]["background"] = card_data["front_view"]["background"]
            if "personality" in card_data["front_view"]:
                if "positive" in card_data["front_view"]["personality"]:
                    existing_card["front_view"]["personality"]["positive"] = card_data["front_view"]["personality"]["positive"]
                if "negative" in card_data["front_view"]["personality"]:
                    existing_card["front_view"]["personality"]["negative"] = card_data["front_view"]["personality"]["negative"]

        if "back_view" in card_data:
            if "backstory" in card_data["back_view"]:
                existing_card["back_view"]["backstory"] = card_data["back_view"]["backstory"]
            if "relationships" in card_data["back_view"]:
                existing_card["back_view"]["relationships"] = card_data["back_view"]["relationships"]
            if "goals" in card_data["back_view"]:
                existing_card["back_view"]["goals"] = card_data["back_view"]["goals"]
            if "secrets" in card_data["back_view"]:
                existing_card["back_view"]["secrets"] = card_data["back_view"]["secrets"]
            if "skills" in card_data["back_view"]:
                existing_card["back_view"]["skills"] = card_data["back_view"]["skills"]

        # 更新正面视图中的能力值
        if "front_view" in card_data and "stats" in card_data["front_view"]:
            if "stats" in existing_card["front_view"]:
                existing_card["front_view"]["stats"].update(card_data["front_view"]["stats"])
            else:
                existing_card["front_view"]["stats"] = card_data["front_view"]["stats"]

        # 更新正面视图中的技能列表
        if "front_view" in card_data and "skills" in card_data["front_view"]:
            existing_card["front_view"]["skills"] = card_data["front_view"]["skills"]

        # 更新修改时间
        existing_card["updated_at"] = datetime.now().isoformat()

        # 保存更新后的角色卡
        fs._save_json(card_file, existing_card)

        logger.info(f"角色卡更新成功: {character_name}")

        return {
            "success": True,
            "data": existing_card,
            "message": f"角色 '{character_name}' 的角色卡更新成功"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新角色卡失败: {e}")
        raise HTTPException(status_code=500, detail=f"更新角色卡失败: {str(e)}")


@router.delete("/{project_id}/{character_name}/card")
async def delete_character_card(
    project_id: str,
    character_name: str,
    fs: ProjectFileSystem = Depends(get_file_system)
):
    """
    删除角色卡
    Delete character card
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

        # 检查角色卡文件是否存在
        card_file = Path(project_path) / "characters" / character_name / "character_card.json"
        if not card_file.exists():
            raise HTTPException(status_code=404, detail="角色卡不存在")

        # 删除角色卡文件
        card_file.unlink()

        # 删除角色卡图片目录
        images_dir = Path(project_path) / "characters" / character_name / "images"
        if images_dir.exists():
            import shutil
            shutil.rmtree(images_dir)
            logger.info(f"已删除角色卡图片目录: {images_dir}")

        logger.info(f"已删除角色卡: {character_name}")

        return {
            "success": True,
            "message": f"角色 '{character_name}' 的角色卡删除成功"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除角色卡失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除角色卡失败: {str(e)}")


@router.delete("/{project_id}/{character_name}")
async def delete_character(
    project_id: str,
    character_name: str,
    fs: ProjectFileSystem = Depends(get_file_system)
):
    """
    删除角色
    Delete character
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

        # 读取角色列表
        characters_file = Path(project_path) / "characters" / "characters.json"
        if not characters_file.exists():
            raise HTTPException(status_code=404, detail="角色不存在")

        characters_data = fs._load_json(characters_file)

        # 查找并移除角色
        character_found = False
        for i, character in enumerate(characters_data):
            if character.get("name") == character_name:
                characters_data.pop(i)
                character_found = True
                break

        if not character_found:
            raise HTTPException(status_code=404, detail="角色不存在")

        # 保存更新后的角色列表
        fs._save_json(characters_file, characters_data)

        # 删除角色目录（包括所有相关文件）
        character_dir = Path(project_path) / "characters" / character_name
        if character_dir.exists():
            import shutil
            shutil.rmtree(character_dir)
            logger.info(f"已删除角色目录: {character_dir}")

        return {
            "success": True,
            "message": f"角色 '{character_name}' 删除成功"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除角色失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除角色失败: {str(e)}")

