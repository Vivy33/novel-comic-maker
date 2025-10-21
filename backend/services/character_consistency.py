"""
角色一致性管理系统
Character Consistency Management System

负责管理角色参考图、一致性匹配和角色特征维护
Responsible for managing character reference images, consistency matching, and character feature maintenance
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import hashlib
import shutil
from dataclasses import dataclass, asdict
import re

logger = logging.getLogger(__name__)


@dataclass
class CharacterProfile:
    """角色档案数据结构"""
    name: str
    description: str
    personality_traits: List[str]
    appearance_features: Dict[str, Any]
    reference_images: List[str]
    consistency_tags: List[str]
    first_appearance: str
    importance_level: str  # main, secondary, minor
    relationships: Dict[str, str]
    last_updated: str

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CharacterProfile':
        """从字典创建实例"""
        return cls(**data)


@dataclass
class ConsistencyMatch:
    """一致性匹配结果"""
    character_name: str
    match_score: float
    matched_features: List[str]
    mismatched_features: List[str]
    confidence: float
    reference_image_used: str
    match_time: str

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return asdict(self)


class CharacterConsistencyManager:
    """角色一致性管理器"""

    def __init__(self, projects_dir: str = "projects"):
        self.projects_dir = Path(projects_dir)
        self.character_profiles_file = "characters.json"
        self.reference_images_dir = "reference_images"
        self.consistency_logs_dir = "consistency_logs"

    async def initialize_character_system(self, project_path: str) -> bool:
        """初始化项目角色系统"""
        try:
            project_root = self.projects_dir / project_path
            characters_dir = project_root / "characters"

            # 创建目录结构
            characters_dir.mkdir(exist_ok=True)
            (characters_dir / self.reference_images_dir).mkdir(exist_ok=True)
            (characters_dir / self.consistency_logs_dir).mkdir(exist_ok=True)

            # 初始化角色档案文件
            profiles_file = characters_dir / self.character_profiles_file
            if not profiles_file.exists():
                self._save_json(profiles_file, {"characters": [], "last_updated": datetime.now().isoformat()})

            logger.info(f"角色系统初始化完成: {project_path}")
            return True

        except Exception as e:
            logger.error(f"角色系统初始化失败: {e}")
            return False

    async def extract_characters_from_text(
        self,
        text: str,
        project_path: str,
        use_ai: bool = True
    ) -> List[CharacterProfile]:
        """从文本中提取角色信息"""
        logger.info("从文本中提取角色信息...")

        try:
            if use_ai:
                characters = await self._ai_extract_characters(text)
            else:
                characters = self._basic_extract_characters(text)

            # 保存角色档案
            await self._save_character_profiles(characters, project_path)

            logger.info(f"成功提取 {len(characters)} 个角色")
            return characters

        except Exception as e:
            logger.error(f"角色提取失败: {e}")
            return []

    async def _ai_extract_characters(self, text: str) -> List[CharacterProfile]:
        """使用AI提取角色信息"""
        from ..services.ai_service import AIService
        ai_service = AIService()

        try:
            # 构建角色提取提示词
            extraction_prompt = f"""
请仔细分析以下文本，提取其中的角色信息：

文本内容：
---
{text[:2000]}...
---

请识别文本中的所有角色，包括主要角色和重要配角，并提取以下信息：
1. 角色姓名
2. 角色描述（外貌、身份、性格等）
3. 性格特征（3-5个关键词）
4. 外貌特征（年龄、发型、身材、服装等）
5. 首次出现的位置或描述
6. 角色重要性（主要角色/次要角色/配角）
7. 与其他角色的关系

请以JSON格式返回：
{{
    "characters": [
        {{
            "name": "角色名",
            "description": "角色描述",
            "personality_traits": ["特征1", "特征2"],
            "appearance_features": {{
                "age": "年龄描述",
                "hair": "发型描述",
                "clothing": "服装描述",
                "other_features": "其他特征"
            }},
            "first_appearance": "首次出现描述",
            "importance_level": "main/secondary/minor",
            "relationships": {{"其他角色名": "关系描述"}}
        }}
    ]
}}
"""

            # 调用AI服务
            result = await ai_service.generate_text(
                prompt=extraction_prompt,
                model_preference="seedream",
                max_tokens=2000,
                temperature=0.3
            )

            # 解析AI结果
            try:
                ai_data = json.loads(result)
                characters_data = ai_data.get('characters', [])

                characters = []
                for char_data in characters_data:
                    profile = CharacterProfile(
                        name=char_data.get('name', ''),
                        description=char_data.get('description', ''),
                        personality_traits=char_data.get('personality_traits', []),
                        appearance_features=char_data.get('appearance_features', {}),
                        reference_images=[],
                        consistency_tags=[],
                        first_appearance=char_data.get('first_appearance', ''),
                        importance_level=char_data.get('importance_level', 'minor'),
                        relationships=char_data.get('relationships', {}),
                        last_updated=datetime.now().isoformat()
                    )
                    characters.append(profile)

                return characters

            except json.JSONDecodeError:
                logger.warning("AI角色提取结果解析失败")
                return self._basic_extract_characters(text)

        except Exception as e:
            logger.error(f"AI角色提取失败: {e}")
            return self._basic_extract_characters(text)

    def _basic_extract_characters(self, text: str) -> List[CharacterProfile]:
        """基础角色提取（非AI方法）"""
        characters = []

        # 简单的人名识别（中文名字模式）
        name_patterns = [
            r'[王李张刘陈杨黄赵吴周徐孙马朱胡郭何高林罗郑梁谢宋唐许韩冯邓曹彭曾萧田董袁潘于蒋蔡余杜叶程苏魏吕丁任沈姚卢姜崔钟谭陆汪范金石廖贾夏韦付方白邹孟熊秦邱江尹薛闫段雷侯龙史陶黎贺顾毛郝龚邵万钱严覃武戴莫孔向汤][一-龯]{1,2}',
            r'[A-Z][a-z]+\s[A-Z][a-z]+',  # 英文名
        ]

        # 提取可能的人名
        potential_names = set()
        for pattern in name_patterns:
            matches = re.findall(pattern, text)
            potential_names.update(matches)

        # 过滤常见词汇
        common_words = {'今天', '明天', '昨天', '这里', '那里', '什么', '怎么', '为什么'}
        potential_names = {name for name in potential_names if name not in common_words}

        # 为每个识别的名字创建基础角色档案
        for name in potential_names:
            if len(name) >= 2:  # 过滤单字符
                profile = CharacterProfile(
                    name=name,
                    description=f"在文本中识别的角色：{name}",
                    personality_traits=[],
                    appearance_features={},
                    reference_images=[],
                    consistency_tags=[],
                    first_appearance="自动识别",
                    importance_level="minor",
                    relationships={},
                    last_updated=datetime.now().isoformat()
                )
                characters.append(profile)

        return characters

    async def _save_character_profiles(
        self,
        characters: List[CharacterProfile],
        project_path: str
    ) -> bool:
        """保存角色档案"""
        try:
            characters_dir = self.projects_dir / project_path / "characters"
            profiles_file = characters_dir / self.character_profiles_file

            # 读取现有档案
            existing_data = self._load_json(profiles_file)
            existing_characters = existing_data.get('characters', [])

            # 合并新角色（避免重复）
            existing_names = {char['name'] for char in existing_characters}
            for new_char in characters:
                if new_char.name not in existing_names:
                    existing_characters.append(new_char.to_dict())
                else:
                    # 更新现有角色信息
                    for i, existing_char in enumerate(existing_characters):
                        if existing_char['name'] == new_char.name:
                            # 合并信息，保留参考图片
                            existing_ref_images = existing_char.get('reference_images', [])
                            updated_char = new_char.to_dict()
                            updated_char['reference_images'] = existing_ref_images
                            updated_char['last_updated'] = datetime.now().isoformat()
                            existing_characters[i] = updated_char
                            break

            # 保存更新后的档案
            updated_data = {
                'characters': existing_characters,
                'last_updated': datetime.now().isoformat(),
                'total_characters': len(existing_characters)
            }

            self._save_json(profiles_file, updated_data)
            logger.info(f"角色档案保存成功: {len(existing_characters)} 个角色")
            return True

        except Exception as e:
            logger.error(f"角色档案保存失败: {e}")
            return False

    async def add_reference_image(
        self,
        project_path: str,
        character_name: str,
        image_path: str,
        image_description: Optional[str] = None
    ) -> bool:
        """添加角色参考图"""
        try:
            characters_dir = self.projects_dir / project_path / "characters"
            ref_images_dir = characters_dir / self.reference_images_dir

            # 创建角色专属目录
            char_dir = ref_images_dir / character_name
            char_dir.mkdir(exist_ok=True)

            # 生成唯一文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_hash = hashlib.md5(str(image_path).encode()).hexdigest()[:8]
            file_extension = Path(image_path).suffix
            new_filename = f"{character_name}_{timestamp}_{file_hash}{file_extension}"

            # 复制图片到参考图目录
            dest_path = char_dir / new_filename
            if Path(image_path).exists():
                shutil.copy2(image_path, dest_path)
            else:
                logger.error(f"源图片文件不存在: {image_path}")
                return False

            # 更新角色档案
            profiles_file = characters_dir / self.character_profiles_file
            profiles_data = self._load_json(profiles_file)

            characters = profiles_data.get('characters', [])
            for char in characters:
                if char['name'] == character_name:
                    ref_images = char.get('reference_images', [])
                    ref_images.append({
                        'filename': new_filename,
                        'relative_path': f"{self.reference_images_dir}/{character_name}/{new_filename}",
                        'absolute_path': str(dest_path),
                        'description': image_description or f"参考图 {len(ref_images) + 1}",
                        'added_time': datetime.now().isoformat(),
                        'file_hash': file_hash
                    })
                    char['reference_images'] = ref_images
                    char['last_updated'] = datetime.now().isoformat()
                    break

            # 保存更新
            profiles_data['last_updated'] = datetime.now().isoformat()
            self._save_json(profiles_file, profiles_data)

            logger.info(f"参考图添加成功: {character_name} -> {new_filename}")
            return True

        except Exception as e:
            logger.error(f"添加参考图失败: {e}")
            return False

    async def get_character_profiles(
        self,
        project_path: str,
        character_name: Optional[str] = None
    ) -> List[CharacterProfile]:
        """获取角色档案"""
        try:
            characters_dir = self.projects_dir / project_path / "characters"
            profiles_file = characters_dir / self.character_profiles_file

            profiles_data = self._load_json(profiles_file)
            characters = profiles_data.get('characters', [])

            if character_name:
                characters = [char for char in characters if char['name'] == character_name]

            return [CharacterProfile.from_dict(char) for char in characters]

        except Exception as e:
            logger.error(f"获取角色档案失败: {e}")
            return []

    async def check_character_consistency(
        self,
        project_path: str,
        character_name: str,
        generated_image_path: str,
        use_ai: bool = True
    ) -> ConsistencyMatch:
        """检查角色一致性"""
        logger.info(f"检查角色一致性: {character_name}")

        try:
            # 获取角色档案
            profiles = await self.get_character_profiles(project_path, character_name)
            if not profiles:
                return ConsistencyMatch(
                    character_name=character_name,
                    match_score=0.0,
                    matched_features=[],
                    mismatched_features=["角色档案不存在"],
                    confidence=0.0,
                    reference_image_used="",
                    match_time=datetime.now().isoformat()
                )

            character_profile = profiles[0]

            if use_ai:
                return await self._ai_consistency_check(character_profile, generated_image_path, project_path)
            else:
                return await self._basic_consistency_check(character_profile, generated_image_path)

        except Exception as e:
            logger.error(f"角色一致性检查失败: {e}")
            return ConsistencyMatch(
                character_name=character_name,
                match_score=0.0,
                matched_features=[],
                mismatched_features=[f"检查失败: {str(e)}"],
                confidence=0.0,
                reference_image_used="",
                match_time=datetime.now().isoformat()
            )

    async def _ai_consistency_check(
        self,
        character_profile: CharacterProfile,
        generated_image_path: str,
        project_path: str
    ) -> ConsistencyMatch:
        """AI辅助一致性检查"""
        from ..services.ai_service import AIService
        ai_service = AIService()

        try:
            # 获取参考图片
            ref_images = character_profile.reference_images
            if not ref_images:
                return ConsistencyMatch(
                    character_name=character_profile.name,
                    match_score=0.5,
                    matched_features=[],
                    mismatched_features=["无参考图片"],
                    confidence=0.3,
                    reference_image_used="",
                    match_time=datetime.now().isoformat()
                )

            # 使用最新参考图
            latest_ref = ref_images[-1] if ref_images else None
            ref_image_path = latest_ref.get('absolute_path', '') if latest_ref else ''

            # 构建一致性检查提示词
            consistency_prompt = f"""
请比较生成的角色图像与角色设定的一致性：

角色姓名：{character_profile.name}
角色描述：{character_profile.description}
性格特征：{', '.join(character_profile.personality_traits)}
外貌特征：{json.dumps(character_profile.appearance_features, ensure_ascii=False)}

请评估生成图像与角色设定的匹配度，包括：
1. 外貌特征匹配度（发型、服装、体型等）
2. 性格特征体现度
3. 整体感觉匹配度

请以JSON格式返回评估结果：
{{
    "match_score": 0.85,
    "matched_features": ["发型匹配", "服装风格一致"],
    "mismatched_features": ["发色略有差异"],
    "confidence": 0.9,
    "detailed_assessment": "详细评估描述",
    "suggestions": ["改进建议"]
}}
"""

            # 调用AI服务
            result = await ai_service.generate_text(
                prompt=consistency_prompt,
                model_preference="seedream",
                max_tokens=800,
                temperature=0.2
            )

            # 解析AI结果
            try:
                ai_data = json.loads(result)

                return ConsistencyMatch(
                    character_name=character_profile.name,
                    match_score=ai_data.get('match_score', 0.5),
                    matched_features=ai_data.get('matched_features', []),
                    mismatched_features=ai_data.get('mismatched_features', []),
                    confidence=ai_data.get('confidence', 0.5),
                    reference_image_used=ref_image_path,
                    match_time=datetime.now().isoformat()
                )

            except json.JSONDecodeError:
                logger.warning("AI一致性检查结果解析失败")
                return await self._basic_consistency_check(character_profile, generated_image_path)

        except Exception as e:
            logger.error(f"AI一致性检查失败: {e}")
            return await self._basic_consistency_check(character_profile, generated_image_path)

    async def _basic_consistency_check(
        self,
        character_profile: CharacterProfile,
        generated_image_path: str
    ) -> ConsistencyMatch:
        """基础一致性检查"""
        # 简单的基础检查逻辑
        match_score = 0.7  # 默认分数
        matched_features = ["基础匹配完成"]
        mismatched_features = []

        # 检查是否有参考图片
        if not character_profile.reference_images:
            mismatched_features.append("缺少参考图片")
            match_score = 0.5

        # 检查是否有外貌特征描述
        if not character_profile.appearance_features:
            mismatched_features.append("缺少外貌特征描述")
            match_score -= 0.1

        return ConsistencyMatch(
            character_name=character_profile.name,
            match_score=max(0.0, match_score),
            matched_features=matched_features,
            mismatched_features=mismatched_features,
            confidence=0.6,
            reference_image_used=character_profile.reference_images[-1].get('absolute_path', '') if character_profile.reference_images else '',
            match_time=datetime.now().isoformat()
        )

    async def log_consistency_result(
        self,
        project_path: str,
        consistency_match: ConsistencyMatch
    ) -> bool:
        """记录一致性检查结果"""
        try:
            characters_dir = self.projects_dir / project_path / "characters"
            logs_dir = characters_dir / self.consistency_logs_dir

            # 生成日志文件名
            timestamp = datetime.now().strftime("%Y%m%d")
            log_file = logs_dir / f"consistency_log_{timestamp}.json"

            # 读取现有日志
            existing_logs = self._load_json(log_file)
            if not isinstance(existing_logs, list):
                existing_logs = []

            # 添加新日志
            existing_logs.append(consistency_match.to_dict())

            # 保存日志
            self._save_json(log_file, existing_logs)

            logger.info(f"一致性检查结果已记录: {consistency_match.character_name}")
            return True

        except Exception as e:
            logger.error(f"记录一致性检查结果失败: {e}")
            return False

    async def get_consistency_stats(
        self,
        project_path: str,
        character_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """获取一致性统计信息"""
        try:
            characters_dir = self.projects_dir / project_path / "characters"
            logs_dir = characters_dir / self.consistency_logs_dir

            # 读取所有日志文件
            all_logs = []
            for log_file in logs_dir.glob("consistency_log_*.json"):
                logs = self._load_json(log_file)
                if isinstance(logs, list):
                    all_logs.extend(logs)

            # 过滤特定角色的日志
            if character_name:
                all_logs = [log for log in all_logs if log.get('character_name') == character_name]

            if not all_logs:
                return {
                    'total_checks': 0,
                    'average_score': 0.0,
                    'character_stats': {}
                }

            # 计算统计信息
            total_checks = len(all_logs)
            scores = [log.get('match_score', 0.0) for log in all_logs]
            average_score = sum(scores) / len(scores) if scores else 0.0

            # 按角色分组统计
            character_stats = {}
            for log in all_logs:
                char_name = log.get('character_name', 'unknown')
                if char_name not in character_stats:
                    character_stats[char_name] = {
                        'checks': 0,
                        'total_score': 0.0,
                        'average_score': 0.0
                    }

                character_stats[char_name]['checks'] += 1
                character_stats[char_name]['total_score'] += log.get('match_score', 0.0)

            # 计算各角色平均分
            for char_name, stats in character_stats.items():
                stats['average_score'] = stats['total_score'] / stats['checks'] if stats['checks'] > 0 else 0.0

            return {
                'total_checks': total_checks,
                'average_score': average_score,
                'character_stats': character_stats,
                'latest_check': max(log.get('match_time', '') for log in all_logs) if all_logs else ''
            }

        except Exception as e:
            logger.error(f"获取一致性统计失败: {e}")
            return {
                'total_checks': 0,
                'average_score': 0.0,
                'character_stats': {},
                'error': str(e)
            }

    def _load_json(self, file_path: Path) -> Any:
        """加载JSON文件"""
        try:
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"加载JSON文件失败 {file_path}: {e}")
        return {} if file_path.suffix == '.json' else []

    def _save_json(self, file_path: Path, data: Any) -> bool:
        """保存JSON文件"""
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"保存JSON文件失败 {file_path}: {e}")
            return False


# 创建全局角色一致性管理器实例
character_consistency_manager = CharacterConsistencyManager()