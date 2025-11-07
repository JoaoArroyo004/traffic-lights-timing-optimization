#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import xml.etree.ElementTree as ET
import numpy as np
import traci
from get_tl_data import discover_from_xml


CFG = "run.sumocfg"
TRIPINFO_PATH = "tripinfos.xml"
E1_OUTPUT_PATH = "e1_output.xml"

# ---------------- Utilidades ----------------
def _mean(lst):
    return float(np.mean(lst)) if lst else 0.0


def parse_tripinfo(path):
    """
    Lê o arquivo tripinfo.xml e devolve médias de algumas métricas
    """
    root = ET.parse(path).getroot()
    # raiz pode ser <tripinfos> ou <log>; iteramos por tag 'tripinfo'
    duration, waiting, timeloss, rlength, speedFactor = [], [], [], [], []

    for ti in root.iter("tripinfo"):
        a = ti.attrib
        duration.append(float(a["duration"]))
        waiting.append(float(a.get("waitingTime", 0.0))) # Por que do 0.0?
        timeloss.append(float(a.get("timeLoss", 0.0)))
        rlength.append(float(a.get("routeLength", 0.0)))

        speedFactor.append(float(a.get("speedFactor", 0.0)))

    return {
        "nVehicles": len(duration),
        "duration": _mean(duration),
        "waitingTime": _mean(waiting),
        "timeLoss": _mean(timeloss),
        "routeLength": _mean(rlength),
        "speedFactor": _mean(speedFactor),
    }

def parse_e1(path):
    """
    Lê o arquivo e1_output.xml (detectores do tipo E1) e devolve médias de algumas métricas
    """
    root = ET.parse(path).getroot()
    nveh, flow, occ, spd, hspd, leng = [], [], [], [], [], []

    for it in root.iter("interval"):
        a = it.attrib
        nveh.append(float(a.get("nVehContrib", 0.0)))
        flow.append(float(a.get("flow", 0.0)))
        o = float(a.get("occupancy", 0.0))
        # alguns cenários gravam occupancy em %, normaliza para fração:
        if o > 1.5:
            o = o / 100.0
        occ.append(o)
        spd.append(float(a.get("speed", 0.0)))
        hspd.append(float(a.get("harmonicMeanSpeed", 0.0)))
        leng.append(float(a.get("length", 0.0)))

    return {
        "nVehContrib": _mean(nveh),
        "flow": _mean(flow),
        "occupancy": _mean(occ),
        "speed": _mean(spd),
        "harmonicMeanSpeed": _mean(hspd),
        "length": _mean(leng),
    }

# ---------------- Objetivos p/ NSGA-II ----------------
def get_objectives():
    """
    Responsável por retornar as médias calculadas a partir dos arquivos de saída da simulação
    """
    if os.path.exists(TRIPINFO_PATH):
        trip_path = TRIPINFO_PATH
    else:
        Exception("Tripinfo file not found.")
    
    trip = parse_tripinfo(trip_path)

    # Objetivos principais (podem / devem ser alterados)
    f1 = trip["duration"]
    f2 = trip["waitingTime"]

    # Outras opções de métricas talvez relevantes
    extras = {"tripinfo": trip}

    if os.path.exists(E1_OUTPUT_PATH):
        e1_path = E1_OUTPUT_PATH
    else:
        e1_path = None

    if e1_path:
        extras["e1"] = parse_e1(e1_path)

    return [f1, f2], extras

# ---------------- Execução da simulação ----------------
def run_simulation():
    """
    Inicia o SUMO sem GUI, roda até o fim e fecha.
    """
    cmd = ["sumo", "-c", CFG]
    print(">> starting SUMO:", " ".join(cmd))
    traci.start(cmd)

    while traci.simulation.getMinExpectedNumber() > 0:
        traci.simulationStep()

    traci.close()
    print(">> simulation finished.")

# ---------------- Main (exemplo) ----------------
if __name__ == "__main__":
    
    #Print 
    traffic_lights_config = discover_from_xml("joined_tls.add.xml")
    print("\n=== Configuração dos Semáforos ===")
    print(json.dumps(traffic_lights_config, indent=4, ensure_ascii=False))
    
    #Simulação
    run_simulation()

    #Obtém objetivos
    f, extras = get_objectives()
    f1, f2 = f
    print("\n=== Objetivos p/ NSGA-II ===")
    print(f"f1 = mean(duration)     = {f1:.4f} s")
    print(f"f2 = mean(waitingTime)  = {f2:.4f} s")

    #Print dos resultados
    t = extras["tripinfo"]
    print("\n--- Tripinfo (médias) ---")
    for k in ["nVehicles", "timeLoss", "routeLength", "speedFactor"]:
        print(f"{k}: {t[k]:.4f}" if isinstance(t[k], float) else f"{k}: {t[k]}")

    if "e1" in extras:
        print("\n--- E1_OUTPUT (detectors) ---")
        for k, v in extras["e1"].items():
            print(f"{k}: {v:.4f}")
    else:
        print("\n(E1 não encontrado; se quiser usar detectores, confirme o nome do arquivo e1_output.xml/detectors.xml.)")
