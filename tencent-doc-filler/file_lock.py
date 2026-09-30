"""跨进程文件锁实现 - 解决并发读写 JSON 文件的竞态条件"""
from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger(__name__)

# Windows 平台不支持 fcntl，使用 msvcrt
try:
    import fcntl
    HAS_FCNTL = True
except ImportError:
    import msvcrt
    HAS_FCNTL = False


class FileLock:
    """文件锁上下文管理器

    跨平台支持：
    - Linux/Mac: fcntl (共享锁/独占锁)
    - Windows: msvcrt (独占锁)
    """

    def __init__(
        self,
        file_path: Path | str,
        timeout: float = 5.0,
        exclusive: bool = True,
    ):
        """
        Args:
            file_path: 要加锁的文件路径
            timeout: 加锁超时时间（秒）
            exclusive: 是否为独占锁（False为共享读锁）
        """
        self.file_path = Path(file_path)
        self.timeout = timeout
        self.exclusive = exclusive
        self.file_handle = None

    def __enter__(self):
        """同步上下文管理器入口"""
        self.file_path.parent.mkdir(parents=True, exist_ok=True)

        # 打开文件（如果不存在则创建）
        mode = 'r+' if self.file_path.exists() else 'w+'
        self.file_handle = open(self.file_path, mode, encoding='utf-8')

        # 尝试加锁
        import time
        start_time = time.time()

        if HAS_FCNTL:
            # Linux/Mac: fcntl
            lock_type = fcntl.LOCK_EX if self.exclusive else fcntl.LOCK_SH
            while True:
                try:
                    fcntl.flock(self.file_handle.fileno(), lock_type | fcntl.LOCK_NB)
                    logger.debug(
                        f"文件锁获取成功: {self.file_path.name} "
                        f"({'独占' if self.exclusive else '共享'})"
                    )
                    break
                except BlockingIOError:
                    if time.time() - start_time > self.timeout:
                        self.file_handle.close()
                        logger.error(f"文件锁获取超时: {self.file_path.name}")
                        raise TimeoutError(f"获取文件锁超时: {self.file_path}")
                    time.sleep(0.01)
        else:
            # Windows: msvcrt (仅支持独占锁)
            while True:
                try:
                    msvcrt.locking(self.file_handle.fileno(), msvcrt.LK_NBLCK, 1)
                    logger.debug(f"文件锁获取成功: {self.file_path.name} (Windows)")
                    break
                except OSError:
                    if time.time() - start_time > self.timeout:
                        self.file_handle.close()
                        logger.error(f"文件锁获取超时: {self.file_path.name}")
                        raise TimeoutError(f"获取文件锁超时: {self.file_path}")
                    time.sleep(0.01)

        return self.file_handle

    def __exit__(self, exc_type, exc_val, exc_tb):
        """同步上下文管理器退出"""
        if self.file_handle:
            try:
                if HAS_FCNTL:
                    fcntl.flock(self.file_handle.fileno(), fcntl.LOCK_UN)
                    logger.debug(f"文件锁释放: {self.file_path.name}")
                else:
                    # Windows: msvcrt.locking 的解锁需要特殊处理
                    try:
                        msvcrt.locking(self.file_handle.fileno(), msvcrt.LK_UNLCK, 1)
                        logger.debug(f"文件锁释放: {self.file_path.name}")
                    except OSError:
                        # Windows 下有时解锁会失败，但文件关闭后会自动释放
                        pass
            except Exception as e:
                logger.warning(f"释放文件锁失败: {e}")
            finally:
                self.file_handle.close()


async def safe_read_json(
    file_path: Path | str,
    default: Any = None,
    timeout: float = 5.0,
) -> Any:
    """安全读取 JSON 文件（带文件锁）

    Args:
        file_path: JSON 文件路径
        default: 文件不存在或为空时的默认值
        timeout: 加锁超时时间（秒）

    Returns:
        解析后的 JSON 数据，失败返回 default
    """
    file_path = Path(file_path)

    if not file_path.exists():
        logger.debug(f"文件不存在，返回默认值: {file_path.name}")
        return default

    def _read():
        try:
            with FileLock(file_path, timeout=timeout, exclusive=False) as f:
                f.seek(0)
                content = f.read()
                if not content.strip():
                    return default
                return json.loads(content)
        except (OSError, json.JSONDecodeError, TimeoutError) as e:
            logger.error(f"读取 JSON 失败: {file_path.name} - {e}")
            return default

    return await asyncio.to_thread(_read)


async def safe_write_json(
    file_path: Path | str,
    data: Any,
    timeout: float = 5.0,
) -> bool:
    """安全写入 JSON 文件（带文件锁）

    Args:
        file_path: JSON 文件路径
        data: 要写入的数据
        timeout: 加锁超时时间（秒）

    Returns:
        是否写入成功
    """
    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)

    def _write():
        try:
            with FileLock(file_path, timeout=timeout, exclusive=True) as f:
                f.seek(0)
                f.truncate()
                json.dump(data, f, ensure_ascii=False, indent=2)
                f.flush()
            logger.debug(f"JSON 写入成功: {file_path.name}")
            return True
        except (OSError, TimeoutError) as e:
            logger.error(f"写入 JSON 失败: {file_path.name} - {e}")
            return False

    return await asyncio.to_thread(_write)


async def safe_update_json(
    file_path: Path | str,
    update_fn: Callable[[Any], Any],
    default: Any = None,
    timeout: float = 5.0,
) -> tuple[bool, Any]:
    """原子性更新 JSON 文件（读-修改-写）

    Args:
        file_path: JSON 文件路径
        update_fn: 更新函数，接收当前数据，返回新数据
        default: 文件不存在时的默认值
        timeout: 加锁超时时间（秒）

    Returns:
        (是否成功, 更新后的数据)
    """
    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)

    def _update():
        try:
            with FileLock(file_path, timeout=timeout, exclusive=True) as f:
                # 读取当前数据
                f.seek(0)
                content = f.read()
                if content.strip():
                    current_data = json.loads(content)
                else:
                    current_data = default

                # 应用更新函数
                new_data = update_fn(current_data)

                # 写入新数据
                f.seek(0)
                f.truncate()
                json.dump(new_data, f, ensure_ascii=False, indent=2)
                f.flush()

            logger.debug(f"JSON 原子更新成功: {file_path.name}")
            return True, new_data

        except (OSError, json.JSONDecodeError, TimeoutError) as e:
            logger.error(f"原子更新 JSON 失败: {file_path.name} - {e}")
            return False, None

    return await asyncio.to_thread(_update)


# 兼容性测试
if __name__ == "__main__":
    import tempfile
    import asyncio

    async def test():
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            test_file = Path(f.name)

        print(f"测试文件: {test_file}")

        # 测试写入
        print("\n1. 测试安全写入...")
        success = await safe_write_json(test_file, {"count": 0, "name": "test"})
        print(f"   写入结果: {'成功' if success else '失败'}")

        # 测试读取
        print("\n2. 测试安全读取...")
        data = await safe_read_json(test_file)
        print(f"   读取结果: {data}")

        # 测试原子更新
        print("\n3. 测试原子更新...")
        def increment(d):
            d = d or {}
            d["count"] = d.get("count", 0) + 1
            return d

        success, new_data = await safe_update_json(test_file, increment)
        print(f"   更新结果: {'成功' if success else '失败'}")
        print(f"   新数据: {new_data}")

        # 并发测试
        print("\n4. 测试并发更新（10次）...")
        tasks = [safe_update_json(test_file, increment) for _ in range(10)]
        results = await asyncio.gather(*tasks)
        final_data = await safe_read_json(test_file)
        print(f"   最终数据: {final_data}")
        print(f"   期望 count=11, 实际 count={final_data.get('count')}")

        # 清理
        test_file.unlink()
        print("\n✅ 测试完成")

    # 运行测试
    asyncio.run(test())
