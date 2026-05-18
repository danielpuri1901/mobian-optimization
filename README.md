# Park & Bike Hub Location Optimization — Mobian

A large-scale MILP for siting Park & Bike (P&B) hubs around a city: pick which hubs to open so the maximum number of commuters will park, ride a bike to their destination, and reduce car-kilometres in the urban core.

**Scale:** 80 hubs × 70 highway junctions × 120 POIs → ~672,000 binary assignment variables. Solved with Gurobi (`MIPFocus=1`).

## Accomplishments

Built by [Daniel Puri](https://github.com/danielpuri1901) as one of three MILP test problems used to design the eval harness for [`optimaze-agent`](https://github.com/danielpuri1901/optimaze-agent) — my open-source Gurobi auto-tuner.

- Drives an **automated eval harness** that benchmarks tuning recommendations against the MIPLIB suite — solve time, optimality gap, branch-and-bound nodes
- Helped optimaze achieve **up to 85% peak / 20–50% typical solve-time improvement** vs. default Gurobi configurations
- Optimaze was **presented to Gurobi's optimization team** and **received an acquisition offer (declined)**
- Distributed as a public **PyPI package** — [`optimaze`](https://pypi.org/project/optimaze/)

The other two test problems are [`uber-network-routing-demo`](https://github.com/danielpuri1901/uber-network-routing-demo) and [`timor-leste-healthcare`](https://github.com/danielpuri1901/timor-leste-healthcare).

## Problem

**Objective:** Maximize total commuter demand served by P&B hubs.

### Key constraints
- Existing hubs must remain operational
- Limited budget for new hubs
- Commuters only use a hub if:
  - Extra travel time is acceptable (< threshold)
  - Biking distance is not too long (< max bike time)
  - Biking distance is not too short (> min distance)
  - Car kilometres saved is significant (> min savings)

## Scale

| Parameter | Value |
|-----------|-------|
| Hubs | 80 |
| Points of Interest | 120 |
| Highway junctions | 70 |
| Assignment variables | ~672,000 |

## Mathematical formulation

### Sets
- **H**: potential hub locations
- **P**: Points of Interest (destinations)
- **S**: highway junctions (origins)

### Decision variables
- **y_h** ∈ {0,1}: 1 if hub h is opened
- **x_shp** ∈ {0,1}: 1 if demand from junction s to POI p uses hub h

### Formulation

```
maximize    Σ(s,h,p) demand_sp · x_shp

subject to:
            Σ(h ∈ new) y_h ≤ max_new_hubs        (budget constraint)
            Σ(h ∈ existing) y_h = num_existing   (keep existing open)
            x_shp ≤ y_h,           ∀s,h,p        (must open hub to use it)
            x_shp ≤ feasible_shp,  ∀s,h,p        (feasibility constraints)
            Σ(h) x_shp ≤ 1,        ∀s,p          (single assignment)
            y_h, x_shp ∈ {0,1}
```

## Run it

```bash
pip install gurobipy
python solve.py
```

Requires a working Gurobi licence ([free academic licence](https://www.gurobi.com/academia/academic-program-and-licenses/)).

## See also

- **[`optimaze-agent`](https://github.com/danielpuri1901/optimaze-agent)** — the open-source auto-tuner this problem helped design ([PyPI](https://pypi.org/project/optimaze/))
- **[`uber-network-routing-demo`](https://github.com/danielpuri1901/uber-network-routing-demo)** — Manhattan MDCVRPTW with 7 deliberate inefficiencies
- **[`timor-leste-healthcare`](https://github.com/danielpuri1901/timor-leste-healthcare)** — rural hospital placement set-cover variant
