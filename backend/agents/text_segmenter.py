"""
智能文本分段Agent
Intelligent Text Segmentation Agent

负责智能地将长文本分割成符合情节完整性的段落
Intelligently segments long text into paragraphs that maintain plot integrity
"""

import logging
import re
from typing import Dict, Any, List, Optional
import json

from ..services.ai_service import AIService

logger = logging.getLogger(__name__)


class TextSegment:
    """文本段落数据结构"""

    def __init__(
        self,
        content: str,
        start_index: int,
        end_index: int,
        segment_type: str = "general",
        scene_setting: Optional[str] = None,
        characters_present: List[str] = None,
        emotional_tone: Optional[str] = None,
        key_events: List[str] = None,
        transition_clues: List[str] = None
    ):
        self.content = content
        self.start_index = start_index
        self.end_index = end_index
        self.segment_type = segment_type
        self.scene_setting = scene_setting
        self.characters_present = characters_present or []
        self.emotional_tone = emotional_tone
        self.key_events = key_events or []
        self.transition_clues = transition_clues or []

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'content': self.content,
            'start_index': self.start_index,
            'end_index': self.end_index,
            'segment_type': self.segment_type,
            'scene_setting': self.scene_setting,
            'characters_present': self.characters_present,
            'emotional_tone': self.emotional_tone,
            'key_events': self.key_events,
            'transition_clues': self.transition_clues,
            'word_count': len(self.content),
            'character_count': len(self.content)
        }


class TextSegmenter:
    """智能文本分段器"""

    def __init__(self):
        self.ai_service = AIService()

        # 段落类型定义
        self.segment_types = {
            'dialogue': '对话场景',
            'action': '动作场景',
            'description': '描述场景',
            'transition': '过渡场景',
            'climax': '高潮场景',
            'resolution': '结局场景'
        }

        # 过渡词和短语
        self.transition_markers = [
            '然而', '但是', '不过', '可是', '只是',
            '于是', '接着', '然后', '随后', '之后',
            '突然', '忽然', '瞬间', '刹那间',
            '此时', '这时', '与此同时', '与此同时',
            '因为', '所以', '因此', '由于',
            '首先', '其次', '最后', '最终',
            '另一方面', '除此之外', '另外',
            '话说', '且说', '却说', '再说'
        ]

        # 场景标记（不含章节关键字）
        self.scene_markers = [
            '清晨', '中午', '下午', '傍晚', '夜晚', '深夜',
            '春天', '夏天', '秋天', '冬天',
            '室内', '室外', '街头', '家中', '公司', '学校'
        ]

    async def segment_text(
        self,
        text: str,
        max_segment_length: int = 2000,
        min_segment_length: int = 200,
        preserve_context: bool = True
    ) -> List[Dict[str, Any]]:
        """
        智能分段主函数

        Args:
            text: 待分段的文本
            max_segment_length: 最大段落长度
            min_segment_length: 最小段落长度
            preserve_context: 是否保持上下文连续性

        Returns:
            分段结果列表
        """
        logger.info(f"开始智能文本分段，总长度: {len(text)} 字符")

        try:
            # 1. 预处理文本
            preprocessed_text = self._preprocess_text(text)

            # 2. 基础分段
            initial_segments = self._initial_segmentation(
                preprocessed_text,
                max_segment_length,
                min_segment_length
            )

            # 3. AI辅助优化分段
            optimized_segments = await self._ai_optimize_segments(
                initial_segments,
                preserve_context
            )

            # 4. 段落特征分析
            analyzed_segments = await self._analyze_segment_features(optimized_segments)

            # 5. 段落连贯性检查
            final_segments = await self._check_segment_coherence(analyzed_segments)

            logger.info(f"文本分段完成，共 {len(final_segments)} 个段落")

            return [segment.to_dict() for segment in final_segments]

        except Exception as e:
            logger.error(f"文本分段失败: {e}")
            # 返回基础分段结果作为备选
            return self._fallback_segmentation(text, max_segment_length)

    def _preprocess_text(self, text: str) -> str:
        """预处理文本"""
        # 清理多余的空白字符
        text = re.sub(r'\s+', ' ', text)

        # 确保标点符号后有空格
        text = re.sub(r'([。！？；])', r'\1\n', text)

        # 处理引号
        text = re.sub(r'([「『])', r'\1', text)
        text = re.sub(r'([」』])', r'\1', text)

        return text.strip()

    def _initial_segmentation(
        self,
        text: str,
        max_length: int,
        min_length: int
    ) -> List[TextSegment]:
        """初始分段"""
        segments = []

        # 按句子分割
        sentences = re.split(r'[。！？；\n]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]

        current_segment = ""
        start_index = 0

        for sentence in sentences:
            # 在章节标记处强制断开，优先于长度规则
            if self._is_chapter_marker(sentence):
                if current_segment.strip():
                    segments.append(TextSegment(
                        content=current_segment.strip(),
                        start_index=start_index,
                        end_index=start_index + len(current_segment),
                        segment_type="general"
                    ))
                    start_index += len(current_segment)
                current_segment = sentence
                continue

            # 检查是否开始新段落（长度触发）
            if (len(current_segment) + len(sentence) > max_length and
                len(current_segment) >= min_length):

                # 检查是否为自然的分段点
                if self._is_natural_break_point(sentence):
                    segments.append(TextSegment(
                        content=current_segment.strip(),
                        start_index=start_index,
                        end_index=start_index + len(current_segment),
                        segment_type="general"
                    ))
                    start_index += len(current_segment)
                    current_segment = sentence
                else:
                    current_segment += "。" + sentence
            else:
                if current_segment:
                    current_segment += "。" + sentence
                else:
                    current_segment = sentence

        # 处理最后一段
        if current_segment.strip():
            segments.append(TextSegment(
                content=current_segment.strip(),
                start_index=start_index,
                end_index=start_index + len(current_segment),
                segment_type="general"
            ))

        return segments

    def _is_natural_break_point(self, sentence: str) -> bool:
        """判断是否为自然的分段点"""
        # 检查是否包含过渡词
        for marker in self.transition_markers:
            if sentence.startswith(marker):
                return True

        # 检查是否包含场景标记或章节标记
        for marker in self.scene_markers:
            if marker in sentence:
                return True
        if self._is_chapter_marker(sentence):
            return True

        # 检查是否为时间转换
        time_patterns = [
            r'第二天', r'次日', r'数日后', r'许久',
            r'同时', r'这时', r'此时', r'那时'
        ]

        for pattern in time_patterns:
            if re.search(pattern, sentence):
                return True

        return False

    def _is_chapter_marker(self, sentence: str) -> bool:
        """识别章节标记，如“第一章”、“第二章”、“第一回”等"""
        s = sentence.strip()
        # 去掉开头的引号、空格和常见非字母数字符号
        s = re.sub(r'^[\s\W]+', '', s)
        # 允许“第…章/回”以及直写形式，兼容中文/英文冒号与空格
        patterns = [
            r'^(第[一二三四五六七八九十百零两]+(章|回))(?:[：:\s]|$)',
            r'^(第一章|第二章|第一回|第二回)(?:[：:\s]|$)'
        ]
        for pat in patterns:
            if re.search(pat, s):
                return True
        # 兼容前置少量标点后出现章节标记的情况（前3字符内）
        if re.search(r'^.{0,3}第[一二三四五六七八九十百零两]+(章|回)', s):
            return True
        return False

    async def _ai_optimize_segments(
        self,
        segments: List[TextSegment],
        preserve_context: bool
    ) -> List[TextSegment]:
        """使用AI优化分段"""
        if not segments:
            return segments

        logger.info("使用AI优化分段边界...")

        try:
            # 构建优化提示词
            segments_text = "\n---\n".join([
                f"段落{i+1}: {segment.content}"
                for i, segment in enumerate(segments[:5])  # 限制处理前5个段落
            ])

            optimization_prompt = f"""
请分析以下文本分段，并优化分段边界，确保每个段落：
1. 保持情节完整性
2. 包含完整的场景或事件
3. 保持逻辑连贯性
4. 长度适中（不过长也不过短）

当前分段：
{segments_text}

请返回优化建议，包括：
- 哪些段落需要合并
- 哪些地方需要新增分段
- 分段边界的调整建议

请以JSON格式返回：
{{
    "merge_suggestions": [[0, 1], [2, 3]],
    "split_suggestions": [
        {{"segment_index": 1, "split_position": "字符位置"}},
        {{"segment_index": 3, "split_position": "字符位置"}}
    ],
    "boundary_adjustments": [
        {{"segment_index": 0, "chars_to_add": 50, "chars_to_remove": 10}}
    ]
}}
"""

            # 调用AI服务
            optimization_result = await self.ai_service.generate_text(
                prompt=optimization_prompt,
                model_preference="seedream",
                max_tokens=1000,
                temperature=0.3
            )

            # 解析AI建议
            try:
                suggestions = json.loads(optimization_result)
                return self._apply_optimization_suggestions(segments, suggestions)
            except json.JSONDecodeError:
                logger.warning("AI优化建议解析失败，使用原始分段")
                return segments

        except Exception as e:
            logger.error(f"AI优化分段失败: {e}")
            return segments

    def _apply_optimization_suggestions(
        self,
        segments: List[TextSegment],
        suggestions: Dict[str, Any]
    ) -> List[TextSegment]:
        """应用AI优化建议"""
        optimized_segments = segments.copy()

        # 应用合并建议
        merge_suggestions = suggestions.get('merge_suggestions', [])
        for indices in reversed(merge_suggestions):  # 从后往前合并，避免索引变化
            if all(i < len(optimized_segments) for i in indices):
                # 合并段落
                merged_content = " ".join(optimized_segments[i].content for i in indices)
                merged_segment = TextSegment(
                    content=merged_content,
                    start_index=optimized_segments[indices[0]].start_index,
                    end_index=optimized_segments[indices[-1]].end_index,
                    segment_type="merged"
                )

                # 替换原段落
                for i in reversed(indices):
                    del optimized_segments[i]
                optimized_segments.insert(indices[0], merged_segment)

        # 这里可以添加其他优化建议的应用逻辑

        return optimized_segments

    async def _analyze_segment_features(self, segments: List[TextSegment]) -> List[TextSegment]:
        """分析段落特征"""
        logger.info("分析段落特征...")

        for i, segment in enumerate(segments):
            try:
                # 构建特征分析提示词
                analysis_prompt = f"""
请分析以下文本段落的主要特征：

段落内容：
---
{segment.content}
---

请识别：
1. 场景类型（对话/动作/描述/过渡等）
2. 场景设定（地点、时间、环境）
3. 出现角色（如果有明确提到的角色名）
4. 情感基调（紧张/轻松/悲伤/愉快等）
5. 关键事件（1-3个重要事件）
6. 过渡线索（连接前后段的线索词）

请以JSON格式返回：
{{
    "segment_type": "dialogue",
    "scene_setting": "咖啡馆室内",
    "characters_present": ["张三", "李四"],
    "emotional_tone": "轻松",
    "key_events": ["点咖啡", "聊天"],
    "transition_clues": ["突然", "这时"]
}}
"""

                # 调用AI服务
                analysis_result = await self.ai_service.generate_text(
                    prompt=analysis_prompt,
                    model_preference="seedream",
                    max_tokens=500,
                    temperature=0.2
                )

                # 解析分析结果
                try:
                    features = json.loads(analysis_result)

                    # 更新段落特征
                    segment.segment_type = features.get('segment_type', 'general')
                    segment.scene_setting = features.get('scene_setting')
                    segment.characters_present = features.get('characters_present', [])
                    segment.emotional_tone = features.get('emotional_tone')
                    segment.key_events = features.get('key_events', [])
                    segment.transition_clues = features.get('transition_clues', [])

                except json.JSONDecodeError:
                    logger.warning(f"段落{i+1}特征分析解析失败")
                    # 使用基础分析
                    segment.segment_type = self._basic_segment_type_detection(segment.content)

            except Exception as e:
                logger.error(f"段落{i+1}特征分析失败: {e}")
                segment.segment_type = self._basic_segment_type_detection(segment.content)

        return segments

    def _basic_segment_type_detection(self, content: str) -> str:
        """基础段落类型检测"""
        # 检测对话
        if re.search(r'[「『]', content):
            return 'dialogue'

        # 检测动作
        action_keywords = ['跑', '跳', '打', '走', '拿起', '放下', '开始', '结束']
        if any(keyword in content for keyword in action_keywords):
            return 'action'

        # 检测描述
        description_keywords = ['美丽', '高大', '宽敞', '安静', '热闹', '装饰']
        if any(keyword in content for keyword in description_keywords):
            return 'description'

        # 检测过渡
        if any(marker in content for marker in self.transition_markers):
            return 'transition'

        return 'general'

    async def _check_segment_coherence(self, segments: List[TextSegment]) -> List[TextSegment]:
        """检查段落连贯性"""
        if len(segments) < 2:
            return segments

        logger.info("检查段落连贯性...")

        coherent_segments = segments.copy()

        for i in range(len(segments) - 1):
            current = segments[i]
            next_segment = segments[i + 1]

            try:
                # 构建连贯性检查提示词
                coherence_prompt = f"""
请检查以下两个相邻段落的连贯性：

段落{i+1}：
---
{current.content}
---

段落{i+2}：
---
{next_segment.content}
---

请评估：
1. 逻辑连贯性（情节是否自然过渡）
2. 角色一致性（角色行为是否一致）
3. 时间连续性（时间线是否合理）
4. 场景转换（场景变化是否自然）

如果连贯性有问题，请建议如何改进。

请以JSON格式返回：
{{
    "coherence_score": 0.85,
    "logical_coherence": 0.9,
    "character_coherence": 0.8,
    "temporal_coherence": 0.85,
    "scene_coherence": 0.8,
    "has_issues": false,
    "issues": [],
    "suggestions": []
}}
"""

                # 调用AI服务
                coherence_result = await self.ai_service.generate_text(
                    prompt=coherence_prompt,
                    model_preference="seedream",
                    max_tokens=500,
                    temperature=0.2
                )

                # 解析连贯性结果
                try:
                    coherence_data = json.loads(coherence_result)
                    coherence_score = coherence_data.get('coherence_score', 0.5)

                    # 如果连贯性较差，记录问题
                    if coherence_score < 0.6:
                        logger.warning(f"段落{i+1}和{i+2}之间连贯性较差: {coherence_score}")
                        # 这里可以添加自动修复逻辑

                except json.JSONDecodeError:
                    logger.warning(f"段落{i+1}连贯性检查解析失败")

            except Exception as e:
                logger.error(f"段落{i+1}连贯性检查失败: {e}")

        return coherent_segments

    def _fallback_segmentation(self, text: str, max_length: int) -> List[Dict[str, Any]]:
        """备选分段方法"""
        logger.warning("使用备选分段方法")

        segments = []

        for i in range(0, len(text), max_length):
            segment_text = text[i:i + max_length]
            segments.append({
                'content': segment_text,
                'start_index': i,
                'end_index': min(i + max_length, len(text)),
                'segment_type': 'fallback',
                'scene_setting': None,
                'characters_present': [],
                'emotional_tone': None,
                'key_events': [],
                'transition_clues': [],
                'word_count': len(segment_text),
                'character_count': len(segment_text)
            })

        return segments


# 创建单例实例
text_segmenter = TextSegmenter()