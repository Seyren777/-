"""แบบรายละเอียดฐานราก F1: แปลน + รูปตัด A–A"""
import math
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import Circle, Rectangle

import footing as ft

FONT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")
for f in ("Sarabun-Regular.ttf", "Sarabun-Bold.ttf"):
    font_manager.fontManager.addfont(os.path.join(FONT_DIR, f))
plt.rcParams["font.family"] = ["Sarabun", "DejaVu Sans"]
INK, MUTED, CONC, STEEL, REBAR = "#1f2937", "#6b7280", "#e5e7eb", "#475569", "#b91c1c"

r = ft.run()
B, t = r["B"] / 100, r["t"] / 100
P, N = ft.PED / 100, ft.PLATE[0] / 100
DF = ft.DF / 100
nb, sb, _ = ft.bars(r["As_bot"], r["B"])
nt, stp, _ = ft.bars(r["As_top"], r["B"], 1.2)
BOT = f"{nb}-DB16 @ {sb/100:.2f} m"
TOP = f"{nt}-DB12 @ {stp/100:.2f} m"

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 8.2), gridspec_kw=dict(width_ratios=[1, 1.08]))


def dim(ax, p1, p2, text, off=(0, 0), rot=0):
    ax.annotate("", xy=p1, xytext=p2, arrowprops=dict(arrowstyle="<->", color=MUTED, lw=0.8))
    ax.text((p1[0] + p2[0]) / 2 + off[0], (p1[1] + p2[1]) / 2 + off[1], text, ha="center", va="center",
            fontsize=9.5, color=INK, rotation=rot, bbox=dict(fc="white", ec="none", pad=0.5))


# ---------------------------------------------------------------- แปลน
ax = ax1
ax.set_title("แปลนฐานราก F1 (ใช้กับเสาทุกต้น 14 ต้น)", loc="left", fontsize=13, fontweight="bold", color=INK)
ax.add_patch(Rectangle((-B / 2, -B / 2), B, B, fc=CONC, ec=INK, lw=1.4))
for k in range(nb):
    x = -B / 2 + 0.075 + k * sb / 100
    ax.plot([x, x], [-B / 2 + 0.075, B / 2 - 0.075], color=REBAR, lw=0.6, alpha=0.55)
    ax.plot([-B / 2 + 0.075, B / 2 - 0.075], [x, x], color=REBAR, lw=0.6, alpha=0.55)
ax.add_patch(Rectangle((-P / 2, -P / 2), P, P, fc="#d1d5db", ec=INK, lw=1.2))
ax.add_patch(Rectangle((-N / 2, -N / 2), N, N, fc="#94a3b8", ec=INK, lw=1.0))
h, bf, tw, tf = 0.2, 0.2, 0.008, 0.012
for x0 in (-h / 2, h / 2 - tf):                       # ปีกตั้งฉากกับแนวโครง (แกนแข็งรับโมเมนต์ในระนาบโครง)
    ax.add_patch(Rectangle((x0, -bf / 2), tf, bf, fc=STEEL, ec="none"))
ax.add_patch(Rectangle((-h / 2, -tw / 2), h, tw, fc=STEEL, ec="none"))
f = N / 2 - ft.BOLT_EDGE / 100
for xb in (-f, f):                                     # แถวรับแรงดึงอยู่สองข้างในแนวโครง
    for yb in (-f, 0, f):
        ax.add_patch(Circle((xb, yb), 0.014, fc="white", ec=INK, lw=1))
ax.annotate("", xy=(B / 2, -B / 2 - 0.3), xytext=(-B / 2, -B / 2 - 0.3), arrowprops=dict(arrowstyle="<->", color=MUTED, lw=0.8))
ax.text(0, -B / 2 - 0.3, "แนวโครงหลังคา (ระนาบโมเมนต์)", ha="center", va="center", fontsize=9.5, color=MUTED,
        bbox=dict(fc="white", ec="none", pad=0.5))
ax.text(B / 2 + 0.05, 0, "A", fontsize=12, fontweight="bold", va="center")
ax.text(-B / 2 - 0.12, 0, "A", fontsize=12, fontweight="bold", va="center")
ax.plot([-B / 2 - 0.05, B / 2 + 0.05], [0, 0], color=INK, lw=0.8, ls="--")
dim(ax, (-B / 2, B / 2 + 0.22), (B / 2, B / 2 + 0.22), f"{B:.2f} m")
dim(ax, (-B / 2 - 0.25, -B / 2), (-B / 2 - 0.25, B / 2), f"{B:.2f} m", rot=90)
notes = [f"ตอม่อ {ft.PED/100:.2f} × {ft.PED/100:.2f} m", f"แผ่นฐาน PL {ft.PLATE[0]*10:.0f}×{ft.PLATE[1]*10:.0f}×30 mm",
         "สลักยึด 6-M24 (หัวหมุด) ฝังลึก 0.75 m", f"เหล็กล่าง {BOT} ทั้งสองทาง", f"เหล็กบน {TOP} ทั้งสองทาง"]
for k, n in enumerate(notes):
    ax.text(-B / 2, -B / 2 - 0.6 - k * 0.17, "• " + n, fontsize=10, color=INK)
ax.set_aspect("equal"); ax.axis("off")
ax.set_xlim(-B / 2 - 0.45, B / 2 + 0.3); ax.set_ylim(-B / 2 - 1.5, B / 2 + 0.4)

# ---------------------------------------------------------------- รูปตัด
ax = ax2
ax.set_title("รูปตัด A–A", loc="left", fontsize=13, fontweight="bold", color=INK)
ztop_f = -DF + t
ax.add_patch(Rectangle((-B / 2 - 0.05, -DF - 0.05), B + 0.1, 0.05, fc="#f3f4f6", ec=MUTED, lw=0.6, hatch="..."))
ax.add_patch(Rectangle((-B / 2, -DF), B, t, fc=CONC, ec=INK, lw=1.4))
ax.add_patch(Rectangle((-P / 2, ztop_f), P, DF - t, fc=CONC, ec=INK, lw=1.4))
ax.plot([-B / 2 - 0.3, -P / 2], [0, 0], color="#a16207", lw=1.2)
ax.plot([P / 2, B / 2 + 0.3], [0, 0], color="#a16207", lw=1.2)
ax.text(B / 2 + 0.3, 0.03, "±0.00 พื้นวางบนดิน", ha="right", va="bottom", fontsize=9, color="#a16207")
ax.add_patch(Rectangle((-N / 2, 0.025), N, 0.03, fc="#94a3b8", ec=INK, lw=1))
ax.add_patch(Rectangle((-N / 2, 0), N, 0.025, fc="#fde68a", ec=MUTED, lw=0.6))
ax.add_patch(Rectangle((-bf / 2, 0.055), bf, 0.7, fc="none", ec=STEEL, lw=1.4))
ax.text(0, 0.8, "เสา H-200×200×8×12", ha="center", fontsize=9.5, color=INK)
c = ft.COVER / 100
ax.plot([-B / 2 + c, B / 2 - c], [-DF + c, -DF + c], color=REBAR, lw=1.8)
ax.plot([-B / 2 + c, B / 2 - c], [ztop_f - 0.05, ztop_f - 0.05], color=REBAR, lw=1.3)
for xb in (-B / 2 + c, B / 2 - c):
    ax.plot([xb, xb], [-DF + c, ztop_f - 0.05], color=REBAR, lw=0.8)
for xb in (-P / 2 + 0.06, P / 2 - 0.06):
    ax.plot([xb, xb], [-0.05, -DF + c + 0.02], color=REBAR, lw=1.5)
    ax.plot([xb, xb + (-0.3 if xb < 0 else 0.3)], [-DF + c + 0.02, -DF + c + 0.02], color=REBAR, lw=1.5)
for z in [x / 100 for x in range(-5, int(-(DF - t) * 100), -15)]:
    ax.plot([-P / 2 + 0.05, P / 2 - 0.05], [z, z], color=REBAR, lw=0.7)
for xb in (-f, f):
    ax.plot([xb, xb], [0.09, -ft.HEF / 100], color=INK, lw=1.6)
    ax.add_patch(Rectangle((xb - 0.03, -ft.HEF / 100 - 0.012), 0.06, 0.012, fc=INK))
dim(ax, (B / 2 + 0.18, -DF), (B / 2 + 0.18, 0), f"{DF:.2f} m", rot=90)
dim(ax, (B / 2 + 0.05, -DF), (B / 2 + 0.05, ztop_f), f"{t:.2f}", off=(0.09, 0), rot=90)
dim(ax, (-B / 2, -DF - 0.2), (B / 2, -DF - 0.2), f"{B:.2f} m")
dim(ax, (-P / 2, -0.85), (P / 2, -0.85), f"{P:.2f}")
labels = [((-P / 2 + 0.06, -0.55), (-B / 2 + 0.05, -0.35), "เหล็กยืนตอม่อ 12-DB16 งอฉาก 0.30 m"),
          ((0.1, -0.35), (P / 2 + 0.25, -0.3), "ปลอก DB10 @ 0.15 m (3 ชุดบนห่าง 0.05 m)"),
          ((f, -0.6), (P / 2 + 0.25, -0.62), "สลัก M24 ฝังลึก 0.75 m + แผ่นหัวหมุด"),
          ((-0.6, -DF + c), (-B / 2 + 0.05, -DF - 0.42), f"เหล็กล่าง {BOT}"),
          ((0.9, ztop_f - 0.05), (P / 2 + 0.25, ztop_f + 0.2), f"เหล็กบน {TOP}"),
          ((-N / 2, 0.012), (-B / 2 + 0.05, 0.25), "ปูนเกราต์ไม่หดตัว 25 mm")]
for xy, xyt, s in labels:
    ax.annotate(s, xy=xy, xytext=xyt, fontsize=9.3, color=INK, arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.7))
ax.text(-B / 2, -DF - 0.42 - 0.17, "คอนกรีตหยาบรองพื้น 5 cm · ระยะหุ้ม 7.5 cm · f'c 210 ksc (ลูกบาศก์ 240) · SD40",
        fontsize=9.3, color=MUTED)
ax.set_aspect("equal"); ax.axis("off")
ax.set_xlim(-B / 2 - 0.35, B / 2 + 0.4); ax.set_ylim(-DF - 0.75, 0.95)
fig.tight_layout()
fig.savefig("5_footing_detail.png", dpi=150)
print("บันทึก 5_footing_detail.png")
