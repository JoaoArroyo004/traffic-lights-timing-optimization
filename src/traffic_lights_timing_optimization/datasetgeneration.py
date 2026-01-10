from pymoo.core.callback import Callback
import pandas as pd

class EvaluationLogger(Callback):
    def __init__(self, record_X=True):
        super().__init__()
        self.rows = []
        self.record_X = record_X

    def notify(self, algorithm):
        # geração atual
        gen = int(algorithm.n_gen)

        # número total de avaliações até agora
        n_eval = int(algorithm.evaluator.n_eval)

        # população atual (já avaliada)
        pop = algorithm.pop

        X = pop.get("X")  # shape: (pop_size, n_var)
        F = pop.get("F")  # shape: (pop_size, n_obj)

        pop_size = F.shape[0]
        n_obj = F.shape[1]

        # Monta linhas: uma por indivíduo na população
        for i in range(pop_size):
            row = {
                "gen": gen,
                "n_eval": n_eval,
                "ind": i,
            }

            # objetivos
            for j in range(n_obj):
                row[f"f{j+1}"] = float(F[i, j])

            # variáveis de decisão (opcional; pode deixar grande o CSV)
            if self.record_X:
                for k in range(X.shape[1]):
                    row[f"x{k+1}"] = float(X[i, k])

            self.rows.append(row)
        df = pd.DataFrame(self.rows)
        df.to_csv("gen_log.csv", index=False)