import matplotlib.pyplot as plt
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.optimize import minimize
from pymoo.termination import get_termination
from pymoo.operators.crossover.sbx import SBX
from pymoo.operators.mutation.pm import PM
from traffic_lights_timing_optimization.fetch_graph_information import fetch_graph_information
from traffic_lights_timing_optimization.problem_definition_parallel import TrafficLightOptimizationParallel
import multiprocessing
from pymoo.core.problem import StarmapParallelization

CYCLE_TIME = 60
# SUMO_CONFIG_PATH = "./traffic-light-benchmark/four_semaphores/traffic.sumocfg"
SUMO_CONFIG_PATH = "./santo-andre-benchmark/demand.sumocfg"
semaphores_information = fetch_graph_information(SUMO_CONFIG_PATH).copy()
print(f"[DBG] semaphore information: {semaphores_information}")

n_proccess = 4
pool = multiprocessing.Pool(n_proccess)
runner = StarmapParallelization(pool.starmap)
problem = TrafficLightOptimizationParallel(cycle_time=CYCLE_TIME, path=SUMO_CONFIG_PATH,
                                   semaphores_information=semaphores_information,
                                    elementwise_runner=runner,
                                    elementwise_evaluation=True)

algorithm = NSGA2(
    pop_size=4,
    crossover= SBX(prob=0.9, eta=20),
    mutation = PM(prob=0.1, eta=20),
    eliminate_duplicates=True
)

termination = get_termination("n_gen", 4)

res = minimize(problem,
               algorithm,
               termination,
               seed=1,
               verbose=True)
pool.close()

# --- PARETO PLOT ---
print("\n=== Pareto Front Solutions (Objective Values) ===")
print(res.F)

print("\n=== Example Decision Variables (First solution) ===")
print(res.X[0])

F = res.F
plt.figure(figsize=(6, 5))
plt.scatter(F[:, 0], F[:, 1], color="blue", alpha=0.7)
plt.xlabel("Average Queue Length")
plt.ylabel("Average Travel Time")
plt.title("Traffic Optimization - Pareto Front (NSGA-II)")
plt.grid(True)
plt.show()