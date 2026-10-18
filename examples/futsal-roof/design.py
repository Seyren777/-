"""ตรวจหน้าตัดตาม AISC 360-16 (ASD) และเลือกหน้าตัดที่เบาที่สุดที่ผ่านทุกชุดน้ำหนัก

หน่วย: kg, cm, ksc
"""
import math

import numpy as np

import roof_model as rm

E, FY = rm.E, rm.FY
RT = math.sqrt(E / FY)
OMEGA_C = OMEGA_T = OMEGA_B = 1.67
DCR_LIMIT = 0.50   # เกณฑ์ DCR ที่ผู้ใช้กำหนด (มาตรฐานยอมให้ถึง 1.00)

# ความยาวไร้ค้ำยัน (cm) และ K — กลุ่ม → (Kx·Lx, Ky·Ly, Lb)
def unbraced(group, L):
    if group == "TC":                     # แปยึดทุกจุดต่อ
        return L, L, L
    if group == "BC":                     # ค้ำยันคอร์ดล่าง (fly brace) ทุก 3 ช่อง
        return L, 3 * L, 3 * L
    if group == "WEB":
        return L, L, L
    if group == "COL":                    # ในระนาบ K = 1.2 ช่วง 6.0 m · นอกระนาบ K = 1.0 ช่วง 7.0 m
        return 1.2 * rm.Z_BOT_EAVE, 1.0 * rm.Z_EAVE, rm.Z_EAVE
    raise KeyError(group)


def compression(sec, KLx, KLy):
    s = sec
    if s["kind"] == "HSS":
        walls = [(s["B"] - 3 * s["t"]) / s["t"], (s["H"] - 3 * s["t"]) / s["t"]]
        slender = max(walls) > 1.40 * RT
    else:
        slender = s["b"] / (2 * s["tf"]) > 0.56 * RT or (s["h"] - 2 * s["tf"]) / s["tw"] > 1.49 * RT
    lam = max(KLx / s["rx"], KLy / s["ry"])
    Fe = math.pi**2 * E / lam**2
    Fcr = 0.658 ** (FY / Fe) * FY if FY / Fe <= 2.25 else 0.877 * Fe
    return Fcr * s["A"] / OMEGA_C, lam, slender


def flexure(sec, Lb, Cb=1.0):
    s = sec
    Mp = FY * s["Zx"]
    if s["kind"] == "HSS":
        lam = (s["B"] - 3 * s["t"]) / s["t"]
        lp, lr = 1.12 * RT, 1.40 * RT
        if lam <= lp:
            Mn = Mp
        elif lam <= lr:
            Mn = min(Mp, Mp - (Mp - FY * s["Sx"]) * (3.57 * lam / RT - 4.0))
        else:
            return 0.0
        return Mn / OMEGA_B
    lam = s["b"] / (2 * s["tf"])                         # F3 ปีกไม่อัดแน่น
    lp, lr = 0.38 * RT, 1.0 * RT
    Mflb = Mp if lam <= lp else Mp - (Mp - 0.7 * FY * s["Sx"]) * (lam - lp) / (lr - lp)
    rts = math.sqrt(math.sqrt(s["Iy"] * s["Cw"]) / s["Sx"])           # F2 LTB
    Lp = 1.76 * s["ry"] * RT
    jc = s["J"] / (s["Sx"] * s["h0"])
    Lr = 1.95 * rts * E / (0.7 * FY) * math.sqrt(jc + math.sqrt(jc**2 + 6.76 * (0.7 * FY / E) ** 2))
    if Lb <= Lp:
        Mltb = Mp
    elif Lb <= Lr:
        Mltb = min(Mp, Cb * (Mp - (Mp - 0.7 * FY * s["Sx"]) * (Lb - Lp) / (Lr - Lp)))
    else:
        Fcr = Cb * math.pi**2 * E / (Lb / rts) ** 2 * math.sqrt(1 + 0.078 * jc * (Lb / rts) ** 2)
        Mltb = min(Mp, Fcr * s["Sx"])
    return min(Mflb, Mltb) / OMEGA_B


def shear(sec):
    s = sec
    if s["kind"] == "HSS":
        return 0.6 * FY * 2 * (s["H"] - 3 * s["t"]) * s["t"] / 1.67
    return 0.6 * FY * s["h"] * s["tw"] / 1.50


def b2_factor(members, res):
    """ตัวขยายโมเมนต์ P-Δ (AISC App. 8, α = 1.6 สำหรับ ASD) ใช้กับเสา"""
    cols = [m for m in members if m["group"] == "COL"]
    sec = cols[0]["sec"]
    Pe = 2 * math.pi**2 * E * sec["Ix"] / (1.2 * rm.Z_BOT_EAVE) ** 2
    P = sum(max(-res[m["name"]]["N"], 0) for m in cols if m["j"].startswith(("b0", f"b{rm.N_PANEL}")))
    return 1 / max(1 - 1.6 * P / Pe, 0.05)


def check(nodes, members, combos):
    """คืนรายการผลตรวจต่อชิ้นส่วน: DCR สูงสุด + ชุดน้ำหนักที่ควบคุม"""
    rows = []
    for m in members:
        s = m["sec"]
        L = rm.length(nodes, m)
        KLx, KLy, Lb = unbraced(m["group"], L)
        Pc_c, lam, slender = compression(s, KLx, KLy)
        Pc_t = FY * s["A"] / OMEGA_T
        Mc = flexure(s, Lb) if m["kind"] == "frame" else math.inf
        Vc = shear(s)
        worst = dict(dcr=0.0)
        for cname, (res, _, _) in combos.items():
            r = res[m["name"]]
            N = r["N"]
            amp = b2_factor(members, res) if m["group"] == "COL" else 1.0
            Mr = amp * np.abs(r["M"]).max() if m["kind"] == "frame" else 0.0
            Vr = np.abs(r["V"]).max() if m["kind"] == "frame" else 0.0
            if N < 0:
                Pr, Pc = -N, Pc_c
                if slender:
                    Pc = 0.0
            else:
                Pr, Pc = N, Pc_t
            ratio_p = Pr / Pc if Pc > 0 else math.inf
            ratio_m = Mr / Mc if Mc > 0 else (math.inf if Mr > 0 else 0)
            h1 = ratio_p + 8 / 9 * ratio_m if ratio_p >= 0.2 else ratio_p / 2 + ratio_m
            dcr = max(h1, Vr / Vc)
            if N < 0 and lam > 200:
                dcr = max(dcr, lam / 200)
            if N >= 0 and max(L / s["rx"], L / s["ry"]) > 300:
                dcr = max(dcr, max(L / s["rx"], L / s["ry"]) / 300)
            if dcr > worst["dcr"]:
                worst = dict(dcr=dcr, combo=cname, N=N, M=Mr, Pc=Pc, Mc=Mc, lam=lam, amp=amp)
        rows.append(dict(member=m["name"], group=m["group"], sec=m["sec_name"], L=L, **worst))
    return rows


def deflections(nodes, case_res):
    """ระยะแอ่นตัวยอดโครงถัก (กรณีน้ำหนักเดี่ยว) และการเอียงของหัวเสา"""
    apex = f"t{rm.N_PANEL // 2}"
    d = {c: case_res[c][1] for c in case_res}
    vert = {c: d[c][apex][1] for c in d}
    drift = {c: max(abs(d[c]["t0"][0]), abs(d[c][f"t{rm.N_PANEL}"][0])) for c in d}
    checks = {
        "นจ. ≤ L/180": (abs(vert["L"]), rm.SPAN / 180),
        "นค.+นจ. ≤ L/120": (abs(vert["D"] + vert["SD"] + vert["L"]), rm.SPAN / 120),
        "ลมยก ≤ L/180": (max(abs(vert[c]) for c in ("W1", "W2", "W2R")), rm.SPAN / 180),
        "หัวเสาเอียงจากลม ≤ H/150": (max(drift[c] for c in ("W1", "W2", "W2R")), rm.Z_EAVE / 150),
        "หัวเสาเอียงจากแผ่นดินไหว (Cd·δ/Ie ≤ 0.02H)": (3.0 * drift["E"] / rm.IE, 0.02 * rm.Z_EAVE),
    }
    return checks


def _evaluate(sizes):
    nodes, members, supports, cases, case_res, combos, W = rm.run_all(sizes)
    rows = check(nodes, members, combos)
    defl = deflections(nodes, case_res)
    bad = {r["group"] for r in rows if r["dcr"] > DCR_LIMIT}
    for name, (val, lim) in defl.items():
        if val > lim:
            bad.add("COL" if "หัวเสา" in name else "TC")
            if "หัวเสา" not in name:
                bad.add("BC")
    return bad, (sizes, nodes, members, supports, cases, case_res, combos, W, rows, defl)


def _frame_weight(out):
    nodes, members = out[1], out[2]
    return sum(m["sec"]["w"] * rm.length(nodes, m) / 100 for m in members)


def _grow_truss(col, cand):
    """เสาคงที่ ขยายกลุ่มโครงถักที่ไม่ผ่านจนผ่านครบ แล้วลดทีละกลุ่มกลับ — คืน None ถ้าเสาเองไม่ผ่าน"""
    groups = ("TC", "BC", "WEB")
    pick = {g: 0 for g in groups}
    sizes = lambda p: {**{g: cand[g][p[g]] for g in groups}, "COL": col}
    for _ in range(80):
        bad, out = _evaluate(sizes(pick))
        if not bad:
            break
        bad.discard("COL")                               # เสาไม่ผ่านชั่วคราวได้ — โครงถักที่แข็งขึ้นอาจลดแรงในเสา
        if not bad:
            return None
        for g in bad:
            if pick[g] + 1 >= len(cand[g]):
                return None
            pick[g] += 1
    else:
        return None
    improved = True
    while improved:
        improved = False
        for g in groups:
            for k in range(pick[g]):
                bad, trial_out = _evaluate(sizes(dict(pick, **{g: k})))
                if not bad:
                    pick, out, improved = dict(pick, **{g: k}), trial_out, True
                    break
    return out


def select():
    """ลองเสาทุกขนาดในรายการ · แต่ละขนาดหาโครงถักที่เบาที่สุดที่ผ่าน · เลือกชุดที่น้ำหนักเหล็กรวมน้อยที่สุด"""
    hss = sorted(rm.HSS_CATALOG, key=lambda k: rm.HSS_CATALOG[k]["w"])
    cand = {"TC": hss, "BC": hss, "WEB": [k for k in hss if rm.HSS_CATALOG[k]["H"] <= 7.5]}
    best = None
    for col in sorted(rm.H_CATALOG, key=lambda k: rm.H_CATALOG[k]["w"]):
        out = _grow_truss(col, cand)
        if out and (best is None or _frame_weight(out) < _frame_weight(best)):
            best = out
    if best is None:
        raise RuntimeError("ไม่มีชุดหน้าตัดในรายการที่ผ่านเกณฑ์")
    return best


if __name__ == "__main__":
    sizes, nodes, members, supports, cases, case_res, combos, W, rows, defl = select()
    print("หน้าตัดที่เลือก:", sizes)
    for g in ("TC", "BC", "WEB", "COL"):
        r = max((r for r in rows if r["group"] == g), key=lambda r: r["dcr"])
        print(f"  {g:4s} {r['sec']:18s} DCR {r['dcr']:.2f}  ชิ้น {r['member']:16s} {r['combo']:15s} "
              f"N={r['N']:8.0f} kg  M={r['M']/100:7.0f} kg·m  KL/r={r['lam']:.0f}")
    for k, (v, lim) in defl.items():
        print(f"  {k:42s} {v:6.2f} cm ≤ {lim:6.2f}  {'ผ่าน' if v <= lim else 'ไม่ผ่าน'}")
