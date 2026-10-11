# Operating Systems Simulation

Simulates core OS concepts: CPU scheduling algorithms, synchronization primitives, deadlock detection, and memory management — all in pure Python with zero external dependencies.

---

## Architecture

```
os-simulation/
├── main.py                              ← Full pipeline entry point
├── requirements.txt                     ← No external deps!
├── core/
│   ├── process.py                       ← Process class with full scheduling metadata
│   └── base_scheduler.py                ← Abstract base + shared metric computation
├── schedulers/
│   └── schedulers.py                    ← 6 scheduling algorithms
├── synchronization/
│   └── synchronization.py               ← Mutex, Semaphore, Producer-Consumer, Dining Philosophers, Deadlock Detector
├── memory/
│   └── memory.py                        ← FIFO, LRU, Optimal page replacement
├── reports/
│   └── report_generator.py              ← HTML report with Gantt chart
└── tests/
    └── test_os_simulation.py            ← 30 unit tests (all passing)
```

---

## Quick Start

```bash
# No dependencies needed - pure Python stdlib!
python3 main.py

# Run unit tests
python3 tests/test_os_simulation.py

# View report
explorer.exe reports/os_simulation_report_*.html
```

---

## CPU Scheduling Algorithms (6)

| Algorithm | Type | Description |
|---|---|---|
| **FCFS** | Non-preemptive | First Come First Served - simplest, convoy effect risk |
| **SJF** | Non-preemptive | Shortest Job First - optimal avg wait (non-preemptive) |
| **SRTF** | Preemptive | Shortest Remaining Time - optimal avg wait overall |
| **Priority** | Preemptive | Priority-based with aging (prevents starvation) |
| **Round Robin** | Preemptive | Time-sliced, quantum=4ms - fair, high context switching |
| **MLFQ** | Preemptive | Multi-Level Feedback Queue - approximates SJF without prior knowledge |

### Metrics Computed Per Scheduler
- Average waiting time
- Average turnaround time
- Average response time
- Total context switches
- CPU utilisation %
- Throughput (processes/ms)

---

## Synchronization Primitives

### Mutex
- Mutual exclusion lock with holder tracking and history log

### Semaphore
- Counting semaphore - P() wait / V() signal operations

### Read-Write Lock
- Multiple concurrent readers OR single exclusive writer

### Producer-Consumer (Bounded Buffer)
- Semaphore-based solution (empty, full, mutex semaphores)
- Configurable buffer capacity, producer/consumer counts

### Dining Philosophers
- 5 philosophers, 5 forks
- **Asymmetric solution**: even philosophers take left→right, odd take right→left
- Breaks circular wait condition - guaranteed deadlock-free

### Deadlock Detection
- Resource Allocation Graph (RAG)
- DFS cycle detection
- Demonstrates both deadlock and non-deadlock scenarios

---

## Memory Management — Page Replacement (3 Algorithms)

| Algorithm | Description | Belady's Anomaly? |
|---|---|---|
| **FIFO** | Evict oldest page | Yes |
| **LRU** | Evict least recently used | No |
| **Optimal** | Evict page not needed soonest (theoretical) | No |

Simulated on a 20-reference string with locality of reference.

---

## Technologies

- **Language**: Python 3.8+ (zero external dependencies)
- **Concurrency**: `threading` module for synchronization demos
- **Algorithms**: FCFS, SJF, SRTF, Priority, RR, MLFQ, FIFO, LRU, Optimal
- **Output**: Terminal + HTML report with visual Gantt chart
