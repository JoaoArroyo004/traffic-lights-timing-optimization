import csv
import numpy as np
from pymoo.core.problem import Problem

from traffic_lights_timing_optimization.evaluate_policy import evaluate_policy

class TrafficLightOptimization(Problem):
    def __init__(self, n_lights):
        # 2 objectives: max queue length, avg travel time
        # 2 variables per traffic light: % green and offset (Sync between traffic-lights)
        super().__init__(n_var=2 * n_lights,
                         n_obj=2,
                         n_constr=0,
                         xl=np.array([0, 0]*n_lights),
                         xu=np.array([1, 60]*n_lights))
        self.n_lights = n_lights

    def _evaluate(self, X, out, *args, **kwargs):
        # X: matrix of shape (population_size, n_var)
        f1 = []  # max queue length
        f2 = []  # avg travel time

        for solution in X:
            green_ratios = solution[0::2]
            offsets = solution[1::2]
            
            metrics = evaluate_policy(flux1_fractions=green_ratios, offsets=offsets, 
                                      gui=False, verbose=False)

            f1.append(metrics["avg_queue_system"])            
            # f1.append(metrics["max_queue"])            
            f2.append(metrics["avg_travel_time"])
            
            with open("./logs.csv", "a", newline="") as f:
                writer = csv.writer(f)
                writer.writerow([
                    list(green_ratios),
                    list(offsets),                    
                    # metrics["max_queue"],
                    metrics["avg_queue_system"],
                    metrics["avg_travel_time"]
                ])

        out["F"] = np.column_stack([f1, f2])