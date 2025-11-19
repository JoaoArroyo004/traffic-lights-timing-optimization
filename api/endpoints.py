from fastapi import FastAPI
from fastapi import UploadFile, File, Form
from pathlib import Path
from fastapi import HTTPException
import zipfile, subprocess, io, uvicorn

EXTRACT_DIR = Path("extracted")
EXTRACT_DIR.mkdir(exist_ok=True)

app = FastAPI()

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
    
    if not file.filename.endswith('.zip'):
        return {"error": "Only .zip files are accepted", "status_code": 400}
    elif sim_type not in ["default", "optimized"]:
        return {"error": "Invalid simulation type", "status_code": 400}
    
    
    zip_content = await file.read()

    try:
        with zipfile.ZipFile(io.BytesIO(zip_content)) as zip_file:
            dest = EXTRACT_DIR / file.filename.replace(".zip", "")
            zip_file.extractall(dest)
            extracted_files = zip_file.namelist()

    except zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail="Invalid zip file")
    
    # TODO: Save data into database
    
    if sim_type == "default":
        print("Processing default simulation...")
        # subprocess.Popen(["python3", "count.py"])
        #TODO: Call the default simulation script here
    else:
        print("Processing optimized simulation...")
        #TODO: Call the optimized simulation script here

    return {"files_extracted": extracted_files, "status_code": 200}



#TODO: A função só retorna 200, mesmo em caso de erro.
#TODO: O front end acusa erro em qualquer situação.
#TODO: Quando envio um arquivo e limpo no front end, preciso recarregar para carregar outro arquivo