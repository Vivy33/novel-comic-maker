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
    from ..config import settings
except Exception:
    from backend.config import settings

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

    def create_project(self, project_name: str, novel_text: str = "") -> str:
        """
        创建新项目目录结构

        Args:
            project_name: 项目名称
            novel_text: 原始小说文本

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