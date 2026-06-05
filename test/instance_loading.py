import numpy as np

from ..pmsp import *


instance_1 = create_instance(4, 10)
instance_1.save_instance_txt('./instance_1.txt')
instance_1.save_json('./instance_1.json')
instance_2 = load_json('./instance_1.json')

assert np.isclose(instance_1.processing_time, instance_2.processing_time).all()
assert np.isclose(instance_1.setup_time, instance_2.setup_time).all()
