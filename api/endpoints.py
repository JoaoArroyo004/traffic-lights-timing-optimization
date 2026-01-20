from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from database import create_db_and_tables, get_session
from sqlmodel import Session, select
from models import Scenario
from pydantic import BaseModel
from typing import List, Optional, Dict, Any, Tuple
import zipfile, subprocess, io, uvicorn, shutil, json, csv, ast, base64
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt




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




def read_first_results_line(path: Path) -> list[float]:
    if not path.exists():
        raise FileNotFoundError(path)
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if line.startswith("RESULTS"):
            parts = [p.strip() for p in line.split(",")[1:] if p.strip()]
            return [float(x) for x in parts]
    raise ValueError(f"Nenhuma linha RESULTS em {path}")

def parse_solutions_file(path: Path) -> list[dict]:
    if not path.exists():
        return []

    def parse_list(v: str) -> list[float]:
        v = v.strip().strip('"').strip()
        return [float(x) for x in ast.literal_eval(v)]

    sols, cur = [], {}
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line:
            if {"offsets","greens","last_greens","results"} <= cur.keys():
                sols.append(cur)
            cur = {}
            continue

        if line.startswith("RESULTS"):
            cur["results"] = [float(x) for x in line.split(",")[1:] if x.strip()]
            continue

        if "," in line:
            k, v = line.split(",", 1)
            k = k.strip().upper()
            v = v.strip()
            if k == "OFFSETS":
                cur["offsets"] = parse_list(v)
            elif k == "GREENS":
                cur["greens"] = parse_list(v)
            elif k == "LAST_GREENS":
                cur["last_greens"] = parse_list(v)

    if {"offsets","greens","last_greens","results"} <= cur.keys():
        sols.append(cur)

    return sols

def pareto_nondominated(solutions: list[dict]) -> list[dict]:
    def dominates(a, b) -> bool:
        return (a[0] <= b[0] and a[1] <= b[1]) and (a[0] < b[0] or a[1] < b[1])

    pts = [(s["results"][0], s["results"][-1]) for s in solutions]
    out = []
    for i, p in enumerate(pts):
        if not any(dominates(pts[j], p) for j in range(len(pts)) if j != i):
            out.append(solutions[i])
    return out

def write_traditional_csv(path: Path, traditional_results: list[float]) -> None:
    line = "RESULTS:," + ",".join(str(x) for x in traditional_results)
    path.write_text(line + "\n", encoding="utf-8")



def write_pareto_csv(path: Path, pareto: list[dict]) -> None:
    def fmt_list(nums: list[float]) -> str:
        return str([f"{x}" for x in nums])

    lines: list[str] = []

    for s in pareto:
        lines.append(f'OFFSETS ,"{fmt_list(s["offsets"])}"')
        lines.append(f'GREENS ,"{fmt_list(s["greens"])}"')
        lines.append(f'LAST_GREENS ,"{fmt_list(s["last_greens"])}"')
        lines.append("RESULTS:," + ",".join(str(x) for x in s["results"]))
        lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")


@app.post("/scenarios/generate_final/{scenario_id}")
def generate_final(scenario_id: int, session: Session = Depends(get_session)):
    sim = session.get(Scenario, scenario_id)
    if not sim:
        raise HTTPException(status_code=404, detail="Scenario not found")

    folder = EXTRACT_DIR / sim.name
    final_dir = folder / "Final"
    final_dir.mkdir(exist_ok=True)

    runs = folder / "Runs"

    try:
        traditional_results = read_first_results_line(runs / "Run_0" / "traditional.csv")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro no tradicional.csv: {e}")

    all_solutions = []
    for run_dir in sorted(runs.glob("Run_*")):
        if run_dir.name == "Run_0":
            continue
        sols = parse_solutions_file(run_dir / "solutions.csv")
        all_solutions.extend(sols)

    pareto = pareto_nondominated(all_solutions)


    traditional_csv_path = final_dir / "traditional.csv"
    pareto_csv_path = final_dir / "final.csv"
    pareto_png_path = final_dir / "pareto_front.png"


    write_traditional_csv(traditional_csv_path, traditional_results)
    write_pareto_csv(pareto_csv_path, pareto)
    write_pareto_plot_png(pareto_png_path, pareto, traditional_results)

    return {"msg": "Final results generated successfully."}

def write_pareto_plot_png(
    out_path: Path,
    pareto_solutions: List[Dict],
    traditional_results: List[float],
) -> None:
    xs = [s["results"][-1] for s in pareto_solutions] 
    ys = [s["results"][0] for s in pareto_solutions]  

    trad_x = traditional_results[-1]
    trad_y = traditional_results[0]  

    plt.figure(figsize=(6, 5))
    if xs and ys:
        plt.scatter(xs, ys, alpha=0.7)
    plt.scatter(trad_x, trad_y, color="red", alpha=0.7)

    plt.xlabel("Max Queue Length")
    plt.ylabel("Average Waiting Time")
    plt.title("Traffic Optimization - Pareto Front (NSGA-II)")
    plt.grid(True)

    out_path.parent.mkdir(exist_ok=True, parents=True)
    plt.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close()


def parse_final_csv(final_csv_path: Path) -> List[Dict[str, Any]]:

    if not final_csv_path.exists():
        return []

    def parse_list(v: str) -> List[float]:
        v = v.strip().strip('"').strip()
        return [float(x) for x in ast.literal_eval(v)]

    sols: List[Dict[str, Any]] = []
    cur: Dict[str, Any] = {}

    for raw in final_csv_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()

        if not line:
            if {"offsets", "greens", "last_greens", "results"} <= cur.keys():
                sols.append(cur)
            cur = {}
            continue

        if line.startswith("RESULTS"):
            parts = [p.strip() for p in line.split(",")[1:] if p.strip() != ""]
            nums = [float(x) for x in parts]
            if len(nums) >= 3:
                cur["results"] = {
                    "avg_wait": nums[0],
                    "avg_queue": nums[1],
                    "max_queue": nums[2],
                }
            continue

        if "," in line:
            k, v = line.split(",", 1)
            k = k.strip().upper()
            v = v.strip()

            if k == "OFFSETS":
                cur["offsets"] = parse_list(v)
            elif k == "GREENS":
                cur["greens"] = parse_list(v)
            elif k == "LAST_GREENS":
                cur["last_greens"] = parse_list(v)

    if {"offsets", "greens", "last_greens", "results"} <= cur.keys():
        sols.append(cur)

    return sols


@app.get("/scenarios/final/{scenario_id}")
def get_final_results(scenario_id: int, session: Session = Depends(get_session)):
    sim = session.get(Scenario, scenario_id)
    if not sim:
        raise HTTPException(status_code=404, detail="Scenario not found")

    final_folder = EXTRACT_DIR / sim.name / "Final"
    if not final_folder.exists():
        return {
            "name": sim.name,
            "traditional_policy_results": {},
            "pareto_solutions": [],
        }
    
    # ---- IMAGEM ----
    img_path = final_folder / "pareto_front.png"
    img = None
    if img_path.exists():
        with img_path.open("rb") as f:
            encoded = base64.b64encode(f.read()).decode("utf-8")
            img = f"data:image/png;base64,{encoded}"

    traditional_policy_results = get_traditional_policy_results(final_folder)

    pareto_solutions = parse_final_csv(final_folder / "final.csv")

    return {
        "name": sim.name,
        "traditional_policy_results": traditional_policy_results,
        "pareto_solutions": pareto_solutions,
        "n_pareto": len(pareto_solutions),
        "pareto_image": img,
    }