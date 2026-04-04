"""
process.py
----------
Defines the Process class representing an OS process/thread,
with all state a real scheduler would track.
"""

import time
from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Optional


class ProcessState(Enum):
    NEW       = auto()
    READY     = auto()
    RUNNING   = auto()
    WAITING   = auto()
    TERMINATED = auto()


class Priority(Enum):
    CRITICAL = 0
    HIGH     = 1
    NORMAL   = 2
    LOW      = 3
    IDLE     = 4


@dataclass
class Process:
    """
    Represents an OS process with full scheduling metadata.

    Attributes
    ----------
    pid             : Unique process ID
    name            : Human-readable name
    burst_time      : Total CPU time needed (ms)
    arrival_time    : When process enters ready queue (ms)
    priority        : Scheduling priority (lower = higher priority)
    memory_required : RAM needed in MB
    io_bursts       : List of I/O wait times interspersed with CPU bursts
    """
    pid             : int
    name            : str
    burst_time      : int               # Total CPU time needed (ms)
    arrival_time    : int = 0           # When it arrives (ms)
    priority        : int = 2           # 0=Critical, 4=Idle
    memory_required : int = 64          # MB
    io_bursts       : list = field(default_factory=list)

    # ── Runtime tracking (set by scheduler) ───────────────────────
    state           : ProcessState = field(default=ProcessState.NEW, init=False)
    remaining_time  : int          = field(default=0,   init=False)
    start_time      : Optional[int]= field(default=None,init=False)
    finish_time     : Optional[int]= field(default=None,init=False)
    waiting_time    : int          = field(default=0,   init=False)
    response_time   : Optional[int]= field(default=None,init=False)
    turnaround_time : int          = field(default=0,   init=False)
    context_switches: int          = field(default=0,   init=False)
    cpu_used        : int          = field(default=0,   init=False)

    def __post_init__(self):
        self.remaining_time = self.burst_time
        self.state          = ProcessState.NEW

    # ── Computed metrics ───────────────────────────────────────────

    @property
    def completion_pct(self) -> float:
        if self.burst_time == 0:
            return 100.0
        return round((self.cpu_used / self.burst_time) * 100, 1)

    @property
    def priority_name(self) -> str:
        names = {0:"CRITICAL", 1:"HIGH", 2:"NORMAL", 3:"LOW", 4:"IDLE"}
        return names.get(self.priority, "NORMAL")

    def to_dict(self) -> dict:
        return {
            "pid":              self.pid,
            "name":             self.name,
            "burst_time":       self.burst_time,
            "arrival_time":     self.arrival_time,
            "priority":         self.priority,
            "priority_name":    self.priority_name,
            "memory_mb":        self.memory_required,
            "state":            self.state.name,
            "start_time":       self.start_time,
            "finish_time":      self.finish_time,
            "waiting_time":     self.waiting_time,
            "response_time":    self.response_time,
            "turnaround_time":  self.turnaround_time,
            "context_switches": self.context_switches,
            "cpu_used":         self.cpu_used,
        }

    def __repr__(self):
        return (f"Process(pid={self.pid}, name={self.name!r}, "
                f"burst={self.burst_time}ms, state={self.state.name})")


def make_process_set(seed: int = 42) -> list:
    """
    Returns a standard set of 8 processes used across all schedulers
    for fair comparison.
    """
    import random
    random.seed(seed)

    templates = [
        # name,               burst, arrival, priority, memory
        ("SystemInit",          4,     0,       0,       32),
        ("WebServer",          20,     1,       1,      128),
        ("DatabaseQuery",      16,     2,       1,      256),
        ("UserProcess_A",      10,     3,       2,       64),
        ("UserProcess_B",      14,     4,       2,       64),
        ("BackgroundSync",     30,     5,       3,       32),
        ("LogCollector",        8,     6,       3,       16),
        ("IdleTask",            6,    10,       4,        8),
    ]

    processes = []
    for i, (name, burst, arrival, priority, mem) in enumerate(templates):
        p = Process(
            pid=i+1, name=name, burst_time=burst,
            arrival_time=arrival, priority=priority,
            memory_required=mem,
        )
        processes.append(p)
    return processes
