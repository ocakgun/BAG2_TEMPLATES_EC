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

"""This module defines template used for transistor characterization."""
from __future__ import (absolute_import, division,
                        print_function, unicode_literals)
# noinspection PyUnresolvedReferences,PyCompatibility
from builtins import *

from .analog_core import AnalogBase


class Transistor(AnalogBase):
    """A template of a single transistor with dummies.

    This class is mainly used for transistor characterization or
    design exploration with config views.

    Parameters
    ----------
    temp_db : :class:`bag.layout.template.TemplateDB`
            the template database.
    lib_name : str
        the layout library name.
    params : dict[str, any]
        the parameter values.
    used_names : set[str]
        a set of already used cell names.
    kwargs : dict[str, any]
        dictionary of optional parameters.  See documentation of
        :class:`bag.layout.template.TemplateBase` for details.
    """

    def __init__(self, temp_db, lib_name, params, used_names, **kwargs):
        AnalogBase.__init__(self, temp_db, lib_name, params, used_names, **kwargs)

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
            mos_type="transistor type, either 'pch' or 'nch'.",
            lch='channel length, in meters.',
            w='transistor width, in meters/number of fins.',
            fg='number of fingers.',
            fg_dum='number of dummies on each side.',
            threshold='transistor threshold flavor.',
            ptap_w='NMOS substrate width, in meters/number of fins.',
            ntap_w='PMOS substrate width, in meters/number of fins.',
            num_track_sep='number of tracks reserved as space between ports.',
            min_ds_cap='True to minimize parasitic Cds.',
            global_gnd_layer='layer of the global ground pin.  None to disable drawing global ground.',
            global_gnd_name='name of global ground pin.',
            draw_other='True to draw the other type of transistor as dummies.',
            nd_tracks='Number of drain tracks.',
        )

    @classmethod
    def get_default_param_values(cls):
        """Returns a dictionary containing default parameter values.

        Override this method to define default parameter values.  As good practice,
        you should avoid defining default values for technology-dependent parameters
        (such as channel length, transistor width, etc.), but only define default
        values for technology-independent parameters (such as number of tracks).

        Returns
        -------
        default_params : dict[str, any]
            dictionary of default parameter values.
        """
        return dict(
            min_ds_cap=False,
            global_gnd_layer=None,
            global_gnd_name='gnd!',
            draw_other=False,
            nd_tracks=1,
        )

    def draw_layout(self):
        """Draw the layout of a transistor for characterization.
        """

        mos_type = self.params['mos_type']
        lch = self.params['lch']
        w = self.params['w']
        fg = self.params['fg']
        fg_dum = self.params['fg_dum']
        threshold = self.params['threshold']
        ptap_w = self.params['ptap_w']
        ntap_w = self.params['ntap_w']
        num_track_sep = self.params['num_track_sep']
        global_gnd_layer = self.params['global_gnd_layer']
        global_gnd_name = self.params['global_gnd_name']
        draw_other = self.params['draw_other']
        nd_tracks = self.params['nd_tracks']
        
        fg_tot = fg + 2 * fg_dum

        nw_list = []
        nth_list = []
        pw_list = []
        pth_list = []
        ng_tracks = []
        nds_tracks = []
        pg_tracks = []
        pds_tracks = []
        num_gate_tr = 2 + num_track_sep
        if mos_type == 'nch' or draw_other:
            nw_list.append(w)
            nth_list.append(threshold)
            ng_tracks.append(num_gate_tr)
            if mos_type == 'nch':
                nds_tracks.append(nd_tracks)
            else:
                nds_tracks.append(1)
        if mos_type == 'pch' or draw_other:
            pw_list.append(w)
            pth_list.append(threshold)
            pg_tracks.append(num_gate_tr)
            if mos_type == 'pch':
                pds_tracks.append(nd_tracks)
            else:
                pds_tracks.append(1)
        self.draw_base(lch, fg_tot, ptap_w, ntap_w, nw_list,
                       nth_list, pw_list, pth_list, num_track_sep,
                       ng_tracks=ng_tracks, nds_tracks=nds_tracks,
                       pg_tracks=pg_tracks, pds_tracks=pds_tracks,
                       )

        if mos_type == 'pch':
            sdir, ddir = 2, 0
        else:
            sdir, ddir = 0, 2
        mos_ports = self.draw_mos_conn(mos_type, 0, fg_dum, fg, sdir, ddir, min_ds_cap=self.params['min_ds_cap'])
        tr_id = self.make_track_id(mos_type, 0, 'g', num_gate_tr - 1)
        warr = self.connect_to_tracks(mos_ports['g'], tr_id)
        self.add_pin('g', warr, show=True)

        tr_id = self.make_track_id(mos_type, 0, 'ds', nd_tracks // 2)
        warr = self.connect_to_tracks(mos_ports['d'], tr_id)
        self.add_pin('d', warr, show=True)

        tr_id = self.make_track_id(mos_type, 0, 'g', 0)
        warr = self.connect_to_tracks(mos_ports['s'], tr_id)
        self.add_pin('s', warr, show=True)

        ptap_wire_arrs, ntap_wire_arrs = self.fill_dummy()
        # export body
        blabel = 'b:' if draw_other else 'b'
        self.add_pin('b', ptap_wire_arrs, label=blabel, show=True)
        self.add_pin('b', ntap_wire_arrs, label=blabel, show=True)

        if global_gnd_layer is not None:
            _, global_gnd_box = next(ptap_wire_arrs[0].wire_iter(self.grid))
            self.add_pin_primitive(global_gnd_name, global_gnd_layer, global_gnd_box)


class TransistorGD(AnalogBase):
    """A template of a single transistor with dummies, where source and body are shorted.

    This class is mainly used for transistor characterization or
    design exploration with config views.

    Parameters
    ----------
    temp_db : :class:`bag.layout.template.TemplateDB`
            the template database.
    lib_name : str
        the layout library name.
    params : dict[str, any]
        the parameter values.
    used_names : set[str]
        a set of already used cell names.
    kwargs : dict[str, any]
        dictionary of optional parameters.  See documentation of
        :class:`bag.layout.template.TemplateBase` for details.
    """

    def __init__(self, temp_db, lib_name, params, used_names, **kwargs):
        AnalogBase.__init__(self, temp_db, lib_name, params, used_names, **kwargs)

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
            mos_type="transistor type, either 'pch' or 'nch'.",
            lch='channel length, in meters.',
            w='transistor width, in meters/number of fins.',
            fg='number of fingers.',
            fg_dum='number of dummies on each side.',
            threshold='transistor threshold flavor.',
            ptap_w='NMOS substrate width, in meters/number of fins.',
            ntap_w='PMOS substrate width, in meters/number of fins.',
            num_track_sep='number of tracks reserved as space between ports.',
            min_ds_cap='True to minimize parasitic Cds.',
            global_gnd_layer='layer of the global ground pin.  None to disable drawing global ground.',
            global_gnd_name='name of global ground pin.',
            draw_other='True to draw the other type of transistor as dummies.',
            nd_tracks='Number of drain tracks.',
            hm_width='Horizontal metal width.',
            hm_cur_width='Horizontal current-carrying metal width.',
        )

    @classmethod
    def get_default_param_values(cls):
        """Returns a dictionary containing default parameter values.

        Override this method to define default parameter values.  As good practice,
        you should avoid defining default values for technology-dependent parameters
        (such as channel length, transistor width, etc.), but only define default
        values for technology-independent parameters (such as number of tracks).

        Returns
        -------
        default_params : dict[str, any]
            dictionary of default parameter values.
        """
        return dict(
            min_ds_cap=False,
            global_gnd_layer=None,
            global_gnd_name='gnd!',
            draw_other=False,
            nd_tracks=1,
            hm_width=1,
            hm_cur_width=1,
        )

    def draw_layout(self):
        """Draw the layout of a transistor for characterization.
        """

        mos_type = self.params['mos_type']
        lch = self.params['lch']
        w = self.params['w']
        fg = self.params['fg']
        fg_dum = self.params['fg_dum']
        threshold = self.params['threshold']
        ptap_w = self.params['ptap_w']
        ntap_w = self.params['ntap_w']
        num_track_sep = self.params['num_track_sep']
        global_gnd_layer = self.params['global_gnd_layer']
        global_gnd_name = self.params['global_gnd_name']
        draw_other = self.params['draw_other']
        nd_tracks = self.params['nd_tracks']
        hm_width = self.params['hm_width']
        hm_cur_width = self.params['hm_cur_width']

        fg_tot = fg + 2 * fg_dum
        nd_tracks = max(nd_tracks, hm_cur_width)

        nw_list = []
        nth_list = []
        pw_list = []
        pth_list = []
        ng_tracks = []
        nds_tracks = []
        pg_tracks = []
        pds_tracks = []
        if mos_type == 'nch' or draw_other:
            nw_list.append(w)
            nth_list.append(threshold)
            ng_tracks.append(hm_width)
            if mos_type == 'nch':
                nds_tracks.append(nd_tracks)
            else:
                nds_tracks.append(hm_cur_width)
        if mos_type == 'pch' or draw_other:
            pw_list.append(w)
            pth_list.append(threshold)
            pg_tracks.append(hm_width)
            if mos_type == 'pch':
                pds_tracks.append(nd_tracks)
            else:
                pds_tracks.append(hm_cur_width)
        self.draw_base(lch, fg_tot, ptap_w, ntap_w, nw_list,
                       nth_list, pw_list, pth_list, num_track_sep,
                       ng_tracks=ng_tracks, nds_tracks=nds_tracks,
                       pg_tracks=pg_tracks, pds_tracks=pds_tracks,
                       )

        if mos_type == 'pch':
            sdir, ddir = 2, 0
        else:
            sdir, ddir = 0, 2
        mos_ports = self.draw_mos_conn(mos_type, 0, fg_dum, fg, sdir, ddir, min_ds_cap=self.params['min_ds_cap'])
        tr_id = self.make_track_id(mos_type, 0, 'g', (hm_width - 1) / 2, width=hm_width)
        warr = self.connect_to_tracks(mos_ports['g'], tr_id)
        self.add_pin('g', warr, show=True)

        tr_id = self.make_track_id(mos_type, 0, 'ds', nd_tracks // 2, width=hm_cur_width)
        warr = self.connect_to_tracks(mos_ports['d'], tr_id)
        self.add_pin('d', warr, show=True)

        if mos_type == 'pch':
            self.connect_to_substrate('ntap', mos_ports['s'])
        else:
            self.connect_to_substrate('ptap', mos_ports['s'])

        ptap_wire_arrs, ntap_wire_arrs = self.fill_dummy()
        # export body
        blabel = 's:' if draw_other else 's'
        self.add_pin('s', ptap_wire_arrs, label=blabel, show=True)
        self.add_pin('s', ntap_wire_arrs, label=blabel, show=True)

        if global_gnd_layer is not None:
            _, global_gnd_box = next(ptap_wire_arrs[0].wire_iter(self.grid))
            self.add_pin_primitive(global_gnd_name, global_gnd_layer, global_gnd_box)
