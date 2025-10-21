"""
连贯性检查Agent
Coherence Checker Agent

负责验证压缩后文本的质量，检查逻辑连贯性、角色一致性、时间线连贯性等
Responsible for verifying the quality of compressed text, checking logical coherence, character consistency, timeline coherence, etc.
"""

import logging
import re
from typing import Dict, Any, List, Optional
import json
from datetime import datetime

from ..services.ai_service import AIService

logger = logging.getLogger(__name__)


class CoherenceIssue:
    """连贯性问题数据结构"""

    def __init__(
        self,
        issue_type: str,
        severity: str,  # low, medium, high, critical
        description: str,
        location: str,  # 问题位置描述
        suggestion: Optional[str] = None,
        affected_elements: List[str] = None
    ):
        self.issue_type = issue_type
        self.severity = severity
        self.description = description
        self.location = location
        self.suggestion = suggestion
        self.affected_elements = affected_elements or []
        self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'issue_type': self.issue_type,
            'severity': self.severity,
            'description': self.description,
            'location': self.location,
            'suggestion': self.suggestion,
            'affected_elements': self.affected_elements,
            'timestamp': self.timestamp
        }


class CoherenceScore:
    """连贯性分数数据结构"""

    def __init__(
        self,
        overall_score: float,
        logical_coherence: float,
        character_coherence: float,
        temporal_coherence: float,
        plot_coherence: float,
        emotional_coherence: float
    ):
        self.overall_score = overall_score
        self.logical_coherence = logical_coherence
        self.character_coherence = character_coherence
        self.temporal_coherence = temporal_coherence
        self.plot_coherence = plot_coherence
        self.emotional_coherence = emotional_coherence

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'overall_score': self.overall_score,
            'logical_coherence': self.logical_coherence,
            'character_coherence': self.character_coherence,
            'temporal_coherence': self.temporal_coherence,
            'plot_coherence': self.plot_coherence,
            'emotional_coherence': self.emotional_coherence
        }


class CoherenceChecker:
    """连贯性检查器"""

    def __init__(self):
        self.ai_service = AIService()

        # 连贯性检查维度
        self.check_dimensions = {
            'logical': '逻辑连贯性',
            'character': '角色连贯性',
            'temporal': '时间连贯性',
            'plot': '情节连贯性',
            'emotional': '情感连贯性'
        }

        # 问题严重程度权重
        self.severity_weights = {
            'low': 0.1,
            'medium': 0.3,
            'high': 0.6,
            'critical': 1.0
        }

    async def check_coherence(
        self,
        original_text: str,
        compressed_text: str,
        text_analysis: Optional[Dict[str, Any]] = None,
        compression_level: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        连贯性检查主函数

        Args:
            original_text: 原始文本
            compressed_text: 压缩后文本
            text_analysis: 文本分析结果
            compression_level: 压缩级别

        Returns:
            连贯性检查结果
        """
        logger.info("开始连贯性检查...")

        try:
            # 1. 基础连贯性检查
            basic_results = await self._basic_coherence_check(
                original_text, compressed_text
            )

            # 2. AI辅助连贯性分析
            ai_results = await self._ai_coherence_analysis(
                original_text, compressed_text, text_analysis
            )

            # 3. 专项检查
            specialized_results = await self._specialized_checks(
                original_text, compressed_text, text_analysis
            )

            # 4. 整合结果
            final_results = self._integrate_results(
                basic_results, ai_results, specialized_results
            )

            logger.info(f"连贯性检查完成，总体得分: {final_results['coherence_score'].overall_score:.2f}")

            return final_results

        except Exception as e:
            logger.error(f"连贯性检查失败: {e}")
            return self._fallback_coherence_check(compressed_text)

    async def _basic_coherence_check(
        self,
        original_text: str,
        compressed_text: str
    ) -> Dict[str, Any]:
        """基础连贯性检查"""
        issues = []

        # 检查文本完整性
        if not compressed_text.strip():
            issues.append(CoherenceIssue(
                issue_type='completeness',
                severity='critical',
                description='压缩后文本为空',
                location='全文',
                suggestion='重新执行压缩流程'
            ))

        # 检查压缩比例是否合理
        compression_ratio = len(compressed_text) / len(original_text) if original_text else 0
        if compression_ratio > 0.9:
            issues.append(CoherenceIssue(
                issue_type='compression_ratio',
                severity='low',
                description=f'压缩比例过低: {compression_ratio:.2%}',
                location='全文',
                suggestion='考虑更积极的压缩策略'
            ))
        elif compression_ratio < 0.1:
            issues.append(CoherenceIssue(
                issue_type='compression_ratio',
                severity='high',
                description=f'压缩比例过高: {compression_ratio:.2%}',
                location='全文',
                suggestion='可能丢失了过多重要信息'
            ))

        # 检查句子完整性
        incomplete_sentences = self._check_sentence_completeness(compressed_text)
        if incomplete_sentences:
            issues.append(CoherenceIssue(
                issue_type='sentence_completeness',
                severity='medium',
                description=f'发现 {len(incomplete_sentences)} 个不完整句子',
                location='全文',
                suggestion='检查并修复不完整的句子',
                affected_elements=incomplete_sentences
            ))

        # 检查段落边界
        paragraph_issues = self._check_paragraph_boundaries(compressed_text)
        issues.extend(paragraph_issues)

        # 计算基础分数
        basic_score = max(0.0, 1.0 - sum(self.severity_weights[issue.severity] for issue in issues))

        return {
            'basic_score': basic_score,
            'basic_issues': [issue.to_dict() for issue in issues]
        }

    def _check_sentence_completeness(self, text: str) -> List[str]:
        """检查句子完整性"""
        incomplete_sentences = []

        # 分割句子
        sentences = re.split(r'[。！？；]', text)
        sentences = [s.strip() for s in sentences if s.strip()]

        for sentence in sentences:
            # 检查句子是否过短（可能不完整）
            if len(sentence) < 5:
                incomplete_sentences.append(sentence)
            # 检查是否以主语开头但没有谓语
            elif re.match(r'^[他她它们][，。！？]?$', sentence):
                incomplete_sentences.append(sentence)

        return incomplete_sentences

    def _check_paragraph_boundaries(self, text: str) -> List[CoherenceIssue]:
        """检查段落边界"""
        issues = []

        paragraphs = text.split('\n\n')
        paragraphs = [p.strip() for p in paragraphs if p.strip()]

        for i, paragraph in enumerate(paragraphs):
            # 检查段落长度
            if len(paragraph) < 10:
                issues.append(CoherenceIssue(
                    issue_type='paragraph_length',
                    severity='low',
                    description=f'第 {i+1} 段过短',
                    location=f'段落 {i+1}',
                    suggestion='考虑与相邻段落合并'
                ))

            # 检查段落开头
            if paragraph and not re.match(r'^[\w\u4e00-\u9fff「『]', paragraph):
                issues.append(CoherenceIssue(
                    issue_type='paragraph_start',
                    severity='low',
                    description=f'第 {i+1} 段开头不规范',
                    location=f'段落 {i+1}',
                    suggestion='检查段落开头格式'
                ))

        return issues

    async def _ai_coherence_analysis(
        self,
        original_text: str,
        compressed_text: str,
        text_analysis: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """AI辅助连贯性分析"""
        logger.info("执行AI连贯性分析...")

        try:
            # 构建AI分析提示词
            analysis_prompt = f"""
请深入分析以下压缩后文本的连贯性质量：

压缩级别：{text_analysis.get('compression_level', 'unknown') if text_analysis else 'unknown'}
原始文本长度：{len(original_text)} 字符
压缩后文本长度：{len(compressed_text)} 字符

压缩后文本：
---
{compressed_text}
---

请从以下维度评估连贯性（0-1分）：

1. 逻辑连贯性：
   - 故事情节是否合乎逻辑
   - 因果关系是否清晰
   - 推理过程是否合理

2. 角色连贯性：
   - 角色性格是否一致
   - 角色行为是否符合其设定
   - 角色关系是否清晰

3. 时间连贯性：
   - 时间线是否清晰
   - 事件顺序是否合理
   - 时间跨度是否适当

4. 情节连贯性：
   - 故事情节是否完整
   - 转折是否自然
   - 前后呼应是否到位

5. 情感连贯性：
   - 情感变化是否合理
   - 情感表达是否一致
   - 情感基调是否统一

请识别存在的连贯性问题，包括：
- 问题类型和严重程度
- 具体位置和描述
- 改进建议

请以JSON格式返回完整分析结果：
{{
    "logical_coherence": {{"score": 0.85, "issues": [], "strengths": []}},
    "character_coherence": {{"score": 0.80, "issues": [], "strengths": []}},
    "temporal_coherence": {{"score": 0.90, "issues": [], "strengths": []}},
    "plot_coherence": {{"score": 0.85, "issues": [], "strengths": []}},
    "emotional_coherence": {{"score": 0.75, "issues": [], "strengths": []}},
    "overall_assessment": {{
        "score": 0.83,
        "summary": "总体连贯性良好",
        "major_issues": [],
        "recommendations": []
    }}
}}
"""

            # 调用AI服务
            analysis_result = await self.ai_service.generate_text(
                prompt=analysis_prompt,
                model_preference="seedream",
                max_tokens=2000,
                temperature=0.2
            )

            # 解析AI分析结果
            try:
                ai_analysis = json.loads(analysis_result)

                # 提取各维度分数
                scores = {}
                issues = []

                for dimension in ['logical', 'character', 'temporal', 'plot', 'emotional']:
                    dimension_key = f"{dimension}_coherence"
                    if dimension_key in ai_analysis:
                        dimension_data = ai_analysis[dimension_key]
                        scores[dimension] = dimension_data.get('score', 0.5)

                        # 转换问题为标准格式
                        for issue in dimension_data.get('issues', []):
                            issues.append(CoherenceIssue(
                                issue_type=dimension,
                                severity=issue.get('severity', 'medium'),
                                description=issue.get('description', ''),
                                location=issue.get('location', ''),
                                suggestion=issue.get('suggestion', ''),
                                affected_elements=issue.get('affected_elements', [])
                            ))

                # 提取总体评估
                overall_assessment = ai_analysis.get('overall_assessment', {})
                overall_score = overall_assessment.get('score', sum(scores.values()) / len(scores))

                return {
                    'ai_scores': scores,
                    'ai_overall_score': overall_score,
                    'ai_issues': [issue.to_dict() for issue in issues],
                    'ai_assessment': overall_assessment
                }

            except json.JSONDecodeError:
                logger.warning("AI连贯性分析结果解析失败")
                return self._fallback_ai_analysis(compressed_text)

        except Exception as e:
            logger.error(f"AI连贯性分析失败: {e}")
            return self._fallback_ai_analysis(compressed_text)

    async def _specialized_checks(
        self,
        original_text: str,
        compressed_text: str,
        text_analysis: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """专项检查"""
        logger.info("执行专项连贯性检查...")

        specialized_issues = []

        # 1. 角色一致性专项检查
        if text_analysis and 'main_characters' in text_analysis:
            character_issues = await self._check_character_consistency(
                compressed_text, text_analysis['main_characters']
            )
            specialized_issues.extend(character_issues)

        # 2. 场景转换检查
        scene_issues = await self._check_scene_transitions(compressed_text)
        specialized_issues.extend(scene_issues)

        # 3. 时间线检查
        timeline_issues = await self._check_timeline_consistency(compressed_text)
        specialized_issues.extend(timeline_issues)

        # 4. 逻辑漏洞检查
        logic_issues = await self._check_logical_gaps(compressed_text)
        specialized_issues.extend(logic_issues)

        return {
            'specialized_issues': [issue.to_dict() for issue in specialized_issues],
            'specialized_score': max(0.0, 1.0 - sum(self.severity_weights[issue.severity] for issue in specialized_issues))
        }

    async def _check_character_consistency(
        self,
        text: str,
        main_characters: List[Dict[str, Any]]
    ) -> List[CoherenceIssue]:
        """检查角色一致性"""
        issues = []

        for character_info in main_characters:
            character_name = character_info.get('name', '')
            if not character_name:
                continue

            # 检查角色出现频率
            appearances = len(re.findall(character_name, text))
            if appearances == 0 and character_info.get('importance', '') == 'main':
                issues.append(CoherenceIssue(
                    issue_type='character_consistency',
                    severity='high',
                    description=f'主要角色 {character_name} 未在压缩文本中出现',
                    location='全文',
                    suggestion='确保主要角色在压缩文本中得到体现',
                    affected_elements=[character_name]
                ))

            # AI辅助角色一致性检查
            try:
                character_check_prompt = f"""
请检查角色 {character_name} 在以下文本中的表现一致性：

角色描述：{json.dumps(character_info, ensure_ascii=False)}
文本内容：
---
{text}
---

请检查：
1. 角色性格是否与描述一致
2. 角色行为是否符合其设定
3. 角色语言风格是否统一

如发现问题，请描述具体位置和改进建议。
"""

                check_result = await self.ai_service.generate_text(
                    prompt=character_check_prompt,
                    model_preference="seedream",
                    max_tokens=500,
                    temperature=0.2
                )

                # 简单解析结果
                if '不一致' in check_result or '问题' in check_result:
                    issues.append(CoherenceIssue(
                        issue_type='character_consistency',
                        severity='medium',
                        description=f'角色 {character_name} 存在一致性问题',
                        location='全文',
                        suggestion=check_result[:200],  # 截取前200字符作为建议
                        affected_elements=[character_name]
                    ))

            except Exception as e:
                logger.error(f"角色 {character_name} 一致性检查失败: {e}")

        return issues

    async def _check_scene_transitions(self, text: str) -> List[CoherenceIssue]:
        """检查场景转换"""
        issues = []

        # 识别场景标记
        scene_markers = re.findall(r'(室内|室外|家中|公司|学校|街头|公园|餐厅)', text)

        # 检查场景转换是否突兀
        if len(scene_markers) > 1:
            transitions = []
            for i in range(len(scene_markers) - 1):
                current_scene = scene_markers[i]
                next_scene = scene_markers[i + 1]
                transitions.append((current_scene, next_scene))

            # AI检查场景转换的自然性
            try:
                transition_prompt = f"""
请检查以下场景转换是否自然：

场景序列：{" -> ".join(f"{s[0]} -> {s[1]}" for s in transitions)}
原文片段：
---
{text[:500]}...
---

请评估场景转换是否合理，如发现问题请指出。
"""

                transition_result = await self.ai_service.generate_text(
                    prompt=transition_prompt,
                    model_preference="seedream",
                    max_tokens=300,
                    temperature=0.2
                )

                if '突兀' in transition_result or '不自然' in transition_result:
                    issues.append(CoherenceIssue(
                        issue_type='scene_transition',
                        severity='medium',
                        description='场景转换可能过于突兀',
                        location='全文',
                        suggestion=transition_result[:200]
                    ))

            except Exception as e:
                logger.error(f"场景转换检查失败: {e}")

        return issues

    async def _check_timeline_consistency(self, text: str) -> List[CoherenceIssue]:
        """检查时间线一致性"""
        issues = []

        # 识别时间标记
        time_patterns = [
            r'(今天|昨天|明天|前天|后天)',
            r'(早上|中午|下午|晚上|深夜)',
            r'(春天|夏天|秋天|冬天)',
            r'(第一天|第二天|第三天)',
            r'(一周后|一个月后|一年后)'
        ]

        time_markers = []
        for pattern in time_patterns:
            matches = re.findall(pattern, text)
            time_markers.extend(matches)

        # 检查时间标记的逻辑性
        if len(time_markers) > 1:
            # AI检查时间线逻辑
            try:
                timeline_prompt = f"""
请检查以下文本中的时间线是否逻辑一致：

识别到的时间标记：{', '.join(time_markers)}
原文片段：
---
{text[:500]}...
---

请评估时间线是否合理，有无矛盾之处。
"""

                timeline_result = await self.ai_service.generate_text(
                    prompt=timeline_prompt,
                    model_preference="seedream",
                    max_tokens=300,
                    temperature=0.2
                )

                if '矛盾' in timeline_result or '不合理' in timeline_result:
                    issues.append(CoherenceIssue(
                        issue_type='timeline_consistency',
                        severity='high',
                        description='时间线存在逻辑矛盾',
                        location='全文',
                        suggestion=timeline_result[:200]
                    ))

            except Exception as e:
                logger.error(f"时间线检查失败: {e}")

        return issues

    async def _check_logical_gaps(self, text: str) -> List[CoherenceIssue]:
        """检查逻辑漏洞"""
        issues = []

        # AI检查逻辑连贯性
        try:
            logic_prompt = f"""
请仔细检查以下文本是否存在逻辑漏洞或不连贯的地方：

文本内容：
---
{text}
---

请检查：
1. 因果关系是否合理
2. 事件发展是否自然
3. 是否存在明显的逻辑漏洞
4. 前后是否有矛盾之处

如发现问题，请描述具体位置和性质。
"""

            logic_result = await self.ai_service.generate_text(
                prompt=logic_prompt,
                model_preference="seedream",
                max_tokens=500,
                temperature=0.2
            )

            if '漏洞' in logic_result or '矛盾' in logic_result or '问题' in logic_result:
                issues.append(CoherenceIssue(
                    issue_type='logical_gap',
                    severity='medium',
                    description='文本存在逻辑问题',
                    location='全文',
                    suggestion=logic_result[:300]
                ))

        except Exception as e:
            logger.error(f"逻辑漏洞检查失败: {e}")

        return issues

    def _integrate_results(
        self,
        basic_results: Dict[str, Any],
        ai_results: Dict[str, Any],
        specialized_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """整合检查结果"""
        # 收集所有问题
        all_issues = []

        # 基础问题
        all_issues.extend(basic_results.get('basic_issues', []))

        # AI识别的问题
        all_issues.extend(ai_results.get('ai_issues', []))

        # 专项检查问题
        all_issues.extend(specialized_results.get('specialized_issues', []))

        # 计算综合分数
        basic_score = basic_results.get('basic_score', 0.5)
        ai_score = ai_results.get('ai_overall_score', 0.5)
        specialized_score = specialized_results.get('specialized_score', 0.5)

        # 加权平均
        overall_score = (basic_score * 0.3 + ai_score * 0.5 + specialized_score * 0.2)

        # 构建连贯性分数对象
        ai_scores = ai_results.get('ai_scores', {})
        coherence_score = CoherenceScore(
            overall_score=overall_score,
            logical_coherence=ai_scores.get('logical', 0.5),
            character_coherence=ai_scores.get('character', 0.5),
            temporal_coherence=ai_scores.get('temporal', 0.5),
            plot_coherence=ai_scores.get('plot', 0.5),
            emotional_coherence=ai_scores.get('emotional', 0.5)
        )

        # 统计问题严重程度
        issue_summary = {
            'critical': len([i for i in all_issues if i.get('severity') == 'critical']),
            'high': len([i for i in all_issues if i.get('severity') == 'high']),
            'medium': len([i for i in all_issues if i.get('severity') == 'medium']),
            'low': len([i for i in all_issues if i.get('severity') == 'low'])
        }

        return {
            'coherence_score': coherence_score.to_dict(),
            'total_issues': len(all_issues),
            'issue_summary': issue_summary,
            'issues': all_issues,
            'check_details': {
                'basic_check': basic_results,
                'ai_analysis': ai_results,
                'specialized_checks': specialized_results
            },
            'recommendations': self._generate_recommendations(all_issues),
            'is_acceptable': overall_score >= 0.6 and issue_summary['critical'] == 0
        }

    def _generate_recommendations(self, issues: List[Dict[str, Any]]) -> List[str]:
        """生成改进建议"""
        recommendations = []

        # 按问题类型生成建议
        issue_types = set(issue.get('issue_type', '') for issue in issues)

        if 'logical_gap' in issue_types:
            recommendations.append("建议重新梳理故事逻辑，确保因果关系合理")

        if 'character_consistency' in issue_types:
            recommendations.append("建议检查角色设定，确保角色性格和行为一致")

        if 'timeline_consistency' in issue_types:
            recommendations.append("建议检查时间线，修复时间逻辑矛盾")

        if 'scene_transition' in issue_types:
            recommendations.append("建议增加场景过渡描述，使场景转换更自然")

        if 'completeness' in issue_types:
            recommendations.append("建议重新执行压缩流程，确保文本完整性")

        if not recommendations:
            recommendations.append("文本连贯性良好，可以继续处理")

        return recommendations

    def _fallback_ai_analysis(self, text: str) -> Dict[str, Any]:
        """AI分析失败的备选方案"""
        return {
            'ai_scores': {
                'logical': 0.5,
                'character': 0.5,
                'temporal': 0.5,
                'plot': 0.5,
                'emotional': 0.5
            },
            'ai_overall_score': 0.5,
            'ai_issues': [],
            'ai_assessment': {
                'score': 0.5,
                'summary': 'AI分析失败，使用默认分数',
                'major_issues': [],
                'recommendations': ['建议手动检查文本连贯性']
            }
        }

    def _fallback_coherence_check(self, text: str) -> Dict[str, Any]:
        """连贯性检查失败的备选方案"""
        logger.warning("使用备选连贯性检查方案")

        # 基础分数基于文本长度和结构
        base_score = 0.5
        if len(text) > 100:
            base_score += 0.1
        if '。' in text and '，' in text:
            base_score += 0.1

        coherence_score = CoherenceScore(
            overall_score=base_score,
            logical_coherence=base_score,
            character_coherence=base_score,
            temporal_coherence=base_score,
            plot_coherence=base_score,
            emotional_coherence=base_score
        )

        return {
            'coherence_score': coherence_score.to_dict(),
            'total_issues': 1,
            'issue_summary': {'critical': 0, 'high': 0, 'medium': 1, 'low': 0},
            'issues': [{
                'issue_type': 'system_error',
                'severity': 'medium',
                'description': '连贯性检查系统出现错误',
                'location': '系统',
                'suggestion': '建议手动检查文本连贯性',
                'timestamp': datetime.now().isoformat()
            }],
            'check_details': {},
            'recommendations': ['建议手动检查文本连贯性'],
            'is_acceptable': base_score >= 0.6
        }


# 创建单例实例
coherence_checker = CoherenceChecker()