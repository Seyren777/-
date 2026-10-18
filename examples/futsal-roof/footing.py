"""ฐานรากเสา: แผ่นฐานเสา + สลักเกลียวยึด + ตอม่อ + ฐานรากแผ่ (ใช้แบบเดียวทั้ง 14 ต้น)

- ดิน (แบกทาน พลิกคว่ำ ถอน เลื่อนไถล): ชุดน้ำหนักใช้งาน ASD กฎกระทรวง 2566 ข้อ 6
- คอนกรีต/เหล็กเสริม/สลักยึด/แผ่นฐาน: ชุดน้ำหนักประลัย กฎกระทรวง 2566 ข้อ 7
  + φ ของกฎหมายไทย (ดัด 0.90, เฉือน 0.85, แบกทาน 0.70) · สูตรกำลัง ACI 318-19 (หน่วย ksc) · แผ่นฐาน AISC Design Guide 1
หน่วย: kg, cm, ksc (แสดงผลเป็น t, m)
"""
import math

import numpy as np

import design
import extras
import roof_model as rm

# ================================================================ ข้อมูลนำเข้า
QA = 5.0              # t/m² ⚠ ไม่มีผลเจาะดิน: ดินเหนียวแข็งปานกลาง (กฎกระทรวงฐานราก 2566 ข้อ 7)
GAMMA_SOIL = 1.8      # t/m³ ดินถมกลับ
MU_SLIDE = 0.30       # ⚠ สัมประสิทธิ์เสียดทานฐานกับดินเหนียว (สมมติ)
DF = 150.0            # cm ความลึกท้องฐานจากระดับ ±0.00 (หลังตอม่อ = โคนเสาในแบบจำลอง)
FC = 210.0            # ksc ทรงกระบอก (ลูกบาศก์ 240)
FY = 4000.0           # ksc SD40
FYT = 4000.0          # ksc ปลอก DB10 (SD40)
COVER = 7.5           # cm หล่อติดดิน (ประกาศ มท. 2567 ตาราง 13)
GAMMA_C = 2.4         # t/m³
BOLT_EDGE = 5.0       # cm ระยะศูนย์สลักถึงขอบแผ่น
BOLT_D = 2.4          # cm M24
BOLT_ASE = 3.53       # cm² พื้นที่รับแรงดึงของเกลียว M24
BOLT_FUTA = 4000.0    # ksc (SS400 / ASTM F1554 Gr.36 ≈ 58 ksi)
BOLT_FYA = 2500.0
N_BOLT = 6            # 3 ตัวต่อฝั่ง
PED_BARS = (12, 1.6)  # ตอม่อ 12-DB16 (4 เส้นต่อด้าน รวมมุม)
HEF = 75.0            # cm ความลึกฝังสลักหัวหมุด
FY_PLATE = 2500.0
PHI = dict(flex=0.90, shear=0.85, bear=0.70)


# ================================================================ แรงที่ฐานเสาจากแบบจำลองหลังคา
sizes, nodes, members, supports, cases, case_res, combos, W, rows, defl = design.select()
COL_NAME = sizes["COL"]
col = rm.H_CATALOG[COL_NAME]
D_COL, BF_COL, TF_COL = col["h"], col["b"], col["tf"]
_np = math.ceil((max(D_COL, BF_COL) + 20) / 5) * 5
PLATE = (float(_np), float(_np))          # cm แผ่นฐาน = ขนาดเสา + 10 cm ต่อข้าง (ปัด 5 cm)
PED = PLATE[0] + 15                       # cm ตอม่อ = แผ่นฐาน + 7.5 cm ต่อข้าง
PLATE_T_STD = (20, 25, 28, 32, 36, 40, 45, 50)   # mm ความหนาเหล็กแผ่นในตลาด
br = extras.bracing(W)
FV_BR = br["Fv_brace"]                    # kg แรงดิ่งเพิ่มจาก X-bracing (ระดับใช้งาน)
H_BR = br["H"] / 4                        # kg แรงราบแนวยาวที่ฐานเสาช่วงค้ำยัน (ระดับใช้งาน)

ASD = {k: v for k, v in rm.COMBOS.items()}
USD = {
    "1.4D+1.7L": {"D": 1.4, "SD": 1.4, "L": 1.7},
    "0.75(1.4D+1.7L)+1.6W↓": {"D": 1.05, "SD": 1.05, "L": 1.275, "W4": 1.6},
    "0.75(1.4D+1.7L)+1.6W2": {"D": 1.05, "SD": 1.05, "L": 1.275, "W2": 1.6},
    "0.75(1.4D+1.7L)+1.6W2R": {"D": 1.05, "SD": 1.05, "L": 1.275, "W2R": 1.6},
    "0.9D+1.6W1": {"D": 0.9, "W1": 1.6},
    "0.9D+1.6W2": {"D": 0.9, "W2": 1.6},
    "0.9D+1.6W2R": {"D": 0.9, "W2R": 1.6},
    "0.75(1.4D+1.7L)+1.0E": {"D": 1.05, "SD": 1.05, "L": 1.275, "E": 1.0},
    "0.75(1.4D+1.7L)-1.0E": {"D": 1.05, "SD": 1.05, "L": 1.275, "E": -1.0},
    "0.9D+1.0E": {"D": 0.9, "E": 1.0},
    "0.9D-1.0E": {"D": 0.9, "E": -1.0},
}


def column_actions(fac):
    """แรงที่เสากระทำต่อหลังตอม่อ (ซองของเสาซ้าย/ขวา): P (+ กดลง), H, M (kg, kg·cm)"""
    out = []
    for n in supports:
        R = sum(f * case_res[c][2][n] for c, f in fac.items())
        out.append((R[1], -R[0], -R[2]))
    return out


def brace_factor(name, fac):
    """ตัวคูณของแรงจาก X-bracing ในชุดนั้น (0 ถ้าไม่มีลม/แผ่นดินไหว)"""
    w = max([abs(v) for k, v in fac.items() if k.startswith("W")] + [0])
    e = max([abs(v) for k, v in fac.items() if k == "E"] + [0])
    return max(w, e / 0.7 if e else 0)          # F_V_BR ใช้แรงใช้งาน (ลม 1.0W หรือ 0.7E)


# ================================================================ ฐานรากแผ่ — ดิน (ASD)
def soil_checks(B, t):
    """B = ด้านฐานสี่เหลี่ยมจัตุรัส (cm), t = ความหนา (cm)"""
    A = (B / 100) ** 2
    h_ped = DF - t
    W_ft = GAMMA_C * A * t / 100
    W_ped = GAMMA_C * (PED / 100) ** 2 * h_ped / 100
    W_soil = GAMMA_SOIL * (A - (PED / 100) ** 2) * h_ped / 100
    W_found = W_ft + W_ped + W_soil                          # t
    res = []
    for name, fac in ASD.items():
        d_fac = fac.get("D", 0)
        for P, H, M in column_actions(fac):
            for sgn in (+1, -1):
                bf = brace_factor(name, fac)
                Pt = P / 1000 + sgn * bf * FV_BR / 1000 + d_fac * W_found     # t
                Mt = abs(M / 1e5 - H / 1000 * DF / 100)                         # t·m รอบท้องฐาน
                Ht = math.hypot(H / 1000, bf * H_BR / 1000)
                if Pt <= 0:
                    res.append(dict(combo=name, P=Pt, M=Mt, H=Ht, q=math.inf, e=math.inf, fs_ot=0, fs_sl=0))
                    continue
                e = Mt / Pt
                Bm = B / 100
                q = Pt / A * (1 + 6 * e / Bm) if e <= Bm / 6 else 2 * Pt / (3 * Bm * (Bm / 2 - e)) if e < Bm / 2 else math.inf
                fs_ot = (Pt * Bm / 2) / Mt if Mt > 0 else math.inf
                fs_sl = MU_SLIDE * Pt / Ht if Ht > 0 else math.inf
                res.append(dict(combo=name, P=Pt, M=Mt, H=Ht, q=q, e=e, fs_ot=fs_ot, fs_sl=fs_sl))
    ok = all(r["q"] <= QA and r["fs_ot"] >= 1.5 and r["fs_sl"] >= 1.5 for r in res)
    return ok, res, dict(W_ft=W_ft, W_ped=W_ped, W_soil=W_soil, W_found=W_found, h_ped=h_ped)


# ================================================================ แผ่นฐาน + สลักยึด (USD)
def base_plate():
    N, Bp = PLATE
    A1 = N * Bp
    A2 = PED**2
    fpmax = PHI["bear"] * 0.85 * FC * min(math.sqrt(A2 / A1), 2.0)
    qmax = fpmax * Bp
    f = N / 2 - BOLT_EDGE
    m = (N - 0.95 * D_COL) / 2
    worst = dict(t=0, T=0, V=0)
    for name, fac in USD.items():
        bf = brace_factor(name, fac) * (1.6 if "W" in name else 1.0)
        for P, H, M in column_actions(fac):
            for sgn in (+1, -1):
                Pu = P + sgn * bf * FV_BR
                Mu, Hu = abs(M), math.hypot(H, bf * H_BR)
                if Pu > 0:
                    e = Mu / Pu
                    ecrit = N / 2 - Pu / (2 * qmax)
                    if e <= ecrit:
                        Y = N - 2 * e
                        T = 0.0
                        fp = Pu / (Y * Bp)
                    else:
                        k = f + N / 2
                        disc = k**2 - 2 * Pu * (e + f) / qmax
                        if disc < 0:
                            return None                                        # แผ่นเล็กเกินไป
                        Y = k - math.sqrt(disc)
                        T = qmax * Y - Pu
                        fp = fpmax
                    t_b = 1.5 * m * math.sqrt(fp / FY_PLATE) if Y >= m else \
                        2.11 * math.sqrt(fp * Y * (m - Y / 2) / FY_PLATE)
                else:                                                         # แรงถอน + โมเมนต์
                    T = -Pu / 2 + Mu / (2 * f)
                    t_b = 0.0
                x = f - D_COL / 2 + TF_COL / 2
                t_t = 2.11 * math.sqrt(T * x / (Bp * FY_PLATE)) if T > 0 else 0.0
                t_req = max(t_b, t_t)
                if t_req > worst["t"]:
                    worst.update(t=t_req, t_combo=name)
                if T > worst["T"]:
                    worst.update(T=T, T_combo=name, V_with_T=Hu)
                worst["V"] = max(worst["V"], Hu)
    return worst, fpmax


def ld_straight(db):
    """ld เหล็กข้ออ้อยตรง ACI 318-19 §25.4.2.3 (ψt = ψe = ψs = ψg = 1, ksc, cm)"""
    coef = 6.6 if db <= 1.9 else 5.3
    return max(FY / (coef * math.sqrt(FC)) * db, 30.0)


def anchors(T_side, V_total, hef):
    """ACI 318-19 บทที่ 17 — สลักหัวหมุด 3 ตัวต่อฝั่ง
    ตอม่อแคบ ระยะขอบน้อย กำลังแตกหักของคอนกรีต (breakout) จึงต่ำ → ใช้เหล็กยืนตอม่อเป็นเหล็กเสริมรับแรงถอน (§17.5.2.1)"""
    n_t = N_BOLT // 2
    Nua = T_side / n_t
    Vua = V_total / N_BOLT
    phiNsa = 0.75 * BOLT_ASE * BOLT_FUTA
    phiVsa = 0.65 * 0.6 * BOLT_ASE * BOLT_FUTA
    Abrg = math.pi / 4 * ((BOLT_D * 1.6) ** 2 - BOLT_D**2)     # cm² หัวน็อต ≈ 1.6d
    phiNpn = 0.70 * 8 * Abrg * FC * n_t
    n_face = PED_BARS[0] // 3 + 1 - 1                          # 12 เส้นรอบตอม่อ → 4 เส้นต่อด้าน
    As_face = 4 * math.pi * PED_BARS[1] ** 2 / 4
    phiNar = 0.75 * As_face * FY
    ld = ld_straight(PED_BARS[1])
    ratio_steel = Nua / phiNsa
    ratio_v = Vua / phiVsa
    inter = ratio_steel + ratio_v if ratio_steel > 0.2 and ratio_v > 0.2 else max(ratio_steel, ratio_v)
    return dict(Nua=Nua, Vua=Vua, phiNsa=phiNsa, phiVsa=phiVsa, phiNpn=phiNpn, phiNar=phiNar,
                As_face=As_face, ld=ld, hef=hef, r_steel=ratio_steel, r_v=ratio_v, inter=inter,
                r_pull=T_side / phiNpn, r_ar=T_side / phiNar, embed_ok=hef >= ld + 5)


# ================================================================ ฐานราก — คอนกรีต (USD, ACI 318-19)
def footing_structure(B, t):
    d = t - COVER - 1.6                                       # cm ค่าเฉลี่ยสองชั้น DB16
    c = PED
    a_cant = (B - c) / 2
    out = dict(Mu=0, Vu1=0, Vu2=0, Mu_top=0)
    for name, fac in USD.items():
        bf = brace_factor(name, fac) * (1.6 if "W" in name else 1.0)
        for P, H, M in column_actions(fac):
            for sgn in (+1, -1):
                Pu = P + sgn * bf * FV_BR
                Mu = abs(M - H * DF)
                if Pu > 0:
                    e = Mu / Pu
                    # แรงดันดินสุทธิเชิงเส้น/สามเหลี่ยม (ไม่รวมน้ำหนักฐานและดิน เพราะหักล้างกัน)
                    xs = np.linspace(-B / 2, B / 2, 401)
                    if e <= B / 6:
                        q = Pu / B**2 * (1 + 12 * e * xs / B**2)
                    else:
                        L_c = 3 * (B / 2 - e)
                        qmx = 2 * Pu / (3 * B * (B / 2 - e))
                        q = np.clip(qmx * (xs - (B / 2 - L_c)) / L_c, 0, None)
                    q = q * B                                      # kg/cm ต่อความกว้างฐานทั้งหมด
                    sel = xs >= c / 2
                    Mf = np.trapezoid(q[sel] * (xs[sel] - c / 2), xs[sel])
                    sel1 = xs >= c / 2 + d
                    V1 = np.trapezoid(q[sel1], xs[sel1])
                    bo_in = xs.__abs__() <= (c + d) / 2
                    V2 = Pu - np.trapezoid(q[bo_in], xs[bo_in]) * (c + d) / B
                    out["Mu"] = max(out["Mu"], Mf)
                    out["Vu1"] = max(out["Vu1"], V1)
                    out["Vu2"] = max(out["Vu2"], V2)
                # เหล็กบน: น้ำหนักฐาน + ดินกดลงบนส่วนยื่น ขณะเสาดึงขึ้น (0.9D)
                if Pu < 0:
                    w_down = 0.9 * (GAMMA_C * t + GAMMA_SOIL * (DF - t)) / 1e3 * B   # kg/cm (t/m³·cm → kg/cm² × B)
                    out["Mu_top"] = max(out["Mu_top"], w_down * a_cant**2 / 2)
    return out, d


def design_flexure(Mu, b, d, h):
    Rn = Mu / (PHI["flex"] * b * d**2)
    rho = 0.85 * FC / FY * (1 - math.sqrt(max(1 - 2 * Rn / (0.85 * FC), 0)))
    As_min = 0.0018 * b * h                                   # ประกาศ มท. 2567 ข้อ 29 (SD40) / ACI 318-19 §13.3.3
    return max(rho * b * d, As_min), rho * b * d, As_min


def select_footing():
    for B in np.arange(120, 401, 10):
        for t in (40, 45, 50, 55, 60, 70):
            ok, soil, wts = soil_checks(B, t)
            if not ok:
                continue
            st, d = footing_structure(B, t)
            phi_vc1 = PHI["shear"] * 0.53 * math.sqrt(FC) * B * d                      # λs = 1 (ฐานราก §13.2.6.2)
            bo = 4 * (PED + d)
            beta, alpha_s = 1.0, 40
            vc2 = min(1.1, 0.53 * (1 + 2 / beta), 0.27 * (alpha_s * d / bo + 2)) * math.sqrt(FC)
            phi_vc2 = PHI["shear"] * vc2 * bo * d
            ldh = ldh_pedestal_bar()
            if st["Vu1"] > phi_vc1 or st["Vu2"] > phi_vc2 or d < ldh + 2:
                continue
            return B, t, soil, wts, st, d, phi_vc1, phi_vc2, ldh
    raise RuntimeError("ไม่พบขนาดฐานรากที่ผ่าน")


def ldh_pedestal_bar(db=1.6):
    """ldh ของเหล็กยืนตอม่อ DB16 งอฉากในฐานราก — ACI 318-19 §25.4.3.1 (หน่วย ksc, cm)"""
    psi_e, psi_r, psi_o = 1.0, 1.6, 1.0
    psi_c = FC / 1055 + 0.6 if FC < 422 else 1.0
    ldh = FY * psi_e * psi_r * psi_o * psi_c / (23.2 * math.sqrt(FC)) * db**1.5
    return max(ldh, 8 * db, 15.0)


def pedestal(h_ped):
    """ตอม่อ 60 × 60: 12-DB16 · ตรวจดัด (ไม่คิดแรงอัดช่วย = ปลอดภัย) และแรงดึงตามแกน"""
    a1 = math.pi * PED_BARS[1] ** 2 / 4
    As_face, As_tot = 4 * a1, PED_BARS[0] * a1
    d = PED - 5.0 - 1.0 - PED_BARS[1] / 2
    a = As_face * FY / (0.85 * FC * PED)
    phiMn = PHI["flex"] * As_face * FY * (d - a / 2)
    phiTn = PHI["flex"] * As_tot * FY
    Mu = Tu = Vu = 0.0
    for name, fac in USD.items():
        bf = brace_factor(name, fac) * (1.6 if "W" in name else 1.0)
        for P, H, M in column_actions(fac):
            Mu = max(Mu, abs(M - H * h_ped))
            Tu = max(Tu, -(P - bf * FV_BR))
            Vu = max(Vu, math.hypot(H, bf * H_BR))
    phiVc = PHI["shear"] * 0.53 * math.sqrt(FC) * PED * d
    return dict(Mu=Mu, phiMn=phiMn, Tu=Tu, phiTn=phiTn, Vu=Vu, phiVc=phiVc, rho=As_tot / PED**2, As_tot=As_tot)


def run():
    B, t, soil, wts, st, d, phi_vc1, phi_vc2, ldh = select_footing()
    bp, fpmax = base_plate()
    anc = anchors(bp["T"], bp["V"], HEF)
    bp["t_std"] = next(x for x in PLATE_T_STD if x >= bp["t"] * 10)
    As_bot, As_bot_req, As_min = design_flexure(st["Mu"], B, d, t)
    _, As_top_req, _ = design_flexure(st["Mu_top"], B, d, t)
    As_top = 1.33 * As_top_req                               # เหล็กบนรับโมเมนต์ขณะลมยก (ACI 9.6.1.3: 4/3 ของที่ต้องการ)
    ped = pedestal(wts["h_ped"])
    return dict(B=B, t=t, soil=soil, wts=wts, st=st, d=d, phi_vc1=phi_vc1, phi_vc2=phi_vc2, ldh=ldh,
                bp=bp, fpmax=fpmax, anc=anc, hef=HEF, As_bot=As_bot, As_bot_req=As_bot_req, As_min=As_min,
                As_top=As_top, As_top_req=As_top_req, ped=ped)


def bars(As, B, db=1.6, smax=25.0):
    a1 = math.pi * db**2 / 4
    n = max(math.ceil(As / a1), math.ceil((B - 2 * COVER) / smax) + 1)
    s = (B - 2 * COVER) / (n - 1)
    return n, s, n * a1


if __name__ == "__main__":
    r = run()
    print(f"ฐานราก {r['B']/100:.2f} × {r['B']/100:.2f} × {r['t']/100:.2f} m · d = {r['d']:.1f} cm · ldh DB16 = {r['ldh']:.1f} cm")
    w = r["wts"]
    print(f"  น้ำหนักฐาน {w['W_ft']:.2f} t ตอม่อ {w['W_ped']:.2f} t ดิน {w['W_soil']:.2f} t รวม {w['W_found']:.2f} t")
    s = r["soil"]
    print("  q สูงสุด %.2f t/m² (≤ %.1f) · FS พลิก min %.2f · FS เลื่อน min %.2f · P min %.2f t" % (
        max(x['q'] for x in s), QA, min(x['fs_ot'] for x in s), min(x['fs_sl'] for x in s), min(x['P'] for x in s)))
    st = r["st"]
    print(f"  Mu ล่าง {st['Mu']/1e5:.2f} t·m · Mu บน {st['Mu_top']/1e5:.2f} t·m · Vu1 {st['Vu1']/1e3:.2f} ≤ {r['phi_vc1']/1e3:.2f} t · "
          f"Vu2 {st['Vu2']/1e3:.2f} ≤ {r['phi_vc2']/1e3:.2f} t")
    print(f"  As ล่าง {r['As_bot']:.2f} (คำนวณ {r['As_bot_req']:.2f}, min {r['As_min']:.2f}) cm² → {bars(r['As_bot'], r['B'])}")
    print(f"  As บน {r['As_top']:.2f} (คำนวณ {r['As_top_req']:.2f}) cm² → {bars(r['As_top'], r['B'], 1.2, 25.0)}")
    bp = r["bp"]
    print(f"  แผ่นฐาน {PLATE} ต้องหนา {bp['t']:.2f} cm ({bp['t_combo']}) · fp,max {r['fpmax']:.0f} ksc · T ฝั่งดึง {bp['T']/1e3:.2f} t ({bp['T_combo']}) · V {bp['V']/1e3:.2f} t")
    a = r["anc"]
    print(f"  สลัก 6-M24: Nua {a['Nua']:.0f} ≤ φNsa {a['phiNsa']:.0f} kg/ตัว · Vua {a['Vua']:.0f} ≤ φVsa {a['phiVsa']:.0f} · interaction {a['inter']:.2f}")
    print(f"    ถอนหัวหมุด T {bp['T']:.0f} ≤ φNpn {a['phiNpn']:.0f} · เหล็กเสริมรับแรงถอน 4-DB16 φNar {a['phiNar']:.0f} (อัตราส่วน {a['r_ar']:.2f}) · "
          f"hef {a['hef']:.0f} ≥ ld {a['ld']:.1f}+5 → {a['embed_ok']}")
    p = r["ped"]
    print(f"  ตอม่อ Mu {p['Mu']/1e5:.2f} ≤ φMn {p['phiMn']/1e5:.2f} t·m · Tu {p['Tu']/1e3:.2f} ≤ φTn {p['phiTn']/1e3:.2f} t · "
          f"Vu {p['Vu']/1e3:.2f} ≤ φVc {p['phiVc']/1e3:.2f} t · ρ {p['rho']:.4f}")
