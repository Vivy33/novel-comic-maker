"""
漫画管理API路由
Comic Management API Routes
"""

from fastapi import APIRouter, HTTPException, Depends, Request, File, UploadFile, Form
from typing import List, Dict, Any, Optional
import logging
from pathlib import Path
from datetime import datetime

from services.file_system import ProjectFileSystem
from services.comic_service import ComicService
from models.comic import (
    ComicGenerateRequest, ChapterComic, ChapterInfo, ChapterDetail,
    PanelConfirmRequest, BatchConfirmRequest, ChapterExportRequest, ChapterExportResponse
)

logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(prefix="/api/comics", tags=["comics"])

# 依赖注入
def get_file_system():
    return ProjectFileSystem()

def get_comic_service():
    return ComicService()


# 新增：图片上传API端点
@router.post("/upload/reference-image", response_model=Dict[str, Any])
async def upload_reference_image(
    project_id: str,
    image: UploadFile = File(..., description="参考图片文件"),
    file_system: ProjectFileSystem = Depends(get_file_system)
):
    """上传参考图片用于角色一致性学习和画风学习"""
    try:
        logger.info(f"上传参考图片到项目 {project_id}")

        # 获取项目路径
        project_path = file_system.get_project_path(project_id)

        if not project_path:
            raise HTTPException(status_code=404, detail="项目不存在")

        # 验证文件类型
        if not image.content_type or not image.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="只支持图片文件上传")

        # 验证文件名
        if not image.filename:
            raise HTTPException(status_code=400, detail="文件名不能为空")

        # 保存图片到参考图片目录
        ref_images_dir = Path(project_path) / "characters/reference_images"
        ref_images_dir.mkdir(parents=True, exist_ok=True)

        # 生成唯一文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_extension = Path(image.filename).suffix or ".jpg"
        # 清理文件名中的特殊字符
        safe_filename = "".join(c for c in Path(image.filename).stem if c.isalnum() or c in (' ', '-', '_')).rstrip()
        if not safe_filename:
            safe_filename = "image"
        filename = f"ref_{timestamp}_{safe_filename}{file_extension}"
        file_path = ref_images_dir / filename

        # 保存文件内容
        try:
            file_content = await image.read()
            # 验证文件内容不为空
            if not file_content:
                raise HTTPException(status_code=400, detail="上传的文件为空")

            with open(file_path, "wb") as buffer:
                buffer.write(file_content)

        except Exception as file_error:
            logger.error(f"保存文件失败: {file_error}")
            raise HTTPException(status_code=500, detail=f"保存文件失败: {str(file_error)}")

        # 生成返回URL
        file_url = f"/projects/{project_id}/characters/reference_images/{filename}"

        logger.info(f"成功保存参考图片: {file_path} (大小: {len(file_content)} bytes)")

        return {
            "success": True,
            "filename": filename,
            "file_url": file_url,
            "file_size": len(file_content)
        }

    except HTTPException:
        # 重新抛出HTTP异常
        raise
    except Exception as e:
        logger.error(f"上传参考图片失败: {e}")
        raise HTTPException(status_code=500, detail=f"上传失败: {str(e)}")


@router.post("/{project_id}/generate", response_model=Dict[str, Any])
async def generate_comic(
    project_id: str,
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
            project_id=project_id,
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


@router.get("/{project_id}/chapters", response_model=List[ChapterInfo])
async def get_project_chapters(
    project_id: str,
    fs: ProjectFileSystem = Depends(get_file_system)
):
    """
    获取项目章节列表
    Get project chapter list
    """
    try:
        chapters = fs.get_chapters_info(project_id)
        return chapters
    except Exception as e:
        logger.error(f"获取章节列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取章节列表失败: {str(e)}")


@router.get("/{project_id}/chapters/{chapter_id}", response_model=ChapterDetail)
async def get_chapter_detail(
    project_id: str,
    chapter_id: str,
    fs: ProjectFileSystem = Depends(get_file_system)
):
    """
    获取章节详细信息
    Get chapter detail
    """
    try:
        chapter_detail = fs.get_chapter_detail(project_id, chapter_id)
        return chapter_detail
    except Exception as e:
        logger.error(f"获取章节详情失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取章节详情失败: {str(e)}")


@router.delete("/{project_id}/chapters/{chapter_id}/panels/{panel_id}")
async def delete_chapter_panel(
    project_id: str,
    chapter_id: str,
    panel_id: int,
    fs: ProjectFileSystem = Depends(get_file_system)
):
    """
    删除章节中的特定画面
    Delete specific panel from chapter
    """
    try:
        fs.delete_chapter_panel(project_id, chapter_id, panel_id)
        return {"success": True, "message": f"画面 {panel_id} 删除成功"}
    except Exception as e:
        logger.error(f"删除画面失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除画面失败: {str(e)}")


@router.put("/{project_id}/chapters/{chapter_id}/panels/{panel_id}/confirm")
async def update_panel_confirmation(
    project_id: str,
    chapter_id: str,
    panel_id: int,
    request: PanelConfirmRequest,
    fs: ProjectFileSystem = Depends(get_file_system)
):
    """
    更新画面确认状态
    Update panel confirmation status
    """
    try:
        fs.update_panel_confirmation(project_id, chapter_id, panel_id, request.confirmed)
        return {"success": True, "message": f"画面 {panel_id} 确认状态更新为 {request.confirmed}"}
    except Exception as e:
        logger.error(f"更新画面确认状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"更新画面确认状态失败: {str(e)}")


@router.put("/{project_id}/chapters/{chapter_id}/panels/batch-confirm")
async def batch_update_panel_confirmation(
    project_id: str,
    chapter_id: str,
    request: BatchConfirmRequest,
    fs: ProjectFileSystem = Depends(get_file_system)
):
    """
    批量更新画面确认状态
    Batch update panel confirmation status
    """
    try:
        fs.batch_update_panel_confirmation(project_id, chapter_id, request.panel_ids, request.confirmed)
        return {
            "success": True,
            "message": f"批量更新 {len(request.panel_ids)} 个画面确认状态为 {request.confirmed}"
        }
    except Exception as e:
        logger.error(f"批量更新画面确认状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"批量更新画面确认状态失败: {str(e)}")


@router.post("/{project_id}/chapters/{chapter_id}/export", response_model=ChapterExportResponse)
async def export_chapter(
    project_id: str,
    chapter_id: str,
    request: ChapterExportRequest,
    fs: ProjectFileSystem = Depends(get_file_system)
):
    """
    导出章节
    Export chapter
    """
    try:
        export_result = fs.export_chapter(
            project_id, chapter_id, request.format,
            request.include_confirmed_only, request.resolution, request.quality
        )
        return ChapterExportResponse(**export_result)
    except Exception as e:
        logger.error(f"导出章节失败: {e}")
        raise HTTPException(status_code=500, detail=f"导出章节失败: {str(e)}")


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


@router.get("/{project_id}/characters")
async def get_project_characters(
    project_id: str,
    fs: ProjectFileSystem = Depends(get_file_system)
):
    """
    获取项目角色列表
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

        # 读取角色文件
        characters_file = Path(fs.projects_dir) / project_path / "characters.json"
        if characters_file.exists():
            import json
            with open(characters_file, 'r', encoding='utf-8') as f:
                characters_data = json.load(f)
                return characters_data.get("characters", [])
        else:
            return []

    except Exception as e:
        logger.error(f"获取项目角色失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取项目角色失败: {str(e)}")


# 封面生成API
@router.post("/{project_id}/generate-cover", response_model=Dict[str, Any])
async def generate_comic_cover(
    project_id: str,
    cover_type: str = Form(..., description="封面类型: project 或 chapter"),
    novel_filename: Optional[str] = Form(None, description="小说文件名（当cover_type为chapter时必需）"),
    cover_prompt: str = Form("", description="封面描述"),
    cover_size: str = Form("1024x1024", description="封面尺寸"),
    reference_image: Optional[UploadFile] = File(None, description="参考图片文件"),
    fs: ProjectFileSystem = Depends(get_file_system),
    comic_service: ComicService = Depends(get_comic_service)
):
    """
    生成漫画封面
    Generate comic cover
    """
    try:
        logger.info(f"开始生成项目 {project_id} 的封面，类型: {cover_type}")

        # 验证项目存在
        project_path = fs.get_project_path(project_id)
        if not project_path:
            raise HTTPException(status_code=404, detail="项目不存在")

        # 验证封面类型
        if cover_type not in ["project", "chapter"]:
            raise HTTPException(status_code=400, detail="封面类型必须是 'project' 或 'chapter'")

        # 如果是章节封面，验证小说文件名
        if cover_type == "chapter" and (not novel_filename or (isinstance(novel_filename, str) and novel_filename.strip() == "")):
            raise HTTPException(status_code=400, detail="章节封面需要提供小说文件名")

        # 调用封面生成服务
        from services.cover_service import CoverService
        cover_service = CoverService()

        result = await cover_service.generate_cover(
            project_id=project_id,
            cover_type=cover_type,
            novel_filename=novel_filename,
            cover_prompt=cover_prompt,
            cover_size=cover_size,
            reference_image=reference_image,
            file_system=fs,
            comic_service=comic_service
        )

        logger.info(f"封面生成完成: {result['cover_id']}")
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"生成封面失败: {e}")
        raise HTTPException(status_code=500, detail=f"生成封面失败: {str(e)}")


@router.get("/{project_id}/covers")
async def get_project_covers(
    project_id: str,
    fs: ProjectFileSystem = Depends(get_file_system)
):
    """
    获取项目封面列表
    Get project covers list
    """
    try:
        logger.info(f"获取项目 {project_id} 的封面列表")

        # 验证项目存在
        project_path = fs.get_project_path(project_id)
        if not project_path:
            raise HTTPException(status_code=404, detail="项目不存在")

        # 调用封面生成服务
        from services.cover_service import CoverService
        cover_service = CoverService()

        covers = cover_service.get_project_covers(project_id, fs)

        return {
            "success": True,
            "covers": covers
        }

    except Exception as e:
        logger.error(f"获取封面列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取封面列表失败: {str(e)}")


@router.delete("/{project_id}/covers/{cover_id}")
async def delete_cover(
    project_id: str,
    cover_id: str,
    fs: ProjectFileSystem = Depends(get_file_system)
):
    """
    删除项目封面
    Delete project cover
    """
    try:
        logger.info(f"删除项目 {project_id} 的封面 {cover_id}")

        # 验证项目存在
        project_path = fs.get_project_path(project_id)
        if not project_path:
            raise HTTPException(status_code=404, detail="项目不存在")

        # 调用封面服务
        from services.cover_service import CoverService
        cover_service = CoverService()

        result = cover_service.delete_cover(project_id, cover_id, fs)

        return {
            "success": True,
            "message": f"封面 {cover_id} 删除成功"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除封面失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除封面失败: {str(e)}")


@router.put("/{project_id}/covers/{cover_id}/set-primary")
async def set_primary_cover(
    project_id: str,
    cover_id: str,
    fs: ProjectFileSystem = Depends(get_file_system)
):
    """
    设置主要封面
    Set primary cover
    """
    try:
        logger.info(f"设置项目 {project_id} 的主要封面 {cover_id}")

        # 验证项目存在
        project_path = fs.get_project_path(project_id)
        if not project_path:
            raise HTTPException(status_code=404, detail="项目不存在")

        # 调用封面服务
        from services.cover_service import CoverService
        cover_service = CoverService()

        result = cover_service.set_primary_cover(project_id, cover_id, fs)

        return {
            "success": True,
            "message": f"封面 {cover_id} 已设置为主要封面",
            "primary_cover": result
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"设置主要封面失败: {e}")
        raise HTTPException(status_code=500, detail=f"设置主要封面失败: {str(e)}")


@router.get("/{project_id}/covers/{cover_id}")
async def get_cover_details(
    project_id: str,
    cover_id: str,
    fs: ProjectFileSystem = Depends(get_file_system)
):
    """
    获取封面详细信息
    Get cover details
    """
    try:
        logger.info(f"获取项目 {project_id} 封面 {cover_id} 的详细信息")

        # 验证项目存在
        project_path = fs.get_project_path(project_id)
        if not project_path:
            raise HTTPException(status_code=404, detail="项目不存在")

        # 调用封面服务
        from services.cover_service import CoverService
        cover_service = CoverService()

        cover = await cover_service.get_cover_details(project_id, cover_id, fs)

        if not cover:
            raise HTTPException(status_code=404, detail="封面不存在")

        return {
            "success": True,
            "cover": cover
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取封面详情失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取封面详情失败: {str(e)}")