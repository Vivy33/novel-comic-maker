"""
AI服务统一接口
Unified Interface for AI Services

封装对不同AI模型提供商的API调用。
"""
import logging
from typing import List, Dict, Optional

from volcenginesdkark import ARKApi
from volcenginesdkark.chat.completions import ChatCompletionMessage

logger = logging.getLogger(__name__)

class VolcengineService:
    """
    封装火山引擎方舟SDK的AI模型调用。
    SDK会自动从环境变量 ARK_API_KEY 或 VOLCENGINE_ACCESS_KEY/VOLCENGINE_SECRET_KEY 读取密钥。
    """
    def __init__(self):
        try:
            # SDK会自动处理环境变量的读取和鉴权
            self.client = ARKApi()
            logger.info("火山引擎方舟SDK客户端初始化成功。SDK将自动使用环境变量进行鉴权。")
        except Exception as e:
            logger.error(f"初始化火山引擎方舟SDK客户端失败: {e}")
            logger.warning("请确保已正确设置 ARK_API_KEY 环境变量。")
            self.client = None

    def is_available(self) -> bool:
        """检查服务是否可用"""
        return self.client is not None

    def chat_completion(self, model: str, messages: List[Dict[str, str]], temperature: float = 0.7) -> Optional[str]:
        """
        调用聊天补全模型 (如 doubao-lite, doubao-flash)。

        Args:
            model: 模型端点ID。
            messages: 对话消息列表。
            temperature: 温度参数。

        Returns:
            模型的响应文本，如果失败则返回None。
        """
        if not self.is_available():
            logger.error("火山引擎服务不可用。")
            return None

        try:
            logger.info(f"向模型 {model} 发送请求...")
            completion = self.client.chat.completions.create(
                model=model,
                messages=[
                    ChatCompletionMessage(**msg) for msg in messages
                ],
                temperature=temperature,
            )
            response_content = completion.choices[0].message.content
            logger.info(f"成功接收到模型 {model} 的响应。")
            return response_content
        except Exception as e:
            logger.error(f"调用模型 {model} 失败: {e}")
            return None

    def text_to_image(self, model: str, prompt: str, width: int = 1024, height: int = 1024) -> Optional[str]:
        """
        调用文生图模型 (如 doubao-seedream-4.0)。

        Args:
            model: 模型端点ID。
            prompt: 图像描述。
            width: 图像宽度。
            height: 图像高度。

        Returns:
            生成图像的URL，如果失败则返回None。
        """
        if not self.is_available():
            logger.error("火山引擎服务不可用。")
            return None
        
        try:
            logger.info(f"向文生图模型 {model} 发送请求...")
            resp = self.client.images.generate(
                model=model,
                prompt=prompt,
                width=width,
                height=height,
            )
            image_url = resp.data[0].url
            logger.info(f"成功接收到文生图模型 {model} 的响应。")
            return image_url
        except Exception as e:
            logger.error(f"调用文生图模型 {model} 失败: {e}")
            return None

    def image_to_image(self, model: str, prompt: str, image_url: str) -> Optional[str]:
        """
        调用图生图模型 (如 doubao-seededit-3.0-i2i)。

        Args:
            model: 模型端点ID。
            prompt: 图像修改描述。
            image_url: 原始图像的URL。

        Returns:
            生成图像的URL，如果失败则返回None。
        """
        if not self.is_available():
            logger.error("火山引擎服务不可用。")
            return None

        try:
            logger.info(f"向图生图模型 {model} 发送请求...")
            resp = self.client.images.edit(
                model=model,
                prompt=prompt,
                image_url=image_url,
            )
            edited_image_url = resp.data[0].url
            logger.info(f"成功接收到图生图模型 {model} 的响应。")
            return edited_image_url
        except Exception as e:
            logger.error(f"调用图生图模型 {model} 失败: {e}")
            return None


# 创建全局AI服务实例
# SDK会自动从环境变量中读取密钥
volc_service = VolcengineService()
