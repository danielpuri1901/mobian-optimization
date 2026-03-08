#!/usr/bin/env python3
"""
Benchmark for mobian Park & Bike Hub Location solve.py

Times each phase of the model-construction and solve pipeline:
  1. JSON data loading
  2. y variable creation (hub open/close)
  3. x variable creation (assignment variables)
  4. Objective construction
  5. Constraint 3: hub_open linking (x <= y)
  6. Constraint 4: feasibility filtering (x <= feasibility)
  7. Constraint 5: single_assignment (at most one hub per s-p pair)
  8. Full Gurobi solve
"""
import os
import sys


def _ensure_venv():
    """Re-exec under venv Python if a venv exists and we are not already in it."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    for venv_dir in ("venv", ".venv", "env"):
        venv_path = os.path.join(script_dir, venv_dir)
        if os.path.isdir(venv_path):
            if sys.platform == "win32":
                venv_python = os.path.join(venv_path, "Scripts", "python.exe")
            else:
                venv_python = os.path.join(venv_path, "bin", "python")
            if os.path.isfile(venv_python) and os.path.abspath(sys.executable) != os.path.abspath(venv_python):
                print(f"[benchmark] Re-launching under {venv_python}")
                os.execv(venv_python, [venv_python] + sys.argv)
            break


_ensure_venv()

import json
import time

try:
    import gurobipy as gp
except ImportError:
    print("SKIP: gurobipy not installed. Install it to run this benchmark.")
    sys.exit(0)


def fmt_time(seconds):
    if seconds < 0.001:
        return f"{seconds*1e6:8.0f} us"
    elif seconds < 1.0:
        return f"{seconds*1e3:8.1f} ms"
    else:
        return f"{seconds:8.2f} s "


def run_benchmark():
    data_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "large_data.json")
    if not os.path.isfile(data_path):
        print(f"SKIP: {data_path} not found. Run generate_data.py first.")
        sys.exit(0)

    results = []

    # ---- Phase 1: JSON data loading ----
    t0 = time.perf_counter()
    with open(data_path, 'r') as f:
        data = json.load(f)
    t_load = time.perf_counter() - t0
    results.append(("JSON data loading", "-", fmt_time(t_load)))

    hubs = data["hubs"]
    pois = data["pois"]
    junctions = data["junctions"]
    demand = data["demand"]
    feasibility = data["feasibility"]
    num_existing_hubs = data["num_existing_hubs"]
    max_new_hubs = data["max_new_hubs"]

    n_hubs = len(hubs)
    n_pois = len(pois)
    n_junctions = len(junctions)
    n_x = n_junctions * n_hubs * n_pois

    print(f"Problem size: {n_junctions} junctions x {n_hubs} hubs x {n_pois} POIs = {n_x:,} x-variables")
    print()

    # ---- Phase 2: y variable creation ----
    env = gp.Env(empty=True)
    env.setParam('OutputFlag', 0)
    env.start()
    model = gp.Model("benchmark", env=env)

    t0 = time.perf_counter()
    y = {}
    for h in hubs:
        y[h] = model.addVar(vtype=gp.GRB.BINARY, name=f"y_{h}")
    model.update()
    t_y = time.perf_counter() - t0
    results.append(("y variable creation", str(n_hubs), fmt_time(t_y)))

    # ---- Phase 3: x variable creation (triple loop) ----
    t0 = time.perf_counter()
    x = {}
    for s in junctions:
        for h in hubs:
            for p in pois:
                x[s, h, p] = model.addVar(vtype=gp.GRB.BINARY, name=f"x_{s}_{h}_{p}")
    model.update()
    t_x = time.perf_counter() - t0
    results.append(("x variable creation (loop)", str(n_x), fmt_time(t_x)))

    # ---- Phase 3b: x variable creation with addVars (batch) ----
    model2 = gp.Model("benchmark_batch", env=env)
    y2 = {}
    for h in hubs:
        y2[h] = model2.addVar(vtype=gp.GRB.BINARY, name=f"y_{h}")

    t0 = time.perf_counter()
    keys = [(s, h, p) for s in junctions for h in hubs for p in pois]
    x2 = model2.addVars(keys, vtype=gp.GRB.BINARY, name="x")
    model2.update()
    t_x_batch = time.perf_counter() - t0
    results.append(("x variable creation (addVars)", str(n_x), fmt_time(t_x_batch)))
    speedup_x = t_x / t_x_batch if t_x_batch > 0 else float('inf')

    # ---- Phase 4: Objective construction ----
    t0 = time.perf_counter()
    objective = gp.quicksum(demand[s][p] * x[s, h, p]
                            for s in junctions for h in hubs for p in pois)
    model.setObjective(objective, gp.GRB.MAXIMIZE)
    model.update()
    t_obj = time.perf_counter() - t0
    results.append(("Objective (quicksum)", str(n_x), fmt_time(t_obj)))

    # ---- Phase 5: Constraint 3 - hub_open (x <= y, individual addConstr) ----
    t0 = time.perf_counter()
    for s in junctions:
        for h in hubs:
            for p in pois:
                model.addConstr(x[s, h, p] <= y[h], name=f"hub_open_{s}_{h}_{p}")
    model.update()
    t_c3 = time.perf_counter() - t0
    results.append(("Constr 3: hub_open (loop)", str(n_x), fmt_time(t_c3)))

    # ---- Phase 5b: Constraint 3 - hub_open via addConstrs ----
    model3 = gp.Model("benchmark_batch_c3", env=env)
    y3 = model3.addVars(hubs, vtype=gp.GRB.BINARY, name="y")
    keys3 = [(s, h, p) for s in junctions for h in hubs for p in pois]
    x3 = model3.addVars(keys3, vtype=gp.GRB.BINARY, name="x")
    model3.update()

    t0 = time.perf_counter()
    model3.addConstrs(
        (x3[s, h, p] <= y3[h] for s in junctions for h in hubs for p in pois),
        name="hub_open"
    )
    model3.update()
    t_c3_batch = time.perf_counter() - t0
    results.append(("Constr 3: hub_open (addConstrs)", str(n_x), fmt_time(t_c3_batch)))
    speedup_c3 = t_c3 / t_c3_batch if t_c3_batch > 0 else float('inf')

    # ---- Phase 6: Constraint 4 - feasibility (individual addConstr) ----
    t0 = time.perf_counter()
    for s in junctions:
        for h in hubs:
            for p in pois:
                model.addConstr(x[s, h, p] <= feasibility[s][h][p],
                                name=f"feasibility_{s}_{h}_{p}")
    model.update()
    t_c4 = time.perf_counter() - t0
    results.append(("Constr 4: feasibility (loop)", str(n_x), fmt_time(t_c4)))

    # ---- Phase 7: Constraint 5 - single_assignment ----
    n_sp = n_junctions * n_pois
    t0 = time.perf_counter()
    for s in junctions:
        for p in pois:
            model.addConstr(gp.quicksum(x[s, h, p] for h in hubs) <= 1,
                            name=f"single_assignment_{s}_{p}")
    model.update()
    t_c5 = time.perf_counter() - t0
    results.append(("Constr 5: single_assign (loop)", str(n_sp), fmt_time(t_c5)))

    total_build = t_y + t_x + t_obj + t_c3 + t_c4 + t_c5
    results.append(("--- Total model build ---", "-", fmt_time(total_build)))

    # ---- Phase 8: Gurobi solve ----
    model.setParam('OutputFlag', 0)
    model.setParam('MIPFocus', 1)
    model.setParam('Heuristics', 0.2)
    model.setParam('RINS', 50)
    model.setParam('SubMIPNodes', 200)
    # Skip DecomposeLP and BendersCutGen - not valid in all Gurobi versions

    t0 = time.perf_counter()
    model.optimize()
    t_solve = time.perf_counter() - t0
    results.append(("Gurobi solve", "-", fmt_time(t_solve)))

    status = model.Status
    obj_val = model.ObjVal if status == 2 else None

    total_wall = t_load + total_build + t_solve
    results.append(("=== TOTAL WALL CLOCK ===", "-", fmt_time(total_wall)))

    # ---- Print results table ----
    print()
    print("=" * 72)
    print(f"{'Phase':<40} {'n':>12} {'Time':>14}")
    print("-" * 72)
    for name, n, t in results:
        print(f"{name:<40} {n:>12} {t:>14}")
    print("=" * 72)

    # ---- Print speedup comparisons ----
    print()
    print("Batch API comparisons:")
    print(f"  x var creation:  loop={fmt_time(t_x).strip()}  addVars={fmt_time(t_x_batch).strip()}  speedup={speedup_x:.1f}x")
    print(f"  hub_open constr: loop={fmt_time(t_c3).strip()}  addConstrs={fmt_time(t_c3_batch).strip()}  speedup={speedup_c3:.1f}x")

    # ---- Print solution info ----
    print()
    if status == 2:
        print(f"Solution: Optimal, Objective = {obj_val:,.0f}")
    else:
        print(f"Solution: Status = {status}")

    print(f"Model: {model.NumVars:,} vars, {model.NumConstrs:,} constrs, {model.NumBinVars:,} binary")

    # ---- Bottleneck analysis ----
    print()
    print("Bottleneck analysis:")
    phases = [
        ("JSON loading", t_load),
        ("Variable creation", t_x),
        ("Objective", t_obj),
        ("Constr 3 (hub_open)", t_c3),
        ("Constr 4 (feasibility)", t_c4),
        ("Constr 5 (single_assign)", t_c5),
        ("Gurobi solve", t_solve),
    ]
    phases.sort(key=lambda x: -x[1])
    for name, t in phases:
        pct = t / total_wall * 100
        bar = "#" * int(pct / 2)
        print(f"  {name:<25} {fmt_time(t).strip():>10}  ({pct:4.1f}%)  {bar}")


if __name__ == "__main__":
    run_benchmark()
