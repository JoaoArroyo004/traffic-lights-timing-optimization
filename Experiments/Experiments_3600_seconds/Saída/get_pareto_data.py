import glob
import matplotlib.pyplot as plt

def extrair_resultados_de_arquivo(arquivo):
    """
    Lê um único arquivo e extrai as tuplas (obj1, obj3).
    """
    resultados = []

    with open(arquivo, "r", encoding="utf-8") as f:
        for linha in f:
            linha = linha.strip()

            if linha.startswith("RESULTS"):
                partes = linha.split(',')
                obj1 = float(partes[1])
                obj3 = float(partes[3])
                resultados.append((obj1, obj3))

    return resultados


def extrair_de_varios(arquivos):
    """
    Recebe uma lista de arquivos e junta todos os resultados.
    Retorna: lista [(obj1, obj3), ...]
    """
    todos = []

    for arquivo in arquivos:
        print(f"Lendo: {arquivo}")
        res = extrair_resultados_de_arquivo(arquivo)
        todos.extend(res)

    return todos


def domina(a, b):
    """
    Teste de dominância de Pareto (minimização).
    Usa apenas obj1 e obj3.
    """
    return (a[0] <= b[0] and a[1] <= b[1]) and (a[0] < b[0] or a[1] < b[1])


def encontrar_nao_dominadas(resultados):
    """
    Retorna apenas as soluções NÃO dominadas.
    """
    n = len(resultados)
    dominadas = set()

    for i in range(n):
        for j in range(n):
            if i != j and domina(resultados[j], resultados[i]):
                dominadas.add(i)
                break

    return [r for idx, r in enumerate(resultados) if idx not in dominadas]


# --------------------------
# USO
# --------------------------

# Busca recursiva em todas as subpastas por arquivos .csv
arquivos = glob.glob("**/*.csv", recursive=True)

if not arquivos:
    print("Nenhum arquivo .csv encontrado.")
else:
    resultados = extrair_de_varios(arquivos)

    if not resultados:
        print("Nenhuma linha 'RESULTS' encontrada nos arquivos.")
    else:
        nao_dominadas = encontrar_nao_dominadas(resultados)

        # Remover duplicatas preservando a ordem
        nao_dominadas_unicas = []
        for r in nao_dominadas:
            if r not in nao_dominadas_unicas:
                nao_dominadas_unicas.append(r)

        print("\nSoluções NÃO dominadas encontradas:")
        for r in nao_dominadas_unicas:
            print(r)

        # Preparar dados para o gráfico
        y = [r[0] for r in nao_dominadas_unicas]
        x = [r[1] for r in nao_dominadas_unicas]

        # Gerar gráfico
        plt.figure(figsize=(6, 5))
        plt.scatter(x, y, alpha=0.7, color='blue')
        plt.scatter(19.33, 28.38, alpha=0.7, color='red')
        plt.xlabel("Tamanho máx de fila")      
        plt.ylabel("Tempo médio de espera")   
        plt.title("Otimização semafórica - Fronteira de Pareto (NSGA-II)")
        plt.grid(True)
        plt.tight_layout()
        plt.savefig("pareto_front10.png", dpi=300)
        plt.close()

        print(f"\nTotal de soluções não dominadas: {len(nao_dominadas_unicas)}")
        print('Gráfico salvo em "pareto_front.png".')
