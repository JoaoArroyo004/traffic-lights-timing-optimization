from traffic_lights_timing_optimization.evaluate_policy import evaluate_policy
from traffic_lights_timing_optimization.fetch_graph_information import fetch_graph_information

if __name__ == '__main__':                    
    SUMO_CFG_PATH = "./santo-andre-benchmark/demand.sumocfg"
    # SUMO_CFG_PATH = "./traffic-light-benchmark/four_semaphores/traffic.sumocfg"
    semaphores_information = fetch_graph_information(SUMO_CFG_PATH).copy()
    cycle_time = 60        
    offsets = [25.0,25.0,0.0]
    green_times = [13.6,7.6,4.8,47.5]
    calculated_last_greens = [31.9,39.6,6.5]
    evaluate_policy(offsets=offsets,
        green_times = green_times,        
        times_for_last_green=calculated_last_greens,
        semaphores_original_information=semaphores_information,
        cycle_time=60,
        gui=True,
        verbose=True,
        path=SUMO_CFG_PATH)