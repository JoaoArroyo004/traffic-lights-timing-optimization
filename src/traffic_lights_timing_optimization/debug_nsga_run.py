from traffic_lights_timing_optimization.evaluate_policy import evaluate_policy
from traffic_lights_timing_optimization.fetch_graph_information import fetch_graph_information

if __name__ == '__main__':                    
    SUMO_CFG_PATH = "./santo-andre-cassiano/demand.sumocfg"    
    semaphores_information = fetch_graph_information(SUMO_CFG_PATH).copy()
    cycle_time = 60

    offsets = [2.51, 12.31, 22.38]
    green_times = [35.06, 36.73]
    calculated_last_greens = [60.00, 0, 13.27]
    evaluate_policy(offsets=offsets,
        green_times = green_times,        
        times_for_last_green=calculated_last_greens,
        semaphores_original_information=semaphores_information,
        cycle_time=60,
        gui=True,
        verbose=True,
        path=SUMO_CFG_PATH)