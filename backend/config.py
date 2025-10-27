"""
小说生成漫画应用 - 配置文件
Novel to Comic Maker - Configuration
"""

import os
from pathlib import Path
from typing import Optional
import logging

# 配置日志
logger = logging.getLogger(__name__)

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent
BACKEND_ROOT = Path(__file__).parent

# 权威.env文件路径
AUTH_ENV_PATH = PROJECT_ROOT / ".env"
ENV_EXAMPLE_PATH = PROJECT_ROOT / ".env.example"
BACKUP_ENV_PATHS = [
    BACKEND_ROOT / ".env",
    PROJECT_ROOT / ".env.local",
    PROJECT_ROOT / ".env.production"
]

# 基础配置
class Settings:
    """应用配置类"""

    # 应用基础信息
    APP_NAME: str = "小说生成漫画应用"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"

    # 服务器配置
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))

    # 项目存储配置
    PROJECTS_DIR: Path = PROJECT_ROOT / "projects"
    TEMP_DIR: Path = PROJECT_ROOT / "temp"
    LOGS_DIR: Path = PROJECT_ROOT / "logs"

    # 临时文件子目录
    TEMP_UPLOADS_DIR: Path = TEMP_DIR / "uploads"
    TEMP_DOWNLOADS_DIR: Path = TEMP_DIR / "downloads"
    TEMP_PROCESSING_DIR: Path = TEMP_DIR / "processing"

    # 缓存目录
    CACHE_DIR: Path = PROJECT_ROOT / "cache"
    CACHE_AI_IMAGES_DIR: Path = CACHE_DIR / "ai_images"

    # 文件上传配置
    MAX_FILE_SIZE: int = int(os.getenv("MAX_FILE_SIZE", "10485760"))  # 10MB
    ALLOWED_IMAGE_TYPES: list = ["image/jpeg", "image/png", "image/gif", "image/webp"]
    ALLOWED_TEXT_TYPES: list = ["text/plain", "text/markdown"]

    # AI 服务配置
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    VOLCENGINE_ACCESS_KEY: Optional[str] = os.getenv("VOLCENGINE_ACCESS_KEY")
    VOLCENGINE_SECRET_KEY: Optional[str] = os.getenv("VOLCENGINE_SECRET_KEY")
    VOLCENGINE_REGION: str = os.getenv("VOLCENGINE_REGION", "cn-beijing")

    # 数据库配置（如果需要）
    DATABASE_URL: Optional[str] = os.getenv("DATABASE_URL")

    # Redis 配置（如果需要缓存）
    REDIS_URL: Optional[str] = os.getenv("REDIS_URL")

    # 日志配置
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # CORS 配置
    ALLOWED_ORIGINS: list = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",  # Vite 默认端口
        "http://127.0.0.1:5173"
    ]

    # 安全配置
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

    # 缓存配置
    CACHE_CONFIG: dict = {
        # 文本分析缓存：30分钟，最多100个条目
        'text_analysis': {
            'ttl': 1800,        # 30分钟缓存
            'max_size': 100     # 最大条目数
        },

        # API响应缓存：5分钟，最多500个条目
        'api_responses': {
            'ttl': 300,         # 5分钟缓存
            'max_size': 500     # 最大条目数
        },

        # 图片缓存：24小时，最多50个条目
        'images': {
            'ttl': 86400,       # 24小时缓存
            'max_size': 50      # 最大条目数
        }
    }

    # 缓存类型映射
    CACHE_TYPE_MAPPING: dict = {
        # 文本分析相关
        'text_compress': 'text_analysis',
        'text_analysis': 'text_analysis',
        'character_analysis': 'text_analysis',

        # API调用相关
        'api_response': 'api_responses',
        'api_call': 'api_responses',
        'image_generation': 'api_responses',

        # 文件存储相关
        'image': 'images',
        'file': 'images'
    }

    def __init__(self):
        """初始化配置，创建必要的目录"""
        self._check_env_files()
        self._create_directories()

    def _create_directories(self):
        """创建必要的目录"""
        directories = [
            self.PROJECTS_DIR,
            self.TEMP_DIR,
            self.LOGS_DIR
        ]

        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)

    def _check_env_files(self):
        """检查.env文件配置，确保使用权威配置文件"""
        # 检查权威.env文件是否存在
        if not AUTH_ENV_PATH.exists():
            logger.warning(f"权威.env文件不存在: {AUTH_ENV_PATH}")

            # 尝试从.env.example复制模板
            if ENV_EXAMPLE_PATH.exists():
                logger.info(f"发现.env.example模板文件: {ENV_EXAMPLE_PATH}")
                logger.info("建议复制模板文件创建.env配置:")
                logger.info(f"  cp {ENV_EXAMPLE_PATH} {AUTH_ENV_PATH}")
                logger.info("然后编辑.env文件，填入实际的API密钥配置")
            else:
                logger.warning("未找到.env.example模板文件")
                logger.warning("请在项目根目录下创建.env文件并配置相关API密钥:")
                logger.warning("  # 火山方舟 API配置")
                logger.warning('  ARK_API_KEY="your_api_key_here"')
                logger.warning('  VOLCENGINE_ACCESS_KEY="your_access_key_here"')
                logger.warning('  VOLCENGINE_SECRET_KEY="your_secret_key_here"')

        # 检查是否存在可能冲突的.env文件
        conflicting_env_files = []
        for backup_path in BACKUP_ENV_PATHS:
            if backup_path.exists():
                conflicting_env_files.append(backup_path)

        if conflicting_env_files:
            logger.warning("检测到可能冲突的环境变量配置文件:")
            for env_file in conflicting_env_files:
                logger.warning(f"  - {env_file}")
            logger.warning(f"系统将优先使用权威配置文件: {AUTH_ENV_PATH}")
            logger.warning("建议删除其他位置的.env文件以避免配置混淆")

        # 记录实际使用的.env文件路径
        if AUTH_ENV_PATH.exists():
            logger.info(f"使用权威环境配置文件: {AUTH_ENV_PATH}")
        else:
            logger.info("未找到.env文件，将使用系统环境变量或默认值")

    def ensure_env_file(self) -> bool:
        """确保.env文件存在，首次部署时自动创建"""
        if AUTH_ENV_PATH.exists():
            return True

        # 尝试从.env.example创建
        if ENV_EXAMPLE_PATH.exists():
            try:
                import shutil
                shutil.copy2(ENV_EXAMPLE_PATH, AUTH_ENV_PATH)
                logger.info(f"已从模板创建.env文件: {AUTH_ENV_PATH}")
                logger.info("请编辑.env文件，填入实际的API密钥配置")
                return True
            except Exception as e:
                logger.error(f"复制.env.example文件失败: {e}")
                return False
        else:
            # 创建基础的.env文件
            try:
                with open(AUTH_ENV_PATH, 'w', encoding='utf-8') as f:
                    f.write("# AI模型API密钥配置\n")
                    f.write("# 请填入您的实际API密钥\n\n")
                    f.write("# 火山方舟 API配置\n")
                    f.write('ARK_API_KEY="your_api_key_here"\n')
                    f.write('VOLCENGINE_ACCESS_KEY="your_access_key_here"\n')
                    f.write('VOLCENGINE_SECRET_KEY="your_secret_key_here"\n')

                logger.info(f"已创建基础.env文件: {AUTH_ENV_PATH}")
                logger.info("请编辑.env文件，填入实际的API密钥配置")
                return True
            except Exception as e:
                logger.error(f"创建.env文件失败: {e}")
                return False

    @property
    def is_development(self) -> bool:
        """判断是否为开发环境"""
        return self.DEBUG

    @property
    def is_production(self) -> bool:
        """判断是否为生产环境"""
        return not self.DEBUG

    def get_project_path(self, project_id: str) -> Path:
        """获取项目路径"""
        return self.PROJECTS_DIR / project_id

    def get_temp_path(self, filename: str) -> Path:
        """获取临时文件路径"""
        return self.TEMP_DIR / filename

    def get_log_path(self, filename: str) -> Path:
        """获取日志文件路径"""
        return self.LOGS_DIR / filename


# 创建全局配置实例
settings = Settings()

# 导出常用配置
__all__ = [
    "settings",
    "Settings",
    "PROJECT_ROOT",
    "BACKEND_ROOT"
]