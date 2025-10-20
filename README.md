# 小说生成漫画应用开发计划

**用户是谁？**
专业用户(长期或专业画漫画的用户)
业余用户(心血来潮)
网络写手、签约作者没有时间和精力来处理

## 项目核心理念

**Human-in-the-loop**: AI生成都可以调整、修改、预览完整的漫画
**降低抽卡成本**: 引入动作编辑、画风滤镜、人物一致性机制
**剧情连贯性**: 前情提要系统，避免长文本理解问题
**快速上手**: 为不熟悉画画的用户提供直观的创作工具

## 技术架构决策

### 核心技术栈
- **后端**: FastAPI + Python (异步处理)
- **前端**: React + TypeScript
- **AI编排**: 混合策略 (LangGraph用于复杂流程，简单函数用于线性流程)
- **AI模型**: 豆包Seedream (主生成) + Qwen-Image-Edit (编辑)
- **存储**: 文件目录系统 (无数据库，无向量数据库，无OSS)

### AI编排策略
**使用LangGraph的场景**:
- 文本压缩Agent链 (多轮迭代状态管理)
- 用户反馈处理流程 (动态分支路由)

**使用简单函数的场景**:
- 主要漫画生成流程 (线性数据流)
- 并行画面生成 (asyncio并发)

### 文件目录存储架构
```
projects/
├── 2025.10.20_19.57_project_name/
│   ├── meta/                    # 项目元信息
│   ├── source/                  # 原始文件
│   ├── processing/              # 处理历史 (.history文件)
│   ├── characters/              # 角色管理
│   ├── chapters/                # 章节和画面
│   ├── output/                  # 最终输出
│   └── logs/                    # 日志文件
```

## 开发阶段规划

### Phase 1: 基础框架和模型测试

#### 项目初始化
- 创建项目目录结构
- 配置开发环境 (Python + FastAPI + React)
- 实现文件目录系统API (ProjectFileSystem类)
- 集成豆包Seedream和Qwen-Image-Edit API

#### 模型能力测试
**重点任务**:
- 测试不同模型的文本处理能力 (1000-100000字)
- 确定最佳文本长度和压缩策略
- 建立JSON结构化输出模板和Few-shot示例库
- 验证图像生成质量和一致性
- 记录完整的测试操作日志

**交付物**:
- 模型能力评估报告
- JSON数据结构定义
- Few-shot示例库
- 文件目录系统实现
- API集成测试通过

### Phase 2: 核心Agent开发

#### 文本处理Agent
- **文本分段Agent**: 智能分段，保持情节完整性
- **文本分析Agent**: 角色、场景、情感提取，JSON结构化输出
- **文本压缩LangGraph工作流**: 多轮压缩优化，状态管理
- **连贯性检查Agent**: 验证压缩后的文本质量
- **质量评估Agent**: 决定是否需要重新压缩

#### 漫画生成Agent
- **脚本生成Agent**: 文本→漫画分镜脚本，JSON格式输出
- **角色一致性Agent**: 基于文件系统管理角色参考图
- **画面生成Agent**: 批量并行生成，支持角色一致性
- **场景合成Agent**: 角色+场景合成，风格统一

#### 集成测试
- Agent间JSON数据流测试
- LangGraph工作流状态管理测试
- 文件目录系统集成测试
- 错误处理和重试机制

### Phase 3: 用户界面和交互

#### 前端核心功能
- 项目创建和管理界面
- 文本输入和编辑器
- 漫画生成进度显示
- 图像预览和基础编辑功能
- 文件目录系统的可视化

#### 高级交互功能
- 用户反馈处理LangGraph工作流
- 角色参考图上传和管理
- 批量生成选项和参数调节
- 项目历史时间线展示
- 基于.history文件的版本管理

### Phase 4: 优化和完善

#### 性能优化
- 并发处理优化 (asyncio)
- 本地缓存机制实现
- API调用优化和成本控制
- 图像生成速度提升
- 文件I/O性能优化

#### 用户体验优化
- 界面响应性改进
- 错误提示和用户引导
- 实时生成进度显示
- 移动端适配
- 预览功能完善

#### 测试和部署
- 全面功能测试
- 性能压力测试
- 本地部署配置
- 用户手册编写
- 测试小说跑通完整流程

## 关键技术实现

### 1. JSON结构化输出系统
```python
class BaseAgent:
    def __init__(self, output_schema: dict, fewshot_examples: list):
        self.output_schema = output_schema
        self.fewshot_examples = fewshot_examples

    async def process(self, input_data: Any) -> dict:
        # Few-shot prompting + JSON输出，零解析成本
        pass
```

### 2. 混合编排架构
```python
class ComicGenerator:
    def __init__(self):
        self.text_compressor = TextCompressionWorkflow()  # LangGraph
        self.feedback_handler = FeedbackWorkflow()        # LangGraph
        self.simple_agents = SimpleAgents()               # 普通函数
        self.file_system = ProjectFileSystem()            # 文件系统

    async def generate(self, novel_text: str, project_path: str):
        # 压缩: LangGraph (复杂状态管理)
        compressed = await self.text_compressor.compress(novel_text)

        # 生成: 简单函数 (线性数据流)
        analysis = await self.simple_agents.analyze(compressed)
        script = await self.simple_agents.generate_script(analysis)
        images = await self.simple_agents.batch_generate(script)

        # 保存到文件系统
        await self.file_system.save_results(project_path, images)

        return ComicProject(images)
```

### 3. 文件目录系统
```python
class ProjectFileSystem:
    def create_project(self, project_name: str) -> str:
        """创建新项目目录结构"""
        timestamp = datetime.now().strftime("%Y.%m.%d_%H.%M")
        project_dir = Path(f"projects/{timestamp}_{project_name}")
        # 创建完整目录结构...
        return str(project_dir)

    def save_history(self, project_path: str, history_type: str, data: dict):
        """保存操作历史到.history文件"""
        # 读取-追加-保存历史记录

    def get_project_timeline(self, project_path: str) -> list:
        """获取项目完整时间线"""
        # 扫描所有.history文件构建时间线
```

### 4. Few-shot示例库
```python
# 预定义高质量示例，确保JSON结构化输出
FEWSHOT_EXAMPLES = {
    "text_analysis": [...],
    "comic_script": [...],
    "character_design": [...],
    "scene_composition": [...]
}
```

### 5. 角色一致性系统
- 角色参考图本地存储和管理
- 基于文件路径的角色图片检索
- Few-shot提示确保角色一致性
- 手动角色匹配和调整机制

## 测试策略

### 测试小说选择
- **国内题材**: 《西游记》片段 (奇幻冒险风格)
- **西方题材**: 《冰与火之歌》片段 (现实主义风格)
- **不同长度**: 短篇(1万字)、中篇(5万字)片段测试

### 测试目标
- 验证完整工作流程
- 测试角色一致性
- 评估生成质量和连贯性
- 记录API调用成本
- 优化参数和提示词

## 成功指标

### 技术指标
- API调用成功率 > 95%
- 图像生成时间 < 30秒/张
- 角色一致性准确率 > 80%
- JSON解析成功率 100% (结构化输出保证)
- 文件系统I/O性能 < 100ms

### 用户体验指标
- 完成短篇漫画平均时间 < 2小时
- 用户满意度 > 4.0/5.0
- 重复使用率 > 60%
- 错误率 < 5%

## 预期交付物

1. **完整的Web应用** (前端 + 后端)
2. **源代码和文档** (架构设计 + API文档)
3. **AI模型集成** (豆包Seedream + Qwen-Image-Edit)
4. **文件目录系统** (完整的项目管理)
5. **Few-shot示例库** (JSON结构化输出模板)
6. **测试用例和日志** (完整测试流程记录)
7. **用户手册** (使用指南 + 最佳实践)
8. **两篇测试小说的完整生成记录**

## 风险控制

### 技术风险
- API稳定性: 多模型备选方案
- 成本控制: 优化prompt和缓存策略
- 性能问题: 并发处理和异步优化
- JSON解析: Few-shot确保结构化输出

### 进度风险
- 每周里程碑检查
- 核心功能优先级排序
- 并行开发降低依赖
- 完整操作日志记录

## 项目结构

```
novel-comic-maker/
├── backend/                 # FastAPI后端
│   ├── agents/             # AI Agent实现
│   ├── workflows/          # LangGraph工作流
│   ├── models/             # 数据模型
│   ├── services/           # 业务逻辑
│   └── main.py             # 应用入口
├── frontend/               # React前端
│   ├── src/
│   │   ├── components/     # React组件
│   │   ├── pages/          # 页面组件
│   │   ├── services/       # API调用
│   │   └── utils/          # 工具函数
├── projects/               # 用户项目存储目录
├── docs/                   # 文档
└── README.md              # 项目说明
```
