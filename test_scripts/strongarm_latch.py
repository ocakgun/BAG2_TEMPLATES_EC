# -*- coding: utf-8 -*-
########################################################################################################################
#
# Copyright (c) 2014, Regents of the University of California
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without modification, are permitted provided that the
# following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice, this list of conditions and the following
#   disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the
#    following disclaimer in the documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES,
# INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
# WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
########################################################################################################################


"""This script tests that AnalogBase draws rows of transistors properly."""


from typing import Dict, Any, Set

import yaml

from bag import BagProject
from bag.layout.routing import RoutingGrid, TrackID
from bag.layout.template import TemplateDB

from abs_templates_ec.laygo.core import LaygoBase


class StrongArmLatch(LaygoBase):
    """A single diff amp.

    Parameters
    ----------
    temp_db : TemplateDB
            the template database.
    lib_name : str
        the layout library name.
    params : Dict[str, Any]
        the parameter values.
    used_names : Set[str]
        a set of already used cell names.
    **kwargs
        dictionary of optional parameters.  See documentation of
        :class:`bag.layout.template.TemplateBase` for details.
    """

    def __init__(self, temp_db, lib_name, params, used_names, **kwargs):
        # type: (TemplateDB, str, Dict[str, Any], Set[str], **Any) -> None
        super(StrongArmLatch, self).__init__(temp_db, lib_name, params, used_names, **kwargs)

    @classmethod
    def get_params_info(cls):
        """Returns a dictionary containing parameter descriptions.

        Override this method to return a dictionary from parameter names to descriptions.

        Returns
        -------
        param_info : dict[str, str]
            dictionary from parameter name to description.
        """
        return dict(
            config='laygo configuration dictionary.',
            threshold='transistor threshold flavor.',
            draw_boundaries='True to draw boundaries.',
            num_nblk='number of nmos blocks, single-ended.',
            num_pblk='number of pmos blocks, single-ended.',
            num_dblk='number of dummy blocks on both sides.',
            show_pins='True to draw pin geometries.',
        )

    def draw_layout(self):
        """Draw the layout of a dynamic latch chain.
        """
        threshold = self.params['threshold']
        draw_boundaries = self.params['draw_boundaries']
        num_pblk = self.params['num_pblk']
        num_nblk = self.params['num_nblk']
        num_dblk = self.params['num_dblk']
        show_pins = self.params['show_pins']

        row_list = ['ptap', 'nch', 'nch', 'nch', 'pch', 'ntap']
        orient_list = ['R0', 'R0', 'MX', 'MX', 'R0', 'MX']
        thres_list = [threshold] * 6
        num_g_tracks = [0, 1, 2, 2, 1, 0]
        num_gb_tracks = [0, 1, 1, 1, 2, 0]
        num_ds_tracks = [2, 0, 1, 1, 1, 2]
        if draw_boundaries:
            end_mode = 15
        else:
            end_mode = 0

        # specify row types
        self.set_row_types(row_list, orient_list, thres_list, draw_boundaries, end_mode,
                           num_g_tracks, num_gb_tracks, num_ds_tracks, guard_ring_nf=0)

        # determine total number of blocks
        tot_pblk = num_pblk + 2
        tot_nblk = num_nblk
        tot_blk_max = max(tot_pblk, tot_nblk)
        tot_blk = 1 + 2 * (tot_blk_max + num_dblk)
        colp = num_dblk + tot_blk_max - tot_pblk
        coln = num_dblk + tot_blk_max - tot_nblk

        # add blocks
        pdum_list, ndum_list = [], []
        blk_type = 'fg2d'

        # nwell tap
        cur_col, row_idx = 0, 5
        nw_tap = self.add_laygo_primitive('sub', loc=(cur_col, row_idx), nx=tot_blk, spx=1)

        # pmos inverter row
        cur_col, row_idx = 0, 4
        pdum_list.append((self.add_laygo_primitive(blk_type, loc=(cur_col, row_idx), nx=colp, spx=1), 0))
        cur_col += colp
        rst_midp = self.add_laygo_primitive(blk_type, loc=(cur_col, row_idx))
        cur_col += 1
        rst_outp = self.add_laygo_primitive(blk_type, loc=(cur_col, row_idx))
        cur_col += 1
        invp_outp = self.add_laygo_primitive(blk_type, loc=(cur_col, row_idx), nx=num_pblk, spx=1)
        cur_col += num_pblk
        pdum_list.append((self.add_laygo_primitive(blk_type, loc=(cur_col, row_idx)), 0))
        cur_col += 1
        invp_outn = self.add_laygo_primitive(blk_type, loc=(cur_col, row_idx), nx=num_pblk, spx=1)
        cur_col += num_pblk
        rst_outn = self.add_laygo_primitive(blk_type, loc=(cur_col, row_idx))
        cur_col += 1
        rst_midn = self.add_laygo_primitive(blk_type, loc=(cur_col, row_idx))
        cur_col += 1
        pdum_list.append((self.add_laygo_primitive(blk_type, loc=(cur_col, row_idx), nx=colp, spx=1), 0))

        # nmos inverter row
        cur_col, row_idx = 0, 3
        ndum_list.append((self.add_laygo_primitive(blk_type, loc=(cur_col, row_idx), nx=coln - 1, spx=1), 0))
        cur_col += coln - 1
        ndum_list.append((self.add_laygo_primitive(blk_type, loc=(cur_col, row_idx), split_s=True), 1))
        cur_col += 1
        invn_outp = self.add_laygo_primitive(blk_type, loc=(cur_col, row_idx), nx=num_nblk, spx=1)
        cur_col += num_nblk
        tail_sw1 = self.add_laygo_primitive('stack2d', loc=(cur_col, row_idx))
        cur_col += 1
        invn_outn = self.add_laygo_primitive(blk_type, loc=(cur_col, row_idx), nx=num_nblk, spx=1)
        cur_col += num_nblk
        ndum_list.append((self.add_laygo_primitive(blk_type, loc=(cur_col, row_idx), split_s=True), -1))
        cur_col += 1
        ndum_list.append((self.add_laygo_primitive(blk_type, loc=(cur_col, row_idx), nx=coln - 1, spx=1), 0))

        # nmos input row
        cur_col, row_idx = 0, 2
        ndum_list.append((self.add_laygo_primitive(blk_type, loc=(cur_col, row_idx), nx=coln - 1, spx=1), 0))
        cur_col += coln - 1
        ndum_list.append((self.add_laygo_primitive(blk_type, loc=(cur_col, row_idx), split_s=True), 1))
        cur_col += 1
        inn = self.add_laygo_primitive(blk_type, loc=(cur_col, row_idx), nx=num_nblk, spx=1)
        cur_col += num_nblk
        tail_sw2 = self.add_laygo_primitive('stack2d', loc=(cur_col, row_idx))
        cur_col += 1
        inp = self.add_laygo_primitive(blk_type, loc=(cur_col, row_idx), nx=num_nblk, spx=1)
        cur_col += num_nblk
        ndum_list.append((self.add_laygo_primitive(blk_type, loc=(cur_col, row_idx), split_s=True), -1))
        cur_col += 1
        ndum_list.append((self.add_laygo_primitive(blk_type, loc=(cur_col, row_idx), nx=coln - 1, spx=1), 0))

        # nmos tail row
        cur_col, row_idx = 0, 1
        ndum_list.append((self.add_laygo_primitive(blk_type, loc=(cur_col, row_idx), nx=coln, spx=1), 0))
        cur_col += coln
        tailn = self.add_laygo_primitive(blk_type, loc=(cur_col, row_idx), nx=num_nblk, spx=1)
        cur_col += num_nblk
        ndum_list.append((self.add_laygo_primitive(blk_type, loc=(cur_col, row_idx)), 0))
        cur_col += 1
        tailp = self.add_laygo_primitive(blk_type, loc=(cur_col, row_idx), nx=num_nblk, spx=1)
        cur_col += num_nblk
        ndum_list.append((self.add_laygo_primitive(blk_type, loc=(cur_col, row_idx), nx=coln, spx=1), 0))

        # pwell tap
        cur_col, row_idx = 0, 0
        pw_tap = self.add_laygo_primitive('sub', loc=(cur_col, row_idx), nx=tot_blk, spx=1)

        # compute overall block size
        self.set_laygo_size(num_col=tot_blk)
        self.fill_space()
        # draw boundaries and get guard ring power rail tracks
        self.draw_boundary_cells()

        # connect ground
        source_vss = pw_tap.get_all_port_pins('VSS') + tailn.get_all_port_pins('s') + tailp.get_all_port_pins('s')
        drain_vss = []
        for inst, mode in ndum_list:
            if mode == 0:
                source_vss.extend(inst.get_all_port_pins('s'))
            drain_vss.extend(inst.get_all_port_pins('d'))
            drain_vss.extend(inst.get_all_port_pins('g'))
        source_vss_tid = self.make_track_id(0, 'ds', 0, width=1)
        drain_vss_tid = self.make_track_id(0, 'ds', 1, width=1)
        source_vss_warrs = self.connect_to_tracks(source_vss, source_vss_tid)
        drain_vss_warrs = self.connect_to_tracks(drain_vss, drain_vss_tid)
        self.add_pin('VSS', source_vss_warrs, show=show_pins)
        self.add_pin('VSS', drain_vss_warrs, show=show_pins)

        # connect tail
        tail = []
        for inst in (tailp, tailn, inp, inn):
            tail.extend(inst.get_all_port_pins('d'))
        tail_tid = self.make_track_id(1, 'gb', 0)
        self.connect_to_tracks(tail, tail_tid)

        # connect tail clk
        clk_list = []
        tclk_tid = self.make_track_id(1, 'g', 0)
        tclk = tailp.get_all_port_pins('g') + tailn.get_all_port_pins('g')
        clk_list.append(self.connect_to_tracks(tclk, tclk_tid))

        # connect inputs
        in_tid = self.make_track_id(2, 'g', 1)
        inp_warr = self.connect_to_tracks(inp.get_all_port_pins('g'), in_tid)
        inn_warr = self.connect_to_tracks(inn.get_all_port_pins('g'), in_tid)

        # connect tail switch clk
        tsw2 = self.make_track_id(2, 'g', 0)
        clk_list.append(self.connect_to_tracks(tail_sw2.get_all_port_pins('g'), tsw2, min_len_mode=0))

        # get output/mid horizontal track id
        hm_layer = self.conn_layer + 1
        nout_idx = self.get_track_index(3, 'gb', 0)
        mid_idx = self.get_track_index(3, 'ds', 0)
        mid_idx = min(mid_idx, nout_idx - 1)
        nout_tid = TrackID(hm_layer, nout_idx)
        mid_tid = TrackID(hm_layer, mid_idx)

        # connect nmos mid
        nmidp = inn.get_all_port_pins('s') + invn_outp.get_all_port_pins('s')
        nmidn = inp.get_all_port_pins('s') + invn_outn.get_all_port_pins('s')
        nmidp = self.connect_to_tracks(nmidp, mid_tid)
        nmidn = self.connect_to_tracks(nmidn, mid_tid)

        # connect pmos mid
        mid_tid = self.make_track_id(4, 'gb', 1)
        pmidp = self.connect_to_tracks(rst_midp.get_all_port_pins('d'), mid_tid, min_len_mode=0)
        pmidn = self.connect_to_tracks(rst_midn.get_all_port_pins('d'), mid_tid, min_len_mode=0)

        # connect nmos output
        noutp = self.connect_to_tracks(invn_outp.get_all_port_pins('d'), nout_tid)
        noutn = self.connect_to_tracks(invn_outn.get_all_port_pins('d'), nout_tid)

        # connect pmos output
        pout_tid = self.make_track_id(4, 'gb', 0)
        poutp = invp_outp.get_all_port_pins('d') + rst_outp.get_all_port_pins('d')
        poutn = invp_outn.get_all_port_pins('d') + rst_outn.get_all_port_pins('d')
        poutp = self.connect_to_tracks(poutp, pout_tid)
        poutn = self.connect_to_tracks(poutn, pout_tid)

        # connect clock in inverter row
        pclk = []
        for inst in (rst_midp, rst_midn, rst_outp, rst_outn):
            pclk.extend(inst.get_all_port_pins('g'))
        nclk = tail_sw1.get_all_port_pins('g')
        pclk_tid = self.make_track_id(4, 'g', 0)
        nclk_tid = self.make_track_id(3, 'g', 0)
        clk_list.append(self.connect_to_tracks(pclk, pclk_tid))
        clk_list.append(self.connect_to_tracks(nclk, nclk_tid, min_len_mode=0))

        # connect inverter gate
        invg_tid = self.make_track_id(3, 'g', 1)
        invgp = invn_outp.get_all_port_pins('g') + invp_outp.get_all_port_pins('g')
        invgp = self.connect_to_tracks(invgp, invg_tid)
        invgn = invn_outn.get_all_port_pins('g') + invp_outn.get_all_port_pins('g')
        invgn = self.connect_to_tracks(invgn, invg_tid)

        # connect vdd
        source_vdd = nw_tap.get_all_port_pins('VDD')
        source_vdd.extend(invp_outp.get_all_port_pins('s'))
        source_vdd.extend(invp_outn.get_all_port_pins('s'))
        drain_vdd = []
        for inst, _ in pdum_list:
            source_vdd.extend(inst.get_all_port_pins('s'))
            drain_vdd.extend(inst.get_all_port_pins('d'))
            drain_vdd.extend(inst.get_all_port_pins('g'))
        source_vdd_tid = self.make_track_id(5, 'ds', 0, width=1)
        drain_vdd_tid = self.make_track_id(5, 'ds', 1, width=1)
        source_vdd_warrs = self.connect_to_tracks(source_vdd, source_vdd_tid)
        drain_vdd_warrs = self.connect_to_tracks(drain_vdd, drain_vdd_tid)
        self.add_pin('VDD', source_vdd_warrs, show=show_pins)
        self.add_pin('VDD', drain_vdd_warrs, show=show_pins)


def make_tdb(prj, target_lib, specs):
    grid_specs = specs['routing_grid']
    layers = grid_specs['layers']
    spaces = grid_specs['spaces']
    widths = grid_specs['widths']
    bot_dir = grid_specs['bot_dir']

    routing_grid = RoutingGrid(prj.tech_info, layers, spaces, widths, bot_dir)
    tdb = TemplateDB('template_libs.def', routing_grid, target_lib, use_cybagoa=True)
    return tdb


def generate(prj, specs):
    lib_name = 'AAAFOO'

    params = specs['params']

    temp_db = make_tdb(prj, lib_name, specs)

    template = temp_db.new_template(params=params, temp_cls=StrongArmLatch, debug=False)
    name = 'STRONGARM_LATCH'
    print('create layout')
    temp_db.batch_layout(prj, [template], [name])
    print('done')


if __name__ == '__main__':

    with open('test_specs/strongarm_latch.yaml', 'r') as f:
        block_specs = yaml.load(f)

    local_dict = locals()
    if 'bprj' not in local_dict:
        print('creating BAG project')
        bprj = BagProject()

        generate(bprj, block_specs)
    else:
        print('loading BAG project')
