from traffic_lights_timing_optimization.evaluate_policy import evaluate_policy
from traffic_lights_timing_optimization.fetch_graph_information import fetch_graph_information

if __name__ == '__main__':                    
    SUMO_CFG_PATH = "./santo-andre-benchmark/demand.sumocfg"
    # SUMO_CFG_PATH = "./traffic-light-benchmark/four_semaphores/traffic.sumocfg"
    semaphores_information = fetch_graph_information(SUMO_CFG_PATH).copy()
    cycle_time = 60
    offsets = [20.7,23.8,32.3]
    green_times = [19.1,35.6,10.6,47.4]
    calculated_last_greens = [26.4,5.7,6.6]
    evaluate_policy(offsets=offsets,
        green_times = green_times,        
        times_for_last_green=calculated_last_greens,
        semaphores_original_information=semaphores_information,
        cycle_time=60,
        gui=False,
        verbose=True,
        path=SUMO_CFG_PATH)