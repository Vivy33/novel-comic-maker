"""
工作流状态管理
Workflow State Management

提供LangGraph工作流的状态管理和数据结构
Provides state management and data structures for LangGraph workflows
"""

from typing import Dict, List, Any, Optional, TypedDict
from datetime import datetime
import json
from enum import Enum


class WorkflowStatus(str, Enum):
    """工作流状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


class CompressionLevel(str, Enum):
    """文本压缩级别枚举"""
    ORIGINAL = "original"
    LIGHT = "light"
    MEDIUM = "medium"
    HEAVY = "heavy"
    EXTREME = "extreme"


class FeedbackType(str, Enum):
    """反馈类型枚举"""
    CHARACTER_ISSUE = "character_issue"
    SCENE_ISSUE = "scene_issue"
    PLOT_ISSUE = "plot_issue"
    STYLE_ISSUE = "style_issue"
    QUALITY_ISSUE = "quality_issue"
    GENERAL = "general"


class WorkflowState(TypedDict):
    """工作流状态数据结构"""
    # 基础信息
    workflow_id: str
    workflow_type: str
    status: WorkflowStatus
    created_at: str
    updated_at: str

    # 文本相关
    original_text: str
    compressed_text: Optional[str]
    compression_level: CompressionLevel
    compression_history: List[Dict[str, Any]]

    # 分析结果
    text_analysis: Optional[Dict[str, Any]]
    quality_scores: Dict[str, float]

    # 反馈相关
    feedback_list: List[Dict[str, Any]]
    feedback_type: Optional[FeedbackType]

    # 处理结果
    final_result: Optional[Dict[str, Any]]
    error_message: Optional[str]
    retry_count: int
    max_retries: int


class StateManager:
    """工作流状态管理器"""

    def __init__(self):
        self.states: Dict[str, WorkflowState] = {}
        self.state_history: Dict[str, List[WorkflowState]] = {}

    def create_state(
        self,
        workflow_id: str,
        workflow_type: str,
        original_text: str,
        max_retries: int = 3
    ) -> WorkflowState:
        """创建新的工作流状态"""
        state = WorkflowState(
            workflow_id=workflow_id,
            workflow_type=workflow_type,
            status=WorkflowStatus.PENDING,
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
            original_text=original_text,
            compressed_text=None,
            compression_level=CompressionLevel.ORIGINAL,
            compression_history=[],
            text_analysis=None,
            quality_scores={},
            feedback_list=[],
            feedback_type=None,
            final_result=None,
            error_message=None,
            retry_count=0,
            max_retries=max_retries
        )

        self.states[workflow_id] = state
        self.state_history[workflow_id] = [state.copy()]
        return state

    def update_state(
        self,
        workflow_id: str,
        updates: Dict[str, Any]
    ) -> Optional[WorkflowState]:
        """更新工作流状态"""
        if workflow_id not in self.states:
            return None

        state = self.states[workflow_id]
        state.update(updates)
        state['updated_at'] = datetime.now().isoformat()

        # 保存历史记录
        self.state_history[workflow_id].append(state.copy())

        return state

    def get_state(self, workflow_id: str) -> Optional[WorkflowState]:
        """获取工作流状态"""
        return self.states.get(workflow_id)

    def get_state_history(self, workflow_id: str) -> List[WorkflowState]:
        """获取工作流状态历史"""
        return self.state_history.get(workflow_id, [])

    def delete_state(self, workflow_id: str) -> bool:
        """删除工作流状态"""
        if workflow_id in self.states:
            del self.states[workflow_id]
            if workflow_id in self.state_history:
                del self.state_history[workflow_id]
            return True
        return False

    def list_states(
        self,
        workflow_type: Optional[str] = None,
        status: Optional[WorkflowStatus] = None
    ) -> List[WorkflowState]:
        """列出工作流状态"""
        states = list(self.states.values())

        if workflow_type:
            states = [s for s in states if s['workflow_type'] == workflow_type]

        if status:
            states = [s for s in states if s['status'] == status]

        return states

    def save_state_to_file(self, workflow_id: str, file_path: str) -> bool:
        """保存状态到文件"""
        try:
            state = self.get_state(workflow_id)
            if state:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(state, f, ensure_ascii=False, indent=2, default=str)
                return True
        except Exception as e:
            print(f"保存状态失败: {e}")
        return False

    def load_state_from_file(self, file_path: str) -> Optional[WorkflowState]:
        """从文件加载状态"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                state = json.load(f)
                workflow_id = state['workflow_id']
                self.states[workflow_id] = state
                if workflow_id not in self.state_history:
                    self.state_history[workflow_id] = []
                self.state_history[workflow_id].append(state)
                return state
        except Exception as e:
            print(f"加载状态失败: {e}")
        return None


# 全局状态管理器实例
state_manager = StateManager()