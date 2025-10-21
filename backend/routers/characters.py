"""
角色管理API路由
Character Management API Routes
"""

from fastapi import APIRouter, HTTPException, Depends, File, UploadFile
from typing import List
import logging
from datetime import datetime

from services.file_system import ProjectFileSystem
from models.character import CharacterInfo, CharacterCreateRequest

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
    Create a new character
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

        # 读取现有角色列表
        characters_file = fs.projects_dir / project_path / "characters" / "characters.json"
        characters = []
        if characters_file.exists():
            characters = fs._load_json(characters_file)

        # 检查角色名是否已存在
        for existing_char in characters:
            if existing_char.get("name") == character.name:
                raise HTTPException(status_code=400, detail="角色名已存在")

        # 添加新角色
        new_character = {
            "name": character.name,
            "description": character.description,
            "appearance": character.appearance,
            "personality": character.personality,
            "reference_images": []
        }

        characters.append(new_character)

        # 保存角色信息
        fs._save_json(characters_file, characters)

        # 记录历史
        fs._save_history(
            project_path,
            "character_created",
            {"character_name": character.name}
        )

        logger.info(f"角色创建成功: {character.name}")
        return {"message": f"角色 {character.name} 创建成功"}

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
        # 查找项目路径
        projects = fs.list_projects()
        project_path = None

        for project in projects:
            if project.get("project_id") == project_id:
                project_path = project.get("project_path")
                break

        if not project_path:
            raise HTTPException(status_code=404, detail="项目不存在")

        # 验证文件类型
        if not file.content_type or not file.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="请上传图片文件")

        # 保存参考图片
        character_dir = fs.projects_dir / project_path / "characters" / character_name
        character_dir.mkdir(exist_ok=True)

        # 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"reference_{timestamp}_{file.filename}"
        file_path = character_dir / filename

        # 保存文件
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)

        # 更新角色信息
        characters_file = fs.projects_dir / project_path / "characters" / "characters.json"
        if characters_file.exists():
            characters = fs._load_json(characters_file)
            for character in characters:
                if character.get("name") == character_name:
                    if "reference_images" not in character:
                        character["reference_images"] = []
                    character["reference_images"].append(str(file_path))
                    break

            fs._save_json(characters_file, characters)

        # 记录历史
        fs._save_history(
            project_path,
            "reference_image_uploaded",
            {"character_name": character_name, "filename": filename}
        )

        logger.info(f"角色参考图片上传成功: {character_name}/{filename}")
        return {"message": "参考图片上传成功", "filename": filename}

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
    Get character reference images list
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

        # 获取角色目录中的图片文件
        character_dir = fs.projects_dir / project_path / "characters" / character_name
        if not character_dir.exists():
            return []

        image_files = []
        for file_path in character_dir.glob("reference_*.png"):
            image_files.append({
                "filename": file_path.name,
                "path": str(file_path)
            })

        return image_files

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

        # 删除图片文件
        file_path = fs.projects_dir / project_path / "characters" / character_name / filename
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="图片文件不存在")

        file_path.unlink()

        # 更新角色信息
        characters_file = fs.projects_dir / project_path / "characters" / "characters.json"
        if characters_file.exists():
            characters = fs._load_json(characters_file)
            for character in characters:
                if character.get("name") == character_name:
                    if "reference_images" in character:
                        character["reference_images"] = [
                            img for img in character["reference_images"]
                            if not img.endswith(filename)
                        ]
                        break

            fs._save_json(characters_file, characters)

        # 记录历史
        fs._save_history(
            project_path,
            "reference_image_deleted",
            {"character_name": character_name, "filename": filename}
        )

        logger.info(f"角色参考图片删除成功: {character_name}/{filename}")
        return {"message": "参考图片删除成功"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除参考图片失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除参考图片失败: {str(e)}")