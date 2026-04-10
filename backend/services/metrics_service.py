import asyncio
import logging
from typing import Any

import psutil
from backend.services.task_manager import task_manager

try:
    import pynvml

    pynvml.nvmlInit()
    HAS_NVML = True
except Exception as e:
    HAS_NVML = False
    logging.warning(f"Failed to initialize pynvml: {e}")


class MetricsService:
    def __init__(self):
        self._running = False
        self._task = None
        self._subscribers = set()
        self._cached_metrics = self._get_metrics()

    def _get_metrics(self) -> dict[str, Any]:
        cpu_percent = psutil.cpu_percent(interval=None)
        mem = psutil.virtual_memory()
        mem_percent = mem.percent
        mem_used_gb = mem.used / (1024**3)
        mem_total_gb = mem.total / (1024**3)

        gpu_metrics = []
        if HAS_NVML:
            try:
                device_count = pynvml.nvmlDeviceGetCount()
                for i in range(device_count):
                    handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                    mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                    util_info = pynvml.nvmlDeviceGetUtilizationRates(handle)
                    gpu_metrics.append(
                        {
                            "id": i,
                            "name": pynvml.nvmlDeviceGetName(handle),
                            "utilization": util_info.gpu,
                            "memory_percent": (
                                (mem_info.used / mem_info.total) * 100
                                if mem_info.total > 0
                                else 0
                            ),
                            "memory_used_gb": mem_info.used / (1024**3),
                            "memory_total_gb": mem_info.total / (1024**3),
                        }
                    )
            except Exception as e:
                logging.warning(f"Error fetching GPU metrics: {e}")

        running_tasks = []
        for task_id, record in list(task_manager._tasks.items()):
            if record.status in ["pending", "running"]:
                running_tasks.append(
                    {
                        "task_id": task_id,
                        "task_type": record.task_type,
                        "status": record.status,
                        "progress": record.progress,
                        "message": record.message,
                    }
                )

        return {
            "cpu": {"percent": cpu_percent},
            "memory": {
                "percent": mem_percent,
                "used_gb": mem_used_gb,
                "total_gb": mem_total_gb,
            },
            "gpus": gpu_metrics,
            "active_tasks": running_tasks,
        }

    async def _poll_metrics(self):
        while self._running:
            self._cached_metrics = self._get_metrics()
            # Broadcast to subscribers
            if self._subscribers:
                for queue in self._subscribers:
                    queue.put_nowait(self._cached_metrics)
            await asyncio.sleep(1.0)

    def start(self):
        if not self._running:
            self._running = True
            psutil.cpu_percent(interval=None)  # Prime the CPU percent calculation
            self._task = asyncio.create_task(self._poll_metrics())

    def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()

    def subscribe(self) -> asyncio.Queue:
        queue = asyncio.Queue()
        self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue):
        self._subscribers.discard(queue)


metrics_service = MetricsService()
