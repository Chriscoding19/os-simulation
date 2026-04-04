#!/usr/bin/env python3
"""
main.py — Operating Systems Simulation
========================================

Simulates core OS concepts:
  1. CPU Scheduling: FCFS, SJF, SRTF, Priority, Round Robin, MLFQ
  2. Synchronization: Mutex, Semaphore, Producer-Consumer, Dining Philosophers
  3. Deadlock Detection: Resource Allocation Graph + DFS cycle detection
  4. Memory Management: FIFO, LRU, Optimal page replacement

Usage:
  python3 main.py
  python3 main.py --no-report
"""

import argparse
import sys
import os
import time

sys.path.insert(0, os.path.dirname(__file__))

from core.process import make_process_set
from schedulers.schedulers import (
    FCFSScheduler, SJFScheduler, SRTFScheduler,
    PriorityScheduler, RoundRobinScheduler, MLFQScheduler,
)
from synchronization.synchronization import (
    run_producer_consumer, DiningPhilosophers, DeadlockDetector,
)
from memory.memory import compare_page_replacement, generate_reference_string
from reports.report_generator import generate_html_report


def parse_args():
    p = argparse.ArgumentParser(description="OS Simulation")
    p.add_argument("--no-report", action="store_true")
    return p.parse_args()


def print_header():
    print("\n" + "═"*65)
    print("   ⚙️  OPERATING SYSTEMS SIMULATION")
    print("   Scheduling · Synchronization · Memory Management")
    print("═"*65)


def section(title):
    print(f"\n┌─────────────────────────────────────────────────────────────┐")
    print(f"│  {title}")
    print(f"└─────────────────────────────────────────────────────────────┘")


def main():
    args  = parse_args()
    start = time.time()
    print_header()

    processes = make_process_set()

    # ── Step 1: CPU Scheduling ─────────────────────────────────────
    section("STEP 1/4 — CPU Scheduling Algorithms")

    print(f"\n  Process set ({len(processes)} processes):")
    print(f"  {'PID':<4} {'NAME':<20} {'BURST':>6} {'ARRIVE':>7} {'PRIORITY':>9}")
    print(f"  {'─'*4} {'─'*20} {'─'*6} {'─'*7} {'─'*9}")
    for p in processes:
        print(f"  P{p.pid:<3} {p.name:<20} {p.burst_time:>5}ms {p.arrival_time:>6}ms {p.priority_name:>9}")

    schedulers = [
        FCFSScheduler(),
        SJFScheduler(),
        SRTFScheduler(),
        PriorityScheduler(),
        RoundRobinScheduler(quantum=4),
        MLFQScheduler(),
    ]

    scheduler_results = []
    print(f"\n  {'ALGORITHM':<40} {'AVG WAIT':>9}  {'AVG TT':>7}  {'CTX SW':>7}  {'CPU UTIL':>9}")
    print(f"  {'─'*40} {'─'*9}  {'─'*7}  {'─'*7}  {'─'*9}")

    for sched in schedulers:
        sched.load(processes)
        gantt  = sched.run()
        result = sched.compute_metrics()
        result["gantt"] = gantt
        scheduler_results.append(result)
        print(f"  {result['scheduler']:<40} {result['avg_waiting']:>8.2f}ms"
              f"  {result['avg_turnaround']:>6.2f}ms"
              f"  {result['total_context_switches']:>7}"
              f"  {result['cpu_utilisation']:>8.1f}%")

    best = min(scheduler_results, key=lambda r: r["avg_waiting"])
    print(f"\n  🏆  Best avg wait: {best['scheduler']} ({best['avg_waiting']}ms)")

    # Per-process breakdown for best scheduler
    print(f"\n  Per-process metrics — {best['scheduler']}:")
    print(f"  {'PID':<4} {'NAME':<20} {'WAIT':>6} {'TT':>6} {'RESP':>6} {'CS':>4}")
    print(f"  {'─'*4} {'─'*20} {'─'*6} {'─'*6} {'─'*6} {'─'*4}")
    for p in best["processes"]:
        print(f"  P{p['pid']:<3} {p['name']:<20} {p['waiting_time']:>5}ms "
              f"{p['turnaround_time']:>5}ms {p['response_time']:>5}ms "
              f"{p['context_switches']:>4}")

    # Gantt chart (text)
    print(f"\n  Gantt Chart — {best['scheduler']}:")
    gantt_data = best["gantt"]
    makespan   = max(g["end"] for g in gantt_data)
    width      = 60
    bar        = ""
    for g in gantt_data:
        seg = max(1, round((g["end"]-g["start"]) / makespan * width))
        bar += f"[P{g['pid']}{'─'*max(0,seg-3)}]"
    print(f"  |{bar[:width*2]}|")
    print(f"  0ms{' '*(width-3)}{makespan}ms")

    # ── Step 2: Synchronization ────────────────────────────────────
    section("STEP 2/4 — Synchronization Primitives")

    print("\n  [Producer-Consumer — Bounded Buffer]")
    pc = run_producer_consumer(n_items=8, buffer_size=3, n_producers=2, n_consumers=2)
    print(f"  Items produced : {sorted(pc['produced'])}")
    print(f"  Items consumed : {sorted(pc['consumed'])}")
    print(f"  Buffer log (first 6 entries):")
    for line in pc["log"][:6]:
        print(f"    {line}")

    print("\n  [Dining Philosophers — Asymmetric Deadlock Prevention]")
    dp  = DiningPhilosophers(5)
    log = dp.run(meals_per_philosopher=2)
    for line in log[:10]:
        print(f"   {line}")
    print(f"    ... ({len(log)} total events)")

    # ── Step 3: Deadlock Detection ─────────────────────────────────
    section("STEP 3/4 — Deadlock Detection (Resource Allocation Graph)")

    # Scenario A: No deadlock
    print("\n  Scenario A: No deadlock")
    d = DeadlockDetector()
    for name in ["P1","P2","P3"]:   d.add_process(name)
    for name in ["R1","R2","R3"]:   d.add_resource(name)
    d.assign("R1","P1"); d.assign("R2","P2"); d.assign("R3","P3")
    d.request("P2","R1")    # P2 wants R1 (held by P1) — no cycle
    report_a = d.state_report()
    print(f"  Assignments : {report_a['assignments']}")
    print(f"  Waiting     : {report_a['waiting']}")
    print(f"  Deadlock    : {'🔴 YES — ' + str(report_a['cycle']) if report_a['has_deadlock'] else '🟢 No'}")

    # Scenario B: Deadlock
    print("\n  Scenario B: Deadlock (circular wait)")
    d2 = DeadlockDetector()
    for name in ["P1","P2","P3"]:   d2.add_process(name)
    for name in ["R1","R2","R3"]:   d2.add_resource(name)
    d2.assign("R1","P1"); d2.assign("R2","P2"); d2.assign("R3","P3")
    d2.request("P1","R2"); d2.request("P2","R3"); d2.request("P3","R1")  # Circular!
    report_b = d2.state_report()
    print(f"  Assignments : {report_b['assignments']}")
    print(f"  Waiting     : {report_b['waiting']}")
    print(f"  Deadlock    : {'🔴 YES — Cycle: ' + ' → '.join(report_b['cycle']) if report_b['has_deadlock'] else '🟢 No'}")

    # ── Step 4: Memory Management ──────────────────────────────────
    section("STEP 4/4 — Memory Management (Page Replacement)")

    ref_string = generate_reference_string(n=20, page_range=8)
    print(f"\n  Reference string (20 refs, pages 0-7): {ref_string}")

    print(f"\n  {'ALGORITHM':<25} {'FRAMES':>7}  {'FAULTS':>7}  {'HITS':>6}  {'FAULT RATE':>11}  {'HIT RATE':>9}")
    print(f"  {'─'*25} {'─'*7}  {'─'*7}  {'─'*6}  {'─'*11}  {'─'*9}")

    all_mem_results = []
    for n_frames in [3, 4]:
        results = compare_page_replacement(ref_string, n_frames)
        for r in results:
            all_mem_results.append(r)
            print(f"  {r['algorithm']:<25} {r['n_frames']:>7}  {r['page_faults']:>7}  "
                  f"{r['page_hits']:>6}  {r['fault_rate']:>10.1f}%  {r['hit_rate']:>8.1f}%")

    print(f"\n  ✓ Optimal always achieves fewest page faults (theoretical minimum)")
    print(f"  ✓ LRU approximates Optimal without needing future knowledge")

    # ── Report ─────────────────────────────────────────────────────
    sync_results = {
        "producer_consumer_log":   pc["log"],
        "dining_philosophers_log": log,
        "deadlock_report":         report_b,
    }

    os.makedirs("reports", exist_ok=True)
    if not args.no_report:
        html_path = generate_html_report(
            scheduler_results, sync_results, all_mem_results
        )
        print(f"\n  📊 Report saved: {html_path}")
        print(f"     explorer.exe {html_path}")

    elapsed = time.time() - start
    print(f"\n{'═'*65}")
    print(f"  ✅  Complete! Total time: {elapsed:.1f}s")
    print(f"{'═'*65}\n")


if __name__ == "__main__":
    main()
