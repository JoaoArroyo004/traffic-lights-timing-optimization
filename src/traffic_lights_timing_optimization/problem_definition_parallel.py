
import csv
import numpy as np
import os
import threading

# from pymoo.core.problem import Problem
from pymoo.core.problem import ElementwiseProblem

from traffic_lights_timing_optimization.evaluate_policy import evaluate_policy, calculate_last_greens

INF = 100_000_00

class TrafficLightOptimizationParallel(ElementwiseProblem):
    # Convention: first len(semaphores_phases) are all offset variables. 
    # After, it follows based on the semaphore IDs.
    def __init__(self, semaphores_information, path, elementwise_runner, shared_cache, tolerance,
                 cycle_time=60, elementwise_evaluation=False):
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
                         xu=np.array(upper_bounds),                         
                         elementwise_runner=elementwise_runner,
                         elementwise_evaluation=elementwise_evaluation)
        
        self.n_lights = amount_semaphores
        self.cycle_time = cycle_time
        self.semaphores_original_information = semaphores_information.copy()
        self.shared_cache = shared_cache
        self.tolerance = tolerance
        
    def _normalize_key(self, offsets, greens):
        original_keys = np.concatenate((offsets, greens))
        return tuple(int(round(v / self.tolerance)) for v in original_keys)
    
    # X: corresponds to a single solution
    def _evaluate(self, X, out, *args, **kwargs):
        print("[_evaluate] Worker:", os.getpid(), threading.get_ident(), "evaluating one solution")
        pid = os.getpid()
        tid = threading.get_ident()
        log_file = f"./logs_parallel/log_worker_{pid}_{tid}.csv"        

        offsets = X[:self.n_lights]
        green_times = X[self.n_lights:]                        
        cache_key = self._normalize_key(offsets, green_times)
            
        calculated_last_greens: list[float] = calculate_last_greens(green_times=green_times, semaphores_original_information=self.semaphores_original_information,
                          cycle_time=self.cycle_time).copy()
            
        with open(log_file, "a", newline="") as f:
            writer = csv.writer(f)

            offsets_fmt = [f"{float(x):.2f}" for x in offsets]
            greens_fmt = [f"{float(x):.2f}" for x in green_times]                
            last_greens_fmt = [f"{float(x):.2f}" for x in calculated_last_greens]
            
            writer.writerow(["OFFSETS ", offsets_fmt])
            writer.writerow(["GREENS ", greens_fmt])
            writer.writerow(["LAST_GREENS ", last_greens_fmt])
            
        if (calculated_last_greens[0] > 0):            
            if cache_key in self.shared_cache:
                metrics = self.shared_cache[cache_key]
                print(f"Cache hit for input: {cache_key}")
            else:
                metrics = evaluate_policy(offsets=offsets, 
                                    green_times=green_times, 
                                    times_for_last_green=calculated_last_greens,
                                    cycle_time=self.cycle_time,
                                    semaphores_original_information=self.semaphores_original_information,
                                    path=self.path,
                                    gui=False, verbose=False)
                
                self.shared_cache[cache_key] = metrics
        else:
            metrics = {"avg_waiting_time": INF, 
                    "avg_queue_system": INF,
                    "max_queue": INF,
                    }

        f1 = metrics["max_queue"]
        # f1 = metrics["avg_queue_system"]            
        f2 = metrics["avg_waiting_time"]
            
        with open(log_file, "a", newline="") as f:
            writer = csv.writer(f)            
            avg_waiting_time_fmt = f"{float(metrics['avg_waiting_time']):.2f}"
            avg_queue_fmt = f"{float(metrics['avg_queue_system']):.2f}"
            max_queue_fmt = f"{float(metrics['max_queue']):.2f}"

            writer.writerow(["RESULTS:", avg_waiting_time_fmt, avg_queue_fmt, max_queue_fmt])
            writer.writerow([])
        
        out["F"] = [f1, f2]
