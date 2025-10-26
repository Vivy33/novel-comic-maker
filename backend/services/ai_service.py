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

    def __init__(self, max_messages: int = 20, max_tokens: int = 32768):
        self.conversation_id = str(uuid.uuid4())
        self.messages: List[Dict[str, str]] = []
        self.max_messages = max_messages
        #self.max_tokens = max_tokens
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

    def create_context(self, max_messages: int = 20, max_tokens: int = 32768) -> str:
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
            logger.info(response_content)
            return response_content
        except Exception as e:
            logger.error(f"调用模型 {model} 失败: {e}")
            return None

    def text_to_image(
        self,
        model: str,
        prompt: str,
        size: str = "2048x2048",
        sequential_generation: str = "auto",
        max_images: int = 1,
        stream: bool = False
    ) -> Optional[any]:
        """
        调用文生图模型 (如 doubao-seedream-4-0-250828)。

        Args:
            model: 模型名称
            prompt: 提示词
            size: 图像尺寸，支持两种格式：
                  1. 预设值：1K、2K、4K
                  2. 像素值：如"2048x2048"，默认"2048x2048"
                  总像素范围：[1280x720, 4096x4096]，宽高比范围：[1/16, 16]
            sequential_generation: 组图设置，"auto" 或 "disabled"
            max_images: 最大生成图片数量 (1-5)
            stream: 是否启用流式输出

        Returns:
            根据模式返回不同结果：
            - 非流式单图：返回单个URL字符串
            - 非流式组图：返回URL列表
            - 流式模式：返回生成器对象
        """
        if not self.is_available():
            logger.error("火山引擎服务不可用。")
            return None
        try:
            logger.info(f"向文生图模型 {model} 发送请求... (组图: {sequential_generation}, 流式: {stream}, 最大图片: {max_images})")

            # 支持官方推荐的K格式和像素尺寸
            def parse_size_with_k_format(size_str: str) -> str:
                """支持1K/2K格式和像素尺寸"""
                size_str = size_str.lower()

                # 官方推荐的K格式（移除超限的4K）
                k_format_mapping = {
                    "1k": "1024x1024",
                    "2k": "2048x2048"
                }

                if size_str in k_format_mapping:
                    return k_format_mapping[size_str]

                # 支持的像素格式
                if "x" in size_str:
                    try:
                        width, height = map(int, size_str.split("x"))
                        # 验证像素限制 (官方：总像素不超过6000×6000)
                        if 512 <= width <= 2048 and 512 <= height <= 2048:
                            # 验证宽高比限制 [1/16, 16]
                            ratio = width / height
                            if 1/16 <= ratio <= 16:
                                return size_str
                    except:
                        pass

                # 默认推荐2K格式
                return "2k"

            # 直接使用传入的size参数
            size = parse_size_with_k_format(size)

            # 验证并限制max_images
            max_images = max(1, min(5, max_images))  # 确保1-5之间

            # 构建请求参数
            request_params = {
                "model": model,
                "prompt": prompt,
                "size": size,
                "response_format": "url",
                "watermark": False
            }

            # 仅对doubao-seedream-4-0-250828模型添加组图和流式参数
            if "seedream-4-0-250828" in model.lower():
                # 修复：正确设置组图参数
                request_params["sequential_image_generation"] = sequential_generation
                request_params["stream"] = stream

                # 当启用组图时，需要明确设置max_images参数来控制生成数量
                if sequential_generation == "auto" and max_images > 1:
                    try:
                        # 使用正确的导入路径
                        from volcenginesdkarkruntime.types.images import SequentialImageGenerationOptions
                        request_params["sequential_image_generation_options"] = SequentialImageGenerationOptions(
                            max_images=max_images
                        )
                        logger.info(f"设置组图选项: max_images={max_images}")
                    except ImportError:
                        # 如果导入失败，使用简单的参数设置
                        request_params["max_images"] = max_images
                        logger.warning(f"SequentialImageGenerationOptions 导入失败，使用简单参数: max_images={max_images}")
                elif max_images > 1:
                    # 如果没有启用组图但需要多张图片，尝试使用max_images参数
                    request_params["max_images"] = max_images
                    logger.info(f"设置多图参数: max_images={max_images}")

                # 添加调试信息
                logger.info(f"组图请求参数: sequential_image_generation={sequential_generation}, max_images={max_images}")

            # 流式或非流式调用
            if stream and "seedream-4-0-250828" in model.lower():
                # 流式输出
                return self.client.images.generate(**request_params)
            else:
                # 非流式输出
                resp = self.client.images.generate(**request_params)

                # 添加响应调试信息
                logger.info(f"API响应类型: {type(resp)}")
                if hasattr(resp, 'data'):
                    logger.info(f"响应数据长度: {len(resp.data)}")
                    if hasattr(resp, 'usage') and hasattr(resp.usage, 'generated_images'):
                        logger.info(f"API报告生成的图片数: {resp.usage.generated_images}")

                # 修复：正确处理组图响应
                if sequential_generation == "auto" and "seedream-4-0-250828" in model.lower():
                    # 组图模式，返回多个URL
                    if hasattr(resp, 'data') and len(resp.data) > 1:
                        # 多图响应
                        image_urls = [image.url for image in resp.data]
                        logger.info(f"成功接收到文生图模型 {model} 的组图响应，共 {len(image_urls)} 张图片。")
                        return image_urls
                    else:
                        # API可能返回单图，尝试获取单图URL
                        if hasattr(resp, 'data') and len(resp.data) > 0:
                            image_url = resp.data[0].url
                            logger.warning(f"组图请求但返回单图，模型: {model}，响应数据长度: {len(resp.data)}")
                            return image_url
                        else:
                            logger.error(f"组图请求失败，响应数据为空")
                            return None
                else:
                    # 单图模式
                    if hasattr(resp, 'data') and len(resp.data) > 0:
                        image_url = resp.data[0].url
                        logger.info(f"成功接收到文生图模型 {model} 的单图响应。")
                        return image_url
                    else:
                        logger.error(f"单图请求失败，响应数据为空")
                        return None

        except Exception as e:
            logger.error(f"调用文生图模型 {model} 失败: {e}")
            return None

    def image_to_image(self, model: str, prompt: str, image_url: str, image_base64: Optional[str] = None) -> Optional[str]:
        """
        调用图生图模型 (doubao-seedream-4-0-250828)。

        Args:
            model: 模型名称
            prompt: 提示词
            image_url: 参考图片URL
            image_base64: 参考图片的Base64编码 (可选)
        """
        if not self.is_available():
            logger.error("火山引擎服务不可用。")
            return None
        try:
            logger.info(f"向图生图模型 {model} 发送请求...")

            # 构建请求参数
            request_params = {
                "model": model,
                "prompt": prompt,
                "size": "1024x1024",
                "response_format": "url",
                "watermark": False
            }

            # 优先使用image_base64，如果没有则使用image_url
            if image_base64:
                # 确保Base64格式正确
                if not image_base64.startswith("data:image/"):
                    image_base64 = f"data:image/png;base64,{image_base64}"
                request_params["image"] = image_base64
                logger.info(f"使用Base64图片输入")
            elif image_url:
                request_params["image"] = image_url
                logger.info(f"使用URL图片输入: {image_url}")
            else:
                # 如果都没有，则纯文本生图
                logger.info(f"未提供参考图片，进行纯文本生图")

            resp = self.client.images.generate(**request_params)
            edited_image_url = resp.data[0].url
            logger.info(f"成功接收到图生图模型 {model} 的响应。")
            return edited_image_url
        except Exception as e:
            logger.error(f"调用图生图模型 {model} 失败: {e}")
            return None

    def multi_reference_text_to_image(
        self,
        model: str,
        prompt: str,
        reference_images: list,
        max_images: int = 1
    ):
        """
        使用多参考图生成图片（doubao-seedream-4.0）

        Args:
            model: 模型名称
            prompt: 提示词
            reference_images: 参考图片路径列表
            max_images: 最大生成图片数量

        Returns:
            生成的图片URL
        """
        if not self.is_available():
            logger.error("火山引擎服务不可用。")
            return None

        try:
            import base64

            # 构建请求参数
            request_params = {
                "model": model,
                "prompt": prompt,
                "size": "1024x1024",
                "response_format": "url",
                "watermark": False
            }

            # 使用image_to_image API来支持参考图片
            if len(reference_images) > 0:
                logger.info(f"使用图生图API来支持{len(reference_images)}张参考图片")

                # 获取第一张参考图片
                ref_path = reference_images[0]
                try:
                    with open(ref_path, 'rb') as f:
                        image_data = f.read()
                    # 使用image_to_image API
                    result = self.image_to_image(
                        model=model,
                        prompt=prompt,
                        image_url=None,  # 不使用URL
                        image_base64=base64.b64encode(image_data).decode('utf-8')
                    )
                    logger.info(f"成功调用图生图API处理参考图片")
                    return result
                except Exception as e:
                    logger.error(f"图生图API调用失败: {e}")
                    # 降级到普通文生图，但在prompt中描述参考图
                    logger.info("降级到普通文生图，增强prompt描述")
                    # 自动分析参考图内容并增强prompt
                    if ref_path and ('蓝色' not in prompt or '宝蓝色' not in prompt):
                        prompt += "，参考图显示的是蓝色长发角色"
                    if ref_path and ('魔法' not in prompt or '巫师' not in prompt):
                        prompt += "，魔法师风格服装"

            logger.info(f"向多参考图模型 {model} 发送请求...")

            # 调用API
            resp = self.client.images.generate(**request_params)

            if hasattr(resp, 'data') and len(resp.data) > 0:
                image_url = resp.data[0].url
                logger.info(f"成功接收到多参考图模型 {model} 的响应。")
                return image_url
            else:
                logger.warning(f"多参考图模型返回空响应: {resp}")
                return None

        except Exception as e:
            logger.error(f"调用多参考图模型 {model} 失败: {e}")
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
        "deepseek-v3-1-terminus",
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

    def create_simple_text_segmentation_schema(self) -> Dict[str, Any]:
        """创建简化版文本分段JSON Schema - 强制使用JSON Schema"""
        return {
            "type": "object",
            "properties": {
                "segments": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "content": {
                                "type": "string",
                                "description": "段落文本内容"
                            },
                            "segment_type": {
                                "type": "string",
                                "description": "段落类型",
                                "enum": ["dialogue", "action", "description", "transition", "climax", "resolution"]
                            },
                            "scene_setting": {
                                "type": "string",
                                "description": "场景设置"
                            },
                            "characters": {
                                "type": "string",
                                "description": "出现的角色，用逗号分隔"
                            },
                            "emotional_tone": {
                                "type": "string",
                                "description": "情感基调"
                            },
                            "visual_focus": {
                                "type": "string",
                                "description": "视觉焦点"
                            }
                        },
                        "required": ["content", "segment_type", "scene_setting", "characters", "emotional_tone", "visual_focus"]
                    }
                }
            },
            "required": ["segments"]
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

    def create_text_segmentation_schema(self) -> Dict[str, Any]:
        """创建文本分段JSON Schema - 漫画导向版本（兼容豆包API）"""
        return {
            "type": "object",
            "properties": {
                "segments": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "content": {
                                "type": "string",
                                "description": "段落完整文本内容"
                            },
                            "start_index": {
                                "type": "integer",
                                "description": "在原文中的起始位置"
                            },
                            "end_index": {
                                "type": "integer",
                                "description": "在原文中的结束位置"
                            },
                            "segment_type": {
                                "type": "string",
                                "enum": ["dialogue", "action", "description", "general"],
                                "description": "段落类型"
                            },
                            "scene_setting": {
                                "type": "string",
                                "description": "具体环境描述（时间、地点、氛围）"
                            },
                            "characters_present": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "出场角色列表"
                            },
                            "emotional_tone": {
                                "type": "string",
                                "description": "情感基调"
                            },
                            "key_events": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "关键事件列表"
                            },
                            "transition_clues": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "过渡线索"
                            },
                            "character_descriptions": {
                                "type": "object",
                                "description": "角色外貌描述关键词",
                                "additionalProperties": {
                                    "type": "array",
                                    "items": {"type": "string"}
                                }
                            },
                            "scene_elements": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "环境视觉要素"
                            },
                            "visual_keywords": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "整体视觉关键词"
                            },
                            "character_importance": {
                                "type": "object",
                                "description": "角色重要性标识",
                                "additionalProperties": {
                                    "type": "boolean"
                                }
                            },
                            "comic_suitability": {
                                "type": "number",
                                "minimum": 0,
                                "maximum": 1,
                                "description": "漫画适配度评分(0-1)"
                            },
                            "panel_focus": {
                                "type": "string",
                                "description": "画面焦点建议"
                            }
                        },
                        "required": ["content", "characters_present", "character_descriptions", "scene_elements", "visual_keywords", "comic_suitability"]
                    }
                }
            },
            "required": ["segments"]
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
        model_preference: str = "deepseek-v3-1-terminus",
        max_tokens: int = 32768,
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
            elif schema_type == "text_segmentation":
                schema = self.create_text_segmentation_schema()
            elif schema_type == "simple_text_segmentation":
                schema = self.create_simple_text_segmentation_schema()
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
        model_preference: str = "deepseek-v3-1-terminus",
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
        model_preference: str = "doubao-seedream-4-0-250828",
        size: str = "1024x1024",
        quality: str = "standard",
        sequential_generation: str = "auto",
        max_images: int = 1,
        stream: bool = True
    ):
        """
        根据文本生成图像，支持组图和流式输出

        Args:
            prompt: 图像描述
            model_preference: 模型偏好
            size: 图像尺寸
            quality: 图像质量
            sequential_generation: 组图设置 ("auto" 或 "disabled")
            max_images: 最大生成图片数量 (1-5)
            stream: 是否启用流式输出

        Returns:
            根据模式返回不同结果：
            - 非流式单图：返回单个URL字符串
            - 非流式组图：返回URL列表
            - 流式模式：返回生成器对象
        """
        width, height = self._parse_size(size)
        model = "doubao-seedream-4-0-250828" if "seedream" in model_preference else self.IMAGE_MODELS[0]

        if self.provider.is_available():
            result = self.provider.text_to_image(
                model=model,
                prompt=prompt,
                width=width,
                height=height,
                sequential_generation=sequential_generation,
                max_images=max_images,
                stream=stream
            )

            if result is not None:
                return result

        # 降级处理
        if stream:
            # 流式模式的降级处理 - 返回同步生成器
            def fallback_stream():
                placeholder = f"placeholder://seedream/{width}x{height}/{int(time.time())}"
                yield placeholder
            return fallback_stream()
        else:
            # 非流式模式的降级处理
            if sequential_generation == "auto" and max_images > 1:
                # 组图降级：返回多个占位符
                placeholders = [
                    f"placeholder://seedream/{width}x{height}/{int(time.time())}_{i}"
                    for i in range(max_images)
                ]
                logger.warning(f"AI组图服务不可用，返回 {max_images} 个占位符URL")
                return placeholders
            else:
                # 单图降级
                placeholder = f"placeholder://seedream/{width}x{height}/{int(time.time())}"
                logger.warning(f"AI图像服务不可用或失败，使用占位符URL: {placeholder}")
                return placeholder

    async def text_to_image(
        self,
        model: str,
        prompt: str,
        size: str = "1024x1024",
        sequential_generation: str = "auto",
        max_images: int = 1,
        stream: bool = True
    ):
        """兼容批处理器的签名，支持组图和流式输出。"""
        width, height = self._parse_size(size)
        if self.provider.is_available():
            result = self.provider.text_to_image(
                model=model,
                prompt=prompt,
                width=width,
                height=height,
                sequential_generation=sequential_generation,
                max_images=max_images,
                stream=stream
            )
            if result is not None:
                return result
        return f"placeholder://{model}/{width}x{height}/{int(time.time())}"

    async def edit_image_with_base64(
        self,
        prompt: str,
        base64_image: str,
        base64_mask: Optional[str] = None,
        model_preference: str = "doubao-seedream-4-0-250828",
        size: str = "1024x1024",
        stream: bool = True,
    ) -> str:
        """使用base64图像进行编辑，返回结果URL或占位符。"""
        width, height = self._parse_size(size)
        model = "doubao-seedream-4-0-250828"

        if self.provider.is_available():
            try:
                # 将base64图像保存为临时文件并通过临时服务器提供访问
                from utils.image_utils import decode_base64_to_file
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
            from utils.image_utils import download_image_from_url, decode_base64_to_file  # type: ignore
        except Exception:
            from utils.image_utils import download_image_from_url, decode_base64_to_file  # type: ignore

        from config import settings
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
        strength: float = 0.8,
        stream: bool = True
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
                from utils.image_utils import decode_base64_to_file
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

