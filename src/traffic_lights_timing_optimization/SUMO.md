# SUMO guide:

This is a small cheat-sheet for SUMO commands and syntax, to avoid the need
to search for the same information over and over.

## Create a scenario:
Create the following files (or import from known benchmarks):
- edges.edg.xml: contains the edges of the graph. Each connects two nodes.
- nodes.nod.xml: contains the nodes of the graph. The traffic lights are declared here.
- routes.rout.xml: contains the input flow of vehicles in the network. Each vehicle must have its
start and end points defined.

### Generate net.net.xml file:
This file is quite complicated and very hard to correctly write by hand. It is better, even for simple
cases, to use:
```shell
netconvert --node-files=nodes.nod.xml --edge-files=edges.edg.xml --output-file=net.net.xml
```

Last, we do need a ```.sumocfg``` file. This file is what is called for the initialization
of the simulation - Be it by traci or terminal. It should link to net.net.xml and routes.rout.xml.

## Execute scenario:
First, to guarantee correctness of the benchmark, it is better to execute the simulation
without using any module from the GA or the traci semaphore-customized simulation.
For this, one can use the GUI in the following way. Remember to change the path/filename
accordingly.
```shell
sumo-gui -c traffic.sumocfg
```

## Run with traci (python)
In order to integrate with the G.A, we need to modify the semaphore policy based on
the current solution that was sent to the simulator function. To do this, it is good
to keep in mind the following commands:

- Sumo initialization:
```python
    sumoCmd = ["sumo", "-c", "./traffic-light-benchmark/traffic.sumocfg", "--no-step-log", "true"]
    traci.start(sumoCmd)
```
- Get id from the traffic lights.
```python
tls_id = traci.trafficlight.getIDList()
```
- Get traffic light plan from a specific semaphore:
```python
logic = traci.trafficlight.getCompleteRedYellowGreenDefinition(tls_id)[0]
```
A traffic plan usually has 2 attributes: the state, which represents the state
of the semaphore for each of the incoming flows (notice no more than 1 can be green
at once), and the duration of the corresponding state.

- Program application:
```python
program = traci.trafficlight.Logic(
            "custom", 0, 0, new_phases
        )
```
The second 0 is the semaphore id, and the new_phases should be an array with a new plan.
We can finally set the new program with:
```python
traci.trafficlight.setCompleteRedYellowGreenDefinition(tls_id, program)
```
