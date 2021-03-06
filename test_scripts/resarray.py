# -*- coding: utf-8 -*-

import yaml

from bag.core import BagProject
from bag.layout import RoutingGrid, TemplateDB

from abs_templates_ec.resistor.core import TerminationCore, Termination


def make_tdb(prj, target_lib, specs):
    grid_specs = specs['routing_grid']
    layers = grid_specs['layers']
    spaces = grid_specs['spaces']
    widths = grid_specs['widths']
    bot_dir = grid_specs['bot_dir']

    routing_grid = RoutingGrid(prj.tech_info, layers, spaces, widths, bot_dir)
    tdb = TemplateDB('template_libs.def', routing_grid, target_lib, use_cybagoa=True)
    return tdb


def generate_core(prj, specs):

    temp_db = make_tdb(prj, impl_lib, specs)
    params = specs['core_params']

    temp_list = [temp_db.new_template(params=params, temp_cls=TerminationCore, debug=False), ]
    temp_db.batch_layout(prj, temp_list, ['TERMCORE'])
    print('done')


def generate(prj, specs):

    temp_db = make_tdb(prj, impl_lib, specs)
    params = specs['params']

    temp_list = [temp_db.new_template(params=params, temp_cls=Termination, debug=False), ]
    temp_db.batch_layout(prj, temp_list, ['TERM'])
    print('done')

if __name__ == '__main__':

    impl_lib = 'AAAFOO'

    with open('test_specs/resarray.yaml', 'r') as f:
        block_specs = yaml.load(f)

    local_dict = locals()
    if 'bprj' not in local_dict:
        print('creating BAG project')
        bprj = BagProject()

        # generate_core(bprj, specs)
        generate(bprj, block_specs)
    else:
        print('loading BAG project')
