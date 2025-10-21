"""
用户反馈处理工作流
User Feedback Handler Workflow

使用LangGraph实现智能用户反馈处理，包括反馈分类、路由决策和执行动作
Implements intelligent user feedback handling using LangGraph, including feedback classification, routing decisions, and action execution
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime
import json
import uuid
from enum import Enum

from langgraph import StateGraph, END

from .state_management import (
    WorkflowState, FeedbackType, WorkflowStatus,
    state_manager
)
from ..services.ai_service import AIService

logger = logging.getLogger(__name__)


class FeedbackAction(str, Enum):
    """反馈动作枚举"""
    REGENERATE_CHARACTER = "regenerate_character"
    REGENERATE_SCENE = "regenerate_scene"
    MODIFY_SCRIPT = "modify_script"
    ADJUST_STYLE = "adjust_style"
    IMPROVE_QUALITY = "improve_quality"
    REQUEST_CLARIFICATION = "request_clarification"
    ESCALATE = "escalate"


class FeedbackWorkflow:
    """用户反馈处理工作流类"""

    def __init__(self):
        self.ai_service = AIService()
        self.state_manager = state_manager
        self.workflow = self._build_workflow()

    def _build_workflow(self) -> StateGraph:
        """构建用户反馈处理工作流图"""
        workflow = StateGraph(WorkflowState)

        # 添加节点
        workflow.add_node("start", self._start_feedback_processing)
        workflow.add_node("classify_feedback", self._classify_feedback)
        workflow.add_node("analyze_context", self._analyze_context)
        workflow.add_node("determine_action", self._determine_action)
        workflow.add_node("execute_action", self._execute_action)
        workflow.add_node("validate_result", self._validate_result)
        workflow.add_node("finalize_feedback", self._finalize_feedback)

        # 设置入口点
        workflow.set_entry_point("start")

        # 定义边（流程）
        workflow.add_edge("start", "classify_feedback")
        workflow.add_edge("classify_feedback", "analyze_context")
        workflow.add_edge("analyze_context", "determine_action")
        workflow.add_edge("determine_action", "execute_action")
        workflow.add_edge("execute_action", "validate_result")
        workflow.add_edge("validate_result", "finalize_feedback")

        # 条件边
        workflow.add_conditional_edges(
            "determine_action",
            self._get_action_route,
            {
                "regenerate": "execute_action",
                "modify": "execute_action",
                "clarify": "finalize_feedback",
                "escalate": "finalize_feedback"
            }
        )

        workflow.add_conditional_edges(
            "validate_result",
            self._should_retry_feedback,
            {
                "retry": "execute_action",
                "finalize": "finalize_feedback",
                "fail": END
            }
        )

        workflow.add_edge("finalize_feedback", END)

        return workflow.compile()

    async def _start_feedback_processing(self, state: WorkflowState) -> WorkflowState:
        """开始反馈处理流程"""
        logger.info(f"开始用户反馈处理工作流: {state['workflow_id']}")

        return self.state_manager.update_state(
            state['workflow_id'],
            {
                'status': WorkflowStatus.RUNNING,
                'updated_at': datetime.now().isoformat()
            }
        )

    async def _classify_feedback(self, state: WorkflowState) -> WorkflowState:
        """分类用户反馈"""
        logger.info("分类用户反馈...")

        feedback_data = state.get('feedback_list', [])
        if not feedback_data:
            return self.state_manager.update_state(
                state['workflow_id'],
                {
                    'error_message': "没有找到反馈数据",
                    'status': WorkflowStatus.FAILED
                }
            )

        latest_feedback = feedback_data[-1]
        feedback_text = latest_feedback.get('text', '')

        try:
            # 构建反馈分类提示词
            classification_prompt = f"""
请分析以下用户反馈，并将其分类到相应的类别中：

用户反馈：
---
{feedback_text}
---

请将反馈分类到以下类型之一：
1. character_issue - 角色相关问题（外貌、性格、行为等）
2. scene_issue - 场景相关问题（背景、环境、氛围等）
3. plot_issue - 情节相关问题（故事逻辑、事件顺序等）
4. style_issue - 风格相关问题（画风、色调、表现手法等）
5. quality_issue - 质量相关问题（图像质量、清晰度、细节等）
6. general - 一般性问题或其他

请以JSON格式返回分类结果：
{{
    "feedback_type": "character_issue",
    "confidence": 0.85,
    "keywords": ["角色", "外貌", "表情"],
    "sentiment": "negative",
    "urgency": "medium",
    "summary": "用户对角色外貌表示不满"
}}
"""

            # 调用AI服务分类反馈
            classification_result = await self.ai_service.generate_text(
                prompt=classification_prompt,
                model_preference="seedream",
                max_tokens=500,
                temperature=0.2
            )

            try:
                classification_data = json.loads(classification_result)
                feedback_type = FeedbackType(classification_data.get('feedback_type', 'general'))
            except (json.JSONDecodeError, ValueError):
                feedback_type = FeedbackType.GENERAL
                classification_data = {'feedback_type': 'general', 'confidence': 0.5}

            return self.state_manager.update_state(
                state['workflow_id'],
                {
                    'feedback_type': feedback_type,
                    'feedback_classification': classification_data,
                    'updated_at': datetime.now().isoformat()
                }
            )

        except Exception as e:
            logger.error(f"反馈分类失败: {e}")
            return self.state_manager.update_state(
                state['workflow_id'],
                {
                    'feedback_type': FeedbackType.GENERAL,
                    'feedback_classification': {'feedback_type': 'general', 'confidence': 0.3},
                    'error_message': f"反馈分类失败: {str(e)}",
                    'updated_at': datetime.now().isoformat()
                }
            )

    async def _analyze_context(self, state: WorkflowState) -> WorkflowState:
        """分析反馈上下文"""
        logger.info("分析反馈上下文...")

        try:
            # 构建上下文分析提示词
            context_prompt = f"""
请分析以下反馈的上下文信息，包括相关的内容和可能的原因：

反馈类型：{state['feedback_type']}
反馈内容：{state['feedback_list'][-1].get('text', '')}

相关上下文信息：
- 原始文本分析：{json.dumps(state.get('text_analysis', {}), ensure_ascii=False)}
- 压缩历史：{json.dumps(state.get('compression_history', []), ensure_ascii=False)}
- 质量分数：{json.dumps(state.get('quality_scores', {}), ensure_ascii=False)}

请分析：
1. 反馈的具体原因
2. 相关的内容元素
3. 可能的解决方案方向
4. 处理的优先级

请以JSON格式返回分析结果：
{{
    "root_cause": "具体原因分析",
    "affected_elements": ["受影响的元素列表"],
    "solution_directions": ["解决方案方向"],
    "priority": "high/medium/low",
    "context_summary": "上下文总结"
}}
"""

            # 调用AI服务分析上下文
            context_result = await self.ai_service.generate_text(
                prompt=context_prompt,
                model_preference="seedream",
                max_tokens=800,
                temperature=0.3
            )

            try:
                context_data = json.loads(context_result)
            except json.JSONDecodeError:
                context_data = {
                    'root_cause': '上下文分析失败',
                    'affected_elements': [],
                    'solution_directions': [],
                    'priority': 'medium',
                    'context_summary': '无法解析分析结果'
                }

            return self.state_manager.update_state(
                state['workflow_id'],
                {
                    'context_analysis': context_data,
                    'updated_at': datetime.now().isoformat()
                }
            )

        except Exception as e:
            logger.error(f"上下文分析失败: {e}")
            return self.state_manager.update_state(
                state['workflow_id'],
                {
                    'context_analysis': {
                        'root_cause': f'分析失败: {str(e)}',
                        'affected_elements': [],
                        'solution_directions': [],
                        'priority': 'medium'
                    },
                    'updated_at': datetime.now().isoformat()
                }
            )

    async def _determine_action(self, state: WorkflowState) -> str:
        """确定处理动作"""
        logger.info("确定反馈处理动作...")

        feedback_type = state.get('feedback_type')
        context_analysis = state.get('context_analysis', {})
        priority = context_analysis.get('priority', 'medium')

        # 根据反馈类型和上下文确定动作
        action_map = {
            FeedbackType.CHARACTER_ISSUE: "regenerate",
            FeedbackType.SCENE_ISSUE: "regenerate",
            FeedbackType.PLOT_ISSUE: "modify",
            FeedbackType.STYLE_ISSUE: "modify",
            FeedbackType.QUALITY_ISSUE: "regenerate",
            FeedbackType.GENERAL: "clarify"
        }

        base_action = action_map.get(feedback_type, "clarify")

        # 根据优先级调整动作
        if priority == "high" and base_action == "clarify":
            base_action = "escalate"

        # 记录决策过程
        decision_data = {
            'feedback_type': feedback_type,
            'context_priority': priority,
            'determined_action': base_action,
            'decision_time': datetime.now().isoformat()
        }

        self.state_manager.update_state(
            state['workflow_id'],
            {
                'action_decision': decision_data,
                'updated_at': datetime.now().isoformat()
            }
        )

        logger.info(f"确定处理动作: {base_action}")
        return base_action

    async def _execute_action(self, state: WorkflowState) -> WorkflowState:
        """执行处理动作"""
        action_decision = state.get('action_decision', {})
        action = action_decision.get('determined_action', 'clarify')

        logger.info(f"执行反馈处理动作: {action}")

        try:
            if action == "regenerate":
                result = await self._execute_regeneration(state)
            elif action == "modify":
                result = await self._execute_modification(state)
            else:
                result = {'status': 'unknown_action', 'message': f'未知动作: {action}'}

            return self.state_manager.update_state(
                state['workflow_id'],
                {
                    'action_result': result,
                    'updated_at': datetime.now().isoformat()
                }
            )

        except Exception as e:
            logger.error(f"执行动作失败: {e}")
            return self.state_manager.update_state(
                state['workflow_id'],
                {
                    'action_result': {
                        'status': 'error',
                        'message': f"执行失败: {str(e)}"
                    },
                    'error_message': f"动作执行失败: {str(e)}",
                    'updated_at': datetime.now().isoformat()
                }
            )

    async def _execute_regeneration(self, state: WorkflowState) -> Dict[str, Any]:
        """执行重新生成动作"""
        feedback_type = state.get('feedback_type')
        feedback_text = state['feedback_list'][-1].get('text', '')

        # 构建重新生成提示词
        regeneration_prompt = f"""
根据以下用户反馈，重新生成相关内容：

反馈类型：{feedback_type}
用户反馈：{feedback_text}

原始内容分析：{json.dumps(state.get('text_analysis', {}), ensure_ascii=False)}

请重新生成满足用户要求的内容，确保：
1. 解决用户提出的问题
2. 保持与整体内容的连贯性
3. 提高质量和用户满意度

请直接返回重新生成的内容。
"""

        try:
            # 调用AI服务重新生成
            regenerated_content = await self.ai_service.generate_text(
                prompt=regeneration_prompt,
                model_preference="seedream",
                max_tokens=2000,
                temperature=0.7
            )

            return {
                'status': 'success',
                'regenerated_content': regenerated_content,
                'regeneration_type': feedback_type,
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            return {
                'status': 'error',
                'message': f"重新生成失败: {str(e)}"
            }

    async def _execute_modification(self, state: WorkflowState) -> Dict[str, Any]:
        """执行修改动作"""
        feedback_type = state.get('feedback_type')
        feedback_text = state['feedback_list'][-1].get('text', '')

        # 构建修改提示词
        modification_prompt = f"""
根据以下用户反馈，对现有内容进行修改：

反馈类型：{feedback_type}
用户反馈：{feedback_text}

当前内容：{state.get('compressed_text', state.get('original_text', ''))}

请进行针对性修改，确保：
1. 直接回应用户的反馈
2. 保持内容的其他部分不变
3. 提升整体质量

请描述具体的修改方案。
"""

        try:
            # 调用AI服务生成修改方案
            modification_plan = await self.ai_service.generate_text(
                prompt=modification_prompt,
                model_preference="seedream",
                max_tokens=1000,
                temperature=0.5
            )

            return {
                'status': 'success',
                'modification_plan': modification_plan,
                'modification_type': feedback_type,
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            return {
                'status': 'error',
                'message': f"修改失败: {str(e)}"
            }

    async def _validate_result(self, state: WorkflowState) -> str:
        """验证处理结果"""
        logger.info("验证反馈处理结果...")

        action_result = state.get('action_result', {})
        result_status = action_result.get('status', 'unknown')

        if result_status == 'success':
            # 进一步验证结果质量
            validation_score = await self._assess_action_quality(state)

            if validation_score >= 0.7:
                return "finalize"
            elif state.get('retry_count', 0) < 2:
                # 增加重试计数
                self.state_manager.update_state(
                    state['workflow_id'],
                    {
                        'retry_count': state.get('retry_count', 0) + 1,
                        'updated_at': datetime.now().isoformat()
                    }
                )
                return "retry"
            else:
                return "finalize"  # 达到重试次数上限
        else:
            # 处理失败
            if state.get('retry_count', 0) < 1:
                self.state_manager.update_state(
                    state['workflow_id'],
                    {
                        'retry_count': state.get('retry_count', 0) + 1,
                        'updated_at': datetime.now().isoformat()
                    }
                )
                return "retry"
            else:
                return "finalize"

    async def _assess_action_quality(self, state: WorkflowState) -> float:
        """评估动作质量"""
        try:
            action_result = state.get('action_result', {})
            feedback_text = state['feedback_list'][-1].get('text', '')

            # 构建质量评估提示词
            quality_prompt = f"""
请评估以下反馈处理结果的质量：

用户反馈：{feedback_text}
处理结果：{json.dumps(action_result, ensure_ascii=False)}

请从以下维度评估质量（0-1分）：
1. 问题解决程度：是否有效解决了用户提出的问题
2. 内容质量：生成或修改的内容质量如何
3. 相关性：结果是否与用户反馈相关
4. 满意度预测：用户可能对结果的满意程度

请返回一个0-1之间的总体质量分数（只需要返回数字）。
"""

            # 调用AI服务评估质量
            quality_result = await self.ai_service.generate_text(
                prompt=quality_prompt,
                model_preference="seedream",
                max_tokens=100,
                temperature=0.1
            )

            try:
                quality_score = float(quality_result.strip())
                return max(0.0, min(1.0, quality_score))  # 确保在0-1范围内
            except ValueError:
                return 0.5  # 默认中等质量

        except Exception as e:
            logger.error(f"质量评估失败: {e}")
            return 0.5

    async def _finalize_feedback(self, state: WorkflowState) -> WorkflowState:
        """完成反馈处理"""
        logger.info("完成用户反馈处理工作流")

        final_result = {
            'feedback_type': state.get('feedback_type'),
            'action_taken': state.get('action_decision', {}).get('determined_action'),
            'action_result': state.get('action_result'),
            'processing_time': datetime.now().isoformat(),
            'retry_count': state.get('retry_count', 0),
            'status': 'completed'
        }

        return self.state_manager.update_state(
            state['workflow_id'],
            {
                'final_result': final_result,
                'status': WorkflowStatus.COMPLETED,
                'updated_at': datetime.now().isoformat()
            }
        )

    def _get_action_route(self, state: WorkflowState) -> str:
        """获取动作路由"""
        action_decision = state.get('action_decision', {})
        return action_decision.get('determined_action', 'clarify')

    def _should_retry_feedback(self, state: WorkflowState) -> str:
        """决定是否重试反馈处理"""
        if state.get('error_message'):
            return "fail"

        action_result = state.get('action_result', {})
        if action_result.get('status') == 'error':
            return "retry" if state.get('retry_count', 0) < 1 else "finalize"

        # 这个决策由 _validate_result 方法处理
        return "finalize"

    async def handle_feedback(
        self,
        feedback_text: str,
        feedback_type: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        workflow_id: Optional[str] = None
    ) -> WorkflowState:
        """处理用户反馈"""

        if not workflow_id:
            workflow_id = str(uuid.uuid4())

        # 准备反馈数据
        feedback_data = {
            'text': feedback_text,
            'type': feedback_type,
            'timestamp': datetime.now().isoformat(),
            'context': context or {}
        }

        # 创建初始状态
        initial_state = self.state_manager.create_state(
            workflow_id=workflow_id,
            workflow_type="feedback_handler",
            original_text="",  # 反馈处理不一定有原始文本
            max_retries=2
        )

        # 添加反馈数据
        self.state_manager.update_state(
            workflow_id,
            {
                'feedback_list': [feedback_data],
                'updated_at': datetime.now().isoformat()
            }
        )

        try:
            # 运行工作流
            logger.info(f"启动用户反馈处理工作流: {workflow_id}")
            result = await self.workflow.ainvoke(initial_state)

            logger.info(f"用户反馈处理工作流完成: {workflow_id}")
            return result

        except Exception as e:
            logger.error(f"反馈处理工作流执行失败: {e}")

            # 更新状态为失败
            self.state_manager.update_state(
                workflow_id,
                {
                    'error_message': f"反馈处理工作流执行失败: {str(e)}",
                    'status': WorkflowStatus.FAILED,
                    'updated_at': datetime.now().isoformat()
                }
            )

            return self.state_manager.get_state(workflow_id)