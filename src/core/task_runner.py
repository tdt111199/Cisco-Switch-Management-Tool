"""Concurrent task runner for multi-device batch automation."""

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from core.inventory import SwitchDevice
from core.logger import logger


class TaskStatus(Enum):
    PENDING = "Chờ"
    CONNECTING = "Đang kết nối"
    RUNNING = "Đang thực thi"
    SUCCESS = "Thành công"
    FAILED = "Thất bại"


@dataclass
class DeviceTaskResult:
    """Stores result and execution stats for a single device task."""
    device: SwitchDevice
    status: TaskStatus = TaskStatus.PENDING
    start_time: float = 0.0
    end_time: float = 0.0
    output: str = ""
    error_message: str = ""

    @property
    def duration_str(self) -> str:
        if self.start_time == 0:
            return "-"
        duration = (self.end_time or time.time()) - self.start_time
        return f"{duration:.1f}s"


class BatchTaskRunner:
    """Executes a function across multiple switch devices concurrently."""

    def __init__(self, max_workers: int = 5):
        self.max_workers = max_workers
        self.executor: Optional[ThreadPoolExecutor] = None
        self.is_running = False

    def run_batch(
        self,
        devices: List[SwitchDevice],
        task_func: Callable[[SwitchDevice], str],
        on_status_change: Optional[Callable[[DeviceTaskResult], None]] = None,
        on_all_complete: Optional[Callable[[List[DeviceTaskResult]], None]] = None,
    ) -> List[DeviceTaskResult]:
        """
        Executes task_func on each device in a separate thread.
        Can be called in a background thread by GUI so UI doesn't freeze.
        """
        results: Dict[str, DeviceTaskResult] = {
            d.id: DeviceTaskResult(device=d, status=TaskStatus.PENDING)
            for d in devices
        }
        self.is_running = True

        for res in results.values():
            if on_status_change:
                on_status_change(res)

        def _worker_wrapper(device: SwitchDevice) -> DeviceTaskResult:
            res = results[device.id]
            res.start_time = time.time()
            res.status = TaskStatus.CONNECTING
            if on_status_change:
                on_status_change(res)

            try:
                res.status = TaskStatus.RUNNING
                if on_status_change:
                    on_status_change(res)

                output = task_func(device)
                res.output = output
                res.status = TaskStatus.SUCCESS
                logger.success(f"Tác vụ hoàn thành xuất sắc trên {device.name}", device.name)
            except Exception as e:
                res.error_message = str(e)
                res.status = TaskStatus.FAILED
                logger.error(f"Tác vụ thất bại trên {device.name}: {e}", device.name)
            finally:
                res.end_time = time.time()
                if on_status_change:
                    on_status_change(res)
            return res

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            self.executor = executor
            futures = [executor.submit(_worker_wrapper, dev) for dev in devices]
            final_results = [f.result() for f in futures]

        self.is_running = False
        if on_all_complete:
            on_all_complete(final_results)
        return final_results
