"""
增强的日志系统
Enhanced Logging System

提供结构化日志、错误分类、性能监控、告警等功能
Provides structured logging, error classification, performance monitoring, alerting, and other features
"""

import logging
import json
import time
import traceback
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, field, asdict
from enum import Enum
import asyncio
from datetime import datetime


class LogLevel(Enum):
    """日志级别"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class ErrorCategory(Enum):
    """错误分类"""
    API_ERROR = "api_error"
    NETWORK_ERROR = "network_error"
    VALIDATION_ERROR = "validation_error"
    BUSINESS_ERROR = "business_error"
    SYSTEM_ERROR = "system_error"
    TIMEOUT_ERROR = "timeout_error"
    RATE_LIMIT_ERROR = "rate_limit_error"
    AUTHENTICATION_ERROR = "authentication_error"
    UNKNOWN_ERROR = "unknown_error"


class AlertLevel(Enum):
    """告警级别"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class LogEntry:
    """日志条目"""
    timestamp: float
    level: LogLevel
    category: str
    message: str
    module: str
    function: str
    line: Optional[int] = None
    error_type: Optional[str] = None
    error_category: Optional[ErrorCategory] = None
    stack_trace: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)
    duration_ms: Optional[float] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None


@dataclass
class ErrorStats:
    """错误统计"""
    total_errors: int = 0
    errors_by_category: Dict[str, int] = field(default_factory=dict)
    errors_by_module: Dict[str, int] = field(default_factory=dict)
    recent_errors: List[LogEntry] = field(default_factory=list)
    critical_alerts: List[LogEntry] = field(default_factory=list)

    def add_error(self, log_entry: LogEntry):
        """添加错误记录"""
        if log_entry.level in [LogLevel.ERROR, LogLevel.CRITICAL]:
            self.total_errors += 1

            # 按分类统计
            if log_entry.error_category:
                category_name = log_entry.error_category.value
                self.errors_by_category[category_name] = self.errors_by_category.get(category_name, 0) + 1

            # 按模块统计
            self.errors_by_module[log_entry.module] = self.errors_by_module.get(log_entry.module, 0) + 1

            # 记录最近的错误（保留最近100条）
            self.recent_errors.append(log_entry)
            if len(self.recent_errors) > 100:
                self.recent_errors.pop(0)

            # 记录严重错误
            if log_entry.level == LogLevel.CRITICAL:
                self.critical_alerts.append(log_entry)
                if len(self.critical_alerts) > 50:
                    self.critical_alerts.pop(0)


class StructuredLogger:
    """结构化日志器"""

    def __init__(
        self,
        name: str,
        log_file: Optional[str] = None,
        max_file_size: int = 10 * 1024 * 1024,  # 10MB
        backup_count: int = 5
    ):
        self.name = name
        self.error_stats = ErrorStats()
        self.performance_metrics = {}

        # 设置标准日志器
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)

        # 清除现有处理器
        self.logger.handlers.clear()

        # 控制台处理器
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)

        # 文件处理器
        if log_file:
            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=max_file_size,
                backupCount=backup_count,
                encoding='utf-8'
            )
            file_handler.setLevel(logging.DEBUG)
            self.logger.addHandler(file_handler)

        # JSON格式化器
        formatter = StructuredFormatter()
        console_handler.setFormatter(formatter)
        file_handler.setFormatter(formatter)

        self.logger.addHandler(console_handler)

        # 异步锁
        self._lock = asyncio.Lock()

    def _create_log_entry(
        self,
        level: LogLevel,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        error_category: Optional[ErrorCategory] = None,
        duration_ms: Optional[float] = None,
        **kwargs
    ) -> LogEntry:
        """创建日志条目"""
        # 获取调用栈信息
        frame = None
        try:
            # 跳过当前函数和调用者的几层
            f = sys._getframe()
            while f:
                if f.f_code.co_filename != __file__:
                    frame = f
                    break
                f = f.f_back
        except:
            pass

        module = "unknown"
        function = "unknown"
        line = None

        if frame:
            module = Path(frame.f_code.co_filename).stem
            function = frame.f_code.co_name
            line = frame.f_lineno

        # 获取错误信息
        error_type = None
        stack_trace = None

        if level in [LogLevel.ERROR, LogLevel.CRITICAL]:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            if exc_type:
                error_type = exc_type.__name__
                stack_trace = traceback.format_exc()

        return LogEntry(
            timestamp=time.time(),
            level=level,
            category=self.name,
            message=message,
            module=module,
            function=function,
            line=line,
            error_type=error_type,
            error_category=error_category,
            stack_trace=stack_trace,
            context=context or {},
            duration_ms=duration_ms,
            **kwargs
        )

    def _log(self, log_entry: LogEntry):
        """内部日志记录方法"""
        # 更新错误统计
        self.error_stats.add_error(log_entry)

        # 记录到标准日志
        level_mapping = {
            LogLevel.DEBUG: logging.DEBUG,
            LogLevel.INFO: logging.INFO,
            LogLevel.WARNING: logging.WARNING,
            LogLevel.ERROR: logging.ERROR,
            LogLevel.CRITICAL: logging.CRITICAL
        }

        log_data = asdict(log_entry)
        log_data['timestamp'] = datetime.fromtimestamp(log_entry.timestamp).isoformat()
        log_data['level'] = log_entry.level.value

        self.logger.log(
            level_mapping[log_entry.level],
            json.dumps(log_data, ensure_ascii=False, default=str)
        )

    async def debug(self, message: str, context: Optional[Dict[str, Any]] = None, **kwargs):
        """调试日志"""
        log_entry = self._create_log_entry(LogLevel.DEBUG, message, context, **kwargs)
        self._log(log_entry)

    async def info(self, message: str, context: Optional[Dict[str, Any]] = None, **kwargs):
        """信息日志"""
        log_entry = self._create_log_entry(LogLevel.INFO, message, context, **kwargs)
        self._log(log_entry)

    async def warning(self, message: str, context: Optional[Dict[str, Any]] = None, **kwargs):
        """警告日志"""
        log_entry = self._create_log_entry(LogLevel.WARNING, message, context, **kwargs)
        self._log(log_entry)

    async def error(
        self,
        message: str,
        error_category: Optional[ErrorCategory] = None,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        """错误日志"""
        log_entry = self._create_log_entry(
            LogLevel.ERROR, message, context, error_category, **kwargs
        )
        self._log(log_entry)

    async def critical(
        self,
        message: str,
        error_category: Optional[ErrorCategory] = None,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        """严重错误日志"""
        log_entry = self._create_log_entry(
            LogLevel.CRITICAL, message, context, error_category, **kwargs
        )
        self._log(log_entry)

    async def performance(
        self,
        operation: str,
        duration_ms: float,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        """性能日志"""
        # 记录性能指标
        if operation not in self.performance_metrics:
            self.performance_metrics[operation] = {
                'count': 0,
                'total_duration': 0.0,
                'min_duration': float('inf'),
                'max_duration': 0.0
            }

        metrics = self.performance_metrics[operation]
        metrics['count'] += 1
        metrics['total_duration'] += duration_ms
        metrics['min_duration'] = min(metrics['min_duration'], duration_ms)
        metrics['max_duration'] = max(metrics['max_duration'], duration_ms)

        # 记录日志
        message = f"操作 {operation} 完成，耗时 {duration_ms:.2f}ms"
        log_entry = self._create_log_entry(
            LogLevel.INFO, message, context, duration_ms=duration_ms, **kwargs
        )
        self._log(log_entry)

    def get_error_stats(self) -> Dict[str, Any]:
        """获取错误统计"""
        return {
            'total_errors': self.error_stats.total_errors,
            'errors_by_category': self.error_stats.errors_by_category.copy(),
            'errors_by_module': self.error_stats.errors_by_module.copy(),
            'recent_error_count': len(self.error_stats.recent_errors),
            'critical_alert_count': len(self.error_stats.critical_alerts),
            'performance_metrics': {
                op: {
                    'count': metrics['count'],
                    'avg_duration': metrics['total_duration'] / metrics['count'],
                    'min_duration': metrics['min_duration'],
                    'max_duration': metrics['max_duration']
                }
                for op, metrics in self.performance_metrics.items()
            }
        }

    def reset_stats(self):
        """重置统计信息"""
        self.error_stats = ErrorStats()
        self.performance_metrics = {}

    def get_recent_errors(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取最近的错误"""
        recent = self.error_stats.recent_errors[-limit:]
        return [asdict(entry) for entry in recent]

    def get_critical_alerts(self, limit: int = 5) -> List[Dict[str, Any]]:
        """获取严重告警"""
        alerts = self.error_stats.critical_alerts[-limit:]
        return [asdict(entry) for entry in alerts]


class StructuredFormatter(logging.Formatter):
    """结构化日志格式化器"""

    def format(self, record):
        try:
            # 尝试解析JSON格式的日志
            log_data = json.loads(record.getMessage())
            return json.dumps(log_data, ensure_ascii=False, indent=None)
        except (json.JSONDecodeError, AttributeError):
            # 如果不是JSON格式，使用传统格式
            return f"{record.levelname} - {record.getMessage()}"


# 全局日志管理器
class LogManager:
    """日志管理器"""

    def __init__(self):
        self.loggers: Dict[str, StructuredLogger] = {}

    def get_logger(
        self,
        name: str,
        log_file: Optional[str] = None,
        **kwargs
    ) -> StructuredLogger:
        """获取或创建结构化日志器"""
        if name not in self.loggers:
            # 确定日志文件路径
            if not log_file:
                log_dir = Path("logs")
                log_dir.mkdir(exist_ok=True)
                log_file = str(log_dir / f"{name}.json")

            self.loggers[name] = StructuredLogger(name, log_file, **kwargs)

        return self.loggers[name]

    def get_all_stats(self) -> Dict[str, Any]:
        """获取所有日志器的统计信息"""
        return {
            'loggers': list(self.loggers.keys()),
            'stats': {name: logger.get_error_stats() for name, logger in self.loggers.items()}
        }

    def reset_all_stats(self):
        """重置所有日志器的统计信息"""
        for logger in self.loggers.values():
            logger.reset_stats()


# 创建全局日志管理器
log_manager = LogManager()


# 便捷函数
def get_logger(name: str, log_file: Optional[str] = None) -> StructuredLogger:
    """获取结构化日志器"""
    return log_manager.get_logger(name, log_file)


async def log_api_call(
    operation: str,
    duration_ms: float,
    success: bool,
    error: Optional[Exception] = None,
    context: Optional[Dict[str, Any]] = None
):
    """记录API调用日志"""
    logger = get_logger("api_calls")

    message = f"API调用 {operation} {'成功' if success else '失败'}"
    if not success and error:
        message += f": {str(error)}"

    log_context = {
        'operation': operation,
        'success': success,
        'duration_ms': duration_ms
    }
    if context:
        log_context.update(context)

    if success:
        await logger.performance(operation, duration_ms, log_context)
    else:
        await logger.error(message, ErrorCategory.API_ERROR, log_context)


async def log_workflow_execution(
    workflow_name: str,
    duration_ms: float,
    success: bool,
    steps: Optional[List[Dict[str, Any]]] = None,
    context: Optional[Dict[str, Any]] = None
):
    """记录工作流执行日志"""
    logger = get_logger("workflows")

    message = f"工作流 {workflow_name} {'执行成功' if success else '执行失败'}"

    log_context = {
        'workflow_name': workflow_name,
        'success': success,
        'duration_ms': duration_ms,
        'steps_count': len(steps) if steps else 0
    }
    if context:
        log_context.update(context)
    if steps:
        log_context['steps'] = steps

    await logger.performance(f"workflow_{workflow_name}", duration_ms, log_context)


async def log_system_event(
    event_type: str,
    message: str,
    severity: str = "info",
    context: Optional[Dict[str, Any]] = None
):
    """记录系统事件日志"""
    logger = get_logger("system_events")

    log_context = {
        'event_type': event_type,
        'severity': severity
    }
    if context:
        log_context.update(context)

    level_map = {
        'debug': LogLevel.DEBUG,
        'info': LogLevel.INFO,
        'warning': LogLevel.WARNING,
        'error': LogLevel.ERROR,
        'critical': LogLevel.CRITICAL
    }

    log_level = level_map.get(severity, LogLevel.INFO)

    if log_level == LogLevel.ERROR:
        await logger.error(message, context=log_context)
    elif log_level == LogLevel.CRITICAL:
        await logger.critical(message, context=log_context)
    elif log_level == LogLevel.WARNING:
        await logger.warning(message, context=log_context)
    else:
        await logger.info(message, context=log_context)