from traffic_lights_timing_optimization.evaluate_policy import evaluate_policy
from traffic_lights_timing_optimization.evaluate_std_policy import evaluate_std_policy
from traffic_lights_timing_optimization.fetch_graph_information import fetch_graph_information

if __name__ == '__main__':                    
    SUMO_CFG_PATH = "./santo-andre-extendido/demand.sumocfg"    
    semaphores_information = fetch_graph_information(SUMO_CFG_PATH).copy()
    cycle_time = 60

    offsets = [69.52, 52.61, 50.79]
    green_times = [56.80, 46.18, 1.27, 54.09]
    calculated_last_greens = [3.70, 19.55, 14.91]
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
    
    # evaluate_std_policy(gui=True,
    #     verbose=True,
    #     path=SUMO_CFG_PATH)
