"""
图像生成Agent
Image Generator Agent

负责根据漫画脚本中的描述生成和编辑图像。
"""
import logging
import os
from typing import Dict, Any, List

from services.ai_service import volc_service

logger = logging.getLogger(__name__)

# 定义模型端点
GENERATION_MODEL = "doubao-seedream-4-0-250828"
EDIT_MODEL = "doubao-seedream-4-0-250828"

class ImageGenerator:
    """
    根据漫画脚本中的描述生成和编辑图像。
    支持单个场景生成多张备选图像（组图功能）。
    """

    def __init__(self):
        pass

    def _get_next_chapter_number(self, project_path: str) -> int:
        """
        获取下一个章节编号

        Args:
            project_path: 项目路径

        Returns:
            下一个章节编号（整数）
        """
        try:
            chapters_dir = os.path.join(project_path, "chapters")
            if not os.path.exists(chapters_dir):
                return 1

            # 扫描现有章节目录
            existing_chapters = []
            for item in os.listdir(chapters_dir):
                if item.startswith("chapter_") and os.path.isdir(os.path.join(chapters_dir, item)):
                    try:
                        # 提取章节编号
                        chapter_num = int(item.split("_")[1])
                        existing_chapters.append(chapter_num)
                    except (ValueError, IndexError):
                        continue

            if not existing_chapters:
                return 1

            # 返回下一个章节编号
            return max(existing_chapters) + 1

        except Exception as e:
            logger.error(f"获取下一个章节编号失败: {e}")
            return 1

    def _get_or_create_current_chapter(self, project_path: str) -> str:
        """
        获取或创建当前章节目录

        为项目维护统一的章节状态，确保同一项目的所有segment使用相同章节

        Args:
            project_path: 项目路径

        Returns:
            章节目录名称（如 "chapter_001"）
        """
        try:
            # 章节状态文件路径
            chapter_state_file = os.path.join(project_path, "chapters", ".current_chapter.txt")

            # 确保chapters目录存在
            chapters_dir = os.path.join(project_path, "chapters")
            os.makedirs(chapters_dir, exist_ok=True)

            # 如果存在章节状态文件，读取当前章节
            if os.path.exists(chapter_state_file):
                with open(chapter_state_file, 'r', encoding='utf-8') as f:
                    current_chapter = f.read().strip()
                    if current_chapter and os.path.exists(os.path.join(chapters_dir, current_chapter)):
                        logger.info(f"📖 使用现有章节: {current_chapter}")
                        return current_chapter

            # 创建新章节
            chapter_number = self._get_next_chapter_number(project_path)
            chapter_dir = f"chapter_{chapter_number:03d}"

            # 创建章节目录
            new_chapter_path = os.path.join(chapters_dir, chapter_dir)
            os.makedirs(new_chapter_path, exist_ok=True)

            # 保存章节状态
            with open(chapter_state_file, 'w', encoding='utf-8') as f:
                f.write(chapter_dir)

            logger.info(f"🆕 创建新章节: {chapter_dir}")
            return chapter_dir

        except Exception as e:
            logger.error(f"获取或创建当前章节失败: {e}")
            # 降级到原有的章节创建逻辑
            return self._get_chapter_dir_name(project_path)

    def _get_chapter_dir_name(self, project_path: str, chapter_number: int = None, force_new_chapter: bool = False) -> str:
        """
        获取章节目录名称

        Args:
            project_path: 项目路径
            chapter_number: 指定章节编号（可选），如果为None则自动分配
            force_new_chapter: 是否强制创建新章节（默认False，会复用现有章节）

        Returns:
            章节目录名称（如 "chapter_001", "chapter_002"）
        """
        if force_new_chapter:
            # 强制创建新章节（用于特殊场景）
            if chapter_number is None:
                chapter_number = self._get_next_chapter_number(project_path)
            return f"chapter_{chapter_number:03d}"
        else:
            # 默认行为：复用现有章节
            return self._get_or_create_current_chapter(project_path)

    def _get_character_references(self, project_path: str, selected_characters: List[str]) -> Dict[str, Any]:
        """
        获取选定角色的参考图片和角色卡信息

        Args:
            project_path: 项目路径
            selected_characters: 选定的角色名称列表

        Returns:
            包含角色参考信息的字典
        """
        try:
            from services.file_system import ProjectFileSystem
            import json
            import os

            fs = ProjectFileSystem()
            character_info = {}

            # 获取项目角色列表 - 使用正确的方法
            try:
                # 使用正确的方法名
                characters = fs.get_project_characters(project_id)
            except AttributeError:
                # 如果方法不存在，使用备用方案
                logger.warning(f"get_project_characters方法不存在，跳过角色参考信息获取")
                characters = []

            for character in characters:
                if character.get("name") in selected_characters:
                    char_name = character["name"]
                    char_data = {
                        "name": char_name,
                        "description": character.get("description", ""),
                        "traits": character.get("traits", []),
                        "reference_images": character.get("reference_images", [])
                    }

                    # 获取角色参考图片路径
                    char_dir = f"{project_path}/characters/{char_name}"
                    if os.path.exists(char_dir):
                        # 查找角色卡JSON文件
                        json_files = [f for f in os.listdir(char_dir) if f.endswith('.json')]
                        if json_files:
                            json_path = os.path.join(char_dir, json_files[0])
                            with open(json_path, 'r', encoding='utf-8') as f:
                                char_data["character_card"] = json.load(f)

                        # 查找角色正反面参考图片
                        image_files = [f for f in os.listdir(char_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
                        char_data["reference_image_paths"] = [os.path.join(char_dir, img) for img in image_files]

                    character_info[char_name] = char_data

            return character_info

        except Exception as e:
            logger.warning(f"获取角色参考信息失败: {e}")
            return {}

    async def generate_images_for_script(self, script: Dict[str, Any], project_path: str, max_images: int = 3, segment_index: int = 0) -> Dict[str, Any]:
        """
        为单个场景描述生成多张备选图像（组图功能）。

        Args:
            script: 包含单个场景描述的脚本字典。
            project_path: 项目路径，用于保存生成的图像。
            max_images: 生成图像数量，默认3张（用户可配置2-4张）
            segment_index: 段落索引，用于确定章节目录

        Returns:
            包含该场景的多张备选图像结果和元数据。
        """
        
        if not volc_service.is_available():
            logger.error("图像生成失败，因为火山引擎服务不可用。")
            return {"error": "AI service is not available."}

        # 获取单个场景描述（修正：不再是多分镜）
        scene_description = script.get("scene_description", "")
        if not scene_description:
            logger.warning("脚本中没有找到场景描述。")
            return {"error": "No scene description found."}

        logger.info(f"🎨 开始为单个场景生成 {max_images} 张备选图像...")

        # 优化：预处理场景描述，确保简洁精准，控制在300字符以内
        # 首先获取前情提要图片路径
        previous_context = script.get("previous_context", "")
        reference_image_path = None
        if previous_context:
            import os

            # 处理项目相对路径 (如 /projects/2025.10.25_11.48_勇者斗恶龙/...)
            image_path = None
            logger.info(f"开始处理前情提要图片路径: {previous_context}")

            if previous_context.startswith("/projects/"):
                # 将项目相对路径转换为绝对路径
                # 格式: /projects/项目名/子路径 -> 当前工作目录/projects/项目名/子路径
                relative_path = previous_context[1:]  # 去掉开头的 /
                image_path = os.path.join(os.getcwd(), relative_path)
                logger.info(f"转换项目相对路径: {previous_context} -> {image_path}")
            elif previous_context.startswith("http"):
                # HTTP/HTTPS URL - 需要下载到本地
                try:
                    from utils.image_utils import download_image_from_url
                    import tempfile
                    import uuid

                    # 创建临时文件
                    temp_filename = f"reference_{uuid.uuid4().hex[:8]}.png"
                    temp_dir = tempfile.gettempdir()
                    temp_path = os.path.join(temp_dir, temp_filename)

                    # 下载图片
                    logger.info(f"下载前情提要图片到本地: {previous_context}")
                    downloaded_path = await download_image_from_url(previous_context, temp_path)
                    if downloaded_path and os.path.isfile(downloaded_path):
                        image_path = downloaded_path
                        logger.info(f"前情提要图片下载成功: {image_path}")
                    else:
                        logger.warning(f"前情提要图片下载失败: {previous_context}")
                except Exception as e:
                    logger.error(f"下载前情提要图片时出错: {e}")
                    image_path = None
            elif os.path.isfile(previous_context):
                # 直接是文件系统路径
                image_path = previous_context
                logger.info(f"使用直接文件路径: {image_path}")
            else:
                # 尝试作为相对路径处理
                possible_path = os.path.join(os.getcwd(), previous_context)
                if os.path.isfile(possible_path):
                    image_path = possible_path
                    logger.info(f"作为相对路径解析成功: {previous_context} -> {image_path}")

            # 验证图片文件是否存在且可读
            if image_path and os.path.isfile(image_path):
                # 检查文件大小，确保不是空文件
                file_size = os.path.getsize(image_path)
                if file_size > 0:
                    reference_image_path = image_path  # 使用绝对路径
                    logger.info(f"✅ 检测到有效的前情提要图片: {reference_image_path} (大小: {file_size} bytes)")
                else:
                    logger.warning(f"前情提要图片文件为空: {image_path}")
            else:
                logger.warning(f"❌ 前情提要图片路径无效或文件不存在: {previous_context}")
                # 列出可能的调试信息
                if previous_context.startswith("/projects/"):
                    project_part = previous_context.split("/")[2] if len(previous_context.split("/")) > 2 else ""
                    if project_part:
                        projects_dir = os.path.join(os.getcwd(), "projects")
                        if os.path.exists(projects_dir):
                            logger.info(f"projects目录存在: {projects_dir}")
                            project_dir = os.path.join(projects_dir, project_part)
                            logger.info(f"项目目录检查: {project_dir}, 存在: {os.path.exists(project_dir)}")

        optimized_prompt = self._optimize_scene_description(scene_description, script, project_path, reference_image_path)

        logger.info(f"生成场景图像，优化后prompt长度: {len(optimized_prompt)} 字符")

        # 初始化有效图片URL列表
        valid_image_urls = []

        try:
            # 根据是否有参考图片选择不同的生成策略
            if reference_image_path:
                # 使用图片参考API进行图生图
                logger.info(f"使用前情提要图片参考生成连贯性画面: {reference_image_path}")

                # 对于有参考图片的情况，一次生成一张，然后生成变体
                image_urls = []

                for i in range(max_images):
                    if i == 0:
                        # 第一张图片使用参考图生成
                        result_url = volc_service.multi_reference_text_to_image(
                            model=GENERATION_MODEL,
                            prompt=optimized_prompt,
                            reference_images=[reference_image_path],
                            max_images=1
                        )
                    else:
                        # 后续图片使用变体prompt生成
                        variant_prompt = self._create_variant_prompt(optimized_prompt, i, max_images)
                        result_url = volc_service.text_to_image(
                            model=GENERATION_MODEL,
                            prompt=variant_prompt,
                            max_images=1,
                            stream=False
                        )

                    if result_url:
                        if isinstance(result_url, list):
                            result_url = result_url[0] if result_url else None
                        # 处理API返回的字典格式
                        if isinstance(result_url, dict):
                            result_url = result_url.get('image_url')
                        image_urls.append(result_url)
                    else:
                        logger.warning(f"第{i+1}张图片生成失败，返回空URL")
                        image_urls.append(None)

                logger.info(f"使用图片参考生成了 {len([url for url in image_urls if url])} 张有效图像")

            else:
                # 使用多次调用来模拟组图生成（无参考图片）
                image_urls = []

                logger.info(f"开始通过多次调用生成 {max_images} 张备选图像...")

                # 获取结构化数据，用于变体prompt生成
                structured_data = script.get("structured_data")
                style_requirements = script.get("style_requirements", "")
                style_reference_info = script.get("style_reference_info", "")

                for i in range(max_images):
                    try:
                        # 为每个图像创建变体prompt
                        if i > 0:
                            # 第一张后的图像使用简单变体
                            variations = [
                                ", 不同角度视角",
                                ", 构图调整",
                                ", 细节变化",
                                ", 表情变化",
                                ", 光影变化"
                            ]
                            variation = variations[(i-1) % len(variations)]
                            variant_prompt = optimized_prompt + variation
                            logger.info(f"🎨 生成第 {i+1}/{max_images} 张图像，变体: {variation}")
                        else:
                            # 第一张图像使用原始prompt
                            variant_prompt = optimized_prompt
                            logger.info(f"🎨 生成第 {i+1}/{max_images} 张图像，原始prompt")

                        # 单次调用生成一张图像
                        logger.info(f"🚀 开始调用火山引擎API - 第 {i+1}/{max_images} 张图像")
                        logger.info(f"📝 Prompt长度: {len(variant_prompt)} 字符")
                        logger.info(f"📝 Prompt内容: {variant_prompt[:100]}...")  # 显示前100个字符

                        try:
                            # 记录调用开始时间
                            import time
                            start_time = time.time()

                            image_url_result = volc_service.text_to_image(
                                model=GENERATION_MODEL,
                                prompt=variant_prompt,
                                max_images=1,  # 每次只生成一张图片
                                sequential_generation="disabled",  # 禁用组图模式
                                stream=False  # 禁用流式模式以获取URL而不是流对象
                            )

                            # 记录调用结束时间
                            end_time = time.time()
                            api_duration = end_time - start_time
                            logger.info(f"⏱️ 火山引擎API调用耗时: {api_duration:.2f} 秒")
                            logger.info(f"📦 API返回结果类型: {type(image_url_result)}")
                            logger.info(f"📦 API返回结果: {image_url_result}")

                        except Exception as api_error:
                            logger.error(f"❌ 火山引擎API调用失败: {api_error}")
                            logger.error(f"❌ API错误类型: {type(api_error)}")
                            raise api_error

                        if image_url_result:
                            # 处理API返回的字典格式
                            if isinstance(image_url_result, dict):
                                image_url_result = image_url_result.get('image_url')
                            image_urls.append(image_url_result)
                            logger.info(f"第 {i+1} 张图像生成成功")
                        else:
                            logger.warning(f"第 {i+1} 张图像生成失败，返回空URL")
                            image_urls.append(None)

                    except Exception as e:
                        logger.error(f"生成第 {i+1} 张图像时发生错误: {e}")
                        image_urls.append(None)

                # 处理生成的图片URL列表
                valid_image_urls = [url for url in image_urls if url is not None]

            if len(valid_image_urls) > 0:
                # 有有效图片，处理下载
                logger.info(f"成功生成 {len(valid_image_urls)} 张备选图像")
                generated_images = []

                for i, image_url in enumerate(image_urls):
                    if image_url is None:
                        # 处理生成失败的图片
                        generated_images.append({
                            "image_option": i + 1,
                            "status": "generation_failed",
                            "error": "图片生成失败，返回空URL"
                        })
                        continue
                    try:
                        from utils.image_utils import download_image_from_url
                        import time

                        filename = f"scene_option_{i+1}_{int(time.time())}.png"
                        # 使用统一章节目录和分镜子目录
                        chapter_dir = self._get_chapter_dir_name(project_path)
                        segment_dir = f"segment_{segment_index + 1:02d}"
                        output_dir = f"{project_path}/chapters/{chapter_dir}/images/{segment_dir}"
                        output_path = f"{output_dir}/{filename}"

                        # 下载图像到本地
                        local_path = await download_image_from_url(image_url, output_path)
                        logger.info(f"备选图 {i+1} 已下载到本地: {local_path}")

                        generated_images.append({
                            "image_option": i + 1,  # 备选图编号
                            "status": "success",
                            "image_url": image_url,
                            "local_path": local_path,
                            "prompt_used": optimized_prompt
                        })
                    except Exception as e:
                        logger.error(f"下载备选图 {i+1} 失败: {e}")
                        generated_images.append({
                            "image_option": i + 1,
                            "status": "download_failed",
                            "error": str(e)
                        })

                return {
                    "scene_description": scene_description,
                    "total_options": len(valid_image_urls),
                    "generated_images": generated_images,
                    "generation_type": "batch_selection",  # 标记为组图选择模式
                    "prompt_used": optimized_prompt,
                    "max_images_configured": max_images,
                    "reference_image_used": reference_image_path or ""  # 记录使用的参考图片
                }
            else:
                # 组图API只返回1张图片或返回单图，使用备用方案生成多张不同图片
                if isinstance(image_urls, list):
                    image_url = image_urls[0]  # 取第一张图片
                else:
                    image_url = image_urls

                logger.warning(f"组图API只返回1张图片，启动备用方案生成 {max_images} 张不同图片")

                generated_images = []
                max_attempts = max_images * 2  # 增加最大尝试次数，确保能生成足够的图片
                attempt_count = 0

                # 生成多张不同的图片，带有重试机制
                while len([img for img in generated_images if img["status"] == "success"]) < max_images and attempt_count < max_attempts:
                    i = len([img for img in generated_images if img["status"] == "success"])

                    try:
                        attempt_count += 1
                        logger.info(f"第 {attempt_count} 次尝试生成备选图 {i+1}/{max_images}")

                        if i == 0 and reference_image_path:
                            # 第一张图片使用参考图生成
                            logger.info(f"生成备选图 {i+1}/{max_images}，使用前情提要图片参考")
                            variant_url = volc_service.multi_reference_text_to_image(
                                model=GENERATION_MODEL,
                                prompt=optimized_prompt,
                                reference_images=[reference_image_path],
                                max_images=1
                            )
                        else:
                            # 为每张图片生成略有不同的prompt
                            variant_prompt = self._create_variant_prompt(optimized_prompt, i, max_images)

                            logger.info(f"生成备选图 {i+1}/{max_images}，使用变体prompt")

                            variant_url = volc_service.text_to_image(
                                model=GENERATION_MODEL,
                                prompt=variant_prompt,
                                max_images=1,  # 每次只生成1张
                                stream=False
                            )

                        if isinstance(variant_url, list):
                            variant_url = variant_url[0] if variant_url else None

                        # 处理API返回的字典格式
                        if isinstance(variant_url, dict):
                            variant_url = variant_url.get('image_url')

                        if variant_url:
                            from utils.image_utils import download_image_from_url
                            import time

                            filename = f"scene_option_{i+1}_{int(time.time())}.png"
                            # 使用统一章节目录和分镜子目录
                            chapter_dir = self._get_chapter_dir_name(project_path)
                            segment_dir = f"segment_{segment_index + 1:02d}"
                            output_dir = f"{project_path}/chapters/{chapter_dir}/images/{segment_dir}"
                            output_path = f"{output_dir}/{filename}"

                            # 下载图像到本地
                            local_path = await download_image_from_url(variant_url, output_path)
                            logger.info(f"备选图 {i+1} 已下载到本地: {local_path}")

                            generated_images.append({
                                "image_option": i + 1,
                                "status": "success",
                                "image_url": variant_url,
                                "local_path": local_path,
                                "prompt_used": variant_prompt if 'variant_prompt' in locals() else optimized_prompt
                            })
                        else:
                            logger.error(f"备选图 {i+1} 生成失败，返回空URL (尝试 {attempt_count}/{max_attempts})")
                            if attempt_count < max_attempts:  # 只有还有尝试机会时才添加失败记录
                                generated_images.append({
                                    "image_option": i + 1,
                                    "status": "generation_failed",
                                    "error": "Empty URL returned"
                                })

                    except Exception as e:
                        logger.error(f"备选图 {i+1} 生成失败 (尝试 {attempt_count}/{max_attempts}): {e}")
                        if attempt_count < max_attempts:  # 只有还有尝试机会时才添加失败记录
                            generated_images.append({
                                "image_option": i + 1,
                                "status": "generation_failed",
                                "error": str(e)
                            })

                        # 如果是网络或API错误，等待一段时间再重试
                        if "network" in str(e).lower() or "connection" in str(e).lower() or "timeout" in str(e).lower():
                            import asyncio
                            await asyncio.sleep(2)  # 等待2秒后重试

                # 过滤掉失败的记录，只保留成功的图片
                successful_images = [img for img in generated_images if img["status"] == "success"]

                # 如果成功图片数量不足，填充占位图片
                while len(successful_images) < max_images:
                    placeholder_index = len(successful_images) + 1
                    logger.warning(f"无法生成足够的图片，使用占位图片 {placeholder_index}/{max_images}")
                    successful_images.append({
                        "image_option": placeholder_index,
                        "status": "placeholder",
                        "image_url": "/placeholder-image.png",
                        "local_path": "/placeholder-image.png",
                        "prompt_used": "占位图片",
                        "error": f"生成失败，使用占位图片"
                    })

                logger.info(f"备用方案完成，成功生成 {len(successful_images)} 张图片 (共尝试 {attempt_count} 次)")

                return {
                    "scene_description": scene_description,
                    "total_options": len(successful_images),
                    "generated_images": successful_images,
                    "generation_type": "fallback_multi_generation",  # 标记为备用多次生成模式
                    "prompt_used": optimized_prompt,
                    "max_images_configured": max_images,
                    "reference_image_used": reference_image_path or "",  # 记录使用的参考图片
                    "total_attempts": attempt_count  # 记录总尝试次数
                }

        except Exception as e:
            logger.error(f"场景图像生成失败: {e}")
            return {
                "scene_description": scene_description,
                "total_options": 0,
                "generated_images": [],
                "error": str(e),
                "generation_type": "failed"
            }

    def _optimize_scene_description(self, description: str, script: Dict[str, Any], project_path: str = "", reference_image_path: str = "") -> str:
        """
        优化场景描述，使用清晰的数据优先级避免信息冲突

        优先级规则：
        1. 用户编辑的文本 (description) - 最高优先级
        2. 用户选定的角色 (characters) - 次高优先级
        3. AI分析的结构化数据 - 仅作为补充，不与用户输入冲突
        4. 前情提要 - 独立的连贯性信息

        Args:
            description: 用户编辑的原始场景描述 (最高优先级)
            script: 包含结构化数据、角色选择等的脚本
            project_path: 项目路径，用于获取角色参考信息

        Returns:
            优化后的图像生成prompt
        """
        try:
            # 获取输入数据
            structured_data = script.get("structured_data")
            selected_characters = script.get("characters", [])
            style_requirements = script.get("style_requirements", "")

            # 获取角色参考信息
            character_references = {}
            if selected_characters and project_path:
                character_references = self._get_character_references(project_path, selected_characters)

            # 提取分段文本中的对话内容
            dialogue_requirements = []
            if description:
                extracted_dialogues = self._extract_dialogue_from_text(description)
                if extracted_dialogues:
                    # 构建对话要求
                    dialogue_text = "; ".join(extracted_dialogues)
                    dialogue_requirements.append(f"**强制要求** 画面中必须体现以下角色对话: {dialogue_text}")
                    logger.info(f"添加对话要求到prompt: {dialogue_text}")

            # 获取风格参考图片信息
            reference_images = script.get("reference_images", [])
            style_reference_info = ""
            if reference_images and project_path:
                style_reference_info = "参考上传的画风图片进行风格渲染"

            # 获取前情提要图片信息
            previous_context = script.get("previous_context", "")
            previous_segment_text = script.get("previous_segment_text", "")  # 新增：前情提要文本
            continuity_info = ""
            reference_image_path = None

            # 检查前情提要是否为图片路径
            if previous_context:
                import os

                # 处理项目相对路径 (如 /projects/2025.10.25_11.48_勇者斗恶龙/...)
                image_path = None
                if previous_context.startswith("/projects/"):
                    # 将项目相对路径转换为绝对路径
                    # 格式: /projects/项目名/子路径 -> 当前工作目录/projects/项目名/子路径
                    relative_path = previous_context[1:]  # 去掉开头的 /
                    image_path = os.path.join(os.getcwd(), relative_path)
                    logger.info(f"转换项目相对路径: {previous_context} -> {image_path}")
                elif os.path.isfile(previous_context):
                    # 直接是文件系统路径
                    image_path = previous_context

                if image_path and os.path.isfile(image_path):
                    # 前情提要是一个有效的图片文件路径
                    reference_image_path = image_path  # 使用绝对路径

                    # 构建包含前情提要文本的连贯性信息
                    if previous_segment_text:
                        continuity_info = f"保持与前情提要的剧情连贯性：前情概述'{previous_segment_text[:150]}...'，严格参考上一段画面的风格、角色外观、表情动作和场景布局"
                        logger.info(f"检测到前情提要图片参考和文本: {reference_image_path} + 文本:{previous_segment_text[:50]}...")
                    else:
                        continuity_info = f"保持与前情提要的剧情连贯性，严格参考上一段画面的风格、角色外观和场景布局"
                        logger.info(f"检测到前情提要图片参考: {reference_image_path}")
                else:
                    # 前情提要只是文字描述或路径无效
                    if previous_segment_text:
                        continuity_info = f"保持与前情提要的剧情连贯性：前情概述'{previous_segment_text[:150]}...'，参考上一段画面风格和角色状态"
                        logger.info(f"前情提要是文本描述（无图片）: {previous_segment_text[:50]}...")
                    else:
                        continuity_info = f"保持与前情提要的剧情连贯性，参考上一段画面"
                        logger.info(f"前情提要是文字描述或无效路径: {previous_context[:50]}...")
            else:
                # 没有前情提要图片，但可能有文本
                if previous_segment_text:
                    continuity_info = f"保持与前情提要的剧情连贯性：前情概述'{previous_segment_text[:150]}...'"
                    logger.info(f"仅前情提要文本（无图片）: {previous_segment_text[:50]}...")

            # 初始化各个部分
            core_scene = []      # 核心情节描述 (用户编辑的文本)
            character_info = []  # 角色信息 (用户选择的角色)
            scene_supplement = [] # 场景补充信息 (AI分析，仅当需要时)
            visual_elements = [] # 视觉元素 (AI分析)
            style_info = []      # 风格信息

            # 1. 核心情节描述 - 优先使用用户编辑的文本
            if description and description.strip():
                # 用户编辑的文本作为核心内容
                core_scene.append(description.strip())
                logger.info(f"使用用户编辑的文本作为核心情节: {len(description)} 字符")
            elif structured_data and "content" in structured_data:
                # 只有在用户没有编辑文本时，才使用AI分析的内容
                ai_content = structured_data["content"]
                core_scene.append(ai_content)
                logger.info(f"使用AI分析的内容作为核心情节: {len(ai_content)} 字符")

            # 2. 角色信息 - 优先使用用户选择的角色
            if selected_characters:
                for char_name in selected_characters:
                    if char_name in character_references:
                        char_ref = character_references[char_name]
                        # 添加角色名称和描述
                        char_desc = char_ref.get("description", "")
                        if char_desc:
                            character_info.append(f"{char_name}: {char_desc}")

                        # 添加角色特征标签
                        traits = char_ref.get("traits", [])
                        if traits:
                            character_info.append(f"{char_name}特征: {', '.join(traits[:3])}")

                        # 添加角色卡信息（如果有）
                        character_card = char_ref.get("character_card", {})
                        if character_card:
                            appearance = character_card.get("appearance", "")
                            personality = character_card.get("personality", "")
                            if appearance:
                                character_info.append(f"{char_name}外观: {appearance}")
                            if personality:
                                character_info.append(f"{char_name}性格: {personality}")
                    else:
                        # 如果没有角色参考信息，至少添加角色名
                        character_info.append(char_name)

            # 2.1. 使用text_segmenter提供的角色信息，无需额外优化

            # 3. 场景补充信息 - 始终使用AI分析数据来增强一致性
            if structured_data:
                # 使用AI分析的场景设定
                if "scene_setting" in structured_data:
                    scene_setting = structured_data["scene_setting"]
                    scene_supplement.append(f"环境: {scene_setting}")

                # 添加环境元素（增加数量）
                if "scene_elements" in structured_data:
                    env_elements = structured_data["scene_elements"]
                    if isinstance(env_elements, list):
                        scene_supplement.extend(env_elements[:4])  # 增加到4个环境元素
                    else:
                        scene_supplement.append(env_elements)

                # 添加关键事件信息（新）
                if "key_events" in structured_data:
                    key_events = structured_data["key_events"]
                    if isinstance(key_events, list):
                        scene_supplement.extend([f"事件: {event}" for event in key_events[:2]])
                    else:
                        scene_supplement.append(f"事件: {key_events}")

            # 4. 视觉元素和情感基调 - 从AI分析中提取（与用户输入不冲突）
            if structured_data:
                # 视觉关键词（增加数量）
                if "visual_keywords" in structured_data:
                    visual_keywords = structured_data["visual_keywords"]
                    if isinstance(visual_keywords, list):
                        visual_elements.extend(visual_keywords[:8])  # 增加到8个视觉关键词
                    else:
                        visual_elements.append(visual_keywords)

                # 画面焦点
                if "panel_focus" in structured_data:
                    visual_elements.append(structured_data["panel_focus"])

                # 情感基调
                if "emotional_tone" in structured_data:
                    visual_elements.append(f"情感基调: {structured_data['emotional_tone']}")

                # 角色描述（新增）
                if "character_descriptions" in structured_data:
                    char_descriptions = structured_data["character_descriptions"]
                    if isinstance(char_descriptions, dict):
                        for char_name, description in list(char_descriptions.items())[:3]:  # 前3个角色描述
                            visual_elements.append(f"{char_name}: {description}")

            # 5. 风格信息
            if style_requirements:
                style_info.append(style_requirements)
            if style_reference_info:
                style_info.append(style_reference_info)

            # 构建优化prompt - 按照优先级顺序
            if structured_data:
                optimized_parts = []

                # 1. 核心情节描述 (最高优先级)
                if core_scene:
                    optimized_parts.append(f"核心情节: {'; '.join(core_scene)}")

                # 2. 角色信息 (高优先级)
                if character_info:
                    optimized_parts.append(f"角色设定: {'; '.join(character_info[:3])}")  # 限制数量避免过长

                # 2.1. 对话要求 (高优先级，必须在画面中体现)
                if dialogue_requirements:
                    optimized_parts.extend(dialogue_requirements)  # 添加对话强制要求

                # 3. 场景补充信息 (中等优先级，仅当需要时)
                if scene_supplement:
                    optimized_parts.append(f"场景环境: {'; '.join(scene_supplement[:4])}")  # 增加到4个

                # 4. 视觉元素和情感 (中等优先级)
                if visual_elements:
                    optimized_parts.append(f"视觉风格: {'; '.join(visual_elements[:10])}")  # 增加到10个

                # 5. 剧情连贯性 (前情提要)
                if continuity_info:
                    if reference_image_path:
                        # 有图片参考时，连贯性信息优先级提高，并强调视觉一致性
                        optimized_parts.append(f"视觉连贯性要求: {continuity_info}")
                        logger.info("检测到图片参考，提升连贯性优先级")
                    else:
                        optimized_parts.append(continuity_info)

                # 6. 风格要求 (用户指定)
                if style_info:
                    optimized_parts.append(f"艺术风格: {', '.join(style_info)}")

                # 7. 基础风格和构图 (默认添加)
                if reference_image_path:
                    # 有图片参考时，更强调与参考图的一致性
                    optimized_parts.extend([
                        "**强制要求** 严格保持与参考图的角色外观、服装、发型、面部特征完全一致",
                        "**强制要求** 保持完全相同的绘画风格、线条粗细、色彩饱和度和色调",
                        "**强制要求** 保持相似的背景渲染风格和光影处理方式",
                        "**强制要求** 保持相同的角色比例和身材特征",
                        "漫画风格, 清晰线条, 精美构图, 统一艺术风格",
                        "高质量渲染, 保持系列连贯性"
                    ])
                else:
                    optimized_parts.extend([
                        "漫画风格, 清晰线条, 精美构图, 统一艺术风格",
                        "高质量渲染, 注意角色一致性"
                    ])

                optimized_prompt = ", ".join(optimized_parts)

            else:
                # 降级：没有结构化数据时的简单逻辑
                # 使用用户编辑的文本作为主要描述
                optimized_parts = [f"场景描述: {description}"]

                # 添加选定的角色信息
                if selected_characters:
                    for char_name in selected_characters:
                        if char_name in character_references:
                            char_ref = character_references[char_name]
                            char_desc = char_ref.get("description", "")
                            if char_desc:
                                optimized_parts.append(f"角色: {char_name} - {char_desc}")
                        else:
                            optimized_parts.append(f"角色: {char_name}")

                # 添加对话要求 (强制要求在画面中体现)
                if dialogue_requirements:
                    optimized_parts.extend(dialogue_requirements)  # 添加对话强制要求

                # 添加风格要求
                if style_requirements:
                    optimized_parts.append(f"风格: {style_requirements}")
                if style_reference_info:
                    optimized_parts.append(style_reference_info)

                # 添加前情提要
                if continuity_info:
                    optimized_parts.append(continuity_info)

                # 基础风格
                optimized_parts.extend(["漫画风格, 清晰线条", "高质量渲染"])

                optimized_prompt = ", ".join(optimized_parts)

            # 记录最终prompt长度和使用的策略
            logger.info(f"生成优化prompt，长度: {len(optimized_prompt)} 字符")
            logger.info(f"数据使用策略 - 用户文本: {'是' if core_scene else '否'}, "
                       f"选定角色: {len(selected_characters)}个, "
                       f"结构化数据: {'是' if structured_data else '否'}, "
                       f"场景补充: {'是' if scene_supplement else '否'}")

            # 6. 添加角色和场景约束 - 使用text_segmenter的分析结果
            character_count_constraints = self._extract_character_count_constraints(core_scene, structured_data, character_info)
            if character_count_constraints:
                # 添加约束到prompt中
                optimized_parts.extend(character_count_constraints)

            # 记录最终prompt长度和使用的策略
            logger.info(f"生成优化prompt，长度: {len(optimized_prompt)} 字符")
            logger.info(f"数据使用策略 - 用户文本: {'是' if core_scene else '否'}, "
                       f"选定角色: {len(selected_characters)}个, "
                       f"结构化数据: {'是' if structured_data else '否'}, "
                       f"场景补充: {'是' if scene_supplement else '否'}")

            return optimized_prompt

        except Exception as e:
            logger.error(f"优化场景描述失败: {e}")
            # 降级到最基础的描述
            return f"场景描述: {description}, 漫画风格, 高质量渲染"

    def _create_variant_prompt(self, base_prompt: str, variant_index: int, total_variants: int) -> str:
        """
        为生成多样性图片创建变体prompt

        Args:
            base_prompt: 基础prompt
            variant_index: 当前变体索引 (0-based)
            total_variants: 总变体数量

        Returns:
            变体prompt
        """
        try:
            # 检查是否有前情提要参考图，如果有则优先保持风格一致性
            has_reference = "**强制要求** " in base_prompt or "reference_image_path" in str(base_prompt)

            if has_reference:
                # 有前情提要时，使用更保守的变体策略，主要调整构图细节
                conservative_variations = [
                    # 构图微调（保持风格一致）
                    ["构图微调: 略微调整画面布局", "构图微调: 优化人物位置", "构图微调: 调整视角角度"],
                    # 细节丰富（保持风格一致）
                    ["细节丰富: 增加背景层次", "细节丰富: 优化服装纹理", "细节丰富: 增强表情细节"],
                    # 焦点变化（保持风格一致）
                    ["焦点调整: 突出人物表情", "焦点调整: 强调动作细节", "焦点调整: 平衡前景背景"],
                    # 情感表达（保持风格一致）
                    ["情感表达: 丰富面部表情", "情感表达: 优化姿态语言", "情感表达: 增强眼神交流"]
                ]

                # 选择保守策略
                strategy_index = variant_index % len(conservative_variations)
                selected_strategy = conservative_variations[strategy_index]
                variation_index_in_strategy = variant_index % len(selected_strategy)
                variation = selected_strategy[variation_index_in_strategy]

                # 为有参考图的变体添加风格一致性强调
                consistency_prefix = "**保持风格一致** "
                variation = f"{consistency_prefix} {variation}"

            else:
                # 没有前情提要时，使用适度变化策略
                moderate_variations = [
                    # 温和的视角变化
                    ["视角: 标准视角", "视角: 略微仰视", "视角: 略微俯视"],
                    # 光照微调
                    ["光照: 自然光效", "光照: 柔和光效", "光照: 明亮光效"],
                    # 构图调整
                    ["构图: 居中构图", "构图: 三分法构图", "构图: 稳定构图"],
                    # 细节侧重
                    ["细节: 人物清晰", "细节: 环境丰富", "细节: 表情生动"]
                ]

                strategy_index = variant_index % len(moderate_variations)
                selected_strategy = moderate_variations[strategy_index]
                variation_index_in_strategy = variant_index % len(selected_strategy)
                variation = selected_strategy[variation_index_in_strategy]

            # 构建变体prompt，确保风格一致性要求在前
            if has_reference:
                # 有参考图时，在前面重复强调风格一致性
                style_consistency = "**再次强调** 严格保持与前面画面的艺术风格、角色外观、色彩完全一致"
                variant_prompt = f"{base_prompt}, {style_consistency}, {variation}"
            else:
                variant_prompt = f"{base_prompt}, {variation}"

            # 确保prompt长度合理
            if len(variant_prompt) > 400:
                variant_prompt = variant_prompt[:397] + "..."

            logger.info(f"创建变体prompt {variant_index+1}/{total_variants}: {variation}")

            return variant_prompt

        except Exception as e:
            logger.error(f"创建变体prompt失败: {e}")
            # 降级：添加安全的、保持风格一致性的变化
            if "**强制要求** " in base_prompt:
                # 有参考图时，使用最保守的变化
                safe_variations = [
                    "构图微调", "细节优化", "表情调整", "姿态优化"
                ]
                safe_variation = safe_variations[variant_index % len(safe_variations)]
                return f"{base_prompt}, **保持风格一致** {safe_variation}"
            else:
                # 没有参考图时的安全变化
                safe_variations = ["不同角度", "细节变化", "构图调整", "表情变化"]
                safe_variation = safe_variations[variant_index % len(safe_variations)]
                return f"{base_prompt}, {safe_variation}"

    async def edit_image_with_prompt(self, image_url: str, edit_prompt: str, project_path: str) -> str:
        """
        使用提示词编辑图像

        Args:
            image_url: 原图像URL
            edit_prompt: 编辑提示词
            project_path: 项目路径

        Returns:
            编辑后的图像URL
        """
        if not volc_service.is_available():
            logger.error("图像编辑失败，因为火山引擎服务不可用。")
            return None

        try:
            logger.info(f"使用提示词编辑图像: {edit_prompt}")

            # 调用图像编辑API
            edited_url = volc_service.image_to_image(
                model=EDIT_MODEL,
                prompt=edit_prompt,
                image_url=image_url
            )

            if edited_url:
                # 处理API返回的字典格式
                if isinstance(edited_url, dict):
                    edited_url = edited_url.get('image_url')

                # 下载编辑后的图像
                try:
                    from utils.image_utils import download_image_from_url
                    import time

                    filename = f"edited_{int(time.time())}.png"
                    # 使用智能章节编号系统，默认保存到最新章节
                    chapter_dir = self._get_chapter_dir_name(project_path)
                    output_dir = f"{project_path}/chapters/{chapter_dir}/images"
                    output_path = f"{output_dir}/{filename}"

                    local_path = await download_image_from_url(edited_url, output_path)
                    logger.info(f"编辑后的图像已下载到本地: {local_path}")

                    return local_path
                except Exception as e:
                    logger.error(f"下载编辑图像失败: {e}")
                    return None
            else:
                logger.error("图像编辑失败，返回空URL")
                return None

        except Exception as e:
            logger.error(f"图像编辑过程出现异常: {e}")
            return None

    def _extract_dialogue_from_text(self, text: str) -> List[str]:
        """
        从文本中提取角色对话内容

        Args:
            text: 输入的文本内容

        Returns:
            提取的对话列表
        """
        try:
            import re
            dialogues = []

            # 匹配中文对话格式："..." 或 「...」
            chinese_quotes_pattern = r'["""](.*?)["""]'
            chinese_brackets_pattern = r'[「『](.*?)[」』]'

            # 提取引号对话
            quote_matches = re.findall(chinese_quotes_pattern, text)
            dialogues.extend([f"\"{dialogue}\"" for dialogue in quote_matches])

            # 提取括号对话
            bracket_matches = re.findall(chinese_brackets_pattern, text)
            dialogues.extend([f"「{dialogue}」" for dialogue in bracket_matches])

            # 匹配英文对话格式："..." 或 '...'
            english_quotes_pattern = r'["\']([^"\']+)["\']'
            english_matches = re.findall(english_quotes_pattern, text)
            dialogues.extend([f"\"{dialogue}\"" for dialogue in english_matches])

            # 去重并过滤过短的对话
            unique_dialogues = []
            for dialogue in dialogues:
                if len(dialogue.strip()) > 3 and dialogue not in unique_dialogues:
                    unique_dialogues.append(dialogue)

            if unique_dialogues:
                logger.info(f"从文本中提取到 {len(unique_dialogues)} 处对话: {unique_dialogues}")

            return unique_dialogues[:3]  # 最多保留3处对话，避免prompt过长

        except Exception as e:
            logger.error(f"提取对话失败: {e}")
            return []

    def _extract_character_count_constraints(self, core_scene: str, structured_data: Dict[str, Any], character_info: List[str]) -> List[str]:
        """
        从结构化数据中提取角色数量约束
        角色识别和数量分析应该在text_segmenter中完成
        """
        constraints = []

        try:
            # 使用text_segmenter已经分析好的结构化数据
            if structured_data:
                # 从characters字段提取角色信息
                characters = structured_data.get("characters", "")
                if characters:
                    constraints.append(f"场景中的角色: {characters}")

                # 从character_descriptions字段提取详细角色信息
                character_descriptions = structured_data.get("character_descriptions", {})
                if character_descriptions and isinstance(character_descriptions, dict):
                    for char_name, descriptions in character_descriptions.items():
                        if descriptions and isinstance(descriptions, list):
                            constraints.append(f"角色{char_name}: {', '.join(descriptions[:2])}")

            # 通用角色一致性约束
            constraints.append("确保角色外观和服装保持一致性")
            constraints.append("严格按照场景描述生成相应数量的角色")

            return constraints

        except Exception as e:
            logger.error(f"提取角色数量约束失败: {e}")
            return []

  
# 创建一个单例
image_generator = ImageGenerator()  # 强制重新加载 - Sat Oct 25 18:09:21 CST 2025
