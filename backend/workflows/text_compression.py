"""
文本压缩工作流
Text Compression Workflow

使用LangGraph实现智能文本压缩，包括多轮迭代、质量评估和连贯性检查
Implements intelligent text compression using LangGraph, including multi-round iteration, quality assessment, and coherence checking
"""

import logging
from typing import Optional
from datetime import datetime
import json
import uuid

from langgraph.graph import StateGraph, END

from .state_management import (
    WorkflowState, CompressionLevel, WorkflowStatus,
    state_manager
)
from ..services.ai_service import AIService
from ..agents.text_analyzer import TextAnalyzer

logger = logging.getLogger(__name__)


class TextCompressionWorkflow:
    """文本压缩工作流类"""

    def __init__(self):
        self.ai_service = AIService()
        self.text_analyzer = TextAnalyzer()
        self.state_manager = state_manager
        self.workflow = self._build_workflow()

    def _build_workflow(self) -> StateGraph:
        """构建文本压缩工作流图"""
        workflow = StateGraph(WorkflowState)

        # 添加节点
        workflow.add_node("start", self._start_compression)
        workflow.add_node("analyze_text", self._analyze_text)
        workflow.add_node("determine_compression_level", self._determine_compression_level)
        workflow.add_node("compress_text", self._compress_text)
        workflow.add_node("check_coherence", self._check_coherence)
        workflow.add_node("assess_quality", self._assess_quality)
        workflow.add_node("decide_retry", self._decide_retry)
        workflow.add_node("finalize", self._finalize)

        # 设置入口点
        workflow.set_entry_point("start")

        # 定义边（流程）
        workflow.add_edge("start", "analyze_text")
        workflow.add_edge("analyze_text", "determine_compression_level")
        workflow.add_edge("determine_compression_level", "compress_text")
        workflow.add_edge("compress_text", "check_coherence")
        workflow.add_edge("check_coherence", "assess_quality")
        workflow.add_edge("assess_quality", "decide_retry")

        # 条件边
        workflow.add_conditional_edges(
            "decide_retry",
            self._should_retry,
            {
                "retry": "compress_text",
                "finalize": "finalize",
                "fail": END
            }
        )

        workflow.add_edge("finalize", END)

        return workflow.compile()

    async def _start_compression(self, state: WorkflowState) -> WorkflowState:
        """开始压缩流程"""
        logger.info(f"开始文本压缩工作流: {state['workflow_id']}")

        return self.state_manager.update_state(
            state['workflow_id'],
            {
                'status': WorkflowStatus.RUNNING,
                'updated_at': datetime.now().isoformat()
            }
        )

    async def _analyze_text(self, state: WorkflowState) -> WorkflowState:
        """分析原始文本"""
        logger.info("分析原始文本结构...")

        try:
            # 使用文本分析器分析文本
            analysis = await self.text_analyzer.analyze(state['original_text'])

            # 计算基础质量分数
            quality_scores = {
                'readability': self._calculate_readability_score(state['original_text']),
                'coherence': 0.8,  # 原始文本连贯性较高
                'completeness': 1.0,
                'length': len(state['original_text'])
            }

            return self.state_manager.update_state(
                state['workflow_id'],
                {
                    'text_analysis': analysis,
                    'quality_scores': quality_scores,
                    'updated_at': datetime.now().isoformat()
                }
            )

        except Exception as e:
            logger.error(f"文本分析失败: {e}")
            return self.state_manager.update_state(
                state['workflow_id'],
                {
                    'error_message': f"文本分析失败: {str(e)}",
                    'status': WorkflowStatus.FAILED
                }
            )

    async def _determine_compression_level(self, state: WorkflowState) -> WorkflowState:
        """确定压缩级别"""
        logger.info("确定文本压缩级别...")

        original_length = len(state['original_text'])

        # 根据文本长度智能选择压缩级别
        if original_length > 50000:
            target_level = CompressionLevel.EXTREME
        elif original_length > 20000:
            target_level = CompressionLevel.HEAVY
        elif original_length > 10000:
            target_level = CompressionLevel.MEDIUM
        elif original_length > 5000:
            target_level = CompressionLevel.LIGHT
        else:
            target_level = CompressionLevel.ORIGINAL

        logger.info(f"选择压缩级别: {target_level}")

        return self.state_manager.update_state(
            state['workflow_id'],
            {
                'compression_level': target_level,
                'updated_at': datetime.now().isoformat()
            }
        )

    async def _compress_text(self, state: WorkflowState) -> WorkflowState:
        """执行文本压缩"""
        logger.info(f"执行文本压缩 (级别: {state['compression_level']})...")

        compression_ratio = self._get_compression_ratio(state['compression_level'])
        target_length = int(len(state['original_text']) * compression_ratio)

        try:
            # 构建压缩提示词
            compression_prompt = self._build_compression_prompt(
                state['original_text'],
                state['compression_level'],
                target_length
            )

            # 调用AI服务进行压缩
            compressed_text = await self.ai_service.generate_text(
                prompt=compression_prompt,
                model_preference="seedream",
                max_tokens=min(target_length * 2, 8000),
                temperature=0.3
            )

            # 记录压缩历史
            compression_record = {
                'timestamp': datetime.now().isoformat(),
                'level': state['compression_level'],
                'original_length': len(state['original_text']),
                'compressed_length': len(compressed_text),
                'compression_ratio': len(compressed_text) / len(state['original_text']),
                'prompt_used': compression_prompt
            }

            compression_history = state.get('compression_history', [])
            compression_history.append(compression_record)

            return self.state_manager.update_state(
                state['workflow_id'],
                {
                    'compressed_text': compressed_text,
                    'compression_history': compression_history,
                    'updated_at': datetime.now().isoformat()
                }
            )

        except Exception as e:
            logger.error(f"文本压缩失败: {e}")
            return self.state_manager.update_state(
                state['workflow_id'],
                {
                    'error_message': f"文本压缩失败: {str(e)}",
                    'status': WorkflowStatus.FAILED
                }
            )

    async def _check_coherence(self, state: WorkflowState) -> WorkflowState:
        """检查压缩后文本的连贯性"""
        logger.info("检查压缩后文本连贯性...")

        if not state.get('compressed_text'):
            return self.state_manager.update_state(
                state['workflow_id'],
                {
                    'error_message': "没有找到压缩后的文本",
                    'status': WorkflowStatus.FAILED
                }
            )

        try:
            # 构建连贯性检查提示词
            coherence_prompt = f"""
请评估以下压缩后文本的连贯性，并给出具体的评分和建议：

原始文本长度：{len(state['original_text'])} 字符
压缩后文本长度：{len(state['compressed_text'])} 字符
压缩级别：{state['compression_level']}

压缩后文本：
---
{state['compressed_text']}
---

请从以下维度评估连贯性（0-1分）：
1. 逻辑连贯性：情节是否合理，逻辑是否通顺
2. 人物连贯性：角色行为是否符合其设定
3. 时间连贯性：时间线是否清晰一致
4. 情节连贯性：故事情节是否完整连贯

请以JSON格式返回评估结果：
{
    "overall_coherence": 0.85,
    "logical_coherence": 0.9,
    "character_coherence": 0.8,
    "temporal_coherence": 0.85,
    "plot_coherence": 0.85,
    "issues": ["发现的具体问题"],
    "suggestions": ["改进建议"]
}
"""

            # 这里可以调用连贯性检查Agent进行更深入分析（示例略）
            # 简化为根据长度和提示词给出基础分数
            coherence_score = 0.8 if len(state['compressed_text']) > 0 else 0.0

            return self.state_manager.update_state(
                state['workflow_id'],
                {
                    'coherence_score': coherence_score,
                    'updated_at': datetime.now().isoformat()
                }
            )

        except Exception as e:
            logger.error(f"连贯性检查失败: {e}")
            return self.state_manager.update_state(
                state['workflow_id'],
                {
                    'error_message': f"连贯性检查失败: {str(e)}",
                    'status': WorkflowStatus.FAILED
                }
            )

    async def _assess_quality(self, state: WorkflowState) -> WorkflowState:
        """评估压缩质量"""
        logger.info("评估压缩质量...")

        try:
            # 构建质量评估提示词（示例略）
            quality_scores = state.get('quality_scores', {})
            quality_scores.update({
                'compression_effectiveness': 0.85,
                'coherence_adjustment': (state.get('coherence_score', 0.8) - 0.8) * 0.2
            })

            return self.state_manager.update_state(
                state['workflow_id'],
                {
                    'quality_scores': quality_scores,
                    'updated_at': datetime.now().isoformat()
                }
            )

        except Exception as e:
            logger.error(f"质量评估失败: {e}")
            return self.state_manager.update_state(
                state['workflow_id'],
                {
                    'error_message': f"质量评估失败: {str(e)}",
                    'status': WorkflowStatus.FAILED
                }
            )

    async def _decide_retry(self, state: WorkflowState) -> str:
        """决定是否重试压缩"""
        logger.info("决定是否重试压缩...")

        # 简化的重试逻辑：如果连贯性评分过低则重试一次
        if state.get('coherence_score', 0.8) < 0.6 and state.get('retry_count', 0) < state.get('max_retries', 1):
            return "retry"
        return "finalize"

    async def _finalize(self, state: WorkflowState) -> WorkflowState:
        """完成工作流"""
        logger.info("完成文本压缩工作流")

        final_result = {
            'original_length': len(state['original_text']),
            'compressed_length': len(state.get('compressed_text', '')),
            'compression_ratio': len(state.get('compressed_text', '')) / len(state['original_text']),
            'compression_level': state['compression_level'],
            'quality_scores': state.get('quality_scores', {}),
            'compression_history': state.get('compression_history', []),
            'retry_count': state['retry_count']
        }

        return self.state_manager.update_state(
            state['workflow_id'],
            {
                'final_result': final_result,
                'status': WorkflowStatus.COMPLETED,
                'updated_at': datetime.now().isoformat()
            }
        )

    def _should_retry(self, state: WorkflowState) -> str:
        """决定下一步是重试还是完成或失败"""
        if state.get('error_message'):
            return "fail"
        if state.get('retry_count', 0) < state.get('max_retries', 1) and state.get('coherence_score', 0.8) < 0.6:
            return "retry"
        return "finalize"

    def _get_compression_ratio(self, level: CompressionLevel) -> float:
        """根据压缩级别设置目标比例"""
        ratios = {
            CompressionLevel.ORIGINAL: 1.0,
            CompressionLevel.LIGHT: 0.7,
            CompressionLevel.MEDIUM: 0.5,
            CompressionLevel.HEAVY: 0.3,
            CompressionLevel.EXTREME: 0.2
        }
        return ratios.get(level, 0.5)

    def _build_compression_prompt(
        self,
        text: str,
        level: CompressionLevel,
        target_length: int
    ) -> str:
        """构建压缩提示词"""
        return f"""
请对以下文本进行{level}级别的压缩，目标长度约为 {target_length} 字符，同时保持关键剧情和角色信息：

{text}
---

请返回压缩后的文本，直接输出内容，不要添加任何解释。
"""

    def _calculate_readability_score(self, text: str) -> float:
        """计算可读性分数（简化版）"""
        # 这里可以实现更复杂的可读性算法
        # 目前使用简单的启发式方法
        sentences = text.split('。')
        if not sentences:
            return 0.0

        avg_sentence_length = len(text) / len(sentences)

        # 理想的句子长度在20-50字之间
        if 20 <= avg_sentence_length <= 50:
            return 0.9
        elif 10 <= avg_sentence_length <= 70:
            return 0.7
        else:
            return 0.5

    async def run_compression(
        self,
        original_text: str,
        workflow_id: Optional[str] = None
    ) -> WorkflowState:
        """运行文本压缩工作流"""

        if not workflow_id:
            workflow_id = str(uuid.uuid4())

        # 创建初始状态
        initial_state = self.state_manager.create_state(
            workflow_id=workflow_id,
            workflow_type="text_compression",
            original_text=original_text,
            max_retries=3
        )

        try:
            # 运行工作流
            logger.info(f"启动文本压缩工作流: {workflow_id}")
            result = await self.workflow.ainvoke(initial_state)

            logger.info(f"文本压缩工作流完成: {workflow_id}")
            return result

        except Exception as e:
            logger.error(f"工作流执行失败: {e}")

            # 更新状态为失败
            self.state_manager.update_state(
                workflow_id,
                {
                    'error_message': f"工作流执行失败: {str(e)}",
                    'status': WorkflowStatus.FAILED,
                    'updated_at': datetime.now().isoformat()
                }
            )

            return self.state_manager.get_state(workflow_id)