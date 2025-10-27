"""
项目文件系统管理服务
Project File System Management Service

负责管理漫画项目的目录结构、文件存储和历史记录
Manages comic project directory structure, file storage, and history
"""

import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging

try:
    from config import settings
except Exception:
    from backend.config import settings

from models.comic import (
    ChapterInfo, ChapterDetail, ChapterImage, ComicPanel,
    ProjectChaptersInfo, StorySegment, ParagraphInfo
)

logger = logging.getLogger(__name__)


class ProjectFileSystem:
    """
    项目文件系统管理类

    实现基于文件目录的项目管理，包括：
    - 项目目录结构的创建和管理
    - 文件存储和检索
    - 操作历史记录的保存和查询
    - 项目时间线的构建
    """

    def __init__(self, projects_dir: Optional[str] = None):
        self.projects_dir = Path(projects_dir) if projects_dir else settings.PROJECTS_DIR
        self.projects_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"项目文件系统初始化完成，根目录: {self.projects_dir}")

    def create_project(self, project_name: str, novel_text: str = "", description: str = "") -> str:
        """
        创建新项目目录结构

        Args:
            project_name: 项目名称
            novel_text: 原始小说文本
            description: 项目描述

        Returns:
            项目目录路径
        """
        timestamp = datetime.now().strftime("%Y.%m.%d_%H.%M")
        project_dir = self.projects_dir / f"{timestamp}_{project_name}"

        # 创建完整目录结构
        directories = [
            "meta",           # 项目元信息
            "source",         # 原始文件
            "processing",     # 处理历史
            "characters",     # 角色管理
            "chapters",       # 章节和画面
            "output",         # 最终输出
            "logs"           # 日志文件
        ]

        for dir_name in directories:
            (project_dir / dir_name).mkdir(parents=True, exist_ok=True)

        # 保存项目基本信息
        meta_info = {
            "project_id": f"{timestamp}_{project_name}",
            "project_name": project_name,
            "description": description,
            "created_at": datetime.now().isoformat(),
            "status": "created",
            "total_characters": len(novel_text),
            "current_step": "initialized"
        }

        self._save_json(project_dir / "meta" / "project.json", meta_info)

        # 保存原始小说文本
        if novel_text:
            source_file = project_dir / "source" / "novel.txt"
            source_file.write_text(novel_text, encoding='utf-8')

            # 记录历史
            self._save_history(
                str(project_dir),
                "source_created",
                {"characters_count": len(novel_text), "file_size": source_file.stat().st_size}
            )

        logger.info(f"项目创建成功: {project_dir}")
        return str(project_dir)

    def _resolve_project_path(self, project_identifier: str) -> Path:
        """
        通过项目名或完整路径解析项目目录。
        - 如果传入的是绝对/相对路径且存在，则直接使用
        - 否则在 projects_dir 下匹配：目录名等于 identifier 或以 "_<name>" 结尾
        """
        candidate = Path(project_identifier)
        if candidate.exists() and candidate.is_dir():
            return candidate
        matched = []
        for d in self.projects_dir.iterdir():
            if d.is_dir():
                # 同时支持传入 project_id（完整目录名）与项目名（后缀匹配）
                if d.name == project_identifier or d.name.endswith(f"_{project_identifier}"):
                    matched.append(d)
        if not matched:
            raise FileNotFoundError(f"未找到项目: {project_identifier}")
        matched.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        return matched[0]

    def save_file(self, project_identifier: str, subdir: str, filename: str, data: Any) -> str:
        """
        保存任意数据到项目子目录文件。
        - data 为 dict/list 时保存为 JSON
        - data 为 str 时保存为文本
        - 其他类型将转换为字符串保存
        返回保存的文件路径字符串
        """
        project_dir = self._resolve_project_path(project_identifier)
        target_dir = project_dir / subdir
        target_dir.mkdir(parents=True, exist_ok=True)
        file_path = target_dir / filename

        try:
            if isinstance(data, (dict, list)) and filename.lower().endswith(".json"):
                self._save_json(file_path, data)  # type: ignore[arg-type]
            elif isinstance(data, str):
                file_path.write_text(data, encoding="utf-8")
            else:
                file_path.write_text(str(data), encoding="utf-8")
        except Exception as e:
            logger.error(f"保存文件失败 {file_path}: {e}")
            raise

        # 记录历史
        try:
            self._save_history(str(project_dir), "file_saved", {
                "subdir": subdir,
                "filename": filename,
                "size": file_path.stat().st_size if file_path.exists() else 0
            })
        except Exception as e:
            logger.warning(f"保存历史失败: {e}")

        return str(file_path)

    def save_history(self, project_identifier: str, history_type: str, data: Dict[str, Any]):
        """对外暴露的保存历史方法，兼容测试脚本调用。"""
        project_dir = self._resolve_project_path(project_identifier)
        self._save_history(str(project_dir), history_type, data)

    def get_project_timeline(self, project_identifier: str) -> List[Dict[str, Any]]:
        """
        获取项目完整时间线（兼容项目名或路径）
        """
        project_dir = self._resolve_project_path(project_identifier)
        processing_dir = project_dir / "processing"

        timeline: List[Dict[str, Any]] = []
        for history_file in processing_dir.glob("*.history"):
            try:
                history_data = self._load_json(history_file)
                if isinstance(history_data, list):
                    timeline.extend(history_data)
            except Exception as e:
                logger.warning(f"读取历史文件失败 {history_file}: {e}")

        timeline.sort(key=lambda x: x.get("timestamp", ""))
        return timeline

    def get_project_path(self, project_name: str) -> str:
        """
        获取项目目录路径

        Args:
            project_name: 项目名称

        Returns:
            项目目录的绝对路径
        """
        project_dir = self.projects_dir / project_name

        if not project_dir.exists():
            raise FileNotFoundError(f"项目目录不存在: {project_dir}")

        return str(project_dir)

    def get_project_info(self, project_path: str) -> Dict[str, Any]:
        """
        获取项目基本信息

        Args:
            project_path: 项目路径

        Returns:
            项目信息字典
        """
        project_dir = Path(project_path)
        meta_file = project_dir / "meta" / "project.json"

        if not meta_file.exists():
            raise FileNotFoundError(f"项目元信息文件不存在: {meta_file}")

        return self._load_json(meta_file)

    def update_project_info(self, project_path: str, update_data: Dict[str, Any]) -> bool:
        """
        更新项目信息

        Args:
            project_path: 项目路径
            update_data: 更新的数据字典

        Returns:
            是否更新成功
        """
        try:
            project_dir = Path(project_path)
            meta_file = project_dir / "meta" / "project.json"

            if not meta_file.exists():
                logger.error(f"项目元信息文件不存在: {meta_file}")
                return False

            # 读取现有项目信息
            project_info = self._load_json(meta_file)

            # 更新字段
            if "name" in update_data and update_data["name"]:
                project_info["project_name"] = update_data["name"]
                # 注意：不要改变项目ID，保持原来的ID以确保文件系统路径一致性

            if "description" in update_data:
                project_info["description"] = update_data["description"]

            # 更新修改时间
            project_info["updated_at"] = datetime.now().isoformat()

            # 保存更新后的信息
            self._save_json(meta_file, project_info)

            # 记录历史
            self._save_history(project_path, "project_updated", {
                "updated_fields": list(update_data.keys()),
                "update_data": update_data
            })

            logger.info(f"项目信息更新成功: {project_path}")
            return True

        except Exception as e:
            logger.error(f"更新项目信息失败: {e}")
            return False

    def update_project_status(self, project_path: str, status: str, step: str, **kwargs):
        """
        更新项目状态

        Args:
            project_path: 项目路径
            status: 新状态
            step: 当前步骤
            **kwargs: 额外的状态信息
        """
        project_dir = Path(project_path)
        meta_file = project_dir / "meta" / "project.json"

        if not meta_file.exists():
            raise FileNotFoundError(f"项目元信息文件不存在: {meta_file}")

        meta_info = self._load_json(meta_file)
        meta_info["status"] = status
        meta_info["current_step"] = step
        meta_info["updated_at"] = datetime.now().isoformat()
        meta_info.update(kwargs)

        self._save_json(meta_file, meta_info)

        # 记录状态更新历史
        self._save_history(
            project_path,
            "status_updated",
            {"status": status, "step": step, **kwargs}
        )

    def save_processing_result(self, project_path: str, process_type: str, data: Dict[str, Any]):
        """
        保存处理结果

        Args:
            project_path: 项目路径
            process_type: 处理类型 (text_analysis, script_generation, etc.)
            data: 处理结果数据
        """
        project_dir = Path(project_path)
        processing_dir = project_dir / "processing"

        # 保存处理结果
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        result_file = processing_dir / f"{process_type}_{timestamp}.json"
        self._save_json(result_file, data)

        # 记录处理历史
        self._save_history(
            project_path,
            f"{process_type}_completed",
            {"result_file": result_file.name, "data_keys": list(data.keys())}
        )

        logger.info(f"处理结果已保存: {result_file}")
        return str(result_file)

    def save_characters(self, project_path: str, characters: List[Dict[str, Any]]):
        """
        保存角色信息

        Args:
            project_path: 项目路径
            characters: 角色信息列表
        """
        project_dir = Path(project_path)
        characters_dir = project_dir / "characters"

        # 保存角色信息文件
        characters_file = characters_dir / "characters.json"
        self._save_json(characters_file, characters)

        # 为每个角色创建目录
        for character in characters:
            if "name" in character:
                char_dir = characters_dir / character["name"]
                char_dir.mkdir(exist_ok=True)

                # 保存角色详细信息
                char_info_file = char_dir / "info.json"
                self._save_json(char_info_file, character)

        # 记录历史
        self._save_history(
            project_path,
            "characters_saved",
            {"count": len(characters), "names": [c.get("name", "unknown") for c in characters]}
        )

        logger.info(f"角色信息已保存，共 {len(characters)} 个角色")

    def save_chapter_comic(self, project_path: str, chapter_id: str, comic_data: Dict[str, Any]):
        """
        保存章节漫画

        Args:
            project_path: 项目路径
            chapter_id: 章节ID
            comic_data: 漫画数据
        """
        project_dir = Path(project_path)
        chapters_dir = project_dir / "chapters"

        # 创建章节目录
        chapter_dir = chapters_dir / chapter_id
        chapter_dir.mkdir(exist_ok=True)

        # 保存漫画脚本
        if "script" in comic_data:
            script_file = chapter_dir / "script.json"
            self._save_json(script_file, comic_data["script"])

        # 保存生成的图像
        if "images" in comic_data:
            images_dir = chapter_dir / "images"
            images_dir.mkdir(exist_ok=True)

            for i, image_data in enumerate(comic_data["images"]):
                if isinstance(image_data, dict) and "image_path" in image_data:
                    # 如果是图像文件路径，复制到项目目录
                    source_path = image_data["image_path"]
                    if os.path.exists(source_path):
                        target_path = images_dir / f"panel_{i+1}.png"
                        shutil.copy2(source_path, target_path)
                        image_data["image_path"] = str(target_path)

        # 保存完整的漫画数据
        comic_file = chapter_dir / "comic.json"
        self._save_json(comic_file, comic_data)

        # 记录历史
        self._save_history(
            project_path,
            "chapter_comic_saved",
            {"chapter_id": chapter_id, "panels_count": len(comic_data.get("images", []))}
        )

        logger.info(f"章节漫画已保存: {chapter_id}")

    def list_projects(self) -> List[Dict[str, Any]]:
        """
        列出所有项目

        Returns:
            项目信息列表
        """
        projects = []

        for project_dir in self.projects_dir.iterdir():
            if project_dir.is_dir():
                try:
                    meta_file = project_dir / "meta" / "project.json"
                    if meta_file.exists():
                        project_info = self._load_json(meta_file)
                        project_info["project_path"] = str(project_dir)
                        projects.append(project_info)
                except Exception as e:
                    logger.warning(f"读取项目信息失败 {project_dir}: {e}")

        # 按创建时间排序
        projects.sort(key=lambda x: x.get("created_at", ""), reverse=True)

        return projects

    def list_chapters(self, project_identifier: str) -> List[str]:
        """
        列出项目的章节ID列表（目录名）。
        """
        project_dir = self._resolve_project_path(project_identifier)
        chapters_dir = project_dir / "chapters"
        if not chapters_dir.exists():
            return []
        chapter_ids: List[str] = []
        for d in chapters_dir.iterdir():
            if d.is_dir():
                chapter_ids.append(d.name)
        # 章节按名称排序（chapter_001, chapter_002 ...）
        try:
            chapter_ids.sort(key=lambda x: int(x.split("_")[-1]))
        except Exception:
            chapter_ids.sort()
        return chapter_ids

    def get_chapter_comic(self, project_identifier: str, chapter_id: str) -> Dict[str, Any]:
        """
        获取指定章节的漫画数据（读取 chapters/<chapter_id>/comic.json）。
        若不存在，则尝试根据脚本与图像目录生成基础结构。
        """
        project_dir = self._resolve_project_path(project_identifier)
        chapter_dir = project_dir / "chapters" / chapter_id
        if not chapter_dir.exists():
            raise FileNotFoundError(f"章节目录不存在: {chapter_dir}")
        comic_file = chapter_dir / "comic.json"
        if comic_file.exists():
            return self._load_json(comic_file)
        # 回退：拼装最简结构
        script_file = chapter_dir / "script.json"
        script: Dict[str, Any] = {}
        if script_file.exists():
            try:
                script = self._load_json(script_file)
            except Exception:
                script = {}
        images_dir = chapter_dir / "images"
        images: List[Dict[str, Any]] = []
        if images_dir.exists():
            for p in sorted(images_dir.glob("*.png")):
                images.append({"image_path": str(p)})
        return {
            "chapter_id": chapter_id,
            "script": script,
            "images": images,
            "created_at": datetime.now().isoformat()
        }

    def _save_history(self, project_path: str, history_type: str, data: Dict[str, Any]):
        """
        保存操作历史

        Args:
            project_path: 项目路径
            history_type: 历史类型
            data: 历史数据
        """
        project_dir = Path(project_path)
        processing_dir = project_dir / "processing"

        # 读取现有历史记录
        history_file = processing_dir / f"{history_type}.history"
        history = []

        if history_file.exists():
            try:
                history = self._load_json(history_file)
                if not isinstance(history, list):
                    history = []
            except Exception as e:
                logger.warning(f"读取历史记录失败 {history_file}: {e}")

        # 添加新的历史记录
        new_record = {
            "timestamp": datetime.now().isoformat(),
            "type": history_type,
            "data": data
        }
        history.append(new_record)

        # 保存历史记录
        self._save_json(history_file, history)

    def _save_json(self, file_path: Path, data: Dict[str, Any]):
        """
        保存JSON数据到文件

        Args:
            file_path: 文件路径
            data: 要保存的数据
        """
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def delete_project_directory(self, project_path: str) -> bool:
        """
        删除指定项目目录

        Args:
            project_path: 项目目录路径

        Returns:
            删除是否成功
        """
        try:
            project_dir = Path(project_path)

            # 安全检查：确保是项目目录，而不是误删其他目录
            if not project_dir.exists():
                logger.warning(f"项目目录不存在: {project_dir}")
                return True  # 不存在的目录认为删除成功

            # 确保要删除的是项目目录（包含meta/project.json）
            meta_file = project_dir / "meta" / "project.json"
            if not meta_file.exists():
                logger.error(f"不是有效的项目目录，缺少meta/project.json: {project_dir}")
                return False

            # 额外安全检查：确保我们不在projects根目录下操作
            try:
                # 检查project_dir是否在projects_dir下
                project_dir.resolve().relative_to(self.projects_dir.resolve())
            except ValueError:
                logger.error(f"项目目录不在projects下，拒绝删除: {project_dir}")
                return False

            logger.info(f"正在删除项目目录: {project_dir}")
            shutil.rmtree(project_dir)
            logger.info(f"项目目录删除成功: {project_dir}")
            return True

        except Exception as e:
            logger.error(f"删除项目目录失败 {project_path}: {e}")
            return False

    def _load_json(self, file_path: Path) -> Dict[str, Any]:
        """
        从文件加载JSON数据

        Args:
            file_path: 文件路径

        Returns:
            加载的数据
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _save_json(self, file_path: Path, data: Dict[str, Any]) -> None:
        """
        保存数据到JSON文件

        Args:
            file_path: 文件路径
            data: 要保存的数据
        """
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def get_chapters_info(self, project_identifier: str) -> List[ChapterInfo]:
        """
        获取项目章节信息列表, 结合新旧两种结构的数据
        """
        logger.info(f"开始获取项目 {project_identifier} 的章节信息")
        
        # 1. 首先尝试使用新的章节结构获取信息
        chapters_from_structure = []
        try:
            project_structure = self.get_project_chapters_structure(project_identifier)
            chapters_from_structure = project_structure.chapters
            logger.info(f"通过新结构获取到 {len(chapters_from_structure)} 个章节")
        except Exception as e:
            logger.warning(f"使用新章节结构获取章节信息失败: {e}")

        # 2. 兼容旧版，扫描目录获取基本信息
        project_dir = self._resolve_project_path(project_identifier)
        chapters_dir = project_dir / "chapters"

        if not chapters_dir.exists():
            logger.info(f"项目 {project_identifier} 不存在章节目录")
            return chapters_from_structure

        chapters_info: List[ChapterInfo] = []
        processed_chapter_ids = set(c.chapter_id for c in chapters_from_structure)
        logger.info(f"开始扫描目录 (兼容模式)，已处理的章节ID: {processed_chapter_ids}")

        for chapter_dir in chapters_dir.iterdir():
            if not chapter_dir.is_dir() or chapter_dir.name in processed_chapter_ids:
                continue

            chapter_id = chapter_dir.name
            logger.info(f"兼容模式：处理章节目录 {chapter_id}")

            try:
                # 使用 get_chapter_detail 获取最完整的信息
                detail = self.get_chapter_detail(project_identifier, chapter_id)
                
                chapters_info.append(ChapterInfo(
                    chapter_id=chapter_id,
                    title=detail.title,
                    created_at=detail.created_at,
                    updated_at=detail.updated_at,
                    status=detail.status,
                    total_panels=detail.total_panels,
                    confirmed_panels=detail.confirmed_panels,
                    unconfirmed_panels=detail.unconfirmed_panels,
                    chapter_number=detail.chapter_number,
                    completion_percentage= (detail.confirmed_panels / detail.total_panels * 100) if detail.total_panels > 0 else 0,
                    has_unconfirmed_panels=detail.unconfirmed_panels > 0
                ))
                logger.info(f"兼容模式：成功添加章节 {chapter_id}")

            except Exception as e:
                logger.warning(f"兼容模式：处理章节 {chapter_id} 失败: {e}")

        # 合并并去重
        final_chapters_map = {c.chapter_id: c for c in chapters_from_structure}
        for c in chapters_info:
            if c.chapter_id not in final_chapters_map:
                final_chapters_map[c.chapter_id] = c
        
        final_chapters = list(final_chapters_map.values())
        final_chapters.sort(key=lambda x: x.chapter_number)
        logger.info(f"章节信息获取完成，共 {len(final_chapters)} 个章节")
        return final_chapters

    def _get_chapter_cover_path(self, project_identifier: str, chapter_id: str) -> Optional[Path]:
        """
        获取章节封面图片路径

        Args:
            project_identifier: 项目标识符
            chapter_id: 章节ID

        Returns:
            章节封面图片路径，如果不存在则返回None
        """
        try:
            project_dir = self._resolve_project_path(project_identifier)
            chapter_dir = project_dir / "chapters" / chapter_id

            if not chapter_dir.exists():
                return None

            # 查找封面图片（优先查找cover.jpg/png，然后查找第一张图片）
            cover_patterns = ["cover.jpg", "cover.png", "cover.jpeg", "cover.webp"]

            for pattern in cover_patterns:
                cover_path = chapter_dir / pattern
                if cover_path.exists() and cover_path.is_file():
                    return cover_path

            # 如果没有找到专门的封面图片，查找images目录中的第一张图片
            images_dir = chapter_dir / "images"
            if images_dir.exists() and images_dir.is_dir():
                image_files = []
                for ext in ["*.jpg", "*.jpeg", "*.png", "*.webp"]:
                    image_files.extend(images_dir.glob(ext))
                image_files.sort()  # 按名称排序

                if image_files:
                    return image_files[0]

        except Exception as e:
            logger.warning(f"获取章节 {chapter_id} 封面路径失败: {e}")

        return None

    def get_chapter_detail(self, project_identifier: str, chapter_id: str) -> ChapterDetail:
        """
        获取章节详细信息, 结合新旧两种结构
        """
        logger.info(f"开始获取章节 {chapter_id} 的详细信息")
        try:
            # 1. 优先使用新结构
            return self.get_story_chapter_detail(project_identifier, chapter_id)
        except Exception as e:
            logger.warning(f"使用新结构获取章节详情失败: {e}，回退到兼容模式")

            # 2. 兼容旧版
            project_dir = self._resolve_project_path(project_identifier)
            chapter_dir = project_dir / "chapters" / chapter_id

            if not chapter_dir.exists():
                raise FileNotFoundError(f"章节目录不存在: {chapter_dir}")

            created_at = datetime.fromtimestamp(chapter_dir.stat().st_ctime).isoformat()
            updated_at = datetime.fromtimestamp(chapter_dir.stat().st_mtime).isoformat()
            
            try:
                chapter_number = int(chapter_id.split("_")[-1])
            except (ValueError, IndexError):
                chapter_number = 1
            title = f"第{chapter_number}章"

            # 从 comic.json 和 images 目录读取
            comic_file = chapter_dir / "comic.json"
            images_dir = chapter_dir / "images"
            
            script = None
            panels = []
            
            if comic_file.exists():
                try:
                    comic_data = self._load_json(comic_file)
                    script = comic_data.get("script")
                    for panel_data in comic_data.get("images", []):
                        panels.append(ComicPanel(**panel_data))
                except Exception as e:
                    logger.error(f"读取 comic.json 失败: {e}")

            if not panels and images_dir.exists():
                for idx, image_file in enumerate(sorted(images_dir.glob("*.png"))):
                    panel_id = idx + 1
                    try:
                        panel_id = int(image_file.stem.split('_')[2])
                    except (ValueError, IndexError):
                        pass
                    
                    panels.append(ComicPanel(
                        panel_id=panel_id,
                        image_path=f"/projects/{project_identifier}/chapters/{chapter_id}/images/{image_file.name}",
                        confirmed=False,
                        generated_at=datetime.fromtimestamp(image_file.stat().st_ctime).isoformat()
                    ))

            total_panels = len(panels)
            confirmed_panels = sum(1 for p in panels if p.confirmed)
            
            status = "pending"
            if total_panels > 0:
                status = "completed" if confirmed_panels == total_panels else "in_progress"

            return ChapterDetail(
                chapter_id=chapter_id,
                title=title,
                created_at=created_at,
                updated_at=updated_at,
                status=status,
                script=script,
                panels=panels,
                total_panels=total_panels,
                confirmed_panels=confirmed_panels,
                unconfirmed_panels=total_panels - confirmed_panels,
                chapter_number=chapter_number
            )

    def delete_chapter_panel(self, project_identifier: str, chapter_id: str, panel_id: int) -> None:
        """
        删除章节中的特定画面

        Args:
            project_identifier: 项目标识符
            chapter_id: 章节ID
            panel_id: 画面ID
        """
        project_dir = self._resolve_project_path(project_identifier)
        chapter_dir = project_dir / "chapters" / chapter_id
        images_dir = chapter_dir / "images"

        if not images_dir.exists():
            raise FileNotFoundError(f"图像目录不存在: {images_dir}")

        # 查找并删除对应的图像文件
        deleted = False
        for image_file in images_dir.iterdir():
            if image_file.is_file() and image_file.suffix.lower() in ['.png', '.jpg', '.jpeg']:
                try:
                    # 从文件名解析panel_id
                    filename_parts = image_file.stem.split('_')
                    file_panel_id = int(filename_parts[2]) if len(filename_parts) >= 3 else 0

                    if file_panel_id == panel_id:
                        image_file.unlink()
                        deleted = True
                        logger.info(f"删除画面文件: {image_file}")
                        break
                except (ValueError, IndexError):
                    continue

        if not deleted:
            raise FileNotFoundError(f"未找到panel_id为 {panel_id} 的画面文件")

        # 更新comic.json（如果存在）
        comic_file = chapter_dir / "comic.json"
        if comic_file.exists():
            try:
                comic_data = self._load_json(comic_file)
                if "images" in comic_data:
                    # 从images列表中移除对应的画面
                    comic_data["images"] = [
                        img for img in comic_data["images"]
                        if img.get("panel_id") != panel_id
                    ]
                    self._save_json(comic_file, comic_data)
                    logger.info(f"更新comic.json，移除panel_id {panel_id}")
            except Exception as e:
                logger.error(f"更新comic.json失败: {e}")

    def update_panel_confirmation(self, project_identifier: str, chapter_id: str, panel_id: int, confirmed: bool) -> None:
        """
        更新画面确认状态

        Args:
            project_identifier: 项目标识符
            chapter_id: 章节ID
            panel_id: 画面ID
            confirmed: 确认状态
        """
        project_dir = self._resolve_project_path(project_identifier)
        chapter_dir = project_dir / "chapters" / chapter_id

        # 优先更新新的 panels.json 文件
        panels_file = chapter_dir / "panels.json"
        chapter_info_file = chapter_dir / "chapter_info.json"

        updated_panels = False
        updated_chapter_info = False

        # 更新 panels.json
        if panels_file.exists():
            try:
                panels_data = self._load_json(panels_file)
                panels = panels_data.get("panels", [])

                # 查找并更新对应panel的确认状态
                for panel in panels:
                    if panel.get("panel_id") == panel_id:
                        panel["confirmed"] = confirmed
                        panel["updated_at"] = datetime.now().isoformat()
                        updated_panels = True
                        break

                # 保存更新后的panels数据
                self._save_json(panels_file, panels_data)
                logger.info(f"更新 panels.json 中画面 {panel_id} 确认状态为: {confirmed}")

            except Exception as e:
                logger.error(f"更新 panels.json 失败: {e}")

        # 更新 chapter_info.json 中的统计信息
        if chapter_info_file.exists():
            try:
                chapter_info = self._load_json(chapter_info_file)

                # 重新计算统计信息
                if panels_file.exists():
                    panels_data = self._load_json(panels_file)
                    panels = panels_data.get("panels", [])
                    total_panels = len(panels)
                    confirmed_panels = sum(1 for p in panels if p.get("confirmed", False))
                    unconfirmed_panels = total_panels - confirmed_panels

                    chapter_info["total_panels"] = total_panels
                    chapter_info["confirmed_panels"] = confirmed_panels
                    chapter_info["unconfirmed_panels"] = unconfirmed_panels
                    chapter_info["updated_at"] = datetime.now().isoformat()

                    # 如果有panel被确认，更新状态
                    if confirmed_panels > 0 and chapter_info.get("status") == "created":
                        chapter_info["status"] = "completed"

                    self._save_json(chapter_info_file, chapter_info)
                    updated_chapter_info = True
                    logger.info(f"更新 chapter_info.json 统计信息: 总计{total_panels}, 已确认{confirmed_panels}")

            except Exception as e:
                logger.error(f"更新 chapter_info.json 失败: {e}")

        # 兼容性：仍然更新旧的 comic.json 文件（如果存在）
        comic_file = chapter_dir / "comic.json"
        if comic_file.exists():
            try:
                comic_data = self._load_json(comic_file)

                # 确保images字段存在
                if "images" not in comic_data:
                    comic_data["images"] = []

                # 查找并更新对应画面的确认状态
                found = False
                for image in comic_data["images"]:
                    if image.get("panel_id") == panel_id:
                        image["confirmed"] = confirmed
                        image["updated_at"] = datetime.now().isoformat()
                        found = True
                        break

                # 如果没有找到对应的面板，添加一个新的
                if not found:
                    comic_data["images"].append({
                        "panel_id": panel_id,
                        "confirmed": confirmed,
                        "updated_at": datetime.now().isoformat()
                    })

                # 保存更新后的数据
                self._save_json(comic_file, comic_data)
                logger.info(f"兼容性更新 comic.json 中画面 {panel_id} 确认状态为: {confirmed}")

            except Exception as e:
                logger.error(f"更新 comic.json 失败: {e}")

        # 如果没有找到任何文件进行更新，记录警告
        if not updated_panels and not updated_chapter_info and not comic_file.exists():
            logger.warning(f"章节 {chapter_id} 没有找到任何数据文件进行更新")

        logger.info(f"完成画面 {panel_id} 确认状态更新为: {confirmed}")

    def batch_update_panel_confirmation(self, project_identifier: str, chapter_id: str, panel_ids: List[int], confirmed: bool) -> None:
        """
        批量更新画面确认状态

        Args:
            project_identifier: 项目标识符
            chapter_id: 章节ID
            panel_ids: 画面ID列表
            confirmed: 确认状态
        """
        project_dir = self._resolve_project_path(project_identifier)
        chapter_dir = project_dir / "chapters" / chapter_id

        # 优先批量更新新的 panels.json 文件
        panels_file = chapter_dir / "panels.json"
        chapter_info_file = chapter_dir / "chapter_info.json"

        updated_panels_count = 0

        # 批量更新 panels.json
        if panels_file.exists():
            try:
                panels_data = self._load_json(panels_file)
                panels = panels_data.get("panels", [])

                # 批量更新对应panels的确认状态
                for panel in panels:
                    if panel.get("panel_id") in panel_ids:
                        panel["confirmed"] = confirmed
                        panel["updated_at"] = datetime.now().isoformat()
                        updated_panels_count += 1

                # 保存更新后的panels数据
                self._save_json(panels_file, panels_data)
                logger.info(f"批量更新 panels.json 中 {updated_panels_count} 个画面确认状态为: {confirmed}")

            except Exception as e:
                logger.error(f"批量更新 panels.json 失败: {e}")

        # 更新 chapter_info.json 中的统计信息
        if chapter_info_file.exists():
            try:
                chapter_info = self._load_json(chapter_info_file)

                # 重新计算统计信息
                if panels_file.exists():
                    panels_data = self._load_json(panels_file)
                    panels = panels_data.get("panels", [])
                    total_panels = len(panels)
                    confirmed_panels = sum(1 for p in panels if p.get("confirmed", False))
                    unconfirmed_panels = total_panels - confirmed_panels

                    chapter_info["total_panels"] = total_panels
                    chapter_info["confirmed_panels"] = confirmed_panels
                    chapter_info["unconfirmed_panels"] = unconfirmed_panels
                    chapter_info["updated_at"] = datetime.now().isoformat()

                    # 根据确认状态更新章节状态
                    if confirmed_panels == total_panels and total_panels > 0:
                        chapter_info["status"] = "completed"
                    elif confirmed_panels > 0:
                        chapter_info["status"] = "in_progress"
                    else:
                        chapter_info["status"] = "created"

                    self._save_json(chapter_info_file, chapter_info)
                    logger.info(f"更新 chapter_info.json 统计信息: 总计{total_panels}, 已确认{confirmed_panels}")

            except Exception as e:
                logger.error(f"更新 chapter_info.json 失败: {e}")

        # 兼容性：仍然批量更新旧的 comic.json 文件（如果存在）
        comic_file = chapter_dir / "comic.json"
        if comic_file.exists():
            try:
                comic_data = self._load_json(comic_file)

                # 确保images字段存在
                if "images" not in comic_data:
                    comic_data["images"] = []

                # 批量更新对应images的确认状态
                for image in comic_data["images"]:
                    if image.get("panel_id") in panel_ids:
                        image["confirmed"] = confirmed
                        image["updated_at"] = datetime.now().isoformat()

                # 保存更新后的数据
                self._save_json(comic_file, comic_data)
                logger.info(f"兼容性批量更新 comic.json 中 {len(panel_ids)} 个画面确认状态为: {confirmed}")

            except Exception as e:
                logger.error(f"批量更新 comic.json 失败: {e}")

        logger.info(f"完成批量更新 {len(panel_ids)} 个画面确认状态为: {confirmed}，实际更新 {updated_panels_count} 个")

    def export_chapter(self, project_identifier: str, chapter_id: str, export_format: str = "pdf",
                      include_confirmed_only: bool = False, resolution: str = "high", quality: str = "standard") -> Dict[str, Any]:
        """
        导出章节

        Args:
            project_identifier: 项目标识符
            chapter_id: 章节ID
            export_format: 导出格式
            include_confirmed_only: 是否只导出已确认的画面
            resolution: 分辨率
            quality: 质量

        Returns:
            导出结果信息
        """
        project_dir = self._resolve_project_path(project_identifier)
        chapter_dir = project_dir / "chapters" / chapter_id
        output_dir = project_dir / "output"
        output_dir.mkdir(exist_ok=True)

        # 获取章节详情
        chapter_detail = self.get_chapter_detail(project_identifier, chapter_id)

        # 筛选要导出的图像
        images_to_export = chapter_detail.images or []
        if include_confirmed_only:
            images_to_export = [img for img in images_to_export if img.confirmed]

        if not images_to_export:
            raise ValueError("没有可导出的画面")

        # 生成导出文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if export_format == "pdf":
            filename = f"chapter_{chapter_id}_{timestamp}.pdf"
            file_path = output_dir / filename

            # TODO: 实现PDF导出逻辑
            # 这里应该调用PDF生成库将图像合并为PDF
            # 暂时创建一个占位文件
            with open(file_path, 'w') as f:
                f.write(f"PDF导出占位文件 - 章节 {chapter_id}")

            file_size = file_path.stat().st_size
            download_url = f"/projects/{project_identifier}/output/{filename}"

        elif export_format == "images":
            # 创建图像压缩包
            import zipfile
            filename = f"chapter_{chapter_id}_images_{timestamp}.zip"
            file_path = output_dir / filename

            with zipfile.ZipFile(file_path, 'w') as zip_file:
                for i, image in enumerate(images_to_export):
                    # 将图像路径转换为本地文件路径
                    local_image_path = project_dir / image.image_path.replace(f"/projects/{project_identifier}/", "")
                    if local_image_path.exists():
                        zip_file.write(local_image_path, f"panel_{i+1:03d}{local_image_path.suffix}")

            file_size = file_path.stat().st_size
            download_url = f"/projects/{project_identifier}/output/{filename}"

        else:
            raise ValueError(f"不支持的导出格式: {export_format}")

        return {
            "download_url": download_url,
            "file_size": file_size,
            "exported_images": len(images_to_export),
            "format": export_format
        }

    # ==================== 新的章节结构管理方法 ====================

    def create_story_chapter(self, project_identifier: str, chapter_number: int,
                           story_text: str, title: str = None) -> str:
        """
        创建新的故事章节（包含多个分镜画面）

        Args:
            project_identifier: 项目标识符
            chapter_number: 章节编号
            story_text: 故事文本
            title: 章节标题

        Returns:
            章节ID
        """
        project_dir = self._resolve_project_path(project_identifier)
        chapters_dir = project_dir / "chapters"

        # 创建章节目录
        chapter_id = f"chapter_{chapter_number:03d}"
        chapter_dir = chapters_dir / chapter_id
        chapter_dir.mkdir(parents=True, exist_ok=True)

        # 创建子目录结构
        (chapter_dir / "images").mkdir(exist_ok=True)
        (chapter_dir / "panels").mkdir(exist_ok=True)

        # 保存章节信息
        chapter_info = {
            "chapter_id": chapter_id,
            "chapter_number": chapter_number,
            "title": title or f"第{chapter_number}章",
            "story_text": story_text,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "status": "created"
        }

        self._save_json(chapter_dir / "chapter_info.json", chapter_info)

        # 记录历史
        self._save_history(
            str(project_dir),
            "chapter_created",
            {
                "chapter_id": chapter_id,
                "chapter_number": chapter_number,
                "title": chapter_info["title"]
            }
        )

        logger.info(f"创建故事章节: {chapter_id} - {chapter_info['title']}")
        return chapter_id

    def save_chapter_panels(self, project_identifier: str, chapter_id: str,
                           panels: List[ComicPanel]) -> None:
        """
        保存章节的分镜画面信息

        Args:
            project_identifier: 项目标识符
            chapter_id: 章节ID
            panels: 分镜画面列表
        """
        project_dir = self._resolve_project_path(project_identifier)
        chapter_dir = project_dir / "chapters" / chapter_id

        if not chapter_dir.exists():
            raise FileNotFoundError(f"章节目录不存在: {chapter_dir}")

        # 保存panels信息
        panels_data = []
        for panel in panels:
            panel_dict = panel.dict()
            panels_data.append(panel_dict)

        # 保存到panels.json
        panels_file = chapter_dir / "panels.json"
        self._save_json(panels_file, {"panels": panels_data})

        # 更新章节信息
        chapter_info_file = chapter_dir / "chapter_info.json"
        if chapter_info_file.exists():
            chapter_info = self._load_json(chapter_info_file)
            chapter_info["updated_at"] = datetime.now().isoformat()
            chapter_info["total_panels"] = len(panels)
            chapter_info["confirmed_panels"] = sum(1 for p in panels if p.confirmed)
            chapter_info["unconfirmed_panels"] = len(panels) - chapter_info["confirmed_panels"]
            chapter_info["status"] = "completed" if panels else "created"

            self._save_json(chapter_info_file, chapter_info)

        logger.info(f"保存章节 {chapter_id} 的 {len(panels)} 个分镜画面")

    def get_project_chapters_structure(self, project_identifier: str) -> ProjectChaptersInfo:
        """
        获取项目的完整章节结构信息

        Args:
            project_identifier: 项目标识符

        Returns:
            项目章节信息
        """
        project_dir = self._resolve_project_path(project_identifier)
        chapters_dir = project_dir / "chapters"

        if not chapters_dir.exists():
            return ProjectChaptersInfo(
                project_id=project_identifier,
                total_chapters=0,
                chapters=[],
                total_panels=0,
                total_confirmed_panels=0
            )

        chapters_info = []
        total_panels = 0
        total_confirmed_panels = 0
        completed_chapters = 0
        generating_chapters = 0
        pending_chapters = 0

        # 扫描章节目录
        logger.info(f"扫描章节目录: {chapters_dir}")
        for chapter_dir in chapters_dir.iterdir():
            if not chapter_dir.is_dir() or not chapter_dir.name.startswith("chapter_"):
                continue

            chapter_id = chapter_dir.name
            try:
                chapter_info_file = chapter_dir / "chapter_info.json"
                if chapter_info_file.exists():
                    with open(chapter_info_file, 'r', encoding='utf-8') as f:
                        chapter_data = json.load(f)
                    
                    total_p = chapter_data.get("total_panels", 0)
                    confirmed_p = chapter_data.get("confirmed_panels", 0)
                    
                    chapter_info = ChapterInfo(
                        chapter_id=chapter_id,
                        title=chapter_data.get("title", f"第{chapter_data.get('chapter_number', 1)}章"),
                        created_at=chapter_data.get("created_at"),
                        updated_at=chapter_data.get("updated_at"),
                        status=chapter_data.get("status", "unknown"),
                        total_panels=total_p,
                        confirmed_panels=confirmed_p,
                        unconfirmed_panels=total_p - confirmed_p,
                        chapter_number=chapter_data.get("chapter_number", 1),
                        completion_percentage=(confirmed_p / total_p * 100) if total_p > 0 else 0,
                        has_unconfirmed_panels=(total_p - confirmed_p) > 0
                    )
                    chapters_info.append(chapter_info)
                    
                    total_panels += total_p
                    total_confirmed_panels += confirmed_p
                    if chapter_info.status == "completed": completed_chapters += 1
                    elif chapter_info.status in ["generating", "processing"]: generating_chapters += 1
                    else: pending_chapters += 1
                else:
                    # Fallback for directories without chapter_info.json
                    logger.warning(f"章节 {chapter_id} 缺少 chapter_info.json, 使用回退信息")
                    detail = self.get_chapter_detail(project_identifier, chapter_id)
                    chapters_info.append(ChapterInfo(
                        chapter_id=chapter_id,
                        title=detail.title,
                        created_at=detail.created_at,
                        updated_at=detail.updated_at,
                        status=detail.status,
                        total_panels=detail.total_panels,
                        confirmed_panels=detail.confirmed_panels,
                        unconfirmed_panels=detail.unconfirmed_panels,
                        chapter_number=detail.chapter_number
                    ))
            except Exception as e:
                logger.error(f"处理章节 {chapter_id} 失败: {e}")

        # 按章节编号排序
        chapters_info.sort(key=lambda x: x.chapter_number)

        return ProjectChaptersInfo(
            project_id=project_identifier,
            total_chapters=len(chapters_info),
            chapters=chapters_info,
            total_panels=total_panels,
            total_confirmed_panels=total_confirmed_panels,
            completed_chapters=completed_chapters,
            generating_chapters=generating_chapters,
            pending_chapters=pending_chapters
        )

    def get_story_chapter_detail(self, project_identifier: str, chapter_id: str) -> ChapterDetail:
        """
        获取故事章节的详细信息（包含所有分镜画面）

        Args:
            project_identifier: 项目标识符
            chapter_id: 章节ID

        Returns:
            章节详细信息
        """
        project_dir = self._resolve_project_path(project_identifier)
        chapter_dir = project_dir / "chapters" / chapter_id

        if not chapter_dir.exists():
            raise FileNotFoundError(f"章节目录不存在: {chapter_dir}")

        # 获取基本信息
        created_at = datetime.fromtimestamp(chapter_dir.stat().st_ctime).isoformat()
        updated_at = datetime.fromtimestamp(chapter_dir.stat().st_mtime).isoformat()

        # 读取章节信息
        chapter_info_file = chapter_dir / "chapter_info.json"
        story_text = None
        title = None
        status = "created"

        # 首先从chapter_id解析章节编号
        try:
            chapter_number = int(chapter_id.split("_")[-1])
        except (ValueError, IndexError):
            logger.warning(f"无法从章节ID {chapter_id} 解析章节编号，使用默认值1")
            chapter_number = 1

        if chapter_info_file.exists():
            try:
                chapter_data = self._load_json(chapter_info_file)
                story_text = chapter_data.get("story_text")
                title = chapter_data.get("title")
                status = chapter_data.get("status", "created")
                # 如果chapter_info.json中有chapter_number，优先使用；否则保持从ID解析的值
                if "chapter_number" in chapter_data:
                    chapter_number = chapter_data["chapter_number"]
                created_at = chapter_data.get("created_at", created_at)
                updated_at = chapter_data.get("updated_at", updated_at)
            except Exception as e:
                logger.error(f"读取章节信息失败: {e}")

        # 读取分镜画面信息
        panels = []
        panels_file = chapter_dir / "panels.json"
        if panels_file.exists():
            try:
                panels_data = self._load_json(panels_file)
                for panel_data in panels_data.get("panels", []):
                    panels.append(ComicPanel(**panel_data))
            except Exception as e:
                logger.error(f"读取分镜画面信息失败: {e}")

        # 如果没有panels信息，尝试从图像文件推断（兼容旧结构）
        if not panels:
            images_dir = chapter_dir / "images"
            if images_dir.exists():
                logger.warning(f"缺少 panels.json，从 images 目录回退")
                # 处理新的分段目录结构: segment_XX/scene_option_1_xxx.png
                segment_dirs = sorted([d for d in images_dir.iterdir() if d.is_dir() and d.name.startswith("segment_")])

                panel_id = 1
                for segment_dir in segment_dirs:
                    # 在每个分段目录中查找图片
                    for image_file in sorted(segment_dir.glob("*.png")):
                        # 从文件名解析信息
                        filename_parts = image_file.stem.split('_')
                        description = f"分段 {segment_dir.name.replace('segment_', '')} - 画面 {panel_id}"

                        panels.append(ComicPanel(
                            panel_id=panel_id,
                            description=description,
                            image_path=f"/projects/{project_identifier}/chapters/{chapter_id}/images/{segment_dir.name}/{image_file.name}",
                            confirmed=False,
                            generated_at=datetime.fromtimestamp(image_file.stat().st_ctime).isoformat(),
                            paragraph_id=segment_dir.name.replace('segment_', '')
                        ))
                        panel_id += 1

                # 如果没有找到分段目录中的图片，尝试在images目录直接查找（兼容旧结构）
                if not panels:
                    for image_file in sorted(images_dir.glob("*.png")):
                        try:
                            panel_id = int(image_file.stem.split('_')[2])
                        except (ValueError, IndexError):
                            panel_id = 0 # or some default

                        panels.append(ComicPanel(
                            panel_id=panel_id,
                            description=f"画面 {panel_id}",
                            image_path=f"/projects/{project_identifier}/chapters/{chapter_id}/images/{image_file.name}",
                            confirmed=False,
                            generated_at=datetime.fromtimestamp(image_file.stat().st_ctime).isoformat()
                        ))

        # 生成段落分组信息
        paragraphs = self._generate_paragraph_groups(panels, story_text)

        # 计算统计信息
        total_panels = len(panels)
        confirmed_panels = sum(1 for p in panels if p.confirmed)
        unconfirmed_panels = total_panels - confirmed_panels

        # 如果没有分镜画面，状态设为pending
        if not panels and status == "created":
            status = "pending"

        return ChapterDetail(
            chapter_id=chapter_id,
            title=title,
            created_at=created_at,
            updated_at=updated_at,
            status=status,
            story_text=story_text,
            panels=panels,
            paragraphs=paragraphs,  # 新增字段：段落分组数据
            total_panels=total_panels,
            confirmed_panels=confirmed_panels,
            unconfirmed_panels=unconfirmed_panels,
            chapter_number=chapter_number
        )

    def _generate_paragraph_groups(self, panels: List[ComicPanel], story_text: Optional[str] = None) -> List[ParagraphInfo]:
        """
        生成段落分组信息
        Args:
            panels: 分镜画面列表
            story_text: 原始故事文本（可选）
        Returns:
            段落分组信息列表
        """
        if not panels:
            return []

        # 直接基于分镜图的paragraph_id进行分组
        panel_paragraph_map = {}
        for panel in panels:
            paragraph_id = panel.paragraph_id
            if paragraph_id:
                if paragraph_id not in panel_paragraph_map:
                    panel_paragraph_map[paragraph_id] = []
                panel_paragraph_map[paragraph_id].append(panel)

        # 为每个段落组生成段落信息对象
        paragraph_infos = []
        for paragraph_id, panel_list in panel_paragraph_map.items():
            if not panel_list:
                continue

            # 提取段落序号（从segment_XX中提取）
            paragraph_index = 1
            try:
                if paragraph_id.startswith("segment_"):
                    # 直接使用字符串中的数字部分，保持原有的顺序
                    paragraph_index = int(paragraph_id.split("_")[1])
                elif paragraph_id.startswith("paragraph_"):
                    paragraph_index = int(paragraph_id.split("_")[1])
                elif paragraph_id.isdigit():
                    paragraph_index = int(paragraph_id)
            except (ValueError, IndexError):
                paragraph_index = 1

            # 生成段落内容 - 使用分镜图的描述
            if len(panel_list) > 0:
                descriptions = []
                for panel in panel_list:
                    if panel.description:
                        descriptions.append(panel.description)
                    elif panel.scene_description:
                        descriptions.append(panel.scene_description)

                content = " ".join(descriptions) if descriptions else f"段落 {paragraph_index}"
            else:
                content = f"段落 {paragraph_index}"

            confirmed_count = sum(1 for p in panel_list if p.confirmed)

            # 确保每个分镜图的paragraph_index正确
            for panel in panel_list:
                panel.paragraph_index = paragraph_index

            paragraph_info = ParagraphInfo(
                paragraph_id=paragraph_id,
                paragraph_index=paragraph_index,
                content=content,
                panels=panel_list,  # 这里应该是分镜图列表，不是空的
                panel_count=len(panel_list),
                confirmed_count=confirmed_count
            )
            paragraph_infos.append(paragraph_info)

        # 按段落序号排序
        paragraph_infos.sort(key=lambda x: x.paragraph_index)

        # 处理未分配段落的分镜图
        unassigned_panels = [p for p in panels if not p.paragraph_id]
        if unassigned_panels:
            paragraph_info = ParagraphInfo(
                paragraph_id="unassigned",
                paragraph_index=999,
                content="未分组分镜图",
                panels=unassigned_panels,
                panel_count=len(unassigned_panels),
                confirmed_count=sum(1 for p in unassigned_panels if p.confirmed)
            )
            paragraph_infos.append(paragraph_info)

        return paragraph_infos

    def _split_text_to_paragraphs(self, text: str) -> List[str]:
        """
        将文本分割为段落
        Args:
            text: 原始文本
        Returns:
            段落列表
        """
        if not text:
            return []

        # 按空行分割段落
        paragraphs = []
        current_paragraph = ""

        for line in text.split('\n'):
            line = line.strip()
            if line:
                if current_paragraph:
                    current_paragraph += " " + line
                else:
                    current_paragraph = line
            elif current_paragraph:
                paragraphs.append(current_paragraph)
                current_paragraph = ""

        if current_paragraph:
            paragraphs.append(current_paragraph)

        return paragraphs

    def _extract_paragraphs_from_panels(self, panels: List[ComicPanel]) -> List[str]:
        """
        从分镜画面描述中提取段落信息
        Args:
            panels: 分镜画面列表
        Returns:
            段落列表
        """
        # 简单实现：每6个分镜图作为一个段落
        paragraph_texts = []
        for i in range(0, len(panels), 6):
            paragraph_panels = panels[i:i + 6]
            if paragraph_panels:
                # 合并这个段落的描述
                descriptions = [p.description or p.scene_description for p in paragraph_panels]
                paragraph_text = " ".join(desc for desc in descriptions if desc)
                paragraph_texts.append(paragraph_text)

        return paragraph_texts

    def _find_best_paragraph_for_panel(self, panel: ComicPanel, paragraphs: List[str]) -> Optional[str]:
        """
        为分镜图找到最匹配的段落
        Args:
            panel: 分镜画面
            paragraphs: 段落列表
        Returns:
            最佳匹配的段落ID
        """
        panel_text = f"{panel.description} {panel.scene_description}".lower()

        best_match_index = -1
        best_match_score = 0

        for i, paragraph in enumerate(paragraphs):
            paragraph_lower = paragraph.lower()
            # 简单的文本匹配算法
            match_score = self._calculate_text_similarity(panel_text, paragraph_lower)

            if match_score > best_match_score:
                best_match_score = match_score
                best_match_index = i

        if best_match_index >= 0 and best_match_score > 0.3:  # 匹配度阈值
            return f"paragraph_{best_match_index + 1:03d}"

        return None

    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """
        计算两个文本的相似度（简单的词汇重叠算法）
        Args:
            text1: 文本1
            text2: 文本2
        Returns:
            相似度分数 (0-1)
        """
        words1 = set(text1.split())
        words2 = set(text2.split())

        if not words1 or not words2:
            return 0.0

        intersection = words1.intersection(words2)
        union = words1.union(words2)

        return len(intersection) / len(union) if union else 0.0
