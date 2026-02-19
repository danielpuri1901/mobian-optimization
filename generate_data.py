#!/usr/bin/env python3
"""Generate larger dataset for mobian problem."""
import random
import numpy as np
import json

def generate_data(seed=42, output_path='large_data.json'):
    random.seed(seed)
    np.random.seed(seed)

    # Larger problem size for harder solving
    num_hubs = 100
    num_pois = 150
    num_junctions = 80

    hubs = [f"h{h+1}" for h in range(num_hubs)]
    pois = [f"p{p+1}" for p in range(num_pois)]
    junctions = [f"s{s+1}" for s in range(num_junctions)]

    # Generate demand using NumPy
    demand = np.random.randint(20, 201, size=(num_junctions, num_pois)).astype(float)

    # Generate distances using NumPy
    distance_sp = np.round(np.random.uniform(1, 20, size=(num_junctions, num_pois)), 2)
    distance_sh = np.round(np.random.uniform(1, 15, size=(num_junctions, num_hubs)), 2)
    distance_hp = np.round(np.random.uniform(1, 10, size=(num_hubs, num_pois)), 2)

    # Generate travel times using NumPy
    car_time_sp = np.round(np.random.uniform(5, 30, size=(num_junctions, num_pois)), 1)
    car_time_sh = np.round(np.random.uniform(3, 20, size=(num_junctions, num_hubs)), 1)
    bike_time_hp = np.round(np.random.uniform(5, 25, size=(num_hubs, num_pois)), 1)

    # Scalar parameters - make it harder by allowing more hubs
    max_bike_time = 18.0  # Fixed for reproducibility
    num_existing_hubs = 20
    max_new_hubs = 25  # More new hubs = harder problem
    min_hub_poi_distance = 3.0
    max_additional_time = 30.0
    min_distance_diff = 2.0

    # Vectorized feasibility calculation
    car_time_sh_3d = car_time_sh[:, :, np.newaxis]
    bike_time_hp_3d = bike_time_hp[np.newaxis, :, :]
    car_time_sp_3d = car_time_sp[:, np.newaxis, :]
    distance_hp_3d = distance_hp[np.newaxis, :, :]
    distance_sp_3d = distance_sp[:, np.newaxis, :]
    distance_sh_3d = distance_sh[:, :, np.newaxis]

    extra_time = car_time_sh_3d + bike_time_hp_3d - car_time_sp_3d
    time_condition = extra_time <= max_additional_time
    bike_time_condition = bike_time_hp_3d <= max_bike_time
    distance_condition = distance_hp_3d >= min_hub_poi_distance
    distance_diff_condition = (distance_sp_3d - distance_sh_3d) >= min_distance_diff

    feasibility = (time_condition & bike_time_condition &
                  distance_condition & distance_diff_condition).astype(int)

    # Convert to nested dictionaries
    def array_to_dict(arr, row_keys, col_keys):
        return {row_keys[i]: {col_keys[j]: float(arr[i, j]) for j in range(arr.shape[1])}
                for i in range(arr.shape[0])}

    def array_3d_to_dict(arr, dim1_keys, dim2_keys, dim3_keys):
        return {dim1_keys[i]: {dim2_keys[j]: {dim3_keys[k]: int(arr[i, j, k])
                for k in range(arr.shape[2])} for j in range(arr.shape[1])}
                for i in range(arr.shape[0])}

    data = {
        "hubs": hubs,
        "pois": pois,
        "junctions": junctions,
        "demand": array_to_dict(demand, junctions, pois),
        "car_time_sp": array_to_dict(car_time_sp, junctions, pois),
        "car_time_sh": array_to_dict(car_time_sh, junctions, hubs),
        "bike_time_hp": array_to_dict(bike_time_hp, hubs, pois),
        "distance_sp": array_to_dict(distance_sp, junctions, pois),
        "distance_hp": array_to_dict(distance_hp, hubs, pois),
        "distance_sh": array_to_dict(distance_sh, junctions, hubs),
        "max_bike_time": max_bike_time,
        "num_existing_hubs": num_existing_hubs,
        "max_new_hubs": max_new_hubs,
        "min_hub_poi_distance": min_hub_poi_distance,
        "max_additional_time": max_additional_time,
        "min_distance_diff": min_distance_diff,
        "feasibility": array_3d_to_dict(feasibility, junctions, hubs, pois)
    }

    with open(output_path, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"Data written to {output_path}")
    print(f"  Hubs: {num_hubs}")
    print(f"  POIs: {num_pois}")
    print(f"  Junctions: {num_junctions}")
    print(f"  Total variables: ~{num_junctions * num_hubs * num_pois:,}")

if __name__ == "__main__":
    generate_data()
