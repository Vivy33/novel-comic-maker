"""
工作流API路由
Workflow API Routes

提供工作流相关的API接口，主要用于启动漫画生成流程
Provides API interfaces for workflow operations, mainly for starting comic generation
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# 简化版本：直接使用comics服务，不依赖复杂的LangGraph工作流
from services.comic_service import ComicService
from services.file_system import ProjectFileSystem

# 批处理器始终尝试导入（该模块内部已做动态依赖处理）
try:
    from services.batch_processor import batch_processor
    BATCH_AVAILABLE = True
except Exception as e:
    BATCH_AVAILABLE = False
    batch_processor = None
    logger.warning(f"批处理器不可用：{e}")

# 创建路由器
router = APIRouter(prefix="/workflows", tags=["workflows"])

# 简化版本：只保留基本功能，不使用复杂的工作流系统


class TextCompressionRequest(BaseModel):
    """文本压缩请求模型"""
    text: str
    workflow_id: Optional[str] = None
    max_retries: int = 3


class FeedbackRequest(BaseModel):
    """反馈处理请求模型"""
    feedback_text: str
    feedback_type: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    workflow_id: Optional[str] = None


class BatchJobRequest(BaseModel):
    """批处理作业请求模型"""
    job_name: str
    tasks: List[Dict[str, Any]]
    max_concurrent_tasks: int = 5


class ComicGenerationRequest(BaseModel):
    """漫画生成请求模型"""
    novel_text: str
    project_name: str
    workflow_type: Optional[str] = "comic_generation"
    options: Optional[Dict[str, Any]] = None
    # 简化后的参数，只保留有效配置
    reference_images: Optional[List[str]] = []
    style_requirements: Optional[str] = ""


class TextSegmentationRequest(BaseModel):
    """文本分段请求模型 - 漫画导向版本"""
    novel_content: str
    project_name: str
    target_length: str = "medium"  # small(200字), medium(300字), large(500字)
    preserve_context: bool = True
    language: str = "chinese"     # chinese/english


class SegmentGenerationRequest(BaseModel):
    """段落生成请求模型"""
    project_name: str
    segment_index: int
    segment_text: str
    style_reference_images: Optional[List[str]] = []
    selected_characters: Optional[List[str]] = []
    style_requirements: Optional[str] = ""
    generation_count: int = 3
    previous_segment_image: Optional[str] = None  # 前情提要图片


@router.post("/text-compression/start")
async def start_text_compression(request: TextCompressionRequest):
    """
    简化版文本压缩（占位符）
    Simplified text compression (placeholder)
    """
    # 暂时返回占位响应
    return {
        "success": False,
        "message": "文本压缩功能暂时不可用",
        "reason": "依赖的LangGraph模块未安装"
    }


@router.post("/feedback/handle")
async def handle_feedback(request: FeedbackRequest):
    """
    简化版反馈处理（占位符）
    Simplified feedback handling (placeholder)
    """
    # 暂时返回占位响应
    return {
        "success": False,
        "message": "反馈处理功能暂时不可用",
        "reason": "依赖的LangGraph模块未安装"
    }


@router.post("/batch/create-job")
async def create_batch_job(request: BatchJobRequest):
    """
    简化版批处理作业创建（占位符）
    Simplified batch job creation (placeholder)
    """
    if not BATCH_AVAILABLE:
        return {
            "success": False,
            "message": "批处理功能暂时不可用",
            "reason": "批处理器未正确初始化"
        }

    # 占位符实现
    return {
        "success": False,
        "message": "批处理功能暂时不可用",
        "reason": "功能正在开发中"
    }


@router.post("/batch/{job_id}/execute")
async def execute_batch_job(job_id: str):
    """
    简化版批处理作业执行（占位符）
    Simplified batch job execution (placeholder)
    """
    return {
        "success": False,
        "message": "批处理执行功能暂时不可用"
    }


@router.get("/batch/{job_id}/status")
async def get_batch_job_status(job_id: str):
    """
    简化版批处理作业状态（占位符）
    Simplified batch job status (placeholder)
    """
    return {
        "success": False,
        "message": "批处理状态查询功能暂时不可用"
    }


@router.post("/batch/{job_id}/cancel")
async def cancel_batch_job(job_id: str):
    """
    简化版批处理作业取消（占位符）
    Simplified batch job cancellation (placeholder)
    """
    return {
        "success": False,
        "message": "批处理取消功能暂时不可用"
    }


@router.post("/segment-and-preview")
async def segment_and_preview_novel(request: TextSegmentationRequest):
    """
    文本分段并预览第一段
    Segment text and preview first segment
    """
    try:
        if not request.novel_content.strip():
            raise HTTPException(status_code=400, detail="小说内容不能为空")

        if not request.project_name:
            raise HTTPException(status_code=400, detail="项目名称不能为空")

        # 使用现有的TextSegmenter进行分段
        from agents.text_segmenter import TextSegmenter

        text_segmenter = TextSegmenter()
        segments = await text_segmenter.segment_text(
            text=request.novel_content,
            target_length=request.target_length,
            preserve_context=request.preserve_context,
            language=request.language
        )

        if not segments:
            raise HTTPException(status_code=500, detail="文本分段失败")

        # 保存分段状态到项目文件系统
        from services.file_system import ProjectFileSystem
        fs = ProjectFileSystem()
        project_path = fs._resolve_project_path(request.project_name)

        # 创建分段状态文件
        segmentation_state = {
            "project_name": request.project_name,
            "total_segments": len(segments),
            "current_segment_index": 0,
            "completed_segments": [],
            "segments": segments,
            "created_at": datetime.now().isoformat()
        }

        fs.save_history(str(project_path), "segmentation", segmentation_state)

        return {
            "success": True,
            "message": f"文本成功分段为 {len(segments)} 个段落",
            "total_segments": len(segments),
            "segments": segments,
            "first_segment": segments[0] if segments else None,
            "project_name": request.project_name
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"文本分段失败: {e}")
        raise HTTPException(status_code=500, detail=f"文本分段失败: {str(e)}")


@router.post("/generate-segment")
async def generate_segment_comics(request: SegmentGenerationRequest):
    """
    为单个段落生成漫画组图
    Generate comic panels for a single segment
    """
    try:
        if not request.segment_text.strip():
            raise HTTPException(status_code=400, detail="段落文本不能为空")

        if not request.project_name:
            raise HTTPException(status_code=400, detail="项目名称不能为空")

        # 构建生成配置
        from services.comic_service import ComicService
        comic_service = ComicService()

        # 创建漫画脚本
        script_config = {
            "segment_text": request.segment_text,
            "segment_index": request.segment_index,
            "style_reference_images": request.style_reference_images or [],
            "selected_characters": request.selected_characters or [],
            "style_requirements": request.style_requirements or "",
            "previous_segment_image": request.previous_segment_image,
            "generation_count": request.generation_count
        }

        # 使用ImageGenerator生成组图
        from agents.image_generator import ImageGenerator
        from services.file_system import ProjectFileSystem

        fs = ProjectFileSystem()
        project_path = fs._resolve_project_path(request.project_name)

        image_generator = ImageGenerator()

        # 获取结构化场景分析数据
        structured_scene_data = None
        try:
            # 从项目历史中获取分段分析结果
            timeline = fs.get_project_timeline(str(project_path))
            for event in reversed(timeline):
                if event.get("type") == "segmentation" and event.get("data"):
                    segmentation_data = event["data"]
                    segments = segmentation_data.get("segments", [])

                    # 找到对应段落的详细分析数据
                    if 0 <= request.segment_index < len(segments):
                        structured_scene_data = segments[request.segment_index]
                        logger.info(f"找到段落 {request.segment_index} 的结构化数据: {list(structured_scene_data.keys()) if structured_scene_data else 'None'}")
                        break
        except Exception as e:
            logger.warning(f"获取结构化场景数据失败，使用原始文本: {e}")

        # 构建漫画脚本（包含结构化数据）
        # 确保前情提要路径是字符串类型，避免PosixPath错误
        previous_context = None
        if request.previous_segment_image:
            previous_context = str(request.previous_segment_image)
            logger.info(f"前情提要路径转换为字符串: {previous_context}")

        comic_script = {
            "scene_description": request.segment_text,
            "structured_data": structured_scene_data,  # 添加结构化数据
            "characters": request.selected_characters or [],
            "style_requirements": request.style_requirements or "",
            "reference_images": request.style_reference_images or [],
            "previous_context": previous_context
        }

        
        # 生成组图
        generation_result = await image_generator.generate_images_for_script(
            script=comic_script,
            project_path=project_path,
            max_images=request.generation_count,
            segment_index=request.segment_index
        )

        # 更新分段状态
        segmentation_state = fs.get_project_timeline(str(project_path))[-1]  # 获取最新的分段状态
        if segmentation_state and segmentation_state.get("type") == "segmentation":
            segmentation_state["current_segment_index"] = request.segment_index
            fs.save_history(str(project_path), "segment_generation", {
                "segment_index": request.segment_index,
                "generation_result": generation_result,
                "config": script_config,
                "timestamp": datetime.now().isoformat()
            })

        return {
            "success": True,
            "message": f"段落 {request.segment_index + 1} 的组图生成完成",
            "segment_index": request.segment_index,
            "generation_result": generation_result,
            "total_generated": len(generation_result.get("generated_images", [])),
            "project_name": request.project_name
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"段落组图生成失败: {e}")
        raise HTTPException(status_code=500, detail=f"段落组图生成失败: {str(e)}")


class SegmentConfirmationRequest(BaseModel):
    """段落确认请求模型"""
    project_name: str
    segment_index: int
    selected_image_index: int


@router.post("/confirm-segment")
async def confirm_segment_selection(request: SegmentConfirmationRequest):
    """
    确认段落选择的图片，进入下一段
    Confirm selected image for segment and move to next
    """
    try:
        logger.info(f"开始处理段落确认请求 - 项目: {request.project_name}, 段落: {request.segment_index}, 选择图片: {request.selected_image_index}")

        if not request.project_name:
            raise HTTPException(status_code=400, detail="项目名称不能为空")

        # 更新分段状态
        from services.file_system import ProjectFileSystem
        fs = ProjectFileSystem()
        project_path = fs._resolve_project_path(request.project_name)

        # 保存用户选择
        confirmation_data = {
            "segment_index": request.segment_index,
            "selected_image_index": request.selected_image_index,
            "confirmed_at": datetime.now().isoformat()
        }

        fs.save_history(str(project_path), "segment_confirmation", confirmation_data)

        # 检查是否还有下一段
        segmentation_state = None
        for event in reversed(fs.get_project_timeline(str(project_path))):
            if event.get("type") == "segmentation":
                segmentation_state = event.get("data", {})
                break

        if not segmentation_state:
            raise HTTPException(status_code=404, detail="未找到分段状态")

        total_segments = segmentation_state.get("total_segments", 0)
        next_segment_index = request.segment_index + 1

        # 获取确认的图片路径作为下一段的前情提要
        selected_image_path = None
        # 确保project_path是字符串类型，避免PosixPath错误
        project_path_str = str(project_path)
        logger.info(f"处理项目路径: {project_path_str}")

        # 从最新的segment_generation历史记录中获取选择的图片路径
        for event in reversed(fs.get_project_timeline(str(project_path))):
            if (event.get("type") == "segment_generation" and
                event.get("data", {}).get("segment_index") == request.segment_index):
                generation_result = event.get("data", {}).get("generation_result", {})
                generated_images = generation_result.get("generated_images", [])
                # 根据用户选择的索引获取对应的图片路径
                if (0 <= request.selected_image_index < len(generated_images)):
                    selected_image = generated_images[request.selected_image_index]
                    # 优先使用本地路径，如果没有则使用远程URL
                    local_path = selected_image.get("local_path")
                    remote_url = selected_image.get("image_url")

                    # 确保路径是字符串类型
                    if local_path:
                        local_path = str(local_path)
                        logger.info(f"本地路径转换为字符串: {local_path}")
                    if remote_url:
                        remote_url = str(remote_url)
                        logger.info(f"远程URL转换为字符串: {remote_url}")

                    # 如果是本地路径，转换为相对于projects根目录的路径
                    if local_path and str(fs.projects_dir) in local_path:
                        # 提取相对于projects根目录的路径（包含项目名）
                        relative_to_projects = local_path.replace(str(fs.projects_dir) + "/", "")
                        selected_image_path = "/projects/" + relative_to_projects
                        logger.info(f"转换本地路径为相对路径: {local_path} -> {selected_image_path}")
                    elif remote_url:
                        # 使用远程URL
                        selected_image_path = remote_url
                        logger.info(f"使用远程URL: {remote_url}")
                    else:
                        logger.warning(f"无法获取确认图片路径，本地路径: {local_path}, 远程URL: {remote_url}")
                        selected_image_path = None
                break

        logger.info(f"段落确认成功 - 段落: {request.segment_index + 1}, 确认图片路径: {selected_image_path}, 有下一段: {next_segment_index < total_segments} [FIXED]")

        return {
            "success": True,
            "message": f"段落 {request.segment_index + 1} 已确认",
            "segment_index": request.segment_index,
            "selected_image_index": request.selected_image_index,
            "has_next_segment": next_segment_index < total_segments,
            "next_segment_index": next_segment_index if next_segment_index < total_segments else None,
            "confirmed_image_path": selected_image_path,
            "project_name": request.project_name
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"确认段落选择失败 - 项目: {request.project_name}, 段落: {request.segment_index}, 错误: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"确认段落选择失败: {str(e)}")




@router.get("/workflows/status")
async def get_workflows_status():
    """
    获取简化版工作流状态
    Get simplified workflows status
    """
    return {
        "success": True,
        "active_batch_jobs": {},
        "total_active_jobs": 0,
        "system_status": "healthy",
        "workflows_available": False,  # LangGraph模块不可用
        "hybrid_available": False,    # 混合编排器不可用
        "batch_available": BATCH_AVAILABLE
    }


@router.post("/system/cleanup")
async def cleanup_completed_jobs(max_age_hours: int = 24):
    """
    清理已完成的作业（占位符）
    Cleanup completed jobs (placeholder)
    """
    return {
        "success": False,
        "message": "清理功能暂时不可用"
    }


@router.get("/system/health")
async def get_system_health():
    """
    获取系统健康状态
    Get system health status
    """
    return {
        "success": True,
        "system_status": "healthy",
        "active_jobs": {
            "total": 0,
            "running": 0,
            "completed": 0,
            "failed": 0
        },
        "available_task_handlers": [],
        "max_workers": 0,
        "workflows_available": False,
        "hybrid_available": False,
        "batch_available": BATCH_AVAILABLE,
        "timestamp": "2025-01-01T00:00:00Z"
    }


@router.post("/start")
async def start_workflow(request: ComicGenerationRequest):
    """
    通用工作流启动端点
    Universal workflow start endpoint
    """
    try:
        workflow_type = request.workflow_type or "comic_generation"

        if workflow_type == "comic_generation":
            # 直接调用漫画生成服务
            return await start_comic_generation_workflow(request)
        else:
            # 其他工作流类型暂时不支持
            raise HTTPException(status_code=400, detail=f"不支持的工作流类型: {workflow_type}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"启动工作流失败: {e}")
        raise HTTPException(status_code=500, detail=f"启动工作流失败: {str(e)}")


async def start_comic_generation_workflow(request: ComicGenerationRequest):
    """
    启动漫画生成工作流 - 使用comics API
    Start comic generation workflow - using comics API
    """
    if not request.project_name:
        raise HTTPException(status_code=400, detail="项目名称不能为空")

    # 创建文件系统和服务实例
    fs = ProjectFileSystem()
    comic_service = ComicService()

    try:
        # 首先创建项目（如果需要）
        project_id = request.project_name  # 简化：使用项目名称作为ID

        # 构建简化的生成配置
        generation_config = {
            "reference_images": request.reference_images or [],
            "style_requirements": request.style_requirements or "",
            # 保留原有的 options 配置作为兼容性支持
            **(request.options or {})
        }

        # 启动异步漫画生成任务
        task_id = await comic_service.start_comic_generation(
            project_id=project_id,
            generation_config=generation_config
        )

        return {
            "workflow_id": task_id,
            "status": "started",
            "message": "漫画生成工作流已启动",
            "project_id": project_id,
            "task_id": task_id
        }
    except Exception as e:
        logger.error(f"启动漫画生成工作流失败: {e}")
        raise HTTPException(status_code=500, detail=f"启动漫画生成失败: {str(e)}")