#!/usr/bin/env python3
"""写入演示数据，供界面开发与评审使用。

患者姓名均为虚构，不含任何真实个人信息。仅在开发阶段调用；
正式使用时以真实录入替代。

用法：
    python backend/scripts/seed_demo.py
"""

from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy.orm import Session  # noqa: E402
from ulid import ULID  # noqa: E402

from app.db import make_engine  # noqa: E402
from app.dictionary import resolve_herb  # noqa: E402
from app.models import (CaseNarrative, Diagnosis, InfoPatient, InfoRecord,  # noqa: E402
                        Mentor, PrescriptionItem, Treatment)
from app.search import rebuild_search_index  # noqa: E402

# 演示处方：药味、单剂剂量
PRESCRIPTION_A = [
    ("黄芩片", 15), ("盐黄柏", 15), ("苦参", 12), ("金银花", 9),
    ("浮萍", 15), ("醋莪术", 12), ("醋三棱", 15), ("茯苓", 30),
    ("薏苡仁", 30), ("莲子心", 12), ("炒酸枣仁", 15), ("砂烫枳实", 12),
    ("醋延胡索", 12), ("甘草片", 6),
]
PRESCRIPTION_B = [
    ("柴胡", 10), ("白芍", 15), ("枳壳", 10), ("甘草", 6),
    ("香附", 10), ("陈皮", 10), ("茯苓", 15),
]


def _patient(session: Session, pid: str, name: str, gender: bool,
             birthday: dt.date) -> InfoPatient:
    patient = InfoPatient(
        patient_id=pid, patient_name=name, gender=gender, birthday=birthday,
        nationality="CHN",
    )
    session.add(patient)
    session.flush()  # 先落库，保证 info_record 的外键可见
    return patient


def _record(session: Session, pid: str, *, visit_no: int, father_id: int,
            clinic_date: dt.date, age: float, visit_type: int = 0) -> InfoRecord:
    record = InfoRecord(
        patient_id=pid, father_id=father_id or 0, visit_no=visit_no,
        visit_type=visit_type, clinic_date=clinic_date, age=age,
        doctor_name="李同学", mentor_id="M-DEMO",
        department="消化科门诊", addr="中日友好医院",
    )
    session.add(record)
    session.flush()
    record.father_id = father_id or record.record_id
    if father_id:
        parent = session.get(InfoRecord, father_id)
        record.course_id = parent.course_id if parent else ""
    else:
        record.course_id = str(ULID())
    return record


def _herbs(session: Session, record_id: int, pid: str, items) -> None:
    for index, (herb, dose) in enumerate(items):
        resolution = resolve_herb(session, herb)
        session.add(PrescriptionItem(
            record_id=record_id, patient_id=pid, sequence=index,
            herb_name=herb, herb_name_norm=resolution.normalised,
            herb_id=resolution.herb_id, dose=dose, unit="g",
            total_quantity=dose * 14,
        ))


def seed(engine) -> None:
    with Session(engine) as session:
        session.add(Mentor(
            mentor_id="M-DEMO", mentor_name="姚教授", title="主任医师",
            affiliation="中日友好医院", department="消化科",
            expertise="脾胃病、代谢病", is_primary=True,
        ))
        session.flush()  # 先落库，保证 info_record 的外键可见

        # 病例一：带状疱疹后遗神经痛（5 次就诊病程）
        _patient(session, "P-DEMO-A", "演示患者甲", False, dt.date(1971, 1, 25))
        root = 0
        for visit_no in range(1, 6):
            record = _record(
                session, "P-DEMO-A", visit_no=visit_no, father_id=root,
                clinic_date=dt.date(2026, 3, 31) + dt.timedelta(days=14 * (visit_no - 1)),
                age=55.0, visit_type=0 if visit_no == 1 else 1,
            )
            root = root or record.record_id
            session.add(CaseNarrative(
                record_id=record.record_id, patient_id="P-DEMO-A",
                complaint="带状疱疹后遗神经痛3月" if visit_no == 1 else "服药后复诊",
                present_illness="左侧腹皮疹后遗留神经疼痛，刺痛，夜间加重，睡眠差。",
                past_history="发现血糖升高2年，高血压病史。",
                body_of_tongue="暗红稍紫", fur_of_tongue="苔稍黄", pulse="弦滑稍数",
                auxiliary_exam="外院生化：空腹血糖 7.5mmol/L，HbA1c 6.9%。",
            ))
            session.add(Diagnosis(
                record_id=record.record_id, patient_id="P-DEMO-A",
                tcm_disease="", syndrome="湿热瘀阻证",
                wm_diagnosis="带状疱疹后神经痛；睡眠障碍；2型糖尿病",
                patterns_analysis="舌暗红苔黄腻，湿热瘀阻之象。",
            ))
            session.add(Treatment(
                record_id=record.record_id, patient_id="P-DEMO-A",
                treatment_principle="清热祛湿，理气活血止痛",
                formula_name="", dose_count=14, decoction="机械煎药（含2袋）",
                usage="每天一次（10点）",
                western_medicine="甲钴胺 0.5mg tid；加巴喷丁 0.3g tid",
            ))
            _herbs(session, record.record_id, "P-DEMO-A", PRESCRIPTION_A)

        # 病例二：胃脘痛（2 次就诊）
        _patient(session, "P-DEMO-B", "演示患者乙", True, dt.date(1968, 5, 10))
        root_b = 0
        for visit_no in range(1, 3):
            record = _record(
                session, "P-DEMO-B", visit_no=visit_no, father_id=root_b,
                clinic_date=dt.date(2026, 2, 18) + dt.timedelta(days=14 * (visit_no - 1)),
                age=58.0, visit_type=0 if visit_no == 1 else 1,
            )
            root_b = root_b or record.record_id
            session.add(CaseNarrative(
                record_id=record.record_id, patient_id="P-DEMO-B",
                complaint="胃脘胀痛3月余" if visit_no == 1 else "服药后复诊",
                present_illness="餐后胀满加重，伴嗳气反酸，情志不畅时尤甚。",
                body_of_tongue="淡红", fur_of_tongue="薄白", pulse="弦细",
            ))
            session.add(Diagnosis(
                record_id=record.record_id, patient_id="P-DEMO-B",
                tcm_disease="胃脘痛", syndrome="肝胃不和证",
                wm_diagnosis="慢性胃炎", patterns_analysis="肝失疏泄，胃气不和。",
            ))
            session.add(Treatment(
                record_id=record.record_id, patient_id="P-DEMO-B",
                treatment_principle="疏肝理气和胃", formula_name="柴胡疏肝散",
                dose_count=7, decoction="水煎服", usage="日一剂，分早晚温服",
            ))
            _herbs(session, record.record_id, "P-DEMO-B", PRESCRIPTION_B)

        # 病例三：失眠（1 次就诊，含 1 味待校对药）
        _patient(session, "P-DEMO-C", "演示患者丙", False, dt.date(1985, 9, 2))
        record = _record(session, "P-DEMO-C", visit_no=1, father_id=0,
                         clinic_date=dt.date(2026, 6, 1), age=41.0)
        session.add(CaseNarrative(
            record_id=record.record_id, patient_id="P-DEMO-C",
            complaint="入睡困难半年", present_illness="入睡困难，多梦易醒，神疲乏力。",
            body_of_tongue="淡", fur_of_tongue="薄白", pulse="细弱",
        ))
        session.add(Diagnosis(
            record_id=record.record_id, patient_id="P-DEMO-C",
            tcm_disease="不寐", syndrome="心脾两虚证", wm_diagnosis="失眠",
        ))
        session.add(Treatment(
            record_id=record.record_id, patient_id="P-DEMO-C",
            treatment_principle="补益心脾，养血安神", formula_name="归脾汤",
            dose_count=7, decoction="水煎服",
        ))
        for index, (herb, dose) in enumerate(
            [("党参", 15), ("白术", 12), ("黄芪", 20), ("当归", 10),
             ("酸枣仁", 20), ("远志", 10), ("茯神", 15)]
        ):
            resolution = resolve_herb(session, herb)
            session.add(PrescriptionItem(
                record_id=record.record_id, patient_id="P-DEMO-C",
                sequence=index, herb_name=herb,
                herb_name_norm=resolution.normalised,
                herb_id=resolution.herb_id, dose=dose, unit="g",
                total_quantity=dose * 7,
                needs_review=(herb == "酸枣仁"),  # 演示一个待校对项
            ))

        session.commit()


def main() -> int:
    engine = make_engine()
    seed(engine)
    rebuild_search_index(engine)
    engine.dispose()
    print("✅ 演示数据已写入并重建检索索引")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
