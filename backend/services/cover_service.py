"""
封面生成服务
Cover Generation Service
"""

import logging
import json
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

from fastapi import UploadFile
from services.file_system import ProjectFileSystem
from services.comic_service import ComicService
from services.ai_service import AIService
from agents.cover_generator import CoverGenerator

logger = logging.getLogger(__name__)


class CoverService:
    """封面生成服务类"""

    def __init__(self):
        self.ai_service = AIService()
        self.cover_generator = CoverGenerator()

    async def generate_cover(
        self,
        project_id: str,
        cover_type: str,
        novel_filename: Optional[str] = None,
        cover_prompt: str = "",
        cover_size: str = "1024x1024",
        reference_image: Optional[UploadFile] = None,
        file_system: Optional[ProjectFileSystem] = None,
        comic_service: Optional[ComicService] = None
    ) -> Dict[str, Any]:
        """
        生成漫画封面

        Args:
            project_id: 项目ID
            cover_type: 封面类型 ("project" | "chapter")
            novel_filename: 小说文件名（章节封面时必需）
            cover_prompt: 用户提供的封面描述
            cover_size: 封面尺寸
            reference_image: 参考图片文件
            file_system: 文件系统服务
            comic_service: 漫画服务

        Returns:
            封面生成结果
        """
        try:
            logger.info(f"开始生成封面 - 项目: {project_id}, 类型: {cover_type}")

            # 获取项目路径
            if not file_system:
                file_system = ProjectFileSystem()

            project_path_str = file_system.get_project_path(project_id)
            if not project_path_str:
                raise ValueError(f"项目 {project_id} 不存在")
            project_path = Path(project_path_str)

            # 处理参考图
            reference_image_path = None
            if reference_image and reference_image.filename:
                reference_image_path = await self._save_reference_image(
                    project_path, reference_image
                )

            # 直接使用用户输入的封面描述，不进行AI分析
            cover_description = cover_prompt.strip() if cover_prompt.strip() else f"精美的漫画{cover_type}封面"

            # 生成封面图像
            image_result = await self._generate_cover_image(
                description=cover_description,
                size=cover_size,
                reference_image_path=reference_image_path
            )

            # 下载图片到本地
            local_image_path = None
            logger.info(f"开始下载图片，image_result: {image_result}")
            if image_result.get("image_url"):
                logger.info(f"图片URL存在，开始下载: {image_result['image_url']}")
                try:
                    # 根据封面类型创建对应目录
                    if cover_type == "project":
                        covers_dir = project_path / "covers" / "project"
                    else:
                        covers_dir = project_path / "covers" / "chapters"

                    covers_dir.mkdir(parents=True, exist_ok=True)
                    logger.info(f"封面目录已创建: {covers_dir}")

                    # 下载图片到对应类型目录
                    local_image_path = await self.ai_service.download_image_result(
                        image_result["image_url"],
                        str(covers_dir)
                    )
                    logger.info(f"图片已下载到本地: {local_image_path}")
                except Exception as e:
                    logger.error(f"下载图片失败: {e}")
                    import traceback
                    logger.error(f"详细错误信息: {traceback.format_exc()}")
                    # 如果下载失败，继续使用远程URL
            else:
                logger.warning("image_result中没有image_url字段")

            # 保存封面信息
            cover_data = {
                "cover_id": f"cover_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "project_id": project_id,
                "cover_type": cover_type,
                "related_novel": novel_filename,
                "title": self._generate_cover_title(cover_type, novel_filename, project_path),
                "description": cover_description,
                "size": cover_size,
                "reference_image_path": reference_image_path,
                "image_url": image_result.get("image_url"),
                "local_path": local_image_path,
                "status": "completed",
                "created_at": datetime.now().isoformat()
            }

            # 保存到文件系统
            await self._save_cover_data(project_path, cover_data)

            logger.info(f"封面生成完成: {cover_data['cover_id']}")

            return {
                "success": True,
                "cover_id": cover_data["cover_id"],
                "title": cover_data["title"],
                "description": cover_data["description"],
                "image_url": cover_data["image_url"],
                "local_path": cover_data["local_path"],
                "cover_type": cover_data["cover_type"],
                "related_novel": cover_data["related_novel"],
                "status": cover_data["status"]
            }

        except Exception as e:
            logger.error(f"封面生成失败: {e}")
            raise

  
    async def _generate_cover_image(
        self,
        description: str,
        size: str,
        reference_image_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        生成封面图像
        """
        try:
            # 直接使用用户输入的描述，不进行AI分析
            final_prompt = description

            # 如果有参考图片，添加一致性要求
            if reference_image_path:
                logger.info(f"📸 使用参考图片: {reference_image_path}")
                # 添加基础的参考图一致性提示
                consistency_prompt = """

请保持与参考图片相同的角色外观、服装、发型和绘画风格，确保整体视觉一致性。
"""
                final_prompt = description + consistency_prompt
            else:
                logger.info(f"ℹ️ 未提供参考图片，使用原始描述")

            # 添加质量要求
            final_prompt = f"{final_prompt}，高质量漫画封面，色彩鲜明，构图均衡"

            # 调用AI服务生成图像
            logger.info(f"🎨 开始生成图像，尺寸: {size}")
            logger.info(f"📝 最终prompt: {final_prompt}")
            result = await self.ai_service.generate_image(
                prompt=final_prompt,
                size=size,
                quality="standard"
            )

            return result

        except Exception as e:
            logger.error(f"生成封面图像失败: {e}")
            raise

    def _generate_cover_title(
        self,
        cover_type: str,
        novel_filename: Optional[str],
        project_path: Path
    ) -> str:
        """
        生成封面标题
        """
        try:
            if cover_type == "project":
                # 项目封面
                meta_file = project_path / "meta" / "project.json"
                if meta_file.exists():
                    with open(meta_file, 'r', encoding='utf-8') as f:
                        project_info = json.load(f)
                        return f"{project_info.get('name', '项目')}封面"
                return "项目封面"
            else:
                # 章节封面
                if novel_filename:
                    # 从小说文件名生成标题
                    title = Path(novel_filename).stem
                    return f"{title}封面"
                return "章节封面"

        except Exception as e:
            logger.error(f"生成封面标题失败: {e}")
            return "漫画封面"

    async def _save_cover_data(self, project_path: Path, cover_data: Dict[str, Any]):
        """
        保存封面数据到文件系统，支持分层目录结构
        """
        try:
            # 创建分层封面目录结构
            if cover_data["cover_type"] == "project":
                # 项目封面存储在 project/covers/ 目录
                cover_type_dir = project_path / "covers" / "project"
            else:
                # 章节封面存储在 chapters/covers/ 目录
                cover_type_dir = project_path / "covers" / "chapters"

            cover_type_dir.mkdir(parents=True, exist_ok=True)

            # 保存封面数据到对应类型目录
            cover_file = cover_type_dir / f"{cover_data['cover_id']}.json"
            with open(cover_file, 'w', encoding='utf-8') as f:
                json.dump(cover_data, f, ensure_ascii=False, indent=2)

            # 更新项目封面列表（保持向后兼容）
            covers_list_file = project_path / "covers" / "covers_list.json"
            covers_list = []

            if covers_list_file.exists():
                with open(covers_list_file, 'r', encoding='utf-8') as f:
                    covers_list = json.load(f)

            covers_list.append({
                "cover_id": cover_data["cover_id"],
                "title": cover_data["title"],
                "cover_type": cover_data["cover_type"],
                "related_novel": cover_data["related_novel"],
                "created_at": cover_data["created_at"],
                "image_url": cover_data["image_url"],
                "local_path": cover_data["local_path"]
            })

            with open(covers_list_file, 'w', encoding='utf-8') as f:
                json.dump(covers_list, f, ensure_ascii=False, indent=2)

            # 同时在对应类型目录下维护类型专属列表
            if cover_data["cover_type"] == "project":
                project_list_file = project_path / "covers" / "project" / "covers_list.json"
            else:
                project_list_file = project_path / "covers" / "chapters" / "covers_list.json"

            type_covers_list = []
            if project_list_file.exists():
                with open(project_list_file, 'r', encoding='utf-8') as f:
                    type_covers_list = json.load(f)

            type_covers_list.append({
                "cover_id": cover_data["cover_id"],
                "title": cover_data["title"],
                "cover_type": cover_data["cover_type"],
                "related_novel": cover_data["related_novel"],
                "created_at": cover_data["created_at"],
                "image_url": cover_data["image_url"],
                "local_path": cover_data["local_path"]
            })

            with open(project_list_file, 'w', encoding='utf-8') as f:
                json.dump(type_covers_list, f, ensure_ascii=False, indent=2)

            logger.info(f"封面数据已保存: {cover_file}")

        except Exception as e:
            logger.error(f"保存封面数据失败: {e}")
            raise

    async def _save_reference_image(self, project_path: Path, reference_image: UploadFile) -> str:
        """
        保存参考图片到项目目录，使用专门的参考图片目录
        """
        try:
            # 创建专门的参考图目录
            ref_images_dir = project_path / "covers" / "reference_images"
            ref_images_dir.mkdir(parents=True, exist_ok=True)

            # 生成唯一文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_extension = Path(reference_image.filename).suffix or ".jpg"
            # 清理文件名中的特殊字符
            safe_filename = "".join(c for c in Path(reference_image.filename).stem if c.isalnum() or c in (' ', '-', '_')).rstrip()
            if not safe_filename:
                safe_filename = "reference"
            filename = f"ref_{timestamp}_{safe_filename}{file_extension}"
            file_path = ref_images_dir / filename

            # 保存文件内容
            file_content = await reference_image.read()
            with open(file_path, "wb") as buffer:
                buffer.write(file_content)

            logger.info(f"参考图已保存: {file_path} (大小: {len(file_content)} bytes)")
            return str(file_path.relative_to(project_path))

        except Exception as e:
            logger.error(f"保存参考图失败: {e}")
            raise

    def get_project_covers(self, project_id: str, file_system: ProjectFileSystem) -> List[Dict[str, Any]]:
        """
        获取项目封面列表，支持新的分层目录结构，同时保持向后兼容
        自动清理指向不存在文件的封面记录
        """
        try:
            project_path_str = file_system.get_project_path(project_id)
            if not project_path_str:
                raise ValueError(f"项目 {project_id} 不存在")
            project_path = Path(project_path_str)

            covers_list = []

            # 首先尝试从传统目录结构获取封面列表（向后兼容）
            covers_list_file = project_path / "covers" / "covers_list.json"
            if covers_list_file.exists():
                with open(covers_list_file, 'r', encoding='utf-8') as f:
                    covers_list = json.load(f)

            # 如果传统列表为空，尝试从新的分层目录结构获取封面
            if not covers_list:
                # 从项目封面目录获取
                project_covers_file = project_path / "covers" / "project" / "covers_list.json"
                if project_covers_file.exists():
                    with open(project_covers_file, 'r', encoding='utf-8') as f:
                        project_covers = json.load(f)
                        covers_list.extend(project_covers)

                # 从章节封面目录获取
                chapter_covers_file = project_path / "covers" / "chapters" / "covers_list.json"
                if chapter_covers_file.exists():
                    with open(chapter_covers_file, 'r', encoding='utf-8') as f:
                        chapter_covers = json.load(f)
                        covers_list.extend(chapter_covers)

            # 清理无效的封面记录
            cleaned_covers = self._clean_invalid_covers(covers_list, project_path)

            # 如果有清理操作，保存清理后的数据
            if len(cleaned_covers) != len(covers_list):
                logger.info(f"清理了 {len(covers_list) - len(cleaned_covers)} 条无效封面记录")
                self._save_cleaned_covers(project_path, cleaned_covers)

            # 按创建时间排序（最新的在前）
            cleaned_covers.sort(key=lambda x: x.get("created_at", ""), reverse=True)

            return cleaned_covers

        except Exception as e:
            logger.error(f"获取封面列表失败: {e}")
            return []

    def _clean_invalid_covers(self, covers_list: List[Dict[str, Any]], project_path: Path) -> List[Dict[str, Any]]:
        """
        清理指向不存在文件的封面记录
        """
        try:
            valid_covers = []
            invalid_count = 0

            # 获取所有实际存在的PNG文件
            actual_files = set()
            for png_file in project_path.rglob('*.png'):
                if 'covers' in str(png_file):
                    actual_files.add(png_file.name)

            for cover in covers_list:
                local_path = cover.get('local_path', '')

                if not local_path:
                    # 没有本地路径但有远程URL的记录保留
                    if cover.get('image_url'):
                        valid_covers.append(cover)
                    else:
                        logger.warning(f"封面记录缺少文件路径和URL: {cover.get('cover_id', 'unknown')}")
                        invalid_count += 1
                    continue

                # 提取文件名
                filename = Path(local_path).name

                # 检查文件是否存在
                if filename in actual_files:
                    valid_covers.append(cover)
                else:
                    logger.warning(f"封面文件不存在: {cover.get('cover_id', 'unknown')} -> {filename}")
                    invalid_count += 1

            if invalid_count > 0:
                logger.info(f"发现 {invalid_count} 条无效封面记录，已清理")

            return valid_covers

        except Exception as e:
            logger.error(f"清理无效封面记录失败: {e}")
            # 如果清理失败，返回原始列表
            return covers_list

    def _save_cleaned_covers(self, project_path: Path, cleaned_covers: List[Dict[str, Any]]):
        """
        保存清理后的封面数据
        """
        try:
            # 更新主要的covers_list.json文件
            covers_list_file = project_path / "covers" / "covers_list.json"

            with open(covers_list_file, 'w', encoding='utf-8') as f:
                json.dump(cleaned_covers, f, ensure_ascii=False, indent=2)

            logger.info(f"已保存清理后的封面列表到: {covers_list_file}")

        except Exception as e:
            logger.error(f"保存清理后的封面数据失败: {e}")

    async def get_cover_details(
        self,
        project_id: str,
        cover_id: str,
        file_system: ProjectFileSystem
    ) -> Optional[Dict[str, Any]]:
        """
        获取封面详细信息，支持新的分层目录结构，同时保持向后兼容
        """
        try:
            project_path_str = file_system.get_project_path(project_id)
            if not project_path_str:
                return None
            project_path = Path(project_path_str)

            # 首先尝试从传统目录查找（向后兼容）
            cover_file = project_path / "covers" / f"{cover_id}.json"
            if cover_file.exists():
                with open(cover_file, 'r', encoding='utf-8') as f:
                    return json.load(f)

            # 如果传统目录中没有，尝试从新的分层目录查找
            # 在项目封面目录中查找
            project_cover_file = project_path / "covers" / "project" / f"{cover_id}.json"
            if project_cover_file.exists():
                with open(project_cover_file, 'r', encoding='utf-8') as f:
                    return json.load(f)

            # 在章节封面目录中查找
            chapter_cover_file = project_path / "covers" / "chapters" / f"{cover_id}.json"
            if chapter_cover_file.exists():
                with open(chapter_cover_file, 'r', encoding='utf-8') as f:
                    return json.load(f)

            return None

        except Exception as e:
            logger.error(f"获取封面详情失败: {e}")
            return None

    def delete_cover(
        self,
        project_id: str,
        cover_id: str,
        file_system: ProjectFileSystem
    ) -> bool:
        """
        删除封面，支持新的分层目录结构，同时保持向后兼容
        """
        try:
            project_path_str = file_system.get_project_path(project_id)
            if not project_path_str:
                raise FileNotFoundError(f"项目 {project_id} 不存在")
            project_path = Path(project_path_str)

            cover_deleted = False
            cover_data = None

            # 首先尝试从传统目录查找并删除（向后兼容）
            cover_file = project_path / "covers" / f"{cover_id}.json"
            if cover_file.exists():
                with open(cover_file, 'r', encoding='utf-8') as f:
                    cover_data = json.load(f)
                cover_file.unlink()
                cover_deleted = True
                logger.info(f"从传统目录删除封面文件: {cover_file}")

            # 如果传统目录中没有，尝试从新的分层目录查找并删除
            if not cover_deleted:
                # 在项目封面目录中查找
                project_cover_file = project_path / "covers" / "project" / f"{cover_id}.json"
                if project_cover_file.exists():
                    with open(project_cover_file, 'r', encoding='utf-8') as f:
                        cover_data = json.load(f)
                    project_cover_file.unlink()
                    cover_deleted = True
                    logger.info(f"从项目封面目录删除封面文件: {project_cover_file}")

                # 在章节封面目录中查找
                if not cover_deleted:
                    chapter_cover_file = project_path / "covers" / "chapters" / f"{cover_id}.json"
                    if chapter_cover_file.exists():
                        with open(chapter_cover_file, 'r', encoding='utf-8') as f:
                            cover_data = json.load(f)
                        chapter_cover_file.unlink()
                        cover_deleted = True
                        logger.info(f"从章节封面目录删除封面文件: {chapter_cover_file}")

            if not cover_deleted:
                logger.warning(f"封面 {cover_id} 的文件未找到")
            else:
                # 删除本地图片文件（如果存在）
                covers_dir = project_path / "covers"
                for img_file in covers_dir.rglob(f"{cover_id}*"):
                    if img_file.is_file() and img_file.name.startswith(cover_id):
                        img_file.unlink()
                        logger.info(f"删除图片文件: {img_file}")

                # 更新所有相关的封面列表文件
                list_files_to_update = [
                    project_path / "covers" / "covers_list.json",
                    project_path / "covers" / "project" / "covers_list.json",
                    project_path / "covers" / "chapters" / "covers_list.json"
                ]

                for list_file in list_files_to_update:
                    if list_file.exists():
                        with open(list_file, 'r', encoding='utf-8') as f:
                            covers_list = json.load(f)

                        # 移除指定的封面
                        original_length = len(covers_list)
                        covers_list = [cover for cover in covers_list if cover.get("cover_id") != cover_id]

                        # 如果有删除，保存更新后的列表
                        if len(covers_list) != original_length:
                            with open(list_file, 'w', encoding='utf-8') as f:
                                json.dump(covers_list, f, ensure_ascii=False, indent=2)
                            logger.info(f"更新封面列表文件: {list_file}")

            logger.info(f"封面 {cover_id} 删除成功")
            return True

        except Exception as e:
            logger.error(f"删除封面失败: {e}")
            raise

    def set_primary_cover(
        self,
        project_id: str,
        cover_id: str,
        file_system: ProjectFileSystem
    ) -> Dict[str, Any]:
        """
        设置主要封面，支持新的分层目录结构，同时保持向后兼容
        """
        try:
            project_path_str = file_system.get_project_path(project_id)
            if not project_path_str:
                raise FileNotFoundError(f"项目 {project_id} 不存在")
            project_path = Path(project_path_str)

            # 需要更新的所有封面列表文件
            list_files_to_update = [
                project_path / "covers" / "covers_list.json",
                project_path / "covers" / "project" / "covers_list.json",
                project_path / "covers" / "chapters" / "covers_list.json"
            ]

            target_cover = None

            # 遍历所有列表文件，找到并更新目标封面
            for list_file in list_files_to_update:
                if list_file.exists():
                    with open(list_file, 'r', encoding='utf-8') as f:
                        covers_list = json.load(f)

                    # 查找目标封面并更新主封面状态
                    updated_covers = []
                    for cover in covers_list:
                        if cover.get("cover_id") == cover_id:
                            target_cover = cover.copy()
                            # 设置为主要封面
                            target_cover["is_primary"] = True
                            updated_covers.append(target_cover)
                        else:
                            # 移除其他封面的主封面标记
                            cover_copy = cover.copy()
                            cover_copy.pop("is_primary", None)
                            updated_covers.append(cover_copy)

                    # 保存更新后的列表
                    with open(list_file, 'w', encoding='utf-8') as f:
                        json.dump(updated_covers, f, ensure_ascii=False, indent=2)

                    logger.info(f"更新封面列表文件: {list_file}")

            if not target_cover:
                raise ValueError(f"封面 {cover_id} 不存在")

            logger.info(f"封面 {cover_id} 已设置为主要封面")
            return target_cover

        except Exception as e:
            logger.error(f"设置主要封面失败: {e}")
            raise