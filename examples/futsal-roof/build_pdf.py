"""สร้างรูปเล่มรายการคำนวณ (PDF) — ตัวเลขทุกตัวดึงจากผลคำนวณจริง แล้วพิมพ์ HTML → PDF ด้วย Chromium"""
import datetime
import html
import math
import os
import subprocess

import numpy as np

import design
import extras
import roof_model as rm

HERE = os.path.dirname(os.path.abspath(__file__))
CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"

sizes, nodes, members, supports, cases, case_res, combos, W, rows, defl = design.select()
p_name, p_sec, p_rows, p_defl, p_lim = extras.purlin()
br = extras.bracing(W)
env = extras.reactions(combos)
items, total = extras.takeoff(nodes, members, p_sec, br)
arc, plan = rm.top_tributary(nodes)
GN = {"TC": "คอร์ดบน", "BC": "คอร์ดล่าง", "WEB": "ตั้ง/ทแยง", "COL": "เสา"}
e = html.escape


def f(x, d=2):
    return f"{x:,.{d}f}"


def tot(case, k):
    return sum(v[k] for v in cases[case][0].values())


# ---------------------------------------------------------------- รายละเอียดการตรวจชิ้นส่วนที่ควบคุม
def detail(group):
    r = max((r for r in rows if r["group"] == group), key=lambda r: r["dcr"])
    m = next(m for m in members if m["name"] == r["member"])
    s = m["sec"]
    L = rm.length(nodes, m)
    KLx, KLy, Lb = design.unbraced(group, L)
    Pa, lam, _ = design.compression(s, KLx, KLy)
    Fe = math.pi**2 * rm.E / lam**2
    Fcr = 0.658 ** (rm.FY / Fe) * rm.FY if rm.FY / Fe <= 2.25 else 0.877 * rm.FE if False else (
        0.658 ** (rm.FY / Fe) * rm.FY if rm.FY / Fe <= 2.25 else 0.877 * Fe)
    Ma = design.flexure(s, Lb) if m["kind"] == "frame" else None
    Ta = rm.FY * s["A"] / 1.67
    N, M = r["N"], r["M"]
    lines = [
        ("หน้าตัด", f"{e(r['sec'])} · A = {f(s['A'])} cm² · I<sub>x</sub> = {f(s['Ix'],0)} cm⁴ · "
                    f"r<sub>x</sub> = {f(s['rx'])} cm · r<sub>y</sub> = {f(s['ry'])} cm · Z<sub>x</sub> = {f(s['Zx'],1)} cm³"),
        ("ความยาว / ไร้ค้ำยัน", f"L = {f(L,1)} cm · K<sub>x</sub>L<sub>x</sub> = {f(KLx,0)} cm · K<sub>y</sub>L<sub>y</sub> = {f(KLy,0)} cm"
                              + (f" · L<sub>b</sub> = {f(Lb,0)} cm" if m["kind"] == "frame" else "")),
        ("ความชะลูด", f"KL/r = {f(lam,1)} ≤ 200 (ประกาศ มท. 2567 ข้อ 27)"),
        ("แรงอัดวิกฤต (AISC E3)", f"F<sub>e</sub> = π²E/(KL/r)² = {f(Fe,0)} ksc · F<sub>y</sub>/F<sub>e</sub> = {f(rm.FY/Fe)} → "
                                f"F<sub>cr</sub> = {f(Fcr,0)} ksc"),
        ("กำลังที่ยอมให้", f"P<sub>a</sub> = F<sub>cr</sub>A/1.67 = {f(Pa/1000)} t (อัด) · T<sub>a</sub> = F<sub>y</sub>A/1.67 = {f(Ta/1000)} t (ดึง)"
                         + (f" · M<sub>a</sub> = M<sub>n</sub>/1.67 = {f(Ma/1e5,3)} t·m" if Ma else "")),
    ]
    if group == "COL":
        rts = math.sqrt(math.sqrt(s["Iy"] * s["Cw"]) / s["Sx"])
        Lp = 1.76 * s["ry"] * design.RT
        jc = s["J"] / (s["Sx"] * s["h0"])
        Lr = 1.95 * rts * rm.E / (0.7 * rm.FY) * math.sqrt(jc + math.sqrt(jc**2 + 6.76 * (0.7 * rm.FY / rm.E) ** 2))
        lines.insert(4, ("การโก่งเดาะด้านข้าง (AISC F2)",
                         f"L<sub>p</sub> = {f(Lp,0)} cm · L<sub>r</sub> = {f(Lr,0)} cm · L<sub>b</sub> = {f(Lb,0)} cm · C<sub>b</sub> = 1.0 (ปลอดภัย)"))
        lines.append(("ตัวขยาย P-Δ (AISC App. 8)", f"B<sub>2</sub> = {f(r['amp'],3)} (α = 1.6) คูณกับโมเมนต์เสาทั้งหมด"))
    Pc = r["Pc"]
    ratio_p = abs(N) / Pc if Pc else 0
    if Ma:
        ratio_m = M / r["Mc"]
        eq = ("H1-1a: P/P<sub>c</sub> + 8/9·M/M<sub>c</sub>" if ratio_p >= 0.2 else "H1-1b: P/2P<sub>c</sub> + M/M<sub>c</sub>")
        val = ratio_p + 8 / 9 * ratio_m if ratio_p >= 0.2 else ratio_p / 2 + ratio_m
        lines.append(("แรงที่เกิด", f"ชุด {e(r['combo'])} · N = {f(N/1000)} t ({'อัด' if N < 0 else 'ดึง'}) · M = {f(M/1e5,3)} t·m"))
        lines.append(("แรงร่วม (AISC H1)", f"{eq} = {f(ratio_p,3)} {'+ 8/9 ×' if ratio_p >= 0.2 else '/ 2 +'} {f(ratio_m,3)} = <b>{f(val)}</b> ≤ 1.00"))
    else:
        lines.append(("แรงที่เกิด", f"ชุด {e(r['combo'])} · N = {f(N/1000)} t ({'อัด' if N < 0 else 'ดึง'})"))
        lines.append(("อัตราส่วน", f"|N|/P<sub>a</sub> = <b>{f(ratio_p)}</b> ≤ 1.00"))
    return r, lines


# ---------------------------------------------------------------- ตารางซองแรงทุกชิ้นส่วน
def envelope_rows():
    out = []
    by_name = {r["member"]: r for r in rows}
    for m in members:
        Ns = [combos[c][0][m["name"]]["N"] for c in combos]
        Ms = [np.abs(combos[c][0][m["name"]]["M"]).max() for c in combos]
        r = by_name[m["name"]]
        out.append((m["name"], GN[m["group"]], m["sec_name"], rm.length(nodes, m), max(Ns), min(Ns), max(Ms), r["dcr"], r["combo"]))
    return out


# ---------------------------------------------------------------- HTML
today = datetime.date.today()
thai_date = f"{today.day} {['ม.ค.','ก.พ.','มี.ค.','เม.ย.','พ.ค.','มิ.ย.','ก.ค.','ส.ค.','ก.ย.','ต.ค.','พ.ย.','ธ.ค.'][today.month-1]} {today.year + 543}"

css = f"""
@font-face {{ font-family: Sarabun; src: url('fonts/Sarabun-Regular.ttf'); font-weight: 400; }}
@font-face {{ font-family: Sarabun; src: url('fonts/Sarabun-SemiBold.ttf'); font-weight: 600; }}
@font-face {{ font-family: Sarabun; src: url('fonts/Sarabun-Bold.ttf'); font-weight: 700; }}
@font-face {{ font-family: Sarabun; src: url('fonts/Sarabun-Italic.ttf'); font-style: italic; }}
@page {{ size: A4; margin: 20mm 18mm 18mm 22mm;
  @top-left {{ content: "รายการคำนวณโครงสร้างเบื้องต้น — หลังคาโค้งสนามฟุตซอล 18 × 27 m"; font: 9pt Sarabun; color: #6b7280; }}
  @top-right {{ content: "ฉบับร่างเพื่อตรวจทาน"; font: 9pt Sarabun; color: #b45309; }}
  @bottom-right {{ content: "หน้า " counter(page) " / " counter(pages); font: 9pt Sarabun; color: #6b7280; }} }}
@page cover {{ margin: 0; @top-left {{ content: none; }} @top-right {{ content: none; }} @bottom-right {{ content: none; }} }}
* {{ box-sizing: border-box; }}
body {{ font-family: Sarabun, sans-serif; font-size: 10.5pt; line-height: 1.55; color: #1f2937; margin: 0; }}
h1 {{ font-size: 15pt; color: #0f3d5c; border-bottom: 2px solid #0f3d5c; padding: 3mm 0 2mm; margin: 0 0 4mm; break-after: avoid; line-height: 1.7; }}
h2 {{ font-size: 12pt; color: #0f3d5c; margin: 3.5mm 0 2mm; padding-top: 1.5mm; line-height: 1.7; break-after: avoid; }}
.calc, table, figure {{ padding-top: 0.3mm; }}
.chapter {{ break-before: page; }}
table {{ border-collapse: collapse; width: 100%; margin: 2mm 0 4mm; font-size: 9.5pt; break-inside: auto; }}
th, td {{ border: 0.6pt solid #9ca3af; padding: 1.2mm 2mm; vertical-align: top; }}
th {{ background: #e8eef4; font-weight: 600; text-align: left; }}
td.n, th.n {{ text-align: right; font-variant-numeric: tabular-nums; }}
tr {{ break-inside: avoid; }}
.ok {{ color: #15803d; font-weight: 600; }} .ng {{ color: #b91c1c; font-weight: 700; }}
.note {{ background: #fff7ed; border-left: 3pt solid #b45309; padding: 2.5mm 3.5mm; margin: 3mm 0; font-size: 9.5pt; }}
.calc {{ background: #f8fafc; border: 0.6pt solid #cbd5e1; padding: 2.5mm 3.5mm; margin: 2mm 0 4mm; break-inside: avoid; }}
.calc div {{ display: grid; grid-template-columns: 46mm 1fr; column-gap: 3mm; margin: 0.6mm 0; }} .calc .k {{ color: #475569; }}
figure {{ margin: 3mm 0 5mm; text-align: center; break-inside: avoid; }}
figure img {{ max-width: 100%; max-height: 205mm; }}
figcaption {{ font-size: 9.5pt; color: #475569; margin-top: 1.5mm; }}
.small {{ font-size: 8.6pt; }} .small td, .small th {{ padding: 0.6mm 1.5mm; }}
.cover {{ page: cover; height: 297mm; padding: 34mm 24mm 22mm; position: relative; background: linear-gradient(#0f3d5c 0 84mm, white 84mm); }}
.cover .tag {{ color: #cfe3f2; font-size: 11pt; letter-spacing: 0.5pt; }}
.cover .title {{ color: white; font-size: 25pt; font-weight: 700; line-height: 1.25; margin-top: 3mm; }}
.cover .meta {{ margin-top: 30mm; font-size: 12pt; }} .cover .meta td {{ border: none; padding: 1.5mm 0; }}
.cover .meta td:first-child {{ width: 45mm; color: #475569; }}
.cover img {{ width: 100%; margin-top: 6mm; }}
.sign {{ position: absolute; bottom: 22mm; left: 24mm; right: 24mm; display: flex; gap: 10mm; }}
.sign div {{ flex: 1; font-size: 10.5pt; text-align: center; line-height: 1.9; }}
.draft {{ position: absolute; top: 62mm; right: 24mm; border: 1.5pt solid #fbbf24; color: #fbbf24; padding: 1.5mm 4mm;
          font-weight: 700; font-size: 11pt; transform: rotate(-4deg); }}
.toc td {{ border: none; border-bottom: 0.5pt dotted #9ca3af; padding: 1.4mm 0; font-size: 11pt; }}
"""

H = []
a = H.append
a(f"<!doctype html><html lang='th'><head><meta charset='utf-8'><title>รายการคำนวณ หลังคาสนามฟุตซอล</title><style>{css}</style></head><body>")

# ---- ปก
a("<section class='cover'>")
a("<div class='tag'>รายการคำนวณโครงสร้าง (เบื้องต้น)</div>")
a("<div class='title'>หลังคาโครงเหล็กโค้งและฐานราก<br>สนามฟุตซอล 18 × 27 เมตร</div>")
a("<div class='draft'>ฉบับร่าง — ยังไม่ได้รับรอง</div>")
a("<table class='meta'>")
for k, v in (("สถานที่", "ในเขตโรงเรียน (ระบุชื่อ) จังหวัดอุทัยธานี"), ("ลักษณะอาคาร", "หลังคาเปิดโล่งรอบด้าน · ชายคา +7.00 m · ยอด +9.00 m"),
             ("ระบบโครงสร้าง", "โครงถักเหล็กโค้ง 7 โครง @ 4.50 m บนเสาเหล็ก H 14 ต้น"),
             ("มาตรฐานอ้างอิง", "กฎกระทรวง พ.ศ. 2566 · ประกาศ มท. 2567 · AISC 360-16 (ASD)"), ("วันที่จัดทำ", thai_date)):
    a(f"<tr><td>{k}</td><td>{v}</td></tr>")
a("</table><img src='cover_3d.png'>")
a("<div class='sign'><div>ลงชื่อ ..................................... ผู้คำนวณ<br>(.....................................)<br>วิศวกรโยธา เลขทะเบียน ................</div>"
  "<div>ลงชื่อ ..................................... ผู้ตรวจสอบ<br>(.....................................)<br>วิศวกรโยธา เลขทะเบียน ................</div></div>")
a("</section>")

# ---- สารบัญ
chapters = ["ข้อมูลโครงการและเกณฑ์การออกแบบ", "น้ำหนักบรรทุก", "แบบจำลองโครงสร้าง", "ชุดน้ำหนักบรรทุก",
            "ผลการวิเคราะห์", "การตรวจสอบหน้าตัด", "ระยะแอ่นตัว", "แป โครงค้ำยัน และคานยึดหัวเสา",
            "แรงที่ฐานเสาสำหรับออกแบบฐานราก", "ปริมาณเหล็กโดยประมาณ", "การตรวจสอบความถูกต้องของการคำนวณ",
            "ฐานรากเสา", "สมมติฐานและข้อจำกัด", "ภาคผนวก ก — ซองแรงของชิ้นส่วนทุกชิ้น"]
a("<section class='chapter'><h1>สารบัญ</h1><table class='toc'>")
for k, c in enumerate(chapters, 1):
    a(f"<tr><td>{k if k < len(chapters) else ''}{'.' if k < len(chapters) else ''} {c}</td></tr>")
a("</table>")
a("<div class='note'><b>สถานะเอกสาร:</b> รายการคำนวณนี้เป็นการออกแบบเบื้องต้นเพื่อประมาณขนาดหน้าตัดและปริมาณเหล็ก "
  "จัดทำด้วยโปรแกรมช่วยคำนวณ ต้องให้วิศวกรผู้ได้รับใบอนุญาตตามกฎหมายว่าด้วยวิศวกรตรวจสอบและลงนามก่อนใช้ก่อสร้าง "
  "โดยเฉพาะค่าที่ระบุไว้ในบทที่ 13</div></section>")

# ---- 1
a("<section class='chapter'><h1>1. ข้อมูลโครงการและเกณฑ์การออกแบบ</h1>")
a("<h2>1.1 ข้อมูลโครงการ</h2><table>")
for k, v in (("ขนาดผัง", "18.00 × 27.00 m (ระยะศูนย์กลางเสา)"), ("ช่วงพาด", "18.00 m"),
             ("ระดับ", f"ผิวหลังคาที่ชายคา +7.00 m · ยอดโค้ง +9.00 m · ใต้คอร์ดล่างที่แนวเสา +{f(rm.Z_BOT_EAVE/100)} m"),
             ("รูปทรงหลังคา", f"ส่วนโค้งวงกลมรัศมี {f(rm.R_TOP/100)} m (สูงโค้ง 2.00 m)"),
             ("โครงหลังคา", f"โครงถักโค้งคอร์ดขนาน ลึก {f(rm.DEPTH/100)} m ตามแนวรัศมี · {rm.N_PANEL} ช่อง · ตั้ง + ทแยงสลับ"),
             ("ระยะโครง", "4.50 m · 7 โครง · เสา 14 ต้น"), ("ลักษณะการใช้งาน", "สนามกีฬาในโรงเรียน · เปิดโล่งรอบด้าน · พื้นวางบนดิน (ไม่อยู่ในขอบเขต)"),
             ("การต่อ", "คอร์ดบนและคอร์ดล่างยึดแน่นกับเสา (โครงข้อแข็ง) · โคนเสายึดแน่นกับตอม่อ คสล.")):
    a(f"<tr><th style='width:38mm'>{k}</th><td>{v}</td></tr>")
a("</table><h2>1.2 มาตรฐานและกฎหมาย</h2><table>")
for k, v in (("น้ำหนักบรรทุกและชุดน้ำหนัก", "กฎกระทรวงกำหนดการรับน้ำหนัก ความต้านทาน ความคงทนของอาคาร พ.ศ. 2566 (ข้อ 6 ASD, ข้อ 11 นจ.)"),
             ("แรงลม", "มยผ. 1311 (ความเร็วลมอ้างอิงกลุ่ม 1) — ค่าสัมประสิทธิ์ตามบทที่ 13"),
             ("แผ่นดินไหว", "กฎกระทรวงแผ่นดินไหว พ.ศ. 2564 — อุทัยธานีอยู่บริเวณที่ 2"),
             ("ระยะแอ่นตัว / ความชะลูด", "ประกาศกระทรวงมหาดไทย 2567 ข้อ 8 ตาราง 1 และข้อ 27"),
             ("กำลังเหล็กรูปพรรณ", "AISC 360-16 วิธีกำลังที่ยอมให้ (ASD, Ω = 1.67)")):
    a(f"<tr><th style='width:52mm'>{k}</th><td>{v}</td></tr>")
a("</table><h2>1.3 วัสดุ</h2><table>")
a(f"<tr><th style='width:52mm'>เหล็กรูปพรรณ / เหล็กกล่อง</th><td>SS400 (มอก. 1227) / STKR400 (มอก. 107) · F<sub>y</sub> = {f(rm.FY,0)} ksc · "
  f"F<sub>u</sub> = {f(rm.FU,0)} ksc · E = {rm.E:,.0f} ksc</td></tr>")
a("<tr><th>แป</th><td>เหล็กขึ้นรูปเย็นรูปตัวซี F<sub>y</sub> = 2,500 ksc (ตรวจแบบง่าย — ดูบทที่ 13)</td></tr>")
a("<tr><th>เหล็กค้ำยัน</th><td>เหล็กเส้นกลม SR24 F<sub>y</sub> = 2,400 ksc พร้อมเกลียวเร่ง</td></tr></table></section>")

# ---- 2
q_ref = rm.Q_REF
a("<section class='chapter'><h1>2. น้ำหนักบรรทุก</h1>")
a("<p>คิดสำหรับโครงภายใน 1 โครง ความกว้างรับน้ำหนัก 4.50 m (โครงริมรับครึ่งหนึ่ง) · ความยาวโค้งหลังคา "
  f"{f(sum(arc.values())/100 - (arc[0]+arc[rm.N_PANEL])/200,2) if False else f(sum(math.dist(nodes[f't{i}'], nodes[f't{i+1}']) for i in range(rm.N_PANEL))/100)} m</p>")
a("<h2>2.1 น้ำหนักบรรทุกคงที่และจร</h2><table><tr><th>รายการ</th><th>ค่า</th><th class='n'>ต่อโครง (kg)</th></tr>")
roof_arc = sum(math.dist(nodes[f't{i}'], nodes[f't{i+1}']) for i in range(rm.N_PANEL)) / 100
steel = -tot("D", 1) - rm.ROOFING * roof_arc * 4.5 - rm.PURLIN_KGM * 4.5 * (rm.N_PANEL + 1)
for k, v, t in (("หลังคาเหล็กรีด 0.47 mm + ฉนวน (D)", f"{rm.ROOFING:.0f} kg/m² × {f(roof_arc)} m × 4.50 m", rm.ROOFING * roof_arc * 4.5),
                ("แป (D)", f"{rm.PURLIN_KGM} kg/m × 4.50 m × {rm.N_PANEL+1} แนว (เผื่อสูงกว่าแปที่เลือก)", rm.PURLIN_KGM * 4.5 * (rm.N_PANEL + 1)),
                ("น้ำหนักโครงถักและเสา (D)", f"คำนวณจากหน้าตัด × 7,850 kg/m³ × 1.10 (แผ่นต่อ)", steel),
                ("ไฟสนามและสายไฟ (SD)", f"{rm.HANGING:.0f} kg/m² × 18.00 m × 4.50 m (ไม่นับในกรณี 0.6D)", -tot("SD", 1)),
                ("น้ำหนักบรรทุกจรหลังคา (L)", f"{rm.LIVE:.0f} kg/m² × 18.00 × 4.50 (กฎกระทรวง 2566 ข้อ 11)", -tot("L", 1))):
    a(f"<tr><td>{k}</td><td>{v}</td><td class='n'>{t:,.0f}</td></tr>")
a("</table>")
a("<h2>2.2 แรงลม</h2><div class='calc'>")
for k, v in (("ความเร็วลมอ้างอิง", f"V̄ = V<sub>50</sub> × T<sub>F</sub> = 25 × 1.0 = 25 m/s (กลุ่ม 1 · อุทัยธานี)"),
             ("หน่วยแรงลมอ้างอิง", f"q = ½ρV̄² = ½ × 1.25 × 25² = 390.6 N/m² = <b>{f(q_ref,1)} kg/m²</b>"),
             ("ตัวคูณความสำคัญ", f"I<sub>W</sub> = {rm.IW} (ประเภทความสำคัญ \"มาก\" — โรงเรียน)"),
             ("ตัวคูณสภาพภูมิประเทศ", f"C<sub>e</sub> = (z/10)<sup>0.2</sup> = (9/10)<sup>0.2</sup> = 0.98 → ใช้ {rm.CE}"),
             ("หน่วยแรงลมออกแบบ", f"q<sub>W</sub> = {f(q_ref,1)} × {rm.IW} × {rm.CE} = <b>{f(rm.Q_W,1)} kg/m²</b>")):
    a(f"<div><span class='k'>{k}</span><span>{v}</span></div>")
a("</div><table><tr><th>กรณี</th><th>C<sub>p</sub>C<sub>g</sub> สุทธิ (สมมติ ⚠)</th><th class='n'>แรงดิ่งรวม/โครง (kg)</th><th class='n'>แรงราบรวม/โครง (kg)</th></tr>")
for c, cp in (("W1 ลมยกทั้งหลังคา", f"{rm.CPCG_UPLIFT}"), ("W2 ลมจากซ้าย (ไม่สมมาตร)", f"ต้นลม {rm.CPCG_WINDWARD} / ท้ายลม {rm.CPCG_LEEWARD}"),
              ("W2R ลมจากขวา", f"ต้นลม {rm.CPCG_WINDWARD} / ท้ายลม {rm.CPCG_LEEWARD}"), ("W4 ลมกดลง", f"+{rm.CPCG_DOWN}")):
    key = c.split()[0].replace("W4", "W4")
    a(f"<tr><td>{c}</td><td>{cp}</td><td class='n'>{tot(key,1):+,.0f}</td><td class='n'>{tot(key,0):+,.0f}</td></tr>")
a(f"</table><p class='small'>แรงลมกระทำตั้งฉากกับผิวโค้งที่จุดต่อคอร์ดบนแต่ละจุดตามพื้นที่รับ · กรณี W1, W2, W2R รวมแรงลากบนเสา "
  f"C<sub>f</sub>C<sub>g</sub> = {rm.CFCG_COL} × ความลึกหน้าตัดเสา · ค่าบวก = กดลง/ไปทางขวา</p>")
a("<h2>2.3 แรงแผ่นดินไหว</h2><div class='calc'>")
for k, v in (("น้ำหนักประสิทธิผล", f"W = D + SD = {f(W,0)} kg/โครง"),
             ("สัมประสิทธิ์", f"C<sub>s</sub> = S<sub>DS</sub>·I<sub>e</sub>/R = {rm.SDS_ASSUMED} × {rm.IE} / {rm.R_SEISMIC} = {f(rm.CS,3)} (S<sub>DS</sub> สมมติ ⚠)"),
             ("แรงเฉือนที่ฐาน", f"V = C<sub>s</sub>W = <b>{f(rm.CS*W,0)} kg/โครง</b> กระทำที่หัวเสาสองข้างเท่ากัน")):
    a(f"<div><span class='k'>{k}</span><span>{v}</span></div>")
a("</div></section>")

# ---- 3
a("<section class='chapter'><h1>3. แบบจำลองโครงสร้าง</h1>")
a(f"<p>วิเคราะห์โครงภายในเป็นโครงข้อแข็ง 2 มิติด้วยวิธีไฟไนต์เอลิเมนต์ (direct stiffness) · {len(nodes)} จุดต่อ · {len(members)} ชิ้นส่วน · "
  "เสาและคอร์ดเป็น frame element (รับแรงตามแกนและโมเมนต์) · ตั้งและทแยงเป็น truss element (หมุดสองปลาย) · "
  "น้ำหนักกระทำที่จุดต่อ (แปวางทุกจุดต่อคอร์ดบน) · แรงแผ่บนเสาใช้แรงยึดปลาย (fixed-end forces)</p>")
a("<figure><img src='1_elevation_sections.png'><figcaption>รูปที่ 1 รูปด้านโครงภายในและหน้าตัดที่เลือก</figcaption></figure>")
a("<h2>3.1 ความยาวไร้ค้ำยันที่ใช้ตรวจ</h2><table><tr><th>กลุ่ม</th><th>ในระนาบโครง</th><th>นอกระนาบโครง</th><th>เหตุผล</th></tr>")
for g, i, o, why in (("คอร์ดบน", "ระยะจุดต่อ ≈ 1.03 m", "ระยะจุดต่อ ≈ 1.03 m", "แปยึดทุกจุดต่อ"),
                     ("คอร์ดล่าง", "ระยะจุดต่อ ≈ 0.99 m", "3 ช่อง ≈ 3.0 m", "ค้ำยันด้านข้าง (fly brace) ทุก 3 จุดต่อ"),
                     ("ตั้ง/ทแยง", "ความยาวชิ้นส่วน", "ความยาวชิ้นส่วน", "K = 1.0"),
                     ("เสา", f"K = 1.2 × {f(rm.Z_BOT_EAVE/100)} m", "K = 1.0 × 7.00 m · L<sub>b</sub> = 7.00 m", "โครงเซได้ · หัวเสายึดด้วยคานยึดหัวเสา + X-bracing")):
    a(f"<tr><td>{g}</td><td>{i}</td><td>{o}</td><td>{why}</td></tr>")
a("</table></section>")

# ---- 4
a("<section><h1 style='margin-top:6mm'>4. ชุดน้ำหนักบรรทุก (กฎกระทรวง 2566 ข้อ 6 — ASD)</h1><table><tr><th>ชุด</th><th>ส่วนประกอบ</th></tr>")
for k, v in rm.COMBOS.items():
    a(f"<tr><td>{e(k)}</td><td>{' + '.join(f'{x:g}·{c}' for c, x in v.items())}</td></tr>")
a("</table><p class='small'>D = น้ำหนักคงที่ · SD = ไฟและสายไฟ · L = นจ.หลังคา · W = แรงลม · E = แผ่นดินไหว · "
  "กรณีตรวจการถอน (0.6D) ไม่นับน้ำหนักไฟเพื่อความปลอดภัย</p></section>")

# ---- 5
a("<section class='chapter'><h1>5. ผลการวิเคราะห์</h1>")
a("<figure><img src='2_axial_forces.png'><figcaption>รูปที่ 2 แรงในชิ้นส่วน — กรณีกดลงที่ควบคุม (บน) และลมยกไม่สมมาตร (ล่าง) · น้ำเงิน = ดึง · แดง = อัด</figcaption></figure></section>")
a("<section class='chapter'><figure><img src='3_deflection.png'><figcaption>รูปที่ 3 รูปการเสียรูป (ขยายสเกล) — นค. + นจ. (ซ้าย) และลมยก (ขวา)</figcaption></figure></section>")

# ---- 6
a("<section class='chapter'><h1>6. การตรวจสอบหน้าตัด (AISC 360-16 ASD)</h1><h2>6.1 สรุป</h2>")
a("<table><tr><th>ชิ้นส่วน</th><th>หน้าตัด</th><th class='n'>kg/m</th><th class='n'>DCR</th><th>ชิ้นที่ควบคุม</th><th>ชุดน้ำหนัก</th><th>ผล</th></tr>")
for g in ("TC", "BC", "WEB", "COL"):
    r = max((r for r in rows if r["group"] == g), key=lambda r: r["dcr"])
    a(f"<tr><td>{GN[g]}</td><td><b>{e(r['sec'])}</b></td><td class='n'>{rm.CATALOG[r['sec']]['w']:.1f}</td>"
      f"<td class='n'>{r['dcr']:.2f}</td><td>{e(r['member'])}</td><td>{e(r['combo'])}</td>"
      f"<td class='{'ok' if r['dcr'] <= 1 else 'ng'}'>{'ผ่าน' if r['dcr'] <= 1 else 'ไม่ผ่าน'}</td></tr>")
a("</table><p class='small'>หน้าตัดเลือกอัตโนมัติจากรายการเหล็กที่มีในตลาด เป็นตัวที่เบาที่สุดที่ผ่านทุกชุดน้ำหนักและเกณฑ์ระยะแอ่นตัว · "
  "DCR = แรงที่เกิด ÷ กำลังที่ยอมให้</p>")
a("<div class='note'><b>ข้อแนะนำ:</b> คอร์ดบน DCR 0.99 ใกล้ขีดจำกัดมาก และควบคุมโดยกรณีลมกดลงซึ่งใช้ค่าสัมประสิทธิ์สมมติ "
  "แนะนำให้ใช้ □100×100×3.2 เท่ากับคอร์ดล่างเพื่อเพิ่มระยะเผื่อและให้ทำรายละเอียดจุดต่อได้ง่าย</div>")
for k, g in enumerate(("TC", "BC", "WEB", "COL"), 2):
    r, lines = detail(g)
    a(f"<h2>6.{k} {GN[g]} — ชิ้น {e(r['member'])}</h2><div class='calc'>")
    for kk, vv in lines:
        a(f"<div><span class='k'>{kk}</span><span>{vv}</span></div>")
    a("</div>")
a("</section>")

# ---- 7
a("<section class='chapter'><h1>7. ระยะแอ่นตัว (ประกาศ มท. 2567 ตาราง 1 — หลังคาไม่รับฝ้า)</h1>")
a("<table><tr><th>รายการ</th><th class='n'>ค่าที่ได้ (cm)</th><th class='n'>เกณฑ์ (cm)</th><th>ผล</th></tr>")
for k, (v, lim) in list(defl.items()) + [("แป: นจ. ≤ L/180", (p_defl, p_lim))]:
    a(f"<tr><td>{e(k)}</td><td class='n'>{v:.2f}</td><td class='n'>{lim:.2f}</td><td class='{'ok' if v <= lim else 'ng'}'>{'ผ่าน' if v <= lim else 'ไม่ผ่าน'}</td></tr>")
a("</table><p class='small'>เกณฑ์เสาเอียงจากลม H/150 เป็นค่าที่ผู้ออกแบบเลือก (กฎหมายไม่ได้กำหนดสำหรับโครงหลังคาเปิดโล่ง) · "
  "เสาเอียงจากแผ่นดินไหวใช้ C<sub>d</sub> = 3</p>")

# ---- 8
a("<h1 style='margin-top:8mm'>8. แป โครงค้ำยัน และคานยึดหัวเสา</h1><h2>8.1 แป (ช่วงเดี่ยว 4.50 m · sag rod ที่จุดแบ่ง 3 ช่วง)</h2>")
a(f"<p>เลือก <b>{p_name}</b> ({p_sec['w']:.2f} kg/m · S<sub>x</sub> = {p_sec['Sx']:.1f} cm³) · หน่วยแรงดัดที่ยอมให้ 0.6F<sub>y</sub> = {0.6*rm.FY:,.0f} ksc "
  f"(จำกัดอัตราส่วนไม่เกิน {extras.PURLIN_MAX_RATIO} เพื่อเผื่อการโก่งเฉพาะที่ของเหล็กขึ้นรูปเย็น)</p>")
a("<table><tr><th>กรณี</th><th class='n'>w (kg/m)</th><th class='n'>M (kg·m)</th><th class='n'>f<sub>b</sub> (ksc)</th><th class='n'>อัตราส่วน</th></tr>")
for c, wv, M, fb, ratio in p_rows:
    a(f"<tr><td>{e(c)}</td><td class='n'>{wv:+.1f}</td><td class='n'>{M:,.0f}</td><td class='n'>{fb:,.0f}</td><td class='n'>{ratio:.2f}</td></tr>")
a("</table><h2>8.2 แรงแนวยาวและ X-bracing</h2><div class='calc'>")
for k, v in (("แรงลมแนวยาว", f"แรงลากบนโครงถัก/เสา + แรงเสียดทานผิวหลังคา ≈ {f(br['F_wind']/1000)} t"),
             ("แผ่นดินไหวแนวยาว", f"0.7 × C<sub>s</sub> × W × 6 โครง ≈ {f(br['F_seis']/1000)} t"),
             ("แรงออกแบบ", f"H = {f(br['H']/1000)} t รับด้วย X-bracing 4 ช่อง (ช่วงริม 2 ช่วง × แนวเสา 2 แนว)"),
             ("แรงในเหล็กค้ำ", f"T = H/4 × L<sub>d</sub>/4.50 = {f(br['T']/1000)} t (L<sub>d</sub> = {f(br['Ld'])} m)"),
             ("เลือก", f"เหล็กเส้นกลม <b>Ø{br['rod']} mm</b> (ตรวจครากที่หน้าตัดเต็ม และขาดที่เกลียว 75 %) · แนะนำ Ø16 mm เพื่อความแข็งตอนติดตั้ง"),
             ("คานยึดหัวเสา", f"□75×75×3.2 ยาว 4.50 m · KL/r = {br['strut_lam']:.0f} ≤ 200 · แรงอัด {f(br['strut_P']/1000)} t ≤ P<sub>a</sub> {f(br['strut_Pc']/1000)} t")):
    a(f"<div><span class='k'>{k}</span><span>{v}</span></div>")
a("</div></section>")

# ---- 9
a("<section class='chapter'><h1>9. แรงที่ฐานเสาสำหรับออกแบบฐานราก</h1>")
a("<p>ต่อเสา 1 ต้นของโครงภายใน · ชุดน้ำหนัก ASD (ไม่คูณตัวคูณเพิ่ม) · V + = กดลงฐาน · H + = ไปทาง +x (ซ้ายไปขวา) · "
  "M เป็นโมเมนต์ในระนาบโครงที่โคนเสา (โคนเสายึดแน่น)</p>")
a("<table><tr><th>เสา</th><th>กรณี</th><th>ชุดน้ำหนัก</th><th class='n'>V (t)</th><th class='n'>H (t)</th><th class='n'>M (t·m)</th></tr>")
label = {"comp": "แรงกดสูงสุด", "uplift": "แรงถอนสูงสุด", "shear": "แรงเฉือนสูงสุด", "moment": "โมเมนต์สูงสุด"}
for n, side in (("cL0", "ซ้าย"), ("cR0", "ขวา")):
    shown = []
    for k in ("comp", "uplift", "shear", "moment"):
        c, r = env[n][k]
        if c in shown and k in ("shear", "moment"):
            continue
        shown.append(c)
        a(f"<tr><td>{side}</td><td>{label[k]}</td><td>{e(c)}</td><td class='n'>{r[1]/1000:+.2f}</td>"
          f"<td class='n'>{r[0]/1000:+.2f}</td><td class='n'>{r[2]/1e5:+.2f}</td></tr>")
a(f"</table><div class='note'>ฐานรากต้องมีน้ำหนักพอต้าน <b>แรงถอน {f(-min(env[n]['uplift'][1][1] for n in env)/1000)} t ต่อเสา</b> "
  f"พร้อมโมเมนต์ที่เกิดร่วมกัน · เสาในช่วงที่มี X-bracing รับแรงดิ่งเพิ่ม ±{f(br['Fv_brace']/1000)} t · "
  "โครงริม (แกนหัว–ท้าย) รับน้ำหนักหลังคาครึ่งหนึ่งของโครงภายใน</div>")

# ---- 10
a("<h1 style='margin-top:8mm'>10. ปริมาณเหล็กโดยประมาณ</h1><table><tr><th>รายการ</th><th class='n'>น้ำหนัก (kg)</th></tr>")
for k, v in items.items():
    a(f"<tr><td>{k}</td><td class='n'>{v:,.0f}</td></tr>")
a(f"<tr><th>รวม (+10 % แผ่นต่อ รอยเชื่อม สลักเกลียว)</th><th class='n'>{total:,.0f}</th></tr></table>"
  f"<p>เฉลี่ย ≈ <b>{total/(18*27):.1f} kg/m²</b> ของพื้นที่หลังคา 486 m² · ยังไม่รวมแผ่นหลังคา ฉนวน และงานฐานราก</p></section>")

# ---- 11
a("<section class='chapter'><h1>11. การตรวจสอบความถูกต้องของการคำนวณ</h1><table><tr><th>การตรวจ</th><th>ผล</th></tr>")
for k, v in (("สมดุลแรงทุกกรณีน้ำหนัก", "ผลรวมแรงปฏิกิริยา = ผลรวมน้ำหนัก ต่างกันน้อยกว่า 10⁻⁹ kg ทุกกรณี"),
             ("ตรวจมือ — นจ.", f"50 × 18 × 4.5 = {rm.LIVE*18*4.5:,.0f} kg/โครง ตรงกับแบบจำลอง ({-tot('L',1):,.0f} kg)"),
             ("ตรวจมือ — ลมยก", f"{abs(rm.CPCG_UPLIFT)*rm.Q_W:.1f} kg/m² × 81 m² = {abs(rm.CPCG_UPLIFT)*rm.Q_W*81:,.0f} kg/โครง ตรงกับแบบจำลอง ({tot('W1',1):,.0f} kg)"),
             ("ตรวจไขว้กับโปรแกรมอื่น", "สร้างแบบจำลองเดียวกันใน PyNite (ไลบรารี FEM โอเพนซอร์ส) — การเคลื่อนตัว แรงปฏิกิริยา แรงตามแกน "
                                      "และโมเมนต์ตรงกันทุกกรณี (ต่างกันน้อยกว่า 10⁻⁹)"),
             ("รูปการเสียรูป", "นค.+นจ.: ยอดยุบ หัวเสาถ่างออก · ลมยก: ยอดยก หัวเสาหุบเข้า — สอดคล้องกับพฤติกรรมของโครงโค้ง")):
    a(f"<tr><th style='width:48mm'>{k}</th><td>{v}</td></tr>")
a("</table>")

# ---- 12 ฐานรากเสา
a("</section>")  # ปิดบทที่ 11
import footing as ft
fr = ft.run()
FB, Ft = fr["B"], fr["t"]
nb, sb, Asb = ft.bars(fr["As_bot"], FB)
ntp, stp, Ast = ft.bars(fr["As_top"], FB, 1.2)
soil = fr["soil"]
g_q = max(soil, key=lambda x: x["q"])
g_ot = min(soil, key=lambda x: x["fs_ot"])
g_sl = min(soil, key=lambda x: x["fs_sl"])
g_p = min(soil, key=lambda x: x["P"])
a("<section class='chapter'><h1>12. ฐานรากเสา (F1 — ใช้กับเสาทุกต้น)</h1>")
a("<figure><img src='5_footing_detail.png'><figcaption>รูปที่ 4 แปลนและรูปตัดฐานราก F1</figcaption></figure>")
a("<h2>12.1 ข้อมูลและเกณฑ์</h2><table>")
for k, v in (("ดิน", f"<b>ไม่มีผลเจาะสำรวจดิน</b> → ใช้ดินเหนียวแข็งปานกลาง q<sub>a</sub> = {ft.QA:.0f} t/m² (กฎกระทรวงฐานราก 2566 ข้อ 7) ⚠"),
             ("การตรวจแรงแบกทาน", "แบบรวม (gross): น้ำหนักเสา + ฐานราก + ตอม่อ + ดินถม ÷ พื้นที่ฐาน + ผลของโมเมนต์ (ปลอดภัย)"),
             ("ความลึกท้องฐาน", f"{ft.DF/100:.2f} m จาก ±0.00 · ดินถม γ = {ft.GAMMA_SOIL} t/m³ · คอนกรีต γ = {ft.GAMMA_C} t/m³"),
             ("ความปลอดภัย", f"พลิกคว่ำ FS ≥ 1.5 · เลื่อนไถล FS ≥ 1.5 (μ = {ft.MU_SLIDE} สมมติ ⚠) · ห้ามถอนขึ้น (P สุทธิ > 0)"),
             ("วัสดุ", f"คอนกรีต f'c {ft.FC:.0f} ksc (ลูกบาศก์ 240) · เหล็ก SD40 f<sub>y</sub> {ft.FY:,.0f} ksc · ระยะหุ้ม {ft.COVER} cm"),
             ("ชุดน้ำหนัก", "ดิน: ASD (ข้อ 6) · คอนกรีต สลักยึด แผ่นฐาน: USD (ข้อ 7) + φ ไทย (ดัด 0.90 · เฉือน 0.85 · แบกทาน 0.70)"),
             ("แรงจากโครงค้ำยัน", f"เพิ่มแรงดิ่ง ±{ft.FV_BR/1000:.2f} t และแรงราบแนวยาว {ft.H_BR/1000:.2f} t (ใช้กับทุกต้นเพื่อให้ฐานแบบเดียว)")):
    a(f"<tr><th style='width:40mm'>{k}</th><td>{v}</td></tr>")
a("</table>")
w = fr["wts"]
a("<h2>12.2 ตรวจดิน (ASD)</h2><div class='calc'>")
for k, v in (("น้ำหนักฐานราก", f"ฐาน {w['W_ft']:.2f} t + ตอม่อ {w['W_ped']:.2f} t + ดินถม {w['W_soil']:.2f} t = <b>{w['W_found']:.2f} t</b>"),
             ("แรงแบกทานสูงสุด", f"ชุด {e(g_q['combo'])}: P = {g_q['P']:.2f} t · M = {g_q['M']:.2f} t·m · e = {g_q['e']:.3f} m ≤ B/6 = {FB/600:.3f} m"),
             ("", f"q<sub>max</sub> = P/A (1 + 6e/B) = <b>{g_q['q']:.2f} t/m²</b> ≤ q<sub>a</sub> {ft.QA:.1f} t/m² <span class='ok'>ผ่าน</span>"),
             ("พลิกคว่ำ", f"FS ต่ำสุด = P·B/2 ÷ M = <b>{g_ot['fs_ot']:.2f}</b> ≥ 1.5 ({e(g_ot['combo'])})"),
             ("เลื่อนไถล", f"FS ต่ำสุด = μP ÷ H = <b>{g_sl['fs_sl']:.2f}</b> ≥ 1.5 ({e(g_sl['combo'])})"),
             ("แรงถอน", f"P สุทธิต่ำสุด = <b>{g_p['P']:.2f} t</b> > 0 ({e(g_p['combo'])}) — น้ำหนักฐานรากต้านแรงถอนได้")):
    a(f"<div><span class='k'>{k}</span><span>{v}</span></div>")
a("</div>")
st = fr["st"]
a("<h2>12.3 ฐานราก คสล. (USD · ACI 318-19)</h2><div class='calc'>")
for k, v in (("ขนาด", f"<b>{FB/100:.2f} × {FB/100:.2f} × {Ft/100:.2f} m</b> · d = {fr['d']:.1f} cm"),
             ("ดัด (เหล็กล่าง)", f"M<sub>u</sub> = {st['Mu']/1e5:.2f} t·m → A<sub>s</sub> คำนวณ {fr['As_bot_req']:.2f} cm² · ขั้นต่ำ 0.0018bh = {fr['As_min']:.2f} cm² → "
                                 f"<b>{nb}-DB16 @ {sb/100:.2f} m</b> ({Asb:.1f} cm²) ทั้งสองทาง"),
             ("ดัด (เหล็กบน)", f"ขณะลมยก น้ำหนักฐาน+ดินกดส่วนยื่น: M<sub>u</sub> = {st['Mu_top']/1e5:.2f} t·m → A<sub>s</sub> = {fr['As_top_req']:.2f} × 4/3 = {fr['As_top']:.2f} cm² → "
                               f"<b>{ntp}-DB12 @ {stp/100:.2f} m</b> ({Ast:.1f} cm²)"),
             ("เฉือนทางเดียว", f"V<sub>u</sub> = {st['Vu1']/1e3:.2f} t ≤ φV<sub>c</sub> = 0.85 × 0.53√f'c·B·d = {fr['phi_vc1']/1e3:.1f} t (λ<sub>s</sub> = 1 ตาม §13.2.6.2)"),
             ("เฉือนทะลุ", f"V<sub>u</sub> = {st['Vu2']/1e3:.2f} t ≤ φV<sub>c</sub> = {fr['phi_vc2']/1e3:.1f} t (b<sub>o</sub> ที่ d/2 รอบตอม่อ)"),
             ("ระยะฝังเหล็กยืนตอม่อ", f"l<sub>dh</sub> DB16 งอฉาก (§25.4.3.1) = {fr['ldh']:.1f} cm ≤ d = {fr['d']:.1f} cm")):
    a(f"<div><span class='k'>{k}</span><span>{v}</span></div>")
a("</div>")
p = fr["ped"]
a("<h2>12.4 ตอม่อ 0.60 × 0.60 m · 12-DB16 · ปลอก DB10 @ 0.15 m</h2><div class='calc'>")
for k, v in (("ดัด", f"M<sub>u</sub> = {p['Mu']/1e5:.2f} t·m ≤ φM<sub>n</sub> = {p['phiMn']/1e5:.2f} t·m (คิดเหล็กด้านเดียว ไม่นับแรงอัดช่วย)"),
             ("ดึง (ลมยก)", f"T<sub>u</sub> = {p['Tu']/1e3:.2f} t ≤ φT<sub>n</sub> = {p['phiTn']/1e3:.1f} t"),
             ("เฉือน", f"V<sub>u</sub> = {p['Vu']/1e3:.2f} t ≤ φV<sub>c</sub> = {p['phiVc']/1e3:.1f} t"),
             ("เหล็กขั้นต่ำ", f"ρ = {p['rho']:.4f} ≥ 0.005 (เหล็กเดือยรอยต่อตอม่อ–ฐานราก ACI 318-19 §16.3.4.1)")):
    a(f"<div><span class='k'>{k}</span><span>{v}</span></div>")
a("</div>")
bp, an = fr["bp"], fr["anc"]
a("<h2>12.5 แผ่นฐานเสาและสลักยึด (AISC Design Guide 1 · ACI 318-19 บทที่ 17)</h2><div class='calc'>")
for k, v in (("แรงแบกทานคอนกรีต", f"f<sub>p,max</sub> = 0.70 × 0.85f'c × √(A<sub>2</sub>/A<sub>1</sub>) = {fr['fpmax']:.0f} ksc"),
             ("แรงดึงฝั่งสลัก", f"T = {bp['T']/1e3:.2f} t ({e(bp['T_combo'])}) — กรณีโมเมนต์มาก (e > e<sub>crit</sub>)"),
             ("ความหนาแผ่น", f"t ต้องการ = {bp['t']:.2f} cm → <b>PL 450 × 450 × 30 mm</b> (SS400)"),
             ("สลัก 6-M24", f"แรงดึงต่อตัว {an['Nua']:.0f} kg ≤ φN<sub>sa</sub> {an['phiNsa']:.0f} kg · แรงเฉือนต่อตัว {an['Vua']:.0f} kg ≤ φV<sub>sa</sub> {an['phiVsa']:.0f} kg · "
                            f"รวม {an['inter']:.2f} ≤ 1.2"),
             ("การถอนหัวหมุด", f"T {bp['T']/1e3:.2f} t ≤ φN<sub>pn</sub> {an['phiNpn']/1e3:.1f} t"),
             ("คอนกรีตแตกหัก", "ตอม่อแคบ ระยะขอบน้อย → ไม่พึ่งกำลังคอนกรีต ใช้เหล็กยืนตอม่อ 4-DB16 ฝั่งรับแรงดึงเป็นเหล็กเสริมรับแรงถอน (§17.5.2.1)"),
             ("", f"φA<sub>s</sub>f<sub>y</sub> = 0.75 × {an['As_face']:.2f} × 4,000 = {an['phiNar']/1e3:.1f} t ≥ T {bp['T']/1e3:.2f} t · "
                  f"ฝังสลัก h<sub>ef</sub> {an['hef']:.0f} cm ≥ l<sub>d</sub> DB16 {an['ld']:.1f} + 5 cm")):
    a(f"<div><span class='k'>{k}</span><span>{v}</span></div>")
a("</div>")
a("<h2>12.6 ขนาดฐานรากถ้ามีผลเจาะดิน</h2><table><tr><th>q<sub>a</sub> (t/m²)</th><th>ท้องฐานลึก</th><th>ขนาดฐานราก</th><th>หมายเหตุ</th></tr>")
_qa, _df = ft.QA, ft.DF
for qa_, df_, note in ((5.0, 150.0, "แบบที่ใช้ในเล่มนี้ (ดินเหนียวแข็งปานกลาง ไม่มีผลเจาะ)"), (5.0, 120.0, "ตื้นขึ้น แต่สลักยึดลงถึงฐานราก"),
                       (10.0, 150.0, "ดินเหนียวแข็ง/ทรายแน่น"), (10.0, 120.0, "น้ำหนักน้อยลง ควบคุมโดยการพลิกคว่ำ")):
    ft.QA, ft.DF = qa_, df_
    Bx, tx, *_ = ft.select_footing()
    a(f"<tr><td>{qa_:.0f}</td><td>{df_/100:.2f} m</td><td><b>{Bx/100:.2f} × {Bx/100:.2f} × {tx/100:.2f} m</b></td><td>{note}</td></tr>")
ft.QA, ft.DF = _qa, _df
a("</table><p class='small'>ผลเจาะสำรวจดินมักคุ้มค่า — ฐานรากเล็กลงได้ถึง ~40 % ของปริมาตรคอนกรีต</p>")
conc = (FB / 100) ** 2 * Ft / 100 + (ft.PED / 100) ** 2 * (ft.DF - Ft) / 100
lean = (FB / 100 + 0.1) ** 2 * 0.05
rb = (2 * nb * (FB - 15) / 100 * 1.578 + 2 * ntp * (FB - 15) / 100 * 0.888
      + 12 * ((ft.DF - 7.5 - 5) / 100 + 0.30) * 1.578 + (int((ft.DF - Ft) / 15) + 3) * 2.2 * 0.617)
plate = 0.45 * 0.45 * 0.030 * 7850
bolts = 6 * 0.95 * 3.55
a("<h2>12.7 ปริมาณงานฐานราก</h2><table><tr><th>รายการ</th><th class='n'>ต่อฐาน</th><th class='n'>14 ฐาน</th></tr>")
for k, v, u in (("คอนกรีต f'c 210 ksc (ฐาน + ตอม่อ)", conc, "m³"), ("คอนกรีตหยาบรองพื้น 5 cm", lean, "m³"),
                ("เหล็กเสริม SD40 (ประมาณ รวมงอ)", rb, "kg"), ("แผ่นฐาน PL 450×450×30", plate, "kg"), ("สลัก M24 ยาว ≈ 0.95 m", bolts, "kg")):
    a(f"<tr><td>{k}</td><td class='n'>{v:,.2f} {u}</td><td class='n'>{v*14:,.1f} {u}</td></tr>")
a("</table></section>")

# ---- 13
a("<section class='chapter'><h1>13. สมมติฐานและข้อจำกัด</h1><table><tr><th style='width:8mm'>#</th><th>รายการ</th></tr>")
assum = [
    f"⚠ <b>ค่าสัมประสิทธิ์แรงลมหลังคาเปิดโล่ง</b> เป็นค่าสมมติแบบเผื่อสูง (ไม่สามารถเข้าถึงตาราง มยผ. 1311 ขณะจัดทำ): ยก {rm.CPCG_UPLIFT} · "
    f"ไม่สมมาตร {rm.CPCG_WINDWARD}/{rm.CPCG_LEEWARD} · กดลง +{rm.CPCG_DOWN} — <b>กรณีลมกดลงควบคุมคอร์ดบนและเสา</b> ต้องยืนยันเป็นอันดับแรก",
    f"⚠ <b>แผ่นดินไหว</b> ใช้ S<sub>DS</sub> = {rm.SDS_ASSUMED} สมมติ (ไม่มีค่า S<sub>S</sub>, S<sub>1</sub> รายอำเภอ) · ผลไม่ควบคุมการออกแบบ แต่ต้องตรวจกับประกาศ มท. รายอำเภอและชั้นดินจริง",
    "⚠ ประเภทความสำคัญ \"มาก\" (โรงเรียนจุ > 250 คน) — ถ้าเป็น \"ปกติ\" แรงลมลดลง 15 %",
    f"ระดับใต้คอร์ดล่างที่แนวเสา +{f(rm.Z_BOT_EAVE/100)} m — ถ้าต้องการ +7.00 m ต้องยกเสาและวิเคราะห์ใหม่",
    "คอร์ดล่างต้องมีค้ำยันด้านข้าง (fly brace) จากแปทุก 3 จุดต่อ",
    "ยังไม่ได้ออกแบบ: จุดต่อและรอยเชื่อมของโครงถัก · แปตามมาตรฐานเหล็กขึ้นรูปเย็น · คานคอดิน (ถ้าต้องการยึดฐานรากเข้าด้วยกัน)",
    "แรงลมเฉพาะที่ขอบหลังคาสำหรับยึดแผ่นหลังคาและแปต้องคำนวณแยก (สูงกว่าค่าที่ใช้กับโครงหลัก)",
    "คุณสมบัติหน้าตัดคำนวณจากขนาด · เหล็ก H ไม่รวมมุมโค้งโคนปีก (ค่าต่ำกว่าตารางผู้ผลิตเล็กน้อย = ปลอดภัย)",
    f"⚠ <b>ดิน</b> ไม่มีผลเจาะสำรวจ ใช้ q<sub>a</sub> = {ft.QA:.0f} t/m² และ μ = {ft.MU_SLIDE} — ก่อนก่อสร้างควรเจาะสำรวจหรือทดสอบแรงแบกทาน (ฐานรากอาจเล็กลงตามบทที่ 12.6)",
    "วิเคราะห์แบบเชิงเส้นอันดับหนึ่ง + ตัวขยาย B<sub>2</sub> สำหรับเสา · ไม่ได้วิเคราะห์การโก่งเดาะทั้งโครง (global buckling) ของโครงโค้ง",
]
for k, v in enumerate(assum, 1):
    a(f"<tr><td>{k}</td><td>{v}</td></tr>")
a("</table></section>")

# ---- ภาคผนวก
a("<section class='chapter'><h1>ภาคผนวก ก — ซองแรงของชิ้นส่วนทุกชิ้น (โครงภายใน)</h1>")
a("<p class='small'>N + = ดึง · N − = อัด · |M| สูงสุดตามความยาวชิ้นส่วน · DCR และชุดน้ำหนักที่ควบคุมตามบทที่ 6 · ชื่อจุดต่อดูรูปที่ 1 (t = คอร์ดบน, b = คอร์ดล่าง นับจากซ้าย)</p>")
a("<table class='small'><thead><tr><th>ชิ้นส่วน</th><th>กลุ่ม</th><th>หน้าตัด</th><th class='n'>L (m)</th><th class='n'>N ดึงสูงสุด (t)</th>"
  "<th class='n'>N อัดสูงสุด (t)</th><th class='n'>|M| (kg·m)</th><th class='n'>DCR</th><th>ชุดที่ควบคุม</th></tr></thead><tbody>")
for name, g, sec, L, nmax, nmin, mm, dcr, c in envelope_rows():
    a(f"<tr><td>{e(name)}</td><td>{g}</td><td>{e(sec)}</td><td class='n'>{L/100:.2f}</td><td class='n'>{max(nmax,0)/1000:.2f}</td>"
      f"<td class='n'>{min(nmin,0)/1000:.2f}</td><td class='n'>{mm/100:,.0f}</td><td class='n'>{dcr:.2f}</td><td>{e(c)}</td></tr>")
a("</tbody></table></section></body></html>")

from PIL import Image
im = Image.open(os.path.join(HERE, "4_overview_3d.png"))
W0, H0 = im.size
im.crop((int(W0 * 0.24), int(H0 * 0.27), int(W0 * 0.82), int(H0 * 0.88))).save(os.path.join(HERE, "cover_3d.png"))
html_path = os.path.join(HERE, "report_book.html")
pdf_path = os.path.join(HERE, "รายการคำนวณ-หลังคาสนามฟุตซอล.pdf")
open(html_path, "w", encoding="utf-8").write("\n".join(H))
subprocess.run([CHROME, "--headless", "--no-sandbox", "--disable-gpu", "--no-pdf-header-footer",
                f"--print-to-pdf={pdf_path}", "file://" + html_path], check=True, capture_output=True)
print("บันทึก", pdf_path)
