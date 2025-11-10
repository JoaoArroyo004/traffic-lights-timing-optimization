import matplotlib.pyplot as plt
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.optimize import minimize
from pymoo.termination import get_termination

from traffic_lights_timing_optimization.problem_definition import TrafficLightOptimization

# n_lights = 1  # simple '+' intersection
n_lights = 4 # four_semaphores case
problem = TrafficLightOptimization(n_lights)

algorithm = NSGA2(
    pop_size=4,
    eliminate_duplicates=True
)

termination = get_termination("n_gen", 4)

res = minimize(problem,
               algorithm,
               termination,
               seed=1,
               verbose=True)

# --- PARETO PLOT ---
print("\n=== Pareto Front Solutions (Objective Values) ===")
print(res.F)

print("\n=== Example Decision Variables (First solution) ===")
print(res.X[0])

F = res.F
plt.figure(figsize=(6, 5))
plt.scatter(F[:, 0], F[:, 1], color="blue", alpha=0.7)
plt.xlabel("Max Queue Length")
plt.ylabel("Average Travel Time")
plt.title("Mock Traffic Optimization - Pareto Front (NSGA-II)")
plt.grid(True)
plt.show()