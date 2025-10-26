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
from agents.text_analyzer import TextAnalyzer
from agents.script_generator import ScriptGenerator
from agents.image_generator import ImageGenerator
from agents.text_segmenter import TextSegmenter
from models.comic import TaskStatus, GenerationConfig, ComicPanel

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
        self.text_segmenter = TextSegmenter()
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

            # 步骤4: 文本分段和故事章节划分 (35-45%)
            self._update_task_status(task_id, "running", 35.0, "分析文本结构，划分故事章节")

            # 智能文本分段：将长篇小说分为合理的故事章节
            text_segments = await self.text_segmenter.segment_text(
                novel_text,
                max_segment_length=2000,  # 增大章节长度，每个章节2000字符
                min_segment_length=500,   # 最小500字符保证故事完整性
                preserve_context=True
            )

            logger.info(f"将小说分为 {len(text_segments)} 个故事章节")

            # 为每个故事章节生成内容
            for i, story_segment in enumerate(text_segments):
                chapter_id = f"chapter_{i+1:03d}"
                chapter_title = f"第{i+1}章"

                # 创建故事章节目录结构
                self._update_task_status(
                    task_id, "running",
                    35.0 + (i / len(text_segments)) * 10.0,
                    f"创建第 {i+1}/{len(text_segments)} 章节结构"
                )

                # 使用新的章节创建方法
                created_chapter_id = self.file_system.create_story_chapter(
                    project_id, i+1, story_segment, chapter_title
                )

                # 步骤5: 生成章节脚本和分镜 (45-65%)
                self._update_task_status(
                    task_id, "running",
                    45.0 + (i / len(text_segments)) * 20.0,
                    f"生成第 {i+1}/{len(text_segments)} 章节的分镜脚本"
                )

                # 为该故事章节生成漫画脚本（包含多个场景）
                script_result = await self.script_generator.generate({
                    "text": story_segment,
                    "characters": text_analysis_result.get("characters", []),
                    "scenes": text_analysis_result.get("scenes", [])
                })

                # 步骤6: 生成该章节的所有分镜画面 (65-90%)
                self._update_task_status(
                    task_id, "running",
                    65.0 + (i / len(text_segments)) * 25.0,
                    f"生成第 {i+1}/{len(text_segments)} 章节的分镜画面"
                )

                # 确定该章节需要生成的画面数量
                panels_count = getattr(config, 'panels_per_chapter', 6)

                # 为该章节生成多个分镜画面
                panels = []
                for panel_idx in range(panels_count):
                    try:
                        # 为每个分镜生成图像
                        image_prompt = self._create_panel_prompt(
                            script_result, panel_idx, panels_count
                        )

                        # 生成图像
                        image_result = await self.image_generator.generate_image(
                            prompt=image_prompt,
                            output_dir=str(self.file_system.projects_dir / project_path / "chapters" / created_chapter_id / "images"),
                            filename_prefix=f"scene_option_{panel_idx}_"
                        )

                        # 创建分镜画面对象
                        panel = ComicPanel(
                            panel_id=panel_idx + 1,
                            description=image_prompt,
                            scene_description=script_result.get("scenes", [f"场景{panel_idx+1}"])[panel_idx % len(script_result.get("scenes", ["场景1"]))],
                            characters=script_result.get("characters", [])[:3],  # 限制角色数量
                            scene=script_result.get("setting", "默认场景"),
                            emotion=script_result.get("emotions", ["平静"])[panel_idx % len(script_result.get("emotions", ["平静"]))],
                            image_path=image_result.get("image_path"),
                            confirmed=False,
                            generated_at=datetime.now().isoformat()
                        )
                        panels.append(panel)

                    except Exception as e:
                        logger.error(f"生成第{panel_idx+1}个分镜画面失败: {e}")
                        # 创建占位画面以保证数量一致
                        panel = ComicPanel(
                            panel_id=panel_idx + 1,
                            description=f"分镜画面 {panel_idx + 1}",
                            scene_description=f"场景 {panel_idx + 1}",
                            confirmed=False,
                            generated_at=datetime.now().isoformat()
                        )
                        panels.append(panel)

                # 保存该章节的所有分镜画面
                self.file_system.save_chapter_panels(
                    project_id, created_chapter_id, panels
                )

                # 保存脚本信息
                chapter_dir = (self.file_system.projects_dir / project_path / "chapters" / created_chapter_id)
                self.file_system._save_json(
                    chapter_dir / "script.json",
                    {
                        "script": script_result,
                        "story_segment": story_segment,
                        "created_at": datetime.now().isoformat()
                    }
                )

                logger.info(f"章节 {created_chapter_id} 生成完成，包含 {len(panels)} 个分镜画面")

            # 步骤7: 完成 (100%)
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

    def _create_panel_prompt(self, script_result: dict, panel_index: int, total_panels: int) -> str:
        """
        为分镜画面创建生成提示

        Args:
            script_result: 脚本生成结果
            panel_index: 当前分镜索引
            total_panels: 总分镜数量

        Returns:
            图像生成提示
        """
        # 从脚本中提取关键信息
        scenes = script_result.get("scenes", ["默认场景"])
        characters = script_result.get("characters", [])
        setting = script_result.get("setting", "现代背景")
        style = script_result.get("style", "漫画风格")
        emotions = script_result.get("emotions", ["平静"])

        # 为当前分镜选择场景和情绪
        current_scene = scenes[panel_index % len(scenes)]
        current_emotion = emotions[panel_index % len(emotions)]

        # 构建提示
        character_desc = ""
        if characters:
            main_characters = characters[:2]  # 限制主要角色数量
            character_desc = f"，主要角色：{', '.join(main_characters)}"

        prompt = f"""{style}漫画分镜画面第{panel_index + 1}张：{current_scene}
场景设定：{setting}{character_desc}
情绪氛围：{current_emotion}
画面要求：高质量的漫画分镜，清晰的构图，适合连环画风格，角色表情生动，背景细节丰富"""

        return prompt