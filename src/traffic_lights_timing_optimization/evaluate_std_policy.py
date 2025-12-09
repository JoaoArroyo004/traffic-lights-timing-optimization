import os
import tempfile
import shutil
from pathlib import Path
import threading
import traci

from traffic_lights_timing_optimization.fetch_graph_information import fetch_graph_information

SOFT_INF = 1_000
INF = 100_000_00

SIMULATION_TIME = 400 # SIMULATION TIME
MAX_DEADLOCK = 200 # If no vehicle reaches a destination in a 200 consecutive step cout, halt.

def calculate_last_greens(green_times: list[float], semaphores_original_information: list[list[tuple[str,int]]],
                          cycle_time: float):
    """
    Given the green times, the semaphore original information and cycle time, returns the time
    for each last green. If it is not positive, return [-1]
    """
    print(f"[DBG] check semaphore info: {semaphores_original_information}")
    print(f"[DBG] check green_times: {green_times}")
    
    currGreen: int = 0
    times_for_last_green: list[float] = []
    foundInvalid: bool = False
    for s_id in range(len(semaphores_original_information)):
        time_sum: float = 0.0
        for p_id in range(len(semaphores_original_information[s_id])):
            if semaphores_original_information[s_id][p_id][0] == 'green':            
                time_sum += green_times[currGreen]
                currGreen += 1
            elif semaphores_original_information[s_id][p_id][0] != 'last_green':
                time_sum += semaphores_original_information[s_id][p_id][1]
        
        last_green_time: float = cycle_time - time_sum
        print(f"[DBG] last_green_time = {last_green_time}")
        if last_green_time <= 0:            
            foundInvalid = True
            break
        else:
            times_for_last_green.append(last_green_time)
    
    
    if foundInvalid:
        # If there is some last_green with negative time, the configuration is infeasable
        # We return a very high value for all metrics, so that the GA tries to get away from this scenarios.
        # TODO: test if this works in practice
        print("---- INVALID ATTEMPT ----")
        return [-1]
    
    print(f"[DBG] Check calculated last_greens:\n {times_for_last_green}")
    return times_for_last_green

def evaluate_std_policy(gui=False, verbose=False, path="./traffic-light-benchmark/four_semaphores/traffic.sumocfg"):
    """
    Evaluates a traffic light policy by adjusting the green phase durations and offsets    
    """        
    tmp_dir = tempfile.mkdtemp(prefix="sumo_sim_")
    cfg_path = Path(tmp_dir) / "traffic.sumocfg"    
    shutil.copy(path, cfg_path) # Copy original simulation config & all referenced files
    
    operationMode = "sumo-gui" if gui else "sumo" # SUMO with GUI ONLY for debugging    
    sumoCmd = [
        operationMode,
        "-c", path,
        "--no-step-log",
        "--no-warnings",
        "--start",          # start simulation immediately (skip GUI pause)
        "--time-to-teleport", "-1",  # disable teleportation
        "--waiting-time-memory", "1000",  # longer waiting-time window
        "--tripinfo-output", str(Path(tmp_dir) / "tripinfo.xml"),
        "--vehroute-output", str(Path(tmp_dir) / "routes.xml")
    ]
    
    port = traci.getFreeSocketPort()
    print(f"[DBG] Starting SUMO | PID={os.getpid()} TID={threading.get_ident()} port={port} tmp_dir={tmp_dir}")
    traci.start(sumoCmd, port=port)    
    if verbose:
        print("[INFO] Connection stablished")

    try:
        step: int = 0
        total_waiting_time: float = 0.0
        total_vehicles_through_system: int = 0
        max_queue_length: int = 0
        graphEdges = traci.edge.getIDList()
        sum_queues: float = 0.0        
        last_arrival_count = 0
        consecutive_steps_no_arrival = 0
        halted_simulation = False       
        tracked_waiting_times = {} 
        while traci.simulation.getMinExpectedNumber() > 0 and traci.simulation.getTime() <= SIMULATION_TIME:
            traci.simulationStep()
            total_vehicles_through_system += len(traci.simulation.getDepartedIDList())

            for vid in traci.vehicle.getIDList():
                if vid in tracked_waiting_times:
                    total_waiting_time += traci.vehicle.getAccumulatedWaitingTime(vid) - tracked_waiting_times[vid]
                    
                tracked_waiting_times[vid] = traci.vehicle.getAccumulatedWaitingTime(vid)

            for vid in traci.simulation.getArrivedIDList():
                tracked_waiting_times.pop(vid)

            queue_lengths = []
            for edge in graphEdges:
                halting = traci.edge.getLastStepHaltingNumber(edge)
                lanes = traci.edge.getLaneNumber(edge)  # faster than getLaneIDs
                if lanes > 0:
                    queue_lengths.append(halting / lanes)
                else:
                    queue_lengths.append(0)

            for queue_len in queue_lengths:
                sum_queues += queue_len

            step_max_queue = max(queue_lengths) if queue_lengths else 0
            if step_max_queue > max_queue_length:
                max_queue_length = step_max_queue

            new_arrival_count = traci.simulation.getArrivedNumber()
            if new_arrival_count == last_arrival_count:
                consecutive_steps_no_arrival += 1
            else:
                consecutive_steps_no_arrival = 0
                last_arrival_count = new_arrival_count

            if (consecutive_steps_no_arrival >= MAX_DEADLOCK):
                halted_simulation = True
                break
            step += 1

        if (not halted_simulation):
            print("[DBG] Simulation finished")        
        else:
            print("[DBG] Simulation halted")
        
        traci.close()

        if halted_simulation:
            return {
                "avg_waiting_time": SOFT_INF, 
                "avg_queue_system": SOFT_INF,
                "max_queue": SOFT_INF,
            }

        avg_queue_system = sum_queues / step        
        avg_waiting_time = total_waiting_time / max(1, total_vehicles_through_system)
        if verbose:
            print(f"""[RESULTS]\nAvg waiting time: {avg_waiting_time:.2f}
                  \nMax per-edge queue length:     {max_queue_length}
                  \nAverage queue length:          {avg_queue_system:.2f}""")
        
        shutil.rmtree(tmp_dir)        
        return {"avg_waiting_time": avg_waiting_time, 
                "avg_queue_system": avg_queue_system,
                "max_queue": max_queue_length,
                }

    except Exception as e:        
        print("[ERROR]", e)
        traci.close(False)
        shutil.rmtree(tmp_dir)
        raise

if __name__ == '__main__':                    
    SUMO_CFG_PATH = "./traffic-light-benchmark/four_semaphores/traffic.sumocfg"
    # SUMO_CFG_PATH = "./santo-andre-benchmark/demand.sumocfg"
    semaphores_information = fetch_graph_information(SUMO_CFG_PATH).copy()
    print("[DBG] FINISHED INFORMATION FETCH")
    evaluate_std_policy(offsets=len(semaphores_information) * [0],
        green_times = [15, 15, 15, 15, 15, 15, 15, 15, 15], # Check: this needs to be of size of the amount of green times.
        cycle_time=60,
        semaphores_original_information=semaphores_information,
        gui=True,
        verbose=True,
        path=SUMO_CFG_PATH)