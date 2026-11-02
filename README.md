# Global Crisis Index (GCI)

ดัชนี 0–100 วัด **ระดับผลกระทบเชิงระบบต่อโลก** จาก 4 เสาหลัก ได้แก่ เศรษฐกิจ/พลังงาน, ภูมิรัฐศาสตร์, ภัยธรรมชาติ และสุขภาพ/โครงสร้างพื้นฐาน
เว็บเป็นภาษาไทย โฮสต์บน **GitHub Pages** และอัปเดตด้วย **GitHub Actions** ทุก 6 ชั่วโมง ใช้ฟรีทั้งหมด ไม่ต้องมีเซิร์ฟเวอร์หรือฐานข้อมูล

| ช่วงคะแนน | ความหมาย |
|---|---|
| 0–20 | 🟢 ผลกระทบเชิงระบบระดับต่ำ |
| 21–45 | 🟡 เฝ้าระวัง / ผันผวนระดับภูมิภาค |
| 46–70 | 🟠 ตึงเครียดสูง / กระทบห่วงโซ่โลก |
| 71–100 | 🔴 วิกฤตเชิงระบบระดับโลก |

---

## สถาปัตยกรรม

```
GitHub Actions (ทุก 6 ชม. ที่นาที :17)
  └─ python scripts/update_index.py      ดึงข้อมูล → คำนวณ (deterministic) → สรุปภาษาไทย
  └─ pytest                              ทดสอบสูตร/การจัดการข้อมูลหาย (ถ้าไม่ผ่านจะไม่ commit)
  └─ git commit JSON                     Git ทำหน้าที่เป็นฐานข้อมูล
  └─ npm run build (Next.js static)      ฝังข้อมูลลงหน้าเว็บ
  └─ actions/deploy-pages                ทำทั้งหมดใน workflow เดียว
```

```
config/scoring_rules.json      น้ำหนัก จุดอ้างอิง Piecewise คำสำคัญ จุดยุทธศาสตร์ — ปรับจูนได้ที่นี่ที่เดียว
scripts/update_index.py        จุดเริ่มของ pipeline
scripts/gci/fetchers/          markets (yfinance → Yahoo JSON → FRED), news (GDELT + RSS), hazards (USGS + GDACS), health_cyber (WHO + CISA)
scripts/gci/scoring.py         Piecewise mapping, ยุบข่าวซ้ำ, decay ของเหตุการณ์ต่อเนื่อง, ตัวกรอง 2 ขั้น, สูตรรวม
scripts/gci/validators.py      กฎ null ≠ 0, ค่าล่าสุดที่ยังไม่หมดอายุ, สถานะ ok/partial/market_closed/stale/degraded
scripts/gci/ai_helper.py       Gemini (ข้อความเท่านั้น) + Gatekeeper + เทมเพลตภาษาไทยสำรอง
scripts/gci/pipeline.py        ประกอบทุกอย่างเป็น JSON
tests/test_scoring.py          Unit tests
app/, components/, lib/        หน้าเว็บ Next.js + Tailwind
public/data/latest_state.json  คะแนนปัจจุบัน ดัชนีย่อย สถานะแหล่งข้อมูล Watchlist หมายเหตุท้องถิ่น
public/data/history.json       ประวัติ 90 วัน (สำหรับกราฟ)
data/state_cache.json          เหตุการณ์ที่ยังไม่ยุติ, ค่าล่าสุดที่ใช้ได้, แคช AI
```

## สูตร

```
S_base = 0.35·S_econ + 0.35·S_geo + 0.15·S_nat + 0.15·S_bio_infra     (หมวดที่ไม่มีข้อมูลถูกตัดออก แล้วกระจายน้ำหนักใหม่)

ถ้า S_max1 > 70 และ S_max2 > 45:   Boost = (100 − S_base)·0.65·((S_max1 − 70)/30)^1.3
ไม่เช่นนั้น:                        Boost = สูตรเดียวกันแต่ไม่เกิน 15  (และเป็น 0 เมื่อ S_max1 ≤ 70)

Global = min(100, round(S_base + Boost))
```

กฎความถูกต้องของข้อมูลที่ระบบบังคับใช้:

- **null ≠ 0** — แหล่งข้อมูลล่มจะใช้ค่าล่าสุดที่ยังไม่หมดอายุ (`stale`) หรือตัดหมวดออกจากการเฉลี่ย (`degraded`) ไม่แทนด้วย 0 เด็ดขาด
- **ตลาดปิดเสาร์-อาทิตย์** — ใช้ราคาปิดวันศุกร์ สถานะ `market_closed` ไม่นับว่าระบบล่ม
- **ข่าวซ้ำ** — ยุบรวมตามหมวด + ประเทศ + ความคล้ายของพาดหัว คะแนนขึ้นกับจำนวน *สำนักข่าว* ที่ยืนยัน ไม่ใช่จำนวนบทความ
- **หมวดรุนแรงสูง** (≥ 70 เช่น นิวเคลียร์ ช่องแคบ) ต้องปรากฏในพาดหัว ไม่นับคำที่พูดถึงผ่านๆ ในเนื้อข่าว
- **เหตุการณ์ต่อเนื่อง** ถูกจดจำข้ามรอบใน `state_cache.json` และลดน้ำหนักลง 15%/วันเมื่อไม่มีรายงานใหม่
- **ภัยพิบัติท้องถิ่น** ที่ห่างจุดยุทธศาสตร์ 8 แห่งเกิน 300 กม. และไม่มีสึนามิข้ามภูมิภาค มีเพดาน 30/100 (กระทบคะแนนโลก ≤ 4.5 แต้ม) และไปแสดงใน “หมายเหตุท้องถิ่น”
- **สุขภาพ/ไซเบอร์ในประเทศเดียว** มีเพดาน 25/100 ส่วนประกาศช่องโหว่ทั่วไปมีน้ำหนักต่ำมาก

---

## ติดตั้งและใช้งานจริง (GitHub Pages)

1. **สร้าง repository บน GitHub** แล้ว push โค้ดนี้ขึ้น branch `main`
   ```bash
   git remote add origin https://github.com/<user>/<repo>.git
   git push -u origin main
   ```
2. **เปิด GitHub Pages:** *Settings → Pages → Build and deployment → Source:* เลือก **GitHub Actions**
3. **อนุญาตให้ workflow เขียน repo:** *Settings → Actions → General → Workflow permissions:* เลือก **Read and write permissions**
4. **(ไม่บังคับ) ใส่ Gemini API Key** เพื่อให้ได้ข้อความสรุปที่เป็นธรรมชาติขึ้น:
   - ขอคีย์ฟรีที่ <https://aistudio.google.com/apikey>
   - *Settings → Secrets and variables → Actions → New repository secret:* ชื่อ `GEMINI_API_KEY`
   - (ไม่บังคับ) แท็บ *Variables:* ชื่อ `GEMINI_MODEL` (ค่าเริ่มต้น `gemini-2.5-flash`)
   - ถ้าไม่ใส่ ระบบทำงานได้ครบด้วยเทมเพลตภาษาไทย
5. **รันครั้งแรก:** *Actions → Update index & deploy → Run workflow*
   เว็บจะอยู่ที่ `https://<user>.github.io/<repo>/` (workflow ตั้ง `basePath` ให้อัตโนมัติ)

หลังจากนั้นระบบจะอัปเดตเองทุก 6 ชั่วโมง

> **หมายเหตุ:** GitHub ปิด schedule อัตโนมัติถ้า repo ไม่มี activity 60 วัน แต่ commit ข้อมูลทุก 6 ชั่วโมงนับเป็น activity อยู่แล้ว

## รันบนเครื่อง

```bash
pip install -r requirements.txt
python -m pytest -q tests              # ทดสอบสูตร
python scripts/update_index.py         # ดึงข้อมูลจริง เขียน public/data/*.json
python scripts/update_index.py --dry-run   # คำนวณอย่างเดียว ไม่เขียนไฟล์

npm install
npm run dev                            # http://localhost:3000
npm run build                          # static export → out/
```

ใช้ Gemini บนเครื่อง: ตั้ง environment variable `GEMINI_API_KEY` (และ `GEMINI_MODEL` ถ้าต้องการ) ก่อนรัน `update_index.py`

## ปรับจูน

ค่าทุกอย่างอยู่ใน `config/scoring_rules.json`:

- `weights`, `booster` — สูตรรวม
- `econ.indicators.*` — จุดอ้างอิง Piecewise ของ VIX, Brent, ทองคำ, S&P 500, SOXX (ระดับราคา / %เปลี่ยน 5 วันทำการ / drawdown จากจุดสูงสุด 52 สัปดาห์)
- `geo.categories` — คำสำคัญและความรุนแรงของแต่ละประเภทเหตุการณ์
- `events` — อัตรา decay, ตัวคูณการยืนยันจากหลายสำนักข่าว
- `nat.strategic_hubs` — จุดยุทธศาสตร์ 8 แห่งและรัศมี
- `bio_infra.categories` — หมวดโรคระบาด/ไซเบอร์ และเพดานกรณีประเทศเดียว

แก้แล้วรัน `pytest` เพื่อยืนยันว่าคุณสมบัติด้านความปลอดภัย (เพดาน, null ≠ 0, ยุบข่าวซ้ำ) ยังคงอยู่

## ข้อจำกัด

- จัดหมวดข่าวด้วยคำสำคัญภาษาอังกฤษ อาจพลาดหรือจัดผิดหมวดได้
- GDELT จำกัดความถี่ (1 คำขอ/5 วินาทีต่อ IP) หากโดนจำกัด หมวดภูมิรัฐศาสตร์จะใช้ RSS ที่เหลือและแสดงสถานะ “ข้อมูลบางส่วนล่าช้า”
- ไม่ใช่ระบบเตือนภัยเรียลไทม์ และไม่ใช่คำแนะนำการลงทุน
