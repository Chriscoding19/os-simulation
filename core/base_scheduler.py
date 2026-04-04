"""
base_scheduler.py
-----------------
Abstract base class for all CPU scheduling algorithms.
Defines the interface and shared metric computation.
"""

import copy
from abc import ABC, abstractmethod
from core.process import Process, ProcessState
from typing import List, Optional


class BaseScheduler(ABC):
    """
    Abstract base for CPU scheduling algorithms.
    All schedulers share the same metric computation — only
    the scheduling logic differs.
    """

    def __init__(self, name: str, preemptive: bool = False):
        self.name       = name
        self.preemptive = preemptive
        self.timeline   = []   # List of (time, pid, event) tuples
        self.processes  = []

    def load(self, processes: List[Process]):
        """Deep-copy processes so original list stays unmodified."""
        self.processes = [copy.deepcopy(p) for p in processes]
        for p in self.processes:
            p.state = ProcessState.NEW

    @abstractmethod
    def run(self) -> List[dict]:
        """
        Execute the scheduling algorithm.
        Returns list of Gantt chart entries:
          {'pid': int, 'name': str, 'start': int, 'end': int}
        """
        pass

    def compute_metrics(self) -> dict:
        """
        Compute average scheduling metrics across all processes.
        Called after run().
        """
        total_wt  = sum(p.waiting_time     for p in self.processes)
        total_tt  = sum(p.turnaround_time  for p in self.processes)
        total_rt  = sum(p.response_time    for p in self.processes
                        if p.response_time is not None)
        total_cs  = sum(p.context_switches for p in self.processes)
        n         = len(self.processes)

        makespan  = max((p.finish_time for p in self.processes
                         if p.finish_time is not None), default=0)
        total_cpu = sum(p.burst_time for p in self.processes)
        cpu_util  = round(total_cpu / makespan * 100, 1) if makespan > 0 else 0.0

        return {
            "scheduler":        self.name,
            "preemptive":       self.preemptive,
            "n_processes":      n,
            "avg_waiting":      round(total_wt / n, 2),
            "avg_turnaround":   round(total_tt / n, 2),
            "avg_response":     round(total_rt / n, 2),
            "total_context_switches": total_cs,
            "makespan":         makespan,
            "cpu_utilisation":  cpu_util,
            "throughput":       round(n / makespan, 4) if makespan > 0 else 0,
            "processes":        [p.to_dict() for p in self.processes],
        }

    def _mark_start(self, p: Process, time: int):
        if p.start_time is None:
            p.start_time   = time
            p.response_time = time - p.arrival_time
        p.state = ProcessState.RUNNING

    def _mark_done(self, p: Process, time: int):
        p.finish_time     = time
        p.turnaround_time = time - p.arrival_time
        p.waiting_time    = p.turnaround_time - p.burst_time
        p.state           = ProcessState.TERMINATED
