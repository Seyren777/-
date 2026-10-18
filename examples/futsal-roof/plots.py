"""รูปประกอบ: รูปด้านโครง + ขนาดหน้าตัด · แรงดึง/อัด · การเสียรูป · ภาพรวม 3 มิติ"""
import math

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager
from mpl_toolkits.mplot3d.art3d import Line3DCollection

import design
import extras
import roof_model as rm

import os
FONT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")
for f in ("Sarabun-Regular.ttf", "Sarabun-Bold.ttf"):
    font_manager.fontManager.addfont(os.path.join(FONT_DIR, f))
plt.rcParams["font.family"] = ["Sarabun", "DejaVu Sans"]

INK, MUTED, GRID = "#1f2937", "#6b7280", "#d1d5db"
TENSION, COMPRESSION = "#2563eb", "#dc2626"
GROUP_COLOR = {"TC": "#0f766e", "BC": "#7c3aed", "WEB": "#64748b", "COL": "#b45309"}
GROUP_NAME = {"TC": "คอร์ดบน", "BC": "คอร์ดล่าง", "WEB": "ตั้ง/ทแยง", "COL": "เสา"}

sizes, nodes, members, supports, cases, case_res, combos, W, rows, defl = design.select()
P = {n: np.array(xy) / 100 for n, xy in nodes.items()}          # m
dcr_by_group = {g: max(r["dcr"] for r in rows if r["group"] == g) for g in GROUP_NAME}


def frame_axes(ax, title):
    ax.set_title(title, loc="left", fontsize=13, fontweight="bold", color=INK)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_xlim(-2.6, 20.2)


def ground(ax):
    ax.plot([-1.5, 19.5], [0, 0], color=MUTED, lw=1)
    for x in (0, 18):
        ax.add_patch(plt.Rectangle((x - 0.35, -0.25), 0.7, 0.25, fc="#e5e7eb", ec=MUTED, lw=0.8))


# ---------------------------------------------------------------- 1) รูปด้านและหน้าตัด
fig, ax = plt.subplots(figsize=(14, 7.6))
frame_axes(ax, "รูปด้านโครงหลังคาภายใน (ทุก 4.5 m × 7 โครง) — หน้าตัดที่เลือก")
ground(ax)
for m in members:
    a, b = P[m["i"]], P[m["j"]]
    ax.plot(*zip(a, b), color=GROUP_COLOR[m["group"]], lw={"COL": 5, "TC": 2.6, "BC": 2.6, "WEB": 1.1}[m["group"]],
            solid_capstyle="round")
for i in range(rm.N_PANEL + 1):
    x, z = P[f"t{i}"]
    ax.plot(x, z + 0.07, marker="s", ms=4, color="#334155")
y0 = 9.75
for k, g in enumerate(("TC", "BC", "WEB", "COL")):
    ax.plot([0.2 + 4.6 * k, 0.9 + 4.6 * k], [y0, y0], color=GROUP_COLOR[g], lw=5)
    ax.text(1.05 + 4.6 * k, y0, f"{GROUP_NAME[g]}  {sizes[g]}\nDCR สูงสุด {dcr_by_group[g]:.2f}",
            va="center", fontsize=10, color=INK)
ax.text(9, 7.2, "■ แป " + extras.purlin()[0] + " ทุกจุดต่อคอร์ดบน (≈ 1.03 m)",
        ha="center", fontsize=9.5, color=MUTED)


def dim_h(x1, x2, y, label):
    ax.annotate("", xy=(x1, y), xytext=(x2, y), arrowprops=dict(arrowstyle="<->", color=MUTED, lw=0.9))
    ax.text((x1 + x2) / 2, y - 0.12, label, ha="center", va="top", fontsize=10, color=INK)


def dim_v(x, y1, y2, label, side="left"):
    ax.annotate("", xy=(x, y1), xytext=(x, y2), arrowprops=dict(arrowstyle="<->", color=MUTED, lw=0.9))
    ax.text(x - 0.12 if side == "left" else x + 0.12, (y1 + y2) / 2, label, ha="right" if side == "left" else "left",
            va="center", fontsize=10, color=INK)


dim_h(0, 18, -0.75, "18.00 m (ศูนย์กลางเสา)")
dim_v(-0.9, 0, rm.Z_EAVE / 100, "+7.00 m\nผิวหลังคา\nที่ชายคา")
dim_v(-2.0, 0, rm.Z_BOT_EAVE / 100, f"+{rm.Z_BOT_EAVE/100:.2f} m\nใต้คอร์ดล่าง")
dim_v(19.0, 0, rm.Z_APEX / 100, "+9.00 m\nยอดโค้ง", side="right")
ax.text(9, 6.75, f"โค้งวงกลม R = {rm.R_TOP/100:.2f} m · ลึก {rm.DEPTH/100:.2f} m",
        ha="center", fontsize=9.5, color=MUTED)
ax.text(0, -0.45, "โคนเสายึดแน่น", ha="center", va="top", fontsize=8.5, color=MUTED)
ax.set_ylim(-1.5, 10.4)
fig.tight_layout()
fig.savefig("1_elevation_sections.png", dpi=150)

# ---------------------------------------------------------------- 2) แรงดึง/อัด
gov_g = max(rows, key=lambda r: r["dcr"] if r["group"] == "TC" else 0)["combo"]
gov_u = "0.6D+W2"
fig, axs = plt.subplots(2, 1, figsize=(14, 11))
for ax, cname, note in ((axs[0], gov_g, "แรงกดลง (ควบคุมคอร์ดบนและเสา)"), (axs[1], gov_u, "แรงลมยกไม่สมมาตร (ลมจากซ้าย)")):
    res = combos[cname][0]
    frame_axes(ax, f"แรงในชิ้นส่วน · {cname} — {note}")
    ground(ax)
    nmax = max(abs(res[m["name"]]["N"]) for m in members if m["group"] != "COL")
    for m in members:
        a, b = P[m["i"]], P[m["j"]]
        N = res[m["name"]]["N"]
        if m["group"] == "COL":
            ax.plot(*zip(a, b), color="#9ca3af", lw=4)
            continue
        ax.plot(*zip(a, b), color=TENSION if N > 0 else COMPRESSION, lw=0.8 + 5 * abs(N) / nmax,
                solid_capstyle="round")
    for g in ("TC", "BC"):
        ms = [m for m in members if m["group"] == g]
        mx = max(ms, key=lambda m: abs(res[m["name"]]["N"]))
        N = res[mx["name"]]["N"]
        c = (P[mx["i"]] + P[mx["j"]]) / 2
        ax.annotate(f"{GROUP_NAME[g]} {N/1000:+.1f} t", xy=c, xytext=(c[0] + (1.6 if c[0] < 9 else -1.6),
                    c[1] + (1.0 if g == "TC" else -1.3)), fontsize=10, fontweight="bold",
                    color=TENSION if N > 0 else COMPRESSION, ha="center",
                    arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.8),
                    bbox=dict(fc="white", ec="none", pad=1))
    webs = [m for m in members if m["group"] == "WEB"]
    mw = max(webs, key=lambda m: abs(res[m["name"]]["N"]))
    N = res[mw["name"]]["N"]
    c = (P[mw["i"]] + P[mw["j"]]) / 2
    ax.annotate(f"เอว {N/1000:+.1f} t", xy=c, xytext=(c[0] + (1.2 if c[0] < 9 else -1.2), c[1] - 1.6),
                fontsize=10, fontweight="bold", color=TENSION if N > 0 else COMPRESSION, ha="center",
                arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.8), bbox=dict(fc="white", ec="none", pad=1))
    reac = combos[cname][2]
    for n, x in (("cL0", 0), ("cR0", 18)):
        Rx, Rz, M = reac[n]
        ax.text(x, -0.55, f"V {Rz/1000:+.2f} t · H {Rx/1000:+.2f} t\nM {M/1e5:+.2f} t·m", ha="center", va="top",
                fontsize=9, color=INK)
    ly = -1.0
    ax.plot([3.2, 3.9], [ly, ly], color=TENSION, lw=5); ax.text(4.05, ly, "ดึง", va="center", color=TENSION)
    ax.plot([5.0, 5.7], [ly, ly], color=COMPRESSION, lw=5); ax.text(5.85, ly, "อัด", va="center", color=COMPRESSION)
    ax.text(6.9, ly, "ความหนาเส้นตามขนาดแรง · ฐานเสา: + V = กดลงฐาน", va="center", color=MUTED, fontsize=9.5)
    ax.set_ylim(-1.7, 10.6)
fig.tight_layout()
fig.savefig("2_axial_forces.png", dpi=150)

# ---------------------------------------------------------------- 3) การเสียรูป
fig, axs = plt.subplots(1, 2, figsize=(15, 5.6))
for ax, (case_lbl, fac) in zip(axs, (("นค. + นจ. (D + SD + L)", {"D": 1, "SD": 1, "L": 1}),
                                     ("ลมยก W1 (ทั้งหลังคา)", {"W1": 1}))):
    d = {n: sum(f * case_res[c][1][n] for c, f in fac.items()) for n in nodes}
    dz = d[f"t{rm.N_PANEL//2}"][1]
    scale = 0.9 / (max(np.hypot(v[0], v[1]) for v in d.values()) / 100)   # ให้เคลื่อนที่สูงสุดในรูป = 0.9 m
    frame_axes(ax, case_lbl)
    ax.set_xlim(-1.5, 19.5)
    ground(ax)
    for m in members:
        a, b = P[m["i"]], P[m["j"]]
        ax.plot(*zip(a, b), color="#9ca3af", lw=0.9, ls="--")
        da, db = d[m["i"]][:2] / 100 * scale, d[m["j"]][:2] / 100 * scale
        ax.plot(*zip(a + da, b + db), color="#2563eb", lw=1.8 if m["group"] != "WEB" else 0.7)
    ax.text(9, 10.1, f"ยอดเคลื่อนที่ {dz:+.2f} cm (ขยาย ×{scale:,.0f}) · เกณฑ์ L/180 = 10 cm",
            ha="center", fontsize=10, color=INK)
    ax.set_ylim(-0.6, 10.6)
fig.tight_layout()
fig.savefig("3_deflection.png", dpi=150)

# ---------------------------------------------------------------- 4) ภาพรวม 3 มิติ
fig = plt.figure(figsize=(14, 8))
ax = fig.add_axes([0, 0, 1, 0.93], projection="3d")
segs = {"COL": [], "TC": [], "BC": [], "WEB": [], "PUR": [], "BR": [], "STRUT": []}
for k in range(rm.N_FRAME):
    y = k * rm.BAY / 100
    for m in members:
        a, b = P[m["i"]], P[m["j"]]
        segs[m["group"]].append([(a[0], y, a[1]), (b[0], y, b[1])])
for i in range(rm.N_PANEL + 1):
    x, z = P[f"t{i}"]
    segs["PUR"].append([(x, 0, z + 0.05), (x, rm.LENGTH / 100, z + 0.05)])
for x in (0, 18):
    segs["STRUT"].append([(x, 0, rm.Z_EAVE / 100), (x, rm.LENGTH / 100, rm.Z_EAVE / 100)])
    for y0 in (0, rm.LENGTH / 100 - rm.BAY / 100):
        y1 = y0 + rm.BAY / 100
        h = rm.Z_BOT_EAVE / 100
        segs["BR"] += [[(x, y0, 0.3), (x, y1, h)], [(x, y1, 0.3), (x, y0, h)]]
for y0 in (0, rm.LENGTH / 100 - rm.BAY / 100):
    y1 = y0 + rm.BAY / 100
    for i0, i1 in ((0, rm.N_PANEL // 2), (rm.N_PANEL // 2, rm.N_PANEL)):
        (xa, za), (xb, zb) = P[f"t{i0}"], P[f"t{i1}"]
        segs["BR"] += [[(xa, y0, za + 0.08), (xb, y1, zb + 0.08)], [(xa, y1, za + 0.08), (xb, y0, zb + 0.08)]]
style = {"COL": ("#b45309", 2.4), "TC": ("#0f766e", 1.4), "BC": ("#7c3aed", 1.4), "WEB": ("#94a3b8", 0.5),
         "PUR": ("#cbd5e1", 0.7), "BR": ("#e11d48", 1.2), "STRUT": ("#0369a1", 1.8)}
for g, sg in segs.items():
    ax.add_collection3d(Line3DCollection(sg, colors=style[g][0], linewidths=style[g][1]))
ax.set_box_aspect((18, 27, 9.5))
ax.set_xlim(0, 18); ax.set_ylim(0, 27); ax.set_zlim(0, 9.5)
ax.view_init(elev=22, azim=-128)
ax.set_axis_off()
labels = [("เสา " + sizes["COL"], "#b45309"), ("คอร์ดบน " + sizes["TC"], "#0f766e"),
          ("คอร์ดล่าง " + sizes["BC"], "#7c3aed"), ("แป " + extras.purlin()[0], "#94a3b8"),
          ("X-bracing ช่วงริม (หลังคา + ระหว่างเสา)", "#e11d48"), ("คานยึดหัวเสา □75×75×3.2", "#0369a1")]
for k, (t, c) in enumerate(labels):
    fig.text(0.02, 0.88 - k * 0.035, "━  " + t, color=c, fontsize=11)
fig.text(0.02, 0.96, "หลังคาโค้งสนามฟุตซอล 18 × 27 m · ชายคา +7.00 m · ยอด +9.00 m · 7 โครง @ 4.5 m",
         fontsize=14, fontweight="bold", color=INK)
fig.savefig("4_overview_3d.png", dpi=150)
print("บันทึกรูป 4 ไฟล์")
