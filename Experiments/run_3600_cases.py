import csv
import ast

from traffic_lights_timing_optimization.evaluate_policy import evaluate_policy
from traffic_lights_timing_optimization.fetch_graph_information import fetch_graph_information


INPUT_CSV = "entrada.csv"   # <-- Seu CSV de entrada
OUTPUT_CSV = "saida.csv"    # <-- CSV gerado com resultados atualizados


def parse_list_str(value: str):
    """
    Converte "['69.52', '52.61', '50.79']" → [69.52, 52.61, 50.79]
    """
    value = value.strip()
    lista = ast.literal_eval(value)
    return [float(x) for x in lista]


def main():
    SUMO_CFG_PATH = "./santo-andre-extendido/demand.sumocfg"
    cycle_time = 60
    semaphores_information = fetch_graph_information(SUMO_CFG_PATH).copy()

    # Lê todo o CSV
    with open(INPUT_CSV, newline="", encoding="utf-8") as f:
        reader = list(csv.reader(f))

    i = 0
    while i < len(reader):
        row = reader[i]

        # Procura os blocos OFFSETS...
        if row and row[0].strip().upper().startswith("OFFSETS"):
            offsets_row = row
            greens_row = reader[i + 1]
            last_greens_row = reader[i + 2]
            results_row = reader[i + 3]

            offsets = parse_list_str(offsets_row[1])
            green_times = parse_list_str(greens_row[1])
            last_greens = parse_list_str(last_greens_row[1])

            # ------------------------------
            # PRINTA INFORMAÇÕES DA ITERAÇÃO
            # ------------------------------
            print("\n======================================")
            print(" Nova simulação detectada!")
            print("--------------------------------------")
            print(f"Offsets:      {offsets}")
            print(f"Green times:  {green_times}")
            print(f"Last greens:  {last_greens}")
            print("Executando evaluate_policy...")
            print("======================================\n")

            # Executa a simulação
            result = evaluate_policy(
                offsets=offsets,
                green_times=green_times,
                times_for_last_green=last_greens,
                semaphores_original_information=semaphores_information,
                cycle_time=cycle_time,
                gui=False,
                verbose=False,
                path=SUMO_CFG_PATH,
            )

            avg_wait = result["avg_waiting_time"]
            avg_queue = result["avg_queue_system"]
            max_queue = result["max_queue"]

            # ------------------------------
            # PRINTA RESULTADO DA ITERAÇÃO
            # ------------------------------
            print(" Resultado da simulação:")
            print(f"   Avg Waiting Time: {avg_wait:.4f}")
            print(f"   Avg Queue Size:   {avg_queue:.4f}")
            print(f"   Max Queue Size:   {max_queue:.4f}")
            print("======================================\n")

            # Atualiza linha RESULTS no CSV
            results_row[0] = "RESULTS:"
            results_row[1] = f"{avg_wait:.2f}"
            results_row[2] = f"{avg_queue:.2f}"
            results_row[3] = f"{max_queue:.2f}"

            reader[i + 3] = results_row

            i += 4
        else:
            i += 1

    # Salva novo CSV
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(reader)

    print("\n🎉 Processamento concluído!")
    print(f"Novo arquivo gerado: {OUTPUT_CSV}\n")


if __name__ == "__main__":
    main()
