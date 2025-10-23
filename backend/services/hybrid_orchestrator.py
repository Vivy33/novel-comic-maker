"""
混合编排架构
Hybrid Orchestration Architecture

整合LangGraph工作流和简单函数，提供统一的漫画生成流程
Integrates LangGraph workflows and simple functions to provide a unified comic generation process
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from ..workflows.text_compression import TextCompressionWorkflow
from ..workflows.feedback_handler import FeedbackWorkflow
from ..agents.text_segmenter import text_segmenter
from ..agents.coherence_checker import coherence_checker
from ..agents.quality_assessor import quality_assessor
from ..agents.character_consistency_agent import character_consistency_agent
from ..agents.scene_composer import scene_composer
from ..services.ai_service import AIService
from ..services.file_system import ProjectFileSystem

logger = logging.getLogger(__name__)


class HybridOrchestrator:
    """混合编排器"""

    def __init__(self):
        self.ai_service = AIService()
        self.file_system = ProjectFileSystem()

        # LangGraph工作流
        self.text_compression_workflow = TextCompressionWorkflow()
        self.feedback_workflow = FeedbackWorkflow()

        # 简单函数Agent
        self.simple_agents = {
            'text_segmenter': text_segmenter,
            'coherence_checker': coherence_checker,
            'quality_assessor': quality_assessor,
            'character_consistency': character_consistency_agent,
            'scene_composer': scene_composer
        }

    async def generate_comic_pipeline(
        self,
        novel_text: str,
        project_name: str,
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        完整的漫画生成流水线

        Args:
            novel_text: 小说文本
            project_name: 项目名称
            options: 生成选项

        Returns:
            生成结果
        """
        logger.info(f"开始漫画生成流水线: {project_name}")

        if not options:
            options = {}

        try:
            # 1. 创建项目
            project_path = await self._create_project(project_name)

            # 2. 文本预处理和分段
            preprocessed_data = await self._preprocess_text(novel_text, project_path, options)

            # 3. 文本压缩（LangGraph工作流）
            if options.get('use_compression', True) and len(novel_text) > 5000:
                compression_result = await self._compress_text_workflow(
                    preprocessed_data['text'], project_path
                )
                processed_text = compression_result.get('compressed_text', preprocessed_data['text'])
            else:
                processed_text = preprocessed_data['text']
                compression_result = None

            # 4. 文本分析
            text_analysis = await self._analyze_text(processed_text, project_path)

            # 5. 脚本生成
            comic_script = await self._generate_comic_script(text_analysis, project_path)

            # 6. 角色管理
            character_data = await self._manage_characters(comic_script, project_path)

            # 7. 场景合成和图像生成
            visual_results = await self._generate_visual_content(
                comic_script, character_data, project_path, options
            )

            # 8. 整合结果
            final_result = await self._integrate_results(
                project_path, preprocessed_data, compression_result, text_analysis,
                comic_script, character_data, visual_results
            )

            logger.info(f"漫画生成流水线完成: {project_name}")
            return {
                'status': 'success',
                'project_path': project_path,
                'pipeline_result': final_result,
                'generation_summary': self._create_generation_summary(final_result)
            }

        except Exception as e:
            logger.error(f"漫画生成流水线失败: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'project_name': project_name
            }

    async def _create_project(self, project_name: str) -> str:
        """创建项目"""
        return self.file_system.create_project(project_name)

    async def _preprocess_text(
        self,
        novel_text: str,
        project_path: str,
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """文本预处理"""
        logger.info("文本预处理...")

        # 保存原始文本
        self.file_system.save_file(project_path, 'source', 'original.txt', novel_text)

        # 智能分段
        segments = await self.simple_agents['text_segmenter'].segment_text(
            novel_text,
            max_segment_length=options.get('segment_length', 2000)
        )

        # 保存分段结果
        self.file_system.save_file(
            project_path, 'processing', 'segments.json', segments
        )

        return {
            'text': novel_text,
            'segments': segments,
            'original_length': len(novel_text),
            'segment_count': len(segments)
        }

    async def _compress_text_workflow(self, text: str, project_path: str) -> Dict[str, Any]:
        """文本压缩工作流（LangGraph）"""
        logger.info("执行文本压缩工作流...")

        workflow_result = await self.text_compression_workflow.run_compression(text)

        # 保存压缩结果
        self.file_system.save_file(
            project_path, 'processing', 'compression_result.json',
            workflow_result
        )

        if workflow_result.get('compressed_text'):
            self.file_system.save_file(
                project_path, 'processing', 'compressed.txt',
                workflow_result['compressed_text']
            )

        return workflow_result

    async def _analyze_text(self, text: str, project_path: str) -> Dict[str, Any]:
        """文本分析"""
        logger.info("分析文本...")

        from ..agents.text_analyzer import text_analyzer
        analysis_result = await text_analyzer.analyze(text)

        # 保存分析结果
        self.file_system.save_file(
            project_path, 'processing', 'text_analysis.json',
            analysis_result
        )

        return analysis_result

    async def _generate_comic_script(
        self,
        text_analysis: Dict[str, Any],
        project_path: str
    ) -> Dict[str, Any]:
        """生成漫画脚本"""
        logger.info("生成漫画脚本...")

        from ..agents.script_generator import script_generator
        comic_script = await script_generator.generate(text_analysis)

        # 保存脚本
        self.file_system.save_file(
            project_path, 'chapters', 'comic_script.json',
            comic_script
        )

        return comic_script

    async def _manage_characters(
        self,
        comic_script: Dict[str, Any],
        project_path: str
    ) -> Dict[str, Any]:
        """角色管理"""
        logger.info("管理角色...")

        # 初始化角色系统
        await self.simple_agents['character_consistency'].consistency_manager.initialize_character_system(project_path)

        # 从脚本提取角色
        script_content = comic_script.get('title', '') + ' ' + \
                       ' '.join(panel.get('scene_description', '') for panel in comic_script.get('panels', []))

        character_profiles = await self.simple_agents['character_consistency'].consistency_manager.extract_characters_from_text(
            script_content, project_path
        )

        return {
            'character_profiles': [profile.to_dict() for profile in character_profiles],
            'character_count': len(character_profiles)
        }

    async def _generate_visual_content(
        self,
        comic_script: Dict[str, Any],
        character_data: Dict[str, Any],
        project_path: str,
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """生成视觉内容"""
        logger.info("生成视觉内容...")

        panels = comic_script.get('panels', [])
        visual_results = []

        for i, panel in enumerate(panels):
            try:
                # 场景合成
                scene_result = await self.simple_agents['scene_composer'].compose_scene(
                    project_path, panel, options.get('style_preferences')
                )

                if scene_result['status'] == 'success':
                    # 生成图像
                    image_prompt = scene_result['generation_prompt']
                    image_url = await self.ai_service.text_to_image("doubao-seedream-4.0", image_prompt)

                    # 保存图像
                    if image_url:
                        image_path = await self._save_generated_image(
                            image_url, project_path, f"panel_{i+1}.png"
                        )
                    else:
                        image_path = None

                    visual_results.append({
                        'panel_number': i + 1,
                        'scene_composition': scene_result['scene_composition'],
                        'image_prompt': image_prompt,
                        'image_url': image_url,
                        'image_path': image_path,
                        'status': 'success'
                    })
                else:
                    visual_results.append({
                        'panel_number': i + 1,
                        'status': 'error',
                        'error': scene_result.get('error', 'Unknown error')
                    })

            except Exception as e:
                logger.error(f"面板 {i+1} 视觉生成失败: {e}")
                visual_results.append({
                    'panel_number': i + 1,
                    'status': 'error',
                    'error': str(e)
                })

        return {
            'visual_results': visual_results,
            'total_panels': len(panels),
            'successful_panels': sum(1 for r in visual_results if r['status'] == 'success')
        }

    async def _save_generated_image(self, image_url: str, project_path: str, filename: str) -> str:
        """保存生成的图像"""
        try:
            # 这里应该实现从URL下载图像的逻辑
            # 简化版本：直接返回路径
            output_path = f"{project_path}/output/{filename}"
            self.file_system.save_file(project_path, 'output', filename, f"Image URL: {image_url}")
            return output_path
        except Exception as e:
            logger.error(f"保存图像失败: {e}")
            return None

    async def _integrate_results(
        self,
        project_path: str,
        preprocessed_data: Dict[str, Any],
        compression_result: Optional[Dict[str, Any]],
        text_analysis: Dict[str, Any],
        comic_script: Dict[str, Any],
        character_data: Dict[str, Any],
        visual_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """整合所有结果"""
        return {
            'project_info': {
                'project_path': project_path,
                'created_at': datetime.now().isoformat()
            },
            'text_processing': {
                'original_length': preprocessed_data['original_length'],
                'compressed_length': compression_result.get('final_result', {}).get('compressed_length', preprocessed_data['original_length']) if compression_result else preprocessed_data['original_length'],
                'compression_ratio': compression_result.get('final_result', {}).get('compression_ratio', 1.0) if compression_result else 1.0,
                'segment_count': preprocessed_data['segment_count']
            },
            'analysis_results': text_analysis,
            'script_results': comic_script,
            'character_results': character_data,
            'visual_results': visual_results,
            'quality_metrics': {
                'text_quality': compression_result.get('final_result', {}).get('quality_scores', {}) if compression_result else {},
                'visual_quality': self._calculate_visual_quality(visual_results)
            }
        }

    def _calculate_visual_quality(self, visual_results: Dict[str, Any]) -> Dict[str, Any]:
        """计算视觉质量指标"""
        total_panels = visual_results.get('total_panels', 0)
        successful_panels = visual_results.get('successful_panels', 0)

        return {
            'success_rate': successful_panels / total_panels if total_panels > 0 else 0,
            'total_panels': total_panels,
            'successful_panels': successful_panels,
            'failed_panels': total_panels - successful_panels
        }

    def _create_generation_summary(self, final_result: Dict[str, Any]) -> Dict[str, Any]:
        """创建生成摘要"""
        text_processing = final_result['text_processing']
        character_results = final_result['character_results']
        visual_results = final_result['visual_results']

        return {
            'original_text_length': text_processing['original_length'],
            'final_text_length': text_processing['compressed_length'],
            'compression_ratio': text_processing['compression_ratio'],
            'characters_extracted': character_results['character_count'],
            'panels_generated': visual_results['total_panels'],
            'successful_panels': visual_results['successful_panels'],
            'overall_success_rate': visual_results['successful_panels'] / visual_results['total_panels'] if visual_results['total_panels'] > 0 else 0,
            'generation_time': final_result['project_info']['created_at']
        }

    async def handle_user_feedback(
        self,
        project_path: str,
        feedback_text: str,
        feedback_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """处理用户反馈（LangGraph工作流）"""
        logger.info("处理用户反馈...")

        try:
            # 运行反馈处理工作流
            feedback_result = await self.feedback_workflow.handle_feedback(
                feedback_text, feedback_type, {'project_path': project_path}
            )

            # 保存反馈结果
            self.file_system.save_file(
                project_path, 'processing', f'feedback_{feedback_result["workflow_id"]}.json',
                feedback_result
            )

            return {
                'status': 'success',
                'feedback_result': feedback_result,
                'recommendations': feedback_result.get('final_result', {}).get('compression_recommendations', [])
            }

        except Exception as e:
            logger.error(f"用户反馈处理失败: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }


# 创建全局编排器实例
hybrid_orchestrator = HybridOrchestrator()