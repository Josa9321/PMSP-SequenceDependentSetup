from .instance import InstancePMSP
import pyomo.environ as pyo
import networkx as nx

from itertools import product
from pyomo.opt import SolverStatus, TerminationCondition
from pyomo.common.timing import tic, toc

from .utils import SolutionPMSP

def solve_instance(instance, method):
    model = create_cmax_model(instance)

    solver = pyo.SolverFactory('highs')
    solver.options['time_limit'] = method['time']
    solver.options['mip_rel_gap'] = method['gap']
    solver.options['output_flag'] = method['print_level']

    tic(msg=None)
    results = _solve_while_subtour_is_generated(solver, model)
    solve_time = toc(msg=None)
    if (results.solver.status == SolverStatus.ok) and (
        results.solver.termination_condition == TerminationCondition.optimal):
        return SolutionPMSP(model, solve_time, results, test_sequences=False)
    return None

def _solve_while_subtour_is_generated(solver, model):
    results = solver.solve(model)
    return results
    do_next_iter = (results.solver.status == SolverStatus.ok) and (
            results.solver.termination_condition != TerminationCondition.infeasibleOrUnbounded)
    while do_next_iter:
        do_next_iter = False

        sets = []
        for i in model.M:
            _get_all_subtours_sets(sets, model, i)

        for S in sets:
            for i in model.M:
                for h in S:
                    model.c6.add(expr=sum(model.x[i, j, k] for j in S for k in model.N0 if not(k in S)) >= model.y[i, h])

        if len(sets) > 0:
            results = solver.solve(model)
            do_next_iter = (results.solver.status == SolverStatus.ok) and (
                    results.solver.termination_condition != TerminationCondition.infeasibleOrUnbounded)

def create_cmax_model(instance: InstancePMSP):
    m = pyo.ConcreteModel()

    m.M = pyo.Set(initialize=instance.M)
    m.N0 = pyo.Set(initialize=instance.N0)
    m.N = pyo.Set(initialize=instance.N)

    m.m = instance.m
    m.n = instance.n

    m.p = pyo.Param(m.M, m.N0, initialize=instance.p, domain=pyo.NonNegativeReals)
    m.s = pyo.Param(m.M, m.N0, m.N0, initialize=instance.s, domain=pyo.NonNegativeReals)

    m.x = pyo.Var(m.M, m.N0, m.N0, domain=pyo.Binary)
    m.y = pyo.Var(m.M, m.N, domain=pyo.Binary)
    m.Cmax = pyo.Var(domain=pyo.NonNegativeReals)

    m.c2 = pyo.Constraint(m.N, rule=c2_cmax)
    m.c3 = pyo.Constraint(m.M, m.N, rule=c3_cmax)
    m.c4 = pyo.Constraint(m.M, m.N, rule=c4_cmax)
    m.c5 = pyo.Constraint(m.M, rule=c5_cmax)
    m.c6 = pyo.ConstraintList()
    m.c7 = pyo.Constraint(m.M, rule=c7_cmax)

    m.obj = pyo.Objective(
            expr=m.Cmax,
            sense=pyo.minimize
            )
    return m

def c2_cmax(m, j):
    return sum(m.y[i, j] for i in m.M) == 1

def c3_cmax(m, i, j):
    return sum(m.x[i, j, k] for k in m.N0 if j != k) == m.y[i, j]

def c4_cmax(m, i, k):
    return sum(m.x[i, j, k] for j in m.N0 if j != k) == sum(m.x[i, k, j] for j in m.N0 if j != k)

def c5_cmax(m, i):
    return sum(m.x[i, 0, k] for k in m.N0) == 1

def c6_cmax(m, h, S, i):
    return sum(m.x[i, j, k] for j in S for k in m.N0 if not(k in S)) >= m.y[i, h]

def c7_cmax(m, i):
    return sum(m.s[i, j, k] * m.x[i, j, k] for j in m.N0 for k in m.N0 if j != k
               ) + sum(m.p[i, j] * m.y[i, j] for j in m.N) <= m.Cmax

def _get_all_subtours_sets(subtours_sets, model, i):
    g = _generate_graph(model, i)
    source = 0
    for target in range(1, model.n):
        if pyo.value(model.y[i, target]) < 0.5:
            continue

        cut_value, partition = nx.minimum_cut(g, source, target)
        if cut_value < 1e-2:
            continue

        partition = list(partition[1])
        partition.sort()
        if not (partition in subtours_sets):
            subtours_sets.append(partition)

    return subtours_sets

def _generate_graph(model, i):
    g = nx.DiGraph()
    for (j, k) in product(model.N0, model.N0):
        if j == k:
            continue
        g.add_edge(j, k, capacity=pyo.value(model.x[i, j, k]))
    return g








