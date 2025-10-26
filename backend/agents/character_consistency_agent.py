"""
角色一致性Agent
Character Consistency Agent

负责确保漫画生成过程中角色的一致性，包括特征提取、匹配算法和一致性保证
Responsible for ensuring character consistency during comic generation, including feature extraction, matching algorithms, and consistency guarantees
"""

import logging
import json
from typing import Dict, Any, List
from datetime import datetime
import re

from services.ai_service import AIService
from services.character_consistency import (
    CharacterConsistencyManager, CharacterProfile
)

logger = logging.getLogger(__name__)


class CharacterFeature:
    """角色特征数据结构"""

    def __init__(
        self,
        character_name: str,
        visual_features: Dict[str, Any],
        personality_features: List[str],
        style_features: Dict[str, Any],
        consistency_tags: List[str],
        confidence: float = 0.0
    ):
        self.character_name = character_name
        self.visual_features = visual_features
        self.personality_features = personality_features
        self.style_features = style_features
        self.consistency_tags = consistency_tags
        self.confidence = confidence
        self.extraction_time = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'character_name': self.character_name,
            'visual_features': self.visual_features,
            'personality_features': self.personality_features,
            'style_features': self.style_features,
            'consistency_tags': self.consistency_tags,
            'confidence': self.confidence,
            'extraction_time': self.extraction_time
        }


class ConsistencyRule:
    """一致性规则数据结构"""

    def __init__(
        self,
        rule_name: str,
        rule_type: str,  # visual, personality, style
        condition: str,
        action: str,
        priority: int = 1
    ):
        self.rule_name = rule_name
        self.rule_type = rule_type
        self.condition = condition
        self.action = action
        self.priority = priority
        self.created_time = datetime.now().isoformat()


class CharacterConsistencyAgent:
    """角色一致性Agent"""

    def __init__(self):
        self.ai_service = AIService()
        self.consistency_manager = CharacterConsistencyManager()

        # 默认一致性规则
        self.default_rules = [
            ConsistencyRule(
                "maintain_hair_color",
                "visual",
                "character.has_hair_color",
                "keep_hair_color_consistent",
                priority=3
            ),
            ConsistencyRule(
                "maintain_clothing_style",
                "visual",
                "character.has_clothing_preference",
                "keep_clothing_style_consistent",
                priority=2
            ),
            ConsistencyRule(
                "maintain_personality",
                "personality",
                "character.has_personality_traits",
                "express_personality_consistently",
                priority=2
            ),
            ConsistencyRule(
                "maintain_age_appearance",
                "visual",
                "character.has_age_range",
                "keep_age_appropriate_appearance",
                priority=2
            )
        ]

    async def ensure_character_consistency(
        self,
        project_path: str,
        script_content: str,
        generated_images: List[Dict[str, Any]],
        apply_corrections: bool = True
    ) -> Dict[str, Any]:
        """
        确保角色一致性的主函数

        Args:
            project_path: 项目路径
            script_content: 脚本内容
            generated_images: 已生成的图像列表
            apply_corrections: 是否应用一致性修正

        Returns:
            一致性检查和修正结果
        """
        logger.info("开始角色一致性检查...")

        try:
            # 1. 获取角色档案
            character_profiles = await self.consistency_manager.get_character_profiles(project_path)

            if not character_profiles:
                logger.warning("未找到角色档案，跳过一致性检查")
                return {'status': 'skipped', 'reason': 'no_character_profiles'}

            # 2. 从脚本中提取角色出现信息
            script_characters = await self._extract_characters_from_script(script_content)

            # 3. 为每个角色进行一致性检查
            consistency_results = {}

            for character in character_profiles:
                if character.name in script_characters:
                    character_result = await self._check_single_character_consistency(
                        character, script_characters[character.name], generated_images, project_path
                    )
                    consistency_results[character.name] = character_result

            # 4. 应用一致性修正
            correction_results = {}
            if apply_corrections:
                correction_results = await self._apply_consistency_corrections(
                    consistency_results, project_path
                )

            # 5. 生成一致性报告
            consistency_report = self._generate_consistency_report(
                consistency_results, correction_results
            )

            logger.info(f"角色一致性检查完成，检查了 {len(consistency_results)} 个角色")
            return {
                'status': 'completed',
                'characters_checked': len(consistency_results),
                'consistency_results': consistency_results,
                'correction_results': correction_results,
                'consistency_report': consistency_report,
                'overall_consistency_score': self._calculate_overall_consistency_score(consistency_results)
            }

        except Exception as e:
            logger.error(f"角色一致性检查失败: {e}")
            return {'status': 'error', 'error': str(e)}

    async def _extract_characters_from_script(self, script_content: str) -> Dict[str, Dict[str, Any]]:
        """从脚本中提取角色出现信息"""
        logger.info("从脚本中提取角色信息...")

        try:
            # 构建角色提取提示词
            extraction_prompt = f"""
请分析以下漫画脚本，识别其中出现的角色及其相关信息：

脚本内容：
---
{script_content}
---

请识别：
1. 每个角色在哪些场景中出现
2. 角色的动作、表情、服装描述
3. 角色之间的互动
4. 场景描述对角色表现的要求

请以JSON格式返回：
{{
    "characters": {
        "角色名": {
            "appearances": [
                {
                    "scene_number": 1,
                    "scene_description": "场景描述",
                    "character_action": "角色动作",
                    "character_expression": "表情描述",
                    "clothing_description": "服装描述",
                    "interaction_with": ["其他角色名"]
                }
            ],
            "total_appearances": 3,
            "key_scenes": [1, 3]
        }
    }
}}
"""

            # 调用AI服务
            result = await self.ai_service.generate_text(
                prompt=extraction_prompt,
                model_preference="seedream",
                max_tokens=8000,
                temperature=0.2
            )

            # 解析结果
            try:
                ai_data = json.loads(result)
                return ai_data.get('characters', {})
            except json.JSONDecodeError:
                logger.warning("脚本角色提取结果解析失败")
                return self._basic_script_character_extraction(script_content)

        except Exception as e:
            logger.error(f"脚本角色提取失败: {e}")
            return self._basic_script_character_extraction(script_content)

    def _basic_script_character_extraction(self, script_content: str) -> Dict[str, Dict[str, Any]]:
        """基础脚本角色提取"""
        characters = {}

        # 简单的人名识别
        name_pattern = r'([王李张刘陈杨黄赵吴周徐孙马朱胡郭何高林罗郑梁谢宋唐许韩冯邓曹彭曾萧田董袁潘于蒋蔡余杜叶程苏魏吕丁任沈姚卢姜崔钟谭陆汪范金石廖贾夏韦付方白邹孟熊秦邱江尹薛闫段雷侯龙史陶黎贺顾毛郝龚邵万钱严覃武戴莫孔向汤][一-龯]{1,2})'

        matches = re.finditer(name_pattern, script_content)
        for match in matches:
            name = match.group()
            if name not in characters:
                characters[name] = {
                    'appearances': [],
                    'total_appearances': 0,
                    'key_scenes': []
                }
            characters[name]['total_appearances'] += 1

        return characters

    async def _check_single_character_consistency(
        self,
        character_profile: CharacterProfile,
        script_info: Dict[str, Any],
        generated_images: List[Dict[str, Any]],
        project_path: str
    ) -> Dict[str, Any]:
        """检查单个角色的一致性"""
        logger.info(f"检查角色 {character_profile.name} 的一致性...")

        try:
            # 1. 提取角色特征
            character_features = await self._extract_character_features(character_profile)

            # 2. 分析脚本中的角色表现要求
            performance_requirements = await self._analyze_performance_requirements(
                character_profile, script_info
            )

            # 3. 检查已生成图像的一致性
            image_consistency_results = []
            for image_info in generated_images:
                if self._image_contains_character(image_info, character_profile.name):
                    consistency_result = await self.consistency_manager.check_character_consistency(
                        project_path, character_profile.name, image_info.get('local_path', '')
                    )
                    image_consistency_results.append({
                        'image_info': image_info,
                        'consistency_match': consistency_result.to_dict()
                    })

            # 4. 识别一致性问题
            consistency_issues = self._identify_consistency_issues(
                character_features, performance_requirements, image_consistency_results
            )

            # 5. 计算一致性分数
            consistency_score = self._calculate_character_consistency_score(
                character_features, image_consistency_results, consistency_issues
            )

            return {
                'character_name': character_profile.name,
                'character_features': character_features.to_dict(),
                'performance_requirements': performance_requirements,
                'image_consistency_results': image_consistency_results,
                'consistency_issues': consistency_issues,
                'consistency_score': consistency_score,
                'needs_correction': len(consistency_issues) > 0 or consistency_score < 0.7
            }

        except Exception as e:
            logger.error(f"角色 {character_profile.name} 一致性检查失败: {e}")
            return {
                'character_name': character_profile.name,
                'status': 'error',
                'error': str(e),
                'consistency_score': 0.0,
                'needs_correction': True
            }

    async def _extract_character_features(self, character_profile: CharacterProfile) -> CharacterFeature:
        """提取角色特征"""
        try:
            # 构建特征提取提示词
            feature_prompt = f"""
请基于角色档案提取详细的特征信息，用于图像生成的一致性检查：

角色姓名：{character_profile.name}
角色描述：{character_profile.description}
性格特征：{', '.join(character_profile.personality_traits)}
外貌特征：{json.dumps(character_profile.appearance_features, ensure_ascii=False)}

请提取以下特征：

1. 视觉特征：
   - 面部特征（脸型、眼睛、鼻子、嘴巴等）
   - 发型特征（发型、发色、长度等）
   - 体型特征（身高、体型等）
   - 服装特征（风格、颜色、款式等）

2. 性格特征：
   - 主要性格特点
   - 情感表达方式
   - 行为习惯

3. 风格特征：
   - 整体艺术风格要求
   - 色彩偏好
   - 表现手法

请以JSON格式返回：
{{
    "visual_features": {{
        "face": "面部特征描述",
        "hair": "发型特征描述",
        "body_type": "体型特征描述",
        "clothing": "服装特征描述",
        "key_visual_elements": ["关键视觉元素"]
    }},
    "personality_features": ["性格特征列表"],
    "style_features": {{
        "art_style": "艺术风格",
        "color_preference": "色彩偏好",
        "expression_style": "表现风格"
    }},
    "consistency_tags": ["一致性标签"],
    "confidence": 0.85
}}
"""

            # 调用AI服务
            result = await self.ai_service.generate_text(
                prompt=feature_prompt,
                model_preference="seedream",
                max_tokens=8000,
                temperature=0.2
            )

            # 解析结果
            try:
                ai_data = json.loads(result)

                return CharacterFeature(
                    character_name=character_profile.name,
                    visual_features=ai_data.get('visual_features', {}),
                    personality_features=ai_data.get('personality_features', []),
                    style_features=ai_data.get('style_features', {}),
                    consistency_tags=ai_data.get('consistency_tags', []),
                    confidence=ai_data.get('confidence', 0.5)
                )

            except json.JSONDecodeError:
                logger.warning(f"角色 {character_profile.name} 特征提取结果解析失败")
                return self._create_basic_character_feature(character_profile)

        except Exception as e:
            logger.error(f"角色 {character_profile.name} 特征提取失败: {e}")
            return self._create_basic_character_feature(character_profile)

    def _create_basic_character_feature(self, character_profile: CharacterProfile) -> CharacterFeature:
        """创建基础角色特征"""
        visual_features = character_profile.appearance_features or {}
        personality_features = character_profile.personality_traits or []

        return CharacterFeature(
            character_name=character_profile.name,
            visual_features=visual_features,
            personality_features=personality_features,
            style_features={'art_style': 'default'},
            consistency_tags=['basic'],
            confidence=0.5
        )

    async def _analyze_performance_requirements(
        self,
        character_profile: CharacterProfile,
        script_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """分析脚本中的角色表现要求"""
        try:
            # 构建表现要求分析提示词
            performance_prompt = f"""
请分析以下角色在漫画脚本中的表现要求：

角色姓名：{character_profile.name}
角色描述：{character_profile.description}

脚本中的出现信息：
{json.dumps(script_info, ensure_ascii=False)}

请分析：
1. 角色在不同场景中的表现要求
2. 表情和动作的具体要求
3. 服装和造型的变化需求
4. 与其他角色的互动要求

请以JSON格式返回：
{{
    "performance_requirements": {{
        "emotional_range": ["情感表现范围"],
        "action_requirements": ["动作要求"],
        "clothing_changes": ["服装变化需求"],
        "interaction_requirements": ["互动要求"]
    }},
    "scene_specific_requirements": {{
        "scene_1": "场景1的特定要求",
        "scene_2": "场景2的特定要求"
    }},
    "consistency_challenges": ["一致性挑战点"]
}}
"""

            # 调用AI服务
            result = await self.ai_service.generate_text(
                prompt=performance_prompt,
                model_preference="seedream",
                max_tokens=8000,
                temperature=0.2
            )

            # 解析结果
            try:
                ai_data = json.loads(result)
                return ai_data
            except json.JSONDecodeError:
                logger.warning(f"角色 {character_profile.name} 表现要求分析结果解析失败")
                return {'performance_requirements': {}, 'consistency_challenges': []}

        except Exception as e:
            logger.error(f"角色 {character_profile.name} 表现要求分析失败: {e}")
            return {'performance_requirements': {}, 'consistency_challenges': []}

    def _image_contains_character(
        self,
        image_info: Dict[str, Any],
        character_name: str
    ) -> bool:
        """检查图像是否包含指定角色"""
        # 简单检查：查看图像信息中是否包含角色名
        scene_description = image_info.get('scene_description', '')
        dialogue = image_info.get('dialogue', '')
        narration = image_info.get('narration', '')

        return character_name in scene_description or character_name in dialogue or character_name in narration

    def _identify_consistency_issues(
        self,
        character_features: CharacterFeature,
        performance_requirements: Dict[str, Any],
        image_consistency_results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """识别一致性问题"""
        issues = []

        # 检查图像一致性结果
        for result in image_consistency_results:
            consistency_match = result.get('consistency_match', {})
            match_score = consistency_match.get('match_score', 1.0)

            if match_score < 0.7:
                issues.append({
                    'issue_type': 'image_consistency',
                    'severity': 'high' if match_score < 0.5 else 'medium',
                    'description': f"图像一致性分数过低: {match_score:.2f}",
                    'affected_image': result.get('image_info', {}),
                    'mismatched_features': consistency_match.get('mismatched_features', []),
                    'suggestions': consistency_match.get('suggestions', [])
                })

        # 检查特征置信度
        if character_features.confidence < 0.6:
            issues.append({
                'issue_type': 'feature_confidence',
                'severity': 'medium',
                'description': f"角色特征提取置信度过低: {character_features.confidence:.2f}",
                'affected_features': ['all'],
                'suggestions': ['增加角色描述信息', '添加更多参考图片']
            })

        # 检查表现要求一致性
        challenges = performance_requirements.get('consistency_challenges', [])
        for challenge in challenges:
            issues.append({
                'issue_type': 'performance_consistency',
                'severity': 'medium',
                'description': f"表现一致性挑战: {challenge}",
                'affected_features': ['performance'],
                'suggestions': ['优化表现要求描述', '增加场景过渡设计']
            })

        return issues

    def _calculate_character_consistency_score(
        self,
        character_features: CharacterFeature,
        image_consistency_results: List[Dict[str, Any]],
        consistency_issues: List[Dict[str, Any]]
    ) -> float:
        """计算角色一致性分数"""
        # 基础分数
        base_score = character_features.confidence * 0.3

        # 图像一致性分数
        if image_consistency_results:
            image_scores = [result.get('consistency_match', {}).get('match_score', 0.0) for result in image_consistency_results]
            avg_image_score = sum(image_scores) / len(image_scores)
            image_score = avg_image_score * 0.5
        else:
            image_score = 0.8 * 0.5  # 默认分数

        # 问题扣分
        penalty = 0.0
        for issue in consistency_issues:
            severity = issue.get('severity', 'medium')
            if severity == 'critical':
                penalty += 0.3
            elif severity == 'high':
                penalty += 0.2
            elif severity == 'medium':
                penalty += 0.1
            elif severity == 'low':
                penalty += 0.05

        # 综合分数
        final_score = max(0.0, base_score + image_score - penalty)

        return round(final_score, 3)

    async def _apply_consistency_corrections(
        self,
        consistency_results: Dict[str, Dict[str, Any]],
        project_path: str
    ) -> Dict[str, Any]:
        """应用一致性修正"""
        logger.info("应用一致性修正...")

        correction_results = {}

        for character_name, result in consistency_results.items():
            if result.get('needs_correction', False):
                correction_result = await self._correct_character_consistency(
                    character_name, result, project_path
                )
                correction_results[character_name] = correction_result
            else:
                correction_results[character_name] = {
                    'status': 'no_correction_needed',
                    'message': '角色一致性良好，无需修正'
                }

        return correction_results

    async def _correct_character_consistency(
        self,
        character_name: str,
        consistency_result: Dict[str, Any],
        project_path: str
    ) -> Dict[str, Any]:
        """修正单个角色的一致性问题"""
        logger.info(f"修正角色 {character_name} 的一致性问题...")

        try:
            issues = consistency_result.get('consistency_issues', [])

            # 构建修正提示词
            correction_prompt = f"""
请为以下角色的一致性问题提供修正建议：

角色姓名：{character_name}
一致性分数：{consistency_result.get('consistency_score', 0.0)}
发现的问题：
{json.dumps(issues, ensure_ascii=False, indent=2)}

角色特征：
{json.dumps(consistency_result.get('character_features', {}), ensure_ascii=False, indent=2)}

请提供：
1. 具体的修正建议
2. 优先级排序
3. 实施方案
4. 预期效果

请以JSON格式返回：
{{
    "correction_plan": [
        {{
            "issue_type": "问题类型",
            "priority": "high/medium/low",
            "correction_method": "修正方法",
            "expected_improvement": "预期改善效果",
            "implementation_steps": ["实施步骤"]
        }}
    ],
    "overall_strategy": "整体修正策略",
    "estimated_improvement": 0.15
}}
"""

            # 调用AI服务
            result = await self.ai_service.generate_text(
                prompt=correction_prompt,
                model_preference="seedream",
                max_tokens=8000,
                temperature=0.3
            )

            # 解析结果
            try:
                correction_data = json.loads(result)

                return {
                    'status': 'success',
                    'correction_plan': correction_data.get('correction_plan', []),
                    'overall_strategy': correction_data.get('overall_strategy', ''),
                    'estimated_improvement': correction_data.get('estimated_improvement', 0.0),
                    'applied_time': datetime.now().isoformat()
                }

            except json.JSONDecodeError:
                logger.warning(f"角色 {character_name} 一致性修正建议解析失败")

                return {
                    'status': 'partial_success',
                    'correction_plan': [
                        {
                            'issue_type': 'general',
                            'priority': 'medium',
                            'correction_method': '增加参考图片',
                            'expected_improvement': '提升一致性识别准确度',
                            'implementation_steps': ['收集更多角色参考图', '更新角色档案']
                        }
                    ],
                    'overall_strategy': '基础修正策略',
                    'estimated_improvement': 0.1
                }

        except Exception as e:
            logger.error(f"角色 {character_name} 一致性修正失败: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }

    def _generate_consistency_report(
        self,
        consistency_results: Dict[str, Dict[str, Any]],
        correction_results: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """生成一致性报告"""
        total_characters = len(consistency_results)
        characters_with_issues = sum(1 for result in consistency_results.values() if result.get('needs_correction', False))
        applied_corrections = sum(1 for result in correction_results.values() if result.get('status') == 'success')

        # 计算平均一致性分数
        scores = [result.get('consistency_score', 0.0) for result in consistency_results.values()]
        average_score = sum(scores) / len(scores) if scores else 0.0

        # 统计问题类型
        issue_types = {}
        for result in consistency_results.values():
            for issue in result.get('consistency_issues', []):
                issue_type = issue.get('issue_type', 'unknown')
                if issue_type not in issue_types:
                    issue_types[issue_type] = 0
                issue_types[issue_type] += 1

        return {
            'summary': {
                'total_characters': total_characters,
                'characters_with_issues': characters_with_issues,
                'applied_corrections': applied_corrections,
                'average_consistency_score': round(average_score, 3),
                'issue_distribution': issue_types
            },
            'recommendations': self._generate_overall_recommendations(consistency_results),
            'report_generated_time': datetime.now().isoformat()
        }

    def _generate_overall_recommendations(
        self,
        consistency_results: Dict[str, Dict[str, Any]]
    ) -> List[str]:
        """生成整体建议"""
        recommendations = []

        # 基于结果生成建议
        low_score_characters = [name for name, result in consistency_results.items() if result.get('consistency_score', 0.0) < 0.6]
        if low_score_characters:
            recommendations.append(f"重点关注角色 {', '.join(low_score_characters)} 的一致性改进")

        # 检查常见问题
        common_issues = {}
        for result in consistency_results.values():
            for issue in result.get('consistency_issues', []):
                issue_type = issue.get('issue_type', 'unknown')
                if issue_type not in common_issues:
                    common_issues[issue_type] = 0
                common_issues[issue_type] += 1

        if common_issues:
            most_common_issue = max(common_issues, key=common_issues.get)
            recommendations.append(f"优先解决 {most_common_issue} 类型的一致性问题")

        # 通用建议
        recommendations.extend([
            "定期更新角色参考图片",
            "保持角色描述的详细性和一致性",
            "建立角色一致性的质量检查流程"
        ])

        return recommendations

    def _calculate_overall_consistency_score(
        self,
        consistency_results: Dict[str, Dict[str, Any]]
    ) -> float:
        """计算整体一致性分数"""
        if not consistency_results:
            return 0.0

        scores = [result.get('consistency_score', 0.0) for result in consistency_results.values()]
        return round(sum(scores) / len(scores), 3)


# 创建单例实例
character_consistency_agent = CharacterConsistencyAgent()