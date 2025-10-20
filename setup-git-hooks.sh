#!/bin/bash
# Git Hooks 安装脚本
# 用于自动配置项目Git Hooks

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 项目信息
PROJECT_NAME="novel-comic-maker"
HOOKS_DIR=".git/hooks"
BACKUP_DIR=".git/hooks.backup"

echo -e "${CYAN}🚀 Git Hooks 安装脚本${NC}"
echo -e "${CYAN}================================${NC}"
echo -e "${BLUE}📁 项目: $PROJECT_NAME${NC}"
echo ""

# 检查是否在Git仓库中
if [[ ! -d ".git" ]]; then
    echo -e "${RED}❌ 错误: 当前目录不是Git仓库！${NC}"
    echo -e "${YELLOW}💡 请在项目根目录运行此脚本${NC}"
    exit 1
fi

# 创建备份目录
echo -e "${BLUE}📦 创建现有hooks备份...${NC}"
if [[ -d "$HOOKS_DIR" ]]; then
    mkdir -p "$BACKUP_DIR"
    cp -r "$HOOKS_DIR"/*.sample "$BACKUP_DIR/" 2>/dev/null || true
    echo -e "${GREEN}✅ 备份完成: $BACKUP_DIR${NC}"
fi

# 设置执行权限
echo -e "\n${BLUE}🔧 设置Hooks执行权限...${NC}"
chmod +x "$HOOKS_DIR/commit-msg"
chmod +x "$HOOKS_DIR/pre-commit"
echo -e "${GREEN}✅ 权限设置完成${NC}"

# 验证hooks文件
echo -e "\n${BLUE}🔍 验证Hooks文件...${NC}"

hooks=("commit-msg" "pre-commit")
for hook in "${hooks[@]}"; do
    hook_file="$HOOKS_DIR/$hook"
    if [[ -f "$hook_file" && -x "$hook_file" ]]; then
        echo -e "${GREEN}✅ $hook: 安装成功${NC}"
    else
        echo -e "${RED}❌ $hook: 安装失败${NC}"
        exit 1
    fi
done

# 测试commit-msg hook
echo -e "\n${BLUE}🧪 测试Commit消息检查...${NC}"
test_commit_msg="feat(test): 测试commit消息格式"
echo "$test_commit_msg" | "$HOOKS_DIR/commit-msg" /dev/stdin
if [[ $? -eq 0 ]]; then
    echo -e "${GREEN}✅ commit-msg hook: 测试通过${NC}"
else
    echo -e "${RED}❌ commit-msg hook: 测试失败${NC}"
    exit 1
fi

# 显示已安装的hooks
echo -e "\n${PURPLE}📋 已安装的Git Hooks:${NC}"
echo ""

echo -e "${CYAN}1️⃣ commit-msg${NC}"
echo -e "   功能: 检查commit消息格式"
echo -e "   规范: <type>(<scope>): <subject>"
echo -e "   示例: feat(workflow): 添加文本压缩工作流"
echo ""

echo -e "${CYAN}2️⃣ pre-commit${NC}"
echo -e "   功能: 提交前代码质量检查"
echo -e "   检查项:"
echo -e "     • Python语法检查"
echo -e "     • JavaScript/TypeScript检查"
echo -e "     • 大文件警告 (>5MB)"
echo -e "     • 敏感文件检测"
echo -e "     • API密钥检查"
echo -e "     • TODO注释提醒"
echo ""

# 创建Git配置建议
echo -e "\n${BLUE}⚙️  Git配置建议:${NC}"
echo ""

echo -e "${YELLOW}设置用户信息:${NC}"
echo "git config user.name '你的名字'"
echo "git config user.email '你的邮箱'"
echo ""

echo -e "${YELLOW}设置默认编辑器:${NC}"
echo "git config core.editor 'code --wait'  # VS Code"
echo "# 或者"
echo "git config core.editor 'nano'         # Nano"
echo "# 或者"
echo "git config core.editor 'vim'          # Vim"
echo ""

echo -e "${YELLOW}设置默认分支名:${NC}"
echo "git config init.defaultBranch 'main'"
echo ""

# 使用示例
echo -e "\n${PURPLE}📝 使用示例:${NC}"
echo ""

echo -e "${GREEN}正确的commit格式:${NC}"
echo -e "${CYAN}feat(workflow): 添加LangGraph工作流系统${NC}"
echo -e "${CYAN}fix(image): 修复base64编码问题${NC}"
echo -e "${CYAN}docs(api): 更新Swagger文档说明${NC}"
echo -e "${CYAN}refactor(agent): 重构文本分析Agent${NC}"
echo -e "${CYAN}test(phase2): 添加第二阶段功能测试${NC}"
echo ""

echo -e "${RED}错误的commit格式:${NC}"
echo -e "${RED}fix bug${NC}"
echo -e "${RED}update code${NC}"
echo -e "${RED}feat: 添加了一个新功能来处理图像，这个功能很重要${NC}"
echo ""

# 测试命令
echo -e "\n${BLUE}🧪 测试命令:${NC}"
echo ""
echo -e "${YELLOW}测试commit格式:${NC}"
echo "git commit -m 'feat(test): 这是一个测试commit'"
echo ""

echo -e "${YELLOW}跳过hooks检查（紧急情况）:${NC}"
echo "git commit --no-verify -m 'emergency fix'"
echo ""

echo -e "${YELLOW}查看hooks日志:${NC}"
echo "# hooks会在终端显示检查过程和结果"
echo ""

# 卸载说明
echo -e "\n${PURPLE}🗑️  卸载Hooks:${NC}"
echo ""
echo -e "${YELLOW}如需卸载hooks，运行:${NC}"
echo "rm .git/hooks/commit-msg"
echo "rm .git/hooks/pre-commit"
echo "恢复备份: cp .git/hooks.backup/* .git/hooks/"
echo ""

# 完成
echo -e "\n${GREEN}🎉 Git Hooks 安装完成！${NC}"
echo -e "${GREEN}现在每次commit都会自动检查格式和代码质量${NC}"
echo ""
echo -e "${BLUE}💡 提示: 首次使用可能会有些不习惯，但有助于保持代码质量${NC}"
echo -e "${BLUE}📚 详细规范请参考: COMMIT_GUIDELINES.md${NC}"
echo ""