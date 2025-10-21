"""
质量评估Agent
Quality Assessment Agent

负责对压缩后文本进行全面的质量评估，决定是否需要重新压缩
Responsible for comprehensive quality assessment of compressed text, determining whether recompression is needed
"""

import logging
import re
from typing import Dict, Any, List, Optional
import json
from datetime import datetime
from enum import Enum

from ..services.ai_service import AIService

logger = logging.getLogger(__name__)


class QualityDimension(str, Enum):
    """质量维度枚举"""
    READABILITY = "readability"
    COMPLETENESS = "completeness"
    ACCURACY = "accuracy"
    CONCISENESS = "conciseness"
    COHERENCE = "coherence"
    FLUENCY = "fluency"


class QualityLevel(str, Enum):
    """质量等级枚举"""
    EXCELLENT = "excellent"
    GOOD = "good"
    ACCEPTABLE = "acceptable"
    POOR = "poor"
    UNACCEPTABLE = "unacceptable"


class QualityMetric:
    """质量指标数据结构"""

    def __init__(
        self,
        dimension: QualityDimension,
        score: float,
        description: str,
        details: Optional[Dict[str, Any]] = None,
        suggestions: List[str] = None
    ):
        self.dimension = dimension
        self.score = score
        self.description = description
        self.details = details or {}
        self.suggestions = suggestions or []
        self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'dimension': self.dimension.value,
            'score': self.score,
            'description': self.description,
            'details': self.details,
            'suggestions': self.suggestions,
            'timestamp': self.timestamp
        }


class QualityAssessment:
    """质量评估结果数据结构"""

    def __init__(
        self,
        overall_score: float,
        quality_level: QualityLevel,
        metrics: List[QualityMetric],
        should_recompress: bool,
        compression_recommendations: List[str] = None
    ):
        self.overall_score = overall_score
        self.quality_level = quality_level
        self.metrics = metrics
        self.should_recompress = should_recompress
        self.compression_recommendations = compression_recommendations or []
        self.assessment_time = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'overall_score': self.overall_score,
            'quality_level': self.quality_level.value,
            'metrics': [metric.to_dict() for metric in self.metrics],
            'should_recompress': self.should_recompress,
            'compression_recommendations': self.compression_recommendations,
            'assessment_time': self.assessment_time
        }


class QualityAssessor:
    """质量评估器"""

    def __init__(self):
        self.ai_service = AIService()

        # 质量维度权重
        self.dimension_weights = {
            QualityDimension.READABILITY: 0.15,
            QualityDimension.COMPLETENESS: 0.25,
            QualityDimension.ACCURACY: 0.20,
            QualityDimension.CONCISENESS: 0.15,
            QualityDimension.COHERENCE: 0.15,
            QualityDimension.FLUENCY: 0.10
        }

        # 质量等级阈值
        self.quality_thresholds = {
            QualityLevel.EXCELLENT: 0.9,
            QualityLevel.GOOD: 0.75,
            QualityLevel.ACCEPTABLE: 0.6,
            QualityLevel.POOR: 0.4,
            QualityLevel.UNACCEPTABLE: 0.0
        }

        # 重新压缩阈值
        self.recompression_threshold = 0.6

    async def assess_quality(
        self,
        original_text: str,
        compressed_text: str,
        text_analysis: Optional[Dict[str, Any]] = None,
        compression_level: Optional[str] = None,
        coherence_results: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        质量评估主函数

        Args:
            original_text: 原始文本
            compressed_text: 压缩后文本
            text_analysis: 文本分析结果
            compression_level: 压缩级别
            coherence_results: 连贯性检查结果

        Returns:
            质量评估结果
        """
        logger.info("开始质量评估...")

        try:
            # 1. 基础质量指标计算
            basic_metrics = await self._calculate_basic_metrics(
                original_text, compressed_text
            )

            # 2. AI辅助质量评估
            ai_metrics = await self._ai_quality_assessment(
                original_text, compressed_text, text_analysis
            )

            # 3. 综合连贯性结果
            coherence_metrics = self._integrate_coherence_results(coherence_results)

            # 4. 计算综合质量分数
            overall_assessment = self._calculate_overall_quality(
                basic_metrics, ai_metrics, coherence_metrics
            )

            # 5. 生成改进建议
            recommendations = self._generate_recommendations(
                overall_assessment, compression_level
            )

            # 6. 决定是否需要重新压缩
            should_recompress = self._should_recompress(overall_assessment)

            logger.info(f"质量评估完成，总体得分: {overall_assessment.overall_score:.2f}, "
                       f"质量等级: {overall_assessment.quality_level.value}")

            return {
                'quality_assessment': overall_assessment.to_dict(),
                'detailed_metrics': {
                    'basic_metrics': [m.to_dict() for m in basic_metrics],
                    'ai_metrics': [m.to_dict() for m in ai_metrics],
                    'coherence_metrics': [m.to_dict() for m in coherence_metrics]
                },
                'recommendations': recommendations,
                'should_recompress': should_recompress,
                'next_steps': self._suggest_next_steps(overall_assessment, should_recompress)
            }

        except Exception as e:
            logger.error(f"质量评估失败: {e}")
            return self._fallback_quality_assessment(compressed_text)

    async def _calculate_basic_metrics(
        self,
        original_text: str,
        compressed_text: str
    ) -> List[QualityMetric]:
        """计算基础质量指标"""
        metrics = []

        # 1. 可读性指标
        readability_score = self._calculate_readability_score(compressed_text)
        metrics.append(QualityMetric(
            dimension=QualityDimension.READABILITY,
            score=readability_score,
            description="文本可读性评分",
            details={
                'avg_sentence_length': self._avg_sentence_length(compressed_text),
                'complex_words_ratio': self._complex_words_ratio(compressed_text)
            }
        ))

        # 2. 完整性指标
        completeness_score = self._calculate_completeness_score(
            original_text, compressed_text
        )
        metrics.append(QualityMetric(
            dimension=QualityDimension.COMPLETENESS,
            score=completeness_score,
            description="内容完整性评分",
            details={
                'compression_ratio': len(compressed_text) / len(original_text) if original_text else 0,
                'key_info_preserved': self._check_key_info_preservation(original_text, compressed_text)
            }
        ))

        # 3. 简洁性指标
        conciseness_score = self._calculate_conciseness_score(
            original_text, compressed_text
        )
        metrics.append(QualityMetric(
            dimension=QualityDimension.CONCISENESS,
            score=conciseness_score,
            description="文本简洁性评分",
            details={
                'redundancy_removed': self._estimate_redundancy_removal(original_text, compressed_text),
                'information_density': len(compressed_text.split()) / len(compressed_text) if compressed_text else 0
            }
        ))

        return metrics

    def _calculate_readability_score(self, text: str) -> float:
        """计算可读性分数"""
        if not text:
            return 0.0

        # 句子长度评分
        avg_length = self._avg_sentence_length(text)
        length_score = 1.0
        if avg_length > 50:
            length_score = max(0.3, 1.0 - (avg_length - 50) / 100)
        elif avg_length < 10:
            length_score = max(0.3, avg_length / 10)

        # 复杂词汇比例评分
        complex_ratio = self._complex_words_ratio(text)
        complex_score = max(0.4, 1.0 - complex_ratio)

        # 标点符号使用评分
        punctuation_score = self._punctuation_usage_score(text)

        # 综合评分
        return (length_score * 0.4 + complex_score * 0.3 + punctuation_score * 0.3)

    def _avg_sentence_length(self, text: str) -> float:
        """计算平均句子长度"""
        sentences = re.split(r'[。！？；]', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        if not sentences:
            return 0.0
        return sum(len(s) for s in sentences) / len(sentences)

    def _complex_words_ratio(self, text: str) -> float:
        """计算复杂词汇比例"""
        words = re.findall(r'[\w\u4e00-\u9fff]+', text)
        if not words:
            return 0.0

        # 简单的复杂词检测（字数>4的词）
        complex_words = [w for w in words if len(w) > 4]
        return len(complex_words) / len(words)

    def _punctuation_usage_score(self, text: str) -> float:
        """评估标点符号使用质量"""
        if not text:
            return 0.0

        # 检查基本标点符号
        has_periods = '。' in text
        has_commas = '，' in text
        has_quotes = any(p in text for p in ['「', '『', '"', "'"])

        score = 0.0
        if has_periods:
            score += 0.4
        if has_commas:
            score += 0.3
        if has_quotes:
            score += 0.3

        return score

    def _calculate_completeness_score(self, original: str, compressed: str) -> float:
        """计算完整性分数"""
        if not original or not compressed:
            return 0.0

        # 关键信息保留度
        key_info_score = self._check_key_info_preservation(original, compressed)

        # 压缩比例合理性
        compression_ratio = len(compressed) / len(original)
        ratio_score = 1.0
        if compression_ratio > 0.8:
            ratio_score = 0.7  # 压缩不足
        elif compression_ratio < 0.2:
            ratio_score = 0.5  # 压缩过度

        # 情节要点保留
        plot_points_score = self._check_plot_points_preservation(original, compressed)

        return (key_info_score * 0.4 + ratio_score * 0.3 + plot_points_score * 0.3)

    def _check_key_info_preservation(self, original: str, compressed: str) -> float:
        """检查关键信息保留度"""
        # 提取关键实体（简化版）
        original_entities = re.findall(r'[\u4e00-\u9fff]{2,}', original)

        if not original_entities:
            return 1.0

        # 计算实体保留率
        preserved_count = sum(1 for entity in original_entities if entity in compressed)
        return preserved_count / len(original_entities)

    def _check_plot_points_preservation(self, original: str, compressed: str) -> float:
        """检查情节要点保留度"""
        # 简单检测：检查重要动词和事件词
        important_words = ['发生', '决定', '发现', '改变', '解决', '胜利', '失败', '相遇', '分离']

        original_count = sum(1 for word in important_words if word in original)
        compressed_count = sum(1 for word in important_words if word in compressed)

        if original_count == 0:
            return 1.0

        return min(1.0, compressed_count / original_count)

    def _calculate_conciseness_score(self, original: str, compressed: str) -> float:
        """计算简洁性分数"""
        if not original:
            return 0.0

        compression_ratio = len(compressed) / len(original)

        # 理想压缩比例在0.3-0.6之间
        if 0.3 <= compression_ratio <= 0.6:
            ratio_score = 1.0
        elif compression_ratio < 0.3:
            ratio_score = max(0.4, compression_ratio / 0.3)
        else:
            ratio_score = max(0.4, 1.0 - (compression_ratio - 0.6) / 0.4)

        # 信息密度
        density_score = self._calculate_information_density(compressed)

        return (ratio_score * 0.6 + density_score * 0.4)

    def _estimate_redundancy_removal(self, original: str, compressed: str) -> float:
        """估算冗余移除效果"""
        # 简化计算：基于重复词的减少
        original_words = re.findall(r'[\w\u4e00-\u9fff]+', original)
        compressed_words = re.findall(r'[\w\u4e00-\u9fff]+', compressed)

        if not original_words:
            return 0.0

        original_repeats = len(original_words) - len(set(original_words))
        compressed_repeats = len(compressed_words) - len(set(compressed_words))

        if original_repeats == 0:
            return 0.8  # 默认分数

        repeat_reduction = (original_repeats - compressed_repeats) / original_repeats
        return max(0.0, min(1.0, repeat_reduction))

    def _calculate_information_density(self, text: str) -> float:
        """计算信息密度"""
        if not text:
            return 0.0

        words = re.findall(r'[\w\u4e00-\u9fff]+', text)
        unique_words = set(words)

        if not words:
            return 0.0

        # 词汇多样性
        diversity = len(unique_words) / len(words)

        # 平均词长
        avg_word_length = sum(len(word) for word in words) / len(words) if words else 0
        length_score = min(1.0, avg_word_length / 3)

        return (diversity * 0.7 + length_score * 0.3)

    async def _ai_quality_assessment(
        self,
        original_text: str,
        compressed_text: str,
        text_analysis: Optional[Dict[str, Any]]
    ) -> List[QualityMetric]:
        """AI辅助质量评估"""
        logger.info("执行AI质量评估...")

        metrics = []

        try:
            # 构建AI评估提示词
            assessment_prompt = f"""
请对以下压缩后的文本进行全面的质量评估：

原始文本长度：{len(original_text)} 字符
压缩后文本长度：{len(compressed_text)} 字符
压缩比例：{len(compressed_text) / len(original_text):.2%}

压缩后文本：
---
{compressed_text}
---

请从以下维度进行评估（0-1分）：

1. 准确性 (Accuracy)：
   - 内容是否忠实于原文
   - 重要信息是否准确传达
   - 有无歪曲或误解

2. 流畅性 (Fluency)：
   - 语言是否流畅自然
   - 有无生硬的表达
   - 语调是否一致

3. 情感表达 (Emotional Expression)：
   - 情感色彩是否保留
   - 情感变化是否自然
   - 氛围营造是否到位

对每个维度，请提供：
- 具体分数
- 详细说明
- 发现的问题
- 改进建议

请以JSON格式返回评估结果：
{{
    "accuracy": {{
        "score": 0.85,
        "description": "内容准确性良好",
        "issues": [],
        "suggestions": []
    }},
    "fluency": {{
        "score": 0.80,
        "description": "表达流畅，偶有不自然之处",
        "issues": ["个别句式略显生硬"],
        "suggestions": ["调整句式结构"]
    }},
    "emotional_expression": {{
        "score": 0.75,
        "description": "情感表达基本到位",
        "issues": ["部分情感转折可以更细腻"],
        "suggestions": ["增加情感描述的层次感"]
    }}
}}
"""

            # 调用AI服务
            ai_result = await self.ai_service.generate_text(
                prompt=assessment_prompt,
                model_preference="seedream",
                max_tokens=1500,
                temperature=0.2
            )

            # 解析AI评估结果
            try:
                ai_assessment = json.loads(ai_result)

                # 准确性指标
                if 'accuracy' in ai_assessment:
                    accuracy_data = ai_assessment['accuracy']
                    metrics.append(QualityMetric(
                        dimension=QualityDimension.ACCURACY,
                        score=accuracy_data.get('score', 0.5),
                        description=accuracy_data.get('description', ''),
                        details={'ai_issues': accuracy_data.get('issues', [])},
                        suggestions=accuracy_data.get('suggestions', [])
                    ))

                # 流畅性指标
                if 'fluency' in ai_assessment:
                    fluency_data = ai_assessment['fluency']
                    metrics.append(QualityMetric(
                        dimension=QualityDimension.FLUENCY,
                        score=fluency_data.get('score', 0.5),
                        description=fluency_data.get('description', ''),
                        details={'ai_issues': fluency_data.get('issues', [])},
                        suggestions=fluency_data.get('suggestions', [])
                    ))

            except json.JSONDecodeError:
                logger.warning("AI质量评估结果解析失败")
                # 使用默认分数
                metrics.extend([
                    QualityMetric(QualityDimension.ACCURACY, 0.5, "AI评估失败"),
                    QualityMetric(QualityDimension.FLUENCY, 0.5, "AI评估失败")
                ])

        except Exception as e:
            logger.error(f"AI质量评估失败: {e}")
            metrics.extend([
                QualityMetric(QualityDimension.ACCURACY, 0.5, "AI评估失败"),
                QualityMetric(QualityDimension.FLUENCY, 0.5, "AI评估失败")
            ])

        return metrics

    def _integrate_coherence_results(
        self,
        coherence_results: Optional[Dict[str, Any]]
    ) -> List[QualityMetric]:
        """整合连贯性检查结果"""
        metrics = []

        if coherence_results and 'coherence_score' in coherence_results:
            coherence_score = coherence_results['coherence_score']
            overall_score = coherence_score.get('overall_score', 0.5)

            metrics.append(QualityMetric(
                dimension=QualityDimension.COHERENCE,
                score=overall_score,
                description="文本连贯性评分",
                details=coherence_score,
                suggestions=coherence_results.get('recommendations', [])
            ))
        else:
            # 默认连贯性分数
            metrics.append(QualityMetric(
                dimension=QualityDimension.COHERENCE,
                score=0.5,
                description="连贯性检查未执行或失败",
                suggestions=["建议手动检查文本连贯性"]
            ))

        return metrics

    def _calculate_overall_quality(
        self,
        basic_metrics: List[QualityMetric],
        ai_metrics: List[QualityMetric],
        coherence_metrics: List[QualityMetric]
    ) -> QualityAssessment:
        """计算综合质量"""
        all_metrics = basic_metrics + ai_metrics + coherence_metrics

        # 计算加权总分
        total_score = 0.0
        total_weight = 0.0

        for metric in all_metrics:
            weight = self.dimension_weights.get(metric.dimension, 0.1)
            total_score += metric.score * weight
            total_weight += weight

        overall_score = total_score / total_weight if total_weight > 0 else 0.5

        # 确定质量等级
        quality_level = self._determine_quality_level(overall_score)

        # 决定是否需要重新压缩
        should_recompress = overall_score < self.recompression_threshold

        # 生成压缩建议
        compression_recommendations = self._generate_compression_recommendations(
            all_metrics, quality_level
        )

        return QualityAssessment(
            overall_score=overall_score,
            quality_level=quality_level,
            metrics=all_metrics,
            should_recompress=should_recompress,
            compression_recommendations=compression_recommendations
        )

    def _determine_quality_level(self, score: float) -> QualityLevel:
        """确定质量等级"""
        if score >= self.quality_thresholds[QualityLevel.EXCELLENT]:
            return QualityLevel.EXCELLENT
        elif score >= self.quality_thresholds[QualityLevel.GOOD]:
            return QualityLevel.GOOD
        elif score >= self.quality_thresholds[QualityLevel.ACCEPTABLE]:
            return QualityLevel.ACCEPTABLE
        elif score >= self.quality_thresholds[QualityLevel.POOR]:
            return QualityLevel.POOR
        else:
            return QualityLevel.UNACCEPTABLE

    def _generate_compression_recommendations(
        self,
        metrics: List[QualityMetric],
        quality_level: QualityLevel
    ) -> List[str]:
        """生成压缩建议"""
        recommendations = []

        # 根据质量等级生成基础建议
        if quality_level == QualityLevel.UNACCEPTABLE:
            recommendations.append("质量严重不达标，建议重新执行完整压缩流程")
        elif quality_level == QualityLevel.POOR:
            recommendations.append("质量较差，建议调整压缩参数后重新压缩")
        elif quality_level == QualityLevel.ACCEPTABLE:
            recommendations.append("质量基本达标，可进行适度优化")
        else:
            recommendations.append("质量良好，建议保持当前压缩设置")

        # 根据具体指标生成针对性建议
        for metric in metrics:
            if metric.score < 0.6:
                if metric.dimension == QualityDimension.COMPLETENESS:
                    recommendations.append("建议降低压缩级别，保留更多关键信息")
                elif metric.dimension == QualityDimension.READABILITY:
                    recommendations.append("建议优化句子结构，提高可读性")
                elif metric.dimension == QualityDimension.COHERENCE:
                    recommendations.append("建议增强文本连贯性，添加过渡描述")
                elif metric.dimension == QualityDimension.ACCURACY:
                    recommendations.append("建议检查内容准确性，修正错误信息")
                elif metric.dimension == QualityDimension.CONCISENESS:
                    recommendations.append("建议进一步去除冗余内容，提高简洁性")

        return recommendations

    def _should_recompress(self, assessment: QualityAssessment) -> bool:
        """决定是否需要重新压缩"""
        # 基于总体分数
        if assessment.overall_score < self.recompression_threshold:
            return True

        # 基于关键维度分数
        critical_dimensions = [QualityDimension.COMPLETENESS, QualityDimension.ACCURACY]
        for metric in assessment.metrics:
            if metric.dimension in critical_dimensions and metric.score < 0.5:
                return True

        # 基于严重问题
        for metric in assessment.metrics:
            if metric.score < 0.3:
                return True

        return False

    def _generate_recommendations(
        self,
        assessment: QualityAssessment,
        compression_level: Optional[str]
    ) -> List[str]:
        """生成改进建议"""
        recommendations = assessment.compression_recommendations.copy()

        # 添加基于压缩级别的建议
        if compression_level:
            if assessment.should_recompress:
                recommendations.append(f"当前压缩级别 ({compression_level}) 可能过高，建议降低")
            else:
                recommendations.append(f"压缩级别 ({compression_level}) 设置合理")

        # 添加总体建议
        if assessment.quality_level in [QualityLevel.EXCELLENT, QualityLevel.GOOD]:
            recommendations.append("当前质量优秀，可以进入下一阶段处理")
        elif assessment.quality_level == QualityLevel.ACCEPTABLE:
            recommendations.append("质量达标，但仍有改进空间")
        else:
            recommendations.append("建议优先解决质量问题后再继续")

        return recommendations

    def _suggest_next_steps(
        self,
        assessment: QualityAssessment,
        should_recompress: bool
    ) -> List[str]:
        """建议下一步操作"""
        next_steps = []

        if should_recompress:
            next_steps.extend([
                "调整压缩参数",
                "重新执行压缩流程",
                "重新进行质量评估"
            ])
        else:
            next_steps.extend([
                "继续后续处理流程",
                "生成漫画脚本",
                "进行图像生成"
            ])

        # 基于质量等级的建议
        if assessment.quality_level == QualityLevel.EXCELLENT:
            next_steps.append("可以考虑保存当前压缩设置作为模板")
        elif assessment.quality_level == QualityLevel.UNACCEPTABLE:
            next_steps.append("建议检查原始文本质量和适用性")

        return next_steps

    def _fallback_quality_assessment(self, text: str) -> Dict[str, Any]:
        """质量评估失败的备选方案"""
        logger.warning("使用备选质量评估方案")

        # 基础分数
        base_score = 0.5
        if len(text) > 100:
            base_score += 0.1
        if '。' in text:
            base_score += 0.1

        # 创建默认评估结果
        default_assessment = QualityAssessment(
            overall_score=base_score,
            quality_level=self._determine_quality_level(base_score),
            metrics=[
                QualityMetric(
                    dimension=QualityDimension.READABILITY,
                    score=base_score,
                    description="质量评估系统错误，使用默认分数"
                )
            ],
            should_recompress=base_score < self.recompression_threshold,
            compression_recommendations=["建议手动检查文本质量"]
        )

        return {
            'quality_assessment': default_assessment.to_dict(),
            'detailed_metrics': {},
            'recommendations': ["质量评估系统出现错误，建议手动检查"],
            'should_recompress': default_assessment.should_recompress,
            'next_steps': ["建议检查系统状态后重试"]
        }


# 创建单例实例
quality_assessor = QualityAssessor()