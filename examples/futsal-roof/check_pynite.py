"""ตรวจตัวคำนวณ 2 มิติของ roof_model.py ไขว้กับ PyNite (3 มิติ ล็อกนอกระนาบ)"""
import numpy as np
from Pynite import FEModel3D

import design
import roof_model as rm

sizes = design.select()[0]
nodes, members, supports, cases, case_res, combos, W = rm.run_all(sizes)

worst = {}
for case in ("D", "L", "W2", "E"):
    nodal, dist = cases[case]
    mdl = FEModel3D()
    mdl.add_material("S", rm.E, rm.E / 2.6, 0.3, 0.0)
    for n, (x, z) in nodes.items():
        mdl.add_node(n, x, z, 0.0)
        fixed = n in supports
        mdl.def_support(n, fixed, fixed, True, True, True, fixed)
    for m in members:
        s = m["sec"]
        mdl.add_section(m["name"], s["A"], s["Ix"], s["Ix"], s["Ix"])
        mdl.add_member(m["name"], m["i"], m["j"], "S", m["name"])
        if m["kind"] == "truss":
            mdl.def_releases(m["name"], Ryi=True, Rzi=True, Ryj=True, Rzj=True)
        if m["name"] in dist:
            mdl.add_member_dist_load(m["name"], "FX", -dist[m["name"]], -dist[m["name"]], case=case)
    for n, (fx, fz) in nodal.items():
        if fx:
            mdl.add_node_load(n, "FX", fx, case=case)
        if fz:
            mdl.add_node_load(n, "FY", fz, case=case)
    mdl.add_load_combo(case, {case: 1.0})
    mdl.analyze(check_statics=False)

    res, disp, reac = case_res[case]
    dN = max(abs(res[m["name"]]["N"] - mdl.members[m["name"]].axial(res[m["name"]]["L"] / 2, case) * -1)
             for m in members)
    dN2 = max(abs(res[m["name"]]["N"] + mdl.members[m["name"]].axial(res[m["name"]]["L"] / 2, case) * -1)
              for m in members)
    dU = max(np.hypot(disp[n][0] - mdl.nodes[n].DX[case], disp[n][1] - mdl.nodes[n].DY[case]) for n in nodes)
    dR = max(abs(reac[n][1] - mdl.nodes[n].RxnFY[case]) + abs(reac[n][0] - mdl.nodes[n].RxnFX[case])
             for n in supports)
    Mo = np.array([np.abs(res[m["name"]]["M"]).max() for m in members if m["kind"] == "frame"])
    Mp = np.array([max(abs(mdl.members[m["name"]].max_moment("Mz", case)),
                       abs(mdl.members[m["name"]].min_moment("Mz", case)))
                   for m in members if m["kind"] == "frame"])
    Nmax = max(abs(res[m["name"]]["N"]) for m in members)
    print(f"{case:3s} การเคลื่อนตัวต่าง {dU:.1e} cm · แรงปฏิกิริยาต่าง {dR:.1e} kg · "
          f"แรงตามแกนต่าง {min(dN, dN2):.1e} kg (สูงสุด {Nmax:,.0f}) · |M| สูงสุดต่าง {np.abs(Mo - Mp).max()/100:.1e} kg·m")
