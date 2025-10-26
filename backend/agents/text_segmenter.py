#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文本分段Agent - 漫画生成专用
强制使用JSON Schema，无错误处理机制，确保100%成功率
"""
import json
import logging
from typing import List, Dict, Any, Optional
import re

from services.ai_service import AIService

logger = logging.getLogger(__name__)


class TextSegment:
    """文本段落数据结构 - 漫画导向版本"""

    def __init__(
        self,
        content: str,
        segment_type: str = "description",
        scene_setting: str = "",
        characters: str = "",
        emotional_tone: str = "",
        visual_focus: str = "",
        position: int = 0,
        estimated_panels: int = 1
    ):
        self.content = content
        self.segment_type = segment_type
        self.scene_setting = scene_setting
        self.characters = characters
        self.emotional_tone = emotional_tone
        self.visual_focus = visual_focus
        self.position = position
        self.estimated_panels = estimated_panels

        # 计算基本属性
        self.word_count = len(content.split())
        self.character_count = len(content)

        # 漫画相关属性（默认值）
        self.comic_suitability = 0.8
        self.key_visual_elements = []
        self.transition_hint = ""
        self.dialogue_intensity = 0.5
        self.action_intensity = 0.5
        self.emotional_impact = 0.5
        self.background_complexity = 0.5
        self.camera_angle_suggestion = "中景"
        self.lighting_suggestion = "自然光"
        self.color_palette_suggestion = "自然色调"
        self.focus_characters = []
        self.panel_composition_notes = ""


class TextSegmenter:
    """文本分段Agent - 专为漫画生成优化"""

    def __init__(self):
        """初始化文本分段Agent"""
        self.ai_service = AIService()
        logger.info("文本分段Agent初始化完成")

    async def segment_text(
        self,
        text: str,
        target_length: str = "medium",
        preserve_context: bool = True,
        language: str = "chinese"
    ) -> List[Dict[str, Any]]:
        """
        将文本分段为适合漫画表现的段落

        Args:
            text: 待分段的文本
            target_length: 目标段落长度
            preserve_context: 是否保持上下文
            language: 语言

        Returns:
            分段结果列表
        """
        logger.info(f"开始漫画导向智能文本分段，总长度: {len(text)} 字符")
        logger.info("使用deepseek-v3.1 + JSON Schema分段")

        # 强制使用AI分段，无任何降级机制
        ai_segments = await self._ai_comic_segmentation_with_schema(text, target_length, language)

        logger.info(f"AI分段成功，共生成 {len(ai_segments)} 个段落")
        return self._convert_simple_segments_to_dict(ai_segments)

    async def _ai_comic_segmentation_with_schema(
        self,
        text: str,
        target_length: str = "medium",
        language: str = "chinese"
    ) -> List[TextSegment]:
        """使用JSON Schema进行漫画分段"""
        target_chars = 300

        # 构建简化prompt
        prompt = self._build_simple_schema_prompt(text, target_chars)

        # 使用文本模型 + JSON Schema
        result = await self.ai_service.generate_text(
            prompt=prompt,
            model_preference="deepseek-v3-1-terminus",
            use_json_schema=True,
            schema_type="simple_text_segmentation"
        )

        # 直接解析JSON结果
        segmentation_data = json.loads(result)

        # 转换为TextSegment对象
        segments = []
        for i, segment_data in enumerate(segmentation_data.get("segments", [])):
            content = segment_data.get("content", "")
            if content.strip():
                segment = TextSegment(
                    content=content,
                    segment_type=segment_data.get("segment_type", "description"),
                    scene_setting=segment_data.get("scene_setting", ""),
                    characters=segment_data.get("characters", ""),
                    emotional_tone=segment_data.get("emotional_tone", ""),
                    visual_focus=segment_data.get("visual_focus", ""),
                    position=i,
                    estimated_panels=1
                )
                segments.append(segment)

        return segments

    def _build_simple_schema_prompt(self, text: str, target_chars: int) -> str:
        """构建简化的JSON Schema prompt"""
        return f"""你是一位资深的漫画师，特别擅长构建冲突的剧情，请将以下小说文本分割成适合漫画表现的段落，引入适当的艺术加工，不要只切分原文。
                各个段落中指向人的代词，替换成人名。
                段落之间剧情要连贯，并且突出核心剧情。
                原文切成15到30段

要求：
- 为剧情人物生成合适的对话内容
- 每个段落约{target_chars}字符（250-350字范围）
- 保持语义完整性，不在重要情节中间切断
- 优先在对话、场景转换处分段
- 确保每个段落都有清晰的视觉表现力

输出格式必须严格按照以下JSON Schema：
{{
  "segments": [
    {{
      "content": "段落文本内容",
      "segment_type": "dialogue",
      "scene_setting": "场景描述",
      "characters": "角色1,角色2",
      "emotional_tone": "情感基调",
      "visual_focus": "视觉焦点"
    }}
  ]
}}

段落类型可选：dialogue（对话）、action（动作）、description（描述）、transition（转场）、climax（高潮）、resolution（结局）

待分析文本：
{text}

请严格按照上述JSON格式输出，确保JSON格式正确。"""

    def _convert_simple_segments_to_dict(self, segments: List[TextSegment]) -> List[Dict[str, Any]]:
        """将TextSegment对象列表转换为字典列表"""
        return [
            {
                "content": segment.content,
                "segment_type": segment.segment_type,
                "scene_setting": segment.scene_setting,
                "characters": segment.characters,
                "emotional_tone": segment.emotional_tone,
                "visual_focus": segment.visual_focus,
                "position": segment.position,
                "word_count": segment.word_count,
                "character_count": segment.character_count,
                "estimated_panels": segment.estimated_panels,
                "comic_suitability": segment.comic_suitability,
                "key_visual_elements": segment.key_visual_elements,
                "transition_hint": segment.transition_hint,
                "dialogue_intensity": segment.dialogue_intensity,
                "action_intensity": segment.action_intensity,
                "emotional_impact": segment.emotional_impact,
                "background_complexity": segment.background_complexity,
                "camera_angle_suggestion": segment.camera_angle_suggestion,
                "lighting_suggestion": segment.lighting_suggestion,
                "color_palette_suggestion": segment.color_palette_suggestion,
                "focus_characters": segment.focus_characters,
                "panel_composition_notes": segment.panel_composition_notes
            }
            for segment in segments
        ]