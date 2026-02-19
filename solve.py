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

    # Build model
    print("[2/3] Building optimization model...")
    model = gp.Model("Mobian_HubLocation")

    # Variables: y_h = 1 if hub h is opened
    y = {}
    for h in hubs:
        y[h] = model.addVar(vtype=gp.GRB.BINARY, name=f"y_{h}")

    # Variables: x_{shp} = 1 if demand from junction s to POI p is assigned via hub h
    # Only create variables for feasible assignments
    x = {}
    feasible_assignments = []
    for s in junctions:
        for h in hubs:
            for p in pois:
                if feasibility[s][h][p] > 0:  # Only create if feasible
                    x[s, h, p] = model.addVar(vtype=gp.GRB.BINARY, name=f"x_{s}_{h}_{p}")
                    feasible_assignments.append((s, h, p))

    # Objective: Maximize total covered demand via hubs
    objective = gp.quicksum(demand[s][p] * x[s, h, p]
                           for s, h, p in feasible_assignments)
    model.setObjective(objective, gp.GRB.MAXIMIZE)

    # Constraint 1: Limit the number of new hubs opened
    # Hub IDs are like "h1", "h2", etc. - extract number to determine if existing
    new_hubs = [h for h in hubs if int(h[1:]) > num_existing_hubs]
    existing_hubs = [h for h in hubs if int(h[1:]) <= num_existing_hubs]

    model.addConstr(gp.quicksum(y[h] for h in new_hubs) <= max_new_hubs,
                   name="max_new_hubs")

    # Constraint 2: Ensure all existing hubs are open
    model.addConstr(gp.quicksum(y[h] for h in existing_hubs) == num_existing_hubs,
                   name="existing_hubs_open")

    # Constraint 3: Demand can only be assigned if hub h is open
    for s, h, p in feasible_assignments:
        model.addConstr(x[s, h, p] <= y[h], name=f"hub_open_{s}_{h}_{p}")

    # Constraint 4: Feasibility constraints no longer needed - variables only created for feasible assignments

    # Constraint 5: Each demand from s to p can be assigned to at most one hub
    for s in junctions:
        for p in pois:
            feasible_hubs = [h for h in hubs if (s, h, p) in x]
            if feasible_hubs:  # Only add constraint if there are feasible hubs for this s,p
                model.addConstr(gp.quicksum(x[s, h, p] for h in feasible_hubs) <= 1,
                               name=f"single_assignment_{s}_{p}")

    print(f"      Variables: {model.NumVars:,}")
    print(f"      Constraints: {model.NumConstrs:,}")
    print(f"      Binary variables: {model.NumBinVars:,}")
    print()

    # Solve
    print("[3/3] Solving...")
    print("-" * 60)

    start_time = time.time()
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
