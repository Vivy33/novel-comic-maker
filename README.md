# 小说生成漫画应用

一个基于AI的小说转漫画生成应用，采用Human-in-the-loop理念，支持用户调整AI生成的漫画内容，通过动作编辑、画风滤镜、人物一致性机制降低抽卡成本。
Demo视频演示：https://zhuanlan.zhihu.com/p/1966151196050972952

## 用户分析与痛点

### 目标用户群体

1. **专业用户**: 长期或专业画漫画的用户，需要提高创作效率
2. **业余用户**: 心血来潮想要创作漫画的新手，缺乏绘画技能
3. **网络写手/签约作者**: 有小说内容但缺乏时间和精力来制作漫画

### 核心痛点

- **抽卡困难**: 频繁生成不符合用户预期的图片，成本高昂
- **角色一致性**: 漫画中人物形象不统一，影响观感
- **剧情连贯性**: 长文本理解困难，缺乏前情提要机制
- **技术门槛**: 不熟悉画画的用户难以快速上手创作漫画

### 用户故事

- 作为网络小说作者，我希望能够快速将我的小说转化为漫画，吸引更多读者
- 作为漫画爱好者，我希望能够创作自己的漫画作品，即使我不擅长绘画
- 作为专业漫画家，我希望AI能够辅助我提高创作效率，让我专注于创意本身

## 项目特色

- **🤖 AI驱动**: 智能分析小说内容并生成高质量漫画
- **🎨 人工在环**: 支持用户预览和调整AI生成的漫画内容，确保创作符合预期
- **👥 角色一致性**: 用户可生成角色卡，确保漫画中人物形象的一致性
- **📖 剧情连贯**: 前情提要系统，处理长文本理解问题
- **⚡ 快速上手**: 为不熟悉画画的用户提供直观的创作工具和界面

## 技术挑战与应对策略

### 主要技术挑战

1. **抽卡效率问题**: AI生成图片的随机性导致用户需要频繁重试
2. **长文本处理**: 小说文本通常很长，超出模型上下文窗口限制
3. **角色一致性**: 确保同一角色在不同画面中保持一致的外观
4. **剧情连贯性**: 保证漫画分镜之间的逻辑连贯性

### 应对策略

1. **批量生成与随机性控制**
   - 一次生成多个候选图片，提高成功率
   - 调高模型温度参数(≥0.7)增加多样性
   - 提供模板化的风格选择(男女频、热血漫、推理漫等)

2. **分层文本处理**
   - 采用多级压缩策略：前情提要summary < 分段生成文本 < 本章summary
   - 智能文本分段，通常1万字对应20页漫画
   - 使用结构化输出格式，减少解析成本

3. **角色管理系统**
   - 主角图片参考系统，避免角色形象偷换
   - 基于参考图片的一致性生成
   - 支持用户上传自定义角色图片

4. **人工在环编辑**
   - AI图像编辑功能
   - 场景拼接和合成工具
   - 预览和完整的漫画预览功能

## AI模型选型对比

### 模型选择考量

在选择AIGC模型时，主要考虑以下因素：
- 推理成本效益(偏向一次推理，多次访问)
- 图像质量和风格一致性
- API稳定性和服务可用性
- 技术支持能力

### 选型决策

**主要选择**: 豆包Seedream (火山引擎)
- **优势**: 中文理解能力强，适合中文小说处理；成本效益高；服务稳定
- **应用场景**: 文生图、图生图的主要生成引擎

**辅助选择**:
- **Seedream-edit**: 图像编辑和PS功能
- **Nano Banana**: 高级图像处理
- **StepFun**: 备选生成模型

**未选择国外模型的原因**:
- 虽然有出海需求，但当前主要面向中文用户市场
- 国外模型在中文理解和文化表达上存在局限性
- 考虑数据合规和传输成本

### 技术架构

- **后端**: FastAPI + Python (异步处理)
- **前端**: React + TypeScript + Material-UI
- **AI编排**: 混合策略 (LangGraph用于复杂流程，简单函数用于线性流程)
- **AI模型**: 豆包Seedream (主要)
- **存储**: 文件目录系统 (无数据库，无向量数据库，无OSS)
- **工作流**: 前情提要 + 文本分段 + 脚本生成 + 图像生成 + 角色一致性检查

## 快速开始

### 环境要求

- Python 3.8+
- Node.js 16+
- npm 或 yarn
- 火山引擎 API密钥（必需）
- OpenAI API密钥（可选）

### 首次部署步骤

1. **克隆项目**
```bash
git clone <repository-url>
cd novel-comic-maker
```

2. **安装Python依赖**
```bash
# 建议使用虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装后端依赖
pip install -r backend/requirements.txt
```

3. **配置API密钥**
```bash
# 复制环境变量模板
cp .env.example backend/.env

# 编辑配置文件，填入您的API密钥
nano backend/.env  # 或使用其他编辑器
```

**重要**: 必须配置以下环境变量：
```bash
# 火山方舟 API配置 (必需)
ARK_API_KEY=your_volcengine_api_key_here
VOLCENGINE_REGION=cn-beijing

# OpenAI API配置 (可选，作为备选)
OPENAI_API_KEY=your_openai_api_key_here

# 应用配置
DEBUG=false
HOST=0.0.0.0
PORT=8000
LOG_LEVEL=INFO
```

4. **启动应用**

使用快速启动脚本（推荐）：
```bash
python run_project.py
```

脚本会自动：
- 检查Python依赖
- 创建必要的目录结构
- 提供交互式启动选项

或手动启动：
```bash
# 启动后端 (终端1)
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 启动前端 (终端2)
cd frontend
npm install
npm start
```

5. **验证部署**
- 前端界面: http://localhost:3000
- API文档: http://localhost:8000/docs
- 健康检查: http://localhost:8000/health

### 常见问题排查

**问题1: 缺少Python依赖**
```bash
# 解决方案
pip install -r backend/requirements.txt
```

**问题2: API密钥配置错误**
- 确保在 `backend/.env` 中正确配置了 `ARK_API_KEY`
- 检查API密钥是否有效且有足够权限

**问题3: 端口被占用**
```bash
# 查看端口占用
lsof -i :8000  # 后端端口
lsof -i :3000  # 前端端口

# 杀死占用进程
kill -9 <PID>
```

**问题4: 前端依赖安装失败**
```bash
# 清理缓存重试
cd frontend
rm -rf node_modules package-lock.json
npm install
```

**问题5: 后端启动失败**
```bash
# 查看详细错误日志
cd backend
uvicorn main:app --reload --log-level debug
```

## 功能特性

### 核心功能

- ✅ **项目管理**: 创建、管理和导出漫画项目
- ✅ **文本处理**: 智能分段、分析和压缩小说文本
- ✅ **漫画生成**: 基于文本自动生成漫画分镜脚本
- ✅ **图像生成**: 批量并行生成漫画画面
- ✅ **角色管理**: 角色卡片生成和一致性管理
- ✅ **封面生成**: 自动生成精美的漫画封面
- ✅ **图像编辑**: 基础的图像编辑和滤镜功能
- ✅ **历史记录**: 完整的项目操作历史和版本管理

### 前端页面

- **首页**: 项目概览和快速创建
- **项目管理**: 项目列表、创建和管理
- **漫画生成**: 文本输入和漫画生成流程
- **角色管理**: 角色卡片生成和管理
- **图像编辑**: 图像编辑和滤镜处理
- **工作流编排**: AI工作流的自定义配置

### API路由

- `/projects/` - 项目管理
- `/comics/` - 漫画生成和管理
- `/characters/` - 角色管理
- `/image-edit/` - 图像编辑
- `/workflows/` - 工作流编排

## 项目结构

```
novel-comic-maker/
├── backend/                 # FastAPI后端
│   ├── agents/             # AI Agent实现
│   │   ├── text_segmenter.py        # 文本分段
│   │   ├── text_analyzer.py         # 文本分析
│   │   ├── script_generator.py      # 脚本生成
│   │   ├── image_generator.py       # 图像生成
│   │   ├── character_consistency_agent.py  # 角色一致性
│   │   └── cover_generator.py       # 封面生成
│   ├── models/             # 数据模型
│   ├── routers/            # API路由
│   ├── services/           # 业务逻辑
│   ├── workflows/          # LangGraph工作流
│   ├── utils/              # 工具函数
│   ├── main.py            # 应用入口
│   └── config.py          # 配置文件
├── frontend/               # React前端
│   ├── src/
│   │   ├── components/     # React组件
│   │   ├── pages/          # 页面组件
│   │   ├── services/       # API调用
│   │   └── utils/          # 工具函数
├── projects/               # 用户项目存储目录
├── docs/                   # 项目文档
├── run_project.py         # 快速启动脚本
└── README.md              # 项目说明
```

## 开发指南

### 常用命令

```bash
# 快速启动 (推荐)
python run_project.py

# 后端开发
cd backend && uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 前端开发
cd frontend && npm start

# 依赖管理
pip install -r backend/requirements.txt
cd frontend && npm install

# 代码质量
cd frontend && npm run lint
cd frontend && npm run format
```

### 环境配置

必需的环境变量：
```bash
# 火山方舟 API配置
ARK_API_KEY=your_api_key_here
VOLCENGINE_REGION=cn-beijing

# OpenAI API配置 (可选)
OPENAI_API_KEY=your_openai_api_key_here

# 应用配置
DEBUG=false
HOST=0.0.0.0
PORT=8000
```

### 测试

```bash
# 后端测试
cd backend && python -m pytest test/

# 前端测试
cd frontend && npm test
```

## 部署说明

### 本地部署

1. 配置所有必需的环境变量
2. 确保Python和Node.js依赖已安装
3. 运行 `python run_project.py` 选择启动方式
4. 访问 http://localhost:3000 使用应用

### 生产部署注意事项

- 确保所有环境变量已正确配置
- 检查文件系统权限
- 配置反向代理 (如需要)
- 设置适当的CORS策略

## 未来功能规划

### 短期规划 (3-6个月)

1. **语音合成系统**
   - 录入用户声音，生成角色语音模板
   - 支持多种语言和方言
   - 语音辨识度和连贯性优化

2. **动态漫画功能**
   - 简单的动画效果
   - 配合语音的自动播放
   - 交互式阅读体验

3. **素材库系统**
   - 向量数据库存储和管理素材
   - 智能素材检索和推荐
   - 用户自定义素材上传

### 中期规划 (6-12个月)

1. **多智能体协作系统**
   - 使用ReAct框架让多个AI智能体讨论并优化输出
   - 自动化的质量评估和改进循环
   - 智能化的创作建议

2. **高级图像处理**
   - 集成更多专业级图像编辑工具
   - 画风迁移和风格滤镜
   - 高级场景合成和特效

3. **跨平台支持**
   - 移动端应用开发
   - 云端协作功能
   - 社区分享平台

### 长期规划 (1-2年)

1. **AI辅助创意工具**
   - 智能剧情建议和优化
   - 自动化的分镜脚本生成
   - 创意灵感推荐系统

2. **国际化支持**
   - 多语言文本处理
   - 不同文化风格的适配
   - 海外市场本地化

3. **商业化功能**
   - 作品发布和版权管理
   - 商业合作平台
   - 收益分成系统

### 功能重要性分析

这些功能之所以重要，是因为：
- **提升用户体验**: 语音和动态效果让漫画更加生动
- **降低创作门槛**: 素材库和AI协作让创作更容易
- **增强竞争力**: 差异化功能在市场中脱颖而出
- **扩展商业模式**: 从工具向平台生态发展

## 核心设计理念

### Human-in-the-loop (人工在环)

所有AI生成的内容都强调用户的参与和控制：
- 每个生成步骤都可以预览和调整
- 支持用户上传自己的图片和修改AI生成结果
- 完整的漫画预览功能，确保最终效果符合预期

### 成本效益优先

- 采用文件目录系统而非复杂的数据库架构
- 选择性价比高的AI模型和服务
- 智能的Token使用统计和优化

### 质量保证机制

- 多轮生成和质量评估
- 角色一致性检查
- 剧情连贯性验证
- 用户反馈循环优化

## 支持

如有问题或建议，请：
- 提交 [Issue](../../issues)
- 查看 [API文档](http://localhost:8000/docs)
- 阅读项目文档
