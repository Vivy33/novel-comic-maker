"""
工作流API路由
Workflow API Routes

提供LangGraph工作流相关的API接口
Provides API interfaces for LangGraph workflow operations
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)

# 尝试导入依赖的工作流模块，失败则降级
try:
    from ..workflows.text_compression import TextCompressionWorkflow
    from ..workflows.feedback_handler import FeedbackWorkflow
    WORKFLOWS_AVAILABLE = True
except Exception as e:
    WORKFLOWS_AVAILABLE = False
    TextCompressionWorkflow = None
    FeedbackWorkflow = None
    logger.warning(f"工作流模块不可用，已降级加载：{e}")

# 尝试导入混合编排器，失败则降级
try:
    from ..services.hybrid_orchestrator import hybrid_orchestrator
    HYBRID_AVAILABLE = True
except Exception as e:
    HYBRID_AVAILABLE = False
    hybrid_orchestrator = None
    logger.warning(f"混合编排器不可用，相关接口将返回 503：{e}")

# 批处理器始终尝试导入（该模块内部已做动态依赖处理）
from ..services.batch_processor import batch_processor

# 创建路由器
router = APIRouter(prefix="/workflows", tags=["workflows"])

# 全局工作流实例（若依赖不可用则为 None）
text_compression_workflow = TextCompressionWorkflow() if WORKFLOWS_AVAILABLE else None
feedback_workflow = FeedbackWorkflow() if WORKFLOWS_AVAILABLE else None

# 添加按需初始化方法，避免因早期导入失败导致的永久不可用标志
def ensure_workflows_initialized() -> bool:
    """按需导入并初始化工作流模块与实例"""
    global WORKFLOWS_AVAILABLE, TextCompressionWorkflow, FeedbackWorkflow, text_compression_workflow, feedback_workflow
    if WORKFLOWS_AVAILABLE and text_compression_workflow and feedback_workflow:
        return True
    try:
        if TextCompressionWorkflow is None or FeedbackWorkflow is None:
            from ..workflows.text_compression import TextCompressionWorkflow as _TCW
            from ..workflows.feedback_handler import FeedbackWorkflow as _FW
            TextCompressionWorkflow = _TCW
            FeedbackWorkflow = _FW
        if text_compression_workflow is None:
            text_compression_workflow = TextCompressionWorkflow()
        if feedback_workflow is None:
            feedback_workflow = FeedbackWorkflow()
        WORKFLOWS_AVAILABLE = True
        return True
    except Exception as e:
        logger.warning(f"工作流模块初始化失败：{e}")
        WORKFLOWS_AVAILABLE = False
        text_compression_workflow = None
        feedback_workflow = None
        return False


def ensure_hybrid_initialized() -> bool:
    """按需导入并初始化混合编排器"""
    global HYBRID_AVAILABLE, hybrid_orchestrator
    if HYBRID_AVAILABLE and hybrid_orchestrator is not None:
        return True
    try:
        from ..services.hybrid_orchestrator import hybrid_orchestrator as _HO
        hybrid_orchestrator = _HO
        HYBRID_AVAILABLE = True
        return True
    except Exception as e:
        logger.warning(f"混合编排器初始化失败：{e}")
        HYBRID_AVAILABLE = False
        hybrid_orchestrator = None
        return False


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
    options: Optional[Dict[str, Any]] = None


@router.post("/text-compression/start")
async def start_text_compression(request: TextCompressionRequest):
    """
    启动文本压缩工作流
    Start text compression workflow
    """
    try:
        ensure_workflows_initialized()
        if not WORKFLOWS_AVAILABLE or text_compression_workflow is None:
            raise HTTPException(status_code=503, detail="文本压缩工作流不可用：依赖未安装或初始化失败")

        if not request.text or len(request.text.strip()) < 100:
            raise HTTPException(status_code=400, detail="文本长度至少需要100个字符")

        logger.info(f"启动文本压缩工作流，文本长度: {len(request.text)}")

        # 运行压缩工作流
        result = await text_compression_workflow.run_compression(
            request.text, request.workflow_id
        )

        return {
            "success": True,
            "workflow_id": result["workflow_id"],
            "status": result["status"],
            "original_length": len(request.text),
            "compressed_length": len(result.get("compressed_text", "")),
            "compression_ratio": len(result.get("compressed_text", "")) / len(request.text) if request.text else 0,
            "quality_scores": result.get("quality_scores", {}),
            "final_result": result.get("final_result"),
            "compression_history": result.get("compression_history", [])
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"文本压缩工作流启动失败: {e}")
        raise HTTPException(status_code=500, detail=f"文本压缩失败: {str(e)}")


@router.post("/feedback/handle")
async def handle_feedback(request: FeedbackRequest):
    """
    处理用户反馈
    Handle user feedback
    """
    try:
        ensure_workflows_initialized()
        if not WORKFLOWS_AVAILABLE or feedback_workflow is None:
            raise HTTPException(status_code=503, detail="反馈处理工作流不可用：依赖未安装或初始化失败")

        if not request.feedback_text or len(request.feedback_text.strip()) < 10:
            raise HTTPException(status_code=400, detail="反馈内容至少需要10个字符")

        logger.info(f"处理用户反馈: {request.feedback_text[:100]}...")

        # 运行反馈处理工作流
        result = await feedback_workflow.handle_feedback(
            request.feedback_text,
            request.feedback_type,
            request.context,
            request.workflow_id
        )

        return {
            "success": True,
            "workflow_id": result["workflow_id"],
            "status": result["status"],
            "feedback_type": result.get("feedback_type"),
            "action_decision": result.get("action_decision"),
            "action_result": result.get("action_result"),
            "final_result": result.get("final_result")
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"反馈处理失败: {e}")
        raise HTTPException(status_code=500, detail=f"反馈处理失败: {str(e)}")


@router.post("/batch/create-job")
async def create_batch_job(request: BatchJobRequest):
    """
    创建批处理作业
    Create batch processing job
    """
    try:
        if not request.tasks:
            raise HTTPException(status_code=400, detail="任务列表不能为空")

        if len(request.tasks) > 100:
            raise HTTPException(status_code=400, detail="任务数量不能超过100个")

        logger.info(f"创建批处理作业: {request.job_name}, {len(request.tasks)} 个任务")

        job_id = await batch_processor.create_batch_job(
            request.job_name,
            request.tasks,
            request.max_concurrent_tasks
        )

        return {
            "success": True,
            "job_id": job_id,
            "job_name": request.job_name,
            "total_tasks": len(request.tasks),
            "max_concurrent_tasks": request.max_concurrent_tasks,
            "status": "created"
        }

    except Exception as e:
        logger.error(f"创建批处理作业失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建作业失败: {str(e)}")


@router.post("/batch/{job_id}/execute")
async def execute_batch_job(job_id: str):
    """
    执行批处理作业
    Execute batch processing job
    """
    try:
        logger.info(f"执行批处理作业: {job_id}")

        # 定义进度回调
        def progress_callback(job_id: str, progress: float, completed: int, failed: int):
            logger.info(f"作业进度 {job_id}: {progress:.1%} ({completed}/{completed + failed})")

        result = await batch_processor.execute_batch_job(job_id, progress_callback)

        return {
            "success": True,
            "job_result": result
        }

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"执行批处理作业失败: {e}")
        raise HTTPException(status_code=500, detail=f"执行作业失败: {str(e)}")


@router.get("/batch/{job_id}/status")
async def get_batch_job_status(job_id: str):
    """
    获取批处理作业状态
    Get batch processing job status
    """
    try:
        status = batch_processor.get_job_status(job_id)

        if not status:
            raise HTTPException(status_code=404, detail="作业不存在")

        return {
            "success": True,
            "job_status": status
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取作业状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取状态失败: {str(e)}")


@router.post("/batch/{job_id}/cancel")
async def cancel_batch_job(job_id: str):
    """
    取消批处理作业
    Cancel batch processing job
    """
    try:
        success = batch_processor.cancel_job(job_id)

        if not success:
            raise HTTPException(status_code=404, detail="作业不存在或无法取消")

        return {
            "success": True,
            "message": "作业已取消"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"取消作业失败: {e}")
        raise HTTPException(status_code=500, detail=f"取消作业失败: {str(e)}")


@router.post("/comic-generation/start")
async def start_comic_generation(request: ComicGenerationRequest, background_tasks: BackgroundTasks):
    """
    启动完整漫画生成流水线
    Start complete comic generation pipeline
    """
    try:
        ensure_hybrid_initialized()
        if not HYBRID_AVAILABLE or hybrid_orchestrator is None:
            raise HTTPException(status_code=503, detail="漫画生成流水线不可用：依赖未安装或初始化失败")

        if not request.novel_text or len(request.novel_text.strip()) < 500:
            raise HTTPException(status_code=400, detail="小说文本至少需要500个字符")

        if not request.project_name or len(request.project_name.strip()) < 1:
            raise HTTPException(status_code=400, detail="项目名称不能为空")

        logger.info(f"启动漫画生成流水线: {request.project_name}")

        # 在后台运行完整的生成流程
        background_tasks.add_task(
            hybrid_orchestrator.generate_comic_pipeline,
            request.novel_text,
            request.project_name,
            request.options
        )

        return {
            "success": True,
            "message": "漫画生成流水线已启动",
            "project_name": request.project_name,
            "text_length": len(request.novel_text),
            "options": request.options or {}
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"启动漫画生成流水线失败: {e}")
        raise HTTPException(status_code=500, detail=f"启动生成失败: {str(e)}")


@router.post("/projects/{project_name}/feedback")
async def handle_project_feedback(project_name: str, request: FeedbackRequest):
    """
    处理项目相关的用户反馈
    Handle project-related user feedback
    """
    try:
        ensure_hybrid_initialized()
        if not HYBRID_AVAILABLE or hybrid_orchestrator is None:
            raise HTTPException(status_code=503, detail="反馈接口不可用：依赖未安装或初始化失败")

        if not request.feedback_text or len(request.feedback_text.strip()) < 10:
            raise HTTPException(status_code=400, detail="反馈内容至少需要10个字符")

        logger.info(f"处理项目反馈: {project_name}")

        result = await hybrid_orchestrator.handle_user_feedback(
            project_name, request.feedback_text, request.feedback_type
        )

        return {
            "success": True,
            "project_name": project_name,
            "feedback_result": result
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"处理项目反馈失败: {e}")
        raise HTTPException(status_code=500, detail=f"处理反馈失败: {str(e)}")


@router.get("/workflows/status")
async def get_workflows_status():
    """
    获取所有工作流状态
    Get all workflows status
    """
    try:
        # 动态确认可用性
        ensure_workflows_initialized()
        ensure_hybrid_initialized()

        # 获取活跃的批处理作业
        active_jobs = {}
        for job_id, job in batch_processor.active_jobs.items():
            active_jobs[job_id] = {
                'job_name': job.job_name,
                'status': job.status.value,
                'total_tasks': job.total_tasks,
                'completed_tasks': job.completed_tasks,
                'failed_tasks': job.failed_tasks,
                'progress': job.completed_tasks / job.total_tasks if job.total_tasks > 0 else 0
            }

        return {
            "success": True,
            "active_batch_jobs": active_jobs,
            "total_active_jobs": len(active_jobs),
            "system_status": "healthy",
            "workflows_available": WORKFLOWS_AVAILABLE,
            "hybrid_available": HYBRID_AVAILABLE
        }

    except Exception as e:
        logger.error(f"获取工作流状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取状态失败: {str(e)}")


@router.post("/system/cleanup")
async def cleanup_completed_jobs(max_age_hours: int = 24):
    """
    清理已完成的作业
    Cleanup completed jobs
    """
    try:
        batch_processor.cleanup_completed_jobs(max_age_hours)

        return {
            "success": True,
            "message": f"已清理超过 {max_age_hours} 小时的已完成作业"
        }

    except Exception as e:
        logger.error(f"清理作业失败: {e}")
        raise HTTPException(status_code=500, detail=f"清理失败: {str(e)}")


@router.get("/system/health")
async def get_system_health():
    """
    获取系统健康状态
    Get system health status
    """
    try:
        # 动态确认可用性
        ensure_workflows_initialized()
        ensure_hybrid_initialized()

        # 统计活跃作业
        total_active_jobs = len(batch_processor.active_jobs)
        running_jobs = sum(1 for job in batch_processor.active_jobs.values() if job.status.value == "running")
        completed_jobs = sum(1 for job in batch_processor.active_jobs.values() if job.status.value == "completed")
        failed_jobs = sum(1 for job in batch_processor.active_jobs.values() if job.status.value == "failed")

        return {
            "success": True,
            "system_status": "healthy",
            "active_jobs": {
                "total": total_active_jobs,
                "running": running_jobs,
                "completed": completed_jobs,
                "failed": failed_jobs
            },
            "available_task_handlers": list(batch_processor.task_handlers.keys()),
            "max_workers": batch_processor.max_workers,
            "workflows_available": WORKFLOWS_AVAILABLE,
            "hybrid_available": HYBRID_AVAILABLE,
            "timestamp": "2024-01-01T00:00:00Z"
        }

    except Exception as e:
        logger.error(f"获取系统健康状态失败: {e}")
        return {
            "success": False,
            "system_status": "error",
            "error": str(e)
        }