"""One-off patch: wire the 6-DOF dynamics (sim/dyn6.py) into sim/engine.py as a default-off switch."""
p = r"D:\newprj\sim\engine.py"
s = open(p, encoding="utf-8").read()
if "_slant_range_dir" in s:
    raise SystemExit("already applied")


def rep(old, new, cnt=1):
    global s
    assert s.count(old) == cnt, (s.count(old), old[:90])
    s = s.replace(old, new)


rep("import numpy as np\n\nG = 1.62", "import numpy as np\n\nimport dyn6 as _dyn6\n\nG = 1.62")
rep('''def _consensus_ok(zapp, var):''', '''def _slant_range_dir(height, px, py, z, dx, dy, cz):
    """Like _slant_range for an arbitrary beam direction: (dx, dy) = horizontal components of the unit direction, cz = its downward
    component (all arrays, one entry per run). Used by the 6-DOF dynamics, where the beams are fixed to the tilting body."""
    agl = np.maximum(z - height(px, py), 0.5)
    S = (agl / cz)[:, None] * _F_GRID[None, :]
    f = (z[:, None] - S * cz[:, None]) - height((px[:, None] + S * dx[:, None]).ravel(), (py[:, None] + S * dy[:, None]).ravel()).reshape(S.shape)
    hit = f <= 0
    anyhit = hit.any(axis=1)
    first = np.where(anyhit, hit.argmax(axis=1), len(_F_GRID) - 1)
    rows = np.arange(len(S))
    hi = S[rows, first]
    lo = np.where(first > 0, S[rows, np.maximum(first - 1, 0)], 0.0)
    for _ in range(12):
        mid = 0.5 * (lo + hi)
        above = (z - mid * cz - height(px + mid * dx, py + mid * dy)) > 0
        lo = np.where(above, mid, lo)
        hi = np.where(above, hi, mid)
    return np.where(anyhit, 0.5 * (lo + hi), hi)


def _consensus_ok(zapp, var):''')

rep('''    res["success"] = np.zeros(n, dtype=bool)
    res["outcome"] = np.array(["flying"] * n, dtype=object)''', '''    res["success"] = np.zeros(n, dtype=bool)
    if dyn6 is not None:
        res["impact_tilt"], res["impact_rate"] = np.zeros(n), np.zeros(n)
        res["success_legacy"] = np.zeros(n, dtype=bool)
    dy = None                                       # 6-DOF state, created at the first step from the first thrust direction
    res["outcome"] = np.array(["flying"] * n, dtype=object)''')

rep('''    g_est = coarse.height(nav.x[:, 0], nav.x[:, 1]).astype(np.float64)
    s_hat = np.ones(n)''', '''    def foot(kb, s, ux, uy):
        """Horizontal offset of the point a beam of slant range s reaches, on the nominal geometry or (6-DOF) on the estimated attitude."""
        if dy is None:
            return s * st * ux, s * st * uy
        return s * DXE[:, kb], s * DYE[:, kb]

    g_est = coarse.height(nav.x[:, 0], nav.x[:, 1]).astype(np.float64)
    s_hat = np.ones(n)''')

rep('''        am = np.linalg.norm(a_cmd, axis=1)
        burn = mass * am / (veh.isp * G0) * DT
        fuel = np.maximum(0.0, fuel - burn * alive)
        acc = a_cmd + np.array([0, 0, -G])
        p_new = p + v * DT + 0.5 * acc * DT * DT
        v_new = v + acc * DT
''', '''        if dyn6 is None:
            am = np.linalg.norm(a_cmd, axis=1)
            burn = mass * am / (veh.isp * G0) * DT
            fuel = np.maximum(0.0, fuel - burn * alive)
            acc = a_cmd + np.array([0, 0, -G])
            p_new = p + v * DT + 0.5 * acc * DT * DT
            v_new = v + acc * DT
        else:
            if dy is None:
                am0 = np.linalg.norm(a_cmd, axis=1)
                dir0 = np.where((am0 > 1e-6)[:, None], a_cmd / np.maximum(am0, 1e-9)[:, None], np.array([0.0, 0.0, 1.0]))
                dy = _dyn6.Dyn6(dyn6, n, draws.seed, dir0)
            p_new, v_new, f_body, t_mean, rcs_kg = dy.step(p, v, a_cmd, mass, veh.tmax, alive & (fuel > 0.0), DT)
            fuel = np.maximum(0.0, fuel - (t_mean / (veh.isp * G0) * DT + rcs_kg) * alive)
''')
rep('''            ok = (res["impact_vz"][ci] <= 2.0) & (res["impact_vh"][ci] <= 1.5) & (res["impact_slope"][ci] <= 10.0) & (fuel[ci] > 0)
''', '''            ok = (res["impact_vz"][ci] <= 2.0) & (res["impact_vh"][ci] <= 1.5) & (res["impact_slope"][ci] <= 10.0) & (fuel[ci] > 0)
            if dy is not None:      # 6-DOF: the vehicle must also touch down upright and not spinning
                res["success_legacy"][ci] = ok
                res["impact_tilt"][ci], res["impact_rate"][ci] = dy.tilt_deg()[ci], dy.rate_dps()[ci]
                ok = ok & (res["impact_tilt"][ci] <= dyn6.tilt_land_max_deg) & (res["impact_rate"][ci] <= dyn6.rate_land_max_dps)
''')
rep('''        a_meas = a_cmd + draws.bias_true + 0.003 * draws.imu_g[:, k, :]
''', '''        if dy is None:
            a_meas = a_cmd + draws.bias_true + 0.003 * draws.imu_g[:, k, :]
        else:
            dy.estimate(k + 1, DT, alive)
            a_meas = dy.accel_world_meas(f_body, draws.bias_true, 0.003 * draws.imu_g[:, k, :])
''')
rep('''        r_true = agl_true
        r_hist[:, tt] = r_true''', '''        r_true = agl_true
        if dy is not None and not mb_mode:      # body-fixed beam: true slant range, converted to a vertical range with the ESTIMATED tilt
            Rt = dy.R_true()
            s_t1 = _slant_range_dir(truth.height, p[:, 0], p[:, 1], p[:, 2], -Rt[:, 0, 2], -Rt[:, 1, 2], np.maximum(Rt[:, 2, 2], 0.2))
            r_true = s_t1 * np.maximum(dy.R_est()[:, 2, 2], 0.2)
        r_hist[:, tt] = r_true''')

rep('''                dirs = [(np.cos(2 * np.pi * kb / Kb), np.sin(2 * np.pi * kb / Kb)) for kb in range(Kb)]
''', '''                dirs = [(np.cos(2 * np.pi * kb / Kb), np.sin(2 * np.pi * kb / Kb)) for kb in range(Kb)]
                if dy is not None:      # beams fixed to the body: world directions from the true (sensor) and estimated (filter) attitude
                    Bb = np.array([(st * ux_, st * uy_, -ct) for ux_, uy_ in dirs])
                    Dt = np.einsum("nij,kj->nki", dy.R_true()[idx], Bb)
                    De = np.einsum("nij,kj->nki", dy.R_est()[idx], Bb)
                    DXE, DYE, CZE = De[:, :, 0], De[:, :, 1], np.maximum(-De[:, :, 2], 0.2)
''')
rep('''                    s_t = _slant_range(truth.height, p[idx, 0], p[idx, 1], p[idx, 2], ux, uy, ct, st)
''', '''                    if dy is None:
                        s_t = _slant_range(truth.height, p[idx, 0], p[idx, 1], p[idx, 2], ux, uy, ct, st)
                    else:
                        s_t = _slant_range_dir(truth.height, p[idx, 0], p[idx, 1], p[idx, 2], Dt[:, kb, 0], Dt[:, kb, 1], np.maximum(-Dt[:, kb, 2], 0.2))
''')
rep('''                    s_terr_b = np.stack([stats.hstd(xi + s_meas[:, kb] * st * ux, yi + s_meas[:, kb] * st * uy, ellipse_k * sig_hi) ** 2
                                         for kb, (ux, uy) in enumerate(dirs)], axis=1)''', '''                    s_terr_b = np.stack([stats.hstd(xi + foot(kb, s_meas[:, kb], ux, uy)[0], yi + foot(kb, s_meas[:, kb], ux, uy)[1], ellipse_k * sig_hi) ** 2
                                         for kb, (ux, uy) in enumerate(dirs)], axis=1)''')
rep('''                zapp = np.zeros_like(s_meas)
                for kb, (ux, uy) in enumerate(dirs):
                    zapp[:, kb] = mapq(xi + s_meas[:, kb] * st * ux, yi + s_meas[:, kb] * st * uy, idx) + s_meas[:, kb] * ct
                var_z = (np.sqrt(R_gate_b) * ct) ** 2 + s_terr_b + world.map_sigma ** 2''', '''                zapp = np.zeros_like(s_meas)
                for kb, (ux, uy) in enumerate(dirs):
                    fxk, fyk = foot(kb, s_meas[:, kb], ux, uy)
                    zapp[:, kb] = mapq(xi + fxk, yi + fyk, idx) + s_meas[:, kb] * (ct if dy is None else CZE[:, kb])
                var_z = (np.sqrt(R_gate_b) * (ct if dy is None else CZE)) ** 2 + s_terr_b + world.map_sigma ** 2''')
rep('''                    for _ in range(3):      # predicted slant range from the map at the predicted footprint
                        s_p = np.clip((ze_i - mapq(xe_i + s_p * st * ux, ye_i + s_p * st * uy, idx)) / ct, 1.0, 1e5)
                    gxk, gyk = mapg(xe_i + s_p * st * ux, ye_i + s_p * st * uy, idx)
                    nu_k = s_meas[:, kb] - s_p
                    Dk = np.maximum(ct + st * (gxk * ux + gyk * uy), 0.1)''', '''                    ctk = ct if dy is None else CZE[:, kb]
                    for _ in range(3):      # predicted slant range from the map at the predicted footprint
                        fxp, fyp = foot(kb, s_p, ux, uy)
                        s_p = np.clip((ze_i - mapq(xe_i + fxp, ye_i + fyp, idx)) / ctk, 1.0, 1e5)
                    fxp, fyp = foot(kb, s_p, ux, uy)
                    gxk, gyk = mapg(xe_i + fxp, ye_i + fyp, idx)
                    nu_k = s_meas[:, kb] - s_p
                    Dk = np.maximum(ct + st * (gxk * ux + gyk * uy), 0.1) if dy is None else np.maximum(CZE[:, kb] + gxk * DXE[:, kb] + gyk * DYE[:, kb], 0.1)''')
rep('''    res["est_off_x"], res["est_off_y"] = est_off[:, 0].copy(), est_off[:, 1].copy()
    return res''', '''    res["est_off_x"], res["est_off_y"] = est_off[:, 0].copy(), est_off[:, 1].copy()
    if dy is not None:
        res["tilt_max"] = dy.tilt_max.copy()
        res["att_err_rms_deg"] = np.sqrt(dy.att_sq / np.maximum(dy.att_n, 1.0))
        res["rcs_fuel"] = dy.rcs_used.copy()
    return res''')
open(p, "w", encoding="utf-8").write(s)
print("ok")
