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


"""This module defines abstract analog mosfet template classes.
"""

from __future__ import (absolute_import, division,
                        print_function, unicode_literals)
# noinspection PyUnresolvedReferences,PyCompatibility
from builtins import *

from typing import Dict, Any, Set

from bag import float_to_si_string
from bag.layout.template import TemplateBase, TemplateDB

from .core import MOSTech


class AnalogMOSBase(TemplateBase):
    """An abstract template for analog mosfet.

    Must have parameters mos_type, lch, w, threshold, fg.
    Instantiates a transistor with minimum G/D/S connections.

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
        # type: (TemplateDB, str, Dict[str, Any], Set[str], **Any) -> None
        super(AnalogMOSBase, self).__init__(temp_db, lib_name, params, used_names, **kwargs)
        self._tech_cls = self.grid.tech_info.tech_params['layout']['mos_tech_class']  # type: MOSTech
        self.prim_top_layer = self._tech_cls.get_mos_conn_layer()

        self._layout_info = None
        self._ext_top_info = None
        self._ext_bot_info = None

        self._g_conn_y = None
        self._d_conn_y = None
        self._sd_yc = None

    def get_g_conn_y(self):
        return self._g_conn_y

    def get_d_conn_y(self):
        return self._d_conn_y

    def get_ext_top_info(self):
        return self._ext_top_info

    def get_ext_bot_info(self):
        return self._ext_bot_info

    def get_sd_yc(self):
        return self._sd_yc

    def get_edge_layout_info(self):
        return self._layout_info

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
            lch='channel length, in meters.',
            w='transistor width, in meters/number of fins.',
            mos_type="transistor type, either 'pch' or 'nch'.",
            threshold='transistor threshold flavor.',
        )

    def get_layout_basename(self):
        fmt = '%s_l%s_w%s_%s'
        mos_type = self.params['mos_type']
        lstr = float_to_si_string(self.params['lch'])
        wstr = float_to_si_string(self.params['w'])
        th = self.params['threshold']
        return fmt % (mos_type, lstr, wstr, th)

    def compute_unique_key(self):
        return self.get_layout_basename()

    def draw_layout(self):
        self._draw_layout_helper(**self.params)

    def _draw_layout_helper(self, lch, w, mos_type, threshold, **kwargs):
        res = self.grid.resolution
        lch_unit = int(round(lch / self.grid.layout_unit / res))

        fg = self._tech_cls.get_analog_unit_fg()
        mos_info = self._tech_cls.get_mos_info(lch_unit, w, mos_type, threshold, fg)
        self._layout_info = mos_info['layout_info']
        # set parameters
        self._ext_top_info = mos_info['ext_top_info']
        self._ext_bot_info = mos_info['ext_bot_info']
        self._sd_yc = mos_info['sd_yc']
        self._g_conn_y = mos_info['g_conn_y']
        self._d_conn_y = mos_info['d_conn_y']

        # draw transistor
        self._tech_cls.draw_mos(self, self._layout_info)


class AnalogMOSExt(TemplateBase):
    """The abstract base class for finfet layout classes.

    This class provides the draw_foundation() method, which draws the poly array
    and implantation layers.
    """

    def __init__(self, temp_db, lib_name, params, used_names, **kwargs):
        # type: (TemplateDB, str, Dict[str, Any], Set[str], **Any) -> None
        super(AnalogMOSExt, self).__init__(temp_db, lib_name, params, used_names, **kwargs)
        self._tech_cls = self.grid.tech_info.tech_params['layout']['mos_tech_class']  # type: MOSTech
        self._layout_info = None
        if self.params['is_laygo']:
            self.prim_top_layer = self._tech_cls.get_dig_conn_layer()
            self._fg = self._tech_cls.get_analog_unit_fg()
        else:
            self.prim_top_layer = self._tech_cls.get_mos_conn_layer()
            self._fg = self._tech_cls.get_analog_unit_fg()

    @classmethod
    def get_default_param_values(cls):
        return dict(is_laygo=False)

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
            lch='channel length, in meters.',
            w='extension width, in layout units/number of fins.',
            bot_mtype="bottom transistor/substrate type",
            top_mtype="top transistor/substrate type.",
            bot_thres='bottom transistor/substrate threshold flavor.',
            top_thres='top transistor/substrate threshold flavor.',
            top_ext_info='top extension info.',
            bot_ext_info='bottom extension info.',
            is_laygo='True if this extension is used in LaygoBase.',
        )

    def get_edge_layout_info(self):
        return self._layout_info

    def get_layout_basename(self):
        fmt = 'ext_b%s_t%s_l%s_w%s_b%s_t%s'
        bot_mtype = self.params['bot_mtype']
        top_mtype = self.params['top_mtype']
        bot_thres = self.params['bot_thres']
        top_thres = self.params['top_thres']
        lstr = float_to_si_string(self.params['lch'])
        wstr = float_to_si_string(self.params['w'])
        ans = fmt % (bot_mtype, top_mtype, lstr, wstr, bot_thres, top_thres)
        if self.params['is_laygo']:
            ans = 'laygo_' + ans
        return ans

    def compute_unique_key(self):
        key = self.get_layout_basename(), self.params['top_ext_info'], self.params['bot_ext_info']
        return self.to_immutable_id(key)

    def draw_layout(self):
        self._draw_layout_helper(**self.params)

    def _draw_layout_helper(self, lch, w, bot_mtype, top_mtype, bot_thres, top_thres, top_ext_info,
                            bot_ext_info, **kwargs):
        res = self.grid.resolution
        lch_unit = int(round(lch / self.grid.layout_unit / res))

        ext_info = self._tech_cls.get_ext_info(lch_unit, w, bot_mtype, top_mtype, bot_thres, top_thres, self._fg,
                                               top_ext_info, bot_ext_info)
        self._layout_info = ext_info
        self._tech_cls.draw_mos(self, ext_info)
