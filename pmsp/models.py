from .instance import InstancePMSP
import pyomo.environ as pyo
import networkx as nx

from itertools import product
from pyomo.opt import SolverStatus, TerminationCondition
from pyomo.common.timing import tic, toc
from logging import error

from .utils import SolutionPMSP

def solve_instance(instance, method={'time': 120, 'gap': 1e-3, 'print_level': 0, 'model': 'cmax'}):
    solver = pyo.SolverFactory('highs')
    solver.options['time_limit'] = method['time']
    solver.options['mip_rel_gap'] = method['gap']
    solver.options['output_flag'] = method['print_level']

    tic(msg=None)
    if method['model'] == 'cmax':
        model = create_cmax_model(instance, method['model'])
        results = _solve_cmax_while_subtour_is_generated(solver, model)
    elif method['model'] == 'sum_e-t':
        model = create_et_model(instance, method['model'])
        results = solver.solve(model)
    else:
        error(f"{method['model']} not defined. Choose 'cmax' or 'sum_e-t'")

    solve_time = toc(msg=None)
    return SolutionPMSP(model, results, solve_time)

##############
# Cmax Model #
##############

def create_cmax_model(instance: InstancePMSP, method_name):
    m = pyo.ConcreteModel()
    m.method = method_name

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

    m.c2 = pyo.Constraint(m.N, rule=rule_c2)
    m.c3 = pyo.Constraint(m.M, m.N, rule=rule_c3)
    m.c4 = pyo.Constraint(m.M, m.N, rule=rule_c4)
    m.c5 = pyo.Constraint(m.M, rule=rule_c5)
    m.gsec = pyo.ConstraintList()
    m.c7 = pyo.Constraint(m.M, rule=rule_c7_cmax)

    for i in m.M:
        for j in m.N:
            m.x[i, j, j].fix(0)

    m.obj = pyo.Objective(
            expr=m.Cmax,
            sense=pyo.minimize
            )
    return m

def rule_c2(m, j):
    return sum(m.y[i, j] for i in m.M) == 1

def rule_c3(m, i, j):
    return sum(m.x[i, j, k] for k in m.N0 if j != k) == m.y[i, j]

def rule_c4(m, i, k):
    return sum(m.x[i, j, k] for j in m.N0 if j != k) == sum(m.x[i, k, j] for j in m.N0 if j != k)

def rule_c5(m, i):
    return sum(m.x[i, 0, k] for k in m.N0) == 1

def rule_c7_cmax(m, i):
    return sum(m.s[i, j, k] * m.x[i, j, k] for j in m.N0 for k in m.N0 if j != k
               ) + sum(m.p[i, j] * m.y[i, j] for j in m.N) <= m.Cmax

#####################################
# Sum earliness and tardiness model #
#####################################

def create_et_model(instance: InstancePMSP, method_name):
    m = pyo.ConcreteModel()
    m.method = method_name

    m.M = pyo.Set(initialize=instance.M)
    m.N0 = pyo.Set(initialize=instance.N0)
    m.N = pyo.Set(initialize=instance.N)

    m.p = pyo.Param(m.M, m.N0, initialize=instance.p, domain=pyo.NonNegativeReals)
    m.s = pyo.Param(m.M, m.N0, m.N0, initialize=instance.s, domain=pyo.NonNegativeReals)
    m.d = pyo.Param(m.N0, initialize=instance.d, domain=pyo.NonNegativeReals)

    m.Mi = pyo.Param(m.M, initialize=[instance.setup_time[i, :, :].max()*instance.n-1 for i in m.M])

    m.x = pyo.Var(m.M, m.N0, m.N0, domain=pyo.Binary)
    m.y = pyo.Var(m.M, m.N, domain=pyo.Binary)

    m.C = pyo.Var(m.N0, domain=pyo.NonNegativeReals)
    m.E = pyo.Var(m.N, domain=pyo.NonNegativeReals)
    m.T = pyo.Var(m.N, domain=pyo.NonNegativeReals)

    m.c2 = pyo.Constraint(m.N, rule=rule_c2)
    m.c3 = pyo.Constraint(m.M, m.N, rule=rule_c3)
    m.c4 = pyo.Constraint(m.M, m.N, rule=rule_c4)
    m.c5 = pyo.Constraint(m.M, rule=rule_c5)
    m.c6 = pyo.Constraint(m.M, m.N0, m.N, rule=rule_c6_et)
    m.c7 = pyo.Constraint(m.N, rule=rule_c7_et)

    for i in m.M:
        for j in m.N:
            m.x[i, j, j].fix(0)

    m.obj = pyo.Objective(
            expr=sum(m.E[j] + m.T[j] for j in m.N),
            sense=pyo.minimize,
            )

    return m

def rule_c6_et(m, i, j, k):
    if j == k:
        return pyo.Constraint.Skip
    else:
        M_ijk = sum(m.p[i, l] for l in m.N) + m.s[i, j, k] + m.Mi[i]
        return m.C[k] >= m.C[j] + m.s[i, j, k] + m.p[i, k] - M_ijk * (1 - m.x[i, j, k])

def rule_c7_et(m, j):
    return m.C[j] == m.d[j] + m.T[j] - m.E[j]

##########################
# GSEC Related Functions #
##########################

def _solve_cmax_while_subtour_is_generated(solver, model):
    results = solver.solve(model)
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
                    model.gsec.add(expr=sum(model.x[i, j, k] for j in S for k in model.N0 if not(k in S)) >= model.y[i, h])

        if len(sets) > 0:
            results = solver.solve(model)
            do_next_iter = (results.solver.status == SolverStatus.ok) and (
                    results.solver.termination_condition != TerminationCondition.infeasibleOrUnbounded)
    return results


def _get_all_subtours_sets(subtours_sets, model, i):
    g = _generate_graph(model, i)
    source = 0
    for target in range(1, model.n):
        if pyo.value(model.y[i, target]) < 0.5:
            continue

        cut_value, partition = nx.minimum_cut(g, source, target)
        if cut_value > 1e-2:
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








