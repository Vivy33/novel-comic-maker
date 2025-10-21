"""
场景合成Agent
Scene Composition Agent

负责角色+场景合成，风格统一，生成最终的漫画场景描述
Responsible for character+scene composition, style unification, and generating final comic scene descriptions
"""

import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime

from ..services.ai_service import AIService
from ..agents.character_consistency_agent import CharacterConsistencyAgent

logger = logging.getLogger(__name__)


class SceneElement:
    """场景元素数据结构"""

    def __init__(
        self,
        element_type: str,  # character, background, object, effect
        description: str,
        position: Dict[str, Any],
        style_requirements: Dict[str, Any],
        priority: int = 1
    ):
        self.element_type = element_type
        self.description = description
        self.position = position
        self.style_requirements = style_requirements
        self.priority = priority
        self.generated_time = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            'element_type': self.element_type,
            'description': self.description,
            'position': self.position,
            'style_requirements': self.style_requirements,
            'priority': self.priority,
            'generated_time': self.generated_time
        }


class SceneComposition:
    """场景合成数据结构"""

    def __init__(
        self,
        scene_id: str,
        scene_description: str,
        characters: List[str],
        background: str,
        composition_elements: List[SceneElement],
        style_directives: Dict[str, Any],
        overall_mood: str
    ):
        self.scene_id = scene_id
        self.scene_description = scene_description
        self.characters = characters
        self.background = background
        self.composition_elements = composition_elements
        self.style_directives = style_directives
        self.overall_mood = overall_mood
        self.composition_time = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            'scene_id': self.scene_id,
            'scene_description': self.scene_description,
            'characters': self.characters,
            'background': self.background,
            'composition_elements': [elem.to_dict() for elem in self.composition_elements],
            'style_directives': self.style_directives,
            'overall_mood': self.overall_mood,
            'composition_time': self.composition_time
        }


class SceneComposer:
    """场景合成器"""

    def __init__(self):
        self.ai_service = AIService()
        self.character_agent = CharacterConsistencyAgent()

        # 场景合成规则
        self.composition_rules = {
            'character_placement': 'ensure_characters_are_properly_positioned',
            'perspective_consistency': 'maintain_consistent_perspective',
            'lighting_consistency': 'ensure_unified_lighting',
            'style_unification': 'maintain_artistic_style_consistency',
            'depth_composition': 'create_proper_depth_layering'
        }

    async def compose_scene(
        self,
        project_path: str,
        panel_script: Dict[str, Any],
        style_preferences: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        场景合成主函数

        Args:
            project_path: 项目路径
            panel_script: 分镜脚本
            style_preferences: 风格偏好设置

        Returns:
            场景合成结果
        """
        logger.info("开始场景合成...")

        try:
            # 1. 解析分镜脚本
            scene_analysis = await self._analyze_panel_script(panel_script)

            # 2. 提取角色信息
            character_info = await self._extract_scene_characters(project_path, scene_analysis)

            # 3. 设计场景背景
            background_design = await self._design_scene_background(scene_analysis, style_preferences)

            # 4. 合成场景元素
            composition_elements = await self._compose_scene_elements(
                character_info, background_design, scene_analysis
            )

            # 5. 统一风格
            style_unification = await self._unify_scene_style(
                composition_elements, style_preferences
            )

            # 6. 生成最终场景描述
            final_scene = SceneComposition(
                scene_id=f"scene_{panel_script.get('panel_number', 'unknown')}",
                scene_description=panel_script.get('scene_description', ''),
                characters=list(character_info.keys()),
                background=background_design,
                composition_elements=composition_elements,
                style_directives=style_unification,
                overall_mood=scene_analysis.get('emotional_tone', 'neutral')
            )

            # 7. 生成图像生成提示词
            generation_prompt = await self._generate_image_prompt(final_scene)

            logger.info(f"场景合成完成: {final_scene.scene_id}")
            return {
                'status': 'success',
                'scene_composition': final_scene.to_dict(),
                'generation_prompt': generation_prompt,
                'composition_quality': self._assess_composition_quality(final_scene)
            }

        except Exception as e:
            logger.error(f"场景合成失败: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'fallback_result': self._create_fallback_composition(panel_script)
            }

    async def _analyze_panel_script(self, panel_script: Dict[str, Any]) -> Dict[str, Any]:
        """分析分镜脚本"""
        scene_description = panel_script.get('scene_description', '')
        dialogue = panel_script.get('dialogue', '')
        narration = panel_script.get('narration', '')

        try:
            # 构建场景分析提示词
            analysis_prompt = f"""
请分析以下漫画分镜脚本的场景要素：

场景描述：{scene_description}
对话：{dialogue}
旁白：{narration}

请分析：
1. 场景类型（室内/室外/具体场所）
2. 情感基调
3. 主要动作和事件
4. 视角和构图要求
5. 时间和氛围
6. 关键视觉元素

请以JSON格式返回：
{{
    "scene_type": "场景类型",
    "emotional_tone": "情感基调",
    "main_actions": ["主要动作列表"],
    "composition_requirements": {{
        "perspective": "视角要求",
        "framing": "构图要求",
        "focus_point": "焦点"
    }},
    "time_setting": "时间设定",
    "atmosphere": "氛围描述",
    "key_visual_elements": ["关键视觉元素"]
}}
"""

            # 调用AI服务
            result = await self.ai_service.generate_text(
                prompt=analysis_prompt,
                model_preference="seedream",
                max_tokens=800,
                temperature=0.3
            )

            # 解析结果
            try:
                return json.loads(result)
            except json.JSONDecodeError:
                logger.warning("场景分析结果解析失败")
                return self._basic_scene_analysis(scene_description, dialogue, narration)

        except Exception as e:
            logger.error(f"场景分析失败: {e}")
            return self._basic_scene_analysis(scene_description, dialogue, narration)

    def _basic_scene_analysis(self, scene_description: str, dialogue: str, narration: str) -> Dict[str, Any]:
        """基础场景分析"""
        return {
            'scene_type': 'unknown',
            'emotional_tone': 'neutral',
            'main_actions': [],
            'composition_requirements': {
                'perspective': 'eye_level',
                'framing': 'medium_shot',
                'focus_point': 'center'
            },
            'time_setting': 'day',
            'atmosphere': scene_description[:100] if scene_description else '',
            'key_visual_elements': []
        }

    async def _extract_scene_characters(
        self,
        project_path: str,
        scene_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """提取场景中的角色信息"""
        try:
            # 获取项目中的角色档案
            character_profiles = await self.character_agent.consistency_manager.get_character_profiles(project_path)

            character_info = {}
            for profile in character_profiles:
                character_info[profile.name] = {
                    'profile': profile.to_dict(),
                    'scene_role': self._determine_character_role(profile, scene_analysis),
                    'placement_suggestions': self._suggest_character_placement(profile, scene_analysis),
                    'expression_requirements': self._determine_expression_requirements(profile, scene_analysis)
                }

            return character_info

        except Exception as e:
            logger.error(f"角色信息提取失败: {e}")
            return {}

    def _determine_character_role(self, profile, scene_analysis: Dict[str, Any]) -> str:
        """确定角色在场景中的角色"""
        # 简化的角色判断逻辑
        if profile.importance_level == 'main':
            return 'protagonist'
        elif profile.importance_level == 'secondary':
            return 'supporting'
        else:
            return 'background'

    def _suggest_character_placement(self, profile, scene_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """建议角色位置"""
        return {
            'position': 'center',
            'size_ratio': 0.3,
            'depth_layer': 'middle',
            'interaction_zone': 'main'
        }

    def _determine_expression_requirements(self, profile, scene_analysis: Dict[str, Any]) -> List[str]:
        """确定表情要求"""
        emotional_tone = scene_analysis.get('emotional_tone', 'neutral')

        expression_map = {
            'happy': ['smile', 'bright_eyes'],
            'sad': ['downcast', 'tearful'],
            'angry': ['frown', 'intense_eyes'],
            'surprised': ['wide_eyes', 'open_mouth'],
            'neutral': ['calm', 'natural']
        }

        return expression_map.get(emotional_tone, ['neutral'])

    async def _design_scene_background(
        self,
        scene_analysis: Dict[str, Any],
        style_preferences: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """设计场景背景"""
        try:
            # 构建背景设计提示词
            background_prompt = f"""
请为以下场景设计背景：

场景类型：{scene_analysis.get('scene_type', 'unknown')}
时间设定：{scene_analysis.get('time_setting', 'day')}
氛围：{scene_analysis.get('atmosphere', '')}
关键视觉元素：{', '.join(scene_analysis.get('key_visual_elements', []))}
构图要求：{json.dumps(scene_analysis.get('composition_requirements', {}), ensure_ascii=False)}

请设计：
1. 主要背景元素
2. 环境细节
3. 光照效果
4. 色彩方案
5. 氛围营造

请以JSON格式返回：
{{
    "main_elements": ["主要背景元素"],
    "environmental_details": ["环境细节"],
    "lighting": {{
        "type": "光照类型",
        "direction": "光照方向",
        "intensity": "光照强度",
        "color": "光照色彩"
    }},
    "color_scheme": {{
        "primary_colors": ["主要色彩"],
        "secondary_colors": ["次要色彩"],
        "mood_colors": ["情绪色彩"]
    }},
    "atmosphere_effects": ["氛围效果"]
}}
"""

            # 调用AI服务
            result = await self.ai_service.generate_text(
                prompt=background_prompt,
                model_preference="seedream",
                max_tokens=800,
                temperature=0.4
            )

            # 解析结果
            try:
                return json.loads(result)
            except json.JSONDecodeError:
                logger.warning("背景设计结果解析失败")
                return self._create_basic_background(scene_analysis)

        except Exception as e:
            logger.error(f"背景设计失败: {e}")
            return self._create_basic_background(scene_analysis)

    def _create_basic_background(self, scene_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """创建基础背景"""
        scene_type = scene_analysis.get('scene_type', 'unknown')

        return {
            'main_elements': [f'{scene_type} setting'],
            'environmental_details': ['basic environment'],
            'lighting': {
                'type': 'natural',
                'direction': 'front',
                'intensity': 'medium',
                'color': 'white'
            },
            'color_scheme': {
                'primary_colors': ['blue', 'green'],
                'secondary_colors': ['gray', 'brown'],
                'mood_colors': ['neutral']
            },
            'atmosphere_effects': []
        }

    async def _compose_scene_elements(
        self,
        character_info: Dict[str, Any],
        background_design: Dict[str, Any],
        scene_analysis: Dict[str, Any]
    ) -> List[SceneElement]:
        """合成场景元素"""
        elements = []

        # 添加角色元素
        for char_name, char_data in character_info.items():
            character_element = SceneElement(
                element_type='character',
                description=f'Character: {char_name}',
                position=char_data.get('placement_suggestions', {}),
                style_requirements={
                    'consistency_tags': char_data.get('profile', {}).get('consistency_tags', []),
                    'expression_requirements': char_data.get('expression_requirements', [])
                },
                priority=1
            )
            elements.append(character_element)

        # 添加背景元素
        for bg_element in background_design.get('main_elements', []):
            background_element = SceneElement(
                element_type='background',
                description=f'Background: {bg_element}',
                position={'layer': 'background', 'coverage': 'full'},
                style_requirements=background_design.get('color_scheme', {}),
                priority=2
            )
            elements.append(background_element)

        # 添加光照效果
        lighting = background_design.get('lighting', {})
        lighting_element = SceneElement(
            element_type='effect',
            description=f'Lighting: {lighting.get("type", "natural")}',
            position={'type': 'global', 'direction': lighting.get('direction', 'front')},
            style_requirements=lighting,
            priority=3
        )
        elements.append(lighting_element)

        return elements

    async def _unify_scene_style(
        self,
        composition_elements: List[SceneElement],
        style_preferences: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """统一场景风格"""
        default_style = {
            'art_style': style_preferences.get('art_style', 'anime') if style_preferences else 'anime',
            'color_palette': style_preferences.get('color_palette', 'vibrant') if style_preferences else 'vibrant',
            'line_quality': 'clean',
            'shading_style': 'cell_shading',
            'detail_level': 'medium'
        }

        # 根据场景元素调整风格
        has_characters = any(elem.element_type == 'character' for elem in composition_elements)
        if has_characters:
            default_style['character_detail_level'] = 'high'

        return default_style

    async def _generate_image_prompt(self, scene_composition: SceneComposition) -> str:
        """生成图像生成提示词"""
        try:
            # 构建提示词组件
            character_descriptions = []
            for elem in scene_composition.composition_elements:
                if elem.element_type == 'character':
                    character_descriptions.append(elem.description)

            background_description = scene_composition.background.get('main_elements', [])
            lighting_info = scene_composition.background.get('lighting', {})
            color_scheme = scene_composition.background.get('color_scheme', {})
            style_info = scene_composition.style_directives

            # 组合完整提示词
            prompt_parts = [
                f"Scene: {scene_composition.scene_description}",
                f"Mood: {scene_composition.overall_mood}",
                f"Characters: {', '.join(character_descriptions)}",
                f"Background: {', '.join(background_description)}",
                f"Lighting: {lighting_info.get('type', 'natural light')} from {lighting_info.get('direction', 'front')}",
                f"Style: {style_info.get('art_style', 'anime style')}",
                f"Colors: {', '.join(color_scheme.get('primary_colors', []))}",
                "High quality, detailed, comic book art style"
            ]

            return ', '.join(prompt_parts)

        except Exception as e:
            logger.error(f"图像提示词生成失败: {e}")
            return f"Comic scene: {scene_composition.scene_description}, high quality, detailed"

    def _assess_composition_quality(self, scene_composition: SceneComposition) -> Dict[str, Any]:
        """评估场景合成质量"""
        try:
            # 基础质量评估
            element_count = len(scene_composition.composition_elements)
            has_characters = len(scene_composition.characters) > 0
            has_background = bool(scene_composition.background)
            has_style = bool(scene_composition.style_directives)

            # 计算质量分数
            quality_score = 0.0
            if has_characters:
                quality_score += 0.3
            if has_background:
                quality_score += 0.3
            if has_style:
                quality_score += 0.2
            if element_count >= 3:
                quality_score += 0.2

            return {
                'overall_score': round(quality_score, 2),
                'element_count': element_count,
                'has_characters': has_characters,
                'has_background': has_background,
                'has_style': has_style,
                'quality_level': 'good' if quality_score >= 0.8 else 'acceptable' if quality_score >= 0.6 else 'needs_improvement'
            }

        except Exception as e:
            logger.error(f"场景质量评估失败: {e}")
            return {
                'overall_score': 0.5,
                'quality_level': 'unknown',
                'error': str(e)
            }

    def _create_fallback_composition(self, panel_script: Dict[str, Any]) -> Dict[str, Any]:
        """创建备选场景合成"""
        fallback_scene = SceneComposition(
            scene_id=f"fallback_scene_{panel_script.get('panel_number', 'unknown')}",
            scene_description=panel_script.get('scene_description', ''),
            characters=[],
            background={'main_elements': ['simple background']},
            composition_elements=[],
            style_directives={'art_style': 'simple'},
            overall_mood='neutral'
        )

        return {
            'scene_composition': fallback_scene.to_dict(),
            'generation_prompt': f"Simple comic scene: {fallback_scene.scene_description}",
            'composition_quality': {'overall_score': 0.5, 'quality_level': 'fallback'}
        }


# 创建单例实例
scene_composer = SceneComposer()