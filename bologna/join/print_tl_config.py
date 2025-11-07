# print_tls.py
# -*- coding: utf-8 -*-

import xml.etree.ElementTree as ET

def _safe_float(x, default=0.0):
    try:
        return float(x)
    except Exception:
        return default

def _count_states(state: str):
    return {
        "G": state.count("G"),
        "g": state.count("g"),
        "y": state.count("y"),
        "r": state.count("r"),
    }

def _cycle_time(phases):
    return sum(_safe_float(p.get("duration", "0")) for p in phases)

def print_tls_from_file(xml_path: str, show_phases: bool = True, truncate_state: int = 60):
    """
    Lê um arquivo *.add.xml com <tlLogic> e imprime um resumo legível.
    - show_phases: imprime tabela por fase com contagem de G/g/y/r
    - truncate_state: corta a string 'state' na impressão para caber no terminal
    """
    tree = ET.parse(xml_path)
    root = tree.getroot()

    # alguns arquivos usam <add> como raiz, outros <additional>
    tls_blocks = list(root.iter("tlLogic"))
    if not tls_blocks:
        print(f"Nenhum <tlLogic> encontrado em: {xml_path}")
        return

    print(f"\n=== Programas semafóricos encontrados ({len(tls_blocks)}) em: {xml_path} ===\n")
    for idx, tl in enumerate(tls_blocks, 1):
        tl_id     = tl.get("id", "?")
        tl_type   = tl.get("type", "?")
        program   = tl.get("programID", "?")
        offset    = _safe_float(tl.get("offset", "0"))

        phases = list(tl.iter("phase"))
        n_phases = len(phases)
        n_moves  = len(phases[0].get("state", "")) if n_phases > 0 else 0
        cycle    = _cycle_time(phases)

        print(f"[{idx}] TLS={tl_id} | program={program} | type={tl_type} | offset={int(offset)}s")
        print(f"    fases={n_phases} | movimentos={n_moves} | ciclo≈{cycle:.1f}s")

        if show_phases and n_phases > 0:
            print("    Fases:")
            print("    idx |  dur  | min | max |  #G  #g  #y  #r | state")
            print("    ----+-------+-----+-----+------------------+---------------------------------------------")
            for i, p in enumerate(phases):
                dur  = _safe_float(p.get("duration", "0"))
                minD = p.get("minDur"); minD = f"{_safe_float(minD):.0f}" if minD is not None else "-"
                maxD = p.get("maxDur"); maxD = f"{_safe_float(maxD):.0f}" if maxD is not None else "-"
                state = p.get("state", "")
                counts = _count_states(state)
                st_view = state if truncate_state is None else (state[:truncate_state] + ("…" if len(state) > truncate_state else ""))
                print(f"    {i:>3} | {dur:>5.0f}s | {minD:>3} | {maxD:>3} |"
                      f"  {counts['G']:>2}  {counts['g']:>2}  {counts['y']:>2}  {counts['r']:>2} | {st_view}")
        print()

if __name__ == "__main__":
    # ajuste o caminho abaixo para o arquivo que você enviou
    print_tls_from_file("joined_tls.add.xml", show_phases=True, truncate_state=72)
