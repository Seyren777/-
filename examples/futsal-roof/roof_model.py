"""แบบจำลองโครงข้อแข็งภายใน (เสา 2 ต้น + โครงถักโค้ง) ของหลังคาสนามฟุตซอล 18 × 27 m

หน่วยภายใน: kg, cm · ระนาบโครง x–z (z ขึ้น)
- เสาและคอร์ด = frame element (รับแรงตามแกน + โมเมนต์)
- เอว (ตั้ง/ทแยง) = truss element (หมุดสองปลาย รับแรงตามแกนอย่างเดียว)
"""
import math

import numpy as np

# ================================================================ เรขาคณิต
SPAN = 1800.0            # cm ระยะศูนย์กลางเสา
Z_EAVE = 700.0           # cm คอร์ดบนที่แนวเสา (จุดต่ำสุดของหลังคา)
Z_APEX = 900.0           # cm คอร์ดบนที่ยอด
DEPTH = 90.0             # cm ความลึกโครงถักตามแนวรัศมี
N_PANEL = 18             # ช่องคอร์ดบน (≈ 1.03 m = ระยะแป)
BAY = 450.0              # cm ระยะห่างโครง (ความกว้างรับน้ำหนัก)
N_FRAME = 7
LENGTH = BAY * (N_FRAME - 1)

RISE = Z_APEX - Z_EAVE
R_TOP = ((SPAN / 2) ** 2 + RISE**2) / (2 * RISE)
XC, ZC = SPAN / 2, Z_APEX - R_TOP
R_BOT = R_TOP - DEPTH
Z_BOT_EAVE = ZC + math.sqrt(R_BOT**2 - (SPAN / 2) ** 2)

E = 2.04e6               # ksc
FY = 2500.0              # ksc (SS400 / STKR400)
FU = 4080.0
STEEL = 7.85e-3          # kg/cm³
CONN = 1.10              # เผื่อแผ่นต่อ/รอยเชื่อม 10 %

# ================================================================ น้ำหนัก (kg/m²)
ROOFING = 10.0           # หลังคาเหล็กรีด 0.47 mm + ฉนวน (ต่อพื้นที่ผิวโค้ง)
PURLIN_KGM = 5.5         # แปตัวซี ≈ C125×50×20×3.2 (kg/m)
HANGING = 10.0           # ไฟและสายไฟ (ต่อพื้นที่ผัง) — ไม่นับใน 0.6D
LIVE = 50.0              # นจ.หลังคา กฎกระทรวง 2566 ข้อ 11 (ต่อพื้นที่ผัง)

# แรงลม มยผ. 1311 (ใช้ค่าสมมติ — ต้องยืนยันกับตัวมาตรฐาน)
V50 = 25.0               # m/s กลุ่ม 1 (อุทัยธานี) T_F = 1.0
Q_REF = 0.5 * 1.25 * V50**2 / 9.80665   # kg/m² = 39.8
IW = 1.15                # ประเภทความสำคัญ "มาก" (โรงเรียน) — สมมติ
CE = 1.0                 # สภาพภูมิประเทศโล่ง z ≈ 9 m: (9/10)^0.2 = 0.98 → ปัดขึ้น
Q_W = Q_REF * IW * CE    # kg/m²
CPCG_UPLIFT = -1.3       # ⚠ สมมติ: แรงยกสุทธิทั้งหลังคา
CPCG_WINDWARD = -1.6     # ⚠ สมมติ: ครึ่งต้นลม (กรณีไม่สมมาตร)
CPCG_LEEWARD = -0.6      # ⚠ สมมติ: ครึ่งท้ายลม
CPCG_DOWN = 0.8          # ⚠ สมมติ: แรงกดสุทธิ
CFCG_COL = 2.0           # ⚠ สมมติ: แรงลากบนเสา H (ต่อความลึกหน้าตัด)

# แผ่นดินไหว (บริเวณที่ 2) — ไม่มี S_S, S_1 รายอำเภอ ใช้ค่าสมมติแบบเผื่อสูง
SDS_ASSUMED = 0.50
IE = 1.25
R_SEISMIC = 3.0          # โครงเหล็กที่ไม่ได้ออกแบบรายละเอียดต้านแผ่นดินไหวเป็นพิเศษ
CS = SDS_ASSUMED * IE / R_SEISMIC


# ================================================================ หน้าตัด
def hss(B, H, t):
    """เหล็กกล่อง B (กว้าง, นอกระนาบ) × H (ลึก, ในระนาบ) × t (mm) → คุณสมบัติหน่วย cm"""
    B, H, t = B / 10, H / 10, t / 10
    bi, hi = B - 2 * t, H - 2 * t
    A_sharp = B * H - bi * hi
    corner = (4 - math.pi) * ((2 * t) ** 2 - t**2)          # มุมโค้ง ro = 2t, ri = t
    k = (A_sharp - corner) / A_sharp
    Ix = (B * H**3 - bi * hi**3) / 12 * k                    # ดัดในระนาบ
    Iy = (H * B**3 - hi * bi**3) / 12 * k
    Zx = (B * H**2 / 4 - bi * hi**2 / 4) * k
    Zy = (H * B**2 / 4 - hi * bi**2 / 4) * k
    A = A_sharp * k
    return dict(kind="HSS", B=B, H=H, t=t, A=A, Ix=Ix, Iy=Iy, Sx=Ix / (H / 2), Sy=Iy / (B / 2),
                Zx=Zx, Zy=Zy, rx=math.sqrt(Ix / A), ry=math.sqrt(Iy / A), w=A * 100 * STEEL)


def hshape(h, b, tw, tf):
    """เหล็ก H (mm) ไม่รวมมุมโค้งโคนปีก (ค่าต่ำกว่าตารางเล็กน้อย = ปลอดภัย) → cm"""
    h, b, tw, tf = h / 10, b / 10, tw / 10, tf / 10
    hw = h - 2 * tf
    A = 2 * b * tf + hw * tw
    Ix = (b * h**3 - (b - tw) * hw**3) / 12
    Iy = (2 * tf * b**3 + hw * tw**3) / 12
    Zx = b * tf * (h - tf) + tw * hw**2 / 4
    Zy = 2 * tf * b**2 / 4 + hw * tw**2 / 4
    h0 = h - tf
    J = (2 * b * tf**3 + h0 * tw**3) / 3
    Cw = Iy * h0**2 / 4
    return dict(kind="H", h=h, b=b, tw=tw, tf=tf, A=A, Ix=Ix, Iy=Iy, Sx=Ix / (h / 2), Sy=Iy / (b / 2),
                Zx=Zx, Zy=Zy, rx=math.sqrt(Ix / A), ry=math.sqrt(Iy / A), J=J, Cw=Cw, h0=h0,
                w=A * 100 * STEEL)


HSS_CATALOG = {f"□{B}×{H}×{t}": hss(B, H, t) for B, H, t in [
    (50, 50, 2.3), (50, 50, 3.2), (50, 100, 2.3), (50, 100, 3.2), (50, 100, 4.5),
    (75, 75, 2.3), (75, 75, 3.2), (75, 75, 4.5), (75, 125, 3.2), (75, 125, 4.5),
    (100, 100, 2.3), (100, 100, 3.2), (100, 100, 4.5), (100, 150, 3.2), (100, 150, 4.5),
    (125, 125, 3.2), (125, 125, 4.5), (150, 150, 4.5), (150, 150, 6.0)]}
H_CATALOG = {f"H-{h}×{b}×{tw}×{tf}": hshape(h, b, tw, tf) for h, b, tw, tf in [
    (150, 75, 5, 7), (150, 150, 7, 10), (175, 175, 7.5, 11), (200, 100, 5.5, 8), (200, 200, 8, 12),
    (250, 125, 6, 9), (250, 250, 9, 14), (300, 150, 6.5, 9), (300, 300, 10, 15), (350, 175, 7, 11)]}
CATALOG = {**HSS_CATALOG, **H_CATALOG}


# ================================================================ สร้างแบบจำลอง
def build(sizes):
    """sizes: dict กลุ่ม → ชื่อหน้าตัด {'TC','BC','WEB','COL'}"""
    nodes, members = {}, []

    a0 = math.atan2(Z_EAVE - ZC, 0 - XC)
    a1 = math.atan2(Z_EAVE - ZC, SPAN - XC)
    angles = np.linspace(a0, a1, N_PANEL + 1)
    for i, a in enumerate(angles):
        nodes[f"t{i}"] = (XC + R_TOP * math.cos(a), ZC + R_TOP * math.sin(a))
        nodes[f"b{i}"] = (XC + R_BOT * math.cos(a), ZC + R_BOT * math.sin(a))
    nodes["b0"] = (0.0, Z_BOT_EAVE)
    nodes[f"b{N_PANEL}"] = (SPAN, Z_BOT_EAVE)

    col_levels = [0, 100, 200, 300, 400, 500, Z_BOT_EAVE]
    for side, x, top, bot in (("L", 0.0, "t0", "b0"), ("R", SPAN, f"t{N_PANEL}", f"b{N_PANEL}")):
        chain = []
        for k, z in enumerate(col_levels[:-1]):
            nodes[f"c{side}{k}"] = (x, float(z))
            chain.append(f"c{side}{k}")
        chain += [bot, top]
        for a, b in zip(chain[:-1], chain[1:]):
            members.append(dict(name=f"COL{side}:{a}-{b}", i=a, j=b, group="COL", kind="frame"))

    for i in range(N_PANEL):
        members.append(dict(name=f"TC{i+1}", i=f"t{i}", j=f"t{i+1}", group="TC", kind="frame"))
        members.append(dict(name=f"BC{i+1}", i=f"b{i}", j=f"b{i+1}", group="BC", kind="frame"))
    for i in range(1, N_PANEL):
        members.append(dict(name=f"V{i}", i=f"b{i}", j=f"t{i}", group="WEB", kind="truss"))
    for i in range(N_PANEL):
        a, b = (f"t{i}", f"b{i+1}") if i % 2 == 0 else (f"b{i}", f"t{i+1}")
        members.append(dict(name=f"D{i+1}", i=a, j=b, group="WEB", kind="truss"))

    for m in members:
        m["sec_name"] = sizes[m["group"]]
        m["sec"] = CATALOG[m["sec_name"]]
    supports = ["cL0", "cR0"]
    return nodes, members, supports


def length(nodes, m):
    (x1, z1), (x2, z2) = nodes[m["i"]], nodes[m["j"]]
    return math.hypot(x2 - x1, z2 - z1)


# ================================================================ น้ำหนักบรรทุก (แรงที่จุดต่อ kg + แรงแผ่บนเสา)
def top_tributary(nodes):
    """ความยาวโค้งและความกว้างผังที่จุดต่อคอร์ดบนแต่ละจุดรับ (cm)"""
    arc, plan = {}, {}
    for i in range(N_PANEL + 1):
        a = nodes[f"t{max(i-1, 0)}"] if i > 0 else nodes["t0"]
        b = nodes[f"t{min(i+1, N_PANEL)}"] if i < N_PANEL else nodes[f"t{N_PANEL}"]
        p = nodes[f"t{i}"]
        arc[i] = (math.dist(a, p) + math.dist(p, b)) / 2
        plan[i] = (abs(p[0] - a[0]) + abs(b[0] - p[0])) / 2
    return arc, plan


def outward_normal(nodes, i):
    x, z = nodes[f"t{i}"]
    n = np.array([x - XC, z - ZC])
    return n / np.linalg.norm(n)


def load_cases(nodes, members):
    """คืน dict กรณีน้ำหนัก → (แรงที่จุดต่อ {node: [Fx, Fz]}, แรงแผ่ตั้งฉากบนชิ้นส่วนเสา {name: q kg/cm})"""
    arc, plan = top_tributary(nodes)
    trib = BAY / 100                                     # m
    cases = {k: ({}, {}) for k in ("D", "SD", "L", "W1", "W2", "W2R", "W4", "E")}

    def add(case, n, fx, fz):
        F = cases[case][0].setdefault(n, np.zeros(2))
        F += (fx, fz)

    for i in range(N_PANEL + 1):
        add("D", f"t{i}", 0, -(ROOFING * arc[i] / 100 * trib + PURLIN_KGM * trib))
        add("SD", f"b{i}", 0, -HANGING * plan[i] / 100 * trib)
        add("L", f"t{i}", 0, -LIVE * plan[i] / 100 * trib)
        nrm = outward_normal(nodes, i)
        area = arc[i] / 100 * trib                       # m²
        x = nodes[f"t{i}"][0]
        for case, cp in (("W1", CPCG_UPLIFT), ("W4", CPCG_DOWN),
                         ("W2", CPCG_WINDWARD if x < SPAN / 2 else CPCG_LEEWARD if x > SPAN / 2 else
                          (CPCG_WINDWARD + CPCG_LEEWARD) / 2),
                         ("W2R", CPCG_LEEWARD if x < SPAN / 2 else CPCG_WINDWARD if x > SPAN / 2 else
                          (CPCG_WINDWARD + CPCG_LEEWARD) / 2)):
            f = -cp * Q_W * area * nrm                   # + Cp = กดเข้าหาผิว = สวนทิศ normal ออก
            add(case, f"t{i}", *f)

    for m in members:                                    # น้ำหนักเหล็ก
        w = m["sec"]["w"] * CONN * length(nodes, m) / 100
        add("D", m["i"], 0, -w / 2)
        add("D", m["j"], 0, -w / 2)

    for m in members:                                    # แรงลากบนเสา (ทิศ +x สำหรับ W1, W2 · −x สำหรับ W2R)
        if m["group"] != "COL":
            continue
        depth = m["sec"].get("h", m["sec"].get("H"))
        q = Q_W * CFCG_COL * depth / 100 / 100           # kg/cm
        # เสาวางแนวดิ่ง: แกน y เฉพาะที่ชี้ไป −x (ดู local frame ใน solve) → แรง +x = q_local ลบ
        for case, sgn in (("W1", 1), ("W2", 1), ("W2R", -1)):
            cases[case][1][m["name"]] = -sgn * q

    W_seis = -sum(F[1] for F in cases["D"][0].values()) - sum(F[1] for F in cases["SD"][0].values())
    for n in ("t0", f"t{N_PANEL}"):
        add("E", n, CS * W_seis / 2, 0)
    return cases, W_seis


COMBOS = {                                               # ASD กฎกระทรวง 2566 ข้อ 6
    "D+L":            {"D": 1, "SD": 1, "L": 1},
    "D+0.75(L+W↓)":   {"D": 1, "SD": 1, "L": 0.75, "W4": 0.75},
    "D+0.75(L+W2)":   {"D": 1, "SD": 1, "L": 0.75, "W2": 0.75},
    "D+0.75(L+W2R)":  {"D": 1, "SD": 1, "L": 0.75, "W2R": 0.75},
    "0.6D+W1":        {"D": 0.6, "W1": 1},
    "0.6D+W2":        {"D": 0.6, "W2": 1},
    "0.6D+W2R":       {"D": 0.6, "W2R": 1},
    "D+0.7E":         {"D": 1, "SD": 1, "E": 0.7},
    "D-0.7E":         {"D": 1, "SD": 1, "E": -0.7},
    "0.6D+0.7E":      {"D": 0.6, "E": 0.7},
    "0.6D-0.7E":      {"D": 0.6, "E": -0.7},
}


# ================================================================ ตัวคำนวณ 2 มิติ (u, w, θ ต่อจุดต่อ)
def solve(nodes, members, supports, nodal, dist):
    names = list(nodes)
    idx = {n: k for k, n in enumerate(names)}
    ndof = 3 * len(names)
    K = np.zeros((ndof, ndof))
    F = np.zeros(ndof)
    for n, f in nodal.items():
        F[3 * idx[n]:3 * idx[n] + 2] += f
    cache = []
    for m in members:
        (x1, z1), (x2, z2) = nodes[m["i"]], nodes[m["j"]]
        L = math.hypot(x2 - x1, z2 - z1)
        c, s = (x2 - x1) / L, (z2 - z1) / L
        T = np.zeros((6, 6))
        for k in (0, 3):
            T[k:k + 2, k:k + 2] = [[c, s], [-s, c]]
            T[k + 2, k + 2] = 1
        A, I = m["sec"]["A"], m["sec"]["Ix"]
        kl = np.zeros((6, 6))
        ea = E * A / L
        kl[np.ix_([0, 3], [0, 3])] = [[ea, -ea], [-ea, ea]]
        q = dist.get(m["name"], 0.0)
        feq = np.zeros(6)
        if m["kind"] == "frame":
            a, b, cc, d = 12 * E * I / L**3, 6 * E * I / L**2, 4 * E * I / L, 2 * E * I / L
            kl[np.ix_([1, 2, 4, 5], [1, 2, 4, 5])] = [[a, b, -a, b], [b, cc, -b, d],
                                                       [-a, -b, a, -b], [b, d, -b, cc]]
            feq[[1, 2, 4, 5]] = [q * L / 2, q * L**2 / 12, q * L / 2, -q * L**2 / 12]
        dofs = np.r_[3 * idx[m["i"]]:3 * idx[m["i"]] + 3, 3 * idx[m["j"]]:3 * idx[m["j"]] + 3]
        K[np.ix_(dofs, dofs)] += T.T @ kl @ T
        F[dofs] += T.T @ feq
        cache.append((m, L, T, kl, feq, dofs, q))

    fixed = np.concatenate([np.arange(3 * idx[n], 3 * idx[n] + 3) for n in supports])
    free = np.setdiff1d(np.arange(ndof), fixed)
    u = np.zeros(ndof)
    u[free] = np.linalg.solve(K[np.ix_(free, free)], F[free])
    R = K @ u - F

    out = {}
    for m, L, T, kl, feq, dofs, q in cache:
        f = kl @ (T @ u[dofs]) - feq
        N = f[3]                                         # + = ดึง
        xs = np.linspace(0, L, 11)
        M = -f[2] + f[1] * xs + q * xs**2 / 2            # kg·cm
        V = f[1] + q * xs
        out[m["name"]] = dict(N=N, M=M, V=V, x=xs, L=L)
    disp = {n: u[3 * idx[n]:3 * idx[n] + 3] for n in names}
    reac = {n: R[3 * idx[n]:3 * idx[n] + 3] for n in supports}
    return out, disp, reac


def run_all(sizes):
    nodes, members, supports = build(sizes)
    cases, W_seis = load_cases(nodes, members)
    case_res = {c: solve(nodes, members, supports, *cases[c]) for c in cases}
    combos = {}
    for name, fac in COMBOS.items():
        res = {}
        for m in members:
            parts = [(f, case_res[c][0][m["name"]]) for c, f in fac.items()]
            res[m["name"]] = dict(N=sum(f * r["N"] for f, r in parts),
                                  M=sum(f * r["M"] for f, r in parts),
                                  V=sum(f * r["V"] for f, r in parts), L=parts[0][1]["L"])
        disp = {n: sum(f * case_res[c][1][n] for c, f in fac.items()) for n in nodes}
        reac = {n: sum(f * case_res[c][2][n] for c, f in fac.items()) for n in supports}
        combos[name] = (res, disp, reac)
    return nodes, members, supports, cases, case_res, combos, W_seis
