import os
import json
import xml.etree.ElementTree as ET

def _to_float(x, default=None):
    try:
        return float(x)
    except Exception:
        return default

def _count_greens(state: str):
    """Conta letras por tipo e retorna flags úteis."""
    if not state:
        return {"G":0, "g":0, "y":0, "r":0, "has_green":False}
    cnt = {
        "G": state.count("G"),
        "g": state.count("g"),
        "y": state.count("y"),
        "r": state.count("r"),
    }
    cnt["has_green"] = (cnt["G"] + cnt["g"]) > 0
    return cnt

# -----------------------------------------------------------------------------
# 1) Descoberta a partir de arquivo XML com <tlLogic>
# -----------------------------------------------------------------------------
def discover_from_xml(tl_add_xml_path: str):
    """
    Lê um arquivo *.add.xml contendo blocos <tlLogic> e monta a 'spec'.

    Retorna:
      spec: dict
        {
          "tls_ids": [...],
          "tls": {
            "<TLS_ID>": {
              "type": "static" | "actuated" | ...,
              "programID": "utopia",
              "offset": 0.0,
              "n_movements": int,         # len(state)
              "phases": [
                 {"duration":float, "min":float|None, "max":float|None,
                  "state":str, "greens": {"G":..,"g":..,"y":..,"r":..,"has_green":bool}}
                 ...
              ],
              "green_phase_indices": [idx,...],
              "cycle": float
            },
            ...
          }
        }
    """
    if not os.path.exists(tl_add_xml_path):
        raise FileNotFoundError(f"Arquivo não encontrado: {tl_add_xml_path}")

    root = ET.parse(tl_add_xml_path).getroot()
    tls_blocks = list(root.iter("tlLogic"))
    if not tls_blocks:
        raise ValueError(f"Nenhum <tlLogic> encontrado em {tl_add_xml_path}")

    spec = {"tls_ids": [], "tls": {}}

    for tl in tls_blocks:
        tls_id   = tl.get("id")
        tl_type  = tl.get("type", "static")
        prog_id  = tl.get("programID", "")
        offset   = _to_float(tl.get("offset", "0"), default=0.0)

        phases = []
        for p in tl.iter("phase"):
            dur  = _to_float(p.get("duration", "0"), default=0.0)
            mind = _to_float(p.get("minDur"))    # pode ser None
            maxd = _to_float(p.get("maxDur"))
            state = p.get("state", "")
            ginfo = _count_greens(state)
            phases.append({
                "duration": dur,
                "min": mind,
                "max": maxd,
                "state": state,
                "greens": ginfo
            })

        n_phases = len(phases)
        n_moves  = len(phases[0]["state"]) if n_phases > 0 else 0
        cycle    = sum(p["duration"] for p in phases)
        green_idxs = [i for i,p in enumerate(phases) if p["greens"]["has_green"]]

        spec["tls_ids"].append(tls_id)
        spec["tls"][tls_id] = {
            "type": tl_type,
            "programID": prog_id,
            "offset": offset,
            "n_movements": n_moves,
            "phases": phases,
            "green_phase_indices": green_idxs,
            "cycle": cycle
        }

    return spec


if __name__ == "__main__":
    traffic_data = discover_from_xml("joined_tls.add.xml")
    print(json.dumps(traffic_data, indent=4, ensure_ascii=False))