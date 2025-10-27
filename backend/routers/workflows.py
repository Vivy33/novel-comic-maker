"""
工作流API路由
Workflow API Routes

提供工作流相关的API接口，主要用于启动漫画生成流程
Provides API interfaces for workflow operations, mainly for starting comic generation
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import logging
from datetime import datetime
import os

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
    previous_segment_text: Optional[str] = None   # 前情提要文本


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
    文本分段并预览第一段 - 100% AI分段，无降级
    Segment text and preview first segment - 100% AI segmentation, no fallback
    """
    try:
        if not request.novel_content.strip():
            raise HTTPException(status_code=400, detail="小说内容不能为空")

        if not request.project_name:
            raise HTTPException(status_code=400, detail="项目名称不能为空")

        # 验证AI服务可用性
        from services.ai_service import AIService
        ai_service = AIService()
        if not ai_service.provider.is_available():
            raise HTTPException(status_code=503, detail="AI服务不可用，无法执行文本分段")

        # 使用TextSegmenter进行分段
        from agents.text_segmenter import TextSegmenter

        logger.info(f"🚀 开始AI文本分段 - 项目: {request.project_name}")
        logger.info(f"📝 文本长度: {len(request.novel_content)} 字符")
        logger.info(f"🎯 目标长度: {request.target_length}")

        text_segmenter = TextSegmenter()
        segments = await text_segmenter.segment_text(
            text=request.novel_content,
            target_length=request.target_length,
            preserve_context=request.preserve_context,
            language=request.language
        )

        if not segments:
            raise HTTPException(status_code=500, detail="AI文本分段失败，未生成任何段落")

        logger.info(f"✅ AI文本分段成功，生成 {len(segments)} 个段落")

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
            "created_at": datetime.now().isoformat(),
            "ai_segmentation": True  # 标记为AI分段
        }

        fs.save_history(str(project_path), "segmentation", segmentation_state)
        logger.info(f"💾 分段状态已保存到项目: {request.project_name}")

        return {
            "success": True,
            "message": f"AI文本成功分段为 {len(segments)} 个段落",
            "total_segments": len(segments),
            "segments": segments,
            "first_segment": segments[0] if segments else None,
            "project_name": request.project_name,
            "ai_generated": True  # 标记为AI生成
        }

    except HTTPException:
        raise
    except RuntimeError as e:
        # AI服务不可用或分段失败的专门处理
        logger.error(f"AI服务错误: {e}")
        raise HTTPException(status_code=503, detail=str(e))
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
        logger.info(f"🎨 开始生成段落漫画 - 项目: {request.project_name}, 段落: {request.segment_index}")
        logger.info(f"📝 段落文本长度: {len(request.segment_text)} 字符")
        logger.info(f"🎭 选定角色: {request.selected_characters}")
        logger.info(f"🎨 风格要求: {request.style_requirements}")
        logger.info(f"📸 生成数量: {request.generation_count}")

        # 详细记录前情提要接收情况
        logger.info(f"🖼️ 前情提要图片: {request.previous_segment_image}")
        logger.info(f"🔍 [前情提要接收详情]")
        logger.info(f"   - 当前段落: {request.segment_index + 1}")
        logger.info(f"   - 前情提要路径: {request.previous_segment_image}")
        logger.info(f"   - 路径类型: {type(request.previous_segment_image)}")
        logger.info(f"   - 路径长度: {len(request.previous_segment_image) if request.previous_segment_image else 0}")
        logger.info(f"   - 是否为空: {not request.previous_segment_image}")

        # 特别关注段落3的前情提要接收
        if request.segment_index == 2:  # 段落3
            logger.info(f"🚨 [重要] 段落3接收前情提要:")
            logger.info(f"   - 前情提要路径: {request.previous_segment_image}")
            logger.info(f"   - 路径有效性: {'✅ 有效' if request.previous_segment_image else '❌ 无效'}")
            if request.previous_segment_image:
                logger.info(f"   - 路径格式: {'项目相对路径' if request.previous_segment_image.startswith('/projects/') else 'HTTP URL' if request.previous_segment_image.startswith('http') else '其他格式'}")
                logger.info(f"   - 文件存在性: {'✅ 存在' if os.path.exists(request.previous_segment_image[1:] if request.previous_segment_image.startswith('/') else request.previous_segment_image) else '❌ 不存在'}")
            else:
                logger.error(f"❌ 段落3没有接收到前情提要，这表明段落2→3传递失败！")
        elif request.segment_index == 1:  # 段落2
            logger.info(f"📊 段落2前情提要状态: {'✅ 有前情提要' if request.previous_segment_image else '❌ 无前情提要'}")

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
            logger.info(f"📎 前情提要路径转换为字符串: {previous_context}")
        else:
            logger.info(f"ℹ️ 段落 {request.segment_index} 没有前情提要图片（第一段或前情提要不可用）")

        # 添加前情提要文本
        previous_segment_text = None
        if request.previous_segment_text:
            previous_segment_text = str(request.previous_segment_text)
            logger.info(f"📝 前情提要文本: {previous_segment_text[:100]}...")
        else:
            logger.info(f"ℹ️ 段落 {request.segment_index} 没有前情提要文本（第一段）")

        comic_script = {
            "scene_description": request.segment_text,
            "structured_data": structured_scene_data,  # 添加结构化数据
            "characters": request.selected_characters or [],
            "style_requirements": request.style_requirements or "",
            "reference_images": request.style_reference_images or [],
            "previous_context": previous_context,
            "previous_segment_text": previous_segment_text  # 新增：前情提要文本
        }

        logger.info(f"🎬 开始调用图像生成器，脚本包含前情提要图片: {'是' if previous_context else '否'}, 前情提要文本: {'是' if previous_segment_text else '否'}")

        # 特别关注段落3的生成过程
        if request.segment_index == 2:  # 段落3
            logger.info(f"🚨 [重要] 开始生成段落3的漫画图像")
            logger.info(f"   - 漫画脚本键: {list(comic_script.keys())}")
            logger.info(f"   - 场景描述长度: {len(comic_script.get('scene_description', ''))}")
            logger.info(f"   - 角色数量: {len(comic_script.get('characters', []))}")
            logger.info(f"   - 参考图片数量: {len(comic_script.get('reference_images', []))}")
            logger.info(f"   - 生成数量: {request.generation_count}")

        # 记录生成开始时间
        import time
        generation_start_time = time.time()
        logger.info(f"⏰ 图像生成开始时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")

        # 生成组图
        try:
            generation_result = await image_generator.generate_images_for_script(
                script=comic_script,
                project_path=project_path,
                max_images=request.generation_count,
                segment_index=request.segment_index
            )

            # 记录生成结束时间
            generation_end_time = time.time()
            generation_duration = generation_end_time - generation_start_time
            logger.info(f"⏱️ 图像生成总耗时: {generation_duration:.2f} 秒")
            logger.info(f"✅ 图像生成完成，生成结果: {generation_result.get('total_options', 0)} 张图片")

            if request.segment_index == 2:  # 段落3
                logger.info(f"🚨 [重要] 段落3图像生成成功")
                logger.info(f"   - 生成选项: {generation_result.get('total_options', 0)}")
                logger.info(f"   - 生成结果键: {list(generation_result.keys())}")

        except Exception as generation_error:
            generation_end_time = time.time()
            generation_duration = generation_end_time - generation_start_time
            logger.error(f"❌ 图像生成失败，耗时: {generation_duration:.2f} 秒")
            logger.error(f"❌ 生成错误: {generation_error}")
            logger.error(f"❌ 错误类型: {type(generation_error)}")
            if request.segment_index == 2:  # 段落3
                logger.error(f"🚨 [关键错误] 段落3图像生成失败！")
            raise generation_error

        # 更新分段状态 - 修复历史记录保存逻辑
        logger.info(f"📝 开始保存段落 {request.segment_index + 1} 的生成历史记录")

        # 获取segmentation状态（而不是获取最新的任意状态）
        segmentation_state = None
        for event in reversed(fs.get_project_timeline(str(project_path))):
            if event.get("type") == "segmentation":
                segmentation_state = event
                break

        if segmentation_state:
            logger.info(f"✅ 找到segmentation状态，保存生成记录")
            # 更新当前段落的生成记录
            fs.save_history(str(project_path), "segment_generation", {
                "segment_index": request.segment_index,
                "generation_result": generation_result,
                "config": script_config,
                "timestamp": datetime.now().isoformat()
            })
            logger.info(f"💾 段落 {request.segment_index + 1} 生成记录已保存到历史")
        else:
            logger.error(f"❌ 未找到segmentation状态，无法保存生成记录")
            # 即使没有segmentation状态，也要保存生成记录
            fs.save_history(str(project_path), "segment_generation", {
                "segment_index": request.segment_index,
                "generation_result": generation_result,
                "config": script_config,
                "timestamp": datetime.now().isoformat()
            })
            logger.info(f"💾 强制保存段落 {request.segment_index + 1} 生成记录")

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
        logger.info(f"✅ 开始处理段落确认请求 - 项目: {request.project_name}, 段落: {request.segment_index}")
        logger.info(f"🖼️ 用户选择的图片索引: {request.selected_image_index}")
        logger.info(f"📋 准备为下一段设置前情提要")

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
        logger.info(f"🔍 开始查找段落 {request.segment_index} 的生成记录...")
        found_segment = False

        for event in reversed(fs.get_project_timeline(str(project_path))):
            if (event.get("type") == "segment_generation" and
                event.get("data", {}).get("segment_index") == request.segment_index):
                found_segment = True
                logger.info(f"✅ 找到段落 {request.segment_index} 的生成记录")

                generation_result = event.get("data", {}).get("generation_result", {})
                generated_images = generation_result.get("generated_images", [])
                logger.info(f"📊 该段落生成了 {len(generated_images)} 张图片")

                # 根据用户选择的索引获取对应的图片路径
                if (0 <= request.selected_image_index < len(generated_images)):
                    selected_image = generated_images[request.selected_image_index]
                    logger.info(f"🎯 用户选择了第 {request.selected_image_index + 1} 张图片")

                    # 优先使用本地路径，如果没有则使用远程URL
                    local_path = selected_image.get("local_path")
                    remote_url = selected_image.get("image_url")
                    image_status = selected_image.get("status", "unknown")

                    logger.info(f"📁 图片状态: {image_status}")
                    logger.info(f"📁 本地路径: {local_path}")
                    logger.info(f"🌐 远程URL: {remote_url}")

                    # 确保路径是字符串类型
                    if local_path:
                        local_path = str(local_path)
                        logger.info(f"✅ 本地路径转换为字符串: {local_path}")
                    if remote_url:
                        remote_url = str(remote_url)
                        logger.info(f"✅ 远程URL转换为字符串: {remote_url}")

                    # 只有成功的图片才能作为前情提要
                    if image_status != "success":
                        logger.warning(f"❌ 选择的图片状态不是success: {image_status}")
                        selected_image_path = None
                    elif local_path and os.path.isfile(local_path):
                        # 如果是本地路径且文件存在，转换为相对于projects根目录的路径
                        try:
                            file_size = os.path.getsize(local_path)
                            logger.info(f"📏 本地图片文件大小: {file_size} bytes")

                            if str(fs.projects_dir) in local_path:
                                # 提取相对于projects根目录的路径（包含项目名）
                                relative_to_projects = local_path.replace(str(fs.projects_dir) + "/", "")
                                selected_image_path = "/projects/" + relative_to_projects
                                logger.info(f"🔄 转换本地路径为相对路径: {local_path} -> {selected_image_path}")
                            else:
                                # 如果本地路径不是在projects目录下，直接使用绝对路径
                                selected_image_path = local_path
                                logger.info(f"🔄 使用本地绝对路径作为前情提要: {selected_image_path}")
                        except Exception as e:
                            logger.error(f"❌ 处理本地路径时出错: {e}")
                            selected_image_path = None
                    elif remote_url:
                        # 使用远程URL
                        selected_image_path = remote_url
                        logger.info(f"🌐 使用远程URL作为前情提要: {selected_image_path}")
                    else:
                        logger.warning(f"❌ 无法获取有效的确认图片路径")
                        logger.warning(f"   本地路径: {local_path} (存在: {os.path.isfile(local_path) if local_path else False})")
                        logger.warning(f"   远程URL: {remote_url}")
                        selected_image_path = None
                else:
                    logger.error(f"❌ 用户选择的索引超出范围: {request.selected_image_index} >= {len(generated_images)}")
                    selected_image_path = None
                break

        if not found_segment:
            logger.error(f"❌ 未找到段落 {request.segment_index} 的生成记录")
            selected_image_path = None

        logger.info(f"🎉 段落 {request.segment_index + 1} 确认成功！")
        logger.info(f"📸 确认的图片路径: {selected_image_path}")
        logger.info(f"➡️ 是否有下一段: {'是' if next_segment_index < total_segments else '否'}")

        if next_segment_index < total_segments:
            logger.info(f"🔄 准备进入段落 {next_segment_index + 1}，前情提要已设置")
            # 特别关注段落2→3的传递
            if next_segment_index == 2:  # 下一段是段落3
                logger.info(f"🚨 [重要] 段落2→3前情提要传递:")
                logger.info(f"   - 当前段落: {request.segment_index + 1} (段落2)")
                logger.info(f"   - 目标段落: {next_segment_index + 1} (段落3)")
                logger.info(f"   - 前情提要路径: {selected_image_path}")
                logger.info(f"   - 路径类型: {type(selected_image_path)}")
                logger.info(f"   - 路径长度: {len(selected_image_path) if selected_image_path else 0}")
                logger.info(f"   - 是否为空: {not selected_image_path}")
        else:
            logger.info(f"🏁 所有段落处理完成！")

        # 在返回前进行最终验证和调试记录
        logger.info(f"📋 最终验证结果:")
        logger.info(f"   - 当前段落: {request.segment_index + 1}")
        logger.info(f"   - 用户选择索引: {request.selected_image_index}")
        logger.info(f"   - 下一段索引: {next_segment_index}")
        logger.info(f"   - 总段落数: {total_segments}")
        logger.info(f"   - 最终确认图片路径: {selected_image_path}")
        logger.info(f"   - 路径类型: {type(selected_image_path)}")
        logger.info(f"   - 路径是否为空: {not selected_image_path}")

        # 额外的调试信息
        if selected_image_path:
            logger.info(f"🔍 [路径详情] ")
            logger.info(f"   - 路径前缀: {selected_image_path[:20]}...")
            logger.info(f"   - 是否以/projects/开头: {selected_image_path.startswith('/projects/')}")
            logger.info(f"   - 是否为HTTP URL: {selected_image_path.startswith('http')}")
        else:
            logger.error(f"❌ [严重错误] 确认图片路径为空，这将导致下一段没有前情提要！")

        # 验证确认图片路径的有效性
        if selected_image_path:
            logger.info(f"🔍 验证确认图片路径...")
            if selected_image_path.startswith('/projects/'):
                logger.info(f"   ✅ 路径格式正确 (项目相对路径)")
                # 验证文件是否存在
                full_path = os.path.join(os.getcwd(), selected_image_path[1:])  # 去掉开头的 /
                if os.path.isfile(full_path):
                    file_size = os.path.getsize(full_path)
                    logger.info(f"   ✅ 确认图片文件存在，大小: {file_size} bytes")
                else:
                    logger.error(f"   ❌ 确认图片文件不存在: {full_path}")
                    logger.warning(f"   ⚠️ 将返回空路径，可能影响前情提要功能")
            elif selected_image_path.startswith('http'):
                logger.info(f"   ✅ 路径格式正确 (HTTP URL)")
            else:
                logger.info(f"   ℹ️ 路径格式未知: {selected_image_path}")
                if os.path.isfile(selected_image_path):
                    file_size = os.path.getsize(selected_image_path)
                    logger.info(f"   ✅ 本地文件存在，大小: {file_size} bytes")
                else:
                    logger.warning(f"   ⚠️ 本地文件不存在: {selected_image_path}")
        else:
            logger.error(f"❌ 最终确认图片路径为空！")
            logger.warning(f"   ⚠️ 这将导致下一段没有前情提要")

        return {
            "success": True,
            "message": f"段落 {request.segment_index + 1} 已确认",
            "segment_index": request.segment_index,
            "selected_image_index": request.selected_image_index,
            "has_next_segment": next_segment_index < total_segments,
            "next_segment_index": next_segment_index if next_segment_index < total_segments else None,
            "confirmed_image_path": selected_image_path,
            "project_name": request.project_name,
            "debug_info": {
                "confirmed_path_type": "project_relative" if selected_image_path and selected_image_path.startswith('/projects/') else "http_url" if selected_image_path and selected_image_path.startswith('http') else "absolute_path" if selected_image_path else "null",
                "path_length": len(selected_image_path) if selected_image_path else 0
            }
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


# ====================== 章节清理API ======================

@router.post("/cleanup-chapters")
async def cleanup_chapters(
    project_name: str,
    target_chapter: str = None,
    dry_run: bool = True
):
    """
    清理项目章节目录结构
    Clean up project chapter directory structure

    Args:
        project_name: 项目名称
        target_chapter: 目标章节名称（可选）
        dry_run: 是否为试运行模式
    """
    try:
        logger.info(f"🧹 开始清理章节目录结构 - 项目: {project_name}")
        logger.info(f"🎯 目标章节: {target_chapter if target_chapter else '自动选择'}")
        logger.info(f"🔍 试运行模式: {'是' if dry_run else '否'}")

        # 解析项目路径
        fs = ProjectFileSystem()
        project_path = fs._resolve_project_path(project_name)
        logger.info(f"📁 项目路径: {project_path}")

        # 导入清理工具
        from utils.chapter_cleanup import cleanup_project_chapters, analyze_project_structure

        # 先分析当前结构
        analysis = analyze_project_structure(str(project_path))
        if "error" in analysis:
            raise HTTPException(status_code=500, detail=f"分析章节结构失败: {analysis['error']}")

        logger.info(f"📊 分析结果 - 总章节数: {analysis['total_chapters']}")
        logger.info(f"📊 找到段落数: {len(analysis['segments'])}")

        # 执行清理
        result = cleanup_project_chapters(
            str(project_path),
            target_chapter=target_chapter,
            dry_run=dry_run
        )

        if not result.get("success"):
            raise HTTPException(status_code=500, detail=f"清理章节失败: {result.get('error')}")

        logger.info(f"✅ 章节清理完成 - {'试运行' if dry_run else '正式执行'}")

        return {
            "success": True,
            "project_name": project_name,
            "dry_run": dry_run,
            "analysis": analysis,
            "result": result
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"清理章节API失败: {e}")
        raise HTTPException(status_code=500, detail=f"清理章节失败: {str(e)}")


@router.get("/analyze-chapters/{project_name}")
async def analyze_chapters(
    project_name: str
):
    """
    分析项目章节目录结构
    Analyze project chapter directory structure
    """
    try:
        logger.info(f"🔍 开始分析章节目录结构 - 项目: {project_name}")

        # 解析项目路径
        fs = ProjectFileSystem()
        project_path = fs._resolve_project_path(project_name)
        logger.info(f"📁 项目路径: {project_path}")

        # 导入分析工具
        from utils.chapter_cleanup import analyze_project_structure

        # 执行分析
        analysis = analyze_project_structure(str(project_path))
        if "error" in analysis:
            raise HTTPException(status_code=500, detail=f"分析章节结构失败: {analysis['error']}")

        logger.info(f"✅ 章节结构分析完成 - 总章节数: {analysis['total_chapters']}")

        return {
            "success": True,
            "project_name": project_name,
            "analysis": analysis
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"分析章节API失败: {e}")
        raise HTTPException(status_code=500, detail=f"分析章节失败: {str(e)}")
