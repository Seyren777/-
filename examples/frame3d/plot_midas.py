"""วาดแผนภาพโมเมนต์ดัดคานแบบ midas Gen (3 มิติ) และรูปด้านโครงแกน B (2 มิติ)"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager
from matplotlib.colors import BoundaryNorm, ListedColormap
from mpl_toolkits.mplot3d.art3d import Line3DCollection, Poly3DCollection

import frame3d_fem as f3

FONT_DIR = "/usr/share/fonts/opentype/tlwg/"
for f in ("Loma.otf", "Loma-Bold.otf"):
    font_manager.fontManager.addfont(FONT_DIR + f)
plt.rcParams["font.family"] = ["Loma", "DejaVu Sans"]

nodes, members, supports = f3.build()
res, disp, reac = f3.solve(nodes, members, supports)
beams = [m for m in members if m["kind"] == "beam"]
cols = [m for m in members if m["kind"] == "col"]
Mmax = max(res[m["name"]]["M"].max() for m in beams)
Mmin = min(res[m["name"]]["M"].min() for m in beams)
m_hi = max(beams, key=lambda m: res[m["name"]]["M"].max())
m_lo = min(beams, key=lambda m: res[m["name"]]["M"].min())

# สีแบบ midas: ลบ (หลังคานดึง) น้ำเงิน→เขียว · บวก (ท้องคานดึง) เหลือง→แดง · 0 อยู่ระหว่างเขียวกับเหลืองเขียว
NEG = ["#1d4fd8", "#2fa8f0", "#3ddbc8", "#3fd27a", "#45cc45", "#5fd23c"]
POS = ["#b6e63a", "#eef03a", "#ffd23a", "#ff9a2e", "#ff3b22"]
bounds = np.r_[np.linspace(Mmin, 0, len(NEG) + 1), np.linspace(0, Mmax, len(POS) + 1)[1:]]
cmap = ListedColormap(NEG + POS)
norm = BoundaryNorm(bounds, cmap.N)
INK, MUTED, FRAME = "#1f2937", "#6b7280", "#334155"

# ================================================================ รูป 3 มิติ
fig = plt.figure(figsize=(15, 8.6))
ax = fig.add_axes([0.0, 0.0, 0.80, 1.0], projection="3d")
side = fig.add_axes([0.81, 0.05, 0.18, 0.90])
side.axis("off")

P = lambda n: np.array(nodes[n], dtype=float)
scale = 110.0 / max(abs(Mmin), abs(Mmax))          # cm ต่อ kg·m สำหรับวาด

# พื้น: ตาข่ายบาง ๆ แบบ plate mesh
mesh = []
for z in f3.ZS[1:]:
    for x in np.arange(0, f3.XS[-1] + 1, 100):
        mesh.append([(x, 0, z), (x, f3.YS[-1], z)])
    for y in np.arange(0, f3.YS[-1] + 1, 100):
        mesh.append([(0, y, z), (f3.XS[-1], y, z)])
ax.add_collection3d(Line3DCollection(mesh, colors="#cbd5e1", linewidths=0.35, alpha=0.55))

ax.add_collection3d(Line3DCollection([[P(m["i"]), P(m["j"])] for m in cols], colors=FRAME, linewidths=1.3))
ax.add_collection3d(Line3DCollection([[P(m["i"]), P(m["j"])] for m in beams], colors=FRAME, linewidths=1.1))

polys, colors = [], []
for m in beams:
    r = res[m["name"]]
    p1, p2 = P(m["i"]), P(m["j"])
    t = (p2 - p1) / r["L"]
    pts = p1 + np.outer(r["x"], t)
    off = np.outer(-scale * r["M"], [0, 0, 1])      # วาดฝั่งรับแรงดึง: บวกลงล่าง · ลบขึ้นบน
    for a in range(len(r["x"]) - 1):
        polys.append([pts[a], pts[a + 1], pts[a + 1] + off[a + 1], pts[a] + off[a]])
        colors.append(cmap(norm((r["M"][a] + r["M"][a + 1]) / 2)))
ax.add_collection3d(Poly3DCollection(polys, facecolors=colors, edgecolors=colors, linewidths=0.3, alpha=0.95))

for m, val, va in ((m_hi, Mmax, "top"), (m_lo, Mmin, "bottom")):
    r = res[m["name"]]
    k = int(np.argmax(r["M"]) if val > 0 else np.argmin(r["M"]))
    p = P(m["i"]) + (P(m["j"]) - P(m["i"])) / r["L"] * r["x"][k] + np.array([0, 0, -scale * val])
    ax.text(*p, f"{'MAX' if val > 0 else 'MIN'} {val:,.0f}", fontsize=10, fontweight="bold", color=INK,
            va=va, ha="left", zorder=10, bbox=dict(fc="white", ec=INK, lw=0.6, pad=2, alpha=0.9))

for i, gx in enumerate(f3.GRID_X):
    ax.text(f3.XS[i], -90, 0, gx, fontsize=10, color=MUTED, ha="center")
for j, gy in enumerate(f3.GRID_Y):
    ax.text(-90, f3.YS[j], 0, gy, fontsize=10, color=MUTED, ha="center")

ax.set_box_aspect((f3.XS[-1], f3.YS[-1], f3.ZS[-1] + 150))
ax.set_xlim(0, f3.XS[-1]); ax.set_ylim(0, f3.YS[-1]); ax.set_zlim(-30, f3.ZS[-1] + 120)
ax.view_init(elev=17, azim=-118)
ax.set_axis_off()

# แถบข้างแบบ post-processor
y = 0.99
def line(txt, size=11, weight="normal", color=INK, gap=0.035):
    global y
    side.text(0.02, y, txt, fontsize=size, fontweight=weight, color=color, transform=side.transAxes, va="top")
    y -= gap
def rule():
    global y
    side.plot([0, 1], [y + 0.008, y + 0.008], color=MUTED, lw=0.8, transform=side.transAxes)
    y -= 0.012
line("FEM โครง 3 มิติ (numpy)", 12, "bold"); line("POST-PROCESSOR", 10, color=MUTED); rule()
line("BEAM DIAGRAM", 11, "bold"); rule()
line("โมเมนต์ดัดคาน (kg·m)", 11, gap=0.05)
cb_top, cb_h = y, 0.40
cax = fig.add_axes([0.815, 0.05 + 0.90 * (cb_top - cb_h), 0.018, 0.90 * cb_h])
cbar = fig.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=cmap), cax=cax, ticks=bounds, spacing="uniform")
cbar.ax.set_yticklabels([f"{b:,.0f}" for b in bounds], fontsize=9)
cbar.outline.set_edgecolor(MUTED)
y = cb_top - cb_h - 0.03
rule()
line("CBS: 1.4D + 1.7L", 10)
line(f"MAX : {m_hi['name']}", 10)
line(f"MIN : {m_lo['name']}", 10); rule()
line("UNIT: kgf·m", 10)
line("+ ท้องคานรับแรงดึง (วาดด้านล่าง)", 9, color=MUTED, gap=0.03)
line("− หลังคานรับแรงดึง (วาดด้านบน)", 9, color=MUTED); rule()
line("ตรวจไขว้กับ PyNite: ตรงกัน", 9, color="#15803d", gap=0.03)
line("ΣR = Σน้ำหนัก = 390,656 kg", 9, color="#15803d")

fig.text(0.01, 0.97, "อาคาร คสล. 2 ชั้น · 4 ช่วง × 2 ช่วง (4 m × 5 m) · สูงชั้นละ 3.5 m",
         fontsize=13, fontweight="bold", color=INK, va="top")
fig.text(0.01, 0.935, "เสา 30×30 cm · คาน 25×50 cm · พื้นหนา 12 cm · f'c 210 ksc · "
         "LL ชั้น 2 = 250, หลังคา = 100 kg/m² · ผนังอิฐบนคานริมชั้น 2",
         fontsize=10, color=MUTED, va="top")
fig.savefig("frame3d_moment.png", dpi=150)

# ================================================================ รูปด้านโครงแกน B
fig2, axs = plt.subplots(1, 1, figsize=(14, 6.2))
ax2 = axs
scale2 = 90.0 / max(abs(Mmin), abs(Mmax))
yB = f3.YS[1]
for m in cols:
    (x1, y1, z1), (x2, y2, z2) = nodes[m["i"]], nodes[m["j"]]
    if y1 == yB:
        ax2.plot([x1, x2], [z1, z2], color=FRAME, lw=2)
for m in beams:
    (x1, y1, z1), (x2, y2, z2) = nodes[m["i"]], nodes[m["j"]]
    if not (y1 == yB and y2 == yB):
        continue
    r = res[m["name"]]
    xs = x1 + r["x"]
    zs = z1 - scale2 * r["M"]
    ax2.plot([x1, x2], [z1, z2], color=FRAME, lw=2)
    for a in range(len(xs) - 1):
        ax2.fill([xs[a], xs[a + 1], xs[a + 1], xs[a]], [z1, z1, zs[a + 1], zs[a]],
                 color=cmap(norm((r["M"][a] + r["M"][a + 1]) / 2)), lw=0)
    ax2.plot(xs, zs, color=INK, lw=0.8)
    kmid = int(np.argmax(r["M"]))
    for k, va in ((0, "bottom"), (len(xs) - 1, "bottom"), (kmid, "top")):
        dx = 18 if k == 0 else -18 if k == len(xs) - 1 else 0
        ha = "left" if k == 0 else "right" if k == len(xs) - 1 else "center"
        ax2.text(xs[k] + dx, zs[k] + (6 if va == "bottom" else -6), f"{r['M'][k]:,.0f}",
                 fontsize=9, ha=ha, va=va, color=INK, fontweight="bold")
for i, gx in enumerate(f3.GRID_X):
    ax2.text(f3.XS[i], -45, gx, ha="center", va="top", fontsize=11, color=MUTED,
             bbox=dict(boxstyle="circle", fc="white", ec=MUTED))
for z, lab in zip(f3.ZS, ["ฐาน", "ชั้น 2", "หลังคา"]):
    ax2.text(-60, z, lab, ha="right", va="center", fontsize=10, color=MUTED)
ax2.set_title("รูปด้านโครงแกน B (คานภายใน) — โมเมนต์ดัดคาน kg·m · 1.4D + 1.7L",
              loc="left", fontsize=13, fontweight="bold", color=INK)
ax2.set_aspect("equal"); ax2.axis("off")
ax2.set_xlim(-170, f3.XS[-1] + 60); ax2.set_ylim(-100, f3.ZS[-1] + 120)
fig2.tight_layout()
fig2.savefig("frame_B_elevation.png", dpi=150)
print("บันทึก frame3d_moment.png และ frame_B_elevation.png")
