import itertools

from .models import solve_instance
from .instance import InstanceDB


def solve_instances_set(method, address, jobs_set: list[int], machines_set: list[int], group: int=0, num_instances: int=10, solve_again: bool=False):
    assert len(jobs_set) == len(machines_set), 'machines_set and jobs_set should have the same number of elements'
    db = InstanceDB(address)
    print(f"Solving instances from {address}")
    print(f'{'m':>4}{'n':>4}{'o':>4}{'idx':>4} {'time':>10} {'obj':>10}')
    print('-'*38)
    for (k, idx) in itertools.product(range(len(jobs_set)), range(num_instances)):
        m = machines_set[k]
        n = jobs_set[k]
        instance = db.load_instance(m, n, group, idx)

        solution = solve_instance(instance, method)
        print(f'{m:>4}{n:>4}{group:>4}{idx:>4} {solution.time:>10.4f} {solution.obj:>10.4f}')

        solution_object = solution.set_object()
        db.save_results(solution_object, m, n, group, idx)

    print('-'*38)
    return print("Instances solved")

