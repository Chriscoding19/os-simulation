"""
schedulers.py
-------------
Implements 5 classic CPU scheduling algorithms:

  1. FCFS   — First Come First Served (non-preemptive)
  2. SJF    — Shortest Job First (non-preemptive)
  3. SRTF   — Shortest Remaining Time First (preemptive SJF)
  4. Priority Scheduling (preemptive)
  5. Round Robin (preemptive, configurable quantum)
  6. MLFQ   — Multi-Level Feedback Queue
"""

import copy
from core.process import Process, ProcessState
from core.base_scheduler import BaseScheduler
from typing import List


# ══════════════════════════════════════════════════════════════════
# 1. FCFS — First Come First Served
# ══════════════════════════════════════════════════════════════════

class FCFSScheduler(BaseScheduler):
    """
    Non-preemptive. Processes run in arrival order.
    Simple but can cause convoy effect (short jobs stuck behind long ones).
    """

    def __init__(self):
        super().__init__("FCFS (First Come First Served)", preemptive=False)

    def run(self) -> List[dict]:
        gantt   = []
        time    = 0
        queue   = sorted(self.processes, key=lambda p: p.arrival_time)

        for p in queue:
            if time < p.arrival_time:
                time = p.arrival_time       # CPU idle until process arrives

            self._mark_start(p, time)
            gantt.append({"pid": p.pid, "name": p.name,
                          "start": time, "end": time + p.burst_time})
            time += p.burst_time
            p.cpu_used = p.burst_time
            p.remaining_time = 0
            self._mark_done(p, time)

        return gantt


# ══════════════════════════════════════════════════════════════════
# 2. SJF — Shortest Job First (non-preemptive)
# ══════════════════════════════════════════════════════════════════

class SJFScheduler(BaseScheduler):
    """
    Non-preemptive. At each scheduling point picks the process
    with the shortest total burst time from those available.
    Optimal for minimising average waiting time (non-preemptive).
    """

    def __init__(self):
        super().__init__("SJF (Shortest Job First)", preemptive=False)

    def run(self) -> List[dict]:
        gantt     = []
        time      = 0
        remaining = list(self.processes)
        completed = []

        while remaining:
            # Find all processes that have arrived
            available = [p for p in remaining if p.arrival_time <= time]

            if not available:
                time = min(p.arrival_time for p in remaining)
                continue

            # Pick shortest burst
            p = min(available, key=lambda x: x.burst_time)
            remaining.remove(p)

            self._mark_start(p, time)
            gantt.append({"pid": p.pid, "name": p.name,
                          "start": time, "end": time + p.burst_time})
            time += p.burst_time
            p.cpu_used = p.burst_time
            p.remaining_time = 0
            self._mark_done(p, time)

        return gantt


# ══════════════════════════════════════════════════════════════════
# 3. SRTF — Shortest Remaining Time First (Preemptive SJF)
# ══════════════════════════════════════════════════════════════════

class SRTFScheduler(BaseScheduler):
    """
    Preemptive version of SJF. At every time unit, picks the
    process with least remaining CPU time. Optimal average wait time
    but high context switching overhead.
    """

    def __init__(self):
        super().__init__("SRTF (Shortest Remaining Time First)", preemptive=True)

    def run(self) -> List[dict]:
        gantt       = []
        time        = 0
        processes   = self.processes
        n           = len(processes)
        completed   = 0
        current     = None
        last_pid    = -1
        seg_start   = 0

        max_time = sum(p.burst_time for p in processes) + max(p.arrival_time for p in processes) + 1

        while completed < n and time < max_time:
            available = [p for p in processes
                         if p.arrival_time <= time and p.remaining_time > 0]

            if not available:
                time += 1
                continue

            p = min(available, key=lambda x: x.remaining_time)

            if p.pid != last_pid:
                if last_pid != -1 and gantt:
                    gantt[-1]["end"] = time
                self._mark_start(p, time)
                gantt.append({"pid": p.pid, "name": p.name,
                              "start": time, "end": time + 1})
                if last_pid != -1:
                    # Increment context switches for the incoming process
                    p.context_switches += 1
                last_pid = p.pid
            else:
                gantt[-1]["end"] = time + 1

            p.remaining_time -= 1
            p.cpu_used       += 1

            if p.remaining_time == 0:
                self._mark_done(p, time + 1)
                completed += 1
                last_pid = -1

            time += 1

        return gantt


# ══════════════════════════════════════════════════════════════════
# 4. Priority Scheduling (Preemptive)
# ══════════════════════════════════════════════════════════════════

class PriorityScheduler(BaseScheduler):
    """
    Preemptive priority scheduling. Lower priority number = higher priority.
    Can cause starvation of low-priority processes.
    Uses aging to prevent starvation (priority improves over wait time).
    """

    def __init__(self, aging_interval: int = 10):
        super().__init__("Priority Scheduling (Preemptive)", preemptive=True)
        self.aging_interval = aging_interval

    def run(self) -> List[dict]:
        gantt     = []
        time      = 0
        processes = self.processes
        n         = len(processes)
        completed = 0
        last_pid  = -1

        # Effective priorities (can be improved by aging)
        eff_priority = {p.pid: p.priority for p in processes}
        wait_since   = {p.pid: p.arrival_time for p in processes}

        max_time = sum(p.burst_time for p in processes) + max(p.arrival_time for p in processes) + 1

        while completed < n and time < max_time:
            available = [p for p in processes
                         if p.arrival_time <= time and p.remaining_time > 0]

            if not available:
                time += 1
                continue

            # Apply aging — reduce effective priority every aging_interval ms of waiting
            for p in available:
                waited = time - wait_since.get(p.pid, time)
                if waited > 0 and waited % self.aging_interval == 0:
                    eff_priority[p.pid] = max(0, eff_priority[p.pid] - 1)

            p = min(available, key=lambda x: (eff_priority[x.pid], x.arrival_time))

            if p.pid != last_pid:
                if last_pid != -1:
                    p.context_switches += 1
                self._mark_start(p, time)
                gantt.append({"pid": p.pid, "name": p.name,
                              "start": time, "end": time + 1})
                last_pid = p.pid
            else:
                gantt[-1]["end"] = time + 1

            p.remaining_time -= 1
            p.cpu_used       += 1

            if p.remaining_time == 0:
                self._mark_done(p, time + 1)
                completed += 1
                last_pid = -1

            time += 1

        return gantt


# ══════════════════════════════════════════════════════════════════
# 5. Round Robin
# ══════════════════════════════════════════════════════════════════

class RoundRobinScheduler(BaseScheduler):
    """
    Time-sliced preemptive scheduler. Each process gets 'quantum' ms
    of CPU time before being preempted and moved to back of queue.
    Fair but adds overhead with many context switches.
    """

    def __init__(self, quantum: int = 4):
        super().__init__(f"Round Robin (quantum={quantum}ms)", preemptive=True)
        self.quantum = quantum

    def run(self) -> List[dict]:
        gantt     = []
        time      = 0
        processes = self.processes
        queue     = []
        remaining = sorted(processes, key=lambda p: p.arrival_time)
        arrived   = []
        idx       = 0          # pointer into remaining (by arrival)

        def enqueue_arrivals(t):
            nonlocal idx
            while idx < len(remaining) and remaining[idx].arrival_time <= t:
                if remaining[idx] not in arrived:
                    queue.append(remaining[idx])
                    arrived.append(remaining[idx])
                    remaining[idx].state = ProcessState.READY
                idx += 1

        enqueue_arrivals(0)

        while queue or idx < len(remaining):
            if not queue:
                # CPU idle — advance to next arrival
                time = remaining[idx].arrival_time
                enqueue_arrivals(time)

            if not queue:
                break

            p = queue.pop(0)
            self._mark_start(p, time)
            run_for = min(self.quantum, p.remaining_time)

            gantt.append({"pid": p.pid, "name": p.name,
                          "start": time, "end": time + run_for})

            p.remaining_time -= run_for
            p.cpu_used       += run_for
            time             += run_for

            enqueue_arrivals(time)

            if p.remaining_time == 0:
                self._mark_done(p, time)
            else:
                p.context_switches += 1
                p.state = ProcessState.READY
                queue.append(p)

        return gantt


# ══════════════════════════════════════════════════════════════════
# 6. MLFQ — Multi-Level Feedback Queue
# ══════════════════════════════════════════════════════════════════

class MLFQScheduler(BaseScheduler):
    """
    Multi-Level Feedback Queue — approximates SJF without knowing burst times.

    Levels:
      Q0: quantum=4ms  (highest priority — I/O bound, short jobs)
      Q1: quantum=8ms  (medium priority)
      Q2: FCFS         (lowest priority — CPU bound long jobs)

    Rules:
      - New jobs enter Q0
      - If a job uses its full quantum, demoted to next level
      - If a job voluntarily yields (I/O), stays at same level
      - Priority boost every boost_interval ms (prevents starvation)
    """

    def __init__(self, quantums: list = None, boost_interval: int = 50):
        super().__init__("MLFQ (Multi-Level Feedback Queue)", preemptive=True)
        self.quantums       = quantums or [4, 8, 16]
        self.boost_interval = boost_interval

    def run(self) -> List[dict]:
        gantt     = []
        time      = 0
        processes = self.processes
        n         = len(processes)
        completed = 0

        # 3 priority queues
        queues    = [[] for _ in self.quantums]
        p_level   = {}       # pid -> current queue level
        p_waited  = {}       # pid -> time entered current queue
        arrived   = set()
        sorted_ps = sorted(processes, key=lambda p: p.arrival_time)
        arr_idx   = 0

        def enqueue_new(t):
            nonlocal arr_idx
            while arr_idx < len(sorted_ps) and sorted_ps[arr_idx].arrival_time <= t:
                p = sorted_ps[arr_idx]
                if p.pid not in arrived:
                    queues[0].append(p)
                    p_level[p.pid]  = 0
                    p_waited[p.pid] = t
                    p.state = ProcessState.READY
                    arrived.add(p.pid)
                arr_idx += 1

        def priority_boost(t):
            """Move all non-completed processes back to Q0."""
            for level in range(1, len(queues)):
                for p in queues[level]:
                    queues[0].append(p)
                    p_level[p.pid] = 0
                queues[level].clear()

        enqueue_new(0)
        last_boost = 0

        max_time = sum(p.burst_time for p in processes) + max(p.arrival_time for p in processes) + 10

        while completed < n and time < max_time:
            enqueue_new(time)

            # Priority boost check
            if time - last_boost >= self.boost_interval and time > 0:
                priority_boost(time)
                last_boost = time

            # Find highest-priority non-empty queue
            p        = None
            level    = 0
            for lvl, q in enumerate(queues):
                if q:
                    p     = q.pop(0)
                    level = lvl
                    break

            if p is None:
                # All queues empty — advance time to next arrival
                if arr_idx < len(sorted_ps):
                    time = sorted_ps[arr_idx].arrival_time
                    enqueue_new(time)
                continue

            quantum  = self.quantums[level]
            run_for  = min(quantum, p.remaining_time)

            self._mark_start(p, time)
            gantt.append({"pid": p.pid, "name": p.name,
                          "start": time, "end": time + run_for,
                          "level": level})

            p.remaining_time -= run_for
            p.cpu_used       += run_for
            time             += run_for

            enqueue_new(time)

            if p.remaining_time == 0:
                self._mark_done(p, time)
                completed += 1
            else:
                # Demote if used full quantum
                if run_for == quantum:
                    next_level = min(level + 1, len(queues) - 1)
                    p.context_switches += 1
                else:
                    next_level = level   # Voluntary yield, stay at same level

                p_level[p.pid] = next_level
                queues[next_level].append(p)
                p.state = ProcessState.READY

        return gantt
