"""ตรวจผลของ frame3d_fem.py ไขว้กับ PyNite (ไลบรารี FEM โครง 3 มิติ, MIT)

PyNite ใช้แกน Y เป็นแนวดิ่ง จึงแปลงพิกัด (x, y, z) ของเรา → (X, Y, Z) = (x, z, y)
"""
import numpy as np
from Pynite import FEModel3D

import frame3d_fem as f3

nodes, members, supports = f3.build()
res, disp, reac = f3.solve(nodes, members, supports)

model = FEModel3D()
model.add_material("RC", f3.E, f3.G, 0.2, 0.0)
for n, (x, y, z) in nodes.items():
    model.add_node(n, x, z, y)
for m in members:
    A, Iz, Iy, J = m["sec"]
    model.add_section(m["name"], A, Iy, Iz, J)
    model.add_member(m["name"], m["i"], m["j"], "RC", m["name"])
    for s0, s1, q0, q1 in m["loads"]:
        if s1 > s0:
            model.add_member_dist_load(m["name"], "FY", -q0, -q1, s0, s1, case="U")
for n in supports:
    model.def_support(n, True, True, True, True, True, True)
model.add_load_combo("U", {"U": 1.0})
model.analyze(check_statics=False)

d_ours = np.array([disp[n][2] for n in nodes])
d_pyn = np.array([model.nodes[n].DY["U"] for n in nodes])
r_ours = np.array([reac[n][2] for n in supports])
r_pyn = np.array([model.nodes[n].RxnFY["U"] for n in supports])

m_ours, m_pyn = [], []
for m in members:
    if m["kind"] != "beam":
        continue
    mem = model.members[m["name"]]
    L = res[m["name"]]["L"]
    for x in (0.0, L / 2, L):
        m_ours.append(np.interp(x, res[m["name"]]["x"], res[m["name"]]["M"]))
        m_pyn.append(mem.moment("Mz", x, "U") / 100)
m_ours, m_pyn = np.array(m_ours), np.array(m_pyn)
sign = np.sign(np.dot(m_ours, m_pyn))               # อนุสัญญาเครื่องหมายของ PyNite อาจกลับด้าน

print(f"การแอ่นตัวดิ่งของจุดต่อ   ต่างสูงสุด {np.abs(d_ours - d_pyn).max():.2e} cm   (ค่าสูงสุด {np.abs(d_ours).max():.4f} cm)")
print(f"แรงปฏิกิริยาดิ่ง          ต่างสูงสุด {np.abs(r_ours - r_pyn).max():.2e} kg   (ค่าสูงสุด {r_ours.max():,.0f} kg)")
print(f"โมเมนต์คาน (หัว-กลาง-ท้าย) ต่างสูงสุด {np.abs(m_ours - sign * m_pyn).max():.2f} kg·m (ค่าสูงสุด {np.abs(m_ours).max():,.0f} kg·m)")
