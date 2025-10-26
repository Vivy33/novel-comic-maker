"""
文本分析Agent
Text Analyzer Agent

负责分析小说文本，提取关键信息，如角色、场景、情感等。
"""
import json
import logging
from typing import Dict, Any, List

from services.ai_service import volc_service, AIService

logger = logging.getLogger(__name__)

# 定义模型端点
LITE_MODEL = "deepseek-v3-1-terminus"
FLASH_MODEL = "deepseek-v3-1-terminus"

class TextAnalyzer:
    """
    分析小说文本，提取结构化信息。
    编排 lite 和 flash 模型以实现高效、深入的分析。
    使用JSON Schema确保输出格式的标准化。
    """

    def __init__(self):
        self.ai_service = AIService()

    def _get_chunk_analysis_schema(self) -> Dict[str, Any]:
        """获取块分析的JSON Schema"""
        return {
            "type": "object",
            "properties": {
                "characters": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "文本中出现的角色列表"
                },
                "setting": {
                    "type": "string",
                    "description": "场景或环境的简要描述"
                },
                "summary": {
                    "type": "string",
                    "description": "文本情节的简要概括"
                }
            },
            "required": ["characters", "setting", "summary"]
        }

    def _get_final_analysis_schema(self) -> Dict[str, Any]:
        """获取最终分析的JSON Schema"""
        return {
            "type": "object",
            "properties": {
                "main_characters": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "description": {"type": "string"}
                        },
                        "required": ["name", "description"]
                    },
                    "description": "主要角色列表"
                },
                "settings": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "故事发生的主要场景和环境"
                },
                "plot_summary": {
                    "type": "string",
                    "description": "连贯、完整的故事情节摘要"
                },
                "emotional_flow": {
                    "type": "string",
                    "description": "整个故事中的情感变化流动"
                },
                "key_events": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "关键的情节转折点或重要事件"
                }
            },
            "required": ["main_characters", "settings", "plot_summary", "emotional_flow", "key_events"]
        }

    def _split_text(self, text: str, chunk_size: int = 1000) -> List[str]:
        """简单的按字符数分割文本"""
        if not text:
            return []
        return [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]

    async def analyze(self, novel_text: str) -> Dict[str, Any]:
        """
        分析小说文本。

        Args:
            novel_text: 小说文本内容。

        Returns:
            一个包含分析结果的字典。
        """
        if not volc_service.is_available():
            logger.error("文本分析失败，因为火山引擎服务不可用。")
            return {"error": "AI service is not available."}

        # 1. 将文本分割成小块
        chunks = self._split_text(novel_text)
        if not chunks:
            return {"error": "Input text is empty."}
            
        logger.info(f"文本被分割成 {len(chunks)} 个块进行初步分析。")

        # 2. 使用 lite 模型对每个块进行初步分析
        chunk_summaries = []
        for i, chunk in enumerate(chunks):
            logger.info(f"使用 {LITE_MODEL} 分析块 {i+1}/{len(chunks)}...")
            prompt = f"""请阅读以下小说文本，提取其核心内容：

            小说文本片段：
            ---
            {chunk}
            ---

            请提取角色列表、场景描述和情节概括。"""

            # 使用JSON Schema强制输出格式
            try:
                summary_str = volc_service.chat_completion(
                    model=LITE_MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    response_format=self.ai_service.create_json_schema_response_format(
                        self._get_chunk_analysis_schema()
                    )
                )

                if summary_str:
                    chunk_summaries.append(json.loads(summary_str))
                else:
                    logger.warning(f"块 {i+1} 的分析结果为空")
                    chunk_summaries.append({"characters": [], "setting": "未识别", "summary": chunk[:100]})
            except Exception as e:
                logger.error(f"块 {i+1} JSON Schema分析失败: {e}")
                # 降级处理：使用传统方式
                summary_str = volc_service.chat_completion(LITE_MODEL, [{"role": "user", "content": prompt}])
                if summary_str:
                    try:
                        chunk_summaries.append(json.loads(summary_str))
                    except json.JSONDecodeError:
                        chunk_summaries.append({"characters": [], "setting": "未识别", "summary": chunk[:100]})
                else:
                    chunk_summaries.append({"characters": [], "setting": "未识别", "summary": chunk[:100]})

        # 3. 使用 flash 模型进行最终的综合分析
        logger.info(f"使用 {FLASH_MODEL} 进行综合分析...")
        combined_summaries = "\n".join([f"片段 {i+1}:\n{json.dumps(s, ensure_ascii=False)}\n" for i, s in enumerate(chunk_summaries)])

        final_prompt = f"""你是一位资深的小说编辑。请整合以下初步分析报告，生成一份全面、连贯的全局分析报告。

        初步分析报告如下：
        ---
        {combined_summaries}
        ---

        请识别主要角色、场景环境、情节摘要、情感流动和关键事件。"""

        # 使用JSON Schema强制输出格式
        try:
            final_analysis_str = volc_service.chat_completion(
                model=FLASH_MODEL,
                messages=[{"role": "user", "content": final_prompt}],
                response_format=self.ai_service.create_json_schema_response_format(
                    self._get_final_analysis_schema()
                )
            )

            if not final_analysis_str:
                return {"error": "Failed to get final analysis from the model."}

            return json.loads(final_analysis_str)
        except Exception as e:
            logger.error(f"最终分析JSON Schema失败: {e}")
            # 降级处理：使用传统方式
            final_analysis_str = volc_service.chat_completion(FLASH_MODEL, [{"role": "user", "content": final_prompt}])
            if not final_analysis_str:
                return {"error": "Failed to get final analysis from the model."}
            try:
                return json.loads(final_analysis_str)
            except json.JSONDecodeError:
                logger.error("最终分析结果不是有效的JSON。")
                return {"error": "Final analysis is not valid JSON.", "raw_output": final_analysis_str}

# 创建一个单例
text_analyzer = TextAnalyzer()
