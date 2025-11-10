import traci

def evaluate_policy(flux1_fractions=[0.7], offsets = [0], cycle_time=60, gui=False, verbose=False):
    """
    Evaluates a traffic light policy by adjusting the green phase durations
    based on a given fraction (e.g., from a GA individual).

    - green_fraction: scaling factor applied to green durations.
    """        
    
    operationMode = "sumo-gui" if gui else "sumo" # SUMO with GUI ONLY for debugging
    port = traci.getFreeSocketPort()
    sumoCmd = [
        operationMode,
        "-c", "./traffic-light-benchmark/four_semaphores/traffic.sumocfg",
        "--no-step-log",
        "--no-warnings"
        "--start",                # start simulation immediately (skip GUI pause)
        "--time-to-teleport", "-1",  # disable teleportation
        "--waiting-time-memory", "1000",  # longer waiting-time window
    ]
    traci.start(sumoCmd, port=port)    
    if verbose:
        print("[INFO] Connection stablished")

    try:
        tls_ids = traci.trafficlight.getIDList()
        if verbose:
            print(f"[INFO] Connected to TLS: {tls_ids}")
            
        if verbose:
            print(f"[DBG] Check existing plan")
            for i, tls_id in enumerate(tls_ids):            
                print(f"Check id: {tls_id}")
                logic = traci.trafficlight.getCompleteRedYellowGreenDefinition(tls_id)[0]
                for phase in logic.phases:
                    if verbose:
                        print(f"Phase state: {phase.state} duration {phase.duration}")
            print("------- ------\n")
                
        print(f"[DBG]Assign new plan")
        for i, tls_id in enumerate(tls_ids):
            logic = traci.trafficlight.getCompleteRedYellowGreenDefinition(tls_id)[0]
        
            time_yellow1 = max(4, 0.9 * flux1_fractions[i])
            time_green1 = max(5, cycle_time * flux1_fractions[i] - time_yellow1)
            time_yellow2 = max(4, 0.9 * (1 - flux1_fractions[i]))
            time_green2 = max(5, cycle_time * (1 - flux1_fractions[i]) - time_yellow2)
        
            new_phases = []
            for phase in logic.phases:
                if  phase.state[0] in ['G', 'g']:
                    new_duration = time_green1
                elif phase.state[0] in ['Y', 'y']:
                    new_duration = time_yellow1
                elif 'G' in phase.state or 'g' in phase.state:
                    new_duration = time_green2
                elif 'Y' in phase.state or 'y' in phase.state:
                    new_duration = time_yellow2
                else:
                    print("[ERROR] Semaphore plan contains unkown state.")

                new_phases.append(traci.trafficlight.Phase(new_duration, phase.state))

            if verbose:
                print("[DBG] Check the new semaphore policy")
                for phase in new_phases:
                    print(f"-- Phase state: {phase.state} duration {phase.duration}")        
                print("-------")
        
            program = traci.trafficlight.Logic("custom", 0, 0, new_phases) # last arg = phase
            traci.trafficlight.setCompleteRedYellowGreenDefinition(tls_id, program)            

            offset_time = offsets[i] % cycle_time
            traci.trafficlight.setPhaseDuration(tls_id, offset_time) # Set offset.
            if verbose:
                print(f"[INFO] Phase offset applied: {offset_time:.2f} seconds")

        
        print("[DBG] Custom program applied successfully.\n Start simulation")
        # ------- SIMULATION VARIABLES ---- #
        step = 0
        total_waiting_time = 0.0
        total_vehicles = 0
        max_queue_length = 0                
        graphEdges = traci.edge.getIDList()        
        sum_queues = 0.0        
        # Check if there are still vehicles to be processed
        # Prefer this, because we do not know the step in which the last vehicle achieves its goal.
        while traci.simulation.getMinExpectedNumber() > 0: 
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

            step += 1
        print("[DBG] Simulation finished")
        
        traci.close()

        avg_queue_system = sum_queues / step
        avg_waiting_time = total_waiting_time / max(1, total_vehicles)        
        if verbose:
            print(f"[RESULT] Avg waiting time: {avg_waiting_time:.2f}, Max per-edge queue length: {max_queue_length}")
                    
        return {"avg_travel_time": avg_waiting_time, 
                "avg_queue_system": avg_queue_system,
                "max_queue": max_queue_length,
                }

    except Exception as e:        
        print("[ERROR]", e)
        traci.close(False)
        raise

if __name__ == '__main__':
    evaluate_policy(flux1_fractions = [0.5, 0.5, 0.4, 0.7],
        offsets=[0,5,10,15],
        cycle_time=60,
        gui=True,
        verbose=True)