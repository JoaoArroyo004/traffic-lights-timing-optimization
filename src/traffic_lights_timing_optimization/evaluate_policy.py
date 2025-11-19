import traci

from traffic_lights_timing_optimization.fetch_graph_information import fetch_graph_information

SOFT_INF = 1_000
INF = 100_000_00
LAST_VEHICLE_SPAWN = 3600.00 # TODO: automate this
TIME_LIMIT = 10 * LAST_VEHICLE_SPAWN
SIMULATION_TIME = 1_800 # How much time each simulation runs
MAX_DEADLOCK = 200 # If no vehicle reaches a destination in a 200 consecutive step cout, halt.

def simulation_ended():
    veh_ids = traci.vehicle.getIDList()
    if not veh_ids:
        return False # Avoid stalling at the start.
    # Notice that if there are no vehicles in the current network either:
    # some of the spawned before SIMULATION_TIME still are gonna enter the network -> False
    # no more spawned before are gonna enter the network. Then, either all vehicles have reached 
    # their destination (traci.simulation.getMinExpectedNumber() == 0) or some vehicle will enter right away, triggering True in this function

    for v in veh_ids:
        departure_time = traci.vehicle.getDeparture(v)
        if departure_time <= SIMULATION_TIME:
            return False

    return True

def calculate_last_greens(green_times: list[float], semaphores_original_information: list[list[tuple[str,int]]],
                          cycle_time: float):
    """
    Given the green times, the semaphore original information and cycle time, returns the time
    for each last green. If it is not positive, return [-1]
    """
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

def evaluate_policy(offsets, green_times, times_for_last_green, semaphores_original_information, cycle_time=60, gui=False, verbose=False,
                    path="./traffic-light-benchmark/four_semaphores/traffic.sumocfg"):
    """
    Evaluates a traffic light policy by adjusting the green phase durations and offsets    
    """        
    print("-------------------\n-------------------")
    print(f"[DBG] Simulate with the following policy:\n")
    print(f"Offsets:\n {offsets}")
    print(f"Green times:\n {green_times}")
    
    print("-------------------\n-------------------")    
    
    
    operationMode = "sumo-gui" if gui else "sumo" # SUMO with GUI ONLY for debugging
    port = traci.getFreeSocketPort()
    sumoCmd = [
        operationMode,
        "-c", path,
        "--no-step-log",
        "--no-warnings",
        "--start",          # start simulation immediately (skip GUI pause)
        "--time-to-teleport", "-1",  # disable teleportation
        "--waiting-time-memory", "1000",  # longer waiting-time window
    ]
    traci.start(sumoCmd, port=port)    
    if verbose:
        print("[INFO] Connection stablished")

    try:
        tls_ids = traci.trafficlight.getIDList()
        
        print(f"[DBG] Check current phase plan")
        for s_id, tls_id in enumerate(tls_ids):
            logic = traci.trafficlight.getCompleteRedYellowGreenDefinition(tls_id)[0]                    
            print(f"For semaphore {s_id}")
            for p_id, phase in enumerate(logic.phases):
                print(f"Phase {p_id} = {phase.state}")
        
                        
        print(f"[DBG]Assign new plan")
        currGreen = 0
        currlastGreen = 0
        for s_id, tls_id in enumerate(tls_ids):
            logic = traci.trafficlight.getCompleteRedYellowGreenDefinition(tls_id)[0]                    
        
            new_phases = []
            print(f"-- For semaphore id = {s_id}")
            for p_id, phase in enumerate(logic.phases):
                print(f"-- For phase id = {p_id}")
                if semaphores_original_information[s_id][p_id][0] == 'last_green':
                    new_duration = times_for_last_green[currlastGreen]
                    currlastGreen += 1
                elif semaphores_original_information[s_id][p_id][0] == 'green':
                    new_duration = green_times[currGreen]
                    currGreen += 1
                else:
                    new_duration = semaphores_original_information[s_id][p_id][1]

                new_phases.append(traci.trafficlight.Phase(new_duration, phase.state))

            if verbose:
                print("[DBG] Check the new semaphore policy")
                for phase in new_phases:
                    print(f"-- Phase state: {phase.state} duration {phase.duration}")        
                print("-------")
        
            program = traci.trafficlight.Logic("custom", 0, 0, new_phases) # last arg = phase
            traci.trafficlight.setCompleteRedYellowGreenDefinition(tls_id, program)            

            offset_time = offsets[s_id] % cycle_time
            traci.trafficlight.setPhaseDuration(tls_id, offset_time) # Set offset.
            if verbose:
                print(f"[INFO] Phase offset applied: {offset_time:.2f} seconds")

        
        print("[DBG] Custom program applied successfully.\n Start simulation")        
        step: int = 0
        total_waiting_time: float = 0.0
        total_vehicles: int = 0
        max_queue_length: int = 0
        graphEdges = traci.edge.getIDList()
        sum_queues: float = 0.0        
        last_arrival_count = 0
        consecutive_steps_no_arrival = 0
        halted_simulation = False
        while traci.simulation.getMinExpectedNumber() > 0 and (not simulation_ended()):
            traci.simulationStep()
            
            queue_lengths = [traci.edge.getLastStepHaltingNumber(e) for e in graphEdges] # consider only stopped/halted edges
            for queue_len in queue_lengths:
                sum_queues += queue_len

            step_max_queue = max(queue_lengths) if queue_lengths else 0
            if step_max_queue > max_queue_length:
                max_queue_length = step_max_queue

            veh_ids = traci.vehicle.getIDList()
            total_vehicles += len(veh_ids)
            for vid in veh_ids:
                total_waiting_time += traci.vehicle.getWaitingTime(vid)                    
            
            new_arrival_count = traci.simulation.getArrivedNumber()
            if new_arrival_count == last_arrival_count:
                consecutive_steps_no_arrival += 1
            else:
                consecutive_steps_no_arrival = 0
                last_arrival_count = new_arrival_count
                
            if (traci.simulation.getTime() >= TIME_LIMIT or consecutive_steps_no_arrival >= MAX_DEADLOCK):
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
                "avg_travel_time": SOFT_INF, 
                "avg_queue_system": SOFT_INF,
                "max_queue": SOFT_INF,
            }

        avg_queue_system = sum_queues / step
        avg_waiting_time = total_waiting_time / max(1, total_vehicles)        
        if verbose:
            print(f"""[RESULTS]\nAvg waiting time: {avg_waiting_time:.2f}
                  \nMax per-edge queue length:     {max_queue_length}
                  \nAverage queue length:          {avg_queue_system:.2f}""")
                    
        return {"avg_travel_time": avg_waiting_time, 
                "avg_queue_system": avg_queue_system,
                "max_queue": max_queue_length,
                }

    except Exception as e:        
        print("[ERROR]", e)
        traci.close(False)
        raise

if __name__ == '__main__':                    
    SUMO_CFG_PATH = "./traffic-light-benchmark/four_semaphores/traffic.sumocfg"
    # SUMO_CFG_PATH = "./santo-andre-benchmark/demand.sumocfg"
    semaphores_information = fetch_graph_information(SUMO_CFG_PATH).copy()
    print("[DBG] FINISHED INFORMATION FETCH")
    evaluate_policy(offsets=len(semaphores_information) * [0],
        green_times = [15, 15, 15, 15, 15, 15, 15, 15, 15], # Check: this needs to be of size of the amount of green times.
        cycle_time=60,
        semaphores_original_information=semaphores_information,
        gui=True,
        verbose=True,
        path=SUMO_CFG_PATH)