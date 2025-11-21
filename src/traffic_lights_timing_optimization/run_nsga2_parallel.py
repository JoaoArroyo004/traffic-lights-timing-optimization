import time
import matplotlib.pyplot as plt
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.optimize import minimize
from pymoo.termination import get_termination
from pymoo.operators.crossover.sbx import SBX
from pymoo.operators.mutation.pm import PM
from traffic_lights_timing_optimization.callback_logger import LogGenerationCallback
from traffic_lights_timing_optimization.fetch_graph_information import fetch_graph_information
from traffic_lights_timing_optimization.problem_definition_parallel import TrafficLightOptimizationParallel
import multiprocessing
from pymoo.core.problem import StarmapParallelization

start_time = time.time()

manager = multiprocessing.Manager()
shared_cache = manager.dict()

CYCLE_TIME = 75
SUMO_CONFIG_PATH = "./santo-andre-extendido/demand.sumocfg"
semaphores_information = fetch_graph_information(SUMO_CONFIG_PATH).copy()
print(f"[DBG] semaphore information: {semaphores_information}")

n_proccess = 4
pool = multiprocessing.Pool(n_proccess)
runner = StarmapParallelization(pool.starmap)
problem = TrafficLightOptimizationParallel(cycle_time=CYCLE_TIME, path=SUMO_CONFIG_PATH,
                                   semaphores_information=semaphores_information,
                                    elementwise_runner=runner,
                                    elementwise_evaluation=True,
                                    shared_cache=shared_cache,
                                    tolerance=0.5)

algorithm = NSGA2(
    pop_size=30,
    crossover= SBX(prob=0.9, eta=20),
    mutation = PM(prob=0.1, eta=20),
    eliminate_duplicates=True
)

termination = get_termination("n_gen", 50)
callback = LogGenerationCallback()
res = minimize(problem,
               algorithm,
               termination,
               seed=1,
               callback = LogGenerationCallback(),
               verbose=False)
pool.close()

elapsed_time = time.time() - start_time
print(f"Total execution time: {elapsed_time:.2f} seconds")
print(f"Total execution time: {elapsed_time/60:.2f} minutes")


# --- PARETO PLOT ---
print("\n=== Pareto Front Solutions (Objective Values) ===")
print(res.F)

print("\n=== Example Decision Variables (First solution) ===")
print(res.X[0])

F = res.F
plt.figure(figsize=(6, 5))
plt.scatter(F[:, 0], F[:, 1], color="blue", alpha=0.7)
plt.xlabel("Max Queue Length")
plt.ylabel("Average Waiting Time")
plt.title("Traffic Optimization - Pareto Front (NSGA-II)")
plt.grid(True)
plt.show()