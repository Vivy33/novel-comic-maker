"""
文本分析Agent
Text Analyzer Agent

负责分析小说文本，提取关键信息，如角色、场景、情感等。
"""
import json
import logging
from typing import Dict, Any, List

from ..services.ai_service import volc_service

logger = logging.getLogger(__name__)

# 定义模型端点
LITE_MODEL = "doubao-lite-32k"
FLASH_MODEL = "doubao-flash-128k"

class TextAnalyzer:
    """
    分析小说文本，提取结构化信息。
    编排 lite 和 flash 模型以实现高效、深入的分析。
    """

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
            prompt = f"""你是一位专业的小说分析助手。请阅读以下小说文本，并以JSON格式提取其核心内容。
            请提取以下信息：
            1. `characters`: 文本中出现的角色列表。
            2. `setting`: 场景或环境的简要描述。
            3. `summary`: 文本情节的简要概括。

            小说文本片段：
            ---
            {chunk}
            ---

            请严格按照JSON格式返回。"""
            
            messages = [{"role": "user", "content": prompt}]
            summary_str = volc_service.chat_completion(LITE_MODEL, messages)
            
            if summary_str:
                try:
                    chunk_summaries.append(json.loads(summary_str))
                except json.JSONDecodeError:
                    logger.warning(f"块 {i+1} 的分析结果不是有效的JSON，将作为纯文本处理。")
                    chunk_summaries.append({"summary": summary_str}) # Fallback handling

        # 3. 使用 flash 模型进行最终的综合分析
        logger.info(f"使用 {FLASH_MODEL} 进行综合分析...")
        combined_summaries = "\n".join([f"片段 {i+1}:\n{json.dumps(s, ensure_ascii=False)}\n" for i, s in enumerate(chunk_summaries)])

        final_prompt = f"""你是一位资深的小说编辑。你收到了关于一部小说连续片段的初步分析报告。
        请整合这些报告，生成一份全面、连贯的全局分析报告。

        你的任务是：
        1. `main_characters`: 识别并列出主要角色，为每个角色写一句描述。
        2. `settings`: 描述故事发生的主要场景和环境。
        3. `plot_summary`: 创建一个连贯、完整的故事情节摘要。
        4. `emotional_flow`: 描述整个故事中的情感变化流动。
        5. `key_events`: 识别出几个关键的情节转折点或重要事件。

        初步分析报告如下：
        ---
        {combined_summaries}
        ---

        请以JSON格式返回最终的分析报告。"""

        messages = [{"role": "user", "content": final_prompt}]
        final_analysis_str = volc_service.chat_completion(FLASH_MODEL, messages)

        if not final_analysis_str:
            return {"error": "Failed to get final analysis from the model."}

        try:
            return json.loads(final_analysis_str)
        except json.JSONDecodeError:
            logger.error("最终分析结果不是有效的JSON。")
            return {"error": "Final analysis is not valid JSON.", "raw_output": final_analysis_str}

# 创建一个单例
text_analyzer = TextAnalyzer()
