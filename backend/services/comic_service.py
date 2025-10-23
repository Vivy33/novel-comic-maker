"""
漫画生成服务
Comic Generation Service

负责协调漫画生成的完整流程，包括文本处理、脚本生成、图像生成等
Coordinates the complete comic generation workflow including text processing,
script generation, image generation, etc.
"""

import asyncio
import uuid
from datetime import datetime
from typing import Dict
import logging

from .file_system import ProjectFileSystem
from .ai_service import AIService
from ..agents.text_analyzer import TextAnalyzer
from ..agents.script_generator import ScriptGenerator
from ..agents.image_generator import ImageGenerator
from ..models.comic import TaskStatus, GenerationConfig

logger = logging.getLogger(__name__)


class ComicService:
    """
    漫画生成服务类

    管理漫画生成的异步任务和状态
    """

    def __init__(self):
        self.file_system = ProjectFileSystem()
        self.ai_service = AIService()
        self.text_analyzer = TextAnalyzer()
        self.script_generator = ScriptGenerator()
        self.image_generator = ImageGenerator()
        self.active_tasks: Dict[str, TaskStatus] = {}
        logger.info("漫画服务初始化完成（包含AI Agent）")

    async def start_comic_generation(
        self,
        project_id: str,
        generation_config: GenerationConfig
    ) -> str:
        """
        启动漫画生成任务

        Args:
            project_id: 项目ID
            generation_config: 生成配置

        Returns:
            任务ID
        """
        task_id = str(uuid.uuid4())

        # 创建任务状态
        task_status = TaskStatus(
            task_id=task_id,
            status="pending",
            progress=0.0,
            message="任务已创建，等待开始",
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat()
        )

        self.active_tasks[task_id] = task_status

        # 启动异步生成任务
        asyncio.create_task(
            self._generate_comic_async(task_id, project_id, generation_config)
        )

        logger.info(f"漫画生成任务已启动: {task_id}")
        return task_id

    async def get_generation_status(self, task_id: str) -> TaskStatus:
        """
        获取生成任务状态

        Args:
            task_id: 任务ID

        Returns:
            任务状态
        """
        if task_id not in self.active_tasks:
            raise ValueError(f"任务不存在: {task_id}")

        return self.active_tasks[task_id]

    async def regenerate_chapter(self, project_id: str, chapter_id: str) -> str:
        """
        重新生成章节漫画

        Args:
            project_id: 项目ID
            chapter_id: 章节ID

        Returns:
            任务ID
        """
        task_id = str(uuid.uuid4())

        # 创建重新生成任务状态
        task_status = TaskStatus(
            task_id=task_id,
            status="pending",
            progress=0.0,
            message=f"重新生成章节 {chapter_id} 任务已创建",
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat()
        )

        self.active_tasks[task_id] = task_status

        # 启动异步重新生成任务
        asyncio.create_task(
            self._regenerate_chapter_async(task_id, project_id, chapter_id)
        )

        logger.info(f"章节重新生成任务已启动: {task_id}")
        return task_id

    async def _generate_comic_async(
        self,
        task_id: str,
        project_id: str,
        config: GenerationConfig
    ):
        """
        异步漫画生成主流程

        Args:
            task_id: 任务ID
            project_id: 项目ID
            config: 生成配置
        """
        try:
            # 更新任务状态：开始执行
            self._update_task_status(task_id, "running", 0.0, "开始生成漫画")

            # 获取项目路径
            projects = self.file_system.list_projects()
            project_path = None
            for project in projects:
                if project.get("project_id") == project_id:
                    project_path = project.get("project_path")
                    break

            if not project_path:
                raise ValueError(f"项目不存在: {project_id}")

            # 步骤1: 读取小说文本 (5%)
            self._update_task_status(task_id, "running", 5.0, "读取小说文本")
            source_file = self.file_system.projects_dir / project_path / "source" / "novel.txt"
            if not source_file.exists():
                raise FileNotFoundError("小说源文件不存在")

            novel_text = source_file.read_text(encoding='utf-8')

            # 步骤2: 文本分析和分段 (10-25%)
            self._update_task_status(task_id, "running", 10.0, "分析小说文本")

            # 使用AI文本分析器
            text_analysis_result = await self.text_analyzer.analyze(novel_text)

            # 保存文本分析结果
            self.file_system.save_processing_result(
                project_path, "text_analysis", text_analysis_result
            )

            self._update_task_status(task_id, "running", 25.0, "文本分析完成")

            # 步骤3: 保存角色信息 (30%)
            self._update_task_status(task_id, "running", 30.0, "保存角色信息")
            characters = text_analysis_result.get("characters", [])
            self.file_system.save_characters(project_path, characters)

            # 步骤4: 分段文本并生成章节 (35-45%)
            self._update_task_status(task_id, "running", 35.0, "分段文本，准备生成脚本")

            # 将文本分为逻辑段落作为章节
            text_segments = self.text_analyzer._split_text(novel_text, 5000)  # 每段5000字符
            chapters = []

            for i, segment in enumerate(text_segments):
                chapter_id = f"chapter_{i+1:03d}"

                # 为每个段落生成漫画脚本
                self._update_task_status(
                    task_id, "running",
                    35.0 + (i / len(text_segments)) * 10.0,
                    f"生成第 {i+1}/{len(text_segments)} 章节脚本"
                )

                script_result = await self.script_generator.generate(text_analysis_result)

                # 保存脚本
                self.file_system.save_processing_result(
                    project_path, f"script_{chapter_id}", script_result
                )

                chapters.append({
                    "chapter_id": chapter_id,
                    "script": script_result,
                    "text_segment": segment
                })

            # 步骤5: 生成图像 (45-90%)
            self._update_task_status(task_id, "running", 45.0, "开始生成漫画图像")

            for i, chapter in enumerate(chapters):
                chapter_id = chapter["chapter_id"]
                script = chapter["script"]

                # 更新进度
                progress = 45.0 + (i / len(chapters)) * 45.0
                self._update_task_status(
                    task_id, "running", progress,
                    f"生成第 {i+1}/{len(chapters)} 章节图像"
                )

                # 使用AI图像生成器
                generated_images = await self.image_generator.generate_images_for_script(
                    script, str(self.file_system.projects_dir / project_path)
                )

                # 保存完整的漫画数据
                comic_data = {
                    "chapter_id": chapter_id,
                    "script": script,
                    "images": generated_images,
                    "created_at": datetime.now().isoformat(),
                    "style": config.style,
                    "quality": config.quality
                }

                self.file_system.save_chapter_comic(project_path, chapter_id, comic_data)

            # 步骤5: 完成 (100%)
            self._update_task_status(task_id, "completed", 100.0, "漫画生成完成")

            # 更新项目状态
            self.file_system.update_project_status(
                project_path, "completed", "comic_generated",
                total_chapters=len(chapters)
            )

            logger.info(f"漫画生成任务完成: {task_id}")

        except Exception as e:
            logger.error(f"漫画生成失败 {task_id}: {e}")
            self._update_task_status(task_id, "failed", 0.0, f"生成失败: {str(e)}")

    async def _regenerate_chapter_async(
        self,
        task_id: str,
        project_id: str,
        chapter_id: str
    ):
        """
        异步重新生成章节

        Args:
            task_id: 任务ID
            project_id: 项目ID
            chapter_id: 章节ID
        """
        try:
            # 更新任务状态
            self._update_task_status(
                task_id, "running", 0.0, f"开始重新生成章节 {chapter_id}"
            )

            # 获取项目路径
            projects = self.file_system.list_projects()
            project_path = None
            for project in projects:
                if project.get("project_id") == project_id:
                    project_path = project.get("project_path")
                    break

            if not project_path:
                raise ValueError(f"项目不存在: {project_id}")

            # 模拟重新生成过程
            self._update_task_status(task_id, "running", 50.0, "重新生成图像")
            await asyncio.sleep(2)

            # TODO: 实现实际的重新生成逻辑

            self._update_task_status(task_id, "completed", 100.0, "章节重新生成完成")
            logger.info(f"章节重新生成任务完成: {task_id}")

        except Exception as e:
            logger.error(f"章节重新生成失败 {task_id}: {e}")
            self._update_task_status(task_id, "failed", 0.0, f"重新生成失败: {str(e)}")

    def _update_task_status(
        self,
        task_id: str,
        status: str,
        progress: float,
        message: str
    ):
        """
        更新任务状态

        Args:
            task_id: 任务ID
            status: 状态
            progress: 进度
            message: 消息
        """
        if task_id in self.active_tasks:
            self.active_tasks[task_id].status = status
            self.active_tasks[task_id].progress = progress
            self.active_tasks[task_id].message = message
            self.active_tasks[task_id].updated_at = datetime.now().isoformat()

            logger.info(f"任务状态更新 {task_id}: {status} ({progress:.1f}%) - {message}")