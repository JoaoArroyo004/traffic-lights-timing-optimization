import argparse
import json
from pathlib import Path
from traffic_lights_timing_optimization.evaluate_policy import evaluate_policy
from traffic_lights_timing_optimization.evaluate_std_policy import evaluate_std_policy
from traffic_lights_timing_optimization.fetch_graph_information import fetch_graph_information



def parse_args():
    parser = argparse.ArgumentParser()

    parser.add_argument("--case", type=str, required=True)
    parser.add_argument("--input_folder", type=str, required=True)
    parser.add_argument("--offsets", type=str, required=False)
    parser.add_argument("--greens", type=str, required=False)
    parser.add_argument("--last_greens", type=str, required=False)

    # se você for adicionar no futuro:
    parser.add_argument("--gui", action="store_true")
    parser.add_argument("--verbose", action="store_true")

    return parser.parse_args()



if __name__ == "__main__":
    args = parse_args()

    case = args.case
    input_file = Path(args.input_folder) / "demand.sumocfg"
    offsets = json.loads(args.offsets) if args.offsets else []
    green_times = json.loads(args.greens) if args.greens else []
    calculated_last_greens = json.loads(args.last_greens) if args.last_greens else []

    print("Offsets:", offsets)
    print("Greens:", green_times)
    print("Last greens:", calculated_last_greens)
    print("Input file:", input_file)
    print("Case:", case)
    print("GUI:", args.gui)
    print("Verbose:", args.verbose)

    semaphores_information = fetch_graph_information(input_file).copy()


    if case == "optimized":

        evaluate_policy(offsets=offsets,
        green_times = green_times,        
        times_for_last_green=calculated_last_greens,
        semaphores_original_information=semaphores_information,
        cycle_time=75,
        gui=args.gui,
        verbose=args.verbose,
        path=input_file)

    elif case == "default":

        evaluate_std_policy(gui=args.gui,
            verbose=args.verbose,
            path=input_file)
