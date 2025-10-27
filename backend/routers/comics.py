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
    PanelConfirmRequest, BatchConfirmRequest, ChapterExportRequest, ChapterExportResponse,
    CoverInfo, ProjectCoversResponse, ChapterCreateRequest
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
    Get project list
    """
    try:
        # 获取原始章节信息
        raw_chapters = fs.get_chapters_info(project_id)

        # 识别需要合并的章节 (chapter_001 到 chapter_005 合并为第1章)
        merged_chapters = []
        chapter_groups = {}

        for chapter in raw_chapters:
            # 检查是否是需要合并的章节 (chapter_001-005)
            if chapter.chapter_id.startswith("chapter_00") and chapter.chapter_id <= "chapter_005":
                # 这是第1章的部分，添加到第1章组
                if "main_chapter" not in chapter_groups:
                    chapter_groups["main_chapter"] = {
                        "chapter_id": "chapter_001",
                        "title": "第1章",
                        "created_at": chapter.created_at,
                        "updated_at": chapter.updated_at,
                        "status": "completed",  # 如果任一部分是completed，整体标记为completed
                        "total_panels": 0,
                        "confirmed_panels": 0,
                        "unconfirmed_panels": 0,
                        "chapter_number": 1,
                        "cover_image_path": chapter.cover_image_path,
                        "cover_thumbnail_url": chapter.cover_thumbnail_url,
                        "completion_percentage": 0.0,
                        "has_unconfirmed_panels": None,
                        "source_chapters": []  # 记录原始章节ID
                    }

                # 合并统计信息
                group = chapter_groups["main_chapter"]
                group["total_panels"] += chapter.total_panels
                group["confirmed_panels"] += chapter.confirmed_panels
                group["unconfirmed_panels"] += chapter.unconfirmed_panels
                group["source_chapters"].append(chapter.chapter_id)

                # 更新状态和更新时间
                if chapter.status == "completed":
                    group["status"] = "completed"
                if chapter.updated_at > group["updated_at"]:
                    group["updated_at"] = chapter.updated_at
                if chapter.created_at < group["created_at"]:
                    group["created_at"] = chapter.created_at

                # 使用最早创建章节的标题（如果有的话）
                if chapter.title and not group["title"]:
                    group["title"] = chapter.title
            else:
                # 其他章节正常添加
                merged_chapters.append(chapter)

        # 添加合并后的主章节
        if "main_chapter" in chapter_groups:
            # 将字典转换为ChapterInfo对象
            from models.comic import ChapterInfo
            main_chapter_dict = chapter_groups["main_chapter"]
            main_chapter = ChapterInfo(**main_chapter_dict)
            merged_chapters.append(main_chapter)
            # 按章节编号排序
            merged_chapters.sort(key=lambda x: x.chapter_number)
        else:
            # 如果没有需要合并的章节，按原样排序
            merged_chapters = raw_chapters
            merged_chapters.sort(key=lambda x: x.chapter_number)

        logger.info(f"返回 {len(merged_chapters)} 个章节的信息（合并后）")
        return merged_chapters
    except Exception as e:
        logger.error(f"获取章节列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取章节列表失败: {str(e)}")


@router.post("/{project_id}/chapters", response_model=Dict[str, Any])
async def create_chapter(
    project_id: str,
    request: ChapterCreateRequest,
    fs: ProjectFileSystem = Depends(get_file_system)
):
    """
    创建新章节
    Create new chapter
    """
    try:
        logger.info(f"为项目 {project_id} 创建新章节，标题: {request.title}")

        # 验证项目存在
        project_path = fs.get_project_path(project_id)
        if not project_path:
            raise HTTPException(status_code=404, detail="项目不存在")

        # 使用智能章节编号系统
        from agents.image_generator import ImageGenerator
        image_gen = ImageGenerator()

        if request.chapter_number is None:
            # 自动分配下一个章节编号
            chapter_number = image_gen._get_next_chapter_number(str(project_path))
        else:
            chapter_number = request.chapter_number

        chapter_dir = image_gen._get_chapter_dir_name(str(project_path), chapter_number)

        # 创建章节目录结构
        chapters_path = project_path / "chapters"
        chapter_path = chapters_path / chapter_dir
        chapter_path.mkdir(parents=True, exist_ok=True)

        # 创建子目录
        (chapter_path / "images").mkdir(exist_ok=True)
        (chapter_path / "metadata").mkdir(exist_ok=True)

        # 创建章节信息文件
        chapter_info = {
            "chapter_id": chapter_dir,
            "title": f"第{chapter_number}章 - {request.title}" if request.title != "新章节" else f"第{chapter_number}章",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "status": "pending",
            "total_panels": 0,
            "confirmed_panels": 0,
            "unconfirmed_panels": 0,
            "chapter_number": chapter_number
        }

        import json
        with open(chapter_path / "chapter_info.json", "w", encoding="utf-8") as f:
            json.dump(chapter_info, f, ensure_ascii=False, indent=2)

        logger.info(f"成功创建章节: {chapter_dir} - {chapter_info['title']}")

        return {
            "success": True,
            "chapter": chapter_info,
            "message": f"章节 {chapter_info['title']} 创建成功"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建章节失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建章节失败: {str(e)}")


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
    except FileNotFoundError as e:
        logger.error(f"项目不存在: {e}")
        raise HTTPException(status_code=404, detail=f"项目不存在")
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
        logger.info(f"从服务层获取到 {len(covers)} 个封面")

        # 分离项目封面和章节封面
        primary_cover = None
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

            # 获取文件大小（如果本地文件存在）
            file_size = cover.get("file_size", 0)
            if file_size == 0 and image_path and image_path.startswith("/"):
                try:
                    import os
                    if os.path.exists(image_path):
                        file_size = os.path.getsize(image_path)
                except Exception:
                    file_size = 0

            cover_info = CoverInfo(
                cover_id=cover["cover_id"],
                cover_type=cover["cover_type"],
                title=cover.get("title"),
                description=cover.get("description"),
                image_path=image_path,
                thumbnail_url=thumbnail_url,
                is_primary=cover.get("is_primary", False),
                created_at=cover["created_at"],
                file_size=file_size
            )

            if cover.get("cover_type") == "project":
                if cover.get("is_primary", False):
                    primary_cover = cover_info
                # 如果没有设置主封面，使用第一个项目封面
                elif primary_cover is None:
                    primary_cover = cover_info
            elif cover.get("cover_type") == "chapter":
                chapter_covers.append(cover_info)
        
        logger.info(f"封面数据处理完成: primary_cover={primary_cover}, chapter_covers_count={len(chapter_covers)}")

        response_data = ProjectCoversResponse(
            project_id=project_id,
            primary_cover=primary_cover,
            chapter_covers=chapter_covers,
            total_covers=len(covers)
        )
        logger.info(f"准备返回封面数据: {response_data.dict()}")
        return response_data

    except FileNotFoundError as e:
        logger.error(f"项目不存在: {e}")
        raise HTTPException(status_code=404, detail=f"项目不存在")
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
    except FileNotFoundError as e:
        logger.error(f"项目不存在: {e}")
        raise HTTPException(status_code=404, detail=f"项目不存在")
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
    except FileNotFoundError as e:
        logger.error(f"项目不存在: {e}")
        raise HTTPException(status_code=404, detail=f"项目不存在")
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
    except FileNotFoundError as e:
        logger.error(f"项目不存在: {e}")
        raise HTTPException(status_code=404, detail=f"项目不存在")
    except Exception as e:
        logger.error(f"获取封面详情失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取封面详情失败: {str(e)}")


@router.delete("/{project_id}/covers/{cover_id}")
async def delete_cover(
    project_id: str,
    cover_id: str,
    fs: ProjectFileSystem = Depends(get_file_system)
):
    """
    删除封面
    Delete cover
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

        success = await cover_service.delete_cover(project_id, cover_id, fs)

        if success:
            return {
                "success": True,
                "message": f"封面 {cover_id} 删除成功"
            }
        else:
            raise HTTPException(status_code=404, detail="封面不存在")

    except HTTPException:
        raise
    except FileNotFoundError as e:
        logger.error(f"项目不存在: {e}")
        raise HTTPException(status_code=404, detail=f"项目不存在")
    except Exception as e:
        logger.error(f"删除封面失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除封面失败: {str(e)}")
