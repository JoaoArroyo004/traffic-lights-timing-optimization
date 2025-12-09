from traffic_lights_timing_optimization.run_nsga2_parallel import optimize

import os
import shutil
import argparse
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from traffic_lights_timing_optimization.evaluate_std_policy import evaluate_std_policy

API_RELATIVE_PATH = Path("./")

import csv
import ast


def get_best_solutions(res_F, csv_folder, ndigits=2):
    """
    res_F: iterable of [max_queue, avg_wait]
    csv_folder: folder containing CSV files

    Compares using rounded values (ndigits decimal places).

    Returns:
        A list in the same order as res_F where each element is:
        (offsets, greens, last_greens, results)
        or None if not found.

        `results` is returned as a list of floats as read from the CSV:
        [avg_wait_csv, ..., max_queue_csv]
    """
    csv_folder = Path(csv_folder)

    # Round res.F into tuples (max_queue, avg_wait)
    targets = [
        (round(float(x[0]), ndigits), round(float(x[1]), ndigits))
        for x in res_F
    ]
    remaining = set(targets)
    found = {target: None for target in targets}

    for csv_path in csv_folder.glob("*.csv"):
        offsets = greens = last_greens = None

        with csv_path.open("r", encoding="utf-8") as f:
            reader = csv.reader(f)

            for row in reader:
                if not row:
                    continue

                key = row[0].strip()

                if key == "OFFSETS":
                    offsets = ast.literal_eval(row[1])

                elif key == "GREENS":
                    greens = ast.literal_eval(row[1])

                elif key == "LAST_GREENS":
                    last_greens = ast.literal_eval(str(row[1]))

                elif key.startswith("RESULTS"):
                    # Example: ["RESULTS:", "avg_wait", "...", "max_queue"]
                    nums = [float(x) for x in row[1:] if x != ""]
                    if len(nums) < 2:
                        continue

                    avg_wait_csv = round(nums[0], ndigits)
                    max_queue_csv = round(nums[-1], ndigits)

                    # res.F is (max_q, avg_w)
                    pair = (max_queue_csv, avg_wait_csv)

                    if pair in remaining:
                        found[pair] = (offsets, greens, last_greens, nums)
                        remaining.remove(pair)

            if not remaining:
                break

    # Return in the same order as res.F (using the rounded targets)
    return [found.get(target) for target in targets]


def save_solutions_to_csv(solutions, output_csv):
    """
    solutions: list of (offsets, greens, last_greens, results)
    output_csv: path for the CSV file to be created
    """
    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        for sol in solutions:
            if sol is None:
                # Skip missing solutions
                continue
            
            offsets, greens, last_greens, results = sol

            writer.writerow(["OFFSETS", str(offsets)])
            writer.writerow(["GREENS", str(greens)])
            writer.writerow(["LAST_GREENS", str(last_greens)])
            writer.writerow(["RESULTS:"] + results)
            writer.writerow([])  # blank line between solutions



def delete_all_csv(folder):
    folder = Path(folder)
    for csv_file in folder.glob("*.csv"):
        csv_file.unlink()   # deleta o arquivo


def parse_args():
    parser = argparse.ArgumentParser()

    parser.add_argument("--population", type=int, required=True)
    parser.add_argument("--generation", type=int, required=True)
    parser.add_argument("--input_folder", type=str, required=True)
    parser.add_argument("--output_folder", type=str, required=True)

    return parser.parse_args()


def move_file(file_path: str, dst_dir: str):
    """
    Move a single file to the destination directory.
    If the destination directory does not exist, it will be created.
    """
    if not os.path.isfile(file_path):
        raise ValueError(f"File does not exist: {file_path}")

    os.makedirs(dst_dir, exist_ok=True)

    file_name = os.path.basename(file_path)
    dst_path = os.path.join(dst_dir, file_name)

    shutil.move(file_path, dst_path)


def create_directory(path: str):
    """
    Create a directory with the given path/name.
    If it already exists, nothing happens.
    """
    os.makedirs(path, exist_ok=True)    


def move_all_files(src: str, dst: str):
    """
    Move all files from src directory to dst directory.
    Only moves files (not subdirectories).
    """
    if not os.path.isdir(src):
        raise ValueError(f"Source directory does not exist: {src}")
        
    create_directory(dst)

    for filename in os.listdir(src):
        src_path = os.path.join(src, filename)
        
        if os.path.isfile(src_path):
            dst_path = os.path.join(dst, filename)
            shutil.move(src_path, dst_path)



def run_experiment(args):
    input_file = API_RELATIVE_PATH / args.input_folder / "demand.sumocfg"
    print(f"[DBG] input file: {input_file}")
    print(f"[DBG] population: {args.population}")
    print(f"[DBG] generation: {args.generation}")
    print(f"Diretorio atual: {os.getcwd()}")

    # Run optimization and get results
    res = optimize(pop_size=args.population, n_gen=args.generation, input_file=input_file, plot_pareto=False)
    F = res.F
    
    
    F = np.array(F)
    F_rounded = np.round(F, 2)
    unique = np.unique(F_rounded, axis=0)


    # Get best solutions from CSVs and save to a new CSV
    solutions = get_best_solutions(unique, "./logs_parallel")
    delete_all_csv("./logs_parallel")
    save_solutions_to_csv(solutions, "logs_parallel/solutions.csv")


    #Create a new run directory
    output_folder = API_RELATIVE_PATH / args.output_folder
    existing = [p for p in output_folder.iterdir() if p.is_dir() and p.name.startswith("Run_")]
    indices = []
    for folder in existing:
        try:
            index = int(folder.name.split("_")[1])
            indices.append(index)
        except:
            pass


    # Evaluate traditional policy
    # if not (API_RELATIVE_PATH / args.output_folder / 'Run_0').exists():
    res_t = evaluate_std_policy(gui=False,
        verbose=False,
        path=input_file)

    avg_wait = res_t['avg_waiting_time']
    avg_queue = res_t['avg_queue_system']
    max_queue = res_t['max_queue']

    create_directory(API_RELATIVE_PATH / args.output_folder / 'Run_0')
    with open(API_RELATIVE_PATH / args.output_folder / 'Run_0' / "traditional.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["RESULTS:", round(avg_wait, 2), round(avg_queue, 2), round(max_queue, 2)])


    next_index = max(indices) + 1 if indices else 1
    curr_dir = output_folder / f'Run_{next_index}'
    create_directory(curr_dir)


    # Plot Pareto front
    plt.figure(figsize=(6, 5))
    plt.scatter(F[:, 0], F[:, 1], color="blue", alpha=0.7)
    plt.scatter(max_queue, avg_wait, color="red", alpha=0.7)
    plt.xlabel("Max Queue Length")
    plt.ylabel("Average Waiting Time")
    plt.title("Traffic Optimization - Pareto Front (NSGA-II)")
    plt.grid(True)
    plt.savefig("pareto_front.png", dpi=300, bbox_inches="tight")
    plt.close()


    # Move results to the new run directory
    move_all_files('./logs_parallel', curr_dir)
    move_file('gen_log.txt', curr_dir)
    move_file('seed.txt', curr_dir)
    move_file('pareto_front.png', curr_dir)        


if __name__ == '__main__':
    args = parse_args()
    run_experiment(args)