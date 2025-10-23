"""
角色管理API路由
Character Management API Routes
"""

from fastapi import APIRouter, HTTPException, Depends, File, UploadFile
from typing import List
import logging
from datetime import datetime
from pathlib import Path

from ..services.file_system import ProjectFileSystem
from ..models.character import CharacterInfo, CharacterCreateRequest

logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(prefix="/characters", tags=["characters"])

# 依赖注入
def get_file_system():
    return ProjectFileSystem()


@router.get("/{project_id}", response_model=List[CharacterInfo])
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
        characters_file = fs.projects_dir / project_path / "characters" / "characters.json"
        if not characters_file.exists():
            return []

        characters_data = fs._load_json(characters_file)
        return [CharacterInfo(**character) for character in characters_data]
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
        characters_dir = fs.projects_dir / project_path / "characters"
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
        new_character = {
            "name": character.name,
            "description": character.description,
            "appearance": character.appearance,
            "personality": character.personality,
            "reference_images": [],
            "created_at": datetime.now().isoformat()
        }
        characters.append(new_character)

        fs._save_json(characters_file, characters)

        return {
            "success": True,
            "character": CharacterInfo(**new_character)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建角色失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建角色失败: {str(e)}")


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
        target_dir = fs.projects_dir / project_path / "characters" / character_name
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
        target_dir = fs.projects_dir / project_path / "characters" / character_name
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
        target_dir = fs.projects_dir / project_path / "characters" / character_name
        target_file = target_dir / filename

        if not target_file.exists():
            raise HTTPException(status_code=404, detail="文件不存在")

        target_file.unlink()

        return {
            "success": True,
            "deleted": filename
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除参考图片失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除参考图片失败: {str(e)}")