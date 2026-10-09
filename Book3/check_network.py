#!/usr/bin/env python3
"""
check_network.py — the Lost Signal choice network holds together.

Plays every possible reader through network.yaml, tracking the Mission
Log and both clocks exactly as a reader would, and reports:

  · broken links, pages with no way out, routes with no fallback
  · pages no reader can ever reach
  · endings no reader can ever reach
  · loops a reader could get stuck in forever
  · how many distinct playthroughs end at each ending

    python Book3/check_network.py                 # exit non-zero on a problem
    python Book3/check_network.py --map           # also write page_map.md
    python Book3/check_network.py --mermaid       # also write network.mmd

Only needs PyYAML. A full run takes about two minutes.
"""

from __future__ import annotations

import argparse
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
NETWORK = HERE / "network.yaml"

State = tuple  # (node_id, frozenset(flags), launch, daylight)


# ── loading and static checks ──────────────────────────────────────────

def load(path: Path) -> dict:
    with path.open() as f:
        return yaml.safe_load(f)


def exits(node: dict) -> list[str]:
    if "choices" in node:
        return [c["to"] for c in node["choices"]]
    if "route" in node:
        return [r["to"] for r in node["route"]]
    if "next" in node:
        return [node["next"]]
    return []


def static_problems(net: dict) -> list[str]:
    nodes, flags = net["nodes"], set(net["flags"])
    problems = []
    if net["start"] not in nodes:
        problems.append(f"start page {net['start']} does not exist")
    for nid, node in nodes.items():
        ways = [k for k in ("choices", "route", "next", "ending") if k in node]
        if len(ways) != 1:
            problems.append(f"{nid}: needs exactly one of choices/route/next/ending, has {ways or 'none'}")
        for target in exits(node):
            if target not in nodes:
                problems.append(f"{nid}: leads to missing page {target}")
        if "route" in node and "if" in node["route"][-1]:
            problems.append(f"{nid}: last route entry needs no `if` (it's the fallback)")
        if "choices" in node and len(node["choices"]) < 2:
            problems.append(f"{nid}: a choice page needs at least two choices")
        for flag in node.get("sets", []) + node.get("clears", []):
            if flag not in flags:
                problems.append(f"{nid}: unknown Mission Log box {flag}")
        for entry in node.get("route", []):
            for cond in entry.get("if", []):
                name = cond.lstrip("!")
                if ">=" not in name and name not in flags:
                    problems.append(f"{nid}: route tests unknown box {name}")
        for clock in node.get("cost", {}):
            if clock not in net["clocks"]:
                problems.append(f"{nid}: unknown clock {clock}")
    return problems


# ── playing it ─────────────────────────────────────────────────────────

def holds(cond: str, flags: frozenset, launch: int, daylight: int) -> bool:
    if ">=" in cond:
        clock, n = cond.split(">=")
        return {"launch": launch, "daylight": daylight}[clock.strip()] >= int(n)
    if cond.startswith("!"):
        return cond[1:] not in flags
    return cond in flags


def relevance(net: dict) -> dict[str, frozenset]:
    """For each page, every box or clock some page from here on still tests.

    Two readers on the same page who differ only in boxes nobody will look
    at again read the rest of the book identically, so they share a state.
    Without this the number of states is every combination of ticks.
    """
    nodes = net["nodes"]
    reads = {i: {c.lstrip("!").split(">=")[0].strip()
                 for r in n.get("route", []) for c in r.get("if", [])}
             for i, n in nodes.items()}
    rel = {i: set(r) for i, r in reads.items()}
    changed = True
    while changed:
        changed = False
        for i, n in nodes.items():
            for t in exits(n):
                if not rel[t] <= rel[i]:
                    rel[i] |= rel[t]
                    changed = True
    return {i: frozenset(r) for i, r in rel.items()}


def arrive(net: dict, nid: str, flags: frozenset, launch: int, daylight: int) -> State:
    node = net["nodes"][nid]
    flags = (flags - set(node.get("clears", []))) | set(node.get("sets", []))
    cost = node.get("cost", {})
    cap = net["clocks"]
    launch = min(launch + cost.get("launch", 0), cap["launch"]["boxes"])
    daylight = min(daylight + cost.get("daylight", 0), cap["daylight"]["boxes"])
    rel = net["_relevant"][nid]
    return (nid, frozenset(flags) & rel,
            launch if "launch" in rel else 0,
            daylight if "daylight" in rel else 0)


def successors(net: dict, state: State) -> list[State]:
    nid, flags, launch, daylight = state
    node = net["nodes"][nid]
    if "choices" in node:
        targets = [c["to"] for c in node["choices"]]
    elif "route" in node:
        targets = [next(r["to"] for r in node["route"]
                        if all(holds(c, flags, launch, daylight) for c in r.get("if", [])))]
    elif "next" in node:
        targets = [node["next"]]
    else:
        targets = []
    return [arrive(net, t, flags, launch, daylight) for t in targets]


def play(net: dict):
    """Explore every reachable state; count playthroughs per ending."""
    start = arrive(net, net["start"], frozenset(), 0, 0)
    seen, order, stack = {start}, [], [start]
    graph: dict[State, list[State]] = {}
    while stack:
        s = stack.pop()
        order.append(s)
        graph[s] = successors(net, s)
        for t in graph[s]:
            if t not in seen:
                seen.add(t)
                stack.append(t)

    # A cycle in the state graph is a loop a reader can repeat forever
    # with nothing changing — not a page they revisit with new boxes.
    WHITE, GREY, BLACK = 0, 1, 2
    colour = defaultdict(int)
    loops = []
    sys.setrecursionlimit(100_000)

    def visit(s):
        colour[s] = GREY
        for t in graph[s]:
            if colour[t] == GREY:
                loops.append((s[0], t[0]))
            elif colour[t] == WHITE:
                visit(t)
        colour[s] = BLACK

    visit(start)

    paths: dict[State, Counter] = {}

    def count(s) -> Counter:
        if s in paths:
            return paths[s]
        paths[s] = Counter()  # guard; loops are reported separately
        node = net["nodes"][s[0]]
        if "ending" in node:
            result = Counter({s[0]: 1})
        else:
            result = Counter()
            for t in graph[s]:
                result.update(count(t))
        paths[s] = result
        return result

    return seen, count(start), loops


# ── rendering ──────────────────────────────────────────────────────────

ACT_NAMES = {1: "Act 1 — The Night Before", 2: "Act 2 — Launch Morning",
             3: "Act 3 — The Flight", 4: "Act 4 — The Search", 0: "Endings"}


def cell(s: str) -> str:
    return " ".join(str(s).split()).replace("|", "\\|")


def page_map(net: dict, totals: Counter) -> str:
    nodes = net["nodes"]
    out = ["# SPARK! Lost Signal — Page Map",
           "",
           "_Generated from `network.yaml` by `check_network.py --map`. "
           "Edit the YAML, not this file._",
           "",
           "**Legend:** ✚ ticks a Mission Log box · ✖ erases one · "
           "⏱ crosses out clock boxes · ⚙ the book routes you from your Mission Log",
           ""]
    for act in (1, 2, 3, 4, 0):
        ids = [i for i, n in nodes.items() if n["act"] == act]
        out += [f"## {ACT_NAMES[act]}", ""]
        if act == 0:
            out += ["| Ending | Tier | Playthroughs | What happened |", "|---|---|---|---|"]
            for i in ids:
                n = nodes[i]
                out.append(f"| **{n['ending']['title']}** `{i}` | {n['ending']['tier']} "
                           f"| {totals.get(i, 0):,} | {cell(n['summary'])} |")
            out.append("")
            continue
        out += ["| Page | What happens | Ticks / clock | Where it goes |", "|---|---|---|---|"]
        for i in ids:
            n = nodes[i]
            marks = [f"✚ {f}" for f in n.get("sets", [])]
            marks += [f"✖ {f}" for f in n.get("clears", [])]
            marks += [f"⏱ {k} +{v}" for k, v in n.get("cost", {}).items()]
            if "choices" in n:
                goes = "<br>".join(f"→ `{c['to']}` {cell(c['text'])}" for c in n["choices"])
            elif "route" in n:
                goes = "<br>".join(
                    f"⚙ {' & '.join(r['if']) if 'if' in r else 'otherwise'} → `{r['to']}`"
                    for r in n["route"])
            else:
                goes = f"→ `{n['next']}`"
            title = f"**{cell(n['title'])}** `{i}`"
            if n.get("steam"):
                title += f" [{n['steam']}]"
            if n.get("note"):
                title += f"<br>_Note: {cell(n['note'])}_"
            out.append(f"| {title} | {cell(n['summary'])} | {'<br>'.join(marks)} | {goes} |")
        out.append("")
    return "\n".join(out) + "\n"


def mermaid(net: dict) -> str:
    nodes = net["nodes"]
    style = {"best": "best", "good": "good", "partial": "partial", "bad": "bad"}
    lines = ["flowchart TD"]
    for i, n in nodes.items():
        label = cell(n["title"]).replace('"', "'")
        if "ending" in n:
            lines.append(f'  {i.replace("-", "_")}(["{label}"]):::{style[n["ending"]["tier"]]}')
        elif "route" in n:
            lines.append(f'  {i.replace("-", "_")}{{"{label}"}}')
        elif "choices" in n:
            lines.append(f'  {i.replace("-", "_")}["{label}"]:::choice')
        else:
            lines.append(f'  {i.replace("-", "_")}["{label}"]')
    for i, n in nodes.items():
        src = i.replace("-", "_")
        if "route" in n:
            for r in n["route"]:
                why = " & ".join(r["if"]) if "if" in r else "else"
                lines.append(f'  {src} -. "{why}" .-> {r["to"].replace("-", "_")}')
        else:
            for t in exits(n):
                lines.append(f"  {src} --> {t.replace('-', '_')}")
    lines += ["  classDef choice fill:#fde7c2,stroke:#c97f09",
              "  classDef best fill:#b7ebc0,stroke:#2e7d32",
              "  classDef good fill:#d8f0c8,stroke:#558b2f",
              "  classDef partial fill:#fff0b3,stroke:#b8860b",
              "  classDef bad fill:#f6c1c1,stroke:#b71c1c"]
    return "\n".join(lines) + "\n"


# ── main ───────────────────────────────────────────────────────────────

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("network", nargs="?", type=Path, default=NETWORK)
    ap.add_argument("--map", action="store_true", help="write page_map.md next to the network")
    ap.add_argument("--mermaid", action="store_true", help="write network.mmd next to the network")
    args = ap.parse_args()

    net = load(args.network)
    nodes = net["nodes"]
    problems = static_problems(net)
    if problems:
        print("\n".join(problems))
        return 1

    net["_relevant"] = relevance(net)
    seen, totals, loops = play(net)
    reached = {s[0] for s in seen}
    unreachable = [i for i in nodes if i not in reached]
    endings = [i for i, n in nodes.items() if "ending" in n]
    never = [e for e in endings if not totals.get(e)]

    decisions = sum(1 for n in nodes.values() if "choices" in n)
    options = sum(len(n["choices"]) for n in nodes.values() if "choices" in n)
    print(f"{len(nodes)} pages · {decisions} decisions ({options} options) · "
          f"{len(endings)} endings · {sum(totals.values()):,} distinct playthroughs")
    for tier in ("best", "good", "partial", "bad"):
        for e in endings:
            if nodes[e]["ending"]["tier"] == tier:
                print(f"  {tier:<8} {totals.get(e, 0):>9,}  {nodes[e]['ending']['title']}")

    for label, items in (("unreachable pages", unreachable), ("unreachable endings", never),
                         ("endless loops", sorted(set(f'{a} → {b}' for a, b in loops)))):
        if items:
            problems.append(f"{label}: {', '.join(items)}")

    if args.map:
        (args.network.parent / "page_map.md").write_text(page_map(net, totals))
    if args.mermaid:
        (args.network.parent / "network.mmd").write_text(mermaid(net))

    if problems:
        print("\n".join(problems))
        return 1
    return 0


if __name__ == "__main__":
    code = main()
    sys.stdout.flush()
    # Freeing ten million states takes longer than finding them.
    os._exit(code)
