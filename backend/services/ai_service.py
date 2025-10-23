"""
AI服务统一接口
Unified Interface for AI Services

封装对不同AI模型提供商的API调用。
"""
import logging
import os
import time
import uuid
from typing import List, Dict, Optional, Any

# 移除对volcenginesdkark的顶层导入，改为在方法内部动态导入

logger = logging.getLogger(__name__)


class ConversationContext:
    """对话上下文管理器"""

    def __init__(self, max_messages: int = 20, max_tokens: int = 8000):
        self.conversation_id = str(uuid.uuid4())
        self.messages: List[Dict[str, str]] = []
        self.max_messages = max_messages
        self.max_tokens = max_tokens
        self.created_at = time.time()
        self.last_updated = time.time()

    def add_message(self, role: str, content: str):
        """添加消息到上下文"""
        message = {
            "role": role,
            "content": content
        }
        self.messages.append(message)
        self.last_updated = time.time()

        # 保持消息数量在限制内
        if len(self.messages) > self.max_messages:
            # 保留系统消息和最近的对话
            system_messages = [msg for msg in self.messages if msg["role"] == "system"]
            recent_messages = self.messages[-(self.max_messages - len(system_messages)):]
            self.messages = system_messages + recent_messages

    def get_messages(self) -> List[Dict[str, str]]:
        """获取所有消息"""
        return self.messages.copy()

    def clear_context(self):
        """清空上下文（保留系统消息）"""
        system_messages = [msg for msg in self.messages if msg["role"] == "system"]
        self.messages = system_messages
        self.last_updated = time.time()

    def get_context_info(self) -> Dict[str, Any]:
        """获取上下文信息"""
        return {
            "conversation_id": self.conversation_id,
            "message_count": len(self.messages),
            "created_at": self.created_at,
            "last_updated": self.last_updated,
            "max_messages": self.max_messages,
            "max_tokens": self.max_tokens
        }


class ContextManager:
    """上下文管理器，管理多个对话会话"""

    def __init__(self):
        self.contexts: Dict[str, ConversationContext] = {}
        self.default_context_id = None

    def create_context(self, max_messages: int = 20, max_tokens: int = 8000) -> str:
        """创建新的对话上下文"""
        context = ConversationContext(max_messages, max_tokens)
        self.contexts[context.conversation_id] = context

        if self.default_context_id is None:
            self.default_context_id = context.conversation_id

        return context.conversation_id

    def get_context(self, context_id: Optional[str] = None) -> Optional[ConversationContext]:
        """获取对话上下文"""
        if context_id is None:
            context_id = self.default_context_id

        return self.contexts.get(context_id) if context_id else None

    def delete_context(self, context_id: str):
        """删除对话上下文"""
        if context_id in self.contexts:
            del self.contexts[context_id]

            if self.default_context_id == context_id:
                self.default_context_id = next(iter(self.contexts.keys()), None)

    def list_contexts(self) -> List[Dict[str, Any]]:
        """列出所有上下文"""
        return [context.get_context_info() for context in self.contexts.values()]


# 全局上下文管理器
context_manager = ContextManager()

class VolcengineService:
    """
    封装火山引擎方舟SDK的AI模型调用。
    SDK会自动从环境变量 ARK_API_KEY 读取密钥。
    """
    def __init__(self):
        try:
            # 优先使用.env文件中的API密钥
            api_key = self._get_api_key_from_env()
            if not api_key:
                logger.error("未找到有效的ARK_API_KEY")
                self.client = None
                return

            # 动态导入，避免在未安装依赖时模块导入失败
            from volcenginesdkarkruntime import Ark  # type: ignore
            self.client = Ark(
                base_url="https://ark.cn-beijing.volces.com/api/v3",
                api_key=api_key
            )
            logger.info("火山引擎方舟SDK客户端初始化成功。")
        except Exception as e:
            logger.error(f"初始化火山引擎方舟SDK客户端失败: {e}")
            logger.warning("请确保已正确设置 ARK_API_KEY 环境变量。")
            self.client = None

    def _get_api_key_from_env(self):
        """从.env文件获取API密钥"""
        try:
            from pathlib import Path
            env_path = Path(__file__).parent.parent.parent / ".env"
            if env_path.exists():
                with open(env_path, 'r') as f:
                    for line in f:
                        if line.startswith('ARK_API_KEY='):
                            return line.split('=', 1)[1].strip().strip('"\'')
        except Exception as e:
            logger.warning(f"读取.env文件失败: {e}")

        # 如果.env文件不存在或读取失败，使用环境变量
        return os.environ.get("ARK_API_KEY")

    def is_available(self) -> bool:
        """检查服务是否可用"""
        return self.client is not None

    def chat_completion(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        response_format: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        调用聊天补全模型 (如 doubao-lite, doubao-flash)。

        Args:
            model: 模型名称
            messages: 消息列表
            temperature: 温度参数
            response_format: 响应格式配置，支持JSON Schema
        """
        if not self.is_available():
            logger.error("火山引擎服务不可用。")
            return None

        try:
            logger.info(f"向模型 {model} 发送请求...")

            # 构建请求参数
            completion_params = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
            }

            # 如果指定了响应格式，添加到参数中
            if response_format:
                completion_params["response_format"] = response_format
                logger.info(f"使用响应格式: {response_format.get('type', 'text')}")

            completion = self.client.chat.completions.create(**completion_params)
            response_content = completion.choices[0].message.content
            logger.info(f"成功接收到模型 {model} 的响应。")
            return response_content
        except Exception as e:
            logger.error(f"调用模型 {model} 失败: {e}")
            return None

    def text_to_image(self, model: str, prompt: str, width: int = 1024, height: int = 1024) -> Optional[str]:
        """
        调用文生图模型 (如 doubao-seedream-4.0)。
        """
        if not self.is_available():
            logger.error("火山引擎服务不可用。")
            return None
        try:
            logger.info(f"向文生图模型 {model} 发送请求...")

            # 转换宽高为尺寸字符串
            if width == 512 and height == 512:
                size = "512x512"
            elif width == 768 and height == 768:
                size = "768x768"
            elif width == 1024 and height == 1024:
                size = "1024x1024"
            elif width == 1536 and height == 1536:
                size = "1536x1536"
            elif width == 2048 and height == 2048:
                size = "2048x2048"
            elif width == 1024 and height == 2048:
                size = "1024x2048"
            elif width == 2048 and height == 1024:
                size = "2048x1024"
            else:
                size = "1024x1024"  # 默认尺寸

            resp = self.client.images.generate(
                model=model,
                prompt=prompt,
                size=size,
                response_format="url",
                watermark=False
            )
            image_url = resp.data[0].url
            logger.info(f"成功接收到文生图模型 {model} 的响应。")
            return image_url
        except Exception as e:
            logger.error(f"调用文生图模型 {model} 失败: {e}")
            return None

    def image_to_image(self, model: str, prompt: str, image_url: str) -> Optional[str]:
        """
        调用图像编辑模型 (doubao-seedream-4-0-250828)。
        """
        if not self.is_available():
            logger.error("火山引擎服务不可用。")
            return None
        try:
            logger.info(f"向图像编辑模型 {model} 发送请求...")
            resp = self.client.images.generate(
                model=model,
                prompt=prompt,
                image=image_url,
                size="1024x1024",
                response_format="url",
                watermark=False
            )
            edited_image_url = resp.data[0].url
            logger.info(f"成功接收到图像编辑模型 {model} 的响应。")
            return edited_image_url
        except Exception as e:
            logger.error(f"调用图像编辑模型 {model} 失败: {e}")
            return None


# 创建全局AI服务实例
volc_service = VolcengineService()

# ------------------ 新增对外统一包装类（异步） ------------------
import time
from pathlib import Path

class AIService:
    """
    对外提供统一的异步接口，并在底层服务不可用时进行优雅降级。
    """
    TEXT_MODELS = [
        "doubao-seed-1-6-flash-250828",
    ]
    IMAGE_MODELS = [
        "doubao-seedream-4-0-250828",
    ]

    def __init__(self, provider: Optional[VolcengineService] = None):
        self.provider = provider or volc_service
        self.context_manager = context_manager

    def is_available(self) -> bool:
        return self.provider.is_available()

    def get_available_models(self) -> List[str]:
        return self.TEXT_MODELS + self.IMAGE_MODELS

    def create_json_schema_response_format(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """创建JSON Schema响应格式"""
        return {
            "type": "json_schema",
            "json_schema": {
                "name": "response",
                "schema": schema,
                "strict": True
            }
        }

    def create_text_analysis_schema(self) -> Dict[str, Any]:
        """创建文本分析JSON Schema"""
        return {
            "type": "object",
            "properties": {
                "summary": {
                    "type": "string",
                    "description": "文本摘要，不超过200字"
                },
                "key_points": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "关键点列表"
                },
                "sentiment": {
                    "type": "string",
                    "enum": ["positive", "negative", "neutral"],
                    "description": "情感倾向"
                },
                "entities": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "type": {"type": "string"},
                            "description": {"type": "string"}
                        }
                    }
                }
            },
            "required": ["summary", "key_points", "sentiment"]
        }

    def create_character_analysis_schema(self) -> Dict[str, Any]:
        """创建角色分析JSON Schema"""
        return {
            "type": "object",
            "properties": {
                "characters": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "description": {"type": "string"},
                            "role": {"type": "string"},
                            "traits": {"type": "array", "items": {"type": "string"}}
                        },
                        "required": ["name", "description", "role"]
                    }
                },
                "relationships": {
                    "type": "object",
                    "description": "角色关系"
                },
                "character_count": {
                    "type": "integer",
                    "description": "角色总数"
                }
            },
            "required": ["characters", "character_count"]
        }

    def create_script_generation_schema(self) -> Dict[str, Any]:
        """创建脚本生成JSON Schema"""
        return {
            "type": "object",
            "properties": {
                "scenes": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "scene_number": {"type": "integer"},
                            "setting": {"type": "string"},
                            "characters": {"type": "array", "items": {"type": "string"}},
                            "dialogue": {"type": "string"},
                            "action": {"type": "string"},
                            "estimated_time": {"type": "string"}
                        },
                        "required": ["scene_number", "setting", "dialogue"]
                    }
                },
                "total_scenes": {
                    "type": "integer",
                    "description": "场景总数"
                },
                "estimated_duration": {
                    "type": "string",
                    "description": "预估总时长"
                }
            },
            "required": ["scenes", "total_scenes"]
        }

    async def health_check(self) -> Dict[str, bool]:
        """
        返回各模型可用状态的字典，用于路由层健康检查。
        若底层不可用，则全部为 False。
        """
        is_up = self.provider.is_available()
        models = self.get_available_models()
        status: Dict[str, bool] = {}
        for m in models:
            status[m] = bool(is_up)
        return status

    async def generate_text(
        self,
        prompt: str,
        model_preference: str = "doubao-seed-1-6-flash-250828",
        max_tokens: int = 1000,
        temperature: float = 0.7,
        context_id: Optional[str] = None,
        use_json_schema: bool = False,
        schema_type: Optional[str] = None
    ) -> str:
        """
        生成文本（用于提示词增强、分析等）。

        Args:
            prompt: 提示词
            model_preference: 模型偏好
            max_tokens: 最大token数
            temperature: 温度参数
            context_id: 上下文ID，用于多轮对话
            use_json_schema: 是否使用JSON Schema
            schema_type: Schema类型 (text_analysis, character_analysis, script_generation)
        """
        model = model_preference if model_preference in self.TEXT_MODELS else self.TEXT_MODELS[0]

        # 获取上下文
        context = self.context_manager.get_context(context_id)
        if not context:
            # 如果没有上下文，创建一个新的
            context_id = self.context_manager.create_context()
            context = self.context_manager.get_context(context_id)

        # 构建消息
        messages = context.get_messages() if context else []
        messages.append({"role": "user", "content": prompt})

        # 构建响应格式
        response_format = None
        if use_json_schema and schema_type:
            if schema_type == "text_analysis":
                schema = self.create_text_analysis_schema()
            elif schema_type == "character_analysis":
                schema = self.create_character_analysis_schema()
            elif schema_type == "script_generation":
                schema = self.create_script_generation_schema()
            else:
                schema = None

            if schema:
                response_format = self.create_json_schema_response_format(schema)

        if self.provider.is_available():
            try:
                result = self.provider.chat_completion(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    response_format=response_format
                )

                if isinstance(result, str) and result.strip():
                    # 将对话添加到上下文
                    if context:
                        context.add_message("user", prompt)
                        context.add_message("assistant", result.strip())

                    return result.strip()
            except Exception as e:
                logger.error(f"AI文本生成失败: {e}")

        # 降级策略
        logger.warning("AI文本服务不可用或失败，使用基础降级结果。")
        fallback_result = f"{prompt}\n\n[enhanced length={min(len(prompt), max_tokens)}]"

        # 即使降级也要添加到上下文
        if context:
            context.add_message("user", prompt)
            context.add_message("assistant", fallback_result)

        return fallback_result

    async def generate_text_with_context(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model_preference: str = "doubao-seed-1-6-flash-250828",
        temperature: float = 0.7,
        context_id: Optional[str] = None,
        clear_context: bool = False
    ) -> Dict[str, Any]:
        """
        带上下文管理的文本生成

        Args:
            prompt: 用户提示词
            system_prompt: 系统提示词
            model_preference: 模型偏好
            temperature: 温度参数
            context_id: 上下文ID
            clear_context: 是否清空上下文
        """
        # 获取或创建上下文
        context = self.context_manager.get_context(context_id)
        if not context:
            context_id = self.context_manager.create_context()
            context = self.context_manager.get_context(context_id)

        # 清空上下文（如果需要）
        if clear_context and context:
            context.clear_context()

        # 添加系统提示词（如果提供且上下文为空）
        if system_prompt and (not context.messages or all(msg["role"] != "system" for msg in context.messages)):
            context.add_message("system", system_prompt)

        # 生成文本
        result = await self.generate_text(
            prompt=prompt,
            model_preference=model_preference,
            temperature=temperature,
            context_id=context_id
        )

        return {
            "result": result,
            "context_id": context_id,
            "context_info": context.get_context_info() if context else None
        }

    async def generate_image(
        self,
        prompt: str,
        model_preference: str = "seedream",
        size: str = "1024x1024",
        quality: str = "standard",
    ) -> str:
        """根据文本生成图像并返回URL。不可用时返回占位符URL。"""
        width, height = self._parse_size(size)
        model = "doubao-seedream-4-0-250828" if "seedream" in model_preference else self.IMAGE_MODELS[0]
        if self.provider.is_available():
            url = self.provider.text_to_image(model=model, prompt=prompt, width=width, height=height)
            if isinstance(url, str) and url:
                return url
        placeholder = f"placeholder://seedream/{width}x{height}/{int(time.time())}"
        logger.warning(f"AI图像服务不可用或失败，使用占位符URL: {placeholder}")
        return placeholder

    async def text_to_image(self, model: str, prompt: str, size: str = "1024x1024") -> str:
        """兼容批处理器的签名，返回图像URL或占位符。"""
        width, height = self._parse_size(size)
        if self.provider.is_available():
            url = self.provider.text_to_image(model=model, prompt=prompt, width=width, height=height)
            if isinstance(url, str) and url:
                return url
        return f"placeholder://{model}/{width}x{height}/{int(time.time())}"

    async def edit_image_with_base64(
        self,
        prompt: str,
        base64_image: str,
        base64_mask: Optional[str] = None,
        model_preference: str = "seedream",
        size: str = "1024x1024",
    ) -> str:
        """使用base64图像进行编辑，返回结果URL或占位符。"""
        width, height = self._parse_size(size)
        model = "doubao-seedream-4-0-250828"

        if self.provider.is_available():
            try:
                # 将base64图像保存为临时文件并通过临时服务器提供访问
                from ..utils.image_utils import decode_base64_to_file
                import tempfile
                import threading
                from http.server import SimpleHTTPRequestHandler
                import socketserver
                import time

                # 创建临时文件保存base64图像
                temp_dir = tempfile.mkdtemp()
                temp_image_path = f"{temp_dir}/input_image.png"
                decode_base64_to_file(base64_image, temp_image_path)

                # 启动一个简单的HTTP服务器来提供图像访问
                # 注意：这是一个简化的实现，在生产环境中应该使用更robust的解决方案
                import socket
                import os

                def find_free_port():
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                        s.bind(('', 0))
                        s.listen(1)
                        port = s.getsockname()[1]
                    return port

                # 简化方案：直接尝试使用占位符URL，因为火山引擎可能支持直接上传
                # 这是一个临时解决方案，实际应该实现文件上传服务
                logger.warning("图生图功能需要公开可访问的图像URL，当前使用占位符URL")

                # 由于火山引擎API限制，暂时返回占位符
                return f"placeholder://edit/{width}x{height}/{int(time.time())}"

            except Exception as e:
                logger.error(f"处理base64图像失败: {e}")
                return f"placeholder://edit/{width}x{height}/{int(time.time())}"

        return f"placeholder://edit/{width}x{height}/{int(time.time())}"

    async def download_image_result(self, image_url: str, output_dir: Optional[str] = None) -> str:
        """
        下载或生成图像到本地并返回路径。
        - http/https: 直接下载
        - placeholder://*: 生成1x1透明PNG文件
        """
        try:
            from ..utils.image_utils import download_image_from_url, decode_base64_to_file  # type: ignore
        except Exception:
            from utils.image_utils import download_image_from_url, decode_base64_to_file  # type: ignore

        from ..config import settings
        base_dir = settings.TEMP_PROCESSING_DIR
        target_dir = Path(output_dir) if output_dir else base_dir
        target_dir.mkdir(parents=True, exist_ok=True)

        filename = f"result_{int(time.time())}.png"
        save_path = str(target_dir / filename)

        try:
            if image_url and image_url.startswith(("http://", "https://")):
                return await download_image_from_url(image_url, save_path)
            tiny_png_base64 = (
                "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9WjhhjQAAAAASUVORK5CYII="
            )
            return decode_base64_to_file(tiny_png_base64, save_path)
        except Exception as e:
            logger.error(f"下载/生成图像失败: {e}")
            tiny_png_base64 = (
                "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9WjhhjQAAAAASUVORK5CYII="
            )
            return decode_base64_to_file(tiny_png_base64, save_path)

    async def image_to_image_with_base64(
        self,
        prompt: str,
        base64_image: str,
        model_preference: str = "doubao-seedream-4-0-250828",
        size: str = "1024x1024",
        strength: float = 0.8
    ) -> str:
        """
        图生图功能 - 使用base64图像作为参考生成新图像

        Args:
            prompt: 描述文本
            base64_image: 参考图像的base64编码
            model_preference: 模型偏好
            size: 图像尺寸
            strength: 变化强度 (0.0-1.0)

        Returns:
            生成图像的URL
        """
        model = "doubao-seedream-4-0-250828"
        if self.provider.is_available():
            try:
                # 将base64图像保存为临时文件并通过临时服务器提供访问
                from ..utils.image_utils import decode_base64_to_file
                import tempfile
                import threading
                from http.server import SimpleHTTPRequestHandler
                import socketserver
                import time

                # 解码base64图像到临时文件
                with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as temp_file:
                    temp_path = temp_file.name
                    decode_base64_to_file(base64_image, temp_path)

                # 启动临时HTTP服务器
                temp_dir = os.path.dirname(temp_path)
                port = 8999  # 固定端口或动态分配
                handler = SimpleHTTPRequestHandler
                httpd = socketserver.TCPServer(("", port), handler)

                def run_server():
                    httpd.serve_forever()

                server_thread = threading.Thread(target=run_server, daemon=True)
                server_thread.start()

                # 等待服务器启动
                time.sleep(0.5)

                # 构建图像URL
                image_filename = os.path.basename(temp_path)
                image_url = f"http://localhost:{port}/{image_filename}"

                # 调用火山引擎图生图API
                result_url = self.provider.image_to_image(
                    model=model,
                    prompt=prompt,
                    image_url=image_url
                )

                # 清理临时文件和服务器
                try:
                    httpd.shutdown()
                    httpd.server_close()
                except:
                    pass
                try:
                    os.unlink(temp_path)
                except:
                    pass

                if result_url:
                    logger.info(f"图生图成功: {result_url}")
                    return result_url
                else:
                    raise Exception("图生图返回空结果")

            except Exception as e:
                logger.error(f"图生图失败: {e}")
                # 降级处理
                return f"placeholder://image-to-image-fallback-{hash(prompt)[:8]}"
        else:
            # 降级返回占位符
            logger.warning("火山引擎服务不可用，返回图生图占位符")
            return f"placeholder://image-to-image-unavailable-{int(time.time())}"

    # 上下文管理API方法
    def create_conversation_context(self, max_messages: int = 20, max_tokens: int = 8000) -> str:
        """创建新的对话上下文"""
        return self.context_manager.create_context(max_messages, max_tokens)

    def get_conversation_context(self, context_id: str) -> Optional[Dict[str, Any]]:
        """获取对话上下文信息"""
        context = self.context_manager.get_context(context_id)
        return context.get_context_info() if context else None

    def delete_conversation_context(self, context_id: str) -> bool:
        """删除对话上下文"""
        if self.context_manager.get_context(context_id):
            self.context_manager.delete_context(context_id)
            return True
        return False

    def list_conversation_contexts(self) -> List[Dict[str, Any]]:
        """列出所有对话上下文"""
        return self.context_manager.list_contexts()

    def clear_conversation_context(self, context_id: str) -> bool:
        """清空对话上下文（保留系统消息）"""
        context = self.context_manager.get_context(context_id)
        if context:
            context.clear_context()
            return True
        return False

    # 结构化数据生成方法
    async def generate_text_analysis(
        self,
        text: str,
        model_preference: str = "doubao-seed-1-6-flash-250828",
        context_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """生成文本分析结果（使用JSON Schema）"""
        prompt = f"""请分析以下文本并提供结构化的分析结果：

文本内容：
{text}

请按照JSON Schema格式返回分析结果，包括：
1. 文本摘要（不超过200字）
2. 关键点列表
3. 情感倾向分析
4. 识别的主要实体

请确保返回有效的JSON格式。"""

        result = await self.generate_text(
            prompt=prompt,
            model_preference=model_preference,
            use_json_schema=True,
            schema_type="text_analysis",
            context_id=context_id
        )

        try:
            import json
            return json.loads(result)
        except json.JSONDecodeError:
            logger.error("文本分析结果不是有效的JSON格式")
            return {
                "error": "Invalid JSON response",
                "raw_result": result
            }

    async def generate_character_analysis(
        self,
        text: str,
        model_preference: str = "doubao-seed-1-6-flash-250828",
        context_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """生成角色分析结果（使用JSON Schema）"""
        prompt = f"""请分析以下文本中的角色信息：

文本内容：
{text}

请按照JSON Schema格式返回角色分析结果，包括：
1. 识别的所有角色（姓名、描述、角色类型、特征）
2. 角色之间的关系图
3. 角色总数统计

请确保返回有效的JSON格式。"""

        result = await self.generate_text(
            prompt=prompt,
            model_preference=model_preference,
            use_json_schema=True,
            schema_type="character_analysis",
            context_id=context_id
        )

        try:
            import json
            return json.loads(result)
        except json.JSONDecodeError:
            logger.error("角色分析结果不是有效的JSON格式")
            return {
                "error": "Invalid JSON response",
                "raw_result": result
            }

    async def generate_script_with_analysis(
        self,
        text_analysis: Dict[str, Any],
        style_requirements: Optional[str] = None,
        model_preference: str = "doubao-seed-1-6-flash-250828",
        context_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """基于文本分析生成漫画脚本（使用JSON Schema）"""
        style_text = f"\n风格要求：{style_requirements}" if style_requirements else ""

        prompt = f"""基于以下文本分析结果，生成漫画脚本：

文本分析：
{text_analysis}
{style_text}

请按照JSON Schema格式返回漫画脚本，包括：
1. 分场景的详细脚本（场景编号、场景设置、角色、对话、动作）
2. 总场景数统计
3. 预估总时长

每个场景应该包含完整的视觉和对话描述。请确保返回有效的JSON格式。"""

        result = await self.generate_text(
            prompt=prompt,
            model_preference=model_preference,
            use_json_schema=True,
            schema_type="script_generation",
            context_id=context_id
        )

        try:
            import json
            return json.loads(result)
        except json.JSONDecodeError:
            logger.error("脚本生成结果不是有效的JSON格式")
            return {
                "error": "Invalid JSON response",
                "raw_result": result
            }

    @staticmethod
    def _parse_size(size: str) -> (int, int):
        try:
            w_str, h_str = size.lower().split('x')
            return int(w_str), int(h_str)
        except Exception:
            return 1024, 1024
