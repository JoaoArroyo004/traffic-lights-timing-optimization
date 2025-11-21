import time
from pymoo.core.callback import Callback

class LogGenerationCallback(Callback):
    def __init__(self):
        super().__init__()
        self.start_time = time.time()

    def notify(self, algorithm):
        gen = algorithm.n_gen
        elapsed = time.time() - self.start_time
        print(f"[GEN {gen}] elapsed: {elapsed:.2f}s")
        with open("gen_log.txt", "a") as log:
            log.write(f"{gen}, {elapsed:.2f}\n")
