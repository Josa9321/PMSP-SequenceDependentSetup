import numpy as np
import json
import pyomo.environ as pyo

class SolutionPMSP:
    def __init__(self, model, results, time=0, test_sequences=True):
        self.M = sorted(model.M)
        self.N0 = sorted(model.N0)
        self.N = sorted(model.N)
        self.m = len(self.M)
        self.n = len(self.N0)

        self.time = time

        self._get_allocations(model)
        self._get_sequences(model)

        if test_sequences:
            self._test_allocations()
            self._test_sequences()

    def _get_allocations(self, model):
        self.allocations = np.array([-1 for _ in self.N0])
        for j in self.N:
            for i in self.M:
                if pyo.value(model.y[i, j]) > 0.5:
                    self.allocations[j] = i
                    break

    def _get_sequences(self, model):
        self.sequences_set = []
        print_matrix(model.x, model.N0, 0)
        for i in self.M:
            sequence = []
            j, k = 0, -1
            while k < self.n:
                k += 1
                print(k, k < self.n)
                if pyo.value(model.x[i, j, k]) < 0.5:
                    print("???")
                    continue

                sequence.append(j)
                j, k = k, -1

            self.sequences_set.append(sequence)

    def _test_allocations(self):
        for (j, i) in enumerate(self.allocations):
            assert i >= 0, f"The Job {j} wasn't allocated"

    def _test_sequences(self):
        for i in self.M:
            for j in self.N:
                if self.allocations[j] != i:
                    continue
                assert j in self.sequences_set[i], f"Job {j}, allocated in ${i}, isn't in a valid sequence that starts at 0. Subtours are being generated"

    def save_json(self, address):
        with open(address, 'w') as f:
            solution_as_dict = {
                    'sequences_set': self.sequences_set,
                    'allocations': self.allocations
                    }
            json.dump(solution_as_dict, f, indent=4)

def print_matrix(x, N0, i):
    for j in N0:
        for k in N0:
            print(f'{pyo.value(x[i, j, k]):>4f}', end=' ')
        print()
