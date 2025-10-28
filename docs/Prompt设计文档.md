# Prompt设计文档

## 概述

本文档详细说明了AI漫画生成系统中各个环节的prompt设计，包括角色定位、任务描述、JSON Schema实现和具体应用场景。

## 一、整体设计原则

### 1.1 核心设计理念
- **角色定位明确** - 每个prompt都有清晰的专业角色定位
- **任务描述具体** - 明确告诉AI需要完成的具体任务
- **输出格式标准化** - 普遍使用JSON Schema确保结构化输出
- **上下文信息完整** - 提供充足的背景信息帮助AI理解
- **专业性导向** - 针对漫画创作的专业需求设计
- **错误处理机制** - 包含异常情况的处理prompt

### 1.2 JSON Schema实现机制
项目实现了完整的JSON Schema系统，确保AI输出的结构化和可靠性：

```python
def create_json_schema_response_format(self, schema: Dict[str, Any]) -> Dict[str, Any]:
    """创建JSON Schema响应格式"""
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "response",
            "schema": schema,
            "strict": True
        }
    }
```

## 二、核心Agent环节的Prompt设计

### 2.1 文本分段Agent (text_segmenter.py)

#### 角色定位
```
你是一位资深的漫画师，特别擅长构建冲突的剧情，请将以下小说文本分割成适合漫画表现的段落
```

#### 核心要求
- **强制分段**: 原文必须切成20到30段
- **代词替换**: 各个段落中指向人的代词，替换成人名
- **剧情连贯**: 段落之间剧情要连贯，并且突出核心剧情
- **对话生成**: 为剧情人物生成合适的对话内容
- **字符控制**: 每个段落约250-350字符

#### JSON Schema结构
```python
{
    "type": "object",
    "properties": {
        "segments": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "段落文本内容"},
                    "segment_type": {
                        "type": "string",
                        "enum": ["dialogue", "action", "description", "transition", "climax", "resolution"]
                    },
                    "scene_setting": {"type": "string", "description": "场景设置"},
                    "characters": {"type": "string", "description": "出现的角色"},
                    "emotional_tone": {"type": "string", "description": "情感基调"},
                    "visual_focus": {"type": "string", "description": "视觉焦点"}
                },
                "required": ["content", "segment_type", "scene_setting", "characters", "emotional_tone", "visual_focus"]
            }
        }
    }
}
```

#### 实际调用示例
```python
result = await self.ai_service.generate_text(
    prompt=prompt,
    model="deepseek-chat",
    use_json_schema=True,
    schema_type="simple_text_segmentation"
)
```

### 2.2 图像生成Agent (image_generator.py)

#### 角色定位
```
作为专业的漫画图像生成专家，请根据以下场景描述生成详细的图像prompt
```

#### 核心任务要素
1. **主体描述** (角色、表情、动作)
2. **环境背景** (室内/室外、具体场景)
3. **构图角度** (远景/中景/特写)
4. **光影效果**
5. **色彩基调**
6. **漫画风格指示**

#### Prompt构建模板
```python
def _optimize_scene_description(self, scene_text, context_info):
    prompt = f"""作为专业的漫画图像生成专家，请根据以下场景描述生成详细的图像prompt：

场景描述：{scene_text}

上下文信息：
- 角色：{context_info.get('characters', [])}
- 风格：{context_info.get('style', 'manga')}
- 前情提要：{context_info.get('previous_scene', '')}

请生成包含以下要素的prompt：
1. 主体描述（角色、表情、动作）
2. 环境背景（室内/室外、具体场景）
3. 构图角度（远景/中景/特写）
4. 光影效果
5. 色彩基调
6. 漫画风格指示

输出格式：JSON"""
```

#### 特色功能
- **前情提要参考**: 确保风格一致性
- **多样性支持**: `_create_variant_prompt()`生成变体
- **对话提取**: `_extract_dialogue_from_text()`从文本中提取对话内容

### 2.3 封面生成Agent (cover_generator.py)

#### 角色定位
```
作为专业的漫画封面设计师，请为以下项目设计封面
```

#### 封面设计要素
1. **主体构图** (主角位置、姿态)
2. **背景设计**
3. **色彩方案**
4. **文字排版建议**
5. **整体氛围**

#### Few-shot示例设计
```python
def _build_cover_prompt(self, project_info, characters, user_requirements):
    # 集成项目信息、角色信息、用户要求
    # 支持项目封面和章节封面的不同策略
    # 使用few-shot示例引导AI生成高质量封面描述
```

### 2.4 脚本生成Agent (script_generator.py)

#### 角色定位
```
你是专业的漫画脚本创作者。请将以下分段文本转换为详细的漫画分镜脚本
```

#### 脚本结构要求
每个脚本段落必须包含：
- **分镜编号**
- **场景描述** (1-2句话)
- **角色动作和表情**
- **对话内容**
- **镜头角度建议**
- **页面布局建议**

#### 单场景优化
```python
# 专门的单场景描述prompt，将段落浓缩为1个核心场景
# 包含核心情节、场景环境、出场角色、主要动作等要素
# JSON Schema格式的prompt输出
```

### 2.5 质量评估Agent (quality_assessor.py)

#### 评估维度
1. **准确性** - 是否保留了关键信息
2. **流畅性** - 语言是否自然流畅
3. **情感表达** - 是否保持了原作情感
4. **完整性** - 故事情节是否完整

#### JSON输出格式
```python
{
    "accuracy_score": 0.95,
    "fluency_score": 0.88,
    "emotional_score": 0.92,
    "completeness_score": 0.90,
    "overall_score": 0.91,
    "detailed_feedback": "详细的评估反馈"
}
```

## 三、工作流环节的Prompt设计

### 3.1 反馈处理工作流 (feedback_handler.py)

#### 反馈分类Prompt
```python
def _classify_feedback(self, user_feedback):
    prompt = f"""请对以下用户反馈进行分类：

用户反馈：{user_feedback}

分类标准：
1. 内容修改 - 对剧情、角色、对话的修改建议
2. 视觉调整 - 对图像、风格、构图的调整要求
3. 技术问题 - 系统错误、功能缺陷
4. 用户体验 - 界面、流程、交互建议

请输出JSON格式：
{{
    "category": "分类结果",
    "priority": "高/中/低",
    "suggested_action": "建议处理方式"
}}"""
```

### 3.2 文本压缩工作流 (text_compression.py)

#### 压缩策略
- 保持内容完整性的压缩策略
- 保留关键情节和角色特征
- 维护情感基调和风格一致性

## 四、服务层的Prompt模板管理

### 4.1 AI服务统一接口 (ai_service.py)

#### Schema类型定义
项目定义了多种专门的Schema类型：

```python
# 文本分析Schema
def create_text_analysis_schema(self) -> Dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "summary": {"type": "string", "description": "文本摘要，不超过200字"},
            "main_theme": {"type": "string", "description": "主要主题"},
            "characters": {"type": "array", "items": {...}},
            "plot_points": {"type": "array", "items": {"type": "string"}},
            "setting": {"type": "string", "description": "故事背景设定"}
        }
    }

# 角色分析Schema
def create_character_analysis_schema(self) -> Dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "characters": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "appearance": {"type": "string"},
                        "personality": {"type": "string"},
                        "role": {"type": "string"}
                    }
                }
            }
        }
    }

# 脚本生成Schema
def create_script_generation_schema(self) -> Dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "script_segments": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "scene_number": {"type": "integer"},
                        "scene_description": {"type": "string"},
                        "characters": {"type": "array", "items": {"type": "string"}},
                        "dialogue": {"type": "string"},
                        "action": {"type": "string"},
                        "camera_angle": {"type": "string"},
                        "panel_layout": {"type": "string"}
                    }
                }
            }
        }
    }
```

### 4.2 统一的Prompt构建接口

```python
async def generate_text(
    self,
    prompt: str,
    model: str = "deepseek-chat",
    temperature: float = 0.7,
    max_tokens: Optional[int] = None,
    use_json_schema: bool = False,
    schema_type: Optional[str] = None
) -> str:
    """
    统一的文本生成接口

    Args:
        prompt: 提示词
        model: 模型名称
        temperature: 温度参数
        max_tokens: 最大token数
        use_json_schema: 是否使用JSON Schema
        schema_type: Schema类型 (text_analysis, character_analysis, script_generation)
    """
```

## 五、特色Prompt技术

### 5.1 上下文增强技术

```python
def enhance_prompt_with_reference_description(self, base_prompt: str, reference_description: str) -> str:
    """基于参考图片增强prompt"""
    enhanced_prompt = f"""{base_prompt}

参考风格描述：
{reference_description}

请严格按照参考风格进行生成，确保：
1. 角色形象一致性
2. 画风统一性
3. 色彩协调性
4. 构图风格一致性"""
    return enhanced_prompt
```

### 5.2 多轮对话上下文管理

```python
class ConversationContext:
    def __init__(self):
        self.history = []
        self.context_summary = ""

    def add_message(self, role: str, content: str):
        self.history.append({"role": role, "content": content})
        # 自动更新上下文摘要

    def build_context_prompt(self, current_prompt: str) -> str:
        """构建包含历史上下文的prompt"""
        context_prompt = f"""对话历史摘要：
{self.context_summary}

当前请求：
{current_prompt}

请基于对话历史上下文，提供一致性的回应。"""
        return context_prompt
```

### 5.3 错误处理和降级机制

```python
try:
    # 尝试使用JSON Schema
    result = await self.ai_service.generate_text(
        prompt=prompt,
        model=model,
        use_json_schema=True,
        schema_type=schema_type
    )
    # 验证JSON格式
    parsed_result = json.loads(result)
    self._validate_schema(parsed_result, schema_type)

except (json.JSONDecodeError, RuntimeError) as e:
    logger.warning(f"JSON Schema失败，启用降级模式: {e}")

    # 降级到普通文本prompt
    fallback_prompt = f"""{prompt}

请直接返回JSON格式的结果，不要添加任何其他文字说明：
{{
    // 期望的JSON结构
}}"""

    result = await self.ai_service.generate_text(
        prompt=fallback_prompt,
        model=model,
        use_json_schema=False
    )
```

## 六、前端集成的Prompt应用

### 6.1 用户引导流程中的Prompt设计

#### 新手引导Prompt
```javascript
const noviceGuidePrompt = `
作为漫画创作助手，请为新手用户提供友好的引导：

用户输入：${userInput}

请：
1. 理解用户的创作意图
2. 提供专业且易懂的建议
3. 引导用户完善创作需求
4. 保持鼓励和支持的语气

输出格式：
{
    "understanding": "对用户需求的理解",
    "suggestions": ["建议1", "建议2", "建议3"],
    "next_steps": ["下一步1", "下一步2"],
    "encouragement": "鼓励的话语"
}
`;
```

#### 专业用户Prompt
```javascript
const professionalPrompt = `
作为专业的漫画创作工具，请为经验丰富的用户提供高效支持：

用户需求：${userRequest}
项目上下文：${projectContext}

请提供：
1. 精准的技术实现方案
2. 专业的创作建议
3. 高效的工作流程
4. 深度定制选项

输出格式：简洁专业的JSON响应
`;
```

### 6.2 实时预览的Prompt优化

```javascript
function generatePreviewPrompt(partialInput, context) {
    return `
    基于以下部分输入和上下文，生成实时预览：

    部分输入：${partialInput}
    上下文：${JSON.stringify(context)}

    要求：
    1. 快速响应，优化生成速度
    2. 保持与之前结果的一致性
    3. 提供渐进式完善建议
    4. 支持用户快速调整

    输出格式：轻量级JSON，便于实时渲染
    `;
}
```

## 七、性能优化策略

### 7.1 Prompt缓存机制

```python
class PromptCache:
    def __init__(self):
        self.cache = {}
        self.cache_ttl = 3600  # 1小时过期

    def get_cached_prompt(self, prompt_type: str, context_hash: str) -> Optional[str]:
        """获取缓存的prompt"""
        cache_key = f"{prompt_type}:{context_hash}"
        cached_item = self.cache.get(cache_key)

        if cached_item and time.time() - cached_item["timestamp"] < self.cache_ttl:
            return cached_item["prompt"]
        return None

    def cache_prompt(self, prompt_type: str, context_hash: str, prompt: str):
        """缓存prompt"""
        cache_key = f"{prompt_type}:{context_hash}"
        self.cache[cache_key] = {
            "prompt": prompt,
            "timestamp": time.time()
        }
```

### 7.2 Prompt模板管理

```python
class PromptTemplateManager:
    def __init__(self):
        self.templates = {}
        self.load_templates()

    def load_templates(self):
        """加载prompt模板"""
        self.templates = {
            "text_segmentation": self._load_template("text_segmentation.json"),
            "image_generation": self._load_template("image_generation.json"),
            "character_design": self._load_template("character_design.json"),
            "script_generation": self._load_template("script_generation.json")
        }

    def render_template(self, template_name: str, variables: Dict[str, Any]) -> str:
        """渲染prompt模板"""
        template = self.templates.get(template_name)
        if not template:
            raise ValueError(f"未找到模板: {template_name}")

        # 使用Jinja2或简单字符串替换进行模板渲染
        return template.format(**variables)
```

## 八、安全和限制

### 8.1 内容安全过滤

```python
def add_content_safety_filters(prompt: str) -> str:
    """添加内容安全过滤prompt"""
    safety_prompt = f"""
    {prompt}

    重要安全要求：
    1. 不得生成暴力、血腥、恐怖内容
    2. 不得生成歧视性、仇恨性言论
    3. 不得生成成人内容或不当暗示
    4. 尊重知识产权，避免抄袭
    5. 遵守法律法规和道德准则

    如发现违规内容，请拒绝生成并说明原因。
    """
    return safety_prompt
```

### 8.2 使用限制提示

```python
def add_usage_limits_prompt(prompt: str, user_tier: str) -> str:
    """添加使用限制提示"""
    limits = {
        "free": "免费用户每日限制10次生成",
        "basic": "基础用户每日限制50次生成",
        "pro": "专业用户每日限制200次生成",
        "enterprise": "企业用户无限制"
    }

    limit_prompt = f"""
    {prompt}

    使用提醒：
    - 当前用户等级：{user_tier}
    - 使用限制：{limits.get(user_tier, '未知')}
    - 请合理使用，避免浪费资源
    """
    return limit_prompt
```

## 九、测试和验证

### 9.1 Prompt单元测试

```python
import pytest
from unittest.mock import Mock, patch

class TestPromptDesign:
    def test_text_segmentation_prompt(self):
        """测试文本分段prompt生成"""
        segmenter = TextSegmenter()
        prompt = segmenter._build_simple_schema_prompt("测试文本", 300)

        # 验证prompt包含必要元素
        assert "20到30段" in prompt
        assert "JSON Schema" in prompt
        assert "漫画师" in prompt

    def test_json_schema_validation(self):
        """测试JSON Schema验证"""
        ai_service = AIService()
        schema = ai_service.create_simple_text_segmentation_schema()

        # 测试有效数据
        valid_data = {
            "segments": [
                {
                    "content": "测试内容",
                    "segment_type": "dialogue",
                    "scene_setting": "测试场景",
                    "characters": "测试角色",
                    "emotional_tone": "测试情感",
                    "visual_focus": "测试焦点"
                }
            ]
        }

        assert ai_service._validate_schema(valid_data, schema) is True

    @pytest.mark.asyncio
    async def test_prompt_generation_with_fallback(self):
        """测试prompt生成的降级机制"""
        ai_service = AIService()

        # 模拟JSON Schema失败
        with patch.object(ai_service, 'generate_text') as mock_generate:
            mock_generate.side_effect = [
                json.JSONDecodeError("Invalid JSON", "", 0),  # 第一次失败
                '{"fallback": "result"}'  # 降级成功
            ]

            result = await ai_service.generate_text_with_fallback(
                "test prompt",
                use_json_schema=True,
                schema_type="text_analysis"
            )

            assert result == '{"fallback": "result"}'
```

### 9.2 Prompt效果评估

```python
class PromptEvaluator:
    def __init__(self):
        self.evaluation_metrics = [
            "response_relevance",
            "output_format_correctness",
            "content_completeness",
            "creativity_score",
            "consistency_score"
        ]

    def evaluate_prompt_result(self, prompt: str, result: str, expected_format: Dict) -> Dict[str, float]:
        """评估prompt结果质量"""
        scores = {}

        # 格式正确性检查
        try:
            parsed_result = json.loads(result)
            scores["format_correctness"] = 1.0 if self._validate_format(parsed_result, expected_format) else 0.0
        except:
            scores["format_correctness"] = 0.0

        # 内容相关性评估
        scores["relevance_score"] = self._calculate_relevance(prompt, result)

        # 创意性评分
        scores["creativity_score"] = self._assess_creativity(result)

        return scores
```

## 十、总结

本项目的prompt设计体现了以下特点：

### 10.1 技术优势
1. **结构化输出** - 通过JSON Schema确保输出的标准化和可靠性
2. **模块化设计** - 不同环节的prompt职责清晰，易于维护
3. **错误处理** - 完善的降级机制和异常处理
4. **性能优化** - 缓存机制和模板管理提升效率

### 10.2 业务价值
1. **专业性** - 针对漫画创作的专业需求设计
2. **用户体验** - 考虑不同用户类型的引导策略
3. **一致性** - 确保角色、风格、剧情的连贯性
4. **安全性** - 内容过滤和使用限制保障安全

### 10.3 创新亮点
1. **Few-shot学习** - 通过示例引导提升生成质量
2. **上下文管理** - 多轮对话的一致性保障
3. **实时优化** - 基于用户反馈的prompt动态调整
4. **跨领域整合** - 文本分析、图像生成、质量评估的统一prompt体系

这套prompt系统为AI漫画生成提供了强大的技术支撑，确保了整个创作流程的专业性、可靠性和用户体验。