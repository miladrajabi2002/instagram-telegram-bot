"""Task scheduler with randomization and human-like behavior."""
import time
import random
import logging
from datetime import datetime, timedelta
from typing import Callable, Dict, List, Optional
from queue import PriorityQueue
from threading import Thread, Event, Lock
from dataclasses import dataclass, field
from enum import Enum

import config
from includes.logger import setup_logger

logger = setup_logger(__name__)


class TaskPriority(Enum):
    """Task priority levels."""
    LOW = 3
    NORMAL = 2
    HIGH = 1


@dataclass(order=True)
class Task:
    """Scheduled task."""
    priority: int
    scheduled_time: datetime = field(compare=False)
    task_id: str = field(compare=False)
    func: Callable = field(compare=False)
    args: tuple = field(default=(), compare=False)
    kwargs: dict = field(default_factory=dict, compare=False)
    task_type: str = field(default='generic', compare=False)


class TaskScheduler:
    """Scheduler for Instagram automation tasks with randomization."""

    def __init__(self, telegram_notifier=None):
        """Initialize task scheduler.
        
        Args:
            telegram_notifier: Function to send Telegram notifications
        """
        self.task_queue = PriorityQueue()
        self.running = False
        self.paused = Event()
        self.paused.set()  # Start unpaused
        self.worker_thread: Optional[Thread] = None
        self.telegram_notifier = telegram_notifier
        self.lock = Lock()
        
        # Statistics
        self.stats = {
            'tasks_completed': 0,
            'tasks_failed': 0,
            'tasks_scheduled': 0,
        }

    def start(self):
        """Start the scheduler."""
        if self.running:
            logger.warning("Scheduler already running")
            return
        
        self.running = True
        self.worker_thread = Thread(target=self._worker, daemon=True)
        self.worker_thread.start()
        logger.info("Scheduler started")
        self._notify("▶️ Scheduler started")

    def stop(self):
        """Stop the scheduler."""
        if not self.running:
            logger.warning("Scheduler not running")
            return
        
        self.running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=10)
        logger.info("Scheduler stopped")
        self._notify("⏸️ Scheduler stopped")

    def pause(self):
        """Pause task execution."""
        self.paused.clear()
        logger.info("Scheduler paused")
        self._notify("⏸️ Tasks paused")

    def resume(self):
        """Resume task execution."""
        self.paused.set()
        logger.info("Scheduler resumed")
        self._notify("▶️ Tasks resumed")

    def is_paused(self) -> bool:
        """Check if scheduler is paused.
        
        Returns:
            bool: True if paused
        """
        return not self.paused.is_set()

    def schedule_task(
        self,
        func: Callable,
        task_type: str = 'generic',
        priority: TaskPriority = TaskPriority.NORMAL,
        delay: Optional[int] = None,
        randomize: bool = True,
        *args,
        **kwargs
    ) -> str:
        """Schedule a task for execution.
        
        Args:
            func: Function to execute
            task_type: Type of task (for statistics)
            priority: Task priority
            delay: Delay in seconds (None for random delay)
            randomize: Apply random delay
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            str: Task ID
        """
        if delay is None:
            delay = self._get_random_delay() if randomize else 0
        
        scheduled_time = datetime.now() + timedelta(seconds=delay)
        task_id = f"{task_type}_{int(time.time() * 1000)}"
        
        task = Task(
            priority=priority.value,
            scheduled_time=scheduled_time,
            task_id=task_id,
            func=func,
            args=args,
            kwargs=kwargs,
            task_type=task_type
        )
        
        self.task_queue.put(task)
        
        with self.lock:
            self.stats['tasks_scheduled'] += 1
        
        logger.debug(f"Scheduled task {task_id} at {scheduled_time} (delay: {delay}s)")
        return task_id

    def schedule_batch(
        self,
        tasks: List[Dict],
        randomize_order: bool = True,
        spread_over_minutes: Optional[int] = None
    ):
        """Schedule multiple tasks with randomization.
        
        Args:
            tasks: List of task dictionaries with 'func', 'task_type', etc.
            randomize_order: Randomize task execution order
            spread_over_minutes: Spread tasks over time period
        """
        task_list = tasks.copy()
        
        if randomize_order:
            random.shuffle(task_list)
        
        if spread_over_minutes:
            # Distribute tasks evenly with randomization
            total_seconds = spread_over_minutes * 60
            interval = total_seconds / len(task_list)
            
            for i, task_info in enumerate(task_list):
                # Add jitter to interval
                delay = int(i * interval + random.uniform(-interval * 0.3, interval * 0.3))
                delay = max(0, delay)
                
                self.schedule_task(
                    func=task_info['func'],
                    task_type=task_info.get('task_type', 'generic'),
                    priority=task_info.get('priority', TaskPriority.NORMAL),
                    delay=delay,
                    randomize=False,
                    *task_info.get('args', ()),
                    **task_info.get('kwargs', {})
                )
        else:
            for task_info in task_list:
                self.schedule_task(
                    func=task_info['func'],
                    task_type=task_info.get('task_type', 'generic'),
                    priority=task_info.get('priority', TaskPriority.NORMAL),
                    *task_info.get('args', ()),
                    **task_info.get('kwargs', {})
                )
        
        logger.info(f"Scheduled {len(task_list)} tasks")

    def _get_random_delay(self) -> int:
        """Generate random human-like delay using log-normal distribution.
        
        Returns:
            int: Delay in seconds
        """
        min_delay = config.MIN_ACTION_DELAY
        max_delay = config.MAX_ACTION_DELAY
        
        # Log-normal distribution for more realistic delays
        mean = (min_delay + max_delay) / 2
        sigma = (max_delay - min_delay) / 6
        
        delay = random.lognormvariate(mean, sigma)
        delay = int(max(min_delay, min(max_delay, delay)))
        
        return delay

    def _worker(self):
        """Worker thread to process tasks."""
        logger.info("Scheduler worker started")
        
        while self.running:
            try:
                # Wait if paused
                self.paused.wait()
                
                # Get next task (with timeout to check running flag)
                if self.task_queue.empty():
                    time.sleep(1)
                    continue
                
                task = self.task_queue.get(timeout=1)
                
                # Wait until scheduled time
                now = datetime.now()
                if task.scheduled_time > now:
                    wait_seconds = (task.scheduled_time - now).total_seconds()
                    if wait_seconds > 0:
                        logger.debug(f"Waiting {wait_seconds:.1f}s for task {task.task_id}")
                        time.sleep(wait_seconds)
                
                # Check if still running and not paused
                if not self.running:
                    break
                
                self.paused.wait()
                
                # Execute task
                try:
                    logger.info(f"Executing task {task.task_id} ({task.task_type})")
                    task.func(*task.args, **task.kwargs)
                    
                    with self.lock:
                        self.stats['tasks_completed'] += 1
                    
                    logger.debug(f"Task {task.task_id} completed successfully")
                    
                except Exception as e:
                    logger.error(f"Task {task.task_id} failed: {e}", exc_info=True)
                    self._notify(f"❌ Task failed: {task.task_type}\n{str(e)}")
                    
                    with self.lock:
                        self.stats['tasks_failed'] += 1
                
                finally:
                    self.task_queue.task_done()
                
            except Exception as e:
                logger.error(f"Worker error: {e}", exc_info=True)
                time.sleep(1)
        
        logger.info("Scheduler worker stopped")

    def get_stats(self) -> Dict:
        """Get scheduler statistics.
        
        Returns:
            Dictionary with statistics
        """
        with self.lock:
            return {
                **self.stats,
                'queue_size': self.task_queue.qsize(),
                'is_running': self.running,
                'is_paused': self.is_paused()
            }

    def clear_queue(self):
        """Clear all pending tasks."""
        with self.task_queue.mutex:
            self.task_queue.queue.clear()
        logger.info("Task queue cleared")
        self._notify("🗑️ Task queue cleared")

    def _notify(self, message: str):
        """Send Telegram notification.
        
        Args:
            message: Notification message
        """
        if self.telegram_notifier:
            try:
                self.telegram_notifier(message)
            except Exception as e:
                logger.error(f"Failed to send notification: {e}")
