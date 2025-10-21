"""
漫画管理API路由
Comic Management API Routes
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any
import logging

from services.file_system import ProjectFileSystem
from services.comic_service import ComicService
from models.comic import ComicGenerateRequest, ChapterComic

logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(prefix="/comics", tags=["comics"])

# 依赖注入
def get_file_system():
    return ProjectFileSystem()

def get_comic_service():
    return ComicService()


@router.post("/generate", response_model=Dict[str, Any])
async def generate_comic(
    request: ComicGenerateRequest,
    fs: ProjectFileSystem = Depends(get_file_system),
    comic_service: ComicService = Depends(get_comic_service)
):
    """
    生成漫画
    Generate comic from novel text
    """
    try:
        # 启动异步漫画生成任务
        task_id = await comic_service.start_comic_generation(
            project_id=request.project_id,
            generation_config=request.config
        )

        return {
            "task_id": task_id,
            "status": "started",
            "message": "漫画生成任务已启动"
        }
    except Exception as e:
        logger.error(f"启动漫画生成失败: {e}")
        raise HTTPException(status_code=500, detail=f"启动漫画生成失败: {str(e)}")


@router.get("/generate/{task_id}/status")
async def get_generation_status(
    task_id: str,
    comic_service: ComicService = Depends(get_comic_service)
):
    """
    获取生成任务状态
    Get comic generation task status
    """
    try:
        status = await comic_service.get_generation_status(task_id)
        return status
    except Exception as e:
        logger.error(f"获取生成状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取生成状态失败: {str(e)}")


@router.get("/{project_id}/chapters", response_model=List[str])
async def get_project_chapters(
    project_id: str,
    fs: ProjectFileSystem = Depends(get_file_system)
):
    """
    获取项目的章节列表
    Get project chapters list
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

        # 获取章节列表
        chapters_dir = fs.projects_dir / project_path / "chapters"
        if not chapters_dir.exists():
            return []

        chapters = [d.name for d in chapters_dir.iterdir() if d.is_dir()]
        chapters.sort()

        return chapters
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取章节列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取章节列表失败: {str(e)}")


@router.get("/{project_id}/chapters/{chapter_id}", response_model=ChapterComic)
async def get_chapter_comic(
    project_id: str,
    chapter_id: str,
    fs: ProjectFileSystem = Depends(get_file_system)
):
    """
    获取章节漫画内容
    Get chapter comic content
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

        # 读取章节漫画数据
        chapter_dir = fs.projects_dir / project_path / "chapters" / chapter_id
        comic_file = chapter_dir / "comic.json"

        if not comic_file.exists():
            raise HTTPException(status_code=404, detail="章节漫画不存在")

        # 读取图像列表
        images_dir = chapter_dir / "images"
        images = []
        if images_dir.exists():
            for img_file in sorted(images_dir.glob("*.png")):
                images.append({
                    "filename": img_file.name,
                    "path": str(img_file)
                })

        # 读取脚本
        script_file = chapter_dir / "script.json"
        script = {}
        if script_file.exists():
            script = fs._load_json(script_file)

        return ChapterComic(
            chapter_id=chapter_id,
            script=script,
            images=images,
            created_at=fs._load_json(comic_file).get("created_at", "")
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取章节漫画失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取章节漫画失败: {str(e)}")


@router.post("/{project_id}/chapters/{chapter_id}/regenerate")
async def regenerate_chapter_comic(
    project_id: str,
    chapter_id: str,
    comic_service: ComicService = Depends(get_comic_service)
):
    """
    重新生成章节漫画
    Regenerate chapter comic
    """
    try:
        task_id = await comic_service.regenerate_chapter(
            project_id=project_id,
            chapter_id=chapter_id
        )

        return {
            "task_id": task_id,
            "status": "started",
            "message": f"章节 {chapter_id} 重新生成任务已启动"
        }
    except Exception as e:
        logger.error(f"重新生成章节漫画失败: {e}")
        raise HTTPException(status_code=500, detail=f"重新生成章节漫画失败: {str(e)}")


@router.get("/{project_id}/export")
async def export_comic(
    project_id: str,
    format: str = "pdf",
    fs: ProjectFileSystem = Depends(get_file_system)
):
    """
    导出漫画
    Export comic in specified format
    """
    try:
        # TODO: 实现漫画导出功能
        return {
            "message": f"导出功能待实现，格式: {format}",
            "project_id": project_id
        }
    except Exception as e:
        logger.error(f"导出漫画失败: {e}")
        raise HTTPException(status_code=500, detail=f"导出漫画失败: {str(e)}")