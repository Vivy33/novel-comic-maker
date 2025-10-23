"""
增强的AI服务
Enhanced AI Service

集成重试机制、熔断器、降级处理等高级功能的AI服务
Enhanced AI service with retry mechanisms, circuit breaker, fallback handling, and other advanced features
"""

import logging
import json
import time
from typing import Any, Dict, List, Optional, Union, Callable
import asyncio

from ..utils.retry_handler import api_retry_handler, safe_api_call, with_retry
from ..utils.cost_controller import record_api_cost
from .ai_service import AIService, volc_service

logger = logging.getLogger(__name__)


class EnhancedAIService(AIService):
    """增强的AI服务类，集成重试机制"""

    def __init__(self):
        super().__init__()
        self.call_count = {
            'text_generation': 0,
            'image_generation': 0,
            'image_editing': 0
        }
        self.total_cost = 0.0
        self.start_time = time.time()

    async def enhanced_chat_completion(
        self,
        model: str,
        messages: List[Dict[str, str]],
        response_format: Optional[Dict[str, Any]] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None
    ) -> str:
        """增强的聊天完成API，带有重试机制"""
        async def _chat_completion():
            logger.info(f"向模型 {model} 发送请求...")
            logger.info(f"使用响应格式: {response_format.get('type') if response_format else 'default'}")

            result = volc_service.chat_completion(
                model=model,
                messages=messages,
                response_format=response_format,
                max_tokens=max_tokens,
                temperature=temperature
            )

            if result:
                self.call_count['text_generation'] += 1
                self._update_cost('text_generation', model, len(str(result)))
                logger.info(f"成功接收到模型 {model} 的响应。")
                return result
            else:
                raise Exception("模型返回空结果")

        # 使用重试机制
        return await safe_api_call(
            _chat_completion,
            retry_type="text",
            fallback_response=json.dumps({"error": "API调用失败", "fallback": True})
        )

    async def enhanced_text_to_image(
        self,
        model: str,
        prompt: str,
        width: int = 1024,
        height: int = 1024,
        watermark: bool = False
    ) -> str:
        """增强的文本生成图像API，带有重试机制"""
        async def _text_to_image():
            logger.info(f"向文生图模型 {model} 发送请求...")

            result = volc_service.text_to_image(
                model=model,
                prompt=prompt,
                width=width,
                height=height,
                watermark=watermark
            )

            if result:
                self.call_count['image_generation'] += 1
                self._update_cost('image_generation', model, len(prompt), image_count=1)
                logger.info(f"成功接收到文生图模型 {model} 的响应。")
                return result
            else:
                raise Exception("文生图API返回空结果")

        # 使用重试机制
        return await safe_api_call(
            _text_to_image,
            retry_type="image",
            fallback_response="placeholder://image_generation_failed"
        )

    async def enhanced_image_to_image(
        self,
        model: str,
        prompt: str,
        image_url: str,
        watermark: bool = False
    ) -> str:
        """增强的图像编辑API，带有重试机制"""
        async def _image_to_image():
            logger.info(f"向图像编辑模型 {model} 发送请求...")

            result = volc_service.image_to_image(
                model=model,
                prompt=prompt,
                image_url=image_url,
                watermark=watermark
            )

            if result:
                self.call_count['image_editing'] += 1
                self._update_cost('image_editing', model, len(prompt), image_count=1)
                logger.info(f"成功接收到图像编辑模型 {model} 的响应。")
                return result
            else:
                raise Exception("图像编辑API返回空结果")

        # 使用重试机制
        return await safe_api_call(
            _image_to_image,
            retry_type="image",
            fallback_response="placeholder://image_editing_failed"
        )

    async def enhanced_edit_image_with_base64(
        self,
        prompt: str,
        base64_image: str,
        model_preference: str = "doubao-seedream-4-0-250828"
    ) -> str:
        """增强的base64图像编辑API，带有重试机制"""
        async def _edit_image_with_base64():
            logger.info(f"使用模型 {model_preference} 进行base64图像编辑...")

            result = volc_service.edit_image_with_base64(
                prompt=prompt,
                base64_image=base64_image,
                model_preference=model_preference
            )

            if result and not result.startswith("placeholder://"):
                self.call_count['image_editing'] += 1
                self._update_cost('image_editing', model_preference, len(prompt), image_count=1)
                logger.info(f"成功完成base64图像编辑，使用模型: {model_preference}")
                return result
            else:
                raise Exception("base64图像编辑失败")

        # 使用重试机制
        return await safe_api_call(
            _edit_image_with_base64,
            retry_type="image",
            fallback_response="placeholder://image_editing_failed"
        )

    def _update_cost(self, call_type: str, model: str, input_size: int, **kwargs):
        """使用cost_controller更新成本计算"""
        try:
            # 估算token数量（简化计算：约4个字符=1个token）
            estimated_tokens = input_size // 4

            # 调用cost_controller记录成本
            cost = record_api_cost(
                model_name=model,
                operation_type=call_type,
                input_tokens=estimated_tokens,
                input_length=input_size,
                **kwargs
            )

            # 更新本地统计（保持兼容性）
            self.total_cost += cost
            return cost
        except Exception as e:
            logger.warning(f"成本记录失败: {e}")
            # 降级处理：使用简化的成本估算
            return 0.1  # 默认成本

    def get_usage_stats(self) -> Dict[str, Any]:
        """获取使用统计"""
        runtime = time.time() - self.start_time
        return {
            'runtime_hours': runtime / 3600,
            'call_counts': self.call_count.copy(),
            'total_calls': sum(self.call_count.values()),
            'estimated_cost': self.total_cost,
            'cost_per_hour': self.total_cost / (runtime / 3600) if runtime > 0 else 0,
            'retry_status': api_retry_handler.get_all_status()
        }

    def reset_usage_stats(self):
        """重置使用统计"""
        self.call_count = {
            'text_generation': 0,
            'image_generation': 0,
            'image_editing': 0
        }
        self.total_cost = 0.0
        self.start_time = time.time()
        api_retry_handler.reset_all_metrics()
        logger.info("AI服务使用统计已重置")

    async def batch_text_generation(
        self,
        prompts: List[str],
        model: str = "doubao-seed-1-6-flash-250828",
        max_concurrent: int = 3
    ) -> List[str]:
        """批量文本生成，支持并发控制"""
        logger.info(f"开始批量文本生成，提示数量: {len(prompts)}, 最大并发: {max_concurrent}")

        semaphore = asyncio.Semaphore(max_concurrent)

        async def generate_single(prompt: str) -> str:
            async with semaphore:
                return await self.enhanced_chat_completion(
                    model=model,
                    messages=[{"role": "user", "content": prompt}]
                )

        # 并发执行所有生成任务
        tasks = [generate_single(prompt) for prompt in prompts]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 处理结果
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"批量生成第{i+1}项失败: {result}")
                final_results.append(f"生成失败: {str(result)}")
            else:
                final_results.append(result)

        logger.info(f"批量文本生成完成，成功: {sum(1 for r in final_results if not r.startswith('生成失败'))}/{len(prompts)}")
        return final_results

    async def batch_image_generation(
        self,
        prompts: List[str],
        model: str = "doubao-seedream-4-0-250828",
        max_concurrent: int = 2
    ) -> List[str]:
        """批量图像生成，支持并发控制"""
        logger.info(f"开始批量图像生成，提示数量: {len(prompts)}, 最大并发: {max_concurrent}")

        semaphore = asyncio.Semaphore(max_concurrent)

        async def generate_single(prompt: str) -> str:
            async with semaphore:
                return await self.enhanced_text_to_image(model=model, prompt=prompt)

        # 并发执行所有生成任务
        tasks = [generate_single(prompt) for prompt in prompts]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 处理结果
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"批量图像生成第{i+1}项失败: {result}")
                final_results.append("placeholder://batch_generation_failed")
            else:
                final_results.append(result)

        logger.info(f"批量图像生成完成，成功: {sum(1 for r in final_results if not r.startswith('placeholder://'))}/{len(prompts)}")
        return final_results

    @with_retry(retry_type="workflow")
    async def workflow_with_retry(self, workflow_func: Callable, *args, **kwargs) -> Any:
        """带有重试的工作流执行"""
        return await workflow_func(*args, **kwargs)

    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        try:
            # 测试基础API连通性
            test_response = await self.enhanced_chat_completion(
                model="doubao-seed-1-6-flash-250828",
                messages=[{"role": "user", "content": "健康检查测试"}],
                max_tokens=10
            )

            base_healthy = bool(test_response and len(test_response) > 0)
        except Exception as e:
            base_healthy = False
            test_response = f"健康检查失败: {str(e)}"

        # 获取重试状态
        retry_status = api_retry_handler.get_all_status()

        # 获取使用统计
        usage_stats = self.get_usage_stats()

        return {
            'service_healthy': base_healthy,
            'api_responsive': base_healthy,
            'retry_status': retry_status,
            'usage_stats': usage_stats,
            'timestamp': time.time(),
            'test_response': test_response if isinstance(test_response, str) else str(test_response)
        }


# 创建增强AI服务实例
enhanced_ai_service = EnhancedAIService()


# 兼容性函数，方便现有代码迁移
async def chat_completion_with_retry(
    model: str,
    messages: List[Dict[str, str]],
    response_format: Optional[Dict[str, Any]] = None,
    max_tokens: Optional[int] = None,
    temperature: Optional[float] = None
) -> str:
    """带有重试的聊天完成函数（兼容现有接口）"""
    return await enhanced_ai_service.enhanced_chat_completion(
        model=model,
        messages=messages,
        response_format=response_format,
        max_tokens=max_tokens,
        temperature=temperature
    )


async def text_to_image_with_retry(
    model: str,
    prompt: str,
    width: int = 1024,
    height: int = 1024,
    watermark: bool = False
) -> str:
    """带有重试的文本生成图像函数（兼容现有接口）"""
    return await enhanced_ai_service.enhanced_text_to_image(
        model=model,
        prompt=prompt,
        width=width,
        height=height,
        watermark=watermark
    )


async def image_to_image_with_retry(
    model: str,
    prompt: str,
    image_url: str,
    watermark: bool = False
) -> str:
    """带有重试的图像编辑函数（兼容现有接口）"""
    return await enhanced_ai_service.enhanced_image_to_image(
        model=model,
        prompt=prompt,
        image_url=image_url,
        watermark=watermark
    )


async def edit_image_with_base64_retry(
    prompt: str,
    base64_image: str,
    model_preference: str = "doubao-seedream-4-0-250828"
) -> str:
    """带有重试的base64图像编辑函数（兼容现有接口）"""
    return await enhanced_ai_service.enhanced_edit_image_with_base64(
        prompt=prompt,
        base64_image=base64_image,
        model_preference=model_preference
    )