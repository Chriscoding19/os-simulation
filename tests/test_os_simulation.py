"""
tests/test_os_simulation.py
---------------------------
Unit tests for the OS Simulation project.

Run with:
  python3 tests/test_os_simulation.py
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.process import Process, ProcessState, make_process_set
from schedulers.schedulers import (
    FCFSScheduler, SJFScheduler, SRTFScheduler,
    PriorityScheduler, RoundRobinScheduler, MLFQScheduler,
)
from memory.memory import (
    FIFOPageReplacement, LRUPageReplacement, OptimalPageReplacement,
    compare_page_replacement, generate_reference_string,
)
from synchronization.synchronization import (
    Mutex, Semaphore, DeadlockDetector,
    run_producer_consumer, DiningPhilosophers,
)


# ── Helper ─────────────────────────────────────────────────────────

def simple_processes():
    return [
        Process(pid=1, name="P1", burst_time=10, arrival_time=0),
        Process(pid=2, name="P2", burst_time=5,  arrival_time=2),
        Process(pid=3, name="P3", burst_time=8,  arrival_time=4),
    ]


# ══════════════════════════════════════════════════════════════════
# PROCESS TESTS
# ══════════════════════════════════════════════════════════════════

class TestProcess(unittest.TestCase):

    def test_initial_state(self):
        p = Process(pid=1, name="Test", burst_time=10)
        self.assertEqual(p.state, ProcessState.NEW)
        self.assertEqual(p.remaining_time, 10)

    def test_completion_pct_zero(self):
        p = Process(pid=1, name="Test", burst_time=10)
        self.assertEqual(p.completion_pct, 0.0)

    def test_completion_pct_half(self):
        p = Process(pid=1, name="Test", burst_time=10)
        p.cpu_used = 5
        self.assertEqual(p.completion_pct, 50.0)

    def test_priority_name(self):
        p = Process(pid=1, name="Test", burst_time=5, priority=0)
        self.assertEqual(p.priority_name, "CRITICAL")
        p.priority = 4
        self.assertEqual(p.priority_name, "IDLE")

    def test_to_dict(self):
        p   = Process(pid=1, name="Test", burst_time=10)
        d   = p.to_dict()
        self.assertIn("pid", d)
        self.assertIn("burst_time", d)
        self.assertIn("state", d)

    def test_make_process_set(self):
        ps = make_process_set()
        self.assertEqual(len(ps), 8)
        self.assertTrue(all(isinstance(p, Process) for p in ps))


# ══════════════════════════════════════════════════════════════════
# SCHEDULER TESTS
# ══════════════════════════════════════════════════════════════════

class TestFCFS(unittest.TestCase):

    def setUp(self):
        self.sched = FCFSScheduler()
        self.sched.load(simple_processes())
        self.gantt = self.sched.run()

    def test_all_processes_complete(self):
        for p in self.sched.processes:
            self.assertEqual(p.state, ProcessState.TERMINATED)

    def test_gantt_covers_all_cpu_time(self):
        total = sum(g["end"] - g["start"] for g in self.gantt)
        expected = sum(p.burst_time for p in self.sched.processes)
        self.assertEqual(total, expected)

    def test_no_overlap(self):
        sorted_g = sorted(self.gantt, key=lambda g: g["start"])
        for i in range(len(sorted_g)-1):
            self.assertLessEqual(sorted_g[i]["end"], sorted_g[i+1]["start"])

    def test_metrics(self):
        m = self.sched.compute_metrics()
        self.assertGreaterEqual(m["avg_waiting"], 0)
        self.assertGreater(m["avg_turnaround"], 0)
        self.assertGreater(m["cpu_utilisation"], 0)

    def test_arrival_order(self):
        # FCFS — first process should be scheduled first
        self.assertEqual(self.gantt[0]["pid"], 1)


class TestSJF(unittest.TestCase):

    def setUp(self):
        self.sched = SJFScheduler()
        self.sched.load(simple_processes())
        self.gantt = self.sched.run()

    def test_all_complete(self):
        for p in self.sched.processes:
            self.assertEqual(p.state, ProcessState.TERMINATED)

    def test_shorter_job_before_longer(self):
        # P2 (burst=5) arrives at t=2, P3 (burst=8) at t=4
        # After P1 finishes at t=10, P2 should run before P3
        pids = [g["pid"] for g in self.gantt]
        idx2 = pids.index(2)
        idx3 = pids.index(3)
        self.assertLess(idx2, idx3)


class TestSRTF(unittest.TestCase):

    def test_all_complete(self):
        sched = SRTFScheduler()
        sched.load(simple_processes())
        sched.run()
        for p in sched.processes:
            self.assertEqual(p.state, ProcessState.TERMINATED)

    def test_preemptive(self):
        self.assertTrue(SRTFScheduler().preemptive)

    def test_metrics_valid(self):
        sched = SRTFScheduler()
        sched.load(make_process_set())
        sched.run()
        m = sched.compute_metrics()
        self.assertGreater(m["avg_waiting"], 0)


class TestPriorityScheduler(unittest.TestCase):

    def test_all_complete(self):
        sched = PriorityScheduler()
        sched.load(make_process_set())
        sched.run()
        for p in sched.processes:
            self.assertEqual(p.state, ProcessState.TERMINATED)

    def test_higher_priority_runs_first(self):
        processes = [
            Process(pid=1, name="Low",  burst_time=10, arrival_time=0, priority=3),
            Process(pid=2, name="High", burst_time=10, arrival_time=0, priority=0),
        ]
        sched = PriorityScheduler()
        sched.load(processes)
        gantt = sched.run()
        self.assertEqual(gantt[0]["pid"], 2)


class TestRoundRobin(unittest.TestCase):

    def setUp(self):
        self.sched = RoundRobinScheduler(quantum=4)
        self.sched.load(make_process_set())
        self.gantt = self.sched.run()

    def test_all_complete(self):
        for p in self.sched.processes:
            self.assertEqual(p.state, ProcessState.TERMINATED)

    def test_no_single_run_exceeds_quantum(self):
        for g in self.gantt:
            self.assertLessEqual(g["end"] - g["start"], 4)

    def test_total_cpu_time_correct(self):
        total = sum(g["end"] - g["start"] for g in self.gantt)
        expected = sum(p.burst_time for p in self.sched.processes)
        self.assertEqual(total, expected)


class TestMLFQ(unittest.TestCase):

    def test_all_complete(self):
        sched = MLFQScheduler()
        sched.load(make_process_set())
        sched.run()
        for p in sched.processes:
            self.assertEqual(p.state, ProcessState.TERMINATED)

    def test_metrics(self):
        sched = MLFQScheduler()
        sched.load(make_process_set())
        sched.run()
        m = sched.compute_metrics()
        self.assertGreater(m["makespan"], 0)
        self.assertGreater(m["cpu_utilisation"], 0)


# ══════════════════════════════════════════════════════════════════
# MEMORY TESTS
# ══════════════════════════════════════════════════════════════════

class TestPageReplacement(unittest.TestCase):

    def setUp(self):
        self.ref = [1,2,3,4,1,2,5,1,2,3,4,5]
        self.n_frames = 3

    def test_fifo_faults(self):
        r = FIFOPageReplacement(self.n_frames).simulate(self.ref)
        self.assertGreater(r["page_faults"], 0)
        self.assertEqual(r["page_faults"] + r["page_hits"], len(self.ref))

    def test_lru_faults(self):
        r = LRUPageReplacement(self.n_frames).simulate(self.ref)
        self.assertGreater(r["page_faults"], 0)

    def test_optimal_faults(self):
        r = OptimalPageReplacement(self.n_frames).simulate(self.ref)
        self.assertGreater(r["page_faults"], 0)

    def test_optimal_le_lru_le_fifo_or_equal(self):
        fifo = FIFOPageReplacement(self.n_frames).simulate(self.ref)["page_faults"]
        lru  = LRUPageReplacement(self.n_frames).simulate(self.ref)["page_faults"]
        opt  = OptimalPageReplacement(self.n_frames).simulate(self.ref)["page_faults"]
        # Optimal always has fewest or equal page faults
        self.assertLessEqual(opt, fifo)
        self.assertLessEqual(opt, lru)

    def test_hit_rate_plus_fault_rate_equals_100(self):
        r = LRUPageReplacement(self.n_frames).simulate(self.ref)
        self.assertAlmostEqual(r["hit_rate"] + r["fault_rate"], 100.0, delta=0.1)

    def test_compare_returns_three_results(self):
        results = compare_page_replacement(self.ref, self.n_frames)
        self.assertEqual(len(results), 3)

    def test_reference_string_length(self):
        ref = generate_reference_string(n=20, page_range=8)
        self.assertEqual(len(ref), 20)
        self.assertTrue(all(0 <= p < 8 for p in ref))


# ══════════════════════════════════════════════════════════════════
# SYNCHRONIZATION TESTS
# ══════════════════════════════════════════════════════════════════

class TestMutex(unittest.TestCase):

    def test_acquire_release(self):
        m = Mutex("test")
        self.assertTrue(m.acquire("T1"))
        self.assertEqual(m.holder, "T1")
        m.release()
        self.assertIsNone(m.holder)

    def test_history_recorded(self):
        m = Mutex("test")
        m.acquire("T1")
        m.release()
        self.assertEqual(len(m.history), 2)
        self.assertEqual(m.history[0][0], "ACQUIRE")
        self.assertEqual(m.history[1][0], "RELEASE")


class TestSemaphore(unittest.TestCase):

    def test_initial_count(self):
        s = Semaphore(3, "test")
        self.assertEqual(s.count, 3)

    def test_wait_decrements(self):
        s = Semaphore(3, "test")
        s.wait("T1")
        self.assertEqual(s.count, 2)

    def test_signal_increments(self):
        s = Semaphore(1, "test")
        s.wait("T1")
        s.signal("T1")
        self.assertEqual(s.count, 1)


class TestDeadlockDetector(unittest.TestCase):

    def test_no_deadlock(self):
        d = DeadlockDetector()
        d.add_process("P1"); d.add_process("P2")
        d.add_resource("R1"); d.add_resource("R2")
        d.assign("R1", "P1")
        d.assign("R2", "P2")
        has_dl, cycle = d.detect_deadlock()
        self.assertFalse(has_dl)

    def test_deadlock_detected(self):
        d = DeadlockDetector()
        d.add_process("P1"); d.add_process("P2")
        d.add_resource("R1"); d.add_resource("R2")
        d.assign("R1", "P1")   # P1 holds R1
        d.assign("R2", "P2")   # P2 holds R2
        d.request("P1", "R2")  # P1 wants R2 (held by P2)
        d.request("P2", "R1")  # P2 wants R1 (held by P1) → DEADLOCK
        has_dl, cycle = d.detect_deadlock()
        self.assertTrue(has_dl)
        self.assertIn("P1", cycle)
        self.assertIn("P2", cycle)

    def test_three_process_deadlock(self):
        d = DeadlockDetector()
        for i in range(1, 4):
            d.add_process(f"P{i}"); d.add_resource(f"R{i}")
        d.assign("R1","P1"); d.assign("R2","P2"); d.assign("R3","P3")
        d.request("P1","R2"); d.request("P2","R3"); d.request("P3","R1")
        has_dl, _ = d.detect_deadlock()
        self.assertTrue(has_dl)

    def test_producer_consumer_runs(self):
        result = run_producer_consumer(n_items=6, buffer_size=3)
        self.assertEqual(len(result["consumed"]), 6)
        self.assertEqual(sorted(result["consumed"]), list(range(1, 7)))

    def test_dining_philosophers_no_deadlock(self):
        dp  = DiningPhilosophers(5)
        log = dp.run(meals_per_philosopher=1)
        self.assertGreater(len(log), 0)
        # All philosophers should have eaten
        eating = [l for l in log if "EATING" in l]
        self.assertEqual(len(eating), 5)


if __name__ == "__main__":
    print("Running OS Simulation tests...\n")
    loader = unittest.TestLoader()
    suite  = unittest.TestSuite()
    for cls in [TestProcess, TestFCFS, TestSJF, TestSRTF, TestPriorityScheduler,
                TestRoundRobin, TestMLFQ, TestPageReplacement, TestMutex,
                TestSemaphore, TestDeadlockDetector]:
        suite.addTests(loader.loadTestsFromTestCase(cls))
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
