import csv
import numpy as np
from pymoo.core.problem import Problem

from traffic_lights_timing_optimization.evaluate_policy import evaluate_policy, calculate_last_greens

INF = 100_000_00
TIME_YELLOW = 5
TIME_RED = 5

class TrafficLightOptimization(Problem):
    # Convention: first len(semaphores_phases) are all offset variables. 
    # After, it follows based on the semaphore IDs.
    def __init__(self, cycle_time, semaphores_information, path):
        self.path = path
        
        amount_semaphores = len(semaphores_information)
        n_var = amount_semaphores
        upper_bounds: list[float] = []
        upper_bounds.extend([cycle_time] * amount_semaphores)
        
        for semaphore_id in range(amount_semaphores):
            already_taken_time: float = 0.0
            count_greens = 0
            for phase_id in range(len(semaphores_information[semaphore_id])):
                if semaphores_information[semaphore_id][phase_id][0] == 'green':
                    count_greens += 1 # free green time variable
                elif semaphores_information[semaphore_id][phase_id][0] == 'last_green':
                    pass
                else: # account for times of yellows and reds, which are fixed.
                    already_taken_time += semaphores_information[semaphore_id][phase_id][1]

            n_var += count_greens
            upper_bounds.extend(count_greens * [cycle_time - already_taken_time])
        
        print(f"[DBG] Lower bounds:\n {np.array([0]*n_var)}")
        print(f"[DBG] Upper bounds:\n {upper_bounds}")
        print(f"[DBG] n_var = {n_var}")
        
        super().__init__(n_var=n_var,
                         n_obj=2,
                         n_constr=0,
                         xl=np.array([0]*n_var),
                         xu=np.array(upper_bounds))
        
        self.n_lights = amount_semaphores
        self.cycle_time = cycle_time
        self.semaphores_original_information = semaphores_information.copy()

    def _evaluate(self, X, out, *args, **kwargs):
        # X: matrix of shape (population_size, n_var)
        f1 = []  # max queue length
        f2 = []  # avg travel time

        for solution in X:
            offsets = solution[:self.n_lights]
            green_times = solution[self.n_lights:]                        
            
            calculated_last_greens: list[float] = calculate_last_greens(green_times=green_times, semaphores_original_information=self.semaphores_original_information,
                          cycle_time=self.cycle_time).copy()
            
            with open("./logs.csv", "a", newline="") as f:
                writer = csv.writer(f)

                offsets_fmt = [f"{float(x):.1f}" for x in offsets]
                greens_fmt = [f"{float(x):.1f}" for x in green_times]                
                last_greens_fmt = [f"{float(x):.1f}" for x in calculated_last_greens]
                
                writer.writerow(offsets_fmt)
                writer.writerow(greens_fmt)
                writer.writerow(last_greens_fmt)
            
            if (calculated_last_greens[0] > 0):
                metrics = evaluate_policy(offsets=offsets, 
                                      green_times=green_times, 
                                      times_for_last_green=calculated_last_greens,
                                      cycle_time=self.cycle_time,
                                      semaphores_original_information=self.semaphores_original_information,
                                      path=self.path,
                                      gui=False, verbose=False)
            else:
                metrics = {"avg_travel_time": INF, 
                        "avg_queue_system": INF,
                        "max_queue": INF,
                        }

            f1.append(metrics["avg_queue_system"])            
            # f1.append(metrics["max_queue"])            
            f2.append(metrics["avg_travel_time"])
            
            with open("./logs.csv", "a", newline="") as f:
                writer = csv.writer(f)

                avg_queue_fmt = f"{float(metrics['avg_queue_system']):.1f}"
                avg_tt_fmt = f"{float(metrics['avg_travel_time']):.1f}"                

                writer.writerow([avg_tt_fmt, avg_queue_fmt])
                writer.writerow([])

        out["F"] = np.column_stack([f1, f2])
