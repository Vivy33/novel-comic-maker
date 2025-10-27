"""
小说生成漫画应用 - 主启动文件
Novel to Comic Maker - Main Startup File
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from contextlib import asynccontextmanager
import logging
import sys
import asyncio
from pathlib import Path
import os
from dotenv import load_dotenv

# 添加Request导入
from fastapi import Request

# 加载环境变量 - 确保使用根目录的.env文件
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info("启动小说生成漫画应用后端服务...")
    logger.info("Phase 2 功能已完成，基础服务运行中")

    # 检查.env文件配置
    from config import settings
    logger.info("检查环境变量配置...")

    # 如果.env文件不存在，尝试创建
    if not (Path(__file__).parent.parent / ".env").exists():
        logger.info("首次部署检测到，尝试创建.env配置文件...")
        if settings.ensure_env_file():
            logger.info(".env文件已创建，请编辑后重启服务以应用配置")
        else:
            logger.warning("无法自动创建.env文件，请手动创建")
    else:
        # 配置检查已在settings初始化时执行
        logger.info("环境变量配置检查完成")

    # 启动临时文件清理任务
    cleanup_task = None
    try:
        # 导入清理函数
        from routers.image_edit import cleanup_temp_files, periodic_cleanup

        # 启动后台清理任务
        cleanup_task = asyncio.create_task(periodic_cleanup())
        logger.info("临时文件定期清理任务已启动")

    except Exception as e:
        logger.warning(f"启动清理任务失败: {e}")

    try:
        yield
    finally:
        logger.info("关闭小说生成漫画应用后端服务...")

        # 停止清理任务
        if cleanup_task:
            cleanup_task.cancel()
            try:
                await cleanup_task
            except asyncio.CancelledError:
                pass
            logger.info("临时文件清理任务已停止")


# 创建FastAPI应用实例
app = FastAPI(
    title="小说生成漫画应用 API",
    description="Novel to Comic Maker API - 将小说转换为漫画的AI服务",
    version="2.0.0",
    lifespan=lifespan
)

# 全局异常处理器
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc: RequestValidationError):
    """处理FastAPI的请求验证错误"""
    logger.error(f"FastAPI请求验证错误: {exc.errors()}")
    logger.error(f"请求URL: {request.url}")
    logger.error(f"请求方法: {request.method}")

    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "detail": "请求参数验证失败",
            "errors": exc.errors(),
            "error_details": [
                {
                    "field": error['loc'][-1] if error['loc'] else 'unknown',
                    "message": error['msg'],
                    "type": error['type']
                }
                for error in exc.errors()
            ]
        }
    )

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request, exc: StarletteHTTPException):
    """处理HTTP异常"""
    logger.error(f"HTTP异常: {exc.status_code} - {exc.detail}")
    logger.error(f"请求URL: {request.url}")

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "detail": exc.detail,
            "error_type": "HTTP异常"
        }
    )

# 配置CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===== 注册API路由 =====
from routers.projects import router as projects_router
from routers.comics import router as comics_router
from routers.characters import router as characters_router
from routers.image_edit import router as image_edit_router
try:
    from routers.workflows import router as workflows_router
    logger.info("工作流路由加载成功")
except Exception as e:
    logger.warning(f"工作流路由加载失败: {e}")
    workflows_router = None
try:
    from routers.text2image import router as text2image_router
except Exception:
    text2image_router = None
try:
    from routers.context_management import router as context_router
except Exception:
    context_router = None

# 将路由挂载到应用
app.include_router(projects_router)
app.include_router(comics_router)
app.include_router(characters_router)
app.include_router(image_edit_router)
if workflows_router:
    app.include_router(workflows_router)
if text2image_router:
    app.include_router(text2image_router)
if context_router:
    app.include_router(context_router)

# 配置静态文件服务
try:
    from config import settings
    projects_dir = Path(settings.PROJECTS_DIR)
    if projects_dir.exists():
        app.mount("/projects", StaticFiles(directory=str(projects_dir)), name="projects")
        logger.info(f"静态文件服务已挂载: /projects -> {projects_dir}")
    else:
        logger.warning(f"项目目录不存在: {projects_dir}")
except Exception as e:
    logger.warning(f"静态文件服务配置失败: {e}")
    # 使用默认路径
    projects_dir = Path(__file__).parent.parent / "projects"
    if projects_dir.exists():
        app.mount("/projects", StaticFiles(directory=str(projects_dir)), name="projects")
        logger.info(f"静态文件服务已挂载(默认路径): /projects -> {projects_dir}")


# TODO: [VULTURE] Flagged as unused. User wants to keep for now, but consider for future removal.
@app.get("/")
async def root():
    """根路径健康检查"""
    return {
        "message": "小说生成漫画应用 API 服务正在运行",
        "status": "healthy",
        "version": "2.0.0",
        "phase2_status": "completed",
        "note": "基础服务运行中，部分功能可能需要额外依赖"
    }


@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {"status": "healthy"}


# TODO: [VULTURE] Flagged as unused. User wants to keep for now, but consider for future removal.
@app.get("/test/basic")
async def test_basic():
    """基础测试接口"""
    return {
        "message": "基础测试成功",
        "status": "running",
        "features": {
            "basic_api": True,
            "phase1_completed": True,
            "phase2_implemented": True
        }
    }


@app.get("/test/status")
async def test_status():
    """测试系统状态"""
    try:
        # 检查项目目录结构（backend 下）
        required_dirs = [
            "backend/agents",
            "backend/models",
            "backend/routers",
            "backend/services",
            "backend/workflows",
            "backend/utils"
        ]
        dir_status = {}

        for dir_name in required_dirs:
            dir_path = Path(dir_name)
            dir_status[dir_name] = {
                "exists": dir_path.exists(),
                "is_dir": dir_path.is_dir() if dir_path.exists() else False
            }

        # 检查核心文件
        core_files = [
            "backend/main.py",
            "test/test_phase1_features.py",
            "test/test_phase2_features.py",
            "backend/requirements.txt"
        ]

        file_status = {}
        for file_name in core_files:
            file_path = Path(file_name)
            file_status[file_name] = file_path.exists()

        return {
            "system_status": "running",
            "directory_status": dir_status,
            "file_status": file_status,
            "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "phase1_complete": True,
            "phase2_complete": True
        }
    except Exception as e:
        return {
            "system_status": "error",
            "error": str(e)
        }


# TODO: [VULTURE] Flagged as unused. User wants to keep for now, but consider for future removal.
@app.get("/test/dependencies")
async def test_dependencies():
    """测试依赖状态"""
    dependencies = {
        "fastapi": False,
        "pydantic": False,
        "uvicorn": False,
        "langgraph": False,
        "langchain": False,
        "openai": False,
        "pillow": False
    }

    for dep in dependencies:
        try:
            __import__(dep)
            dependencies[dep] = True
        except ImportError:
            pass

    return {
        "dependencies": dependencies,
        "missing": [dep for dep, status in dependencies.items() if not status]
    }


# 简化版启动逻辑
if __name__ == "__main__":
    import uvicorn

    print("=" * 60)
    print("🚀 启动小说生成漫画应用")
    print("=" * 60)
    print("📍 服务地址: http://localhost:8000")
    print("📖 API文档: http://localhost:8000/docs")
    print("🧪 系统测试: http://localhost:8000/test/status")
    print("🔍 依赖检查: http://localhost:8000/test/dependencies")
    print("=" * 60)
    print("📝 当前状态:")
    print("   ✅ Phase 1: 基础框架 - 已完成")
    print("   ✅ Phase 2: 高级功能 - 已完成")
    print("   ✅ 基础API: 可用")
    print("   ⚠  高级功能: 需要额外依赖")
    print("=" * 60)
    print("📝 启动方式:")
    print("   基础功能: 已启动")
    print("   高级功能: 需要安装额外依赖包")
    print("   完整功能: pip install -r requirements.txt && python main_full.py")
    print("=" * 60)

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )