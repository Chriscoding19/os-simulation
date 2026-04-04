"""
memory.py
---------
Simulates OS memory management:

  - Physical memory divided into fixed-size frames
  - Virtual memory via paging (virtual → physical mapping)
  - Page replacement algorithms:
      * FIFO   — First In First Out
      * LRU    — Least Recently Used
      * Optimal — Belady's algorithm (theoretical best)
  - Tracks page faults, hit rate, and frame utilisation
"""

from collections import OrderedDict, deque
from typing import List, Optional


# ══════════════════════════════════════════════════════════════════
# PAGE TABLE ENTRY
# ══════════════════════════════════════════════════════════════════

class PageTableEntry:
    """One entry in the page table."""

    def __init__(self, page_num: int):
        self.page_num    = page_num
        self.frame_num   : Optional[int] = None
        self.present     : bool          = False   # In physical memory?
        self.dirty       : bool          = False   # Modified since loaded?
        self.referenced  : bool          = False   # Accessed recently?
        self.access_count: int           = 0

    def __repr__(self):
        return (f"PTE(page={self.page_num}, frame={self.frame_num}, "
                f"present={self.present}, dirty={self.dirty})")


# ══════════════════════════════════════════════════════════════════
# MEMORY MANAGER
# ══════════════════════════════════════════════════════════════════

class MemoryManager:
    """
    Simulates physical memory with frame management and page replacement.

    Parameters
    ----------
    n_frames   : Number of physical frames available
    page_size  : Size of each page/frame in KB
    """

    def __init__(self, n_frames: int = 4, page_size: int = 4):
        self.n_frames   = n_frames
        self.page_size  = page_size
        self.frames     = [None] * n_frames   # frame_num → page_num
        self.free_frames= list(range(n_frames))

    def allocate_frame(self, page_num: int) -> Optional[int]:
        """Allocate a free frame. Returns frame number or None if full."""
        if self.free_frames:
            frame = self.free_frames.pop(0)
            self.frames[frame] = page_num
            return frame
        return None

    def free_frame(self, frame_num: int):
        """Return a frame to the free list."""
        self.frames[frame_num] = None
        self.free_frames.append(frame_num)

    def is_full(self) -> bool:
        return len(self.free_frames) == 0

    def utilisation(self) -> float:
        used = sum(1 for f in self.frames if f is not None)
        return round(used / self.n_frames * 100, 1)


# ══════════════════════════════════════════════════════════════════
# BASE PAGE REPLACEMENT
# ══════════════════════════════════════════════════════════════════

class PageReplacementSimulator:
    """Base class for page replacement algorithms."""

    def __init__(self, n_frames: int, name: str):
        self.n_frames   = n_frames
        self.name       = name
        self.page_faults= 0
        self.page_hits  = 0
        self.log        = []

    def simulate(self, reference_string: List[int]) -> dict:
        raise NotImplementedError

    def _stats(self, n: int) -> dict:
        total = self.page_faults + self.page_hits
        return {
            "algorithm":    self.name,
            "n_frames":     self.n_frames,
            "n_references": n,
            "page_faults":  self.page_faults,
            "page_hits":    self.page_hits,
            "fault_rate":   round(self.page_faults / n * 100, 1) if n else 0,
            "hit_rate":     round(self.page_hits   / n * 100, 1) if n else 0,
            "log":          self.log,
        }


# ══════════════════════════════════════════════════════════════════
# FIFO PAGE REPLACEMENT
# ══════════════════════════════════════════════════════════════════

class FIFOPageReplacement(PageReplacementSimulator):
    """
    Replace the page that has been in memory the longest.
    Simple but can suffer from Belady's Anomaly (more frames → more faults).
    """

    def __init__(self, n_frames: int):
        super().__init__(n_frames, "FIFO")

    def simulate(self, ref_string: List[int]) -> dict:
        frames = []
        order  = deque()   # Tracks insertion order

        for ref in ref_string:
            if ref in frames:
                self.page_hits += 1
                status = "HIT "
            else:
                self.page_faults += 1
                status = "FAULT"
                if len(frames) < self.n_frames:
                    frames.append(ref)
                    order.append(ref)
                else:
                    victim = order.popleft()
                    frames[frames.index(victim)] = ref
                    order.append(ref)

            self.log.append({
                "ref": ref, "status": status,
                "frames": frames[:]
            })

        return self._stats(len(ref_string))


# ══════════════════════════════════════════════════════════════════
# LRU PAGE REPLACEMENT
# ══════════════════════════════════════════════════════════════════

class LRUPageReplacement(PageReplacementSimulator):
    """
    Replace the page that was Least Recently Used.
    Approximates optimal replacement. No Belady's anomaly.
    Uses an OrderedDict as an efficient LRU cache.
    """

    def __init__(self, n_frames: int):
        super().__init__(n_frames, "LRU")

    def simulate(self, ref_string: List[int]) -> dict:
        cache = OrderedDict()   # page → last access order

        for ref in ref_string:
            if ref in cache:
                self.page_hits += 1
                status = "HIT "
                cache.move_to_end(ref)   # Mark as most recently used
            else:
                self.page_faults += 1
                status = "FAULT"
                if len(cache) >= self.n_frames:
                    cache.popitem(last=False)   # Remove least recently used
                cache[ref] = True

            self.log.append({
                "ref": ref, "status": status,
                "frames": list(cache.keys())
            })

        return self._stats(len(ref_string))


# ══════════════════════════════════════════════════════════════════
# OPTIMAL PAGE REPLACEMENT (Belady's Algorithm)
# ══════════════════════════════════════════════════════════════════

class OptimalPageReplacement(PageReplacementSimulator):
    """
    Replace the page that will not be used for the longest time in future.
    Theoretical lower bound — requires knowing future references (not practical).
    Used as benchmark comparison for FIFO and LRU.
    """

    def __init__(self, n_frames: int):
        super().__init__(n_frames, "Optimal (Belady's)")

    def simulate(self, ref_string: List[int]) -> dict:
        frames = []

        for i, ref in enumerate(ref_string):
            if ref in frames:
                self.page_hits += 1
                status = "HIT "
            else:
                self.page_faults += 1
                status = "FAULT"
                if len(frames) < self.n_frames:
                    frames.append(ref)
                else:
                    # Find which page in frames is used farthest in future
                    future = ref_string[i+1:]
                    farthest     = -1
                    victim_page  = frames[0]

                    for page in frames:
                        if page not in future:
                            victim_page = page
                            break
                        next_use = future.index(page)
                        if next_use > farthest:
                            farthest    = next_use
                            victim_page = page

                    frames[frames.index(victim_page)] = ref

            self.log.append({
                "ref": ref, "status": status,
                "frames": frames[:]
            })

        return self._stats(len(ref_string))


# ══════════════════════════════════════════════════════════════════
# CONVENIENCE — Run all 3 algorithms on same reference string
# ══════════════════════════════════════════════════════════════════

def compare_page_replacement(ref_string: List[int], n_frames: int = 3) -> list:
    """Run FIFO, LRU, and Optimal on the same reference string."""
    algorithms = [
        FIFOPageReplacement(n_frames),
        LRUPageReplacement(n_frames),
        OptimalPageReplacement(n_frames),
    ]
    return [algo.simulate(ref_string) for algo in algorithms]


def generate_reference_string(n: int = 20, page_range: int = 8,
                               seed: int = 42) -> List[int]:
    """Generate a realistic reference string with locality of reference."""
    import random
    random.seed(seed)
    result = []
    current = random.randint(0, page_range - 1)
    for _ in range(n):
        # 70% chance of staying in same "working set" (locality)
        if random.random() < 0.7:
            current = (current + random.randint(-1, 1)) % page_range
        else:
            current = random.randint(0, page_range - 1)
        result.append(current)
    return result
