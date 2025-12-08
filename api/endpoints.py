from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from database import create_db_and_tables, get_session
from sqlmodel import Session, select
from models import Scenario
import zipfile, subprocess, io, uvicorn, shutil



EXTRACT_DIR = Path("extracted")
EXTRACT_DIR.mkdir(exist_ok=True)

app = FastAPI()

ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

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
    return sim



@app.post("/scenarios/create", response_model=Scenario)
def create_scenario_endpoint(name: str = Form(...), sim_type: str = Form(...), session: Session = Depends(get_session)):
    sim = create_scenario(name, sim_type, session)
    return sim



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
    elif sim_type not in ["default", "optimized"]:
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


@app.post("/scenarios/optmize/{scenario_id}")
def optimize_scenario(scenario_id: int,
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
                        "--input_folder", str(folder_name / "Files"),
                        "--output_folder", str(folder_name / "Runs")])
    return {"msg": f"Optimization for scenario {sim.name} started with population {population} and generation {generation}."}


@app.post("/scenarios/simulate/{scenario_id}")
def start_scenario(scenario_id: int, 
                   gui: bool = False, 
                   verbose: bool = False, 
                   session: Session = Depends(get_session)):
    sim = session.get(Scenario, scenario_id)
    if not sim:
        raise HTTPException(status_code=404, detail="Scenario not found")

    folder_name = EXTRACT_DIR / sim.name
    #Call the scenario script based on sim_type
    if sim.sim_type == "default":
        print("Processing default scenario...")
        subprocess.Popen(["python3", "../src/traffic_lights_timing_optimization/count.py"])
        # subprocess.Popen(["python3", "count.py"])

        #TODO: Call the default scenario script here
    elif sim.sim_type == "optimized":
        print("Processing optimized scenario...")
        #TODO: Call the optimized scenario script here
    else:
        raise HTTPException(status_code=400, detail="Unknown scenario type")
    
    return {"msg": f"Scenario {sim.name} of type {sim.sim_type} started."}


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
