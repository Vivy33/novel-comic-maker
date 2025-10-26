"""
批量处理优化系统
Batch Processing Optimization System

提供高效的并发处理能力，支持进度跟踪和错误处理
Provides efficient concurrent processing capabilities with progress tracking and error handling
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
import uuid
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)


class BatchStatus(str, Enum):
    """批处理状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PARTIALLY_COMPLETED = "partially_completed"


class TaskStatus(str, Enum):
    """任务状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class BatchTask:
    """批处理任务数据结构"""
    task_id: str
    task_type: str
    task_data: Dict[str, Any]
    priority: int = 1
    dependencies: List[str] = None
    retry_count: int = 0
    max_retries: int = 3
    timeout: Optional[float] = None

    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TaskResult:
    """任务结果数据结构"""
    task_id: str
    status: TaskStatus
    result: Optional[Any] = None
    error: Optional[str] = None
    execution_time: float = 0.0
    retry_count: int = 0
    completed_at: str = ""

    def __post_init__(self):
        if not self.completed_at:
            self.completed_at = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class BatchJob:
    """批处理作业数据结构"""
    job_id: str
    job_name: str
    tasks: List[BatchTask]
    created_at: str = ""
    started_at: str = ""
    completed_at: str = ""
    status: BatchStatus = BatchStatus.PENDING
    max_concurrent_tasks: int = 5
    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        self.total_tasks = len(self.tasks)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class BatchProcessor:
    """批处理器"""

    def __init__(self, max_workers: int = 10):
        self.max_workers = max_workers
        self.active_jobs: Dict[str, BatchJob] = {}
        self.task_results: Dict[str, TaskResult] = {}
        self.task_handlers: Dict[str, Callable] = {}
        self.job_progress_callbacks: Dict[str, List[Callable]] = {}

        # 注册默认任务处理器
        self._register_default_handlers()

    def _register_default_handlers(self):
        """注册默认任务处理器"""
        self.register_task_handler('text_generation', self._handle_text_generation)
        self.register_task_handler('image_generation', self._handle_image_generation)
        self.register_task_handler('file_processing', self._handle_file_processing)
        self.register_task_handler('data_analysis', self._handle_data_analysis)

    async def create_batch_job(
        self,
        job_name: str,
        tasks: List[Dict[str, Any]],
        max_concurrent_tasks: int = 5
    ) -> str:
        """创建批处理作业"""
        job_id = str(uuid.uuid4())

        # 转换任务数据
        batch_tasks = []
        for task_data in tasks:
            task = BatchTask(
                task_id=str(uuid.uuid4()),
                task_type=task_data.get('task_type', 'unknown'),
                task_data=task_data,
                priority=task_data.get('priority', 1),
                dependencies=task_data.get('dependencies', []),
                max_retries=task_data.get('max_retries', 3),
                timeout=task_data.get('timeout')
            )
            batch_tasks.append(task)

        # 创建作业
        job = BatchJob(
            job_id=job_id,
            job_name=job_name,
            tasks=batch_tasks,
            max_concurrent_tasks=max_concurrent_tasks
        )

        self.active_jobs[job_id] = job
        logger.info(f"创建批处理作业: {job_name} ({job_id}), {len(tasks)} 个任务")

        return job_id

    async def execute_batch_job(
        self,
        job_id: str,
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """执行批处理作业"""
        if job_id not in self.active_jobs:
            raise ValueError(f"作业不存在: {job_id}")

        job = self.active_jobs[job_id]
        job.status = BatchStatus.RUNNING
        job.started_at = datetime.now().isoformat()

        if progress_callback:
            self.job_progress_callbacks.setdefault(job_id, []).append(progress_callback)

        try:
            logger.info(f"开始执行批处理作业: {job.job_name}")

            # 按优先级和依赖关系排序任务
            sorted_tasks = self._sort_tasks_by_priority_and_dependencies(job.tasks)

            # 执行任务
            semaphore = asyncio.Semaphore(job.max_concurrent_tasks)
            tasks_to_execute = [
                self._execute_task_with_semaphore(semaphore, task, job_id)
                for task in sorted_tasks
            ]

            # 等待所有任务完成
            await asyncio.gather(*tasks_to_execute, return_exceptions=True)

            # 更新作业状态
            self._update_job_status(job_id)

            result = self._generate_job_result(job_id)
            logger.info(f"批处理作业完成: {job.job_name}")

            return result

        except Exception as e:
            logger.error(f"批处理作业执行失败: {e}")
            job.status = BatchStatus.FAILED
            job.completed_at = datetime.now().isoformat()
            return {
                'job_id': job_id,
                'status': 'failed',
                'error': str(e),
                'total_tasks': job.total_tasks,
                'completed_tasks': job.completed_tasks,
                'failed_tasks': job.failed_tasks
            }

    def _sort_tasks_by_priority_and_dependencies(self, tasks: List[BatchTask]) -> List[BatchTask]:
        """按优先级和依赖关系排序任务"""
        # 简单的拓扑排序，考虑优先级
        sorted_tasks = []
        remaining_tasks = tasks.copy()
        processed_tasks = set()

        while remaining_tasks:
            # 找到没有未处理依赖的任务
            ready_tasks = [
                task for task in remaining_tasks
                if all(dep in processed_tasks for dep in task.dependencies)
            ]

            if not ready_tasks:
                # 如果没有准备好的任务，可能有循环依赖，按优先级处理
                ready_tasks = remaining_tasks

            # 按优先级排序
            ready_tasks.sort(key=lambda t: t.priority, reverse=True)

            # 添加最高优先级的任务
            task = ready_tasks.pop(0)
            sorted_tasks.append(task)
            processed_tasks.add(task.task_id)
            remaining_tasks.remove(task)

        return sorted_tasks

    async def _execute_task_with_semaphore(
        self,
        semaphore: asyncio.Semaphore,
        task: BatchTask,
        job_id: str
    ) -> TaskResult:
        """使用信号量执行任务"""
        async with semaphore:
            return await self._execute_task(task, job_id)

    async def _execute_task(self, task: BatchTask, job_id: str) -> TaskResult:
        """执行单个任务"""
        start_time = datetime.now()

        try:
            logger.debug(f"执行任务: {task.task_type} ({task.task_id})")

            # 检查任务处理器是否存在
            if task.task_type not in self.task_handlers:
                raise ValueError(f"未找到任务处理器: {task.task_type}")

            # 执行任务
            handler = self.task_handlers[task.task_type]

            if task.timeout:
                result = await asyncio.wait_for(
                    handler(task.task_data), timeout=task.timeout
                )
            else:
                result = await handler(task.task_data)

            execution_time = (datetime.now() - start_time).total_seconds()

            task_result = TaskResult(
                task_id=task.task_id,
                status=TaskStatus.COMPLETED,
                result=result,
                execution_time=execution_time,
                retry_count=task.retry_count
            )

            self.task_results[task.task_id] = task_result

            # 更新作业进度
            self._update_job_progress(job_id)

            logger.debug(f"任务完成: {task.task_id}")
            return task_result

        except asyncio.TimeoutError:
            logger.error(f"任务超时: {task.task_id}")
            return await self._handle_task_failure(task, job_id, "任务执行超时", start_time)

        except Exception as e:
            logger.error(f"任务执行失败: {task.task_id}, 错误: {e}")
            return await self._handle_task_failure(task, job_id, str(e), start_time)

    async def _handle_task_failure(
        self,
        task: BatchTask,
        job_id: str,
        error_message: str,
        start_time: datetime
    ) -> TaskResult:
        """处理任务失败"""
        execution_time = (datetime.now() - start_time).total_seconds()

        if task.retry_count < task.max_retries:
            # 重试任务
            task.retry_count += 1
            logger.info(f"重试任务: {task.task_id}, 第 {task.retry_count} 次重试")

            # 等待一段时间再重试
            await asyncio.sleep(2 ** task.retry_count)  # 指数退避

            return await self._execute_task(task, job_id)
        else:
            # 任务最终失败
            task_result = TaskResult(
                task_id=task.task_id,
                status=TaskStatus.FAILED,
                error=error_message,
                execution_time=execution_time,
                retry_count=task.retry_count
            )

            self.task_results[task.task_id] = task_result
            self._update_job_progress(job_id)

            return task_result

    def _update_job_progress(self, job_id: str):
        """更新作业进度"""
        if job_id not in self.active_jobs:
            return

        job = self.active_jobs[job_id]

        # 统计任务状态
        completed_count = 0
        failed_count = 0

        for task in job.tasks:
            if task.task_id in self.task_results:
                result = self.task_results[task.task_id]
                if result.status == TaskStatus.COMPLETED:
                    completed_count += 1
                elif result.status == TaskStatus.FAILED:
                    failed_count += 1

        job.completed_tasks = completed_count
        job.failed_tasks = failed_count

        # 调用进度回调
        callbacks = self.job_progress_callbacks.get(job_id, [])
        for callback in callbacks:
            try:
                progress = completed_count / job.total_tasks if job.total_tasks > 0 else 0
                callback(job_id, progress, completed_count, failed_count)
            except Exception as e:
                logger.error(f"进度回调执行失败: {e}")

    def _update_job_status(self, job_id: str):
        """更新作业状态"""
        if job_id not in self.active_jobs:
            return

        job = self.active_jobs[job_id]
        job.completed_at = datetime.now().isoformat()

        if job.completed_tasks == job.total_tasks:
            job.status = BatchStatus.COMPLETED
        elif job.failed_tasks > 0:
            job.status = BatchStatus.PARTIALLY_COMPLETED
        else:
            job.status = BatchStatus.FAILED

    def _generate_job_result(self, job_id: str) -> Dict[str, Any]:
        """生成作业结果"""
        if job_id not in self.active_jobs:
            return {'error': f'作业不存在: {job_id}'}

        job = self.active_jobs[job_id]

        # 收集任务结果
        task_results = []
        for task in job.tasks:
            if task.task_id in self.task_results:
                task_results.append(self.task_results[task.task_id].to_dict())

        return {
            'job_id': job_id,
            'job_name': job.job_name,
            'status': job.status.value,
            'total_tasks': job.total_tasks,
            'completed_tasks': job.completed_tasks,
            'failed_tasks': job.failed_tasks,
            'success_rate': job.completed_tasks / job.total_tasks if job.total_tasks > 0 else 0,
            'created_at': job.created_at,
            'started_at': job.started_at,
            'completed_at': job.completed_at,
            'task_results': task_results,
            'execution_time': (
                datetime.fromisoformat(job.completed_at) -
                datetime.fromisoformat(job.started_at)
            ).total_seconds() if job.started_at and job.completed_at else 0
        }

    def register_task_handler(self, task_type: str, handler: Callable):
        """注册任务处理器"""
        self.task_handlers[task_type] = handler
        logger.info(f"注册任务处理器: {task_type}")

    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """获取作业状态"""
        if job_id not in self.active_jobs:
            return None

        job = self.active_jobs[job_id]
        return {
            'job_id': job_id,
            'job_name': job.job_name,
            'status': job.status.value,
            'total_tasks': job.total_tasks,
            'completed_tasks': job.completed_tasks,
            'failed_tasks': job.failed_tasks,
            'progress': job.completed_tasks / job.total_tasks if job.total_tasks > 0 else 0,
            'created_at': job.created_at,
            'started_at': job.started_at,
            'completed_at': job.completed_at
        }

    def cancel_job(self, job_id: str) -> bool:
        """取消作业"""
        if job_id not in self.active_jobs:
            return False

        job = self.active_jobs[job_id]
        if job.status in [BatchStatus.COMPLETED, BatchStatus.FAILED, BatchStatus.CANCELLED]:
            return False

        job.status = BatchStatus.CANCELLED
        job.completed_at = datetime.now().isoformat()
        logger.info(f"作业已取消: {job.job_name}")

        return True

    def cleanup_completed_jobs(self, max_age_hours: int = 24):
        """清理已完成的作业"""
        current_time = datetime.now()
        jobs_to_remove = []

        for job_id, job in self.active_jobs.items():
            if job.status in [BatchStatus.COMPLETED, BatchStatus.FAILED, BatchStatus.CANCELLED]:
                if job.completed_at:
                    completed_time = datetime.fromisoformat(job.completed_at)
                    age_hours = (current_time - completed_time).total_seconds() / 3600
                    if age_hours > max_age_hours:
                        jobs_to_remove.append(job_id)

        for job_id in jobs_to_remove:
            del self.active_jobs[job_id]
            # 清理相关的任务结果
            task_ids_to_remove = [
                task_id for task_id in self.task_results.keys()
                if any(task.task_id == task_id for task in self.active_jobs.get(job_id, {}).get('tasks', []))
            ]
            for task_id in task_ids_to_remove:
                del self.task_results[task_id]

            # 清理进度回调
            if job_id in self.job_progress_callbacks:
                del self.job_progress_callbacks[job_id]

        logger.info(f"清理了 {len(jobs_to_remove)} 个已完成的作业")

    # 默认任务处理器
    async def _handle_text_generation(self, task_data: Dict[str, Any]) -> str:
        """处理文本生成任务"""
        from services.ai_service import AIService
        ai_service = AIService()

        prompt = task_data.get('prompt', '')
        model = task_data.get('model', 'seedream')
        max_tokens = task_data.get('max_tokens', 32768)

        return await ai_service.generate_text(prompt, model, max_tokens)

    async def _handle_image_generation(self, task_data: Dict[str, Any]) -> str:
        """处理图像生成任务"""
        from services.ai_service import AIService
        ai_service = AIService()

        prompt = task_data.get('prompt', '')
        model = task_data.get('model', 'doubao-seedream-4-0-250828')
        size = task_data.get('size', '1024x1024')

        return await ai_service.text_to_image(model, prompt, size)

    async def _handle_file_processing(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理文件任务"""
        # 模拟文件处理
        await asyncio.sleep(0.1)
        return {'processed': True, 'file_info': task_data}

    async def _handle_data_analysis(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理数据分析任务"""
        # 模拟数据分析
        await asyncio.sleep(0.2)
        return {'analysis_result': 'completed', 'data_size': len(str(task_data))}


# 创建全局批处理器实例
batch_processor = BatchProcessor()