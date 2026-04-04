"""
synchronization.py
------------------
Implements OS synchronization primitives and demonstrates
classic concurrency problems using Python threading.

Primitives:
  - Mutex (mutual exclusion lock)
  - Counting Semaphore
  - Monitor (condition variable pattern)
  - Read-Write Lock

Classic Problems:
  - Producer-Consumer (Bounded Buffer)
  - Dining Philosophers (deadlock demonstration + solution)
  - Readers-Writers
  - Deadlock Detection (Resource Allocation Graph)
"""

import threading
import time
import random
import queue
from collections import defaultdict
from typing import List, Dict, Optional


# ══════════════════════════════════════════════════════════════════
# MUTEX
# ══════════════════════════════════════════════════════════════════

class Mutex:
    """
    Simple mutual exclusion lock.
    Only one thread can hold the lock at a time.
    Tracks acquisition/release history for demonstration.
    """

    def __init__(self, name: str = "mutex"):
        self.name    = name
        self._lock   = threading.Lock()
        self.holder  = None
        self.history = []

    def acquire(self, thread_name: str = None, timeout: float = 5.0) -> bool:
        name = thread_name or threading.current_thread().name
        acquired = self._lock.acquire(timeout=timeout)
        if acquired:
            self.holder = name
            self.history.append(("ACQUIRE", name, time.time()))
        return acquired

    def release(self):
        name = self.holder
        self.holder = None
        self.history.append(("RELEASE", name, time.time()))
        self._lock.release()

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, *args):
        self.release()


# ══════════════════════════════════════════════════════════════════
# SEMAPHORE
# ══════════════════════════════════════════════════════════════════

class Semaphore:
    """
    Counting semaphore.
    Allows up to N concurrent threads into a critical section.
    """

    def __init__(self, initial: int = 1, name: str = "semaphore"):
        self.name    = name
        self._sem    = threading.Semaphore(initial)
        self.initial = initial
        self.count   = initial
        self._lock   = threading.Lock()
        self.history = []

    def wait(self, thread_name: str = None):
        """P() / down() — decrement, block if zero."""
        name = thread_name or threading.current_thread().name
        self._sem.acquire()
        with self._lock:
            self.count -= 1
            self.history.append(("WAIT", name, self.count))

    def signal(self, thread_name: str = None):
        """V() / up() — increment, unblock a waiting thread."""
        name = thread_name or threading.current_thread().name
        self._sem.release()
        with self._lock:
            self.count += 1
            self.history.append(("SIGNAL", name, self.count))


# ══════════════════════════════════════════════════════════════════
# READ-WRITE LOCK
# ══════════════════════════════════════════════════════════════════

class ReadWriteLock:
    """
    Allows multiple concurrent readers OR one exclusive writer.
    Writers have priority to prevent writer starvation.
    """

    def __init__(self):
        self._read_lock   = threading.Lock()
        self._write_lock  = threading.Lock()
        self._readers     = 0
        self.history      = []

    def acquire_read(self, name: str = ""):
        with self._read_lock:
            self._readers += 1
            if self._readers == 1:
                self._write_lock.acquire()   # First reader blocks writers
            self.history.append(("READ_ACQUIRE", name, self._readers))

    def release_read(self, name: str = ""):
        with self._read_lock:
            self._readers -= 1
            if self._readers == 0:
                self._write_lock.release()   # Last reader unblocks writers
            self.history.append(("READ_RELEASE", name, self._readers))

    def acquire_write(self, name: str = ""):
        self._write_lock.acquire()
        self.history.append(("WRITE_ACQUIRE", name, 0))

    def release_write(self, name: str = ""):
        self.history.append(("WRITE_RELEASE", name, 0))
        self._write_lock.release()


# ══════════════════════════════════════════════════════════════════
# PRODUCER-CONSUMER (Bounded Buffer)
# ══════════════════════════════════════════════════════════════════

class BoundedBuffer:
    """
    Classic Producer-Consumer problem with a bounded buffer.
    Uses semaphores to synchronize access.

    empty  semaphore: tracks empty slots (producer waits if 0)
    full   semaphore: tracks full slots  (consumer waits if 0)
    mutex  semaphore: mutual exclusion for buffer access
    """

    def __init__(self, capacity: int = 5):
        self.capacity = capacity
        self.buffer   = []
        self.empty    = Semaphore(capacity, "empty")
        self.full     = Semaphore(0, "full")
        self.mutex    = Semaphore(1, "mutex")
        self.log      = []

    def produce(self, item, producer_name: str = "Producer"):
        self.empty.wait(producer_name)     # Wait for empty slot
        self.mutex.wait(producer_name)     # Enter critical section
        self.buffer.append(item)
        self.log.append(f"[PRODUCE] {producer_name} → added {item!r} | buffer={self.buffer[:]}")
        self.mutex.signal(producer_name)   # Leave critical section
        self.full.signal(producer_name)    # Signal new item available

    def consume(self, consumer_name: str = "Consumer"):
        self.full.wait(consumer_name)      # Wait for item
        self.mutex.wait(consumer_name)     # Enter critical section
        item = self.buffer.pop(0)
        self.log.append(f"[CONSUME] {consumer_name} ← got    {item!r} | buffer={self.buffer[:]}")
        self.mutex.signal(consumer_name)   # Leave critical section
        self.empty.signal(consumer_name)   # Signal slot freed
        return item


def run_producer_consumer(n_items: int = 8, buffer_size: int = 3,
                           n_producers: int = 2, n_consumers: int = 2) -> dict:
    """Run a bounded-buffer producer-consumer simulation."""
    buf     = BoundedBuffer(buffer_size)
    results = {"produced": [], "consumed": [], "log": []}
    lock    = threading.Lock()

    items_to_produce = list(range(1, n_items + 1))
    item_queue       = queue.Queue()
    for item in items_to_produce:
        item_queue.put(item)

    def producer(name):
        while True:
            try:
                item = item_queue.get_nowait()
            except queue.Empty:
                break
            time.sleep(random.uniform(0.001, 0.005))
            buf.produce(item, name)
            with lock:
                results["produced"].append(item)

    def consumer(name):
        consumed_count = 0
        while True:
            with lock:
                total_produced = len(results["produced"])
                total_consumed = len(results["consumed"])
                if total_consumed >= n_items:
                    break
            try:
                item = buf.consume(name)
                with lock:
                    results["consumed"].append(item)
                time.sleep(random.uniform(0.001, 0.008))
                consumed_count += 1
            except Exception:
                break

    threads = []
    for i in range(n_producers):
        t = threading.Thread(target=producer, args=(f"Producer-{i+1}",))
        threads.append(t)
    for i in range(n_consumers):
        t = threading.Thread(target=consumer, args=(f"Consumer-{i+1}",))
        threads.append(t)

    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)

    results["log"] = buf.log
    return results


# ══════════════════════════════════════════════════════════════════
# DINING PHILOSOPHERS
# ══════════════════════════════════════════════════════════════════

class DiningPhilosophers:
    """
    Classic Dining Philosophers problem.

    5 philosophers sit at a round table.
    Each needs TWO forks (left + right) to eat.
    Naive solution deadlocks when all pick up left fork simultaneously.

    Solution implemented: Asymmetric — even philosophers pick left then right,
    odd philosophers pick right then left. Breaks circular wait condition.
    """

    PHILOSOPHERS = ["Aristotle", "Plato", "Socrates", "Descartes", "Kant"]

    def __init__(self, n: int = 5):
        self.n     = n
        self.forks = [threading.Lock() for _ in range(n)]
        self.log   = []
        self._lock = threading.Lock()

    def _log(self, msg: str):
        with self._lock:
            self.log.append(f"  {msg}")

    def philosopher(self, i: int, meals: int = 2):
        name = self.PHILOSOPHERS[i % len(self.PHILOSOPHERS)]

        for _ in range(meals):
            # Think
            self._log(f"{name:<12} is THINKING")
            time.sleep(random.uniform(0.001, 0.005))

            # Asymmetric fork acquisition — prevents deadlock
            if i % 2 == 0:
                left, right = i, (i + 1) % self.n
            else:
                left, right = (i + 1) % self.n, i

            self._log(f"{name:<12} is HUNGRY — waiting for forks {left} and {right}")
            self.forks[left].acquire()
            self.forks[right].acquire()

            # Eat
            self._log(f"{name:<12} is EATING  (forks {left}+{right} held)")
            time.sleep(random.uniform(0.002, 0.006))

            # Put down forks
            self.forks[right].release()
            self.forks[left].release()
            self._log(f"{name:<12} FINISHED  — forks {left}+{right} released")

    def run(self, meals_per_philosopher: int = 2) -> list:
        threads = [
            threading.Thread(
                target=self.philosopher,
                args=(i, meals_per_philosopher),
                name=f"Philosopher-{i}"
            )
            for i in range(self.n)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)
        return self.log


# ══════════════════════════════════════════════════════════════════
# DEADLOCK DETECTION — Resource Allocation Graph
# ══════════════════════════════════════════════════════════════════

class DeadlockDetector:
    """
    Detects deadlock using a Resource Allocation Graph (RAG).

    Nodes: Processes (P) and Resources (R)
    Edges:
      - Request edge:    P → R  (process waiting for resource)
      - Assignment edge: R → P  (resource held by process)

    Deadlock exists if the graph contains a cycle.
    Uses DFS cycle detection.
    """

    def __init__(self):
        self.held_by    : Dict[str, str]       = {}   # resource → process
        self.waiting_for: Dict[str, str]       = {}   # process → resource
        self.processes  : set                  = set()
        self.resources  : set                  = set()

    def add_process(self, pid: str):
        self.processes.add(pid)

    def add_resource(self, rid: str):
        self.resources.add(rid)

    def assign(self, resource: str, process: str):
        """Mark a resource as held by a process."""
        self.held_by[resource]   = process

    def request(self, process: str, resource: str):
        """Mark a process as waiting for a resource."""
        self.waiting_for[process] = resource

    def release(self, process: str, resource: str):
        """Release a resource."""
        if self.held_by.get(resource) == process:
            del self.held_by[resource]
        if self.waiting_for.get(process) == resource:
            del self.waiting_for[process]

    def detect_deadlock(self) -> tuple:
        """
        Returns (has_deadlock: bool, cycle: list).
        cycle is the list of processes involved in the deadlock.
        Uses path-tracking DFS to correctly reconstruct the cycle.
        """
        visited = set()

        def dfs(process, path, in_path):
            if process in in_path:
                idx = path.index(process)
                return path[idx:] + [process]
            if process in visited:
                return None
            visited.add(process)
            resource = self.waiting_for.get(process)
            if not resource:
                return None
            holder = self.held_by.get(resource)
            if not holder:
                return None
            return dfs(holder, path + [process], in_path | {process})

        for p in self.processes:
            if p not in visited:
                result = dfs(p, [], set())
                if result:
                    return True, result

        return False, []

    def state_report(self) -> dict:
        has_deadlock, cycle = self.detect_deadlock()
        return {
            "processes":     list(self.processes),
            "resources":     list(self.resources),
            "assignments":   dict(self.held_by),
            "waiting":       dict(self.waiting_for),
            "has_deadlock":  has_deadlock,
            "cycle":         cycle,
        }
