"""ส่วนประกอบรอง: แป · โครงค้ำยันแนวยาว · แรงที่ฐานเสา · น้ำหนักเหล็กรวม (หน่วย kg, cm)"""
import math

import numpy as np

import design
import roof_model as rm


def lipped_channel(h, b, d, t):
    """เหล็กตัวซี (มุมฉาก ไม่รวมรัศมีมุม) h×b×d×t mm → A, Ix, Sx (cm)"""
    h, b, d, t = h / 10, b / 10, d / 10, t / 10
    parts = [(b * t, h / 2 - t / 2, b * t**3 / 12), (b * t, -(h / 2 - t / 2), b * t**3 / 12),
             ((h - 2 * t) * t, 0, t * (h - 2 * t) ** 3 / 12),
             ((d - t) * t, h / 2 - t - (d - t) / 2, t * (d - t) ** 3 / 12),
             ((d - t) * t, -(h / 2 - t - (d - t) / 2), t * (d - t) ** 3 / 12)]
    A = sum(p[0] for p in parts)
    Ix = sum(p[2] + p[0] * p[1] ** 2 for p in parts)
    return dict(A=A, Ix=Ix, Sx=Ix / (h / 2), w=A * 100 * rm.STEEL)


PURLINS = {"C100×50×20×2.3": (100, 50, 20, 2.3), "C125×50×20×2.3": (125, 50, 20, 2.3),
           "C125×50×20×3.2": (125, 50, 20, 3.2), "C150×50×20×2.3": (150, 50, 20, 2.3),
           "C150×50×20×3.2": (150, 50, 20, 3.2)}
PURLIN_MAX_RATIO = 0.75   # เผื่อการโก่งเฉพาะที่ของเหล็กขึ้นรูปเย็นที่การตรวจแบบง่ายนี้ไม่ได้คิด


def purlin():
    """แปช่วงเดี่ยว 4.5 m · sag rod ที่จุดแบ่ง 3 ช่วง · Fb = 0.6Fy (ประกาศ มท. 2567 ข้อ 27) · เลือกตัวเบาสุดที่ผ่าน"""
    s = 1.033                                              # m ระยะแป (ตามโค้ง)
    L = rm.BAY / 100
    fb_allow = 0.6 * rm.FY
    for name in sorted(PURLINS, key=lambda k: lipped_channel(*PURLINS[k])["w"]):
        sec = lipped_channel(*PURLINS[name])
        D = rm.ROOFING * s + sec["w"]
        Lv = rm.LIVE * s
        up = abs(rm.CPCG_WINDWARD) * rm.Q_W * s
        rows = []
        for case, w in {"D+L": D + Lv, "0.6D+W (ยก)": 0.6 * D - up}.items():
            M = abs(w) * L**2 / 8 * 100                    # kg·cm
            fb = M / sec["Sx"]
            rows.append((case, w, M / 100, fb, fb / fb_allow))
        defl = 5 * (Lv / 100) * rm.BAY**4 / (384 * rm.E * sec["Ix"])
        if max(r[4] for r in rows) <= PURLIN_MAX_RATIO and defl <= rm.BAY / 180:
            return name, sec, rows, defl, rm.BAY / 180
    raise RuntimeError("ไม่มีแปในรายการที่ผ่าน")


def bracing(W_frame):
    """แรงแนวยาวรวม (ลม/แผ่นดินไหว) → X-bracing เหล็กเส้นกลม SR24 ในช่วงริม 2 ช่วง × 2 แนวเสา"""
    q = rm.Q_W
    truss_face = rm.DEPTH / 100 * 18.6 * 0.30              # m² ต่อโครงถัก (ความทึบ 0.30 — สมมติ)
    col_face = 0.20 * rm.Z_EAVE / 100                      # m² ต่อเสา
    shield = 0.40                                          # โครงด้านหลังรับแรงลม 40 % — สมมติ
    area = truss_face * (1 + shield * (rm.N_FRAME - 1)) + 2 * col_face * (1 + shield * (rm.N_FRAME - 1))
    F_drag = q * 2.0 * area
    F_fric = q * 0.04 * 18.6 * rm.LENGTH / 100             # แรงเสียดทานผิวหลังคา Cf = 0.04 — สมมติ
    F_wind = F_drag + F_fric
    F_seis = 0.7 * rm.CS * W_frame * (rm.N_FRAME - 1)      # ASD 0.7E · โครงริมรับครึ่งเดียว
    H = max(F_wind, F_seis)
    panels = 4                                             # 2 ช่วงริม × 2 แนวเสา
    h = rm.Z_BOT_EAVE / 100
    Ld = math.hypot(rm.BAY / 100, h)
    T = H / panels * Ld / (rm.BAY / 100)
    rod_d = next(d for d in (12, 16, 20, 25)
                 if min(2400 * math.pi * (d / 20) ** 2 / 1.67, 3900 * 0.75 * math.pi * (d / 20) ** 2 / 2.0) >= T)
    # คานยึดหัวเสา (eave strut) □75×75×3.2 ยาว 4.5 m รับแรงอัด H/2
    strut = rm.HSS_CATALOG["□75×75×3.2"]
    Pc, lam, _ = design.compression(strut, rm.BAY, rm.BAY)
    return dict(F_wind=F_wind, F_seis=F_seis, H=H, T=T, rod=rod_d, Ld=Ld, strut_P=H / 2, strut_Pc=Pc,
                strut_lam=lam, Fv_brace=T * h / Ld)


def reactions(combos):
    """ซองแรงที่ฐานเสาโครงภายใน (ต่อเสา 1 ต้น): N อัด, N ถอน, H, M"""
    rows = {}
    for cname, (res, disp, reac) in combos.items():
        for n, r in reac.items():
            rows.setdefault(n, []).append((cname, r))
    env = {}
    for n, lst in rows.items():
        env[n] = dict(
            comp=max(lst, key=lambda x: x[1][1]),
            uplift=min(lst, key=lambda x: x[1][1]),
            shear=max(lst, key=lambda x: abs(x[1][0])),
            moment=max(lst, key=lambda x: abs(x[1][2])),
        )
    return env


def takeoff(nodes, members, sec_p, brace):
    truss = sum(m["sec"]["w"] * rm.length(nodes, m) / 100 for m in members if m["group"] != "COL")
    col = sum(m["sec"]["w"] * rm.length(nodes, m) / 100 for m in members if m["group"] == "COL")
    n_purlin = rm.N_PANEL + 1
    purl = n_purlin * rm.LENGTH / 100 * sec_p["w"]
    rod_w = math.pi * (brace["rod"] / 20) ** 2 * 100 * rm.STEEL
    brace_w = (4 * 2 * brace["Ld"] + 2 * 2 * 2 * math.hypot(4.5, 9.3)) * rod_w   # ผนัง 4 ช่วง + หลังคา 2 ช่วง
    strut_w = 2 * rm.LENGTH / 100 * rm.HSS_CATALOG["□75×75×3.2"]["w"]
    items = {"โครงถัก 7 โครง": truss * rm.N_FRAME, "เสา 14 ต้น": col * rm.N_FRAME,
             f"แป {n_purlin} แนว": purl, "X-bracing + sag rod": brace_w * 1.3, "คานยึดหัวเสา 2 แนว": strut_w}
    total = sum(items.values()) * rm.CONN
    return items, total
