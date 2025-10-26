"""
图像处理工具函数
Image Processing Utility Functions

包含base64编码、图像格式转换、下载等功能
"""

import os
import base64
import mimetypes
import httpx
import hashlib
import time
from pathlib import Path
from typing import Tuple, Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


def encode_file_to_base64(file_path: str) -> str:
    """
    将本地文件编码为base64格式

    Args:
        file_path: 本地文件路径

    Returns:
        base64编码字符串，格式: data:{mime_type};base64,{base64_data}

    Raises:
        FileNotFoundError: 文件不存在
        ValueError: 文件格式不支持
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"文件不存在: {file_path}")

    # 检测文件类型
    mime_type, _ = mimetypes.guess_type(file_path)
    if not mime_type or not mime_type.startswith('image/'):
        raise ValueError(f"不支持的文件格式: {file_path}, MIME类型: {mime_type}")

    # 读取并编码文件
    try:
        with open(file_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')

        base64_data = f"data:{mime_type};base64,{encoded_string}"
        logger.info(f"文件编码成功: {file_path}, 大小: {len(encoded_string)} 字符")
        return base64_data

    except Exception as e:
        logger.error(f"文件编码失败: {file_path}, 错误: {e}")
        raise


def encode_file(file_path: str) -> str:
    """
    将本地文件编码为base64格式 - 简化版本，按照用户提供格式

    格式为 data:{mime_type};base64,{base64_data}

    Args:
        file_path: 本地文件路径

    Returns:
        base64编码字符串

    Raises:
        FileNotFoundError: 文件不存在
    """
    mime_type, _ = mimetypes.guess_type(file_path)
    with open(file_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
    return f"data:{mime_type};base64,{encoded_string}"


def decode_base64_to_file(base64_data: str, output_path: str) -> str:
    """
    将base64数据解码保存为文件

    Args:
        base64_data: base64编码数据
        output_path: 输出文件路径

    Returns:
        保存的文件路径
    """
    try:
        # 提取base64部分
        if ',' in base64_data:
            header, base64_string = base64_data.split(',', 1)
        else:
            base64_string = base64_data

        # 解码并保存
        image_data = base64.b64decode(base64_string)

        # 确保输出目录存在
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "wb") as f:
            f.write(image_data)

        logger.info(f"base64数据解码保存成功: {output_path}")
        return output_path

    except Exception as e:
        logger.error(f"base64解码失败: {e}")
        raise


def get_image_info(base64_data: str) -> dict:
    """
    获取base64图像的基本信息

    Args:
        base64_data: base64编码的图像数据

    Returns:
        包含图像信息的字典
    """
    try:
        # 初始化默认值
        mime_type = "unknown"
        base64_string = ""

        # 检查输入是否为空或无效
        if not base64_data or not isinstance(base64_data, str):
            logger.warning("输入的base64数据无效或为空")
            return {
                "mime_type": "unknown",
                "encoded_size": 0,
                "original_size": 0,
                "compression_ratio": 0
            }

        # 提取MIME类型和base64字符串
        if ',' in base64_data:
            header, base64_string = base64_data.split(',', 1)
            # 安全地解析MIME类型
            if header and isinstance(header, str) and header.startswith('data:'):
                header_parts = header.split(':')
                if len(header_parts) >= 2:
                    mime_part = header_parts[1]
                    if ';' in mime_part:
                        mime_type = mime_part.split(';')[0]
                    else:
                        mime_type = mime_part
        else:
            base64_string = base64_data

        # 验证base64字符串
        if not base64_string:
            logger.warning("未能提取到有效的base64字符串")
            return {
                "mime_type": mime_type,
                "encoded_size": 0,
                "original_size": 0,
                "compression_ratio": 0
            }

        try:
            # 尝试解码base64以验证数据有效性
            decoded_data = base64.b64decode(base64_string)
            original_size = len(decoded_data)
        except Exception as decode_error:
            logger.warning(f"base64解码失败: {decode_error}")
            return {
                "mime_type": mime_type,
                "encoded_size": len(base64_string),
                "original_size": 0,
                "compression_ratio": 0
            }

        data_size = len(base64_string)  # base64编码后的长度

        return {
            "mime_type": mime_type,
            "encoded_size": data_size,
            "original_size": original_size,
            "compression_ratio": original_size / data_size if data_size > 0 else 0
        }

    except Exception as e:
        logger.error(f"获取图像信息失败: {e}")
        return {
            "mime_type": "unknown",
            "encoded_size": 0,
            "original_size": 0,
            "compression_ratio": 0
        }


async def download_image_from_url(
    image_url: str,
    save_path: str,
    timeout: int = 30
) -> str:
    """
    从URL下载图像到本地

    Args:
        image_url: 图像URL
        save_path: 本地保存路径
        timeout: 下载超时时间（秒）

    Returns:
        下载的文件路径

    Raises:
        httpx.RequestError: 下载失败
        IOError: 文件保存失败
    """
    try:
        # 确保输出目录存在
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)

        # 下载文件
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            response = await client.get(image_url)
            response.raise_for_status()

            # 保存文件
            with open(save_path, "wb") as f:
                f.write(response.content)

        file_size = os.path.getsize(save_path)
        logger.info(f"图像下载成功: {image_url} -> {save_path}, 大小: {file_size} 字节")
        return save_path

    except httpx.RequestError as e:
        logger.error(f"图像下载失败 {image_url}: {e}")
        raise
    except Exception as e:
        logger.error(f"保存图像失败 {save_path}: {e}")
        raise


async def download_to_temp_images(image_url: str, filename: Optional[str] = None) -> str:
    """
    下载图像到 temp/images/ 目录

    Args:
        image_url: 图像URL
        filename: 可选的文件名，如果不提供则自动生成

    Returns:
        下载的文件路径
    """
    from ..config import settings
    temp_dir = settings.TEMP_DOWNLOADS_DIR
    temp_dir.mkdir(parents=True, exist_ok=True)

    if not filename:
        # 生成基于时间戳的唯一文件名
        timestamp = int(time.time())
        hash_suffix = hashlib.md5(image_url.encode()).hexdigest()[:8]
        filename = f"download_{timestamp}_{hash_suffix}.png"

    save_path = temp_dir / filename

    return await download_image_from_url(image_url, str(save_path))


def generate_unique_filename(original_path: str, suffix: str = "") -> str:
    """
    生成唯一的文件名

    Args:
        original_path: 原始文件路径
        suffix: 文件名后缀

    Returns:
        唯一的文件路径
    """
    path = Path(original_path)

    # 生成时间戳和哈希
    import time
    timestamp = int(time.time())
    hash_obj = hashlib.md5(f"{original_path}{timestamp}".encode())
    hash_suffix = hash_obj.hexdigest()[:8]

    # 构建新文件名
    stem = f"{path.stem}_{suffix}_{hash_suffix}" if suffix else f"{path.stem}_{hash_suffix}"
    new_filename = f"{stem}{path.suffix}"

    return str(path.parent / new_filename)


def validate_image_file(file_path: str) -> Tuple[bool, str]:
    """
    验证图像文件是否有效

    Args:
        file_path: 文件路径

    Returns:
        (是否有效, 错误信息)
    """
    if not os.path.exists(file_path):
        return False, f"文件不存在: {file_path}"

    # 检查文件大小（限制为10MB）
    file_size = os.path.getsize(file_path)
    max_size = 10 * 1024 * 1024  # 10MB
    if file_size > max_size:
        return False, f"文件过大: {file_size} 字节，最大支持 {max_size} 字节"

    # 检查文件类型
    mime_type, _ = mimetypes.guess_type(file_path)
    supported_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp', 'image/gif']

    if not mime_type or mime_type not in supported_types:
        return False, f"不支持的文件类型: {mime_type}，支持的类型: {', '.join(supported_types)}"

    return True, "文件验证通过"


def compress_base64_if_needed(base64_data: str, max_size: int = 1024*1024) -> str:
    """
    如果base64数据过大，进行压缩

    Args:
        base64_data: base64编码的图像数据
        max_size: 最大允许大小（字节）

    Returns:
        处理后的base64数据
    """
    try:
        # 获取原始数据大小
        if ',' in base64_data:
            _, base64_string = base64_data.split(',', 1)
        else:
            base64_string = base64_data

        original_data = base64.b64decode(base64_string)
        original_size = len(original_data)

        if original_size <= max_size:
            return base64_data

        logger.warning(f"图像过大 ({original_size} 字节)，尝试压缩...")

        # 这里可以添加图像压缩逻辑
        # 目前只是记录警告，实际压缩需要PIL等图像处理库
        logger.warning("图像压缩功能需要额外实现，当前返回原始数据")

        return base64_data

    except Exception as e:
        logger.error(f"base64压缩失败: {e}")
        return base64_data


class ImageProcessor:
    """图像处理器类"""

    def __init__(self, temp_dir: Optional[str] = None):
        if temp_dir is None:
            from config import settings
            temp_dir = str(settings.TEMP_DOWNLOADS_DIR)
        self.temp_dir = Path(temp_dir)
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    async def process_uploadedImage(
        self,
        base64_data: str,
        process_type: str = "edit"
    ) -> dict:
        """
        处理上传的base64图像

        Args:
            base64_data: base64编码的图像数据
            process_type: 处理类型 (edit, generate, enhance)

        Returns:
            处理结果字典
        """
        try:
            # 验证和获取图像信息
            image_info = get_image_info(base64_data)

            # 生成临时文件路径
            temp_filename = f"upload_{process_type}_{hash(base64_data[:100])[:16]}.png"
            temp_path = self.temp_dir / temp_filename

            # 解码保存到临时文件
            decode_base64_to_file(base64_data, str(temp_path))

            return {
                "success": True,
                "temp_path": str(temp_path),
                "image_info": image_info,
                "process_type": process_type
            }

        except Exception as e:
            logger.error(f"处理上传图像失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def download_and_process_result(
        self,
        image_url: str,
        original_filename: str,
        process_type: str = "result"
    ) -> dict:
        """
        下载并处理AI生成的图像结果

        Args:
            image_url: 图像URL
            original_filename: 原始文件名
            process_type: 处理类型

        Returns:
            处理结果字典
        """
        try:
            # 生成结果文件路径
            result_filename = generate_unique_filename(
                original_filename,
                suffix=f"{process_type}_result"
            )
            result_path = self.temp_dir / result_filename

            # 下载图像
            downloaded_path = await download_image_from_url(
                image_url,
                str(result_path)
            )

            # 获取下载文件信息
            file_size = os.path.getsize(downloaded_path)

            return {
                "success": True,
                "downloaded_path": downloaded_path,
                "original_url": image_url,
                "file_size": file_size,
                "process_type": process_type
            }

        except Exception as e:
            logger.error(f"下载处理结果失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }