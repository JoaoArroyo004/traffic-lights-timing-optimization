from traffic_lights_timing_optimization.evaluate_policy import evaluate_policy
from traffic_lights_timing_optimization.fetch_graph_information import fetch_graph_information

if __name__ == '__main__':                    
    SUMO_CFG_PATH = "./santo-andre-extendido/demand.sumocfg"    
    semaphores_information = fetch_graph_information(SUMO_CFG_PATH).copy()
    cycle_time = 60

    offsets = [21.37, 31.45, 40.83]
    green_times = [8.28, 45.91, 3.13, 52.58]
    calculated_last_greens = [52.22, 17.96, 16.42]
    # offsets = [46.08, 23.85, 24.18]
    # green_times = [24.33, 45.33, 3.05, 56.04]
    # calculated_last_greens = [36.17, 18.62, 12.96]

    evaluate_policy(offsets=offsets,
        green_times = green_times,        
        times_for_last_green=calculated_last_greens,
        semaphores_original_information=semaphores_information,
        cycle_time=60,
        gui=True,
        verbose=True,
        path=SUMO_CFG_PATH)
