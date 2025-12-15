from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from database import create_db_and_tables, get_session
from sqlmodel import Session, select
from models import Scenario
from pydantic import BaseModel
from typing import List, Optional, Dict
import zipfile, subprocess, io, uvicorn, shutil, json, csv, ast, base64



EXTRACT_DIR = Path("extracted")
EXTRACT_DIR.mkdir(exist_ok=True)
ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]



app = FastAPI()



class SimulationParams(BaseModel):
    offsets: List[float]
    greens: List[float]
    last_greens: List[float]



# CORS configuration: it's necessary to allow sending responses to the front end
app.add_middleware(
    CORSMiddleware,
    allow_origins=ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],   
    allow_headers=["*"],
)



@app.on_event("startup")
def on_startup():
    create_db_and_tables()



@app.get("/scenarios", response_model=list[Scenario])
def get_scenarios(session: Session = Depends(get_session)):
    sims = session.exec(select(Scenario)).all()
    return sims



@app.get("/scenarios/{scenario_id}")
def get_scenario_by_id(scenario_id: int, session: Session = Depends(get_session)):
    sim = session.get(Scenario, scenario_id)

    if not sim:
        raise HTTPException(status_code=404, detail="Scenario not found")

    runs_folder = EXTRACT_DIR / sim.name / "Runs"

    runs = get_runs_data(runs_folder)
    traditonal_policy_results = get_traditional_policy_results(runs_folder / "Run_0")
    data = {
        "name": sim.name,
        "n_runs": len(list(runs_folder.iterdir()))-1 if runs_folder.exists() else 0,
        "traditional_policy_results": traditonal_policy_results,
        "runs": runs
    }
    return data



@app.post("/scenarios/create", response_model=Scenario)
def create_scenario_endpoint(name: str = Form(...), sim_type: str = Form(...), session: Session = Depends(get_session)):
    sim = create_scenario(name, sim_type, session)
    return sim



# Update scenario status and execution time
@app.put("/scenarios/update/{scenario_id}", response_model=Scenario)
def update_scenario(scenario_id: int, status: str = None, execution_time: float = None, session: Session = Depends(get_session)):
    sim = session.get(Scenario, scenario_id)

    if not sim:
        raise HTTPException(status_code=404, detail="Scenario not found")
    
    new_status = status if status != None else sim.status
    new_exec_time = execution_time if execution_time != None else sim.execution_time

    sim.status = new_status
    sim.execution_time = new_exec_time
    session.add(sim)
    session.commit()
    session.refresh(sim)
    
    return sim



# Delete a scenario by ID
@app.delete("/scenarios/remove/{scenario_id}")
def delete_scenario(scenario_id: int, session: Session = Depends(get_session)):
    sim = session.get(Scenario, scenario_id)

    if not sim:
        raise HTTPException(status_code=404, detail="Scenario not found")
    
    #Remove extracted files
    folder_path = EXTRACT_DIR / sim.name
    shutil.rmtree(folder_path,ignore_errors=True)

    #Remove db data
    session.delete(sim)
    session.commit()
    return {"msg": "Scenario deleted successfully"}
    


#Receive .zip file and extract contents
@app.post("/scenarios/upload")
async def upload_scenario_file(
    file: UploadFile = File(...),
    name: str = Form(...),
    sim_type: str = Form(...),
    session: Session = Depends(get_session)
    ):
    
    # Validate file type and scenario type
    if not file.filename.endswith('.zip'):
        raise HTTPException(status_code=400, detail="Only .zip files are accepted")
    elif sim_type not in ["Multi-Objective GA"]:
        raise HTTPException(status_code=400, detail="Invalid scenario type")
    
    zip_content = await file.read()

    # Try to extract the zip file
    try:
        with zipfile.ZipFile(io.BytesIO(zip_content)) as zip_file:
            base_dest = EXTRACT_DIR / name
            dest = get_unique_folder(base_dest)
            zip_file.extractall(dest / "Files")
            extracted_files = zip_file.namelist()

    except zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail="Invalid zip file")
    
    # Create a folder with name Runs inside the extracted folder
    runs_folder = dest / "Runs"
    runs_folder.mkdir(exist_ok=True)
    
    #Save data into database
    create_scenario(dest.name, sim_type, session)

    return {"files_extracted": extracted_files}



# Optimize scenario for a given scenario
@app.post("/scenarios/optmize/{scenario_id}")
def optimize_scenario(scenario_id: int,
                      simulation_time:int,
                      cycle_time:int = 75,
                      population: int = 1,
                      generation: int = 1,
                      session: Session = Depends(get_session)):
    
    sim = session.get(Scenario, scenario_id)
    if not sim:
        raise HTTPException(status_code=404, detail="Scenario not found")
    folder_name = EXTRACT_DIR / sim.name
    #Call the optimization script
    subprocess.Popen(["poetry", "run", "python", "../src/traffic_lights_timing_optimization/experiment_runner_frontend.py",
                      "--population", str(population),
                        "--generation", str(generation),
                        "--cycle_time", str(cycle_time),
                        "--simulation_time", str(simulation_time),
                        "--input_folder", str(folder_name / "Files"),
                        "--output_folder", str(folder_name / "Runs")])
    return {"msg": f"Optimization for scenario {sim.name} started with population {population} and generation {generation}."}



# Start simulation for a given scenario
@app.post("/scenarios/simulate/{scenario_id}")
def start_scenario(scenario_id: int, 
                   params: SimulationParams,
                   simulation_time:int,
                   cycle_time:int = 75,
                   case: str = "default",
                   gui: bool = False, 
                   verbose: bool = False, 
                   session: Session = Depends(get_session)):
    
    sim = session.get(Scenario, scenario_id)
    if not sim:
        raise HTTPException(status_code=404, detail="Scenario not found")

    folder_name = EXTRACT_DIR / sim.name
    
    #Call the scenario script based on sim_type
    if case == "optimized":
        print("Processing optimized scenario...")
        cmd = [
            "poetry", "run", "python",
            "../src/traffic_lights_timing_optimization/debug_nsga_run_frontend.py",
            "--case", str(case),
            "--offsets", json.dumps(params.offsets),
            "--simulation_time", str(simulation_time),
            "--cycle_time", str(cycle_time),
            "--greens", json.dumps(params.greens),
            "--last_greens", json.dumps(params.last_greens),
            "--input_folder", str(folder_name / "Files")
        ]

        if gui:
            cmd.append("--gui")
        if verbose:
            cmd.append("--verbose")

        subprocess.Popen(cmd)


    elif case == "default":
        print("Processing default scenario...")
        cmd = [
            "poetry", "run", "python",
            "../src/traffic_lights_timing_optimization/debug_nsga_run_frontend.py",
            "--case", str(case),
            "--simulation_time", str(simulation_time),
            "--input_folder", str(folder_name / "Files")
        ]

        if gui:
            cmd.append("--gui")

        if verbose:
            cmd.append("--verbose")

        subprocess.Popen(cmd)
    
    elif case == "both":
        print("Processing both scenarios...")

        # Default case
        cmd_default = [
            "poetry", "run", "python",
            "../src/traffic_lights_timing_optimization/debug_nsga_run_frontend.py",
            "--case", "default",
            "--simulation_time", str(simulation_time),
            "--input_folder", str(folder_name / "Files")
        ]

        if gui:
            cmd_default.append("--gui")

        if verbose:
            cmd_default.append("--verbose")

        subprocess.Popen(cmd_default)

        # Optimized case
        cmd_optimized = [
            "poetry", "run", "python",
            "../src/traffic_lights_timing_optimization/debug_nsga_run_frontend.py",
            "--case", "optimized",
            "--simulation_time", str(simulation_time),
            "--cycle_time", str(cycle_time),
            "--offsets", json.dumps(params.offsets),
            "--greens", json.dumps(params.greens),
            "--last_greens", json.dumps(params.last_greens),
            "--input_folder", str(folder_name / "Files")
        ]

        if gui:
            cmd_optimized.append("--gui")
        if verbose:
            cmd_optimized.append("--verbose")

        subprocess.Popen(cmd_optimized)


    else:
        raise HTTPException(status_code=400, detail="Unknown case type")
    
    return {"msg": f"Scenario {sim.name} of type {case} started."}



def create_scenario(name: str, sim_type: str, session: Session):
    sim = Scenario(name=name, sim_type=sim_type)
    session.add(sim)
    session.commit()
    session.refresh(sim)
    return sim



def get_unique_folder(base_path: Path) -> Path:
    if not base_path.exists():
        return base_path

    i = 1
    while True:
        new_path = Path(f"{base_path} ({i})")
        if not new_path.exists():
            return new_path
        i += 1



def get_runs_data(runs_folder: Path) -> List[Dict]:
    runs: List[Dict] = []
    if not runs_folder.exists():
        return runs

    # Se o nome não for um diretório ou seu nome for Runs_0, ignore
    for run_dir in sorted(runs_folder.iterdir()):
        if (not run_dir.is_dir()):
            continue

        if run_dir.name == "Run_0":
            continue

        # ---- IMAGEM ----
        img_path = run_dir / "pareto_front.png"
        img = None
        if img_path.exists():
            with img_path.open("rb") as f:
                encoded = base64.b64encode(f.read()).decode("utf-8")
                img = f"data:image/png;base64,{encoded}"

        # ---- SOLUÇÕES ----
        csv_path = run_dir / "solutions.csv"
        solutions = parse_solutions_csv(csv_path)

        run_data = {
            "run_name": run_dir.name,
            "image": img,
            "solutions": solutions,
        }

        runs.append(run_data)

    return runs

def get_traditional_policy_results(runs_folder: Path) -> Dict:
    results = {}
    csv_path = runs_folder / "traditional.csv"

    print(csv_path)

    if not runs_folder.exists():
        return results
    
    if not csv_path.exists():
        return results

    with csv_path.open("r", encoding="utf-8") as f:
        #There is only one row following the formate: ["RESULTS:", avg_wait, avg_queue, max_queue]
        reader = csv.reader(f)
        for row in reader:
            if not row:
                continue
            
            key = row[0].strip()
            if key == "RESULTS:":
                nums = [float(x) for x in row[1:] if x != ""]
                if len(nums) >= 3:
                    results = {
                        "avg_wait": nums[0],
                        "avg_queue": nums[1],
                        "max_queue": nums[2],
                    }
    return results


# Get solutions from CSV file
def parse_solutions_csv(csv_path: Path) -> List[Dict]:
    solutions = []
    if not csv_path.exists():
        return solutions

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
                last_greens = ast.literal_eval(row[1])

            elif key.startswith("RESULTS"):
                nums = [float(x) for x in row[1:] if x != ""]
                if len(nums) >= 2:
                    solution = {
                        "offsets": offsets,
                        "greens": greens,
                        "last_greens": last_greens,
                        "avg_wait": nums[0],
                        "avg_queue": nums[1],
                        "max_queue": nums[2],
                    }
                    solutions.append(solution)

                # Reset to prepare for next block
                offsets = greens = last_greens = None

    return solutions