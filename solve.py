#!/usr/bin/env python3
"""
Park & Bike Hub Location Optimization - Mobian

Optimizes Park and Bike hub locations for sustainable urban mobility.
Determines which hubs to open to maximize the number of commuters
that will use a hub instead of driving directly to their destination.

Problem Scale:
- 80 potential hubs
- 120 Points of Interest (POIs)
- 70 highway junctions
- O(70 x 80 x 120) = 672,000 assignment variables
"""
import json
import time
import os

import gurobipy as gp


def main():
    print("=" * 60)
    print("PARK & BIKE HUB LOCATION OPTIMIZATION - MOBIAN")
    print("=" * 60)
    print()

    # Load data
    data_path = os.path.join(os.path.dirname(__file__), "large_data.json")
    print("[1/3] Loading dataset...")

    with open(data_path, 'r') as f:
        data = json.load(f)

    hubs = data["hubs"]
    pois = data["pois"]
    junctions = data["junctions"]
    demand = data["demand"]
    feasibility = data["feasibility"]
    num_existing_hubs = data["num_existing_hubs"]
    max_new_hubs = data["max_new_hubs"]

    print(f"      Hubs: {len(hubs)}")
    print(f"      POIs: {len(pois)}")
    print(f"      Junctions: {len(junctions)}")
    print(f"      Existing hubs: {num_existing_hubs}")
    print(f"      Max new hubs: {max_new_hubs}")
    print()

    # Pre-filter: only create variables for feasible (s,h,p) assignments
    feasible_arcs = []
    for s in junctions:
        for h in hubs:
            for p in pois:
                if feasibility[s][h][p]:
                    feasible_arcs.append((s, h, p))

    print(f"      Feasible arcs: {len(feasible_arcs):,} / {len(junctions)*len(hubs)*len(pois):,}")

    # Build model
    print("[2/3] Building optimization model...")
    model = gp.Model("Mobian_HubLocation")

    # Variables: y_h = 1 if hub h is opened
    y = model.addVars(hubs, vtype=gp.GRB.BINARY, name="y")

    # Variables: x_{shp} — continuous [0,1] since integrality is implied by y
    x = model.addVars(feasible_arcs, vtype=gp.GRB.CONTINUOUS, name="x")

    # Objective: Maximize total covered demand via hubs
    model.setObjective(
        gp.quicksum(demand[s][p] * x[s, h, p] for s, h, p in feasible_arcs),
        gp.GRB.MAXIMIZE)

    # Constraint 1: Limit the number of new hubs opened
    new_hubs = [h for h in hubs if int(h[1:]) > num_existing_hubs]
    existing_hubs = [h for h in hubs if int(h[1:]) <= num_existing_hubs]

    model.addConstr(gp.quicksum(y[h] for h in new_hubs) <= max_new_hubs,
                   name="max_new_hubs")

    # Constraint 2: Ensure all existing hubs are open
    model.addConstr(gp.quicksum(y[h] for h in existing_hubs) == num_existing_hubs,
                   name="existing_hubs_open")

    # Constraint 3: Demand can only be assigned if hub h is open
    model.addConstrs(
        (x[s, h, p] <= y[h] for s, h, p in feasible_arcs),
        name="hub_open")

    # Constraint 5: Each demand from s to p can be assigned to at most one hub
    # Build index of feasible hubs per (s, p) pair
    sp_hubs = {}
    for s, h, p in feasible_arcs:
        sp_hubs.setdefault((s, p), []).append(h)

    for (s, p), h_list in sp_hubs.items():
        model.addConstr(gp.quicksum(x[s, h, p] for h in h_list) <= 1)

    model.update()
    print(f"      Variables: {model.NumVars:,}")
    print(f"      Constraints: {model.NumConstrs:,}")
    print(f"      Binary variables: {model.NumBinVars:,}")
    print()

    # Solve
    print("[3/3] Solving...")
    print("-" * 60)

    start_time = time.time()
    model.setParam('LogFile', 'gurobi.log')
    model.setParam('MIPFocus', 1)
    model.optimize()
    solve_time = time.time() - start_time

    print("-" * 60)
    print()

    # Results
    print("RESULTS")
    print("=" * 60)

    if model.Status == 2:  # Optimal
        print(f"Status: Optimal")
        print(f"Objective: {model.ObjVal:,.0f} (total demand covered)")
        print(f"Solve time: {solve_time:.2f} seconds")
        print(f"Nodes explored: {int(model.NodeCount):,}")

        # Count opened hubs
        opened_new = sum(1 for h in new_hubs if y[h].X > 0.5)
        print(f"New hubs opened: {opened_new}/{max_new_hubs}")
    else:
        print(f"Status: {model.Status}")
        print(f"Solve time: {solve_time:.2f} seconds")

    print()


if __name__ == "__main__":
    main()
