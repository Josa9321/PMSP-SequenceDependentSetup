import numpy as np
import sqlite3 as sql
import json

from ast import literal_eval
from itertools import product

from .utils import SolutionPMSP

class InstancePMSP:
    def __init__(self, processing_time: np.ndarray, setup_time: np.ndarray):
        m, n = processing_time.shape
        assert setup_time.shape == (m, n, n), "The instance has different sizes"

        self.m = m
        self.n = n

        self.M = range(m)
        self.N0 = range(n)
        self.N = range(1, n)

        self.processing_time = processing_time
        self.setup_time = setup_time

        self.p = self._convert_dict(self.processing_time, [range(i) for i in self.processing_time.shape])
        self.s = self._convert_dict(self.setup_time, [range(i) for i in self.setup_time.shape])

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

    def save_json(self, address: str):
        instance_dict = {
                "m": self.m,
                "n": self.n,
                "processing_time": self.processing_time.tolist(),
                "setup_time": self.setup_time.tolist()
                }

        with open(address, 'w') as f:
            json.dump(instance_dict, f, indent=4)

    def _convert_dict(self, array, ranges):
        results = dict()
        for idxs in product(*ranges):
            results[*idxs] = array[*idxs]
        return results

def create_instance(m: int, n: int, interval_p: tuple = (1, 99), interval_s: tuple = (1, 99)):
    processing_time = np.random.randint(interval_p[0], interval_p[1], (m, n))
    setup_time = np.random.randint(interval_s[0], interval_s[1], (m, n, n))
    for i in range(m):
        processing_time[i, 0] = 0.0
        for j in range(n):
            setup_time[i, j, j] = 0.0
    return InstancePMSP(processing_time, setup_time)

def load_instance():
    pass

def load_json_file(address):
    with open(address, 'r') as f:
        instance_dict = json.load(f)
    return load_json(instance_dict)

def load_json(instance_dict):
    return InstancePMSP(
            np.array(instance_dict['processing_time']),
            np.array(instance_dict['setup_time'])
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
        PRIMARY KEY (m, n, o, idx)
        )
        """)

        self.cur.execute("""
        CREATE TABLE IF NOT EXISTS results (
        m INTEGER,
        n INTEGER,
        o INTEGER,
        idx INTEGER,
        obj FLOAT,
        time FLOAT,
        allocation TEXT,
        sequences TEXT,
        PRIMARY KEY (m, n, o, idx),
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
                        INSERT OR IGNORE INTO instances VALUES (?, ?, ?, ?, ?, ?)
                        """, (
                            instance.m,
                            instance.n,
                            group, idx,
                            json.dumps(instance.processing_time.tolist()),
                            json.dumps(instance.setup_time.tolist())
                            )
                         )
        self.conn.commit()

    def load_instance(self, m, n, group, idx):
        p_exec = self.cur.execute(
            'SELECT processing_time FROM instances WHERE (m = ? AND n = ? AND o = ? AND idx = ?)', 
            (m, n, group, idx)
        )
        processing_time = np.array(literal_eval(p_exec.fetchall()[0][0]))

        s_exec = self.cur.execute(
            'SELECT setup_time FROM instances WHERE (m = ? AND n = ? AND o = ? AND idx = ?)', 
            (m, n, group, idx)
        )
        setup_time = np.array(literal_eval(s_exec.fetchall()[0][0]))
        return InstancePMSP(processing_time, setup_time)

    def save_results(self, solution: SolutionPMSP, m, n, o, idx):
        solution_object = solution.set_object()
        self.cur.execute("""
        INSERT OR REPLACE INTO results VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
                         (
                          m,
                          n,
                          o,
                          idx,
                          solution.obj,
                          solution.time,
                          json.dumps(solution_object['allocations']),
                          json.dumps(solution_object['sequences_set'])
                          )
                         )
        self.conn.commit()
