"""
API调用成本控制器
API Call Cost Controller

提供API调用成本监控、限额管理、预警等功能
Provides API call cost monitoring, quota management, alerting, and other features
"""

import time
import json
import threading
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

class CostLevel(Enum):
    """成本级别"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class APIPricing:
    """API定价配置"""
    model_name: str
    cost_per_1k_input_tokens: float
    cost_per_1k_output_tokens: float
    cost_per_image: Optional[float] = None
    max_tokens_per_request: Optional[int] = None


@dataclass
class CostRecord:
    """成本记录"""
    timestamp: float
    model_name: str
    operation_type: str
    input_tokens: int
    output_tokens: int
    cost: float
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None


@dataclass
class CostQuota:
    """成本配额"""
    daily_limit: float
    hourly_limit: float
    monthly_limit: float
    user_id: Optional[str] = None

    # 当前使用量
    daily_usage: float = 0.0
    hourly_usage: float = 0.0
    monthly_usage: float = 0.0

    # 重置时间
    last_daily_reset: float = 0.0
    last_hourly_reset: float = 0.0
    last_monthly_reset: float = 0.0


class CostController:
    """成本控制器"""

    def __init__(self, config_file: Optional[str] = None):
        self.pricing_config = self._load_pricing_config(config_file)
        self.cost_records: List[CostRecord] = []
        self.quotas: Dict[str, CostQuota] = {}
        self.alert_callbacks: List[Callable[[Dict[str, Any]], None]] = []

        # 统计信息
        self.total_cost = 0.0
        self.daily_cost = 0.0
        self.hourly_cost = 0.0
        self.operation_count = 0

        # 重置时间
        self.last_daily_reset = self._get_start_of_day()
        self.last_hourly_reset = self._get_start_of_hour()
        self.last_monthly_reset = self._get_start_of_month()

        # 线程锁
        self._lock = threading.Lock()

        # 启动定期清理
        self._start_cleanup_task()

    def _load_pricing_config(self, config_file: Optional[str]) -> Dict[str, APIPricing]:
        """加载定价配置"""
        default_pricing = {
            "doubao-seed-1-6-flash-250828": APIPricing(
                model_name="doubao-seed-1-6-flash-250828",
                cost_per_1k_input_tokens=0.003,
                cost_per_1k_output_tokens=0.006,
                max_tokens_per_request=8000
            ),
            "doubao-seedream-4-0-250828": APIPricing(
                model_name="doubao-seedream-4-0-250828",
                cost_per_1k_input_tokens=0.0,
                cost_per_1k_output_tokens=0.0,
                cost_per_image=0.2
            )
        }

        if config_file and Path(config_file).exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    custom_pricing = json.load(f)
                    # 更新默认配置
                    for model_name, pricing_data in custom_pricing.items():
                        if model_name in default_pricing:
                            default_pricing[model_name] = APIPricing(
                                model_name=model_name,
                                **pricing_data
                            )
            except Exception as e:
                print(f"加载定价配置失败: {e}")

        return default_pricing

    def _get_start_of_day(self) -> float:
        """获取今日开始时间"""
        now = time.time()
        current_date = time.localtime(now)
        start_of_day = time.mktime((
            current_date.tm_year,
            current_date.tm_mon,
            current_date.tm_mday,
            0, 0, 0, 0, 0, 0
        ))
        return start_of_day

    def _get_start_of_hour(self) -> float:
        """获取当前小时开始时间"""
        now = time.time()
        current_time = time.localtime(now)
        start_of_hour = time.mktime((
            current_time.tm_year,
            current_time.tm_mon,
            current_time.tm_mday,
            current_time.tm_hour,
            0, 0, 0, 0, 0
        ))
        return start_of_hour

    def _get_start_of_month(self) -> float:
        """获取当月开始时间"""
        now = time.time()
        current_time = time.localtime(now)
        start_of_month = time.mktime((
            current_time.tm_year,
            current_time.tm_mon,
            1,
            0, 0, 0, 0, 0, 0
        ))
        return start_of_month

    def _reset_usage_if_needed(self):
        """如果需要，重置使用量"""
        current_time = time.time()

        # 重置日使用量
        if current_time >= self._get_start_of_day() > self.last_daily_reset:
            self.daily_cost = 0.0
            self.last_daily_reset = self._get_start_of_day()

        # 重置小时使用量
        if current_time >= self._get_start_of_hour() > self.last_hourly_reset:
            self.hourly_cost = 0.0
            self.last_hourly_reset = self._get_start_of_hour()

        # 重置月使用量
        if current_time >= self._get_start_of_month() > self.last_monthly_reset:
            self.monthly_cost = 0.0
            self.last_monthly_reset = self._get_start_of_month()

    def calculate_cost(
        self,
        model_name: str,
        operation_type: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
        input_length: int = 0,
        **kwargs
    ) -> float:
        """计算成本"""
        if model_name not in self.pricing_config:
            return 0.0

        pricing = self.pricing_config[model_name]

        if operation_type == "text_generation":
            # 文本生成：基于token数量
            cost = (input_tokens / 1000) * pricing.cost_per_1k_input_tokens + \
                   (output_tokens / 1000) * pricing.cost_per_1k_output_tokens
        elif operation_type == "image_generation":
            # 图像生成：基于图像数量
            image_count = kwargs.get('image_count', 1)
            cost = image_count * (pricing.cost_per_image or 0.02)
        elif operation_type == "image_editing":
            # 图像编辑：基于图像数量
            image_count = kwargs.get('image_count', 1)
            cost = image_count * (pricing.cost_per_image or 0.015)
        else:
            # 默认：基于输入长度估算
            estimated_input_tokens = input_length / 4  # 简化估算
            cost = (estimated_input_tokens / 1000) * pricing.cost_per_1k_input_tokens

        return max(0.0, cost)  # 确保成本非负

    def record_cost(
        self,
        model_name: str,
        operation_type: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
        input_length: int = 0,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        request_id: Optional[str] = None,
        **kwargs
    ) -> float:
        """记录成本"""
        with self._lock:
            # 计算成本
            cost = self.calculate_cost(
                model_name, operation_type, input_tokens, output_tokens, input_length, **kwargs
            )

            # 创建成本记录
            cost_record = CostRecord(
                timestamp=time.time(),
                model_name=model_name,
                operation_type=operation_type,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost=cost,
                user_id=user_id,
                session_id=session_id,
                request_id=request_id
            )

            # 添加到记录
            self.cost_records.append(cost_record)

            # 更新统计
            self.total_cost += cost
            self.operation_count += 1
            self._reset_usage_if_needed()
            self.daily_cost += cost
            self.hourly_cost += cost
            self.monthly_cost += cost

            # 更新用户配额
            if user_id and user_id in self.quotas:
                quota = self.quotas[user_id]
                quota.daily_usage += cost
                quota.hourly_usage += cost
                quota.monthly_usage += cost

            # 检查告警
            self._check_alerts(cost, user_id)

            # 保持记录数量在合理范围内
            if len(self.cost_records) > 10000:
                self.cost_records = self.cost_records[-5000:]

            return cost

    def _check_alerts(self, cost: float, user_id: Optional[str]):
        """检查成本告警"""
        alert_data = {
            'cost': cost,
            'total_cost': self.total_cost,
            'daily_cost': self.daily_cost,
            'hourly_cost': self.hourly_cost,
            'operation_count': self.operation_count,
            'timestamp': time.time(),
            'user_id': user_id
        }

        # 检查总成本告警
        if self.total_cost > 100:  # 总成本超过100元
            alert_data['alert_type'] = 'high_total_cost'
            alert_data['level'] = CostLevel.HIGH.value
        elif self.daily_cost > 20:  # 日成本超过20元
            alert_data['alert_type'] = 'high_daily_cost'
            alert_data['level'] = CostLevel.HIGH.value
        elif self.hourly_cost > 5:  # 小时成本超过5元
            alert_data['alert_type'] = 'high_hourly_cost'
            alert_data['level'] = CostLevel.MEDIUM.value
        elif self.operation_count > 1000:  # 操作次数超过1000
            alert_data['alert_type'] = 'high_operation_count'
            alert_data['level'] = CostLevel.MEDIUM.value
        elif cost > 5:  # 单次操作成本超过5元
            alert_data['alert_type'] = 'expensive_operation'
            alert_data['level'] = CostLevel.HIGH.value
        else:
            return  # 无告警

        # 触发告警回调
        for callback in self.alert_callbacks:
            try:
                callback(alert_data)
            except Exception as e:
                print(f"告警回调执行失败: {e}")

    def set_quota(self, user_id: str, quota: CostQuota):
        """设置用户配额"""
        with self._lock:
            quota.user_id = user_id
            self.quotas[user_id] = quota

    def check_quota(self, user_id: str, cost: float) -> bool:
        """检查用户配额"""
        if user_id not in self.quotas:
            return True  # 无配额限制

        quota = self.quotas[user_id]
        self._reset_usage_if_needed()

        # 检查各级别配额
        if quota.daily_limit > 0 and quota.daily_usage + cost > quota.daily_limit:
            return False
        if quota.hourly_limit > 0 and quota.hourly_usage + cost > quota.hourly_limit:
            return False
        if quota.monthly_limit > 0 and quota.monthly_usage + cost > quota.monthly_limit:
            return False

        return True

    def add_alert_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """添加告警回调"""
        self.alert_callbacks.append(callback)

    def get_cost_stats(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """获取成本统计"""
        with self._lock:
            self._reset_usage_if_needed()

            stats = {
                'total_cost': self.total_cost,
                'daily_cost': self.daily_cost,
                'hourly_cost': self.hourly_cost,
                'monthly_cost': self.monthly_cost,
                'operation_count': self.operation_count,
                'average_cost_per_operation': self.total_cost / self.operation_count if self.operation_count > 0 else 0
            }

            if user_id and user_id in self.quotas:
                quota = self.quotas[user_id]
                stats['user_quota'] = {
                    'daily_limit': quota.daily_limit,
                    'daily_usage': quota.daily_usage,
                    'daily_remaining': max(0, quota.daily_limit - quota.daily_usage),
                    'hourly_limit': quota.hourly_limit,
                    'hourly_usage': quota.hourly_usage,
                    'hourly_remaining': max(0, quota.hourly_limit - quota.hourly_usage),
                    'monthly_limit': quota.monthly_limit,
                    'monthly_usage': quota.monthly_usage,
                    'monthly_remaining': max(0, quota.monthly_limit - quota.monthly_usage)
                }

            return stats

    def get_cost_breakdown(self, hours: int = 24) -> Dict[str, Any]:
        """获取成本分解"""
        with self._lock:
            cutoff_time = time.time() - (hours * 3600)
            recent_records = [r for r in self.cost_records if r.timestamp >= cutoff_time]

            breakdown = {
                'total_cost': sum(r.cost for r in recent_records),
                'operation_count': len(recent_records),
                'by_model': {},
                'by_operation_type': {},
                'hourly_breakdown': {}
            }

            # 按模型分解
            for record in recent_records:
                model = record.model_name
                breakdown['by_model'][model] = breakdown['by_model'].get(model, 0) + record.cost

            # 按操作类型分解
            for record in recent_records:
                op_type = record.operation_type
                breakdown['by_operation_type'][op_type] = breakdown['by_operation_type'].get(op_type, 0) + record.cost

            # 按小时分解
            for record in recent_records:
                hour = int((record.timestamp - cutoff_time) / 3600)
                hour_key = f"hour_{hour}"
                breakdown['hourly_breakdown'][hour_key] = breakdown['hourly_breakdown'].get(hour_key, 0) + record.cost

            return breakdown

    def reset_stats(self):
        """重置统计信息"""
        with self._lock:
            self.cost_records.clear()
            self.total_cost = 0.0
            self.daily_cost = 0.0
            self.hourly_cost = 0.0
            self.monthly_cost = 0.0
            self.operation_count = 0
            self.last_daily_reset = self._get_start_of_day()
            self.last_hourly_reset = self._get_start_of_hour()
            self.last_monthly_reset = self._get_start_of_month()

    def _start_cleanup_task(self):
        """启动定期清理任务"""
        def cleanup():
            while True:
                try:
                    # 每24小时清理一次
                    time.sleep(24 * 3600)
                    with self._lock:
                        # 删除30天前的记录
                        cutoff_time = time.time() - (30 * 24 * 3600)
                        self.cost_records = [r for r in self.cost_records if r.timestamp >= cutoff_time]
                except Exception as e:
                    print(f"成本控制器清理任务失败: {e}")

        cleanup_thread = threading.Thread(target=cleanup, daemon=True)
        cleanup_thread.start()


# 创建全局成本控制器实例
cost_controller = CostController()


# 便捷函数
def calculate_api_cost(
    model_name: str,
    operation_type: str,
    input_tokens: int = 0,
    output_tokens: int = 0,
    input_length: int = 0,
    **kwargs
) -> float:
    """计算API调用成本"""
    return cost_controller.calculate_cost(
        model_name, operation_type, input_tokens, output_tokens, input_length, **kwargs
    )


def record_api_cost(
    model_name: str,
    operation_type: str,
    input_tokens: int = 0,
    output_tokens: int = 0,
    input_length: int = 0,
    user_id: Optional[str] = None,
    **kwargs
) -> float:
    """记录API调用成本"""
    return cost_controller.record_cost(
        model_name, operation_type, input_tokens, output_tokens, input_length, user_id, **kwargs
    )


def check_user_quota(user_id: str, cost: float) -> bool:
    """检查用户配额"""
    return cost_controller.check_quota(user_id, cost)


def get_cost_stats(user_id: Optional[str] = None) -> Dict[str, Any]:
    """获取成本统计"""
    return cost_controller.get_cost_stats(user_id)


def set_user_quota(user_id: str, daily_limit: float, hourly_limit: float = 0, monthly_limit: float = 0):
    """设置用户配额"""
    quota = CostQuota(
        daily_limit=daily_limit,
        hourly_limit=hourly_limit,
        monthly_limit=monthly_limit
    )
    cost_controller.set_quota(user_id, quota)


def add_cost_alert_callback(callback: Callable[[Dict[str, Any]], None]):
    """添加成本告警回调"""
    cost_controller.add_alert_callback(callback)