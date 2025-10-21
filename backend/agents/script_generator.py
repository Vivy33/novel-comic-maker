"""
漫画脚本生成Agent
Comic Script Generator Agent

负责将结构化的文本分析结果转换为详细的漫画分镜脚本。
"""
import json
import logging
from typing import Dict, Any

from ..services.ai_service import volc_service

logger = logging.getLogger(__name__)

# 定义模型端点
FLASH_MODEL = "doubao-flash-128k"

class ScriptGenerator:
    """
    根据文本分析结果生成漫画脚本。
    """

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
        
        脚本需要遵循以下JSON格式，包含一个名为 `panels` 的列表，每个panel对象代表一个分镜：
        {{
          "title": "故事标题",
          "panels": [
            {{
              "panel_number": 1,
              "scene_description": "（详细描述画面内容，包括场景、角色位置、动作、表情和氛围）",
              "dialogue": "（角色的对话内容，如果没有则为 null）",
              "narration": "（旁白内容，用于解释背景或角色内心想法，如果没有则为 null）"
            }},
            // ... 更多panel
          ]
        }}

        请确保分镜能够生动地展现故事情节和情感流动。

        小说分析报告：
        ---
        {analysis_summary}
        ---

        请严格按照上述JSON格式返回漫画脚本。"""

        messages = [{"role": "user", "content": prompt}]
        script_str = volc_service.chat_completion(FLASH_MODEL, messages)

        if not script_str:
            return {"error": "Failed to get script from the model."}

        try:
            return json.loads(script_str)
        except json.JSONDecodeError:
            logger.error("生成的脚本不是有效的JSON。")
            return {"error": "Generated script is not valid JSON.", "raw_output": script_str}

# 创建一个单例
script_generator = ScriptGenerator()
