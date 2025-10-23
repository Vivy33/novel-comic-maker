"""
漫画脚本生成Agent
Comic Script Generator Agent

负责将结构化的文本分析结果转换为详细的漫画分镜脚本。
"""
import json
import logging
from typing import Dict, Any

from ..services.ai_service import volc_service, AIService

logger = logging.getLogger(__name__)

# 定义模型端点
FLASH_MODEL = "doubao-seed-1-6-flash-250828"

class ScriptGenerator:
    """
    根据文本分析结果生成漫画脚本。
    使用JSON Schema确保输出格式的标准化。
    """

    def __init__(self):
        self.ai_service = AIService()

    def _get_script_schema(self) -> Dict[str, Any]:
        """获取脚本生成的JSON Schema"""
        return {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "故事标题"
                },
                "panels": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "panel_number": {
                                "type": "integer",
                                "description": "分镜编号"
                            },
                            "scene_description": {
                                "type": "string",
                                "description": "详细描述画面内容，包括场景、角色位置、动作、表情和氛围"
                            },
                            "dialogue": {
                                "type": "string",
                                "description": "角色的对话内容"
                            },
                            "sound_effects": {
                                "type": "string",
                                "description": "音效描述（可选）"
                            },
                            "notes": {
                                "type": "string",
                                "description": "额外备注（可选）"
                            }
                        },
                        "required": ["panel_number", "scene_description", "dialogue"]
                    },
                    "description": "漫画分镜列表"
                },
                "total_panels": {
                    "type": "integer",
                    "description": "总分镜数"
                },
                "estimated_pages": {
                    "type": "integer",
                    "description": "预估页数"
                }
            },
            "required": ["title", "panels", "total_panels", "estimated_pages"]
        }

    async def generate(self, text_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        生成漫画脚本。

        Args:
            text_analysis: 来自TextAnalyzer的结构化分析数据。

        Returns:
            一个包含漫画脚本的字典。
        """
        if not volc_service.is_available():
            logger.error("脚本生成失败，因为火山引擎服务不可用。")
            return {"error": "AI service is not available."}

        logger.info(f"使用 {FLASH_MODEL} 生成漫画脚本...")

        # 将分析数据转换为格式化的字符串，作为模型的输入
        analysis_summary = json.dumps(text_analysis, ensure_ascii=False, indent=2)

        prompt = f"""你是一位专业的漫画编剧。请根据以下的小说分析报告，创作一份详细的漫画分镜脚本。

        请创作包含标题、分镜描述、对话和音效的漫画脚本。

        小说分析报告：
        ---
        {analysis_summary}
        ---

        请确保分镜能够生动地展现故事情节和情感流动。"""

        # 使用JSON Schema强制输出格式
        try:
            script_str = volc_service.chat_completion(
                model=FLASH_MODEL,
                messages=[{"role": "user", "content": prompt}],
                response_format=self.ai_service.create_json_schema_response_format(
                    self._get_script_schema()
                )
            )

            if not script_str:
                return {"error": "Failed to get script from the model."}

            return json.loads(script_str)
        except Exception as e:
            logger.error(f"脚本生成JSON Schema失败: {e}")
            # 降级处理：使用传统方式
            script_str = volc_service.chat_completion(FLASH_MODEL, [{"role": "user", "content": prompt}])
            if not script_str:
                return {"error": "Failed to get script from the model."}
            try:
                return json.loads(script_str)
            except json.JSONDecodeError:
                logger.error("生成的脚本不是有效的JSON。")
                return {"error": "Generated script is not valid JSON.", "raw_output": script_str}

# 创建一个单例
script_generator = ScriptGenerator()
