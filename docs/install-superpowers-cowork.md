# งานสำหรับ Cowork: ติดตั้ง Superpowers ให้ Claude Code ใน VS Code (Windows)

## เป้าหมาย
ติดตั้งชุด skill **Superpowers** (ผู้พัฒนา Jesse Vincent / obra) ให้ Claude Code ที่ใช้ผ่านส่วนขยาย VS Code บนเครื่องนี้
ให้ใช้ได้ทุกโปรเจกต์ แล้วตรวจว่า skill ขึ้นครบ

## ข้อมูลที่รู้แล้ว
- ในแชต Claude Code ของ VS Code พิมพ์ `/plugin install ...` ไม่ได้ ขึ้น "/plugin isn't available in this environment"
- พิมพ์ `/plugins` แล้วเปิดหน้าต่าง Manage plugins ได้ เจอตัวที่ถูกต้องแล้ว:
  **superpowers** — "Core skills library for Claude Code: TDD, debugging, collaboration patterns, and proven techniques" — from anthropic-plugin-directory
- กด Install แล้วขึ้น **"Something went wrong while installing this plugin."** ยังไม่รู้สาเหตุ

## ข้อห้าม
- **ห้ามติดตั้งตัวที่ชื่อคล้ายกัน**: research-superpowers, sdd-superpowers, design-superpowers, ux-superpowers,
  beads-superpowers, ZSL Superpowers, Decibel Superpowers, Superpower Builder — มี skill ชื่อซ้ำและ hook ชนกัน
  ถ้าพบว่าเคยติดตั้งตัวใดไปแล้ว ให้ถอนออกในหน้าต่าง `/plugins`
- อย่าแก้ไฟล์อื่นในโฟลเดอร์ `.claude` นอกจากที่ระบุ

## ขั้นตอน (ทำตามลำดับ หยุดเมื่อสำเร็จ)

### ขั้นที่ 1 — หาสาเหตุ error
1. ใน VS Code เปิดแชต Claude Code พิมพ์ `/plugins` → แท็บ Plugins → หา **superpowers** (ตามคำอธิบายข้างบน) → Install
2. ถ้า error อีก กด **Copy error** แล้วอ่านข้อความ
3. ถ้าเกี่ยวกับ **git** (เช่น git not found): เปิด Command Prompt/PowerShell พิมพ์ `git --version`
   ถ้าไม่มี git ให้ติดตั้งจาก https://git-scm.com/download/win (ค่าเริ่มต้นทั้งหมด) แล้วปิด-เปิด VS Code และลองข้อ 1 ใหม่
4. ถ้าเกี่ยวกับเครือข่าย/สิทธิ์ หรือยังไม่สำเร็จหลังลอง 2 ครั้ง → ไปขั้นที่ 2

### ขั้นที่ 2 — ติดตั้งผ่าน command line (ถ้ามีคำสั่ง `claude`)
เปิด PowerShell (นอก VS Code ก็ได้) แล้วรันทีละบรรทัด:
```
claude plugin marketplace add obra/superpowers-marketplace
claude plugin install superpowers@superpowers-marketplace
```
ถ้าขึ้นว่าไม่รู้จักคำสั่ง `claude` หรือ error → ไปขั้นที่ 3

### ขั้นที่ 3 — คัดลอกโฟลเดอร์ skill เอง (ไม่ต้องใช้ git / plugin)
1. ดาวน์โหลด https://github.com/obra/superpowers/archive/refs/heads/main.zip
2. แตกไฟล์ จะได้โฟลเดอร์ `superpowers-main`
3. เปิด `%USERPROFILE%\.claude` (Win + R แล้ววาง) — ถ้าไม่มีโฟลเดอร์ `skills` ให้สร้าง
4. คัดลอก **โฟลเดอร์ย่อยทั้ง 15 โฟลเดอร์** จาก `superpowers-main\skills\` ไปไว้ใน `%USERPROFILE%\.claude\skills\`
   ผลลัพธ์ต้องเป็น `%USERPROFILE%\.claude\skills\brainstorming\SKILL.md` (ไม่ใช่ `...\skills\skills\...`)
   รายชื่อ: brainstorming, diagnosing-superpowers, dispatching-parallel-agents, executing-plans,
   finishing-a-development-branch, receiving-code-review, requesting-code-review, subagent-driven-development,
   systematic-debugging, test-driven-development, using-git-worktrees, using-superpowers,
   verification-before-completion, writing-plans, writing-skills

## (ไม่บังคับ) skill งานโครงสร้างที่ทำไว้
- **structural-verification**: อยู่ใน GitHub repo `Seyren777/-` branch `claude/add-superpowers-skills`
  โฟลเดอร์ `.claude/skills/structural-verification/` → คัดลอกทั้งโฟลเดอร์ไปที่ `%USERPROFILE%\.claude\skills\`
- **structural-design (ACI 318-19)**: ไฟล์ `structural-design.zip` (โฟลเดอร์ `skill-updates/` ใน repo เดียวกัน)
  แตกให้ได้ `%USERPROFILE%\.claude\skills\structural-design\SKILL.md`

## ตรวจผล (ต้องทำทุกครั้ง)
1. ใน VS Code กด Ctrl+Shift+P → **Developer: Reload Window**
2. เปิดแชต Claude Code ใหม่ พิมพ์ `/` (หรือ `/skills`)
3. ต้องเห็นอย่างน้อย: **brainstorming, systematic-debugging, using-superpowers, writing-plans**
4. ถ่ายภาพหน้าจอผลลัพธ์ และรายงานว่าสำเร็จด้วยวิธีไหน (ขั้นที่ 1, 2 หรือ 3) พร้อมข้อความ error ที่เจอ (ถ้ามี)
