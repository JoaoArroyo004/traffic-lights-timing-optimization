from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi import UploadFile, File, Form
from pathlib import Path
from fastapi import HTTPException
import zipfile, subprocess, io, uvicorn

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

@app.get("/simulations")
def get_simulations():
    return {"message": "Hello, World!"}

@app.get("/simulations/{simulation_id}")
def get_simulation_by_id(simulation_id: int):
    return {"simulation_id": simulation_id, "status": "running"}


#Receive .zip file and extract contents
@app.post("/simulations/upload")
async def upload_simulation_file(
    file: UploadFile = File(...),
    name: str = Form(...),
    sim_type: str = Form(...)
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
            dest = EXTRACT_DIR / name
            zip_file.extractall(dest)
            extracted_files = zip_file.namelist()

    except zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail="Invalid zip file")
    
    # TODO: Save data into database
    
    #Call the simulation script based on sim_type
    if sim_type == "default":
        print("Processing default simulation...")
        # subprocess.Popen(["python3", "count.py"])
        #TODO: Call the default simulation script here
    else:
        print("Processing optimized simulation...")
        #TODO: Call the optimized simulation script here

    return {"files_extracted": extracted_files, "status_code": 200}