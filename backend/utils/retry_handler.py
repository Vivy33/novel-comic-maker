"""
API调用重试处理器
API Call Retry Handler

提供智能重试机制，包含指数退避、熔断器、降级处理等功能
Provides intelligent retry mechanisms with exponential backoff, circuit breaker, and fallback handling
"""

import asyncio
import logging
import time
import random
from typing import Any, Callable, Dict, Optional, Union, List, Type
from dataclasses import dataclass, field
from enum import Enum
import json

logger = logging.getLogger(__name__)


class RetryStrategy(Enum):
    """重试策略"""
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    LINEAR_BACKOFF = "linear_backoff"
    FIXED_INTERVAL = "fixed_interval"
    IMMEDIATE = "immediate"


class CircuitState(Enum):
    """熔断器状态"""
    CLOSED = "closed"      # 正常状态
    OPEN = "open"         # 熔断状态
    HALF_OPEN = "half_open"  # 半开状态


@dataclass
class RetryConfig:
    """重试配置"""
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    backoff_multiplier: float = 2.0
    jitter: bool = True
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF

    # 熔断器配置
    circuit_breaker_threshold: int = 5
    circuit_breaker_timeout: float = 60.0

    # 降级处理配置
    enable_fallback: bool = True
    fallback_response: Optional[Any] = None
    fallback_timeout: float = 10.0


@dataclass
class RetryAttempt:
    """重试尝试记录"""
    attempt: int
    timestamp: float
    error: Optional[Exception] = None
    response: Optional[Any] = None
    duration: float = 0.0
    success: bool = False


@dataclass
class RetryMetrics:
    """重试指标"""
    total_attempts: int = 0
    successful_attempts: int = 0
    failed_attempts: int = 0
    circuit_breaks: int = 0
    fallback_activations: int = 0
    average_response_time: float = 0.0
    attempts: List[RetryAttempt] = field(default_factory=list)

    def success_rate(self) -> float:
        """成功率"""
        if self.total_attempts == 0:
            return 0.0
        return self.successful_attempts / self.total_attempts

    def average_time(self) -> float:
        """平均响应时间"""
        successful_attempts = [a for a in self.attempts if a.success and a.duration > 0]
        if not successful_attempts:
            return 0.0
        return sum(a.duration for a in successful_attempts) / len(successful_attempts)


class CircuitBreaker:
    """熔断器"""

    def __init__(self, threshold: int = 5, timeout: float = 60.0):
        self.threshold = threshold
        self.timeout = timeout
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = 0
        self._lock = asyncio.Lock()

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """通过熔断器调用函数"""
        async with self._lock:
            if self.state == CircuitState.OPEN:
                if time.time() - self.last_failure_time > self.timeout:
                    self.state = CircuitState.HALF_OPEN
                    logger.info("熔断器进入半开状态")
                else:
                    raise Exception("熔断器开启，拒绝调用")

            try:
                result = await func(*args, **kwargs)
                if self.state == CircuitState.HALF_OPEN:
                    self.state = CircuitState.CLOSED
                    self.failure_count = 0
                    logger.info("熔断器恢复到关闭状态")
                return result

            except Exception as e:
                self.failure_count += 1
                self.last_failure_time = time.time()

                if self.failure_count >= self.threshold:
                    self.state = CircuitState.OPEN
                    logger.warning(f"熔断器开启，失败次数: {self.failure_count}")

                raise e

    def get_state(self) -> CircuitState:
        """获取熔断器状态"""
        return self.state

    def reset(self):
        """重置熔断器"""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = 0
        logger.info("熔断器已重置")


class RetryHandler:
    """重试处理器"""

    def __init__(self, config: Optional[RetryConfig] = None):
        self.config = config or RetryConfig()
        self.metrics = RetryMetrics()
        self.circuit_breaker = CircuitBreaker(
            threshold=self.config.circuit_breaker_threshold,
            timeout=self.config.circuit_breaker_timeout
        )

    async def execute_with_retry(
        self,
        func: Callable,
        *args,
        retry_config: Optional[RetryConfig] = None,
        **kwargs
    ) -> Any:
        """执行函数并重试"""
        config = retry_config or self.config
        last_error = None

        for attempt in range(1, config.max_attempts + 1):
            attempt_start = time.time()
            attempt_record = RetryAttempt(attempt=attempt, timestamp=attempt_start)

            try:
                # 通过熔断器执行
                result = await self._execute_with_circuit_breaker(func, *args, **kwargs)

                # 记录成功尝试
                attempt_record.duration = time.time() - attempt_start
                attempt_record.success = True
                attempt_record.response = result

                self.metrics.attempts.append(attempt_record)
                self.metrics.total_attempts += 1
                self.metrics.successful_attempts += 1

                logger.info(f"函数执行成功，尝试次数: {attempt}, 耗时: {attempt_record.duration:.2f}s")
                return result

            except Exception as e:
                # 记录失败尝试
                attempt_record.duration = time.time() - attempt_start
                attempt_record.error = e
                attempt_record.success = False

                self.metrics.attempts.append(attempt_record)
                self.metrics.total_attempts += 1
                self.metrics.failed_attempts += 1

                last_error = e
                logger.warning(f"函数执行失败，尝试次数: {attempt}, 错误: {str(e)}")

                # 如果不是最后一次尝试，计算延迟并等待
                if attempt < config.max_attempts:
                    delay = self._calculate_delay(attempt, config)
                    logger.info(f"等待 {delay:.2f}s 后重试...")
                    await asyncio.sleep(delay)

        # 所有重试都失败，尝试降级处理
        if config.enable_fallback and config.fallback_response is not None:
            logger.warning("所有重试失败，启用降级处理")
            self.metrics.fallback_activations += 1
            return config.fallback_response

        # 没有降级处理，抛出最后的错误
        raise last_error or Exception("未知错误")

    async def _execute_with_circuit_breaker(self, func: Callable, *args, **kwargs) -> Any:
        """通过熔断器执行函数"""
        try:
            return await self.circuit_breaker.call(func, *args, **kwargs)
        except Exception as e:
            if "熔断器开启" in str(e):
                self.metrics.circuit_breaks += 1
            raise e

    def _calculate_delay(self, attempt: int, config: RetryConfig) -> float:
        """计算重试延迟"""
        if config.strategy == RetryStrategy.IMMEDIATE:
            return 0.0
        elif config.strategy == RetryStrategy.FIXED_INTERVAL:
            delay = config.base_delay
        elif config.strategy == RetryStrategy.LINEAR_BACKOFF:
            delay = config.base_delay * attempt
        elif config.strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
            delay = config.base_delay * (config.backoff_multiplier ** (attempt - 1))
        else:
            delay = config.base_delay

        # 限制最大延迟
        delay = min(delay, config.max_delay)

        # 添加抖动
        if config.jitter:
            jitter_range = delay * 0.1
            delay += random.uniform(-jitter_range, jitter_range)

        return max(0.0, delay)

    def get_metrics(self) -> RetryMetrics:
        """获取重试指标"""
        # 更新计算指标
        self.metrics.average_response_time = self.metrics.average_time()
        return self.metrics

    def reset_metrics(self):
        """重置指标"""
        self.metrics = RetryMetrics()
        self.circuit_breaker.reset()
        logger.info("重试处理器指标已重置")

    def get_status(self) -> Dict[str, Any]:
        """获取状态信息"""
        metrics = self.get_metrics()
        return {
            'circuit_breaker_state': self.circuit_breaker.get_state().value,
            'total_attempts': metrics.total_attempts,
            'success_rate': f"{metrics.success_rate():.1%}",
            'average_response_time': f"{metrics.average_response_time:.2f}s",
            'circuit_breaks': metrics.circuit_breaks,
            'fallback_activations': metrics.fallback_activations
        }


class APIRetryHandler:
    """专用API重试处理器"""

    def __init__(self):
        # 为不同类型的API调用创建不同的重试处理器
        self.text_retry_handler = RetryHandler(RetryConfig(
            max_attempts=3,
            base_delay=1.0,
            backoff_multiplier=2.0,
            circuit_breaker_threshold=5,
            enable_fallback=True,
            fallback_response="API调用失败，请稍后重试"
        ))

        self.image_retry_handler = RetryHandler(RetryConfig(
            max_attempts=2,
            base_delay=2.0,
            backoff_multiplier=2.0,
            circuit_breaker_threshold=3,
            enable_fallback=False
        ))

        self.workflow_retry_handler = RetryHandler(RetryConfig(
            max_attempts=2,
            base_delay=5.0,
            backoff_multiplier=1.5,
            circuit_breaker_threshold=3,
            enable_fallback=True,
            fallback_response={"status": "error", "message": "工作流执行失败"}
        ))

    async def retry_text_generation(self, func: Callable, *args, **kwargs) -> Any:
        """重试文本生成API"""
        return await self.text_retry_handler.execute_with_retry(func, *args, **kwargs)

    async def retry_image_generation(self, func: Callable, *args, **kwargs) -> Any:
        """重试图像生成API"""
        return await self.image_retry_handler.execute_with_retry(func, *args, **kwargs)

    async def retry_workflow_execution(self, func: Callable, *args, **kwargs) -> Any:
        """重试工作流执行"""
        return await self.workflow_retry_handler.execute_with_retry(func, *args, **kwargs)

    def get_all_status(self) -> Dict[str, Any]:
        """获取所有重试处理器的状态"""
        return {
            'text_generation': self.text_retry_handler.get_status(),
            'image_generation': self.image_retry_handler.get_status(),
            'workflow_execution': self.workflow_retry_handler.get_status()
        }

    def reset_all_metrics(self):
        """重置所有指标"""
        self.text_retry_handler.reset_metrics()
        self.image_retry_handler.reset_metrics()
        self.workflow_retry_handler.reset_metrics()


# 创建全局重试处理器实例
api_retry_handler = APIRetryHandler()


def with_retry(retry_type: str = "text"):
    """装饰器：为函数添加重试机制"""
    def decorator(func: Callable) -> Callable:
        async def wrapper(*args, **kwargs):
            if retry_type == "text":
                return await api_retry_handler.retry_text_generation(func, *args, **kwargs)
            elif retry_type == "image":
                return await api_retry_handler.retry_image_generation(func, *args, **kwargs)
            elif retry_type == "workflow":
                return await api_retry_handler.retry_workflow_execution(func, *args, **kwargs)
            else:
                # 默认使用文本重试
                return await api_retry_handler.retry_text_generation(func, *args, **kwargs)
        return wrapper
    return decorator


# 便捷函数
async def safe_api_call(
    func: Callable,
    *args,
    retry_type: str = "text",
    fallback_response: Optional[Any] = None,
    **kwargs
) -> Any:
    """安全API调用，带有重试和降级处理"""
    try:
        if retry_type == "text":
            return await api_retry_handler.retry_text_generation(func, *args, **kwargs)
        elif retry_type == "image":
            return await api_retry_handler.retry_image_generation(func, *args, **kwargs)
        elif retry_type == "workflow":
            return await api_retry_handler.retry_workflow_execution(func, *args, **kwargs)
        else:
            return await api_retry_handler.retry_text_generation(func, *args, **kwargs)
    except Exception as e:
        logger.error(f"API调用完全失败: {e}")
        if fallback_response is not None:
            return fallback_response
        raise e