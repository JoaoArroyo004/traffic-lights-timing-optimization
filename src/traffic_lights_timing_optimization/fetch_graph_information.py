import traci

def fetch_graph_information(path="./traffic-light-benchmark/four_semaphores/traffic.sumocfg"):
    """
    Fetches the phases (with the corresponding duration) of each semaphore present in the specified graph.
    
    path: relative path to the .sumocfg file of the benchmark 
    """

    port = traci.getFreeSocketPort()
    sumoCmd = [
        "sumo",
        "-c", path,
        "--no-step-log",
        "--no-warnings",
        "--start",
        "--time-to-teleport", "-1",
        "--waiting-time-memory", "1000"
    ]
    
    traci.start(sumoCmd, port=port) 
    try:
        tls_ids = traci.trafficlight.getIDList()            
        
        print(f"[DBG] Check existing plan")
        semaphores_information: list[list[tuple[str,float]]] = []
        semaphores_phases: list[list[str]] = []
        semaphores_durations: list[list[float]] = []
        for i, tls_id in enumerate(tls_ids):          
            print(f"Checking semaphore with id = {i}")
            logic = traci.trafficlight.getCompleteRedYellowGreenDefinition(tls_id)[0]
            semaphore_information: list[tuple[str,float]] = []
            for phase in logic.phases:                
                print(f"-- Phase state: {phase.state} duration {phase.duration}")
                curr_duration = phase.duration
                curr_phase = "unkown"                
                
                if 'y' in phase.state or 'Y' in phase.state:
                    curr_phase = "yellow"                    
                elif 'g' in phase.state or 'G' in phase.state:
                    curr_phase = "green"                    
                else:
                    curr_phase = "red"                    
                    
                semaphore_information.append([curr_phase, curr_duration])

            lastGreen = -1
            for i in range(len(semaphore_information)):
                if semaphore_information[i][0] == 'green':
                    lastGreen = i
            semaphore_information[lastGreen][0] = "last_green"            
            
            semaphores_information.append(semaphore_information)

        print("[DBG] Information Fetched")        
        traci.close()

        return semaphores_information
    except Exception as e:
        print("[ERROR]", e)
        traci.close(False)
        raise

if __name__ == '__main__':    
    # semaphores_information = fetch_graph_information()
    semaphores_information = fetch_graph_information("./santo-andre-benchmark/demand.sumocfg").copy()
    
    print(f"Check phases and durations: {semaphores_information}\n")