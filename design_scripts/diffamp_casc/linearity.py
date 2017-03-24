# -*- coding: utf-8 -*-

from typing import List, Union, Dict, Tuple
import cProfile
import pstats

import numpy as np
import scipy.optimize
import scipy.signal

from bag.tech.mos import MosCharDB
from bag.math.dfun import DiffFunction
from bag.data.lti import LTICircuit
from bag.data.dc import DCCircuit
from bag.util.search import BinaryIterator


def solve_casc_diff_dc(env_list,  # type: List[str]
                       ndb,  # type: MosCharDB
                       pdb,  # type: MosCharDB
                       lch,  # type: float
                       intent_list,  # type: List[str]
                       w_list,  # type: List[Union[float, int]]
                       fg_list,  # type: List[int]
                       vbias_list,  # type: List[float]
                       vload_list,  # type: List[float]
                       vtail_list,  # type: List[float]
                       vmid_list,  # type: List[float]
                       vdd,  # type: float
                       vcm,  # type: float
                       vin_max,  # type: float
                       verr_max,  # type: float
                       num_points=20,
                       inorm=1e-6,  # type: float
                       itol=1e-9  # type: float
                       ):
    # type: (...) -> Tuple[np.ndarray, List[np.ndarray], List[float], List[float]]

    intent_tail, intent_in, intent_casc, intent_load = intent_list
    w_tail, w_in, w_casc, w_load = w_list
    fg_tail, fg_in, fg_casc, fg_load = fg_list
    # construct DC circuit
    circuit = DCCircuit(ndb, pdb)
    circuit.add_transistor('tail', 'bias', 'gnd', 'gnd', 'nch', intent_tail, w_tail, lch, fg=2 * fg_tail)
    circuit.add_transistor('midn', 'inp', 'tail', 'gnd', 'nch', intent_in, w_in, lch, fg=fg_in)
    circuit.add_transistor('midp', 'inn', 'tail', 'gnd', 'nch', intent_in, w_in, lch, fg=fg_in)
    circuit.add_transistor('outn', 'vdd', 'midn', 'gnd', 'nch', intent_casc, w_casc, lch, fg=fg_casc)
    circuit.add_transistor('outp', 'vdd', 'midp', 'gnd', 'nch', intent_casc, w_casc, lch, fg=fg_casc)
    circuit.add_transistor('outn', 'load', 'vdd', 'vdd', 'pch', intent_load, w_load, lch, fg=fg_load)
    circuit.add_transistor('outp', 'load', 'vdd', 'vdd', 'pch', intent_load, w_load, lch, fg=fg_load)
    circuit.set_voltage_source('vdd', vdd)

    vin_vec = np.linspace(0, vin_max, num_points, endpoint=True)
    vin_vec_diff = np.linspace(-vin_max, vin_max, 2 * num_points - 1, endpoint=True)  # type: np.ndarray
    vmat_list = []
    verr_list = []
    gain_list = []
    for env, vbias, vload, vt, vm in zip(env_list, vbias_list, vload_list, vtail_list, vmid_list):
        circuit.set_voltage_source('bias', vbias)
        circuit.set_voltage_source('load', vload)
        guess_dict = {'tail': vt, 'midp': vm, 'midn': vm, 'outp': vcm, 'outn': vcm}
        vmat = np.empty((2 * num_points - 1, 5))

        for idx, vin_diff in enumerate(vin_vec):
            circuit.set_voltage_source('inp', vcm + vin_diff / 2)
            circuit.set_voltage_source('inn', vcm - vin_diff / 2)

            op_dict = circuit.solve(env, guess_dict, inorm=inorm, itol=itol)
            vts, vmps, vmns = op_dict['tail'], op_dict['midp'], op_dict['midn']
            vops, vons = op_dict['outp'], op_dict['outn']
            vmat[idx + num_points - 1, 0] = vts
            vmat[num_points - 1 - idx, 0] = vts
            vmat[idx + num_points - 1, 1] = vmps
            vmat[num_points - 1 - idx, 1] = vmns
            vmat[idx + num_points - 1, 2] = vmns
            vmat[num_points - 1 - idx, 2] = vmps
            vmat[idx + num_points - 1, 3] = vops
            vmat[num_points - 1 - idx, 3] = vons
            vmat[idx + num_points - 1, 4] = vons
            vmat[num_points - 1 - idx, 4] = vops

        gain, verr = get_inl(vin_vec_diff, vmat[:, 3] - vmat[:, 4])
        if verr > verr_max:
            # we didn't meet linearity spec, abort.
            raise ValueError('failed linearity error spec at env = %s' % env)

        gain_list.append(gain)
        verr_list.append(verr)
        vmat_list.append(vmat)

    return vin_vec_diff, vmat_list, verr_list, gain_list


def solve_casc_gm_dc(env_list,  # type: List[str]
                     db_list,  # type: List[MosCharDB]
                     w_list,  # type: List[Union[float, int]]
                     fg_list,  # type: List[int]
                     vdd,  # type: float
                     vcm,  # type: float
                     vstar_targ,  # type: float
                     inorm=1e-6,  # type: float
                     itol=1e-9,  # type: float
                     vtol=1e-6  # type: float
                     ):
    # type: (...) -> Tuple[List[Dict[str, float]], List[float], List[float]]
    vtail_list = []
    vmid_list = []
    in_params_list = []

    db_in, db_casc = db_list
    w_in, w_casc = w_list
    fg_in, fg_casc = fg_list
    x0 = np.array([0, vcm / 2])

    # in_op = (w, -vtail, vmid - vtail, vcm - vtail)
    in_amat = np.array([[0, 0],
                        [-1, 0],
                        [-1, 1],
                        [-1, 0]])
    in_bmat = np.array([w_in, 0, 0, vcm])
    # casc_op = (w, -vmid, vcm - vmid, vdd - vmid)
    casc_amat = np.array([[0, 0],
                          [0, -1],
                          [0, -1],
                          [0, -1]])
    casc_bmat = np.array([w_casc, 0, vcm, vdd])

    for env in env_list:
        vstar_in = db_in.get_function('vstar', env=env)
        ids_in = db_in.get_function('ids', env=env)
        ids_casc = db_casc.get_function('ids', env=env)

        ids_in = (fg_in / inorm) * ids_in.transform_input(in_amat, in_bmat)
        vstar_diff = vstar_in.transform_input(in_amat, in_bmat) - vstar_targ  # type: DiffFunction
        ids_casc = (fg_casc / inorm) * ids_casc.transform_input(casc_amat, casc_bmat)
        idiff = ids_casc - ids_in  # type: DiffFunction

        def fun1(vin1):
            ans = np.empty(2)
            ans[0] = vstar_diff(vin1)
            ans[1] = idiff(vin1)
            return ans

        result = scipy.optimize.root(fun1, x0, tol=min(vtol, itol / inorm), method='hybr')
        if not result.success:
            raise ValueError('solution failed.')
        vtail, vmid = result.x

        in_params = db_list[0].query(env=env, w=w_in, vbs=-vtail, vds=vmid - vtail, vgs=vcm - vtail)
        vtail_list.append(vtail)
        vmid_list.append(vmid)
        in_params_list.append(in_params)

    return in_params_list, vtail_list, vmid_list


def solve_load_bias(env_list, pdb, w_load, fg_load, vdd, vcm, ibias_list, vtol=1e-6):
    # type: (List[str], MosCharDB, float, int, float, float, List[float], float) -> List[float]
    # find load bias voltage

    vload_list = []
    for env, ibias in zip(env_list, ibias_list):
        ids_load = pdb.get_function('ids', env=env)

        def fun2(vin2):
            return (-fg_load * ids_load(np.array([w_load, 0, vcm - vdd, vin2 - vdd])) - ibias) / 1e-6

        vload_list.append(scipy.optimize.brentq(fun2, 0, vdd, xtol=vtol))

    return vload_list


def solve_tail_bias(env, ndb, w_tail, fg_tail, vdd, vtail, ibias, vtol=1e-6):
    # type: (str, MosCharDB, float, int, float, float, float, float) -> float
    # find load bias voltage
    ids_tail = ndb.get_function('ids', env=env)

    def fun2(vin2):
        return (fg_tail * ids_tail(np.array([w_tail, 0, vtail, vin2])) - ibias) / 1e-6

    vbias = scipy.optimize.brentq(fun2, 0, vdd, xtol=vtol)  # type: float

    return vbias


def design_tail(env_list, ndb, fg_in, in_params_list, vtail_list, fg_swp, w_tail, vdd, tau_max):
    fg_opt = None
    ro_opt = 0
    vbias_list_opt = []
    ro_list_opt = None
    for fg_tail in fg_swp:
        tau_worst = 0
        ro_worst = float('inf')
        ro_list = []
        vbias_list = []
        for env, vtail, in_params in zip(env_list, vtail_list, in_params_list):
            ibias = in_params['ids'] * fg_in
            try:
                vbias = solve_tail_bias(env, ndb, w_tail, fg_tail, vdd, vtail, ibias)
            except ValueError:
                tau_worst = None
                break

            vbias_list.append(vbias)
            tail_params = ndb.query(env=env, w=w_tail, vbs=0, vds=vtail, vgs=vbias)
            ro_tail = 1 / (fg_tail * tail_params['gds'])
            gm_in = fg_in * in_params['gm']
            cdd_tail = fg_tail * tail_params['cdd']
            css_gm = fg_in * in_params['css']
            tau = (css_gm + cdd_tail) / (1 / ro_tail + gm_in)
            ro_list.append(ro_tail)
            if tau > tau_worst:
                tau_worst = tau
            if ro_tail < ro_worst:
                ro_worst = ro_tail

        if tau_worst is not None:
            if tau_worst <= tau_max and ro_worst > ro_opt:
                ro_opt = ro_worst
                fg_opt = fg_tail
                vbias_list_opt = vbias_list
                ro_list_opt = ro_list

    if fg_opt is None:
        raise ValueError('No solution for tail current source.')

    return fg_opt, ro_list_opt, vbias_list_opt


def get_inl(xvec, yvec):
    def fit_fun(xval, scale):
        return scale * xval

    mvec = scipy.optimize.curve_fit(fit_fun, xvec, yvec, p0=1)[0]
    return mvec[0], np.max(np.abs(yvec - mvec[0] * xvec))


def characterize_casc_amp(env_list, lch, intent_list, fg_list, w_list, db_list, vbias_list, vload_list,
                          vtail_list, vmid_list, vcm, vdd, vin_max,
                          cw, rw, fanout, ton, k_settle_targ, verr_max,
                          scale_res=0.1, scale_min=0.25, scale_max=20):
    # compute DC transfer function curve and compute linearity spec
    ndb, pdb = db_list[0], db_list[-1]
    results = solve_casc_diff_dc(env_list, ndb, pdb, lch, intent_list, w_list, fg_list, vbias_list, vload_list,
                                 vtail_list, vmid_list, vdd, vcm, vin_max, verr_max, num_points=20)

    vin_vec, vmat_list, verr_list, gain_list = results

    # compute settling ratio
    fg_in, fg_casc, fg_load = fg_list[1:]
    db_in, db_casc, db_load = db_list[1:]
    w_in, w_casc, w_load = w_list[1:]
    fzin = 1.0 / (2 * ton)
    wzin = 2 * np.pi * fzin
    tvec = np.linspace(0, ton, 200, endpoint=True)
    scale_list = []
    for env, vload, vtail, vmid in zip(env_list, vload_list, vtail_list, vmid_list):
        # step 1: construct half circuit
        in_params = db_in.query(env=env, w=w_in, vbs=-vtail, vds=vmid-vtail, vgs=vcm-vtail)
        casc_params = db_casc.query(env=env, w=w_casc, vbs=-vmid, vds=vcm-vmid, vgs=vdd-vmid)
        load_params = db_load.query(env=env, w=w_load, vbs=0, vds=vcm-vdd, vgs=vload-vdd)
        circuit = LTICircuit()
        circuit.add_transistor(in_params, 'mid', 'in', 'gnd', fg=fg_in)
        circuit.add_transistor(casc_params, 'd', 'gnd', 'mid', fg=fg_casc)
        circuit.add_transistor(load_params, 'd', 'gnd', 'gnd', fg=fg_load)
        # step 2: get input capacitance
        zin = circuit.get_impedance('in', fzin)
        cin = (1 / zin).imag / wzin
        circuit.add_cap(cin * fanout, 'out', 'gnd')
        # step 3: find scale factor to achieve k_settle
        bin_iter = BinaryIterator(scale_min, None, step=scale_res, is_float=True)
        while bin_iter.has_next():
            # add scaled wired parasitics
            cur_scale = bin_iter.get_next()
            cap_cur = cw / 2 / cur_scale
            res_cur = rw * cur_scale
            circuit.add_cap(cap_cur, 'd', 'gnd')
            circuit.add_cap(cap_cur, 'out', 'gnd')
            circuit.add_res(res_cur, 'd', 'out')
            # get settling factor
            sys = circuit.get_voltage_gain_system('in', 'out')
            dc_gain = sys.freqresp(w=np.array([0.1]))[1][0]
            sgn = 1 if dc_gain.real >= 0 else -1
            dc_gain = abs(dc_gain)
            _, yvec = scipy.signal.step(sys, T=tvec)  # type: Tuple[np.ndarray, np.ndarray]
            k_settle_cur = 1 - abs(yvec[-1] - sgn * dc_gain) / dc_gain
            # print('scale = %.4g, k_settle = %.4g' % (cur_scale, k_settle_cur))
            # update next scale factor
            if k_settle_cur >= k_settle_targ:
                # print('save scale = %.4g' % cur_scale)
                bin_iter.save()
                bin_iter.down()
            else:
                if cur_scale > scale_max:
                    raise ValueError('cannot meet settling time spec at scale = %d' % cur_scale)
                bin_iter.up()
            # remove wire parasitics
            circuit.add_cap(-cap_cur, 'd', 'gnd')
            circuit.add_cap(-cap_cur, 'out', 'gnd')
            circuit.add_res(-res_cur, 'd', 'out')
        scale_list.append(bin_iter.get_last_save())

    return vmat_list, verr_list, gain_list, scale_list


def test(vstar_targ=0.25, vin_max=0.25, vdd=0.9, vcm=0.775, verr_max=10e-3):
    root_dir = 'tsmc16_FFC/mos_data'
    # env_range = ['tt', 'ff', 'ss', 'fs', 'sf', 'ff_hot', 'ss_hot', 'ss_cold']
    lch = 16e-9
    env_range = ['tt', 'ff', 'ss_cold', 'fs', 'sf']
    cw = 6e-15
    rw = 200
    ton = 50e-12
    fanout = 2
    k_settle_targ = 0.95
    tau_tail_max = ton / 20
    min_fg = 2

    w_list = [4, 4, 4, 6]
    fg_in = 4
    # fg_casc_swp = [4]
    # fg_load_swp = [4]
    fg_casc_range = list(range(4, 11, 2))
    fg_tail_range = list(range(4, 9, 2))
    fg_load_range = list(range(2, 5, 2))

    ndb = MosCharDB(root_dir, 'nch', ['intent', 'l'], env_range, intent='ulvt', l=lch, method='linear')
    pdb = MosCharDB(root_dir, 'pch', ['intent', 'l'], env_range, intent='ulvt', l=lch, method='linear')

    db_list = [ndb, ndb, ndb, pdb]
    intent_list = ['ulvt', 'ulvt', 'ulvt', 'ulvt']
    db_gm_list = [ndb, ndb]
    w_gm_list = w_list[1:3]
    w_load = w_list[3]
    w_tail = w_list[0]

    opt_ibias = None
    opt_info = {}
    for fg_casc in fg_casc_range:
        fg_gm_list = [fg_in, fg_casc]
        try:
            in_params_list, vtail_list, vmid_list = solve_casc_gm_dc(env_range, db_gm_list, w_gm_list, fg_gm_list,
                                                                     vdd, vcm, vstar_targ)
        except ValueError:
            print('failed to solve cascode with fg_casc = %d' % fg_casc)
            continue

        try:
            fg_tail, rtail_list_opt, vbias_list = design_tail(env_range, ndb, fg_in, in_params_list, vtail_list,
                                                              fg_tail_range, w_tail, vdd, tau_tail_max)
        except ValueError:
            print('failed to solve tail with fg_casc = %d' % fg_casc)
            continue

        # noinspection PyUnresolvedReferences
        ibias_list = [fg_in * in_params['ids'][0] for in_params in in_params_list]
        for fg_load in fg_load_range:
            try:
                vload_list = solve_load_bias(env_range, pdb, w_load, fg_load, vdd, vcm, ibias_list)
            except ValueError:
                print('failed to solve load with fg_load = %d' % fg_load)
                continue

            fg_list = [fg_tail, fg_in, fg_casc, fg_load]
            scale_min = min(fg_list) / min_fg
            try:
                results = characterize_casc_amp(env_range, lch, intent_list, fg_list, w_list, db_list, vbias_list,
                                                vload_list, vtail_list, vmid_list, vcm, vdd, vin_max, cw, rw,
                                                fanout, ton, k_settle_targ, verr_max, scale_min=scale_min)
            except ValueError:
                print('failed nonlinearity or bandwidth spec with fg_load = %d' % fg_load)
                continue

            vmat_list, verr_list, gain_list, scale_list = results
            max_scale = max(scale_list)
            ibias_list = [max_scale * val for val in ibias_list]
            print('fg: %s' % ' '.join(['%.4g' % val for val in fg_list]))
            print('vbias: %s' % ' '.join(['%.4g' % val for val in vbias_list]))
            print('vload: %s' % ' '.join(['%.4g' % val for val in vload_list]))
            print('vtail: %s' % ' '.join(['%.4g' % val for val in vtail_list]))
            print('vmid: %s' % ' '.join(['%.4g' % val for val in vmid_list]))
            print('verr: %s' % ' '.join(['%.4g' % val for val in verr_list]))
            print('gain: %s' % ' '.join(['%.4g' % val for val in gain_list]))
            print('scale: %s' % ' '.join(['%.4g' % val for val in scale_list]))
            print('ibias: %s' % ' '.join(['%.4g' % val for val in ibias_list]))
            ibias_worst = max(ibias_list)
            if opt_ibias is None or ibias_worst < opt_ibias:
                opt_ibias = ibias_worst
                opt_info['fg_list'] = fg_list
                opt_info['vbias_list'] = vbias_list
                opt_info['vload_list'] = vload_list
                opt_info['vtail_list'] = vtail_list
                opt_info['vmid_list'] = vmid_list
                opt_info['verr_list'] = verr_list
                opt_info['gain_list'] = gain_list
                opt_info['ibias_list'] = ibias_list
                opt_info['scale'] = max_scale

    return opt_info


def profile():
    cProfile.runctx('test()',
                    globals(), locals(), filename='casc_linearity.data')
    p = pstats.Stats('casc_linearity.data')
    return p.strip_dirs()
