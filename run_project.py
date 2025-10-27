#!/usr/bin/env python3
"""
项目启动脚本
Project Startup Script

用于快速启动和测试小说生成漫画应用
"""

import os
import sys
import subprocess
import time
import logging
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def check_requirements():
    """检查Python依赖和环境"""
    logger.info("检查Python依赖和环境...")

    # 检查Python版本
    python_version = sys.version_info
    if python_version < (3, 8):
        logger.error(f"Python版本过低: {python_version.major}.{python_version.minor}")
        logger.error("需要Python 3.8或更高版本")
        return False
    logger.info(f"✅ Python版本: {python_version.major}.{python_version.minor}.{python_version.micro}")

    # 检查后端依赖
    backend_requirements = [
        ("fastapi", "fastapi"),
        ("uvicorn", "uvicorn"),
        ("pydantic", "pydantic"),
        ("httpx", "httpx"),
        ("aiofiles", "aiofiles"),
        ("pillow", "PIL"),
        ("langgraph", "langgraph"),
        ("openai", "openai"),
        ("volcengine", "volcenginesdkark")
    ]

    missing_requirements = []
    for req_name, import_name in backend_requirements:
        try:
            __import__(import_name)
        except ImportError:
            missing_requirements.append(req_name)

    if missing_requirements:
        logger.error(f"缺少依赖: {missing_requirements}")
        logger.info("请运行: pip install -r backend/requirements.txt")

        # 提供自动安装选项
        try:
            choice = input("是否自动安装缺少的依赖？(y/n): ").strip().lower()
            if choice == 'y':
                logger.info("正在安装依赖...")
                subprocess.run([sys.executable, "-m", "pip", "install", "-r", "backend/requirements.txt"], check=True)
                logger.info("✅ 依赖安装完成")
            else:
                return False
        except subprocess.CalledProcessError as e:
            logger.error(f"依赖安装失败: {e}")
            return False
        except KeyboardInterrupt:
            logger.info("安装已取消")
            return False

    # 检查Node.js和npm
    try:
        npm_result = subprocess.run(["npm", "--version"], capture_output=True, text=True)
        npm_version = npm_result.stdout.strip()
        logger.info(f"✅ npm版本: {npm_version}")
    except FileNotFoundError:
        logger.warning("⚠️  npm未安装，前端功能可能无法使用")
        logger.info("请安装Node.js和npm: https://nodejs.org/")

    # 检查API密钥配置
    env_file = Path("backend/.env")
    if not env_file.exists():
        logger.warning("⚠️  未找到.env文件，将创建模板")
        setup_environment()
    else:
        # 检查关键环境变量
        with open(env_file, 'r') as f:
            env_content = f.read()

        if 'ARK_API_KEY=' not in env_content or 'your_api_key_here' in env_content:
            logger.warning("⚠️  请在backend/.env中配置ARK_API_KEY")
            logger.info("获取API密钥: https://console.volcengine.com/ark")
        else:
            logger.info("✅ API密钥配置检查通过")

    logger.info("✅ 环境检查完成")
    return True


def setup_environment():
    """设置环境"""
    logger.info("设置环境...")

    # 创建必要的目录
    directories = [
        "projects",
        "backend/logs",
        "temp/images"
    ]

    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)

    # 创建.env文件（如果不存在）
    env_file = Path(".env")
    if not env_file.exists():
        logger.info("创建.env文件...")
        env_example = Path(".env.example")
        if env_example.exists():
            import shutil
            shutil.copy(env_example, env_file)
            logger.info("✅ 已创建.env文件，请填入API密钥")
        else:
            env_file.write_text("# AI模型API密钥配置\n")
            logger.info("✅ 已创建.env文件")

    logger.info("✅ 环境设置完成")


def check_backend_health():
    """检查后端服务健康状态"""
    import socket

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex(('localhost', 8000))
        sock.close()
        return result == 0
    except:
        return False


def start_backend():
    """启动后端服务"""
    logger.info("🚀 启动FastAPI后端服务...")

    # 切换到backend目录
    backend_dir = Path("backend")
    if not backend_dir.exists():
        logger.error("backend目录不存在")
        return None

    # 检查端口是否被占用
    if check_backend_health():
        logger.warning("⚠️  端口8000已被占用")
        try:
            choice = input("是否停止占用进程并重新启动？(y/n): ").strip().lower()
            if choice == 'y':
                # 尝试停止占用进程
                subprocess.run(["pkill", "-f", "uvicorn.*8000"], capture_output=True)
                time.sleep(2)
            else:
                logger.info("使用现有后端服务")
                return None
        except:
            pass

    original_dir = os.getcwd()
    os.chdir(backend_dir)

    try:
        # 启动uvicorn服务器
        process = subprocess.Popen([
            sys.executable, "-m", "uvicorn",
            "main:app",
            "--host", "0.0.0.0",
            "--port", "8000",
            "--reload",
            "--log-level", "info"
        ], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

        # 等待服务启动并检查健康状态
        logger.info("等待后端服务启动...")
        for i in range(10):  # 最多等待10秒
            time.sleep(1)
            if process.poll() is not None:
                stdout, _ = process.communicate()
                logger.error(f"后端服务启动失败: {stdout}")
                return None

            if check_backend_health():
                logger.info("✅ 后端服务启动成功")
                logger.info("📍 API地址: http://localhost:8000")
                logger.info("📖 API文档: http://localhost:8000/docs")
                logger.info("🏥 健康检查: http://localhost:8000/health")
                return process

        logger.error("❌ 后端服务启动超时")
        process.terminate()
        return None

    except Exception as e:
        logger.error(f"启动后端服务失败: {e}")
        return None
    finally:
        # 切换回原目录
        os.chdir(original_dir)


def check_frontend_health():
    """检查前端服务健康状态"""
    import socket

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex(('localhost', 3000))
        sock.close()
        return result == 0
    except:
        return False


def start_frontend():
    """启动前端服务"""
    logger.info("🎨 启动React前端服务...")

    # 切换到frontend目录
    original_dir = os.getcwd()
    frontend_dir = Path("frontend")
    if not frontend_dir.exists():
        logger.error("frontend目录不存在")
        return None

    os.chdir(frontend_dir)

    try:
        # 检查package.json是否存在
        if not Path("package.json").exists():
            logger.error("package.json不存在，请确保在正确的前端项目目录中")
            os.chdir(original_dir)
            return None

        # 检查Node.js是否可用
        try:
            subprocess.run(["npm", "--version"], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            logger.error("❌ npm不可用，请安装Node.js和npm")
            logger.info("下载地址: https://nodejs.org/")
            os.chdir(original_dir)
            return None

        # 检查端口是否被占用
        if check_frontend_health():
            logger.warning("⚠️  端口3000已被占用")
            try:
                choice = input("是否停止占用进程并重新启动？(y/n): ").strip().lower()
                if choice == 'y':
                    # 尝试停止占用进程
                    subprocess.run(["pkill", "-f", "react-scripts.*3000"], capture_output=True)
                    time.sleep(2)
                else:
                    logger.info("使用现有前端服务")
                    os.chdir(original_dir)
                    return None
            except:
                pass

        # 检查node_modules是否存在
        if not Path("node_modules").exists():
            logger.info("📦 安装前端依赖...")
            try:
                result = subprocess.run(["npm", "install"], capture_output=True, text=True, timeout=300)
                if result.returncode == 0:
                    logger.info("✅ 前端依赖安装完成")
                else:
                    logger.error(f"安装前端依赖失败: {result.stderr}")
                    os.chdir(original_dir)
                    return None
            except subprocess.TimeoutExpired:
                logger.error("依赖安装超时，请手动运行: cd frontend && npm install")
                os.chdir(original_dir)
                return None
            except Exception as e:
                logger.error(f"安装前端依赖失败: {e}")
                os.chdir(original_dir)
                return None

        # 启动React开发服务器
        logger.info("启动React开发服务器...")
        process = subprocess.Popen([
            "npm", "start"
        ], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

        # 等待服务启动并检查健康状态
        logger.info("等待前端服务启动...")
        for i in range(15):  # 最多等待15秒
            time.sleep(1)
            if process.poll() is not None:
                stdout, _ = process.communicate()
                logger.error(f"前端服务启动失败: {stdout}")
                os.chdir(original_dir)
                return None

            if check_frontend_health():
                logger.info("✅ 前端服务启动成功")
                logger.info("🌐 前端地址: http://localhost:3000")
                return process

        logger.error("❌ 前端服务启动超时")
        process.terminate()
        os.chdir(original_dir)
        return None

    except Exception as e:
        logger.error(f"启动前端服务失败: {e}")
        os.chdir(original_dir)
        return None


def show_status():
    """显示项目状态"""
    logger.info("📊 项目状态:")
    logger.info("🎯 小说生成漫画应用")
    logger.info("🏗️  架构: FastAPI + React + AI")
    logger.info("🤖 AI模型: 豆包Seedream")
    logger.info("💾 存储: 文件目录系统")
    logger.info("")
    logger.info("📋 可用功能:")
    logger.info("  ✅ 项目创建和管理")
    logger.info("  ✅ 文本分析和分段")
    logger.info("  ✅ 漫画脚本生成")
    logger.info("  ✅ 图像生成和编辑")
    logger.info("  ✅ 角色一致性管理")
    logger.info("  ✅ 项目历史记录")
    logger.info("")
    logger.info("🔧 下一步:")
    logger.info("  1. 在backend/.env中配置AI模型API密钥")
    logger.info("  2. 访问http://localhost:8000/docs测试API")
    logger.info("  3. 访问http://localhost:3000使用Web界面")


def main():
    """主函数"""
    print("🎨 小说生成漫画应用 - 启动脚本")
    print("=" * 50)

    # 检查依赖
    if not check_requirements():
        return

    # 设置环境
    setup_environment()

    # 显示状态
    show_status()

    # 询问用户启动方式
    print("\n请选择启动方式:")
    print("1. 仅启动后端服务 (FastAPI)")
    print("2. 仅启动前端服务 (React)")
    print("3. 同时启动前后端服务")
    print("4. 仅检查环境")

    try:
        choice = input("\n请输入选择 (1-4): ").strip()
    except KeyboardInterrupt:
        logger.info("\n👋 启动已取消")
        return

    processes = []

    try:
        if choice == "1":
            process = start_backend()
            if process:
                processes.append(process)
                logger.info("✅ 后端服务已启动，按Ctrl+C停止")

        elif choice == "2":
            process = start_frontend()
            if process:
                processes.append(process)
                logger.info("✅ 前端服务已启动，按Ctrl+C停止")

        elif choice == "3":
            backend_process = start_backend()
            if backend_process:
                processes.append(backend_process)

                # 等待后端完全启动
                time.sleep(2)

                frontend_process = start_frontend()
                if frontend_process:
                    processes.append(frontend_process)
                    logger.info("✅ 前后端服务已启动，按Ctrl+C停止")
                else:
                    logger.warning("前端服务启动失败")

        elif choice == "4":
            logger.info("✅ 环境检查完成")
            return

        else:
            logger.error("❌ 无效选择")
            return

        # 等待用户中断
        if processes:
            print("\n按Ctrl+C停止所有服务...")
            while True:
                time.sleep(1)
                # 检查进程是否还在运行
                for i, process in enumerate(processes):
                    if process.poll() is not None:
                        logger.warning(f"进程 {i} 已意外停止")

    except KeyboardInterrupt:
        logger.info("\n🛑 正在停止服务...")

    finally:
        # 停止所有进程
        for process in processes:
            try:
                process.terminate()
                process.wait(timeout=5)
            except:
                try:
                    process.kill()
                except:
                    pass

        logger.info("✅ 所有服务已停止")


if __name__ == "__main__":
    main()