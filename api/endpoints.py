from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from database import create_db_and_tables, get_session
from sqlmodel import Session, select
from models import Simulation
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


@app.get("/simulations", response_model=list[Simulation])
def get_simulations(session: Session = Depends(get_session)):
    sims = session.exec(select(Simulation)).all()
    return sims



@app.get("/simulations/{simulation_id}")
def get_simulation_by_id(simulation_id: int, session: Session = Depends(get_session)):
    sim = session.get(Simulation, simulation_id)
    if not sim:
        raise HTTPException(status_code=404, detail="Simulation not found")
    return sim



@app.post("/simulations/create", response_model=Simulation)
def create_simulation_endpoint(name: str = Form(...), sim_type: str = Form(...), session: Session = Depends(get_session)):
    sim = create_simulation(name, sim_type, session)
    return sim



@app.put("/simulations/update/{simulation_id}", response_model=Simulation)
def update_simulation(simulation_id: int, status: str = None, execution_time: float = None, session: Session = Depends(get_session)):
    sim = session.get(Simulation, simulation_id)

    if not sim:
        raise HTTPException(status_code=404, detail="Simulation not found")
    
    new_status = status if status != None else sim.status
    new_exec_time = execution_time if execution_time != None else sim.execution_time

    sim.status = new_status
    sim.execution_time = new_exec_time
    session.add(sim)
    session.commit()
    session.refresh(sim)
    
    return sim



@app.delete("/simulations/remove/{simulation_id}")
def delete_simulation(simulation_id: int, session: Session = Depends(get_session)):
    sim = session.get(Simulation, simulation_id)

    if not sim:
        raise HTTPException(status_code=404, detail="Simulation not found")
    
    #Remove extracted files
    folder_path = EXTRACT_DIR / sim.name
    shutil.rmtree(folder_path,ignore_errors=True)

    #Remove db data
    session.delete(sim)
    session.commit()
    return {"msg": "Simulation deleted successfully"}
    


#Receive .zip file and extract contents
@app.post("/simulations/upload")
async def upload_simulation_file(
    file: UploadFile = File(...),
    name: str = Form(...),
    sim_type: str = Form(...),
    session: Session = Depends(get_session)
    ):
    
    # Validate file type and simulation type
    if not file.filename.endswith('.zip'):
        raise HTTPException(status_code=400, detail="Only .zip files are accepted")
    elif sim_type not in ["default", "optimized"]:
        raise HTTPException(status_code=400, detail="Invalid simulation type")
    
    zip_content = await file.read()

    # Try to extract the zip file
    try:
        with zipfile.ZipFile(io.BytesIO(zip_content)) as zip_file:
            base_dest = EXTRACT_DIR / name
            dest = get_unique_folder(base_dest)
            zip_file.extractall(dest)
            extracted_files = zip_file.namelist()

    except zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail="Invalid zip file")
    
    #Save data into database
    create_simulation(dest.name, sim_type, session)

    return {"files_extracted": extracted_files}



@app.post("/simulations/start/{simulation_id}")
def start_simulation(simulation_id: int, gui: bool = False, verbose: bool = False, session: Session = Depends(get_session)):
    sim = session.get(Simulation, simulation_id)
    if not sim:
        raise HTTPException(status_code=404, detail="Simulation not found")

    folder_name = EXTRACT_DIR / sim.name
    #Call the simulation script based on sim_type
    if sim.sim_type == "default":
        print("Processing default simulation...")
        # subprocess.Popen(["python3", "count.py"])
        #TODO: Call the default simulation script here
    elif sim.sim_type == "optimized":
        print("Processing optimized simulation...")
        #TODO: Call the optimized simulation script here
    else:
        raise HTTPException(status_code=400, detail="Unknown simulation type")
    
    return {"msg": f"Simulation {sim.name} of type {sim.sim_type} started."}


def create_simulation(name: str, sim_type: str, session: Session):
    sim = Simulation(name=name, sim_type=sim_type)
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
