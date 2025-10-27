"""
项目管理API路由
Project Management API Routes
"""

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from typing import List, Optional
import logging
import os
import re
from pathlib import Path

from services.file_system import ProjectFileSystem
from services.cover_service import CoverService
from models.file_system import ProjectCreate, ProjectUpdate, ProjectInfo, Project, ProjectTimeline, ApiResponse, NovelCreate, NovelUpdate

logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(prefix="/api/projects", tags=["projects"])

# 依赖注入：获取文件系统实例
def get_file_system():
    return ProjectFileSystem()

# 依赖注入：获取封面服务实例
def get_cover_service():
    return CoverService()


@router.post("/", response_model=ApiResponse[Project])
async def create_project(
    project: ProjectCreate,
    fs: ProjectFileSystem = Depends(get_file_system)
):
    """
    创建新项目
    Create a new project
    """
    try:
        project_path = fs.create_project(project.name, project.novel_text or "", project.description or "")
        project_info = fs.get_project_info(project_path)

        # 转换为前端期望的格式
        project_data = Project(
            id=project_info["project_id"],
            name=project_info["project_name"],
            description=project_info.get("description") or project.description or f"项目 {project_info['project_name']}",
            created_at=project_info["created_at"],
            updated_at=project_info.get("updated_at") or project_info["created_at"],  # 如果没有更新时间，使用创建时间
            status=project_info["status"],
            metadata={
                "display_id": project_info["project_id"].split("_", 2)[-1],  # 只显示项目名称部分
                "current_step": project_info.get("current_step", "initialized"),
                "total_characters": project_info.get("total_characters", 0),
                "project_path": project_path
            }
        )

        return ApiResponse[Project](
            data=project_data,
            message="项目创建成功",
            success=True
        )
    except Exception as e:
        logger.error(f"创建项目失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建项目失败: {str(e)}")


@router.get("/", response_model=ApiResponse[List[Project]])
async def list_projects(
    fs: ProjectFileSystem = Depends(get_file_system),
    cover_service: CoverService = Depends(get_cover_service)
):
    """
    获取所有项目列表
    Get list of all projects
    """
    logger.info("enter, GET /api/projects/ list_projects@projects.py")
    try:
        projects = fs.list_projects()
        # 转换为前端期望的格式
        project_list = []

        for project in projects:
            # 获取项目封面信息
            primary_cover = None
            try:
                covers = cover_service.get_project_covers(project["project_id"], fs)

                # 分离项目封面和章节封面（与comics.py中的逻辑相同）
                primary_cover_info = None
                chapter_covers = []

                for cover in covers:
                    # 数据字段映射和兼容性处理
                    image_path = cover.get("local_path", "")
                    thumbnail_url = cover.get("image_url", "")

                    # 处理 image_url 的不同数据结构
                    if isinstance(thumbnail_url, dict) and "image_url" in thumbnail_url:
                        thumbnail_url = thumbnail_url["image_url"]

                    # 如果没有 local_path但有 image_url，使用 image_url 作为缩略图
                    if not image_path and thumbnail_url:
                        image_path = thumbnail_url
                    elif not image_path:
                        # 如果都没有，使用默认值
                        image_path = ""
                        thumbnail_url = ""

                    # 生成缩略图URL（如果本地文件存在）
                    if image_path and not thumbnail_url:
                        # 将本地路径转换为可通过静态文件服务访问的URL
                        if image_path.startswith("/"):
                            # 绝对路径，转换为相对路径
                            relative_path = image_path.replace("/home/vivy/novel-comic-maker/projects/", "")
                            thumbnail_url = f"/{relative_path}"
                        elif image_path.startswith("projects/"):
                            # 相对路径，直接使用
                            thumbnail_url = f"/{image_path}"

                    if cover.get("cover_type") == "project":
                        if cover.get("is_primary", False):
                            primary_cover_info = {
                                "cover_id": cover["cover_id"],
                                "thumbnail_url": thumbnail_url,
                                "title": cover.get("title")
                            }
                        # 如果没有设置主封面，使用第一个项目封面
                        elif primary_cover_info is None:
                            primary_cover_info = {
                                "cover_id": cover["cover_id"],
                                "thumbnail_url": thumbnail_url,
                                "title": cover.get("title")
                            }

                primary_cover = primary_cover_info

                if primary_cover:
                    logger.info(f"项目 {project['project_id']} 主封面: {primary_cover.get('title', '无标题')}")

            except Exception as cover_error:
                logger.warning(f"获取项目 {project['project_id']} 封面信息失败: {cover_error}")

            project_data = Project(
                id=project["project_id"],
                name=project["project_name"],
                description=project.get("description") or f"项目 {project['project_name']}",
                created_at=project["created_at"],
                updated_at=project.get("updated_at") or project["created_at"],  # 如果没有更新时间，使用创建时间
                status=project["status"],
                metadata={
                    "display_id": project["project_id"].split("_", 2)[-1],  # 只显示项目名称部分
                    "current_step": project.get("current_step", "initialized"),
                    "total_characters": project.get("total_characters", 0),
                    "project_path": project.get("project_path")
                },
                primary_cover=primary_cover
            )
            project_list.append(project_data)

        return ApiResponse[List[Project]](
            data=project_list,
            message="获取项目列表成功",
            success=True
        )
    except Exception as e:
        logger.error(f"获取项目列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取项目列表失败: {str(e)}")


@router.get("/{project_id}", response_model=ApiResponse[Project])
async def get_project(
    project_id: str,
    fs: ProjectFileSystem = Depends(get_file_system),
    cover_service: CoverService = Depends(get_cover_service)
):
    """
    获取项目详细信息
    Get project details
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

        # 获取项目信息并转换为前端期望格式
        project_info = fs.get_project_info(project_path)
        project_info["project_path"] = project_path

        # 获取项目封面信息
        primary_cover = None
        try:
            covers = cover_service.get_project_covers(project_id, fs)

            # 分离项目封面和章节封面（与comics.py中的逻辑相同）
            primary_cover_info = None

            for cover in covers:
                # 数据字段映射和兼容性处理
                image_path = cover.get("local_path", "")
                thumbnail_url = cover.get("image_url", "")

                # 处理 image_url 的不同数据结构
                if isinstance(thumbnail_url, dict) and "image_url" in thumbnail_url:
                    thumbnail_url = thumbnail_url["image_url"]

                # 如果没有 local_path但有 image_url，使用 image_url 作为缩略图
                if not image_path and thumbnail_url:
                    image_path = thumbnail_url
                elif not image_path:
                    # 如果都没有，使用默认值
                    image_path = ""
                    thumbnail_url = ""

                # 生成缩略图URL（如果本地文件存在）
                if image_path and not thumbnail_url:
                    # 将本地路径转换为可通过静态文件服务访问的URL
                    if image_path.startswith("/"):
                        # 绝对路径，转换为相对路径
                        relative_path = image_path.replace("/home/vivy/novel-comic-maker/projects/", "")
                        thumbnail_url = f"/{relative_path}"
                    elif image_path.startswith("projects/"):
                        # 相对路径，直接使用
                        thumbnail_url = f"/{image_path}"

                if cover.get("cover_type") == "project":
                    if cover.get("is_primary", False):
                        primary_cover_info = {
                            "cover_id": cover["cover_id"],
                            "thumbnail_url": thumbnail_url,
                            "title": cover.get("title")
                        }
                    # 如果没有设置主封面，使用第一个项目封面
                    elif primary_cover_info is None:
                        primary_cover_info = {
                            "cover_id": cover["cover_id"],
                            "thumbnail_url": thumbnail_url,
                            "title": cover.get("title")
                        }

            primary_cover = primary_cover_info

        except Exception as cover_error:
            logger.warning(f"获取项目 {project_id} 封面信息失败: {cover_error}")

        project_data = Project(
            id=project_info["project_id"],
            name=project_info["project_name"],
            description=project_info.get("description") or f"项目 {project_info['project_name']}",
            created_at=project_info["created_at"],
            updated_at=project_info.get("updated_at") or project_info["created_at"],  # 如果没有更新时间，使用创建时间
            status=project_info["status"],
            metadata={
                "display_id": project_info["project_id"].split("_", 2)[-1],  # 只显示项目名称部分
                "current_step": project_info.get("current_step", "initialized"),
                "total_characters": project_info.get("total_characters", 0),
                "project_path": project_path
            },
            primary_cover=primary_cover
        )

        return ApiResponse[Project](
            data=project_data,
            message="获取项目信息成功",
            success=True
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取项目信息失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取项目信息失败: {str(e)}")


@router.put("/{project_id}", response_model=ApiResponse[Project])
async def update_project(
    project_id: str,
    project_update: ProjectUpdate,
    fs: ProjectFileSystem = Depends(get_file_system)
):
    """
    更新项目信息
    Update project information
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

        # 更新项目信息
        success = fs.update_project_info(project_path, project_update.dict(exclude_unset=True))
        if not success:
            raise HTTPException(status_code=500, detail="更新项目失败")

        # 获取更新后的项目信息
        project_info = fs.get_project_info(project_path)
        project_info["project_path"] = project_path

        project_data = Project(
            id=project_info["project_id"],
            name=project_info["project_name"],
            description=project_info.get("description") or f"项目 {project_info['project_name']}",
            created_at=project_info["created_at"],
            updated_at=project_info.get("updated_at") or project_info["created_at"],
            status=project_info["status"],
            metadata={
                "display_id": project_info["project_id"].split("_", 2)[-1],
                "current_step": project_info.get("current_step", "initialized"),
                "total_characters": project_info.get("total_characters", 0),
                "project_path": project_path
            }
        )

        return ApiResponse[Project](
            data=project_data,
            message="项目更新成功",
            success=True
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新项目失败: {e}")
        raise HTTPException(status_code=500, detail=f"更新项目失败: {str(e)}")


@router.delete("/{project_id}", response_model=ApiResponse[None])
async def delete_project(
    project_id: str,
    fs: ProjectFileSystem = Depends(get_file_system)
):
    """
    删除项目
    Delete a project
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

        # 删除项目目录（只删除指定项目）
        if not fs.delete_project_directory(project_path):
            raise HTTPException(status_code=500, detail="删除项目失败")

        return ApiResponse[None](
            data=None,
            message="项目删除成功",
            success=True
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除项目失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除项目失败: {str(e)}")


@router.get("/{project_id}/timeline", response_model=ProjectTimeline)
async def get_project_timeline(
    project_id: str,
    fs: ProjectFileSystem = Depends(get_file_system)
):
    """
    获取项目时间线
    Get project timeline
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

        timeline = fs.get_project_timeline(project_path)
        return ProjectTimeline(
            project_id=project_id,
            timeline=timeline
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取项目时间线失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取项目时间线失败: {str(e)}")


# 小说文件管理相关API
@router.get("/{project_id}/novels", response_model=ApiResponse[List[dict]])
async def get_novels(
    project_id: str,
    fs: ProjectFileSystem = Depends(get_file_system)
):
    """
    获取项目的小说文件列表
    Get list of novel files in the project
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

        # 获取小说文件列表
        source_dir = Path(project_path) / "source"
        if not source_dir.exists():
            source_dir.mkdir(parents=True, exist_ok=True)

        # 读取主要小说配置
        primary_filename = None
        primary_config_path = source_dir / ".primary_novel.txt"
        if primary_config_path.exists():
            with open(primary_config_path, 'r', encoding='utf-8') as f:
                primary_filename = f.read().strip()

        novels = []
        for file_path in source_dir.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in ['.txt', '.md'] and not file_path.name.startswith('.'):
                stat = file_path.stat()
                novels.append({
                    "filename": file_path.name,
                    "title": file_path.stem,
                    "size": stat.st_size,
                    "created_at": stat.st_ctime,
                    "modified_at": stat.st_mtime,
                    "is_primary": (file_path.name == primary_filename)
                })

        # 按修改时间倒序排列
        novels.sort(key=lambda x: x["modified_at"], reverse=True)

        return ApiResponse[List[dict]](
            data=novels,
            message="获取小说文件列表成功",
            success=True
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取小说文件列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取小说文件列表失败: {str(e)}")


@router.post("/{project_id}/novels/upload", response_model=ApiResponse[dict])
async def upload_novel(
    project_id: str,
    file: UploadFile = File(...),
    is_primary: bool = False,
    fs: ProjectFileSystem = Depends(get_file_system)
):
    """
    上传小说文件
    Upload a novel file
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

        # 检查文件类型
        if not file.filename:
            raise HTTPException(status_code=400, detail="文件名为空")

        file_extension = Path(file.filename).suffix.lower()
        if file_extension not in ['.txt', '.md']:
            raise HTTPException(status_code=400, detail="只支持 .txt 和 .md 文件")

        # 确保source目录存在
        source_dir = Path(project_path) / "source"
        source_dir.mkdir(parents=True, exist_ok=True)

        # 保持原文件名
        target_filename = file.filename

        # 处理主要小说标识
        if is_primary:
            # 创建或更新主要小说配置文件
            primary_config_path = source_dir / ".primary_novel.txt"
            with open(primary_config_path, 'w', encoding='utf-8') as f:
                f.write(target_filename)

        target_path = source_dir / target_filename

        # 检查文件大小（限制10MB）
        content = await file.read()
        if len(content) > 10 * 1024 * 1024:  # 10MB
            raise HTTPException(status_code=400, detail="文件大小不能超过10MB")

        # 写入文件
        with open(target_path, 'wb') as f:
            f.write(content)

        # 获取文件信息
        stat = target_path.stat()

        # 检查是否为主要小说
        is_primary = False
        primary_config_path = source_dir / ".primary_novel.txt"
        if primary_config_path.exists():
            with open(primary_config_path, 'r', encoding='utf-8') as f:
                primary_filename = f.read().strip()
                is_primary = (primary_filename == target_filename)

        return ApiResponse[dict](
            data={
                "filename": target_filename,
                "title": Path(file.filename).stem,  # 使用原始文件名作为标题
                "size": stat.st_size,
                "created_at": stat.st_ctime,
                "modified_at": stat.st_mtime,
                "is_primary": is_primary
            },
            message="小说文件上传成功",
            success=True
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"上传小说文件失败: {e}")
        raise HTTPException(status_code=500, detail=f"上传小说文件失败: {str(e)}")


@router.post("/{project_id}/novels/create", response_model=ApiResponse[dict])
async def create_novel(
    project_id: str,
    request: NovelCreate,
    fs: ProjectFileSystem = Depends(get_file_system)
):
    """
    创建新的小说文件
    Create a new novel file
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

        # 确保source目录存在
        source_dir = Path(project_path) / "source"
        source_dir.mkdir(parents=True, exist_ok=True)

        # 生成文件名（总是使用标题）
        safe_title = "".join(c for c in request.title if c.isalnum() or c in (' ', '-', '_')).strip()
        if not safe_title:
            safe_title = "untitled"

        filename = f"{safe_title}.txt"

        # 处理主要小说标识
        if request.is_primary:
            # 创建或更新主要小说配置文件
            primary_config_path = source_dir / ".primary_novel.txt"
            with open(primary_config_path, 'w', encoding='utf-8') as f:
                f.write(filename)

        target_path = source_dir / filename

        # 写入文件
        with open(target_path, 'w', encoding='utf-8') as f:
            f.write(request.content)

        # 获取文件信息
        stat = target_path.stat()

        # 检查是否为主要小说
        is_primary = False
        primary_config_path = source_dir / ".primary_novel.txt"
        if primary_config_path.exists():
            with open(primary_config_path, 'r', encoding='utf-8') as f:
                primary_filename = f.read().strip()
                is_primary = (primary_filename == filename)

        return ApiResponse[dict](
            data={
                "filename": filename,
                "title": request.title,  # 使用原始标题而不是文件名
                "size": stat.st_size,
                "created_at": stat.st_ctime,
                "modified_at": stat.st_mtime,
                "is_primary": is_primary
            },
            message="小说文件创建成功",
            success=True
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建小说文件失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建小说文件失败: {str(e)}")


@router.get("/{project_id}/novels/{filename}/content", response_model=ApiResponse[dict])
async def get_novel_content(
    project_id: str,
    filename: str,
    fs: ProjectFileSystem = Depends(get_file_system)
):
    """
    获取小说文件内容
    Get novel file content
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

        # 构建文件路径
        source_dir = Path(project_path) / "source"
        file_path = source_dir / filename

        if not file_path.exists() or not file_path.is_file():
            raise HTTPException(status_code=404, detail="小说文件不存在")

        # 读取文件内容
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 检查是否为主要小说
        primary_config_path = source_dir / ".primary_novel.txt"
        is_primary = False
        if primary_config_path.exists():
            with open(primary_config_path, 'r', encoding='utf-8') as f:
                primary_filename = f.read().strip()
                is_primary = (primary_filename == filename)

        stat = file_path.stat()

        return ApiResponse[dict](
            data={
                "filename": filename,
                "title": Path(filename).stem,
                "content": content,
                "size": stat.st_size,
                "created_at": stat.st_ctime,
                "modified_at": stat.st_mtime,
                "is_primary": is_primary
            },
            message="获取小说内容成功",
            success=True
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取小说内容失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取小说内容失败: {str(e)}")


@router.put("/{project_id}/novels/{filename}/content", response_model=ApiResponse[dict])
async def update_novel_content(
    project_id: str,
    filename: str,
    request: NovelUpdate,
    fs: ProjectFileSystem = Depends(get_file_system)
):
    """
    更新小说文件内容
    Update novel file content
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

        # 构建文件路径
        source_dir = Path(project_path) / "source"
        file_path = source_dir / filename

        if not file_path.exists() or not file_path.is_file():
            raise HTTPException(status_code=404, detail="小说文件不存在")

        # 写入文件内容
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(request.content)

        # 检查是否为主要小说
        primary_config_path = source_dir / ".primary_novel.txt"
        is_primary = False
        if primary_config_path.exists():
            with open(primary_config_path, 'r', encoding='utf-8') as f:
                primary_filename = f.read().strip()
                is_primary = (primary_filename == filename)

        # 获取更新后的文件信息
        stat = file_path.stat()

        return ApiResponse[dict](
            data={
                "filename": filename,
                "title": Path(filename).stem,
                "content": request.content,
                "size": stat.st_size,
                "created_at": stat.st_ctime,
                "modified_at": stat.st_mtime,
                "is_primary": is_primary
            },
            message="小说内容更新成功",
            success=True
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新小说内容失败: {e}")
        raise HTTPException(status_code=500, detail=f"更新小说内容失败: {str(e)}")


@router.delete("/{project_id}/novels/{filename}", response_model=ApiResponse[None])
async def delete_novel(
    project_id: str,
    filename: str,
    fs: ProjectFileSystem = Depends(get_file_system)
):
    """
    删除小说文件
    Delete a novel file
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

        # 构建文件路径
        source_dir = Path(project_path) / "source"
        file_path = source_dir / filename

        if not file_path.exists() or not file_path.is_file():
            raise HTTPException(status_code=404, detail="小说文件不存在")

        # 删除文件
        file_path.unlink()

        return ApiResponse[None](
            data=None,
            message="小说文件删除成功",
            success=True
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除小说文件失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除小说文件失败: {str(e)}")


@router.put("/{project_id}/novels/{filename}/set-primary", response_model=ApiResponse[dict])
async def set_primary_novel(
    project_id: str,
    filename: str,
    fs: ProjectFileSystem = Depends(get_file_system)
):
    """
    设置主要小说文件
    Set primary novel file
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

        # 构建文件路径
        source_dir = Path(project_path) / "source"
        file_path = source_dir / filename

        if not file_path.exists() or not file_path.is_file():
            raise HTTPException(status_code=404, detail="小说文件不存在")

        # 创建或更新主要小说配置文件
        primary_config_path = source_dir / ".primary_novel.txt"
        with open(primary_config_path, 'w', encoding='utf-8') as f:
            f.write(filename)

        # 获取文件信息
        stat = file_path.stat()

        return ApiResponse[dict](
            data={
                "filename": filename,
                "title": Path(filename).stem,
                "size": stat.st_size,
                "created_at": stat.st_ctime,
                "modified_at": stat.st_mtime,
                "is_primary": True
            },
            message="主要小说文件设置成功",
            success=True
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"设置主要小说文件失败: {e}")
        raise HTTPException(status_code=500, detail=f"设置主要小说文件失败: {str(e)}")


def convert_chinese_number_to_arabic(chinese_num: str) -> int:
    """
    将中文数字转换为阿拉伯数字
    Convert Chinese numbers to Arabic numbers
    """
    chinese_map = {
        '零': 0, '一': 1, '二': 2, '三': 3, '四': 4, '五': 5,
        '六': 6, '七': 7, '八': 8, '九': 9, '十': 10,
        '百': 100, '千': 1000, '万': 10000
    }

    if chinese_num.isdigit():
        return int(chinese_num)

    result = 0
    temp = 0

    for char in chinese_num:
        if char in chinese_map:
            value = chinese_map[char]
            if value == 10:
                if temp == 0:
                    temp = 1
                result += temp
                temp = 0
            elif value >= 100:
                if temp == 0:
                    temp = 1
                result += temp * value
                temp = 0
            else:
                temp = temp * 10 + value

    result += temp
    return result


@router.get("/{project_id}/novels/chapters", response_model=ApiResponse[List[dict]])
async def get_novel_chapters(
    project_id: str,
    fs: ProjectFileSystem = Depends(get_file_system)
):
    """
    获取小说章节列表
    Get novel chapters list
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

        # 构建小说文件目录路径
        source_dir = Path(project_path) / "source"

        # 查找主要小说文件
        primary_config_path = source_dir / ".primary_novel.txt"
        primary_filename = None

        if primary_config_path.exists():
            with open(primary_config_path, 'r', encoding='utf-8') as f:
                primary_filename = f.read().strip()

        # 如果没有主要小说，查找第一个小说文件
        if not primary_filename:
            for file_path in source_dir.glob("*.txt"):
                primary_filename = file_path.name
                break

        if not primary_filename:
            return ApiResponse[List[dict]](
                data=[],
                message="未找到小说文件",
                success=True
            )

        # 读取小说内容
        novel_path = source_dir / primary_filename
        if not novel_path.exists():
            raise HTTPException(status_code=404, detail="小说文件不存在")

        with open(novel_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 解析章节标题
        chapters_by_number = {}

        # 常见的章节标题模式
        chapter_patterns = [
            r'第[一二三四五六七八九十百千万零\d]+章[：:\s]*(.+?)(?=\n|$)',
            r'第[一二三四五六七八九十百千万零\d]+节[：:\s]*(.+?)(?=\n|$)',
            r'Chapter\s*\d+[：:\s]*(.+?)(?=\n|$)',
            r'第\d+章[：:\s]*(.+?)(?=\n|$)',
            r'【(.+?)】',
            r'（(.+?)）',
            r'\((.+?)\)',
        ]

        lines = content.split('\n')
        chapter_index = 1

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 尝试匹配各种章节标题模式
            for pattern in chapter_patterns:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    chapter_title = match.group(1) if match.groups() else line

                    # 提取章节编号
                    chapter_num_match = re.search(r'第([一二三四五六七八九十百千万零\d]+)章', line)
                    chapter_num = chapter_index  # 默认使用顺序编号

                    if chapter_num_match:
                        num_str = chapter_num_match.group(1)
                        # 尝试转换中文数字
                        chapter_num = convert_chinese_number_to_arabic(num_str) or chapter_index

                    # 如果还没有这个章节编号的目录，创建一个
                    if chapter_num not in chapters_by_number:
                        chapters_by_number[chapter_num] = {
                            "chapter_number": chapter_num,
                            "chapter_title": f"第{chapter_num}章",
                            "chapters": []
                        }

                    chapters_by_number[chapter_num]["chapters"].append({
                        "chapter_id": f"chapter_{chapter_index:03d}",
                        "title": chapter_title.strip(),
                        "full_line": line
                    })
                    chapter_index += 1
                    break

        # 如果没有找到标准章节标题，尝试按段落分割
        if not chapters_by_number:
            paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
            for i, paragraph in enumerate(paragraphs[:20]):  # 最多取前20段
                if len(paragraph) > 50:  # 只取有实质内容的段落
                    chapter_num = i + 1
                    # 取段落的前30个字符作为标题
                    title = paragraph[:30] + "..." if len(paragraph) > 30 else paragraph

                    # 如果还没有这个章节编号的目录，创建一个
                    if chapter_num not in chapters_by_number:
                        chapters_by_number[chapter_num] = {
                            "chapter_number": chapter_num,
                            "chapter_title": f"第{chapter_num}章",
                            "chapters": []
                        }

                    chapters_by_number[chapter_num]["chapters"].append({
                        "chapter_id": f"chapter_{chapter_num:03d}",
                        "title": title,
                        "full_line": title
                    })

        # 转换为列表格式并排序
        chapters = sorted(list(chapters_by_number.values()), key=lambda x: x["chapter_number"])

        return ApiResponse[List[dict]](
            data=chapters,
            message="获取小说章节成功",
            success=True
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取小说章节失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取小说章节失败: {str(e)}")