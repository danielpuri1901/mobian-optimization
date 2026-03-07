# Baseline Performance Report

## Problem Summary
- **Type**: Mixed Integer Program (MIP) — Facility Location / Hub Location
- **Solver**: Gurobi 13.0.1 (mac64[arm], Apple M2, 8 threads)
- **Instance**: `large_data.json` (23MB) — 100 hubs, 150 POIs, 80 junctions
- **Dimensions**: 1,200,100 variables (all binary), 2,412,002 constraints, 4,800,100 nonzeros

## Baseline Timing
- **Run command**: `python3 solve.py` (with `DecomposeLP` and `BendersCutGen` params skipped — not valid in Gurobi 13.0.1)
- **Run 1**: 18.19s
- **Run 2**: 17.32s
- **Run 3**: 16.99s
- **Median**: 17.32s
- **Solver-only time** (from Gurobi logs): 1.31s (median of 1.37s, 1.31s, 1.29s)
- **Python overhead** (estimated): 16.01s (92.4% of total time)

## Solution Quality
- **Objective value**: 1,160,404 (total demand covered)
- **Status**: Optimal
- **MIP Gap**: 0.0075%
- **Nodes explored**: 1 (solved at root)
- **New hubs opened**: 25/25

## Solver Log Highlights

```
Presolve removed 2,147,661 rows and 883,918 columns (73.7% of variables eliminated)
Presolve time: 0.50s + 0.18s + 0.03s = 0.71s

Presolved (final): 4,318 rows, 3,758 columns, 11,114 nonzeros

Root relaxation: objective 1,160,676.91, 2,252 iterations, 0.03s
Root heuristics found optimal incumbent (1,160,404) within 1s
Gap closed from 7.23% → 0.02% → 0.01% at root node

Cutting planes: 1 Gomory, 17 Zero half
Total solver time: 1.31s (2.11 work units)
```

**Key insight**: Gurobi's presolve eliminates 73.7% of variables — these are all the infeasible assignments (`feasibility[s][h][p] = 0`). The problem is trivially solved at the root node with heuristics.

## Bottleneck Analysis

**The bottleneck is overwhelmingly Python model construction (92.4% of total time).**

| Phase | Time (est.) | % of Total |
|-------|-------------|------------|
| JSON loading (~23MB) | ~2.5s | 14% |
| Variable creation (1.2M addVar calls in triple loop) | ~4.5s | 26% |
| Constraint generation (2.4M addConstr calls in triple loops) | ~8.5s | 49% |
| Objective construction (quicksum over 1.2M terms) | ~0.5s | 3% |
| **Gurobi solve** (presolve + root + cuts) | **1.31s** | **7.6%** |

The solver is extremely fast — it solves at the root node in 1.3s. All optimization effort should target Python-side model construction.

### Why construction is so slow:
1. **Triple-nested Python loops** for variable creation (lines 61-64) and constraint creation (lines 84-87, 90-94)
2. **Creating variables for infeasible assignments** — 73.7% of variables are immediately eliminated by presolve. These should never be created.
3. **Individual `addVar()`/`addConstr()` calls** — each call has Python→C overhead. 3.6M total calls.
4. **23MB JSON → nested Python dicts** — slow deserialization and dict-of-dict-of-dict lookups.

## Recommended Optimizations (ranked by expected impact)

1. **Pre-filter infeasible assignments (expected: 5-8x speedup on construction)** — Don't create variables or constraints where `feasibility[s][h][p] = 0`. This eliminates ~73% of variables (883,918 out of 1,200,000) and their associated linking constraints. Instead of building 1.2M variables and relying on presolve to remove them, only build the ~316K feasible ones. This is a mathematically equivalent reformulation.

2. **Batch variable/constraint creation (expected: 2-3x additional speedup)** — Replace `addVar()` loops with `model.addVars()`. Replace individual `addConstr()` calls with `model.addConstrs()` generator API or the matrix constraint API `addMConstrs()`. This reduces Python→C call overhead from millions of calls to a handful.

3. **Relax x variables to continuous [0,1] (expected: modest solver speedup)** — Since `x[s,h,p]` is bounded above by `y[h]` (binary) and the objective maximizes demand, the LP relaxation will naturally produce binary x values at optimality. Declaring x as continuous eliminates integrality requirements for 1.2M variables, reducing the MIP to just 100 binary variables. This is a well-known valid relaxation for this type of covering/assignment problem.

4. **Replace JSON with numpy binary format (expected: ~2s savings)** — Use `.npz` for the feasibility/demand matrices instead of a 23MB JSON file with nested dicts. Numpy loading is orders of magnitude faster than `json.load()` + dict construction.

5. **Remove unnecessary solver parameters** — `NumericFocus=1` adds overhead for a problem with all-unit coefficients. `DecomposeLP` and `BendersCutGen` are invalid params that crash the current version. `RINS=50` and `SubMIPNodes=200` are irrelevant since the problem is solved at the root node.

6. **Fix upper-bound constraints as variable bounds** — For infeasible assignments that aren't filtered out, instead of `x[s,h,p] <= 0` as a constraint, fix the variable bound `x.ub = 0`. This reduces constraint count without changing the model.
