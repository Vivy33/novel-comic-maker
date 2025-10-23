"""
漫画管理API路由
Comic Management API Routes
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any
import logging
from pathlib import Path

from ..services.file_system import ProjectFileSystem
from ..services.comic_service import ComicService
from ..models.comic import ComicGenerateRequest, ChapterComic

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
        logger.error(f"漫画生成任务启动失败: {e}")
        raise HTTPException(status_code=500, detail=f"漫画生成任务启动失败: {str(e)}")


@router.get("/generate/{task_id}/status")
async def get_generation_status(
    task_id: str,
    comic_service: ComicService = Depends(get_comic_service)
):
    """
    获取生成任务状态
    Get generation task status
    """
    try:
        status = await comic_service.get_generation_status(task_id)
        return status
    except Exception as e:
        logger.error(f"获取任务状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取任务状态失败: {str(e)}")


@router.get("/{project_id}/chapters", response_model=List[str])
async def get_project_chapters(
    project_id: str,
    fs: ProjectFileSystem = Depends(get_file_system)
):
    """
    获取项目章节列表
    Get project chapter list
    """
    try:
        chapters = fs.list_chapters(project_id)
        return chapters
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
        chapter = fs.get_chapter_comic(project_id, chapter_id)
        return ChapterComic(**chapter)
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
    Regenerate chapter comic content
    """
    try:
        task_id = await comic_service.regenerate_chapter(project_id, chapter_id)
        return {
            "task_id": task_id,
            "status": "started",
            "message": "重新生成任务已启动"
        }
    except Exception as e:
        logger.error(f"重新生成章节失败: {e}")
        raise HTTPException(status_code=500, detail=f"重新生成章节失败: {str(e)}")


@router.get("/{project_id}/export")
async def export_comic(
    project_id: str,
    format: str = "pdf",
    fs: ProjectFileSystem = Depends(get_file_system)
):
    """
    导出漫画
    Export comic
    """
    try:
        export_path = fs.export_comic(project_id, format)
        return {
            "success": True,
            "export_path": str(export_path)
        }
    except Exception as e:
        logger.error(f"导出漫画失败: {e}")
        raise HTTPException(status_code=500, detail=f"导出漫画失败: {str(e)}")