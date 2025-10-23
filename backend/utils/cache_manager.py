"""
简化的TTL缓存管理器
Simplified TTL Cache Manager

只保留时间过期策略，提供简单易用的缓存接口
Only keeps time-based expiration policy, provides simple and easy-to-use cache interface
"""

import json
import time
import hashlib
import pickle
import threading
from typing import Any, Dict, Optional, List, Callable
from pathlib import Path
import asyncio


class CacheEntry:
    """简化的缓存条目"""

    def __init__(self, value: Any, ttl_seconds: int):
        self.value = value
        self.created_at = time.time()
        self.expires_at = time.time() + ttl_seconds

    def is_expired(self) -> bool:
        """检查是否过期"""
        return self.expires_at < time.time()


class CacheStats:
    """缓存统计"""

    def __init__(self):
        self.hits = 0
        self.misses = 0
        self.sets = 0
        self.deletes = 0

    @property
    def hit_rate(self) -> float:
        """命中率"""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0


class MemoryCache:
    """简化的TTL内存缓存"""

    def __init__(self, name: str, ttl_seconds: int = 3600, max_size: int = 100):
        self.name = name
        self.ttl_seconds = ttl_seconds
        self.max_size = max_size

        self._cache: Dict[str, CacheEntry] = {}
        self._stats = CacheStats()
        self._lock = threading.RLock()

    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        with self._lock:
            if key not in self._cache:
                self._stats.misses += 1
                return None

            entry = self._cache[key]

            # 检查是否过期
            if entry.is_expired():
                del self._cache[key]
                self._stats.misses += 1
                self._stats.deletes += 1
                return None

            self._stats.hits += 1
            return entry.value

    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> bool:
        """设置缓存值"""
        with self._lock:
            # 如果达到最大容量，删除最旧的条目
            if len(self._cache) >= self.max_size and key not in self._cache:
                oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k].created_at)
                del self._cache[oldest_key]
                self._stats.deletes += 1

            # 计算过期时间
            ttl = ttl_seconds if ttl_seconds is not None else self.ttl_seconds

            # 创建缓存条目
            entry = CacheEntry(value, ttl)
            self._cache[key] = entry
            self._stats.sets += 1
            return True

    def delete(self, key: str) -> bool:
        """删除缓存条目"""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                self._stats.deletes += 1
                return True
            return False

    def clear(self):
        """清空缓存"""
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            self._stats.deletes += count

    def cleanup_expired(self):
        """清理过期条目"""
        with self._lock:
            expired_keys = [
                key for key, entry in self._cache.items()
                if entry.is_expired()
            ]

            for key in expired_keys:
                del self._cache[key]
                self._stats.deletes += 1

            return len(expired_keys)

    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        with self._lock:
            return {
                'name': self.name,
                'ttl_seconds': self.ttl_seconds,
                'max_size': self.max_size,
                'current_size': len(self._cache),
                'hits': self._stats.hits,
                'misses': self._stats.misses,
                'sets': self._stats.sets,
                'deletes': self._stats.deletes,
                'hit_rate': f"{self._stats.hit_rate:.1%}"
            }


class FileCache:
    """简化的文件缓存"""

    def __init__(self, name: str, cache_dir: str, ttl_seconds: int = 86400):
        self.name = name
        self.ttl_seconds = ttl_seconds
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()

    def _get_cache_path(self, key: str) -> Path:
        """获取缓存文件路径"""
        key_hash = hashlib.md5(key.encode('utf-8')).hexdigest()
        return self.cache_dir / f"{key_hash}.cache"

    def _get_meta_path(self, key: str) -> Path:
        """获取元数据文件路径"""
        key_hash = hashlib.md5(key.encode('utf-8')).hexdigest()
        return self.cache_dir / f"{key_hash}.meta"

    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        with self._lock:
            cache_path = self._get_cache_path(key)
            meta_path = self._get_meta_path(key)

            # 检查文件是否存在
            if not cache_path.exists() or not meta_path.exists():
                return None

            try:
                # 读取元数据
                with open(meta_path, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)

                # 检查是否过期
                if metadata['expires_at'] < time.time():
                    self.delete(key)
                    return None

                # 读取缓存数据
                with open(cache_path, 'rb') as f:
                    return pickle.load(f)

            except Exception:
                self.delete(key)
                return None

    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> bool:
        """设置缓存值"""
        with self._lock:
            try:
                cache_path = self._get_cache_path(key)
                meta_path = self._get_meta_path(key)

                # 序列化数据
                serialized_data = pickle.dumps(value)

                # 计算过期时间
                ttl = ttl_seconds if ttl_seconds is not None else self.ttl_seconds
                expires_at = time.time() + ttl

                # 写入缓存文件
                with open(cache_path, 'wb') as f:
                    f.write(serialized_data)

                # 写入元数据
                metadata = {
                    'key': key,
                    'created_at': time.time(),
                    'expires_at': expires_at,
                    'size_bytes': len(serialized_data)
                }

                with open(meta_path, 'w', encoding='utf-8') as f:
                    json.dump(metadata, f, indent=2)

                return True

            except Exception:
                return False

    def delete(self, key: str) -> bool:
        """删除缓存条目"""
        with self._lock:
            cache_path = self._get_cache_path(key)
            meta_path = self._get_meta_path(key)

            success = False

            try:
                if cache_path.exists():
                    cache_path.unlink()
                    success = True
            except Exception:
                pass

            try:
                if meta_path.exists():
                    meta_path.unlink()
                    success = True
            except Exception:
                pass

            return success

    def clear(self):
        """清空缓存"""
        with self._lock:
            # 删除所有缓存和元数据文件
            for cache_file in list(self.cache_dir.glob('*.cache')) + list(self.cache_dir.glob('*.meta')):
                try:
                    cache_file.unlink()
                except Exception:
                    pass

    def cleanup_expired(self) -> int:
        """清理过期文件"""
        with self._lock:
            cleaned_count = 0
            current_time = time.time()

            for meta_file in self.cache_dir.glob('*.meta'):
                try:
                    with open(meta_file, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)

                    if metadata['expires_at'] < current_time:
                        key = metadata['key']
                        self.delete(key)
                        cleaned_count += 1

                except Exception:
                    # 删除损坏的元数据文件
                    try:
                        meta_file.unlink()
                    except Exception:
                        pass

            return cleaned_count


class CacheManager:
    """简化的缓存管理器"""

    def __init__(self, cache_config: Optional[Dict[str, Dict[str, Any]]] = None):
        """初始化缓存管理器"""
        # 优先使用传入的配置，否则使用settings中的配置
        if cache_config is None:
            try:
                from ..config import settings
                self.config = settings.CACHE_CONFIG
            except ImportError:
                # 如果无法导入settings，使用默认配置
                self.config = {
                    'text_analysis': {'ttl': 1800, 'max_size': 100},
                    'api_responses': {'ttl': 300, 'max_size': 500},
                    'images': {'ttl': 86400, 'max_size': 50}
                }
        else:
            self.config = cache_config

        # 初始化缓存实例
        self.caches: Dict[str, Any] = {}

        # 文本分析缓存 - 内存缓存
        self.caches['text_analysis'] = MemoryCache(
            name='text_analysis',
            ttl_seconds=self.config['text_analysis']['ttl'],
            max_size=self.config['text_analysis']['max_size']
        )

        # API响应缓存 - 内存缓存
        self.caches['api_responses'] = MemoryCache(
            name='api_responses',
            ttl_seconds=self.config['api_responses']['ttl'],
            max_size=self.config['api_responses']['max_size']
        )

        # 图片缓存 - 文件缓存，使用专门的cache目录
        self.caches['images'] = FileCache(
            name='images',
            cache_dir='cache/ai_images',
            ttl_seconds=self.config['images']['ttl']
        )

    def get(self, key: str, cache_type: str = "text_analysis") -> Optional[Any]:
        """获取缓存值"""
        if cache_type not in self.caches:
            return None
        return self.caches[cache_type].get(key)

    def set(
        self,
        key: str,
        value: Any,
        cache_type: str = "text_analysis",
        ttl_seconds: Optional[int] = None
    ) -> bool:
        """设置缓存值"""
        if cache_type not in self.caches:
            return False
        return self.caches[cache_type].set(key, value, ttl_seconds)

    def delete(self, key: str, cache_type: str = "text_analysis") -> bool:
        """删除缓存条目"""
        if cache_type not in self.caches:
            return False
        return self.caches[cache_type].delete(key)

    def clear(self, cache_type: Optional[str] = None):
        """清空缓存"""
        if cache_type is None:
            # 清空所有缓存
            for cache in self.caches.values():
                if hasattr(cache, 'clear'):
                    cache.clear()
        elif cache_type in self.caches:
            if hasattr(self.caches[cache_type], 'clear'):
                self.caches[cache_type].clear()

    def cleanup_expired(self) -> Dict[str, int]:
        """清理过期条目"""
        results = {}
        for cache_name, cache in self.caches.items():
            if hasattr(cache, 'cleanup_expired'):
                cleaned_count = cache.cleanup_expired()
                results[cache_name] = cleaned_count
        return results

    def get_stats(self) -> Dict[str, Any]:
        """获取所有缓存统计信息"""
        stats = {}
        for cache_name, cache in self.caches.items():
            if hasattr(cache, 'get_stats'):
                cache_stats = cache.get_stats()
                stats[cache_name] = cache_stats
        return stats

    def get_cache_key(self, *args, **kwargs) -> str:
        """生成缓存键"""
        key_data = {
            'args': args,
            'kwargs': sorted(kwargs.items())
        }
        key_str = json.dumps(key_data, sort_keys=True, default=str)
        return hashlib.md5(key_str.encode('utf-8')).hexdigest()

    def cache_api_call(
        self,
        api_func: Callable,
        cache_duration: int = 300,
        key_prefix: str = "api"
    ):
        """装饰器：缓存API调用结果"""
        def decorator(*args, **kwargs):
            # 生成缓存键
            cache_key = f"{key_prefix}:{self.get_cache_key(*args, **kwargs)}"

            # 尝试从缓存获取
            cached_result = self.get(cache_key, "api_responses")
            if cached_result is not None:
                return cached_result

            # 调用API函数
            try:
                # 如果是异步函数
                if asyncio.iscoroutinefunction(api_func):
                    async def wrapper():
                        result = await api_func(*args, **kwargs)
                        self.set(cache_key, result, "api_responses", cache_duration)
                        return result
                    return wrapper()
                else:
                    result = api_func(*args, **kwargs)
                    self.set(cache_key, result, "api_responses", cache_duration)
                    return result
            except Exception as e:
                # API调用失败，不缓存结果
                raise e

        return decorator


# 创建全局缓存管理器实例
cache_manager = CacheManager()


# 便捷函数
def get_cache(key: str, cache_type: str = "text_analysis") -> Optional[Any]:
    """获取缓存值"""
    return cache_manager.get(key, cache_type)


def set_cache(
    key: str,
    value: Any,
    cache_type: str = "text_analysis",
    ttl_seconds: Optional[int] = None
) -> bool:
    """设置缓存值"""
    return cache_manager.set(key, value, cache_type, ttl_seconds)


def delete_cache(key: str, cache_type: str = "text_analysis") -> bool:
    """删除缓存条目"""
    return cache_manager.delete(key, cache_type)


def clear_cache(cache_type: Optional[str] = None):
    """清空缓存"""
    cache_manager.clear(cache_type)


def get_cache_stats() -> Dict[str, Any]:
    """获取缓存统计信息"""
    return cache_manager.get_stats()


def generate_cache_key(*args, **kwargs) -> str:
    """生成缓存键"""
    return cache_manager.get_cache_key(*args, **kwargs)


def simple_cache_decorator(cache_type: str = "text_analysis", ttl_seconds: Optional[int] = None):
    """简单的缓存装饰器"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            # 生成缓存键
            cache_key = generate_cache_key(func.__name__, *args, **kwargs)

            # 尝试从缓存获取
            cached_result = get_cache(cache_key, cache_type)
            if cached_result is not None:
                return cached_result

            # 调用函数并缓存结果
            try:
                result = func(*args, **kwargs)
                set_cache(cache_key, result, cache_type, ttl_seconds)
                return result
            except Exception:
                # 函数调用失败，不缓存结果
                raise

        return wrapper
    return decorator