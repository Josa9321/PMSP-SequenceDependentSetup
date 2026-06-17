import numpy as np
import sqlite3 as sql
import json

from ast import literal_eval
from itertools import product
from math import trunc

from .utils import SolutionPMSP

class InstancePMSP:
    def __init__(self, processing_time: np.ndarray, setup_time: np.ndarray, due_date: np.ndarray):
        m, n = processing_time.shape
        assert setup_time.shape == (m, n, n), "The instance has different sizes"
        assert due_date.shape == (n,), '''The instance's due_date has different sizes than other arrays'''

        self.m = m
        self.n = n

        self.M = range(m)
        self.N0 = range(n)
        self.N = range(1, n)

        self.processing_time = processing_time
        self.setup_time = setup_time
        self.due_date = due_date

        self.p = self._convert_dict(self.processing_time)
        self.s = self._convert_dict(self.setup_time)
        self.d = self._convert_dict(self.due_date)

    def save_instance_txt(self, address: str):
        with open(address, 'w') as f:
            f.write(f'{self.processing_time.shape}\n')
            f.write('processing_time\n')
            for i in self.M:
                for j in self.N0:
                    f.write(f"{self.processing_time[i, j]:>4}")
                f.write(f"\n")

            f.write('setup_time\n')
            for i in self.M:
                f.write(f'machine_{i}\n')
                for j in self.N0:
                    for k in self.N0:
                        f.write(f"{self.setup_time[i, j, k]:>4}")
                    f.write(f"\n")

            f.write('due_date\n')
            for i in self.N0:
                f.write(f"{self.due_date[i]:>4}\n")

    def save_json(self, address: str):
        instance_dict = {
                "m": self.m,
                "n": self.n,
                "processing_time": self.processing_time.tolist(),
                "setup_time": self.setup_time.tolist(),
                'due_date': self.due_date.tolist()
                }

        with open(address, 'w') as f:
            json.dump(instance_dict, f, indent=4)

    def _convert_dict(self, array: np.ndarray):
        ranges = [range(i) for i in array.shape]
        results = dict()
        for idxs in product(*ranges):
            results[*idxs] = array[*idxs]
        return results

def create_instance(m: int, n: int, interval_p: tuple = (1, 99), interval_s: tuple = (1, 99), value_d: float = 1.5):
    processing_time = np.random.randint(interval_p[0], interval_p[1], (m, n))
    setup_time = np.random.randint(interval_s[0], interval_s[1], (m, n, n))
    for i in range(m):
        processing_time[i, 0] = 0.0
        for j in range(n):
            setup_time[i, j, j] = 0.0

    due_date = np.zeros(n, int)
    min_time = processing_time.max(0) + setup_time[:, 0, :].max(0)
    max_time = trunc((processing_time.mean() + setup_time.mean()) * n * value_d / m)
    for j in range(1, n):
        due_date[j] = np.random.randint(min_time[j], max_time)

    return InstancePMSP(processing_time, setup_time, due_date)

def load_instance():
    pass

def load_json_file(address):
    with open(address, 'r') as f:
        instance_dict = json.load(f)
    return load_json(instance_dict)

def load_json(instance_dict):
    return InstancePMSP(
            np.array(instance_dict['processing_time']),
            np.array(instance_dict['setup_time']),
            np.array(instance_dict['due_date']),
            )


#= SQL =#

class InstanceDB:
    def __init__(self, address):
        self.conn = sql.connect(address)
        self.cur = self.conn.cursor()
        self.mk_tables_if_not_exists()

    def mk_tables_if_not_exists(self):
        self.cur.execute("""
        PRAGMA foreign_keys=ON
        """)

        self.cur.execute("""
        CREATE TABLE IF NOT EXISTS instances(
        m INTEGER,
        n INTEGER,
        o INTEGER,
        idx INTEGER,
        processing_time TEXT,
        setup_time TEXT,
        due_date TEXT,
        PRIMARY KEY (m, n, o, idx)
        )
        """)

        self.cur.execute("""
        CREATE TABLE IF NOT EXISTS results (
        method TEXT,
        m INTEGER,
        n INTEGER,
        o INTEGER,
        idx INTEGER,
        obj FLOAT,
        time FLOAT,
        allocation TEXT,
        sequences TEXT,
        completion_time TEXT,
        PRIMARY KEY (method, m, n, o, idx),
        FOREIGN KEY (m, n, o, idx) REFERENCES instances (m, n, o, idx)
        )
        """)
        self.conn.commit()

    def create_instances(self, m, n, num_instances, group=0, interval_p: tuple = (1, 99), interval_s: tuple = (1, 99)):
        for idx in range(num_instances):
            instance = create_instance(m, n, interval_p, interval_s)
            self._save_instances(instance, group, idx)

    def _save_instances(self, instance: InstancePMSP, group:int, idx: int):
        self.cur.execute("""
                        INSERT OR IGNORE INTO instances VALUES (?, ?, ?, ?, ?, ?, ?)
                        """, (
                            instance.m,
                            instance.n,
                            group, idx,
                            json.dumps(instance.processing_time.tolist()),
                            json.dumps(instance.setup_time.tolist()),
                            json.dumps(instance.due_date.tolist())
                            )
                         )
        self.conn.commit()

    def load_instance(self, m, n, group, idx):
        processing_time = self._load_array(m, n, group, idx, "processing_time")
        setup_time = self._load_array(m, n, group, idx, "setup_time")
        due_date = self._load_array(m, n, group, idx, "due_date")
        return InstancePMSP(processing_time, setup_time, due_date)

    def _load_array(self, m, n, group, idx, array_text):
        query = f'SELECT {array_text} FROM instances WHERE (m = ? AND n = ? AND o = ? AND idx = ?)'
        execution = self.cur.execute(
            query,
            (m, n, group, idx)
        )
        return np.array(literal_eval(execution.fetchall()[0][0]))


    def save_results(self, solution, m, n, o, idx):
        self.cur.execute("""
        INSERT OR REPLACE INTO results VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
                         (
                          solution['method'],
                          m,
                          n,
                          o,
                          idx,
                          solution['obj'],
                          solution['time'],
                          json.dumps(solution['allocations']),
                          json.dumps(solution['sequences_set']),
                          json.dumps(solution['completion_time'])
                          )
                         )
        self.conn.commit()
