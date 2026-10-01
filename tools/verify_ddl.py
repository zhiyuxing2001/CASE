import re, sqlite3, sys, pathlib
doc = pathlib.Path("docs/phase-1-database-design.md").read_text(encoding="utf-8")
blocks = re.findall(r"```sql\n(.*?)```", doc, re.S)
sql = "\n".join(blocks)
print(f"从文档抽取 {len(blocks)} 个 SQL 块，共 {len(sql.splitlines())} 行")

con = sqlite3.connect(":memory:")
con.execute("PRAGMA foreign_keys=ON")
try:
    con.executescript(sql)
except Exception as e:
    print("❌ DDL 执行失败：", e); sys.exit(1)

tables = [r[0] for r in con.execute(
    "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
idx = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%'")]
trg = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='trigger'")]
print(f"✅ DDL 全部执行成功：{len(tables)} 张表, {len(idx)} 个索引, {len(trg)} 个触发器")
print("表:", ", ".join(tables))

# --- 端到端冒烟：写入完整病案并验证 FTS 同步与检索 ---
con.executescript("""
INSERT INTO patients(patient_code,name,gender,birth_year) VALUES('P2026001','张三','男',1975);
INSERT INTO mentors(name,title,affiliation,is_primary) VALUES('李教授','主任医师','省中医院',1);
INSERT INTO encounters(encounter_date,mentor_id,session_no,chief_topic) VALUES('2026-03-05',1,7,'脾胃病专诊');
INSERT INTO cases(case_code,patient_id,encounter_id,mentor_id,visit_date,visit_type,visit_no,
                  chief_complaint,present_illness,tcm_disease,syndrome,treatment_principle,
                  search_text,status)
VALUES('C20260305-001',1,1,1,'2026-03-05','初诊',1,
       '胃脘胀痛反复发作3月余','患者3月前无明显诱因出现胃脘胀痛，餐后加重，伴嗳气。',
       '胃脘痛','肝胃不和证','疏肝理气和胃',
       '主诉 胃脘胀痛反复发作3月余 现病史 餐后加重 嗳气 中医病名 胃脘痛 证型 肝胃不和证 治法 疏肝理气和胃 处方 柴胡10g 白芍15g 枳壳10g 甘草6g 香附10g 舌质 淡红 舌苔 薄白 脉象 弦细',
       'confirmed');
INSERT INTO case_examinations(case_id,tongue_body,tongue_coating,pulse) VALUES(1,'淡红','薄白','弦细');
INSERT INTO diagnoses(case_id,diagnosis_type,name,is_primary) VALUES(1,'中医病名','胃脘痛',1),(1,'证型','肝胃不和证',1);
INSERT INTO prescriptions(case_id,formula_name,is_modified,dose_count,decoction) VALUES(1,'柴胡疏肝散',1,7,'水煎服，日一剂，分早晚温服');
INSERT INTO herbs(name,pinyin,category,nature) VALUES('柴胡','chaihu','解表药','微寒'),('白芍','baishao','补虚药','微寒');
INSERT INTO herbs(name,pinyin,category,nature) VALUES('枳壳','zhike','理气药','温'),('甘草','gancao','补虚药','平');
INSERT INTO herb_aliases(herb_id,alias,alias_type) VALUES(2,'白芍药','异名'),(2,'杭白芍','处方名');
INSERT INTO prescription_items(prescription_id,herb_id,herb_name,herb_name_norm,dose,dose_unit,sequence)
VALUES(1,1,'柴胡','柴胡',10,'g',1),(1,2,'白芍','白芍',15,'g',2),
      (1,3,'枳壳','枳壳',10,'g',3),(1,4,'甘草','甘草',6,'g',4);
INSERT INTO learning_notes(note_type,title,content_md,status,encounter_id,mentor_id)
VALUES('学习心得','从柴胡疏肝散看李师治胃脘痛思路','## 今日跟诊\n李师强调**疏肝不忘和胃**……','published',1,1);
INSERT INTO note_case_links(note_id,case_id,relation) VALUES(1,1,'引证');
INSERT INTO mentor_comments(target_type,target_id,mentor_id,content,comment_type)
VALUES('note',1,1,'思路清晰，但需补充对弦细脉的理解。','评语');
""")

# FTS 同步验证
n = con.execute("SELECT count(*) FROM cases_fts").fetchone()[0]
print(f"FTS 触发器同步：cases_fts 中有 {n} 条记录")
assert n == 1, "FTS 触发器未同步！"

print("\n=== 检索路由验证（核心坑回归）===")
for kw in ["胃脘胀痛", "疏肝理气", "风热", "气虚", "柴胡", "弦细"]:
    if len(kw) >= 3:
        try:
            rows = con.execute(
              "SELECT c.case_code FROM cases c JOIN cases_fts f ON f.rowid=c.id "
              "WHERE cases_fts MATCH ? AND c.is_deleted=0", (f'"{kw}"',)).fetchall()
            mode = "FTS5-trigram"
        except Exception as e:
            rows, mode = [], f"FTS出错:{e}"
    else:
        rows = con.execute("SELECT case_code FROM cases WHERE search_text LIKE ? AND is_deleted=0",
                           (f"%{kw}%",)).fetchall()
        mode = "LIKE回退   "
    hit = "命中" if rows else "未命中"
    print(f"  [{mode}] {kw:<8} → {hit} {[r[0] for r in rows]}")

# 完整性抽查
print("\n=== 数据完整性抽查 ===")
q = """SELECT pi.herb_name, pi.dose, pi.dose_unit, h.category
       FROM prescription_items pi LEFT JOIN herbs h ON h.id=pi.herb_id
       WHERE pi.prescription_id=1 ORDER BY pi.sequence"""
for r in con.execute(q):
    print(f"  {r[0]} {r[1]}{r[2]}  ({r[3]})")
print("  别名归一:", con.execute(
  "SELECT a.alias, h.name FROM herb_aliases a JOIN herbs h ON h.id=a.herb_id").fetchall())
print("  心得→病案:", con.execute(
  "SELECT n.title, c.case_code FROM note_case_links l JOIN learning_notes n ON n.id=l.note_id "
  "JOIN cases c ON c.id=l.case_id").fetchall())
print("\n✅ 端到端冒烟测试通过")
