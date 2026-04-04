"""
report_generator.py
--------------------
Generates a professional HTML report of the OS simulation results.
"""

import os
from datetime import datetime


def generate_html_report(scheduler_results: list, sync_results: dict,
                          memory_results: list, output_dir: str = "reports") -> str:
    os.makedirs(output_dir, exist_ok=True)
    ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.join(output_dir, f"os_simulation_report_{ts}.html")

    # ── Scheduler comparison table ─────────────────────────────────
    sched_rows = ""
    for r in scheduler_results:
        sched_rows += f"""
        <tr>
            <td><strong>{r['scheduler']}</strong></td>
            <td>{'✓ Preemptive' if r['preemptive'] else '✗ Non-preemptive'}</td>
            <td>{r['avg_waiting']}</td>
            <td>{r['avg_turnaround']}</td>
            <td>{r['avg_response']}</td>
            <td>{r['total_context_switches']}</td>
            <td>{r['cpu_utilisation']}%</td>
            <td>{r['makespan']}ms</td>
        </tr>"""

    # ── Gantt chart for best scheduler ────────────────────────────
    best = min(scheduler_results, key=lambda r: r['avg_waiting'])
    gantt_html = _build_gantt(best)

    # ── Per-process table for best scheduler ──────────────────────
    proc_rows = ""
    for p in best.get("processes", []):
        proc_rows += f"""
        <tr>
            <td>P{p['pid']}</td>
            <td>{p['name']}</td>
            <td>{p['burst_time']}ms</td>
            <td>{p['arrival_time']}ms</td>
            <td>{p['priority_name']}</td>
            <td>{p['start_time']}ms</td>
            <td>{p['finish_time']}ms</td>
            <td>{p['waiting_time']}ms</td>
            <td>{p['turnaround_time']}ms</td>
            <td>{p['response_time']}ms</td>
        </tr>"""

    # ── Memory comparison table ────────────────────────────────────
    mem_rows = ""
    for r in memory_results:
        mem_rows += f"""
        <tr>
            <td><strong>{r['algorithm']}</strong></td>
            <td>{r['n_frames']}</td>
            <td>{r['page_faults']}</td>
            <td>{r['page_hits']}</td>
            <td>{r['fault_rate']}%</td>
            <td>{r['hit_rate']}%</td>
        </tr>"""

    # ── Sync log ───────────────────────────────────────────────────
    pc_log = ""
    for line in sync_results.get("producer_consumer_log", [])[:20]:
        pc_log += f"<div class='log-line'>{line}</div>"

    phil_log = ""
    for line in sync_results.get("dining_philosophers_log", [])[:20]:
        phil_log += f"<div class='log-line'>{line}</div>"

    deadlock = sync_results.get("deadlock_report", {})
    dl_status = "🔴 DEADLOCK DETECTED" if deadlock.get("has_deadlock") else "🟢 No Deadlock"
    dl_cycle  = " → ".join(deadlock.get("cycle", [])) if deadlock.get("has_deadlock") else "None"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>OS Simulation Report</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: 'Segoe UI', system-ui, sans-serif; background: #0d1117; color: #c9d1d9; line-height: 1.6; }}
  .container {{ max-width: 1300px; margin: 0 auto; padding: 2rem; }}
  h1 {{ color: #58a6ff; font-size: 2rem; margin-bottom: 0.3rem; }}
  h2 {{ color: #79c0ff; font-size: 1.2rem; margin: 2rem 0 1rem; border-bottom: 1px solid #30363d; padding-bottom: 0.5rem; }}
  h3 {{ color: #79c0ff; font-size: 1rem; margin: 1.2rem 0 0.5rem; }}
  .meta {{ color: #8b949e; margin-bottom: 2rem; font-size: 0.9rem; }}
  .summary-grid {{ display: grid; grid-template-columns: repeat(auto-fit,minmax(140px,1fr)); gap: 1rem; margin-bottom: 2rem; }}
  .summary-card {{ background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 1.2rem; text-align: center; }}
  .summary-card .number {{ font-size: 1.8rem; font-weight: bold; }}
  .summary-card .label  {{ font-size: 0.75rem; color: #8b949e; text-transform: uppercase; }}
  table {{ width: 100%; border-collapse: collapse; background: #161b22; border-radius: 8px; overflow: hidden; border: 1px solid #30363d; margin-bottom: 1.5rem; font-size: 0.85rem; }}
  th {{ background: #21262d; color: #8b949e; text-align: left; padding: 0.6rem 0.8rem; font-size: 0.75rem; text-transform: uppercase; }}
  td {{ padding: 0.6rem 0.8rem; border-top: 1px solid #21262d; }}
  tr:hover td {{ background: #1c2128; }}
  .gantt-container {{ overflow-x: auto; margin-bottom: 1.5rem; }}
  .gantt {{ display: flex; height: 36px; align-items: center; min-width: 600px; border-radius: 4px; overflow: hidden; }}
  .gantt-block {{ display: flex; align-items: center; justify-content: center; font-size: 0.7rem; font-weight: bold; color: #fff; border-right: 1px solid rgba(0,0,0,0.3); white-space: nowrap; overflow: hidden; padding: 0 4px; }}
  .log-box {{ background: #161b22; border: 1px solid #30363d; border-radius: 6px; padding: 1rem; font-family: monospace; font-size: 0.8rem; max-height: 250px; overflow-y: auto; margin-bottom: 1rem; }}
  .log-line {{ padding: 0.15rem 0; border-bottom: 1px solid #21262d; color: #a8d8a8; }}
  .badge {{ display:inline-block; padding:0.2rem 0.5rem; border-radius:4px; font-size:0.75rem; font-weight:bold; }}
  .badge-green {{ background:#0d2a14; color:#3fb950; }}
  .badge-red   {{ background:#2a0d0d; color:#f85149; }}
  .card {{ background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 1.5rem; margin-bottom: 1.5rem; }}
</style>
</head>
<body>
<div class="container">
  <h1>⚙️ Operating Systems Simulation</h1>
  <div class="meta">Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")} &nbsp;|&nbsp; CPU Scheduling · Synchronization · Memory Management</div>

  <div class="summary-grid">
    <div class="summary-card"><div class="number" style="color:#58a6ff">{len(scheduler_results)}</div><div class="label">Schedulers</div></div>
    <div class="summary-card"><div class="number" style="color:#3fb950">{best['avg_waiting']}</div><div class="label">Best Avg Wait (ms)</div></div>
    <div class="summary-card"><div class="number" style="color:#d29922">{len(memory_results)}</div><div class="label">Page Algorithms</div></div>
    <div class="summary-card"><div class="number" style="color:#bc8cff">{'Yes' if deadlock.get('has_deadlock') else 'No'}</div><div class="label">Deadlock Found</div></div>
  </div>

  <h2>CPU Scheduling Algorithm Comparison</h2>
  <table>
    <thead><tr>
      <th>Algorithm</th><th>Type</th><th>Avg Wait</th><th>Avg Turnaround</th>
      <th>Avg Response</th><th>Context Switches</th><th>CPU Util</th><th>Makespan</th>
    </tr></thead>
    <tbody>{sched_rows}</tbody>
  </table>

  <h2>Gantt Chart — Best Scheduler: {best['scheduler']}</h2>
  <div class="gantt-container">{gantt_html}</div>

  <h3>Per-Process Metrics ({best['scheduler']})</h3>
  <table>
    <thead><tr>
      <th>PID</th><th>Name</th><th>Burst</th><th>Arrival</th><th>Priority</th>
      <th>Start</th><th>Finish</th><th>Wait</th><th>Turnaround</th><th>Response</th>
    </tr></thead>
    <tbody>{proc_rows}</tbody>
  </table>

  <h2>Memory Management — Page Replacement Algorithms</h2>
  <table>
    <thead><tr><th>Algorithm</th><th>Frames</th><th>Page Faults</th><th>Page Hits</th><th>Fault Rate</th><th>Hit Rate</th></tr></thead>
    <tbody>{mem_rows}</tbody>
  </table>

  <h2>Synchronization Primitives</h2>

  <div class="card">
    <h3>Producer-Consumer (Bounded Buffer)</h3>
    <p style="color:#8b949e;margin-bottom:0.8rem;font-size:0.85rem">
      Semaphore-based synchronization. Buffer capacity: 3. 2 producers, 2 consumers, 8 items.
    </p>
    <div class="log-box">{pc_log}</div>
  </div>

  <div class="card">
    <h3>Dining Philosophers (Asymmetric Solution)</h3>
    <p style="color:#8b949e;margin-bottom:0.8rem;font-size:0.85rem">
      5 philosophers, 5 forks. Deadlock prevented via asymmetric fork ordering.
    </p>
    <div class="log-box">{phil_log}</div>
  </div>

  <div class="card">
    <h3>Deadlock Detection (Resource Allocation Graph)</h3>
    <p style="color:#8b949e;margin-bottom:0.8rem;font-size:0.85rem">
      DFS-based cycle detection on the resource allocation graph.
    </p>
    <p><strong>Status:</strong> {dl_status}</p>
    <p><strong>Cycle:</strong> <code style="color:#d29922">{dl_cycle}</code></p>
    <br>
    <p><strong>Assignments:</strong> {deadlock.get('assignments', {})}</p>
    <p><strong>Waiting:</strong> {deadlock.get('waiting', {})}</p>
  </div>
</div>
</body>
</html>"""

    with open(filename, "w") as f:
        f.write(html)
    return filename


GANTT_COLORS = [
    "#388bfd","#3fb950","#d29922","#f85149","#bc8cff",
    "#58a6ff","#79c0ff","#56d364","#e3b341","#ff7b72",
]


def _build_gantt(result: dict) -> str:
    """Build an inline HTML Gantt chart from scheduler gantt data."""
    gantt_data = result.get("gantt", [])
    if not gantt_data:
        return "<p style='color:#8b949e'>No Gantt data available</p>"

    makespan = max(g["end"] for g in gantt_data)
    if makespan == 0:
        return ""

    # Assign color per PID
    pids   = list({g["pid"] for g in gantt_data})
    colors = {pid: GANTT_COLORS[i % len(GANTT_COLORS)] for i, pid in enumerate(sorted(pids))}

    blocks = ""
    for g in gantt_data:
        width_pct = (g["end"] - g["start"]) / makespan * 100
        if width_pct < 0.5:
            continue
        color    = colors[g["pid"]]
        label    = g["name"].split("_")[0][:8]
        gname    = g["name"]
        gstart   = g["start"]
        gend     = g["end"]
        blocks  += (f'<div class="gantt-block" style="width:{width_pct:.1f}%;'
                    f'background:{color};min-width:4px" '
                    f'title="{gname} ({gstart}-{gend}ms)">'
                    f'{label}</div>')

    legend = " ".join(
        f'<span style="background:{colors[pid]};padding:2px 8px;border-radius:3px;'
        f'font-size:0.75rem;margin:2px;display:inline-block">'
        f'P{pid}</span>'
        for pid in sorted(pids)
    )

    return f"""
    <div class="gantt">{blocks}</div>
    <div style="margin-top:0.5rem;font-size:0.75rem;color:#8b949e">0ms → {makespan}ms</div>
    <div style="margin-top:0.5rem">{legend}</div>
    """
