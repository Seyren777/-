"""เฉลยโจทย์ทรัสหลังคา Howe — ใช้ตัวคำนวณจาก ../truss_fem.py"""
import contextlib, importlib.util, io, math, os
here = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("t", os.path.join(here, "..", "truss_fem.py"))
t = importlib.util.module_from_spec(spec)
with contextlib.redirect_stdout(io.StringIO()):
    spec.loader.exec_module(t)

E = 2.04e6
ys = {1: 60.0, 2: 120.0, 3: 180.0, 4: 120.0, 5: 60.0}
nodes = {f"b{i}": (200.0*i, 0.0) for i in range(7)}
nodes.update({f"t{i}": (200.0*i, ys[i]) for i in range(1, 6)})
A_TOP, A_BOT, A_WEB = 12.0, 9.6, 4.8
members = [(f"B{i+1}", f"b{i}", f"b{i+1}", A_BOT) for i in range(6)]
top = ["b0", "t1", "t2", "t3", "t4", "t5", "b6"]
members += [(f"T{i+1}", top[i], top[i+1], A_TOP) for i in range(6)]
members += [(f"V{i}", f"b{i}", f"t{i}", A_WEB) for i in range(1, 6)]
members += [("D1", "b1", "t2", A_WEB), ("D2", "b2", "t3", A_WEB),
            ("D3", "b4", "t3", A_WEB), ("D4", "b5", "t4", A_WEB)]
supports = {"b0": (True, True), "b6": (False, True)}
loads = {f"t{i}": (0.0, -600.0) for i in range(1, 6)}
loads["t3"] = (400.0, -600.0)

F, D, R = t.solve(nodes, members, supports, loads, E)
print("แรงปฏิกิริยา (kg):")
for n, (rx, ry) in R.items():
    print(f"  {n}: Rx = {rx:9.1f}  Ry = {ry:9.1f}")
print("\nแรงในชิ้นส่วน (kg, + ดึง / − อัด):")
for name, *_ in members:
    f = F[name]; s = "ดึง" if f > 0.05 else "อัด" if f < -0.05 else "ศูนย์"
    print(f"  {name:3s} {f:10.1f}  {s}")
n_max = min(D, key=lambda n: D[n][1])
print(f"\nการแอ่นตัวลงมากสุด: จุด {n_max}  dy = {D[n_max][1]:.4f} cm")
print(f"การเลื่อนแนวนอนที่ลูกกลิ้ง b6: dx = {D['b6'][0]:.4f} cm")
print(f"ยอด t3: dx = {D['t3'][0]:.4f} cm  dy = {D['t3'][1]:.4f} cm")
