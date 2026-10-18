"""วิเคราะห์โครงอาคาร คสล. 3 มิติ ด้วยวิธี direct stiffness (frame element 12 DOF)
แล้ววาดแผนภาพโมเมนต์ดัดของคานแบบ midas Gen

หน่วยภายใน: kg, cm  ·  แสดงผลโมเมนต์เป็น kg·m (kgf·m)
โมเมนต์คาน: + = ท้องคานรับแรงดึง (sagging) · − = หลังคานรับแรงดึง (hogging)

ตัวอย่าง: อาคาร 2 ชั้น 4 ช่วง (แกน X 4 × 4 m) × 2 ช่วง (แกน Y 2 × 5 m) สูงชั้นละ 3.5 m
ตัวคูณน้ำหนัก 1.4D + 1.7L (กฎกระทรวง พ.ศ. 2566)
"""
import math

import numpy as np

# ---------------------------------------------------------------- ข้อมูลนำเข้า
XS = [0, 400, 800, 1200, 1600]          # cm  แกน 1–5
YS = [0, 500, 1000]                     # cm  แกน A–C
ZS = [0, 350, 700]                      # cm  ฐาน, ชั้น 2, หลังคา
GRID_X = "12345"
GRID_Y = "ABC"

FC = 210.0                              # ksc (ทรงกระบอก)
E = 15100 * math.sqrt(FC)               # ksc
G = E / (2 * (1 + 0.2))
COL = (30, 30)                          # cm  b × h
BEAM = (25, 50)                         # cm  b × h

SLAB_DL = 0.12 * 2400 + 100             # kg/m²  พื้นหนา 12 cm + วัสดุปูผิว
LIVE = {350: 250, 700: 100}             # kg/m²  ชั้น 2 (สำนักงาน, สมมติ) · หลังคา
WALL = 180 * 3.0                        # kg/m   ผนังก่ออิฐครึ่งแผ่นสูง 3 m บนคานริมชั้น 2
BEAM_SW = BEAM[0] * BEAM[1] / 1e4 * 2400  # kg/m
FACTOR_D, FACTOR_L = 1.4, 1.7


def rect(b, h):
    """คุณสมบัติหน้าตัดสี่เหลี่ยม: A, I รอบแกนนอน (ดัดในระนาบดิ่ง), I รอบแกนดิ่ง, J"""
    a, c = max(b, h), min(b, h)
    J = a * c**3 * (1 / 3 - 0.21 * c / a * (1 - c**4 / (12 * a**4)))
    return b * h, b * h**3 / 12, h * b**3 / 12, J


# ---------------------------------------------------------------- สร้างแบบจำลอง
def build():
    nodes = {}
    for k, z in enumerate(ZS):
        for j, y in enumerate(YS):
            for i, x in enumerate(XS):
                nodes[f"{GRID_X[i]}{GRID_Y[j]}-{k}"] = (x, y, z)

    # แต่ละชิ้นส่วนเก็บน้ำหนักเป็นรายการ (s0, s1, q0, q1): แรงแผ่เชิงเส้นจาก s0 ถึง s1 (cm), kg/cm, ลง = +
    members = []
    for k in range(1, len(ZS)):
        for j in range(len(YS)):
            for i in range(len(XS)):
                members.append(dict(name=f"C{GRID_X[i]}{GRID_Y[j]}-{k}", i=f"{GRID_X[i]}{GRID_Y[j]}-{k-1}",
                                    j=f"{GRID_X[i]}{GRID_Y[j]}-{k}", sec=rect(*COL), loads=[], kind="col"))

    for k in range(1, len(ZS)):
        beam = {}
        for j in range(len(YS)):
            for i in range(len(XS) - 1):
                beam[("X", i, j)] = dict(name=f"BX{GRID_X[i]}{GRID_X[i+1]}{GRID_Y[j]}-{k}",
                                         i=f"{GRID_X[i]}{GRID_Y[j]}-{k}", j=f"{GRID_X[i+1]}{GRID_Y[j]}-{k}",
                                         sec=rect(*BEAM), loads=[], kind="beam")
        for i in range(len(XS)):
            for j in range(len(YS) - 1):
                beam[("Y", i, j)] = dict(name=f"BY{GRID_X[i]}{GRID_Y[j]}{GRID_Y[j+1]}-{k}",
                                         i=f"{GRID_X[i]}{GRID_Y[j]}-{k}", j=f"{GRID_X[i]}{GRID_Y[j+1]}-{k}",
                                         sec=rect(*BEAM), loads=[], kind="beam")

        # แผ่นพื้นสองทาง: แบ่งพื้นที่รับน้ำหนักด้วยเส้น 45° → คานด้านสั้นรับสามเหลี่ยม คานด้านยาวรับคางหมู
        wu = (FACTOR_D * SLAB_DL + FACTOR_L * LIVE[ZS[k]]) / 1e4    # kg/cm²
        for j in range(len(YS) - 1):
            for i in range(len(XS) - 1):
                lx, ly = XS[i + 1] - XS[i], YS[j + 1] - YS[j]
                a = min(lx, ly) / 2                                  # ระยะถึงสันหลังคาแบ่งน้ำหนัก
                peak = wu * a
                for key, L in ((("X", i, j), lx), (("X", i, j + 1), lx), (("Y", i, j), ly), (("Y", i + 1, j), ly)):
                    rise = min(a, L / 2)
                    beam[key]["loads"] += [(0, rise, 0, peak), (rise, L - rise, peak, peak), (L - rise, L, peak, 0)]

        for (d, i, j), m in beam.items():
            L = (XS[i + 1] - XS[i]) if d == "X" else (YS[j + 1] - YS[j])
            edge = (d == "X" and j in (0, len(YS) - 1)) or (d == "Y" and i in (0, len(XS) - 1))
            w = FACTOR_D * BEAM_SW + (FACTOR_D * WALL if k == 1 and edge else 0)
            m["loads"].append((0, L, w / 100, w / 100))
            members.append(m)
    supports = [n for n, (x, y, z) in nodes.items() if z == 0]
    return nodes, members, supports


def load_at(loads, s):
    """ความเข้มแรงแผ่ (kg/cm, ลง = +) ที่ตำแหน่ง s"""
    q = np.zeros_like(s)
    end = s.max()
    for s0, s1, q0, q1 in loads:
        if s1 > s0:
            inside = (s >= s0) & ((s < s1) | ((s1 >= end) & (s <= s1)))   # ช่วงครึ่งเปิด กันนับรอยต่อซ้ำ
            q[inside] += q0 + (q1 - q0) * (s[inside] - s0) / (s1 - s0)
    return q


def total_load(m, L):
    return sum((q0 + q1) / 2 * (s1 - s0) for s0, s1, q0, q1 in m["loads"])


# ---------------------------------------------------------------- ตัวคำนวณ
def local_axes(p1, p2):
    """แกนเฉพาะที่: x ตามชิ้นส่วน · คาน: y ชี้ขึ้น (ดัดในระนาบดิ่งรอบแกน z) · เสา: y ตามแกน X"""
    ex = (np.array(p2) - np.array(p1)) / np.linalg.norm(np.subtract(p2, p1))
    ref = np.array([1.0, 0, 0]) if abs(ex[2]) > 0.999 else np.array([0, 0, 1.0])
    ez = np.cross(ex, ref)
    ez /= np.linalg.norm(ez)
    ey = np.cross(ez, ex)
    return np.vstack([ex, ey, ez])


def k_local(A, Iz, Iy, J, L):
    k = np.zeros((12, 12))
    k[0, 0] = k[6, 6] = E * A / L
    k[0, 6] = -E * A / L
    k[3, 3] = k[9, 9] = G * J / L
    k[3, 9] = -G * J / L
    a, b, c, d = 12 * E * Iz / L**3, 6 * E * Iz / L**2, 4 * E * Iz / L, 2 * E * Iz / L
    k[1, 1] = k[7, 7] = a; k[1, 7] = -a
    k[1, 5] = k[1, 11] = b; k[5, 7] = k[7, 11] = -b
    k[5, 5] = k[11, 11] = c; k[5, 11] = d
    a, b, c, d = 12 * E * Iy / L**3, 6 * E * Iy / L**2, 4 * E * Iy / L, 2 * E * Iy / L
    k[2, 2] = k[8, 8] = a; k[2, 8] = -a
    k[2, 4] = k[2, 10] = -b; k[4, 8] = k[8, 10] = b
    k[4, 4] = k[10, 10] = c; k[4, 10] = d
    return k + np.triu(k, 1).T


def solve(nodes, members, supports):
    names = list(nodes)
    idx = {n: q for q, n in enumerate(names)}
    ndof = 6 * len(names)
    K = np.zeros((ndof, ndof))
    F = np.zeros(ndof)
    cache = []
    for m in members:
        p1, p2 = nodes[m["i"]], nodes[m["j"]]
        L = float(np.linalg.norm(np.subtract(p2, p1)))
        A, Iz, Iy, J = m["sec"]
        R3 = local_axes(p1, p2)
        T = np.kron(np.eye(4), R3)
        kl = k_local(A, Iz, Iy, J, L)
        s = np.linspace(0, L, 801)
        qy = -load_at(m["loads"], s)                  # แรงแผ่ในแกน y เฉพาะที่ (ลง = −)
        xi = s / L
        shape = [1 - 3*xi**2 + 2*xi**3, L*(xi - 2*xi**2 + xi**3), 3*xi**2 - 2*xi**3, L*(-xi**2 + xi**3)]
        feq = np.zeros(12)
        feq[[1, 5, 7, 11]] = [np.trapezoid(N * qy, s) for N in shape]   # แรงยึดปลาย (Hermite)
        dofs = np.r_[6 * idx[m["i"]]:6 * idx[m["i"]] + 6, 6 * idx[m["j"]]:6 * idx[m["j"]] + 6]
        K[np.ix_(dofs, dofs)] += T.T @ kl @ T
        F[dofs] += T.T @ feq
        cache.append((m, L, T, kl, feq, dofs, (s, qy)))

    fixed = np.r_[[np.arange(6 * idx[n], 6 * idx[n] + 6) for n in supports]].ravel()
    free = np.setdiff1d(np.arange(ndof), fixed)
    u = np.zeros(ndof)
    u[free] = np.linalg.solve(K[np.ix_(free, free)], F[free])
    R = K @ u - F

    results = {}
    for m, L, T, kl, feq, dofs, (s, qy) in cache:
        f = kl @ (T @ u[dofs]) - feq                  # แรงปลายชิ้นส่วนในแกนเฉพาะที่
        # M(x) = −Mz1 + Vy1·x + ∫₀ˣ (x − t)·qy(t) dt   (kg·cm, + = sagging)
        Q = np.concatenate([[0], np.cumsum((qy[1:] + qy[:-1]) / 2 * np.diff(s))])          # ∫ q
        SQ = np.concatenate([[0], np.cumsum((s[1:] * qy[1:] + s[:-1] * qy[:-1]) / 2 * np.diff(s))])  # ∫ t·q
        M = -f[5] + f[1] * s + s * Q - SQ
        results[m["name"]] = dict(x=s, M=M / 100, V1=f[1], L=L, end=f)
    disp = {n: u[6 * idx[n]:6 * idx[n] + 6] for n in names}
    reac = {n: R[6 * idx[n]:6 * idx[n] + 6] for n in supports}
    return results, disp, reac


if __name__ == "__main__":
    nodes, members, supports = build()
    res, disp, reac = solve(nodes, members, supports)

    total = sum(total_load(m, res[m["name"]]["L"]) for m in members)
    rz = sum(r[2] for r in reac.values())
    print(f"น้ำหนักรวม {total:,.0f} kg · แรงปฏิกิริยารวม {rz:,.0f} kg · ต่างกัน {abs(total - rz):.2e}")
    beams = [m for m in members if m["kind"] == "beam"]
    mmax = max(beams, key=lambda m: res[m["name"]]["M"].max())
    mmin = min(beams, key=lambda m: res[m["name"]]["M"].min())
    print(f"โมเมนต์บวกสูงสุด {res[mmax['name']]['M'].max():,.0f} kg·m ที่ {mmax['name']}")
    print(f"โมเมนต์ลบสูงสุด {res[mmin['name']]['M'].min():,.0f} kg·m ที่ {mmin['name']}")
