"""
图像生成Agent
Image Generator Agent

负责根据漫画脚本生成或编辑图像。
"""
import logging
from typing import Dict, Any, List, Optional

from ..services.ai_service import volc_service

logger = logging.getLogger(__name__)

# 定义模型端点
GENERATION_MODEL = "doubao-seedream-4-0-250828"
EDIT_MODEL = "doubao-seedream-4-0-250828"

class ImageGenerator:
    """
    根据漫画脚本中的描述生成和编辑图像。
    """

    async def generate_images_for_script(self, script: Dict[str, Any], project_path: str) -> List[Dict[str, Any]]:
        """
        为整个脚本的每个分镜生成图像。

        Args:
            script: 包含多个分镜(panel)的脚本字典。
            project_path: 项目路径，用于保存生成的图像。

        Returns:
            一个列表，包含每个分镜的图像生成结果。
        """
        if not volc_service.is_available():
            logger.error("图像生成失败，因为火山引擎服务不可用。")
            return [{"error": "AI service is not available."}]

        panels = script.get("panels", [])
        if not panels:
            logger.warning("脚本中没有找到任何分镜。")
            return []

        logger.info(f"开始为 {len(panels)} 个分镜生成图像...")
        
        generated_images = []
        for panel in panels:
            panel_number = panel.get("panel_number", "unknown")
            description = panel.get("scene_description", "")

            if not description:
                logger.warning(f"分镜 {panel_number} 没有场景描述，跳过图像生成。")
                continue

            logger.info(f"正在为分镜 {panel_number} 生成图像...")
            image_url = volc_service.text_to_image(GENERATION_MODEL, prompt=description)

            if image_url:
                # 下载图像到本地
                try:
                    from ..utils.image_utils import download_image_from_url
                    import time

                    filename = f"panel_{panel_number}_{int(time.time())}.png"
                    output_dir = f"{project_path}/chapters/chapter_001/images"
                    output_path = f"{output_dir}/{filename}"

                    # 使用真实的下载逻辑
                    local_path = await download_image_from_url(image_url, output_path)
                    logger.info(f"图像已下载到本地: {local_path}")

                    generated_images.append({
                        "panel_number": panel_number,
                        "status": "success",
                        "image_url": image_url,
                        "local_path": local_path
                    })
                except Exception as e:
                    logger.error(f"下载分镜 {panel_number} 的图像失败: {e}")
                    generated_images.append({
                        "panel_number": panel_number,
                        "status": "error",
                        "reason": f"Failed to download image: {e}"
                    })
            else:
                logger.error(f"为分镜 {panel_number} 生成图像失败。")
                generated_images.append({
                    "panel_number": panel_number,
                    "status": "error",
                    "reason": "AI service failed to generate image."
                })
        
        return generated_images

    async def edit_image(self, original_image_path: str, edit_prompt: str, output_dir: str = None) -> Optional[str]:
        """
        编辑现有图像，支持base64上传。

        Args:
            original_image_path: 本地原始图像的路径。
            edit_prompt: 编辑指令。
            output_dir: 输出目录，如果为None则使用默认临时目录。

        Returns:
            编辑后图像的本地路径。
        """
        if not volc_service.is_available():
            logger.error("图像编辑失败，因为火山引擎服务不可用。")
            return None

        logger.info(f"准备使用 {EDIT_MODEL} 编辑图像: {original_image_path}...")

        try:
            from ..utils.image_utils import encode_file_to_base64, download_image_from_url
            import time
            import os

            # 将本地图片编码为base64
            base64_image = encode_file_to_base64(original_image_path)
            logger.info(f"图片已编码为base64，长度: {len(base64_image)}")

            # 使用AI服务进行图生图
            result_url = await volc_service.edit_image_with_base64(
                prompt=edit_prompt,
                base64_image=base64_image,
                model_preference=EDIT_MODEL
            )

            if result_url and not result_url.startswith("placeholder://"):
                # 下载编辑后的图片到本地
                if output_dir is None:
                    output_dir = f"{os.path.dirname(original_image_path)}"

                filename = f"edited_{int(time.time())}.png"
                output_path = f"{output_dir}/{filename}"

                try:
                    local_path = await download_image_from_url(result_url, output_path)
                    logger.info(f"图像编辑成功！编辑后的图片已保存到: {local_path}")
                    return local_path
                except Exception as e:
                    logger.error(f"下载编辑后的图片失败: {e}")
                    return result_url  # 返回URL作为备选
            else:
                logger.error(f"图像编辑失败，AI服务返回: {result_url}")
                return None

        except Exception as e:
            logger.error(f"图像编辑过程出现异常: {e}")
            return None

# 创建一个单例
image_generator = ImageGenerator()
