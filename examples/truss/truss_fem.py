"""วิเคราะห์โครงทรัส 2 มิติด้วยวิธี direct stiffness (FEM แบบ truss element)

หน่วย: kg, cm, ksc ตลอดทั้งไฟล์
แรงในชิ้นส่วน: + = ดึง, − = อัด

ตัวอย่าง: ทรัสแบบ Pratt ช่วง 12 m (6 ช่อง × 2 m) สูง 2 m
รองรับแบบหมุดที่ปลายซ้าย และลูกกลิ้งที่ปลายขวา
น้ำหนักจุด 1,000 kg ที่จุดต่อคอร์ดล่างทั้ง 5 จุด
"""
import math

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
import numpy as np

# ---------------------------------------------------------------- ข้อมูลนำเข้า
E = 2.04e6          # ksc (เหล็กรูปพรรณ)
PANEL = 200.0       # cm
H = 200.0           # cm
N_PANEL = 6
P = 1000.0          # kg ต่อจุด

A_CHORD = 9.6       # cm²  เช่น 2L-50×50×5
A_WEB = 4.8         # cm²  เช่น L-50×50×5

# จุดต่อ: b0..b6 คอร์ดล่าง, t1..t5 คอร์ดบน
nodes = {}
for i in range(N_PANEL + 1):
    nodes[f"b{i}"] = (i * PANEL, 0.0)
for i in range(1, N_PANEL):
    nodes[f"t{i}"] = (i * PANEL, H)

members = []  # (ชื่อ, จุดเริ่ม, จุดปลาย, พื้นที่)
for i in range(N_PANEL):
    members.append((f"B{i+1}", f"b{i}", f"b{i+1}", A_CHORD))            # คอร์ดล่าง
for i in range(1, N_PANEL - 1):
    members.append((f"T{i}", f"t{i}", f"t{i+1}", A_CHORD))              # คอร์ดบน
members.append(("E1", "b0", "t1", A_CHORD))                             # ขาปลาย
members.append(("E2", f"b{N_PANEL}", f"t{N_PANEL-1}", A_CHORD))
for i in range(1, N_PANEL):
    members.append((f"V{i}", f"b{i}", f"t{i}", A_WEB))                  # ตั้ง
mid = N_PANEL // 2
for i in range(1, mid):
    members.append((f"D{i}", f"t{i}", f"b{i+1}", A_WEB))                # ทแยงซ้าย
for i in range(mid + 1, N_PANEL):
    members.append((f"D{i-1}", f"t{i}", f"b{i-1}", A_WEB))              # ทแยงขวา

supports = {"b0": (True, True), f"b{N_PANEL}": (False, True)}           # (ux, uy) ยึดหรือไม่
loads = {f"b{i}": (0.0, -P) for i in range(1, N_PANEL)}


# ---------------------------------------------------------------- ตัวคำนวณ
def solve(nodes, members, supports, loads, E):
    names = list(nodes)
    idx = {n: k for k, n in enumerate(names)}
    ndof = 2 * len(names)
    K = np.zeros((ndof, ndof))
    F = np.zeros(ndof)

    geo = []
    for name, a, b, A in members:
        (x1, y1), (x2, y2) = nodes[a], nodes[b]
        L = math.hypot(x2 - x1, y2 - y1)
        c, s = (x2 - x1) / L, (y2 - y1) / L
        k = E * A / L * np.array([[c*c, c*s, -c*c, -c*s],
                                  [c*s, s*s, -c*s, -s*s],
                                  [-c*c, -c*s, c*c, c*s],
                                  [-c*s, -s*s, c*s, s*s]])
        dofs = [2*idx[a], 2*idx[a] + 1, 2*idx[b], 2*idx[b] + 1]
        K[np.ix_(dofs, dofs)] += k
        geo.append((name, dofs, L, c, s, A))

    for n, (fx, fy) in loads.items():
        F[2*idx[n]] += fx
        F[2*idx[n] + 1] += fy

    fixed = [2*idx[n] + d for n, fix in supports.items() for d in (0, 1) if fix[d]]
    free = [d for d in range(ndof) if d not in fixed]

    Kff = K[np.ix_(free, free)]
    if np.linalg.matrix_rank(Kff) < len(free):
        raise ValueError("โครงสร้างไม่มั่นคง (unstable) — ตรวจจุดรองรับหรือชิ้นส่วนที่ขาด")

    u = np.zeros(ndof)
    u[free] = np.linalg.solve(Kff, F[free])
    R = K @ u - F

    forces = {}
    for name, dofs, L, c, s, A in geo:
        ue = u[dofs]
        forces[name] = E * A / L * np.dot([-c, -s, c, s], ue)
    disp = {n: (u[2*idx[n]], u[2*idx[n] + 1]) for n in names}
    reactions = {n: (R[2*idx[n]], R[2*idx[n] + 1]) for n in supports}
    return forces, disp, reactions


forces, disp, reactions = solve(nodes, members, supports, loads, E)

# ---------------------------------------------------------------- ตรวจผลกับวิธีมือ
total = P * (N_PANEL - 1)
Ry_left = reactions["b0"][1]
Ry_right = reactions[f"b{N_PANEL}"][1]
checks = [
    ("ผลรวมแรงปฏิกิริยา = น้ำหนักรวม", Ry_left + Ry_right, total),
    ("แรงปฏิกิริยาซ้าย = ครึ่งหนึ่ง (สมมาตร)", Ry_left, total / 2),
    ("ขาปลาย E1 = −R/sin45°", forces["E1"], -Ry_left * math.sqrt(2)),
    ("คอร์ดล่าง B3 (ตัดหน้าตัด, โมเมนต์รอบ t2)", forces["B3"], (Ry_left*2*PANEL - P*PANEL) / H),
    ("คอร์ดบน T2 (ตัดหน้าตัด, โมเมนต์รอบ b3)", forces["T2"], -(Ry_left*3*PANEL - P*(2*PANEL + PANEL)) / H),
]
print("=== ตรวจผลกับวิธีมือ ===")
for label, fem, hand in checks:
    ok = abs(fem - hand) < 1e-6 * max(1.0, abs(hand))
    print(f"{'ผ่าน' if ok else 'ไม่ผ่าน':6s} {label:42s} FEM {fem:10.1f}  มือ {hand:10.1f}")
    assert ok, label

print("\n=== แรงในชิ้นส่วน (kg) ===")
for name, *_ in members:
    f = forces[name]
    state = "ดึง" if f > 1e-6 else ("อัด" if f < -1e-6 else "ศูนย์")
    print(f"{name:4s} {f:10.1f}  {state}")

dy_max = min(d[1] for d in disp.values())
print(f"\nการแอ่นตัวสูงสุด = {abs(dy_max):.3f} cm  (L/{N_PANEL*PANEL/abs(dy_max):.0f})")

# ---------------------------------------------------------------- วาดรูป
FONT_DIR = "/usr/share/fonts/opentype/tlwg/"
for f in ("Loma.otf", "Loma-Bold.otf"):
    font_manager.fontManager.addfont(FONT_DIR + f)
FAMILY = ["Loma", "DejaVu Sans"]  # DejaVu เติมตัวที่ Loma ไม่มี เช่น δ − ⁶
plt.rcParams["font.family"] = FAMILY
thai = font_manager.FontProperties(family=FAMILY)
thai_b = font_manager.FontProperties(family=FAMILY, weight="bold")
TENSION, COMPRESSION, ZERO, INK, MUTED = "#2563eb", "#dc2626", "#9ca3af", "#1f2937", "#6b7280"

fig, axes = plt.subplots(3, 1, figsize=(11, 12.5))
span = N_PANEL * PANEL


def frame(ax, title):
    ax.set_title(title, fontproperties=thai_b, fontsize=14, loc="left", color=INK)
    ax.set_aspect("equal")
    ax.set_xlim(-120, span + 120)
    ax.set_ylim(-170, H + 90)
    ax.axis("off")


def draw_supports(ax):
    x, y = nodes["b0"]
    ax.add_patch(plt.Polygon([[x, y], [x-25, y-40], [x+25, y-40]], fc="white", ec=INK, lw=1.5))
    ax.plot([x-35, x+35], [y-45, y-45], color=INK, lw=1.5)
    x, y = nodes[f"b{N_PANEL}"]
    ax.add_patch(plt.Polygon([[x, y], [x-25, y-34], [x+25, y-34]], fc="white", ec=INK, lw=1.5))
    for dx in (-14, 14):
        ax.add_patch(plt.Circle((x+dx, y-40), 6, fc="white", ec=INK, lw=1.2))
    ax.plot([x-35, x+35], [y-48, y-48], color=INK, lw=1.5)


# (1) แบบจำลองและน้ำหนัก
ax = axes[0]
frame(ax, "1) แบบจำลองและน้ำหนักบรรทุก")
for name, a, b, A in members:
    (x1, y1), (x2, y2) = nodes[a], nodes[b]
    ax.plot([x1, x2], [y1, y2], color=INK, lw=2.4 if A == A_CHORD else 1.4)
    ax.text((x1+x2)/2, (y1+y2)/2, name, fontsize=8, color=MUTED, ha="center", va="center",
            bbox=dict(fc="white", ec="none", pad=0.6))
for n, (x, y) in nodes.items():
    ax.plot(x, y, "o", ms=6, mfc="white", mec=INK, mew=1.4)
for n, (fx, fy) in loads.items():
    x, y = nodes[n]
    ax.annotate("", xy=(x, y - 95), xytext=(x, y - 10),
                arrowprops=dict(arrowstyle="-|>", color="#b45309", lw=1.8))
    ax.text(x, y - 115, f"{P:,.0f} kg", ha="center", fontsize=9, color="#b45309")
draw_supports(ax)
ax.text(0, H + 55, f"ช่วง {span/100:.0f} m · สูง {H/100:.0f} m · คอร์ด A = {A_CHORD} cm² · "
        f"ตั้ง/ทแยง A = {A_WEB} cm² · E = 2.04×10⁶ ksc",
        fontproperties=thai, fontsize=10, color=MUTED)

# (2) แรงดึง/แรงอัด
ax = axes[1]
frame(ax, "2) แรงในชิ้นส่วน (kg)")
fmax = max(abs(f) for f in forces.values())
for name, a, b, A in members:
    (x1, y1), (x2, y2) = nodes[a], nodes[b]
    f = forces[name]
    color = TENSION if f > 1e-6 else COMPRESSION if f < -1e-6 else ZERO
    ax.plot([x1, x2], [y1, y2], color=color, lw=1.5 + 5 * abs(f) / fmax, solid_capstyle="round")
    label = "0" if abs(f) < 1e-6 else f"{f:+,.0f}"
    ax.text((x1+x2)/2, (y1+y2)/2, label, fontsize=8.5, ha="center", va="center", color=color,
            fontweight="bold", bbox=dict(fc="white", ec=color, lw=0.8, pad=1.5, boxstyle="round"))
for n, (x, y) in nodes.items():
    ax.plot(x, y, "o", ms=5, mfc="white", mec=INK, mew=1.2)
draw_supports(ax)
for n, (rx, ry) in reactions.items():
    x, y = nodes[n]
    ax.text(x, y - 85, f"R = {ry:,.0f} kg", ha="center", fontsize=9, color=INK)
ax.plot([0, 70], [H + 55, H + 55], color=TENSION, lw=5)
ax.text(85, H + 55, "ดึง (+)", fontproperties=thai, fontsize=10, va="center", color=TENSION)
ax.plot([230, 300], [H + 55, H + 55], color=COMPRESSION, lw=5)
ax.text(315, H + 55, "อัด (−)", fontproperties=thai, fontsize=10, va="center", color=COMPRESSION)
ax.plot([460, 530], [H + 55, H + 55], color=ZERO, lw=2)
ax.text(545, H + 55, "แรงเป็นศูนย์ · ความหนาเส้นตามขนาดแรง", fontproperties=thai,
        fontsize=10, va="center", color=MUTED)

# (3) รูปการเสียรูป
ax = axes[2]
scale = 40.0 / abs(dy_max)
frame(ax, f"3) รูปการเสียรูป (ขยาย ×{scale:,.0f})")
for name, a, b, A in members:
    (x1, y1), (x2, y2) = nodes[a], nodes[b]
    ax.plot([x1, x2], [y1, y2], color=ZERO, lw=1, ls="--")
    (u1, v1), (u2, v2) = disp[a], disp[b]
    ax.plot([x1 + scale*u1, x2 + scale*u2], [y1 + scale*v1, y2 + scale*v2], color=INK, lw=2)
for n, (x, y) in nodes.items():
    u, v = disp[n]
    ax.plot(x + scale*u, y + scale*v, "o", ms=5, mfc="white", mec=INK, mew=1.2)
draw_supports(ax)
xm, ym = nodes[f"b{mid}"]
ax.annotate(f"δ สูงสุด = {abs(dy_max):.3f} cm\n(L/{span/abs(dy_max):,.0f})",
            xy=(xm, ym + scale*disp[f'b{mid}'][1]), xytext=(xm + 170, -140),
            fontproperties=thai, fontsize=10, color=INK,
            arrowprops=dict(arrowstyle="->", color=INK))
ax.text(0, H + 55, "เส้นประ = รูปเดิม · เส้นทึบ = รูปหลังรับน้ำหนัก",
        fontproperties=thai, fontsize=10, color=MUTED)

plt.tight_layout()
out = __file__.replace(".py", ".png")
plt.savefig(out, dpi=150, bbox_inches="tight")
print(f"\nบันทึกรูป: {out}")
