"""
封面生成器Agent
Cover Generator Agent
"""

import logging
import json
from typing import Dict, Any, List, Optional

from services.ai_service import AIService

logger = logging.getLogger(__name__)


class CoverGenerator:
    """封面生成器Agent"""

    def __init__(self):
        self.ai_service = AIService()
        self.output_schema = {
            "type": "object",
            "properties": {
                "cover_description": {
                    "type": "string",
                    "description": "封面图像的详细描述"
                },
                "key_elements": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "封面的关键元素列表"
                },
                "color_palette": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "建议的色调方案"
                },
                "composition": {
                    "type": "string",
                    "description": "构图建议"
                }
            },
            "required": ["cover_description", "key_elements", "color_palette", "composition"]
        }

        self.fewshot_examples = [
            {
                "input": {
                    "project_info": {"name": "魔法学院", "description": "一个关于魔法学习的故事"},
                    "chapter_info": {},
                    "characters": [{"name": "小明", "description": "年轻魔法师"}],
                    "cover_type": "project",
                    "user_prompt": "想要一个神秘的魔法风格封面"
                },
                "output": {
                    "cover_description": "神秘的魔法学院封面，宏伟的城堡在月光下矗立，周围环绕着魔法光芒，年轻的魔法师站在城堡前，手持法杖，周围飘浮着魔法符文和星光，整体氛围神秘而梦幻",
                    "key_elements": ["魔法城堡", "月光", "年轻魔法师", "法杖", "魔法符文", "星光"],
                    "color_palette": ["深蓝色", "紫色", "金色", "银色"],
                    "composition": "中心构图，城堡作为背景，人物在中景，魔法元素作为前景装饰"
                }
            },
            {
                "input": {
                    "project_info": {"name": "都市侦探", "description": "现代都市背景的侦探故事"},
                    "chapter_info": {"title": "第一章：神秘的失踪案", "content": "侦探接到一宗失踪案"},
                    "characters": [{"name": "李侦探", "description": "经验丰富的私家侦探"}],
                    "cover_type": "chapter",
                    "user_prompt": "想要一个悬疑的氛围"
                },
                "output": {
                    "cover_description": "悬疑氛围的都市侦探封面，雨夜的都市街道，霓虹灯反射在湿漉漉的地面上，侦探站在阴影中，大衣领子竖起，远处有一个模糊的人影，整体色调阴暗，充满神秘感",
                    "key_elements": ["雨夜街道", "霓虹灯", "侦探", "阴影", "模糊人影", "都市背景"],
                    "color_palette": ["深蓝色", "黑色", "霓虹红", "深灰色"],
                    "composition": "前景到中景的层次构图，利用光影对比营造悬疑氛围"
                }
            }
        ]

    async def generate_cover_description(
        self,
        project_info: Dict[str, Any],
        chapter_info: Dict[str, Any],
        characters: List[Dict[str, Any]],
        cover_type: str,
        user_prompt: str = "",
        reference_image_path: Optional[str] = None
    ) -> str:
        """
        生成封面描述

        Args:
            project_info: 项目信息
            chapter_info: 章节信息
            characters: 角色列表
            cover_type: 封面类型
            user_prompt: 用户提供的提示
            reference_image_path: 参考图片路径

        Returns:
            封面描述文本
        """
        try:
            # 构建输入信息
            input_data = {
                "project_info": project_info,
                "chapter_info": chapter_info,
                "characters": characters,
                "cover_type": cover_type,
                "user_prompt": user_prompt,
                "reference_image_path": reference_image_path
            }

            # 构建提示
            prompt = self._build_cover_prompt(input_data)

            # 调用AI服务生成封面描述
            response = await self.ai_service.generate_text(
                prompt=prompt,
                temperature=0.7,
                max_tokens=8000
            )

            # 解析AI响应
            result = self._parse_ai_response(response)

            if result and "cover_description" in result:
                return result["cover_description"]
            else:
                # 如果解析失败，返回默认描述
                return self._get_default_description(cover_type, project_info, chapter_info)

        except Exception as e:
            logger.error(f"生成封面描述失败: {e}")
            return self._get_default_description(cover_type, project_info, chapter_info)

    def _build_cover_prompt(self, input_data: Dict[str, Any]) -> str:
        """
        构建AI提示
        """
        project_info = input_data.get("project_info", {})
        chapter_info = input_data.get("chapter_info", {})
        characters = input_data.get("characters", [])
        cover_type = input_data.get("cover_type", "project")
        user_prompt = input_data.get("user_prompt", "")
        reference_image_path = input_data.get("reference_image_path")

        # 基础提示
        if cover_type == "project":
            base_prompt = "请为这个漫画项目生成一个封面描述，需要体现整个项目的主题和风格。"
        else:
            base_prompt = f"请为章节 '{chapter_info.get('title', '')}' 生成一个封面描述，需要体现章节的主要内容和情节。"

        # 构建详细信息
        details = []

        if project_info.get("name"):
            details.append(f"项目名称: {project_info['name']}")
        if project_info.get("description"):
            details.append(f"项目描述: {project_info['description']}")

        if chapter_info.get("title"):
            details.append(f"章节标题: {chapter_info['title']}")
        if chapter_info.get("summary"):
            details.append(f"章节概要: {chapter_info['summary']}")

        if characters:
            main_characters = [char["name"] for char in characters[:3]]  # 只取前3个主要角色
            details.append(f"主要角色: {', '.join(main_characters)}")

        if user_prompt:
            details.append(f"用户要求: {user_prompt}")

        if reference_image_path:
            details.append(f"参考图片: 有参考图片，请参考其风格、色彩和构图来生成封面")

        # 完整提示
        full_prompt = f"""
{base_prompt}

项目/章节信息:
{chr(10).join(details)}

请根据以上信息，生成一个详细的封面描述，包括:
1. 画面主体内容
2. 背景和环境
3. 色彩氛围
4. 关键元素
5. 构图建议

请用中文回答，描述要生动具体，适合AI图像生成。
"""

        return full_prompt

    def _parse_ai_response(self, response: str) -> Optional[Dict[str, Any]]:
        """
        解析AI响应
        """
        try:
            # 尝试解析JSON响应
            if response.strip().startswith('{'):
                return json.loads(response)

            # 如果不是JSON，尝试提取描述文本
            lines = response.strip().split('\n')
            description = ""

            for line in lines:
                line = line.strip()
                if line and not line.startswith('1.') and not line.startswith('2.') and not line.startswith('3.') and not line.startswith('4.') and not line.startswith('5.'):
                    description += line + " "

            if description:
                return {"cover_description": description.strip()}

            return None

        except Exception as e:
            logger.error(f"解析AI响应失败: {e}")
            return None

    def _get_default_description(
        self,
        cover_type: str,
        project_info: Dict[str, Any],
        chapter_info: Dict[str, Any]
    ) -> str:
        """
        获取默认封面描述
        """
        if cover_type == "project":
            project_name = project_info.get("name", "漫画项目")
            return f"精美的{project_name}封面，展现故事的主要风格和氛围，色彩鲜明，构图均衡，适合作为作品代表"
        else:
            chapter_title = chapter_info.get("title", "章节")
            return f"精美的{chapter_title}封面，展现章节的主要情节和氛围，画面生动，引人入胜"