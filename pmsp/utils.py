import numpy as np
import pandas as pd

import json
import pyomo.environ as pyo

class SolutionPMSP:
    def __init__(self, model, results, time=0, test_sequences=True):
        self.method = model.method

        self.M = sorted(model.M)
        self.N0 = sorted(model.N0)
        self.N = sorted(model.N)
        self.m = len(self.M)
        self.n = len(self.N0)

        self.time = time
        self.obj = pyo.value(model.obj)

        self._get_allocations(model)
        self._get_sequences(model)
        self._get_completion_time(model)

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
        for i in self.M:
            sequence = []
            j, k = 0, -1
            while k < self.n:
                k += 1
                if pyo.value(model.x[i, j, k]) < 0.5:
                    continue

                sequence.append(j)

                if k == 0:
                    break

                j, k = k, -1

            self.sequences_set.append(sequence)

    def _get_completion_time(self, model):
        self.completion_time = np.zeros(self.n)
        machine_current_time = np.zeros(self.m)
        last_job = np.zeros(self.m, int)
        for (i, sequence) in enumerate(self.sequences_set):
            for k in sequence[1:]:
                if k == 0:
                    continue

                j = last_job[i]
                start_job_time = machine_current_time[i] + model.s[i, j, k]
                self.completion_time[k] = start_job_time + model.p[i, k]

                machine_current_time[i] += model.s[i, j, k] + model.p[i, k]
                last_job[i] = k

    def _test_allocations(self):
        for j in self.N:
            i = self.allocations[j]
            assert i >= 0, f"The Job {j} wasn't allocated"

    def _test_sequences(self):
        for i in self.M:
            for j in self.N:
                if self.allocations[j] != i:
                    continue
                assert j in self.sequences_set[i], f"Job {j}, allocated in ${i}, isn't in a valid sequence that starts at 0. Subtours are being generated"

    def set_object(self):
        solution_as_dict = {
                'method': self.method,
                'sequences_set': self.sequences_set,
                'allocations': self.allocations.tolist(),
                'completion_time': self.completion_time.tolist(),
                'obj': self.obj,
                'time': self.time
                }
        return solution_as_dict

    def save_json(self, address):
        solution_as_dict = self.set_object()
        with open(address, 'w') as f:
            json.dump(solution_as_dict, f, indent=4)

def create_solution_df(solution, instance):
    machine_current_time = np.zeros(instance.m)
    last_job = np.zeros(instance.m, int)
    data = []
    sequences_set = solution['sequences_set']
    completion_time = solution['completion_time']
    for (i, sequence) in enumerate(sequences_set):
        for k in sequence[1:]:
            if k == 0:
                continue

            j = last_job[i]

            data.append({
                        'Machine': i,
                        'Task': f's_{j}{k}',
                        'Start': completion_time[k] - instance.setup_time[i, j, k] - instance.processing_time[i, k],
                        'Finish': completion_time[k] - instance.processing_time[i, k],
                        'Type': 'Setup',
                        'Time': instance.setup_time[i, j, k]
                })

            data.append({
                        'Machine': i,
                        'Task': f'Job {k}',
                        'Start': completion_time[k] - instance.processing_time[i, k],
                        'Finish': completion_time[k],
                        'Type': 'Job',
                        'Time': instance.processing_time[i, k]
                    })
            last_job[i] = k

        k = sequences_set[i][-1]
        machine_current_time[i] = completion_time[k]
        data.append({
                    'Machine': i,
                    'Task': f's_{k}0',
                    'Start': machine_current_time[i],
                    'Finish': machine_current_time[i]+instance.setup_time[i, k, 0],
                    'Type': 'Setup',
                    'Time': instance.setup_time[i, k, 0]
            })

    return pd.DataFrame(data)

def create_machines_df(solution_df):
    data = []
    makespan = solution_df.Finish.max()
    for i in solution_df.Machine.unique():
        processing_time = solution_df[(solution_df.Type=='Job') & (solution_df.Machine == i)].Time.sum()
        setup_time = solution_df[(solution_df.Type=='Setup') & (solution_df.Machine == i)].Time.sum()
        idle_time = makespan - (processing_time + setup_time)
        data.append({
            'Machine': i, 
            'Processing Time': processing_time,
            'Setup Time': setup_time,
            'Idle Time': idle_time,
            '% Production': processing_time/makespan,
            '% Setup': setup_time/makespan,
            '% Idle': idle_time/makespan
        })
    
    return pd.DataFrame(data)









