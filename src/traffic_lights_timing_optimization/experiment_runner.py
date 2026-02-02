from traffic_lights_timing_optimization.run_nsga2_parallel import optimize

import os
import shutil

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

def run_experiment(amount_runs, generations, population, sumo_path, cycle_time, threads):
    for i in range (1, amount_runs + 1):        
        optimize(generations, population, sumo_path, cycle_time, threads)
        curr_dir = f'./experiment_ID{i}'
        create_directory(curr_dir)
        move_all_files('./logs_parallel', curr_dir)
        # move_file('gen_log.txt', curr_dir)
        move_file('seed.txt', curr_dir)
        move_file('pareto_front.png', curr_dir)        


if __name__ == '__main__':
    run_experiment(amount_runs=1, generations=1000, population= 100, sumo_path="./santo-andre-extendido/demand.sumocfg", cycle_time=75, threads=4)
