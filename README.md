# Park & Bike Hub Location Optimization - Mobian

## Problem Description

Urban mobility optimization for Park & Bike (P&B) hubs. The goal is to determine optimal hub locations to maximize the number of commuters who will park their car at a hub and bike to their destination, reducing urban traffic and emissions.

**Objective:** Maximize total commuter demand served by P&B hubs.

### Key Constraints
- Existing hubs must remain operational
- Limited budget for new hubs
- Commuters only use a hub if:
  - Extra travel time is acceptable (< threshold)
  - Biking distance is not too long (< max bike time)
  - Biking distance is not too short (> min distance)
  - Car kilometers saved is significant (> min savings)

## Problem Scale

| Parameter | Value |
|-----------|-------|
| Hubs | 80 |
| Points of Interest | 120 |
| Highway Junctions | 70 |
| Assignment Variables | ~672,000 |

## Mathematical Formulation

### Sets
- **H**: Set of potential hub locations
- **P**: Set of Points of Interest (destinations)
- **S**: Set of highway junctions (origins)

### Decision Variables
- **y_h** ∈ {0,1}: 1 if hub h is opened
- **x_shp** ∈ {0,1}: 1 if demand from junction s to POI p uses hub h

### Formulation

```
maximize    Σ(s,h,p) demand_sp · x_shp

subject to:
            Σ(h ∈ new) y_h ≤ max_new_hubs        (budget constraint)
            Σ(h ∈ existing) y_h = num_existing   (keep existing open)
            x_shp ≤ y_h,  ∀s,h,p                 (must open hub to use it)
            x_shp ≤ feasible_shp,  ∀s,h,p        (feasibility constraints)
            Σ(h) x_shp ≤ 1,  ∀s,p                (single assignment)
            y_h, x_shp ∈ {0,1}
```

## Usage

```bash
python solve.py
```
