import os
import time
import redis
import json
import logging
import sys
import io
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import List, Tuple, Dict, Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from helper.diagram import bar, bidirection, gauge, bidirection_two_side, horizontal, scatter, tube
from helper.diagram.ag_report1 import build_chart_data, render_report_media
from helper.diagram.ag_report2 import render_report_media as render_report2_media
from helper.diagram.ag_report2.report import MEDIA_TARGETS as REPORT2_MEDIA_TARGETS
from helper.diagram.ag_report2.report import BRANCHES as REPORT2_BRANCHES
from helper.diagram.ag_report2.report import BRANCH_COLORS as REPORT2_BRANCH_COLORS
from helper.diagram.ag_report2.report import branch_id_for as report2_branch_id
from helper.diagram.ag_report2.report import persianize_text as persianize_report2_text
from helper.db.sqlalchemy import session_scope
from helper.db.sqlalchemy.queries.quiz_labels import upsert_quiz_labels
from helper.db.sqlalchemy.queries.scheduler_reports import (
    get_scheduler_student_context,
    list_completed_attempt_versions,
    update_redis_log_status,
    upsert_hedayat_fields,
    upsert_result_state,
    upsert_scl_score,
    upsert_score,
)
from helper.quiz.runtime_provider import resolve_attempt_runtime
from helper.office.excel_helper import compute_brain_info
from quiz_packages.ag.legacy_v1.reports import *
from quiz_packages.scl.legacy_v1.report_bookmarks import CALC_DATA, COLOR_TAGS, USER_TAGS_INFO
from quiz_packages.scl.legacy_v1.reports import get_interfast_value, get_report_text, get_statefast_value
from quiz_packages.scl.legacy_v1.scoring import bookmark_scl_object
from helper.office.word_helper import (
    generate_first_report_documents,
    generate_second_report_documents,
    require_libreoffice,
)
from helper.office.scl_reports import (
    SCL_REPORT3_HIDDEN_MARKER_REPLACEMENTS,
    make_scl_report_context,
    render_scl_report_set,
    select_scl_report3_media,
    select_scl_score_image_name,
)
from helper.diagram.scl_report3.report import order_r3_layer_factor_ids
from config import (
    DEFAULT_REPORT_LOGO_PATH,
    REPORTS_DIR,
    INS_PIC_DIR,
    REDIS_QUEUE_NAME,
    REDIS_HOST,
    REDIS_PORT,
    REDIS_PASSWORD,
    REDIS_DB,
)

# Logging configuration
utf8_stream = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d:%(funcName)s] - %(message)s',
    handlers=[
        logging.FileHandler('ag_report_scheduler.log', encoding='utf-8'),
        logging.StreamHandler(utf8_stream)
    ]
)

# Constants
FIRST_REPORT_IMAGES = [
    'image9.png', 'image12.png', 'image14.jpg', 'image16.jpg', 'image19.jpg', 'image22.jpg',
    'image26.jpg', 'image29.jpg', 'image32.jpg', 'image35.jpg', 'image39.png', 'image40.png',
    'image41.png', 'image42.png', 'image43.png', 'image44.png', 'image48.png'
]

SECOND_REPORT_IMAGES = REPORT2_MEDIA_TARGETS + ("image15.jpeg",)

CATEL_EFFECT = [
    ['سرآمد', ' ۱۶۴ به بالا', ' ۰/۰۰۳ ٪'], ['نابغه', ' ۱۴۸ - ۱۶۳', ' ۰/۱۳ ٪'],
    ['تیزهوش', ' ۱۳۲-۱۴۷', ' ۲/۱۴ ٪'], ['باهوش', ' ۱۲۰ - ۱۳۱', ' ۸/۲۹ ٪'],
    ['قوی', ' ۱۱۰ - ۱۱۹', ' ۱۶/۰۳ ٪'], ['متوسط', ' ۹۰ - ۱۰۹', ' ۴۶/۸ ٪'],
    ['مرزی', ' ۶۸ - ۸۹', ' ۲۴/۳۲ ٪'], ['آموزش پذیر', ' ۵۲ - ۶۷', ' ۲/۱۴ ٪'],
    ['آموزش پذیر', ' ۵۲ - ۶۷', ' ۲/۱۴ ٪'], ['حمایت پذیر', ' ۳۶ به پایین', ' ۰/۰۰۳ ٪']
]

REPORT2_BRANCH_IDS = tuple(identifier for identifier, _, _ in REPORT2_BRANCHES)
STATE_TAG_BY_BRANCH_ID = {
    1: '#t_state', 2: '#r_state', 3: '#e_state', 4: '#a_state',
    5: '#m_state', 6: '#f_state', 7: '#i_state',
}

STATE_INFO = [
    (('زممممممممد', 'زمممممممممد', 'زممممممممممد'), ('تممممممممد', 'تمممممممممد', 'تممممممممممد')),

    (('زممد', 'زمممد', 'زممممد'), ('تممد', 'تمممد', 'تممممد')),

    (('زمممممد', 'زممممممد', 'زمممممممد'), ('تمممممد', 'تممممممد', 'تمممممممد')),

    (('زممممممممممممممممممممد', 'زمممممممممممممممممممممد', 'زممممممممممممممممممممممد'),
     ('تممممممممممممممممممممد', 'تمممممممممممممممممممممد', 'تممممممممممممممممممممممد')),

    (('زمممممممممممممممممد', 'زممممممممممممممممممد', 'زمممممممممممممممممممد'),
     ('تمممممممممممممممممد', 'تممممممممممممممممممد', 'تمممممممممممممممممممد')),

    (('زمممممممممممد', 'زممممممممممممد', 'زمممممممممممممد'), ('تمممممممممممد', 'تممممممممممممد', 'تمممممممممممممد')),

    (('زممممممممممممممد', 'زمممممممممممممممد', 'زممممممممممممممممد'),
     ('تممممممممممممممد', 'تمممممممممممممممد', 'تممممممممممممممممد')),
]
STATE_INFO_BY_BRANCH_ID = {
    1: STATE_INFO[0],
    2: STATE_INFO[1],
    3: STATE_INFO[2],
    4: STATE_INFO[3],
    5: STATE_INFO[5],  # DOCX state placeholders put Management after Agriculture.
    6: STATE_INFO[4],
    7: STATE_INFO[6],
}

# Keys are Brain BranchIds. The DOCX tables appear in a different visual order,
# so table population must target the visible Persian placeholder by branch.
FIELDS_BENCHMARK_NAME = {
    1: (('Reshteha_Tajrobi', ['رشته_پیشنهادی_تجربی', 'S1', 'S2', 'T1', 'T2']),
        ('Sayer_Tajrobi', ['سایر_تجربی', 'سایر_رنگ'])),
    2: (('Reshteha_Riazi', ['رشته_پیشنهادی_ریاضی', 'S1', 'S2', 'T1', 'T2']),
        ('Sayer_Riazi', ['سایر_ریاضی', 'سایر_رنگ'])),
    3: (('Reshteha_Ensani', ['رشته_پیشنهادی_انسانی', 'S1', 'S2', 'T1', 'T2']),
        ('Sayer_Ensani', ['سایر_انسانی', 'سایر_رنگ'])),
    4: (('Reshteha_Honar', ['رشته_پیشنهادی_هنر', 'S1', 'S2', 'T1', 'T2']),
        ('Sayer_Honar', ['سایر_هنر', 'سایر_رنگ'])),
    5: (('Reshteha_Modiriat', ['رشته_پیشنهادی_مدیریت', 'S1', 'S2', 'T1', 'T2']),
        ('Sayer_Modiriat', ['سایر_مدیریت', 'سایر_رنگ'])),
    6: (('Reshteha_Keshavarzi', ['رشته_پیشنهادی_کشاورزی', 'S1', 'S2', 'T1', 'T2']),
        ('Sayer_Keshavarzi', ['سایر_کشاورزی', 'سایر_رنگ'])),
    7: (('Reshteha_Sanat', ['رشته_پیشنهادی_صنعت', 'S1', 'S2', 'T1', 'T2']),
        ('Sayer_Sanat', ['سایر_صنعت', 'سایر_رنگ'])),
}

CATEGORY_DEF_COLOR = {
    "دبیری": "#c8acdc", "مدیریت": "#a0a4bc", "علوم پایه": "#a0c4e4", "هنر": "#a0dcfc",
    "مهندسی سازه": "#99dfb9", "مهندسی صنعتی": "#d8ecbc", "الکترونیک و کامپیوتر": "#fffc9c",
    "علوم انسانی": "#ffe699", "مالی و حسابداری": "#ff9999", "روانشناسی": "#e69999",
    "روابط عمومی": "#c6acd9", "کشاورزی و امور دامی": "#99a6bf", "حقوق و علوم سیاسی": "#99c6e6",
    "خدمات فنی": "#99dff9", "تکنسین فنی": "#99dfb9", "بالینی و درمانی": "#d3ecb9",
    "تشخیصی و درمانی": "#ffff99", "تکنسین کامپیوتر": "#ffe699"
}

BRANCH_COLOR = {
    1: "#E39B00", 2: "#E8505B", 3: "#9DB000", 4: "#1FA463",
    5: "#2F6FD6", 6: "#0FA3C9", 7: "#8456C9"
}


class AGReportScheduler:
    def __init__(self):
        libreoffice_path = require_libreoffice()
        logging.info("Using LibreOffice executable: %s", libreoffice_path)
        self.redis = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            password=REDIS_PASSWORD if REDIS_PASSWORD else None,
            db=REDIS_DB,
            decode_responses=True
        )

    def _log_error(self, user_id: str, kind: str, error: str) -> None:
        """Log errors to database with user context."""
        try:
            with session_scope() as session:
                update_redis_log_status(
                    session=session,
                    user_id=user_id,
                    kind=kind,
                    result=f"Error: {error}",
                    status=3,
                )
        except Exception as e:
            logging.error(f"Failed to log error to database: {str(e)}")

    def _get_student_info(self, user_id: str):
        """Retrieve student information with institute and consultant details."""
        try:
            with session_scope() as session:
                student = get_scheduler_student_context(session=session, user_id=user_id)

            if not student:
                raise ValueError(f"Student with ID {user_id} not found")

            institute_name = ""
            consultant_name = ""
            logo_path = None

            if student["owner_role"] == "ins":
                institute_name = student.get("institute_name") or ""
                if student.get("institute_logo"):
                    logo_path = os.path.join(INS_PIC_DIR, student["institute_logo"])
            elif student["owner_role"] == "sch":
                institute_name = student.get("school_name") or ""
                if student.get("school_logo"):
                    logo_path = os.path.join(INS_PIC_DIR, student["school_logo"])
            else:
                consultant_name = f"{student.get('ocon_first_name') or ''} {student.get('ocon_last_name') or ''}".strip()
                institute_name = consultant_name

            if student.get("consultant_user_id") and student["owner_role"] != "ocon":
                consultant_name = (
                    f"{student.get('consultant_first_name') or ''} "
                    f"{student.get('consultant_last_name') or ''}"
                ).strip()

            student_name = f"{student.get('first_name') or ''} {student.get('last_name') or ''}".strip()
            phone = student["phone"]

            return student, student_name, phone, institute_name, consultant_name, logo_path

        except Exception as e:
            logging.error(f"Error getting student info: {str(e)}")
            self._log_error(user_id, "AG", str(e))
            raise

    def _validate_quiz_data(self, user_id: str, report_kind: str):
        """Resolve and validate the runtime recorded on completed attempts."""
        try:
            with session_scope() as session:
                attempt_versions = list_completed_attempt_versions(
                    session=session,
                    user_id=user_id,
                    report_kind=report_kind,
                )

            return resolve_attempt_runtime(
                report_kind,
                attempt_versions,
            )
        except Exception as e:
            logging.error(f"Error validating quiz data: {str(e)}")
            self._log_error(user_id, report_kind, str(e))
            raise

    def _create_report_directory(self, phone: str) -> str:
        """Create directory for report files."""
        user_directory = os.path.join(REPORTS_DIR, phone)
        try:
            os.makedirs(user_directory, exist_ok=True)
            logging.info(f"Directory '{user_directory}' created/exists")
            return user_directory
        except Exception as e:
            logging.error(f"Failed to create directory: {str(e)}")
            raise

    @staticmethod
    def _motivation_summary(value: float, maximum: float, subject: str) -> str:
        score = max(0, min(100, round(float(value) * 100 / maximum)))
        if score < 20:
            level = "خیلی کم"
        elif score < 40:
            level = "کم"
        elif score < 60:
            level = "متوسط"
        elif score < 80:
            level = "زیاد"
        else:
            level = "خیلی زیاد"
        return f"اهمیت {subject} برای شما در سطح {level} قرار دارد (امتیاز {score} از ۱۰۰)."

    def _build_first_report_text(
            self,
            data: Dict,
            institute_name: str,
            consultant_name: str,
            chart_data,
    ) -> Dict[str, str]:
        """Build all AG Report 1 text replacements without rendering charts."""
        catel_explain, _, _, _ = catel_info(data["IQ_Number"])
        info = {
            "#name": data.get("student_name", ""),
            "#inst_name": institute_name,
            "#con_name": consultant_name,
            "#right_cattel": str(data.get("correct", 0)),
            "#wrong_cattel": str(data.get("wrong", 0)),
            "#non_cattel": str(data.get("unanswered", 0)),
            "#توضیحات_کتل": catel_explain,
        }

        gardner_text = (
            ("سلاام", "Visual_spatial", gardner_visual_explain),
            ("سلااام", "Linguistic_verbal", gardner_linguistic_explain),
            ("سلاااام", "Logical_mathematical", gardner_logical_explain),
            ("سلااااام", "Body_kinesthetic", gardner_body_explain),
            ("سلاااااام", "Musical", gardner_musical_explain),
            ("سلااااااام", "Interpersonal", gardner_interpersonal_explain),
            ("سلاااااااام", "Intrapersonal", gardner_intrapersonal_explain),
            ("سلااااااااام", "Naturalistic", gardner_naturalistic_explain),
        )
        for placeholder, key, explain in gardner_text:
            info[placeholder] = explain(data[key])

        neo_text = (
            ("سلاااااااااام", "Extraversion", neo_extraversion_explain),
            ("سلااااااااااام", "Agreeableness", neo_agreeableness_explain),
            ("سلاااااااااااام", "Neuroticism", neo_neuroticism_explain),
            ("سلااااااااااااام", "Openness", neo_openness_explain),
            ("سلاااااااااااااام", "Conscientiousness", neo_conscientiousness_explain),
        )
        for placeholder, key, explain in neo_text:
            info[placeholder] = explain(data[key])[0]

        holland_keys = [key for key, _, _ in (
            ("Realistic", "و", "واقع گرایی"),
            ("Investigative", "ج", "جستجوگری"),
            ("Artistic", "هـ", "هنری"),
            ("Social", "الف", "اجتماعی"),
            ("Enterprising", "م", "متهور"),
            ("Conventional", "ق", "قراردادی"),
        )]
        top_holland = sorted(holland_keys, key=lambda key: data[key], reverse=True)[:3]
        for index, key in enumerate(top_holland):
            ordinal = ("first", "second", "third")[index]
            desire_title, desire_text = get_holland_desire(key)
            work_title, work_text = get_holland_work(key)[:2]
            info[f"#desire_{ordinal}_title"] = desire_title
            info[("سلااااااااااااااام", "سلاااااااااااااااام", "سلااااااااااااااااام")[index]] = desire_text
            info[f"#work_{ordinal}_title"] = work_title
            info[("سلاااااااااااااااااام", "سلااااااااااااااااااام", "سلاااااااااااااااااااام")[index]] = work_text

        info.update({
            "سلااااااااااااااااااااام": get_clifton_strategic(data),
            "سلاااااااااااااااااااااام": get_clifton_relation(data),
            "سلااااااااااااااااااااااام": get_clifton_infiltrate(data),
            "سلاااااااااااااااااااااااام": get_clifton_executive(data),
            "#تعهد": f"سطح تعهد تحصیلی شما {chart_data.commitment['label']} است.",
            "#سختی": self._motivation_summary(data["Field"], 12, "تحمل سختی مسیر تحصیلی"),
            "#مهاجرت": self._motivation_summary(data["Imigration"], 16, "مهاجرت"),
            "#شغل": self._motivation_summary(data["Job"], 12, "وجود شغل مرتبط با رشته"),
            "#درآمد": self._motivation_summary(data["Money"], 16, "درآمد"),
            "#جایگاه": self._motivation_summary(data["Social_place"], 12, "جایگاه اجتماعی"),
            "#زمان": self._motivation_summary(data["Speed"], 12, "سرعت رسیدن به درآمد"),
        })
        persian_digits = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
        for key in info.keys() - {"#name", "#inst_name", "#con_name"}:
            info[key] = str(info[key]).translate(persian_digits)
        return info

    def _generate_first_report_charts(self, data: Dict, user_directory: str,
                                      institute_name: str, consultant_name: str) -> Tuple[List, Dict, List, List, List]:
        """Generate all charts for the first report."""
        report_pictures = []
        report_info = {
            "#name": data.get("student_name", ""),
            "#inst_name": institute_name,
            "#con_name": consultant_name,
            "#right_cattel": str(data.get("correct", 0)),
            "#wrong_cattel": str(data.get("wrong", 0)),
            "#non_cattel": str(data.get("unanswered", 0))
        }
        color_handle_tag = []
        color_handle_color = []

        try:
            # Gauge chart (Catel Quiz)
            ranges = [(0, 51), (52, 89), (90, 119), (120, 147), (148, 200)]
            gauge_path = gauge.create_gauge_chart(
                value=data["IQ_Number"],
                labels=['', '', '', '', ''],
                colors=['#42b74a', '#cfdf28', '#ffbb10', '#f76420', '#cf2020'],
                ranges=ranges,
                path=user_directory,
                filename='gague'
            )
            catel_explain, catel_number, iq_name, iq_num = catel_info(data["IQ_Number"])
            report_pictures.append(f"{gauge_path}.png")
            report_info["#توضیحات_کتل"] = catel_explain
            report_info["#gauge_state"] = iq_name
            ca_effect = CATEL_EFFECT[iq_num]

            # Bar chart (Gardner Quiz)
            categories_bar = [
                'تصویری-فضایی', 'زبانی-کلامی', 'منطقی-ریاضی', 'جسمی-حرکتی',
                'موسیقیایی', 'بین فردی', 'درون فردی', 'طبیعت گرا'
            ]
            colors = [
                '#3BABC5', '#E6C90B', '#49CFFF', '#FF75B5',
                '#8FD351', '#9472DE', '#F1AB37', '#FF6C6C'
            ]

            bar_path = bar.create_bar_chart(
                categories=categories_bar,
                title='ﻪﻧﺎﮔ ۸ ﯼﺎﻫﺵﻮﻫ ﺭﺩ ﺎﻤﺷ ﺖﯿﻌﺿﻭ ﻪﺑ ﯽﻠﮐ ﻩﺎﮕﻧ',
                values=[
                    data["Visual_spatial"] * 2, data["Linguistic_verbal"] * 2,
                    data["Logical_mathematical"] * 2, data["Body_kinesthetic"] * 2,
                    data["Musical"] * 2, data["Intrapersonal"] * 2,
                    data["Interpersonal"] * 2, data["Naturalistic"] * 2
                ],
                colors=colors,
                rotation=45,
                size=6,
                path=user_directory,
                filename='bar'
            )
            report_pictures.append(f"{bar_path}.png")

            # Tube charts for each attribute
            attributes = [
                ("Visual_spatial", "سلاام", gardner_visual_explain),
                ("Linguistic_verbal", "سلااام", gardner_linguistic_explain),
                ("Logical_mathematical", "سلاااام", gardner_logical_explain),
                ("Body_kinesthetic", "سلااااام", gardner_body_explain),
                ("Musical", "سلاااااام", gardner_musical_explain),
                ("Intrapersonal", "سلااااااام", gardner_intrapersonal_explain),
                ("Interpersonal", "سلاااااااام", gardner_interpersonal_explain),
                ("Naturalistic", "سلااااااااام", gardner_naturalistic_explain)
            ]

            for i, (attr, key, explain_func) in enumerate(attributes, start=1):
                value = data[attr]
                tube_path = tube.create_tube_chart(
                    charge_level=value,
                    color=colors[i - 1],
                    path=user_directory,
                    filename=f'tube{i}'
                )
                report_pictures.append(f"{tube_path}.png")
                report_info[key] = explain_func(value)

            # Bidirectional chart (Neo Quiz)
            neo_data = self._prepare_neo_data(data)
            bi_path = bidirection.create_bi_chart(
                negative_values=[neo_data[0][1], neo_data[1][1], neo_data[2][1], neo_data[3][1], neo_data[4][1]],
                positive_values=[neo_data[0][0], neo_data[1][0], neo_data[2][0], neo_data[3][0], neo_data[4][0]],
                path=user_directory,
                filename='bi'
            )
            report_pictures.append(f"{bi_path}.png")

            # Two-value direction charts
            bi_charts_data = [
                ("Extraversion", neo_data[0], '#0070c0', 'bitwo1', "سلاااااااااام", neo_extraversion_explain),
                ("Agreeableness", neo_data[1], '#00b050', 'bitwo2', "سلااااااااااام", neo_agreeableness_explain),
                ("Neuroticism", neo_data[2], '#ed7d31', 'bitwo3', "سلاااااااااااام", neo_neuroticism_explain),
                ("Openness", neo_data[3], '#ffc000', 'bitwo4', "سلااااااااااااام", neo_openness_explain),
                ("Conscientiousness", neo_data[4], '#ff0000', 'bitwo5', "سلاااااااااااااام",
                 neo_conscientiousness_explain)
            ]

            for attr, values, color, filename, key, explain_func in bi_charts_data:
                path = bidirection_two_side.create_bidirectional_two_side(
                    '', '', values[0], values[1], color, path=user_directory, filename=filename
                )
                report_pictures.append(f"{path}.png")
                report_info[key] = explain_func(data[attr])[0]

            # Holland Quiz charts and data
            holland_data = self._process_holland_data(data, user_directory, report_pictures, report_info)
            color_handle_tag, color_handle_color = self._extract_holland_colors(holland_data, report_info)

            # Clifton Quiz info
            report_info.update({
                "سلااااااااااااااااااااام": get_clifton_strategic(data),
                "سلاااااااااااااااااااااام": get_clifton_relation(data),
                "سلااااااااااااااااااااااام": get_clifton_infiltrate(data),
                "سلاااااااااااااااااااااااام": get_clifton_executive(data)
            })

            return report_pictures, report_info, ca_effect, color_handle_tag, color_handle_color

        except Exception as e:
            logging.error(f"Error generating first report charts: {str(e)}")
            raise

    def _prepare_neo_data(self, data: Dict) -> List[Tuple]:
        """Prepare NEO data for bidirectional charts."""
        labels = ['Extraversion', 'Agreeableness', 'Neuroticism', 'Openness', 'Conscientiousness']
        neo_data = []
        for x in labels:
            value = data[x] - 24
            if value >= 0:
                neo_data.append((value, 0))
            else:
                neo_data.append((0, value))
        return neo_data

    def _process_holland_data(self, data: Dict, user_directory: str, report_pictures: List, report_info: Dict) -> Dict:
        """Process Holland quiz data and generate charts."""
        holland_labels = ['Realistic', 'Investigative', 'Artistic', 'Social', 'Enterprising', 'Conventional']
        holland_data = {x: data[x] for x in holland_labels}

        # Horizontal bar chart
        holland_pic = horizontal.create_horizontal_chart(
            categories=holland_labels,
            values=[holland_data[x] for x in holland_labels],
            colors=["#ed242b", "#2aa7dd", "#039449", "#814198", "#f36e23", "#fcb01c"],
            path=user_directory,
            filename='horiz'
        )
        report_pictures.append(f"{holland_pic}.png")

        # Sort and process top 3 categories
        sorted_holland = {k: v for k, v in sorted(holland_data.items(), key=lambda item: item[1], reverse=True)}
        desire_data = []
        work_data = []

        for key in list(sorted_holland.keys())[:3]:
            desire_info = get_holland_desire(key)
            work_info = get_holland_work(key)
            color = get_holland_score_color_name(data[key], key)[0]

            desire_data.append((desire_info[0], desire_info[1]))
            work_data.append((work_info[0], work_info[1], color))

        # Add desire info to report
        desire_keys = ["#desire_first_title", "#desire_second_title", "#desire_third_title"]
        desire_values = ["سلااااااااااااااام", "سلاااااااااااااااام", "سلااااااااااااااااام"]

        for i, (key, value_key) in enumerate(zip(desire_keys, desire_values)):
            if i < len(desire_data):
                report_info[key] = desire_data[i][0]
                report_info[value_key] = desire_data[i][1]

        # Add work info to report
        work_keys = ["#work_first_title", "#work_second_title", "#work_third_title"]
        work_values = ["سلاااااااااااااااااام", "سلااااااااااااااااااام", "سلاااااااااااااااااااام"]

        color_handle_data = []
        for i, (key, value_key) in enumerate(zip(work_keys, work_values)):
            if i < len(work_data):
                report_info[key] = work_data[i][0]
                report_info[value_key] = work_data[i][1]
                color_handle_data.append((key, work_data[i][2]))

        return {"data": holland_data, "color_handle": color_handle_data}

    def _extract_holland_colors(self, holland_data: Dict, report_info: Dict) -> Tuple[List, List]:
        """Extract color handling information from Holland data."""
        color_handle_tag = []
        color_handle_color = []
        for tag, color in holland_data.get("color_handle", []):
            color_handle_tag.append(tag)
            color_handle_color.append(color)
        return color_handle_tag, color_handle_color

    def _get_sorted_suggested_fields(self, fields: List) -> Dict[int, tuple]:
        """Sort and group suggested fields by branch."""
        branch_groups = {}
        for item in fields:
            branch = int(item["BranchId"])
            if branch not in REPORT2_BRANCH_IDS:
                raise ValueError(f"Unknown Report2 Brain BranchId: {branch}")
            branch_groups.setdefault(branch, []).append(item)

        def _c1_value(field: Dict) -> float:
            """Return numeric C1 value; fallback to 0 when missing/invalid."""
            try:
                return float(field.get("C1", 0) or 0)
            except (TypeError, ValueError):
                return 0.0

        groups_by_id = {}
        for branch_id in REPORT2_BRANCH_IDS:
            branch = branch_groups.get(branch_id, [])
            suggested_list = [f for f in branch if _c1_value(f) > 0]
            other_list = [f for f in branch if _c1_value(f) <= 0]
            all_list = branch.copy()
            groups_by_id[branch_id] = (suggested_list, other_list, all_list)
        return groups_by_id

    def _process_hedayat_fields(self, fields: List) -> Tuple[str, str]:
        """Process fields to extract suggested and other field names for hedayat_fields table."""
        suggested_names = []
        other_names = []

        for item in fields:
            field_name = item.get("Field", "")
            c1_value = item.get("C1", 0)

            if c1_value > 0:
                suggested_names.append(field_name)
            elif c1_value <= 0:
                other_names.append(field_name)

        return ','.join(suggested_names), ','.join(other_names)

    def _update_hedayat_fields(self, user_id: str, suggested: str, other: str) -> None:
        """Update or insert hedayat_fields record."""
        try:
            with session_scope() as session:
                upsert_hedayat_fields(
                    session=session,
                    user_id=user_id,
                    suggested=suggested,
                    other=other,
                )
            logging.info(f"Updated hedayat_fields for user {user_id}")
        except Exception as e:
            logging.error(f"Error updating hedayat_fields for user {user_id}: {str(e)}")
            # Don't raise - this is not critical for report generation

    def _update_scl_scores(self, user_id: str, context) -> None:
        """Update or insert scl_scores record with JSON data containing value, name, color, chart_name, and image_name for each key."""
        try:

            scl_scores_json = {}
            for key, value in context.factor_scores.items():
                if key in CALC_DATA:
                    calc_data_info = CALC_DATA[key]
                    image_name = select_scl_score_image_name(key, value)

                    scl_scores_json[key] = {
                        "value": value,
                        "name": calc_data_info.get("name", ""),
                        "color": calc_data_info.get("color", ""),
                        "chart_name": calc_data_info.get("chart_name", ""),
                        "image_name": image_name
                    }

            # Convert to JSON string
            scl_date_json = json.dumps(scl_scores_json, ensure_ascii=False)

            with session_scope() as session:
                upsert_scl_score(session=session, user_id=user_id, scl_date=scl_date_json)
            logging.info(f"Updated scl_scores for user {user_id}")
        except Exception as e:
            logging.error(f"Error updating scl_scores for user {user_id}: {str(e)}")
            # Don't raise - this is not critical for report generation

    def _generate_second_report_charts(self, data: Dict, categories: List, branches: List,
                                       suggested_other: List, user_directory: str,
                                       institute_name: str, consultant_name: str,
                                       user_id: str, phone: str,
                                       chart_directory: str) -> Tuple[
        Dict[str, Path], Dict, List, List, List]:
        """Generate all charts for the second report."""
        report_info = {
            "#name": data.get("student_name", ""),
            "#inst_name": institute_name,
            "#con_name": consultant_name,
            "سلااااااااااام": personality_info(data)
        }
        colors_tag = []
        colors_color = []
        state_values_by_branch_id = {}

        try:
            for branch in branches:
                branch_id = report2_branch_id(branch)
                if branch_id not in STATE_TAG_BY_BRANCH_ID:
                    raise ValueError(f"Unknown Report2 Brain BranchId: {branch_id}")
                if branch_id in state_values_by_branch_id:
                    raise ValueError(f"Duplicate Report2 Brain BranchId: {branch_id}")
                fields_match = get_fields_matches(branch["Value"])
                state_tag = STATE_TAG_BY_BRANCH_ID[branch_id]
                colors_tag.append(state_tag)
                colors_color.append(fields_match[1])
                report_info[state_tag] = persianize_report2_text(fields_match[0])
                report_info[f"#{branch_id}_branch_color"] = REPORT2_BRANCH_COLORS[branch_id]
                state_values_by_branch_id[branch_id] = fields_match[0]

            fields = [
                item for branch_id in REPORT2_BRANCH_IDS
                for item in suggested_other[branch_id][2]
            ]
            # Prepare field matches
            fields_matched = self._prepare_field_matches(suggested_other, report_info)
            chart_media = render_report2_media(branches, categories, fields, chart_directory)
            if set(state_values_by_branch_id) != set(REPORT2_BRANCH_IDS):
                raise ValueError(
                    "Report2 result-state data must contain all seven Brain branches; "
                    f"received BranchIds={sorted(state_values_by_branch_id)}"
                )
            state_data = [state_values_by_branch_id[branch_id] for branch_id in REPORT2_BRANCH_IDS]
            with session_scope() as session:
                upsert_result_state(session=session, user_id=user_id, state_data=state_data)
            return chart_media, report_info, fields_matched, colors_tag, colors_color

        except Exception as e:
            logging.error(f"Error generating second report charts: {str(e)}")
            raise

    def _prepare_scatter_data(self, branches: List, suggested_other: List, report_info: Dict,
                              colors_tag: List, colors_color: List, user_id: str, phone: str) -> Dict:
        """Prepare data for scatter chart."""
        x_positions = []
        all_values = []
        all_diameters = []
        all_colors = []
        branch_labels = []
        branch_lines = []
        current_x = 0
        state_data = []

        for branch in branches:
            branch_id = report2_branch_id(branch)
            fields_match = get_fields_matches(branch["Value"])
            state_tag = STATE_TAG_BY_BRANCH_ID[branch_id]
            colors_tag.append(state_tag)
            colors_color.append(fields_match[1])

            tag_branch_color = f"#{branch_id}_branch_color"
            branch_name = branch["Branch"]
            branch_start_x = current_x
            branch_lines.append(current_x - 0.5)

            # Process fields in this branch
            branch_fields = suggested_other[branch_id][2]
            for item in branch_fields:
                x_positions.append(current_x)
                all_values.append(item["Personality"])
                all_diameters.append(item["Ratio"])
                all_colors.append(BRANCH_COLOR[int(item['BranchId'])])
                current_x += 1

            branch_end_x = current_x - 1
            branch_labels.append(((branch_start_x + branch_end_x) / 2, branch_name))
            report_info[state_tag] = fields_match[0]
            state_data.append(fields_match[0])
            report_info[tag_branch_color] = REPORT2_BRANCH_COLORS[branch_id]

        with session_scope() as session:
            upsert_result_state(session=session, user_id=user_id, state_data=state_data)
        return {
            "branch_lines": branch_lines,
            "current_x": current_x,
            "x_positions": x_positions,
            "all_values": all_values,
            "all_diameters": all_diameters,
            "all_colors": all_colors,
            "branch_labels": branch_labels,
            "state_data": state_data
        }

    def _prepare_field_matches(self, suggested_other: Dict[int, tuple], report_info: Dict) -> Dict[int, tuple]:
        """Prepare field matches for report generation."""
        fields_matched = {}

        for branch_id in REPORT2_BRANCH_IDS:
            branch_data = suggested_other[branch_id]
            suggested_list = []
            other_list = []

            # Process suggested fields
            sorted_suggested = sorted(branch_data[0], key=lambda x: x['Personality'], reverse=True)
            top_field_tags = STATE_INFO_BY_BRANCH_ID[branch_id][0]

            if not sorted_suggested:
                for tag in top_field_tags:
                    report_info[tag] = 'رشته ای یافت نشد!'
                suggested_list.append(['هیچ رشته ای یافت نشد!', '*' * 0, '*' * 10, '*' * 0, '*' * 10])
            else:
                for field in sorted_suggested:
                    suggested_list.append([
                        field["Field"],
                        field["IQStars"],
                        '*' * (10 - len(field["IQStars"])),
                        field["PersonalityStars"],
                        '*' * (10 - len(field["PersonalityStars"]))
                    ])
                for i, tag in enumerate(top_field_tags):
                    field_data = sorted_suggested[i] if i < len(sorted_suggested) else {"Field": 'رشته ای یافت نشد!'}
                    report_info[tag] = field_data["Field"]

            # Process other fields
            sorted_other = sorted(branch_data[1], key=lambda x: x['Personality'], reverse=True)
            but_field_tags = STATE_INFO_BY_BRANCH_ID[branch_id][1]

            if not sorted_other:
                for tag in but_field_tags:
                    report_info[tag] = 'رشته ای یافت نشد!'
                other_list.append(['هیچ رشته ای یافت نشد!', '↓' * 10])
            else:
                for field in sorted_other:
                    other_list.append([
                        field["Field"],
                        '↓' * (10 - int(field["Color"]))
                    ])
                last_other = sorted_other[-3:][::-1]
                for i, tag in enumerate(but_field_tags):
                    field_data = last_other[i] if i < len(last_other) else {"Field": 'رشته ای یافت نشد!'}
                    report_info[tag] = field_data["Field"]

            fields_matched[branch_id] = (suggested_list, other_list)

        return fields_matched

    def _compute_scl_scores(self, user_id: str, runtime_provider) -> tuple[Dict, List[int]]:
        """Compute SCL labels for a user based on quiz question answer rows."""
        try:
            labels, missing_questions = runtime_provider.score_user(int(user_id))
            return labels, missing_questions
        except Exception as e:
            logging.error(f"Error computing SCL scores for user {user_id}: {e}")
            raise

    def _calculate_scl_calc_data(self, labels: Dict[str, float]) -> Dict[str, float]:
        """
        Calculate scl_calc_data for each tag in CALC_DATA based on labels.

        For each tag:
        - For positive_labels: (value of label from labels) / count(bookmark_scl_object[label])
        - For negative_labels: (value of label from labels - count(bookmark_scl_object[label])*4) / count(bookmark_scl_object[label])
        - Final value: (sum of positive + sum of negative) / (len(positive_labels) + len(negative_labels))

        Args:
            labels: Dictionary with label names as keys and their computed values

        Returns:
            Dictionary with tag names as keys and calculated values
        """
        scl_calc_data = {}
        # this is checkout the scores
        for label in labels.keys():
            if label in ["generalSE", "professionalSE", "familySE", "socialSE"]:
                label_value = labels.get(label)
                labels[label] = label_value * 4
            if label in ["OCD"]:
                ocd_dict = labels.get(label)
                for ocd_label in ocd_dict.keys():
                    ocd_value = ocd_dict.get(ocd_label)
                    ocd_dict[ocd_label] = ocd_value * 4
                labels[label] = ocd_dict
        for tag, tag_data in CALC_DATA.items():
            positive_labels = tag_data.get("positive_labels", [])
            negative_labels = tag_data.get("negative_labels", [])

            positive_sum = 0.0
            negative_sum = 0.0
            # Calculate for positive labels
            for label in positive_labels:
                if label in bookmark_scl_object:
                    if label in ["ocd", "ocd1", "ocd2", "ocd3", "ocd4"]:
                        label_value = labels["OCD"][label]
                    else:
                        label_value = labels[label]
                    count = bookmark_scl_object[label]["count"]
                    if count > 0:
                        positive_sum += label_value / count

            # Calculate for negative labels
            for label in negative_labels:
                if label in bookmark_scl_object:
                    if label in ["ocd", "ocd1", "ocd2", "ocd3", "ocd4"]:
                        label_value = labels["OCD"][label]
                    else:
                        label_value = labels[label]
                    count = bookmark_scl_object[label]["count"]
                    if count > 0:
                        negative_sum += ((count * 4) - label_value) / count

            # Calculate final value
            total_labels_count = len(positive_labels) + len(negative_labels)
            if total_labels_count > 0:
                scl_calc_data[tag] = (positive_sum + negative_sum) / total_labels_count
            else:
                scl_calc_data[tag] = 0.0

        return scl_calc_data

    def _handle_scl_report(self, user_id: str, runtime_provider=None) -> None:
        """Handle SCL kind: compute labels and store result in redis_logs."""
        try:
            start_time = time.time()
            report_kind = "SCL"

            # Validate quiz data
            runtime_provider = runtime_provider or self._validate_quiz_data(
                user_id,
                report_kind,
            )

            # Get student information
            student, student_name, phone, institute_name, consultant_name, logo_path = self._get_student_info(user_id)
            # Build user_info object from USER_TAGS_INFO keys mapped to student info
            user_info = {}
            for tag_key in USER_TAGS_INFO.keys():
                if tag_key == "studentname":
                    user_info[tag_key] = student_name
                elif tag_key == "instname":
                    user_info[tag_key] = institute_name
                elif tag_key == "conname":
                    user_info[tag_key] = consultant_name
                else:
                    user_info[tag_key] = ""  # Default empty for unknown keys
            user_info["Studentname"] = student_name
            # Create report directory
            user_directory = self._create_report_directory(phone)

            with session_scope() as session:
                update_redis_log_status(
                    session=session,
                    user_id=user_id,
                    kind="SCL",
                    result="SCL computation started in scheduler",
                    status=1,
                )

            labels, missing_questions = self._compute_scl_scores(
                user_id,
                runtime_provider,
            )
            scl_calc_data = self._calculate_scl_calc_data(labels)
            with session_scope() as session:
                upsert_quiz_labels(
                    session=session,
                    user_id=user_id,
                    quiz_kind=runtime_provider.package_name,
                    labels=labels,
                    metadata={"missing_questions": missing_questions},
                    definition_version=runtime_provider.definition_versions[0],
                    scoring_version=runtime_provider.scoring_version,
                )

            # Prepare one shared presentation context for the complete SCL report set.
            calc_key_to_advice = {
                "drug_addicion": "addictionadvice",
                "body_problem": "bodyadvice",
                "sleep_problem": "Sleepadvice",
                "wage_future": "Wagefutureadvice",
                "game_addiction": "Mobileadvice",
                "study_problem": "studyadvice",
                "anxiety": "Anxadvice",
                "depression": "Depadvice",
                "ocd": "Ocdadvice",
                "motivation": "Motadvice",
                "self_confident": "Confadvice",
                "truma": "Trumaadvice",
                "adhd": "Adhdadvice",
                "family_problem": "Familyadvice",
                "interpersonal": "Interadvice",
                "ideal": "Idealadvice",
            }
            calc_key_to_prefix = {
                "drug_addicion": "addict",
                "body_problem": "body",
                "sleep_problem": "sleep",
                "wage_future": "future",
                "game_addiction": "game",
                "study_problem": "study",
                "anxiety": "anx",
                "depression": "dep",
                "ocd": "ocd",
                "motivation": "motive",
                "self_confident": "conf",
                "truma": "ptsd",
                "adhd": "adhd",
                "family_problem": "family",
                "interpersonal": "interp",
                "ideal": "ideal",
            }
            gray_color = "CCCCCC"
            colors_tag = []
            colors_color = []

            def calculate_color_from_value(value: float) -> str:
                if value < 0:
                    value = 0.0
                if value < 1.0:
                    return "33CC33"
                if value < 2.0:
                    return "FFFF66"
                if value < 3.0:
                    return "FF9900"
                return "FF0000"

            for color_tag_key, color_tag_info in COLOR_TAGS.items():
                calc_data_key = color_tag_key.replace("_so", "")
                if calc_data_key not in scl_calc_data:
                    continue
                value = scl_calc_data[calc_data_key]
                if value < 2.0:
                    colors_tag.append(color_tag_info["tag_triangle"])
                    colors_color.append(gray_color)
                colors_tag.append(color_tag_info["tag_circle"])
                colors_color.append(calculate_color_from_value(value))

            def round_to_quarter(value: float) -> float:
                return round(value * 4) / 4

            skill_tags = ["vav", "vaav", "vaaav", "vaaaav", "vaaaaav", "vaaaaaav"]
            skill_keys = ["body_problem", "game_addiction", "wage_future", "drug_addicion",
                          "sleep_problem", "study_problem"]
            psycho_tags = ["waw", "waaw", "waaaw", "waaaaw", "waaaaaw"]
            psycho_keys = ["ocd", "depression", "motivation", "self_confident", "anxiety"]
            real_tags = ["zaz", "zaaz", "zaaaz", "zaaaaz", "zaaaaaz"]
            real_keys = ["family_problem", "truma", "adhd", "interpersonal", "ideal"]

            report3_text_replacements = {}
            report3_needed = []
            report3_unneeded = []
            severity_states = {}
            priorities = {}
            selected_advice = {}
            for key in CALC_DATA:
                if key not in scl_calc_data:
                    continue
                prefix = calc_key_to_prefix.get(key)
                if not prefix:
                    continue
                value = scl_calc_data[key]
                state = get_statefast_value(value)
                priority = get_interfast_value(value)
                severity_states[key] = state
                priorities[key] = priority
                report3_text_replacements[f"{prefix}statefast"] = state
                report3_text_replacements[f"{prefix}interfast"] = priority
                report3_text_replacements[f"{prefix}scorefast"] = str(round_to_quarter(value * 2.5))
                report3_text_replacements[f"{prefix}fast"] = get_report_text(f"{prefix}fast", value)

                advice_key = calc_key_to_advice.get(key)
                if advice_key:
                    advice_labels = [f"{advice_key}{index}" for index in range(1, 5)]
                    if 0 <= value < 1:
                        keep_index = 0
                    elif 1 <= value < 2:
                        keep_index = 1
                    elif 2 <= value < 3:
                        keep_index = 2
                    else:
                        keep_index = 3
                    selected_advice[key] = advice_labels[keep_index]
                    for index, label in enumerate(advice_labels):
                        (report3_needed if index == keep_index else report3_unneeded).append(label)

            def process_layer(keys, tags):
                ordered_keys = order_r3_layer_factor_ids(keys, scl_calc_data)[:len(tags)]
                for index, key in enumerate(ordered_keys):
                    report3_text_replacements[tags[index]] = CALC_DATA.get(key, {}).get("name", "")
                return ordered_keys

            report3_layer_order = {
                "surface": process_layer(skill_keys, skill_tags),
                "psych": process_layer(psycho_keys, psycho_tags),
                "root": process_layer(real_keys, real_tags),
            }

            report3_text_replacements.update(SCL_REPORT3_HIDDEN_MARKER_REPLACEMENTS)

            report5_text_replacements = {}
            report5_needed = []
            report5_unneeded = []
            for key in CALC_DATA:
                if key not in scl_calc_data:
                    continue
                prefix = calc_key_to_prefix.get(key)
                if not prefix:
                    continue
                value = scl_calc_data[key]
                report5_text_replacements[f"{prefix}statefast"] = get_statefast_value(value)
                report5_text_replacements[f"{prefix}interfast"] = get_interfast_value(value)
                report5_text_replacements[f"{prefix}scorefast"] = str(round_to_quarter(value * 2.5))
                fast_labels = [f"{prefix}fast{index}" for index in range(1, 5)]
                if 0 <= value < 1:
                    keep_index = 0
                elif 1 <= value < 2:
                    keep_index = 1
                elif 2 <= value < 3:
                    keep_index = 2
                else:
                    keep_index = 3
                for index, label in enumerate(fast_labels):
                    (report5_needed if index == keep_index else report5_unneeded).append(label)

            report5_categories = []
            report5_values = []
            report5_colors = []
            for key in CALC_DATA:
                if key in scl_calc_data:
                    report5_categories.append(CALC_DATA[key]["chart_name"])
                    report5_values.append(round(scl_calc_data[key] / 4 * 100, 2))
                    report5_colors.append(CALC_DATA[key]["color"])

            report3_user_info = {
                **user_info,
                "#name": student_name,
                "#con_name": consultant_name,
                "#inst_name": institute_name,
                **report3_text_replacements,
            }
            other_report_text_replacements = {
                key: value for key, value in report3_text_replacements.items()
                if key not in SCL_REPORT3_HIDDEN_MARKER_REPLACEMENTS
            }
            report4_user_info = {**user_info, **other_report_text_replacements}
            report4_values = {key: scl_calc_data.get(key, 0.0)
                              for key in ("anxiety", "ocd", "depression")}
            report4_kind = max(report4_values, key=report4_values.get)
            if report4_values[report4_kind] <= 0:
                report4_kind = None

            image_selections, active_ocd_subtypes, active_ocd_count_asset = select_scl_report3_media(
                scl_calc_data, labels
            )
            report5_user_info = {**report4_user_info, **report5_text_replacements}

            with open(os.path.join(user_directory, "labels.json"), "w", encoding="utf-8") as f:
                json.dump(labels, f, ensure_ascii=False, indent=2)
            with open(os.path.join(user_directory, "user_info.json"), "w", encoding="utf-8") as f:
                json.dump(report3_user_info, f, ensure_ascii=False, indent=2)
            with open(os.path.join(user_directory, "report_text_replacements.json"), "w", encoding="utf-8") as f:
                json.dump(report3_text_replacements, f, ensure_ascii=False, indent=2)
            with open(os.path.join(user_directory, "scl_calc_data.json"), "w", encoding="utf-8") as f:
                json.dump(scl_calc_data, f, ensure_ascii=False, indent=2)

            context = make_scl_report_context(
                student={
                    "user_id": str(user_id),
                    "name": student_name,
                    "phone": phone,
                    "institute_name": institute_name,
                    "consultant_name": consultant_name,
                    "logo_path": str(logo_path) if logo_path else None,
                },
                labels=labels,
                factor_scores=scl_calc_data,
                severity_states=severity_states,
                priorities=priorities,
                selected_advice=selected_advice,
                report3_user_info=report3_user_info,
                report3_text_replacements=report3_text_replacements,
                report3_layer_order=report3_layer_order,
                report3_needed=report3_needed,
                report3_unneeded=report3_unneeded,
                report3_color_targets=colors_tag,
                report3_color_values=colors_color,
                report4_user_info=report4_user_info,
                report4_kind=report4_kind,
                report5_user_info=report5_user_info,
                report5_needed=report5_needed,
                report5_unneeded=report5_unneeded,
                report5_categories=report5_categories,
                report5_values=report5_values,
                report5_colors=report5_colors,
                image_selections=image_selections,
                active_ocd_subtypes=active_ocd_subtypes,
                active_ocd_count_asset=active_ocd_count_asset,
            )
            published_reports = render_scl_report_set(context, user_directory)
            logging.info("Generated SCL reports for user %s: %s", user_id, ", ".join(published_reports))

            # Update or insert scl_scores record
            self._update_scl_scores(user_id, context)

            with session_scope() as session:
                update_redis_log_status(
                    session=session,
                    user_id=user_id,
                    kind="SCL",
                    result="user info checked in scheduler",
                    status=2,
                )

            logging.info(
                "Successfully computed SCL labels for user %s in %.2f seconds",
                user_id,
                time.time() - start_time,
            )
        except Exception as e:
            logging.exception(
                "Failed to compute SCL report data for user %s: %s", user_id, e
            )
            self._log_error(user_id, "SCL", str(e))
            raise

    def _handle_psy_labels(self, user_id: str, runtime_provider=None) -> None:
        """Compute and persist labels for PSY packages without generating a PDF."""
        if runtime_provider is None:
            raise ValueError("PSY runtime provider is required")
        report_kind = runtime_provider.package_name
        try:
            with session_scope() as session:
                update_redis_log_status(
                    session=session,
                    user_id=user_id,
                    kind=runtime_provider.package_name,
                    result="PSY label computation started in scheduler",
                    status=1,
                )

            labels, missing_questions = runtime_provider.score_user(int(user_id))
            with session_scope() as session:
                stored_ag_labels = upsert_quiz_labels(
                    session=session,
                    user_id=user_id,
                    quiz_kind=runtime_provider.package_name,
                    labels=labels,
                    metadata={"missing_questions": missing_questions},
                    definition_version=runtime_provider.definition_versions[0],
                    scoring_version=runtime_provider.scoring_version,
                )
                update_redis_log_status(
                    session=session,
                    user_id=user_id,
                    kind=runtime_provider.package_name,
                    result="PSY labels stored successfully",
                    status=2,
                )
        except Exception as exc:
            logging.exception(
                "Failed to compute PSY labels for user %s and package %s: %s",
                user_id,
                report_kind,
                exc,
            )
            self._log_error(user_id, report_kind, str(exc))
            raise

    def _handle_ag_report(self, user_id: str, runtime_provider=None) -> None:
        """Main method to generate complete report for a user."""
        try:
            start_time = time.time()
            report_kind = "AG"

            # Validate quiz data
            runtime_provider = runtime_provider or self._validate_quiz_data(
                user_id,
                report_kind,
            )

            # Get student information
            student, student_name, phone, institute_name, consultant_name, logo_path = self._get_student_info(user_id)

            # Create report directory
            user_directory = self._create_report_directory(phone)

            # Update log status for AG job
            with session_scope() as session:
                update_redis_log_status(
                    session=session,
                    user_id=user_id,
                    kind="AG",
                    result="user info check in scheduler",
                    status=1,
                )

            # Compute brain info
            data, fields, categories, branches, correct, wrong, unanswered = compute_brain_info(
                user_id,
                phone=phone,
                scorer=runtime_provider.score_user,
                calculator=runtime_provider.calculate_report_data,
            )

            quiz_score_json = json.dumps(
                {"correct": correct, "wrong": wrong, "unanswered": unanswered},
                ensure_ascii=False,
            )
            brain_fields_json = json.dumps(fields, ensure_ascii=False)
            brain_categories_json = json.dumps(categories, ensure_ascii=False)
            brain_branches_json = json.dumps(branches, ensure_ascii=False)

            with session_scope() as session:
                stored_ag_labels = upsert_quiz_labels(
                    session=session,
                    user_id=user_id,
                    quiz_kind=runtime_provider.package_name,
                    labels=data,
                    metadata={
                        "correct": correct,
                        "wrong": wrong,
                        "unanswered": unanswered,
                    },
                    definition_version=runtime_provider.definition_versions[0],
                    scoring_version=runtime_provider.scoring_version,
                )
                upsert_score(
                    session=session,
                    user_id=user_id,
                    quiz_score=quiz_score_json,
                    brain_fields=brain_fields_json,
                    brain_categories=brain_categories_json,
                    brain_branches=brain_branches_json,
                )

            # Persist raw fields to JSON for debugging/inspection
            try:
                with open(os.path.join(user_directory, f"fields_{phone}.json"), "w", encoding="utf-8") as f:
                    json.dump(fields, f, ensure_ascii=False, indent=2)
            except Exception as exc:
                logging.warning("Could not save fields debug file: %s", exc)

            # Process and update hedayat_fields
            suggested_names, other_names = self._process_hedayat_fields(fields)
            self._update_hedayat_fields(user_id, suggested_names, other_names)

            # Add student info to data
            data["student_name"] = student_name
            data["user_id"] = int(user_id)
            data["phone"] = phone
            data["correct"] = correct
            data["wrong"] = wrong
            data["unanswered"] = unanswered

            # Generate AG Report 1 from the persisted, versioned label payload.
            chart_data = build_chart_data(stored_ag_labels["labels"])
            first_report_info = self._build_first_report_text(
                data,
                institute_name,
                consultant_name,
                chart_data,
            )
            with TemporaryDirectory(prefix="ag-report1-charts-", dir=user_directory) as chart_directory:
                report_media = render_report_media(chart_data, chart_directory)
                effective_logo = Path(logo_path) if logo_path and Path(logo_path).is_file() else DEFAULT_REPORT_LOGO_PATH
                if effective_logo and effective_logo.is_file():
                    report_media["image14.jpeg"] = effective_logo

                generate_first_report_documents(
                    list(first_report_info.keys()),
                    list(first_report_info.values()),
                    list(report_media.keys()),
                    list(report_media.values()),
                    user_directory,
                    [],
                    [],
                    [],
                    phone,
                )

            report1_pdf = Path(user_directory) / "Report1.pdf"
            if not report1_pdf.is_file() or report1_pdf.stat().st_size == 0:
                raise RuntimeError("AG Report 1 generation did not produce a non-empty PDF")

            # Generate second report
            suggested_other = self._get_sorted_suggested_fields(fields)
            with TemporaryDirectory(prefix="ag-report2-charts-", dir=user_directory) as chart_directory:
                report2_media, second_report_info, fields_matched, colors_tag, colors_color = \
                    self._generate_second_report_charts(
                        data, categories, branches, suggested_other, user_directory,
                        institute_name, consultant_name, user_id, phone, chart_directory,
                    )
                logo = Path(logo_path) if logo_path and Path(logo_path).is_file() else DEFAULT_REPORT_LOGO_PATH
                if logo and logo.is_file():
                    report2_media["image15.jpeg"] = logo
                second_report_images = tuple(
                    target for target in SECOND_REPORT_IMAGES if target in report2_media
                )
                second_report_pictures = [str(report2_media[target]) for target in second_report_images]
                # Persist matched fields and benchmark names for debugging/traceability.
                try:
                    with open(os.path.join(user_directory, f"fields_matched_{phone}.json"), "w", encoding="utf-8") as f:
                        json.dump(
                            {
                                "fields_matched": fields_matched,
                                "fields_benchmark_name": FIELDS_BENCHMARK_NAME,
                            },
                            f,
                            ensure_ascii=False,
                            indent=2,
                        )
                except Exception as exc:
                    logging.warning("Could not save fields_matched debug file: %s", exc)

                generate_second_report_documents(
                    user_directory,
                    fields_matched,
                    FIELDS_BENCHMARK_NAME,
                    second_report_images,
                    second_report_pictures,
                    list(second_report_info.keys()),
                    list(second_report_info.values()),
                    colors_tag,
                    colors_color,
                    phone
                )

            # Update completion status
            with session_scope() as session:
                update_redis_log_status(
                    session=session,
                    user_id=user_id,
                    kind="AG",
                    result="user info checked in scheduler",
                    status=2,
                )

            logging.info(
                f"Successfully generated complete report for user {user_id}. "
                f"Time taken: {time.time() - start_time:.2f} seconds"
            )

        except Exception as e:
            logging.exception(
                f"Failed to generate report for user {user_id}: {str(e)}"
            )
            self._log_error(user_id, "AG", str(e))
            raise

    def run(self) -> None:
        """Main scheduler loop."""
        logging.info("AG Report scheduler started")

        try:
            while True:
                queue_item = self.redis.lpop(REDIS_QUEUE_NAME)
                if queue_item is None:
                    logging.debug("No users in queue, sleeping...")
                    time.sleep(10)
                    continue

                # Support both legacy plain user_id and new JSON payloads
                try:
                    try:
                        payload = json.loads(queue_item)
                        user_id = str(payload.get("user_id"))
                        kind = (payload.get("kind") or "AG").upper()
                    except Exception:
                        # Legacy format: queue_item is just user_id, assume AG
                        user_id = str(queue_item)
                        kind = "AG"

                    logging.info(f"Processing user ID: {user_id} with kind: {kind}")

                    runtime_provider = self._validate_quiz_data(user_id, kind)
                    runtime_provider.generate_report(self, user_id)

                    time.sleep(10)

                except Exception as e:
                    logging.exception(f"Error processing user {user_id}: {str(e)}")
                    continue

        except KeyboardInterrupt:
            logging.info("AG Report scheduler stopped by user")
        except Exception as e:
            logging.error(f"AG Report scheduler crashed: {str(e)}")
            raise


if __name__ == "__main__":
    try:
        scheduler = AGReportScheduler()
        scheduler.run()
    except Exception as e:
        logging.critical(f"Fatal error in AG report scheduler: {str(e)}")
        raise
