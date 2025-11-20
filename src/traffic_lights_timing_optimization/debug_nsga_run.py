from traffic_lights_timing_optimization.evaluate_policy import evaluate_policy
from traffic_lights_timing_optimization.fetch_graph_information import fetch_graph_information

if __name__ == '__main__':                    
    SUMO_CFG_PATH = "./santo-andre-extendido/demand.sumocfg"    
    semaphores_information = fetch_graph_information(SUMO_CFG_PATH).copy()
    cycle_time = 60                
    
    offsets = [72.16, 29.82, 40.65]
    green_times = [12.69, 45.81, 6.01, 48.40]
    calculated_last_greens = [47.81, 15.18, 20.60]
    evaluate_policy(offsets=offsets,
        green_times = green_times,        
        times_for_last_green=calculated_last_greens,
        semaphores_original_information=semaphores_information,
        cycle_time=60,
        gui=True,
        verbose=True,
        path=SUMO_CFG_PATH)
