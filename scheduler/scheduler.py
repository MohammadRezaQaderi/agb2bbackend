import os
import time
import redis
import json
import pyodbc
import logging
import sys
import io
from datetime import datetime
from pathlib import Path
from typing import List, Tuple, Dict, Any

from helper.chart import bar, bidirection, gauge, bidirection_two_side, tube, scatter, horizontal
import helper.db.db_helper as db_helper
from helper.quiz import answer_store
from helper.office.excel_helper import LoadExcelSourceFile, compute_brain_info
from helper.quiz.check_score import score_computation_scl
from helper.quiz.report_info import *
from helper.quiz.bookmarks_info import CALC_DATA, USER_TAGS_INFO, COLOR_TAGS
from helper.quiz.scl_answer_info import bookmark_scl_object
from helper.quiz.scl_report_info import get_statefast_value, get_interfast_value, get_report_text
from helper.office.word_helper import (
    generate_first_report_documents,
    generate_second_report_documents,
    generate_third_report_documents,
    generate_forth_report_documents,
    generate_fifth_report_documents,
)
from config import (
    BRAIN_EXCEL_PATH,
    REPORTS_DIR,
    INS_PIC_DIR,
    PICS_WORD_SCL_DIR,
    REDIS_QUEUE_NAME,
    REDIS_HOST,
    REDIS_PORT,
    REDIS_PASSWORD,
    REDIS_DB,
    DB_CONN_STRING,
)

master_file = None
master_sheet = None


def load_master_excel():
    global master_file, master_sheet
    if master_file is None or master_sheet is None:
        master_file = LoadExcelSourceFile(str(BRAIN_EXCEL_PATH))
        master_sheet = master_file.sheets["نسخه اصلی"]
    return master_file, master_sheet

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

SECOND_REPORT_IMAGES = [
    'image27.png', 'image30.png', 'image32.png', 'image36.png', 'image37.png', 'image40.png',
    'image41.png', 'image44.png', 'image45.png', 'image48.png', 'image49.png', 'image52.png',
    'image53.png', 'image56.png', 'image57.png', 'image61.png', 'image62.png', 'image65.png',
    'image66.png', 'image69.png'
]

CATEL_EFFECT = [
    ['سرآمد', ' ۱۶۴ به بالا', ' ۰/۰۰۳ ٪'], ['نابغه', ' ۱۴۸ - ۱۶۳', ' ۰/۱۳ ٪'],
    ['تیزهوش', ' ۱۳۲-۱۴۷', ' ۲/۱۴ ٪'], ['باهوش', ' ۱۲۰ - ۱۳۱', ' ۸/۲۹ ٪'],
    ['قوی', ' ۱۱۰ - ۱۱۹', ' ۱۶/۰۳ ٪'], ['متوسط', ' ۹۰ - ۱۰۹', ' ۴۶/۸ ٪'],
    ['مرزی', ' ۶۸ - ۸۹', ' ۲۴/۳۲ ٪'], ['آموزش پذیر', ' ۵۲ - ۶۷', ' ۲/۱۴ ٪'],
    ['آموزش پذیر', ' ۵۲ - ۶۷', ' ۲/۱۴ ٪'], ['حمایت پذیر', ' ۳۶ به پایین', ' ۰/۰۰۳ ٪']
]

STATE_TAGS = ['#t_state', '#r_state', '#e_state', '#a_state', '#m_state', '#f_state', '#i_state']

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

FIELDS_BENCHMARK_NAME = [
    (('Reshteha_Tajrobi', ['رشته_پیشنهادی_تجربی', 'S1', 'S2', 'T1', 'T2']),
     ('Sayer_Tajrobi', ['سایر_تجربی', 'سایر_رنگ'])),

    (('Reshteha_Riazi', ['رشته_پیشنهادی_ریاضی', 'S1', 'S2', 'T1', 'T2']),
     ('Sayer_Riazi', ['سایر_ریاضی', 'سایر_رنگ'])),

    (('Reshteha_Ensani', ['رشته_پیشنهادی_انسانی', 'S1', 'S2', 'T1', 'T2']),
     ('Sayer_Ensani', ['سایر_انسانی', 'سایر_رنگ'])),

    (('Reshteha_Honar', ['رشته_پیشنهادی_هنر', 'S1', 'S2', 'T1', 'T2']),
     ('Sayer_Honar', ['سایر_هنر', 'سایر_رنگ'])),

    (('Reshteha_Keshavarzi', ['رشته_پیشنهادی_کشاورزی', 'S1', 'S2', 'T1', 'T2']),
     ('Sayer_Keshavarzi', ['سایر_کشاورزی', 'سایر_رنگ'])),

    (('Reshteha_Modiriat', ['رشته_پیشنهادی_مدیریت', 'S1', 'S2', 'T1', 'T2']),
     ('Sayer_Modiriat', ['سایر_مدیریت', 'سایر_رنگ'])),

    (('Reshteha_Sanat', ['رشته_پیشنهادی_صنعت', 'S1', 'S2', 'T1', 'T2']),
     ('Sayer_Sanat', ['سایر_صنعت', 'سایر_رنگ']))
]

CATEGORY_DEF_COLOR = {
    "دبیری": "#c8acdc", "مدیریت": "#a0a4bc", "علوم پایه": "#a0c4e4", "هنر": "#a0dcfc",
    "مهندسی سازه": "#99dfb9", "مهندسی صنعتی": "#d8ecbc", "الکترونیک و کامپیوتر": "#fffc9c",
    "علوم انسانی": "#ffe699", "مالی و حسابداری": "#ff9999", "روانشناسی": "#e69999",
    "روابط عمومی": "#c6acd9", "کشاورزی و امور دامی": "#99a6bf", "حقوق و علوم سیاسی": "#99c6e6",
    "خدمات فنی": "#99dff9", "تکنسین فنی": "#99dfb9", "بالینی و درمانی": "#d3ecb9",
    "تشخیصی و درمانی": "#ffff99", "تکنسین کامپیوتر": "#ffe699"
}

BRANCH_COLOR = {
    1: "#FF9900", 2: "#FF5050", 3: "#FFFF00", 4: "#00B050",
    5: "#0070C0", 6: "#00B0F0", 7: "#7030A0"
}

SCL_PIC_DICT = {"drug_addicion": [("image15.png", "drog4.png"), ("image16.png", "drog3.png"),
                                  ("image17.png", "drog1.png"), ("image18.png", "drog1.png")],
                "body_problem": [("image21.png", "physical problems4.png"),
                                 ("image22.png", "physical problems3.png"),
                                 ("image23.png", "physical problems2.png"),
                                 ("image24.png", "physical problems1.png")],
                "sleep_problem": [("image27.png", "sleep4.png"), ("image28.png", "sleep3.png"),
                                  ("image29.png", "sleep2.png"), ("image30.png", "sleep1.png")],
                "game_addiction": [("image33.png", "game4.png"), ("image34.png", "game3.png"),
                                   ("image35.png", "game2.png"), ("image36.png", "game1.png")],
                "wage_future": [("image39.png", "lack of foresight4.png"),
                                ("image40.png", "lack of foresight3.png"),
                                ("image41.png", "lack of foresight2.png"),
                                ("image42.png", "lack of foresight1.png")],
                "study_problem": [("image45.png", "study .weakness4.png"),
                                  ("image46.png", "study .weakness3.png"),
                                  ("image47.png", "study .weakness2.png"),
                                  ("image48.png", "study .weakness1.png")],
                "anxiety": [("image51.png", "anxiety4.png"), ("image53.png", "anxiety3.png"),
                            ("image54.png", "anxiety2.png"), ("image55.png", "anxiety1.png")],
                "depression": [("image61.png", "depression4.png"), ("image62.png", "depression3.png"),
                               ("image63.png", "depression2.png"), ("image64.png", "depression1.png")],
                "ocd": [("image69.png", "ocd3.png"), ("image70.png", "ocd4.png"), ("image71.png", "ocd2.png"),
                        ("image72.png", "ocd1.png")],
                "motivation": [("image77.png", "unmotivated4.png"), ("image78.png", "unmotivated3.png"),
                               ("image79.png", "unmotivated2.png"), ("image80.png", "unmotivated1.png")],
                "self_confident": [("image83.png", "Lack of self-confidence4.png"),
                                   ("image84.png", "Lack of self-confidence3.png"),
                                   ("image85.png", "Lack of self-confidence2.png"),
                                   ("image86.png", "Lack of self-confidence1.png")],
                "adhd": [("image89.png", "hyperactivity4.png"), ("image90.png", "hyperactivity3.png"),
                         ("image91.png", "hyperactivity2.png"), ("image93.png", "hyperactivity1.png")],
                "family_problem": [("image96.png", "family problem4.png"),
                                   ("image97.png", "family problem3.png"),
                                   ("image98.png", "family problem2.png"),
                                   ("image99.png", "family problem1.png")],
                "interpersonal": [("image102.png", "Interpersonal problems4.png"),
                                  ("image103.png", "Interpersonal problems3.png"),
                                  ("image104.png", "Interpersonal problems2.png"),
                                  ("image105.png", "Interpersonal problems1.png")],
                "truma": [("image108.png", "war4.png"), ("image109.png", "war3.png"),
                          ("image110.png", "war2.png"), ("image111.png", "war1.png")],
                "ideal": [("image125.png", "perfectionism4.png"), ("image125.png", "perfectionism3.png"),
                          ("image125.png", "perfectionism2.png"), ("image125.png", "perfectionism1.png")],
                }


class AGReportScheduler:
    def __init__(self):
        self.redis = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            password=REDIS_PASSWORD if REDIS_PASSWORD else None,
            db=REDIS_DB,
            decode_responses=True
        )

        try:
            self.db_conn = pyodbc.connect(DB_CONN_STRING)
            self.db_cursor = self.db_conn.cursor()
        except pyodbc.Error as e:
            logging.error(f"Database connection failed: {str(e)}")
            raise

    def _log_error(self, user_id: str, kind: str, error: str) -> None:
        """Log errors to database with user context."""
        try:
            db_helper.update_record(
                self.db_conn,
                self.db_cursor,
                "redis_logs",
                ["result", "status", "edited_time"],
                [f"Error: {error}", 3, datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
                "user_id = ? AND kind = ?",
                [str(user_id), (kind or "").upper()],
            )
        except Exception as e:
            logging.error(f"Failed to log error to database: {str(e)}")

    def _get_student_info(self, user_id: str):
        """Retrieve student information with institute and consultant details."""
        try:
            student_query = '''
                SELECT s.user_id, s.first_name, s.last_name, u.phone,
                       s.owner_user_id, s.consultant_user_id, owner.role AS owner_role
                FROM stu s
                INNER JOIN users u ON u.user_id = s.user_id
                LEFT JOIN users owner ON owner.user_id = s.owner_user_id
                WHERE s.user_id = ?
            '''
            student = db_helper.search_table(
                self.db_conn, self.db_cursor, student_query, user_id
            )

            if not student:
                raise ValueError(f"Student with ID {user_id} not found")

            institute_name = ""
            consultant_name = ""
            logo_path = None

            if student[6] == "ins":
                ins_query = 'SELECT user_id, name, logo FROM ins WHERE user_id = ?'
                institute = db_helper.search_table(self.db_conn, self.db_cursor, ins_query, student[4])
                institute_name = institute[1] if institute else ""

                if institute and institute[2]:
                    logo_path = os.path.join(INS_PIC_DIR, institute[2])

            elif student[6] == "sch":
                sch_query = 'SELECT user_id, name, logo FROM sch WHERE user_id = ?'
                school = db_helper.search_table(self.db_conn, self.db_cursor, sch_query, student[4])
                institute_name = school[1] if school else ""

                if school and school[2]:
                    logo_path = os.path.join(INS_PIC_DIR, school[2])
            else:
                ocon_query = 'SELECT first_name, last_name FROM ocon WHERE user_id = ?'
                consultant = db_helper.search_table(self.db_conn, self.db_cursor, ocon_query, student[4])
                institute_name = f"{consultant[0]} {consultant[1]}" if consultant else ""
                consultant_name = f"{consultant[0]} {consultant[1]}" if consultant else ""

            if student[5] and student[6] not in ["ocon"]:
                con_query = 'SELECT user_id, first_name, last_name FROM con WHERE user_id = ?'
                consultant = db_helper.search_table(self.db_conn, self.db_cursor, con_query, student[5])
                consultant_name = f"{consultant[1]} {consultant[2]}" if consultant else ""

            student_name = f"{student[1]} {student[2]}"
            phone = student[3]

            return student, student_name, phone, institute_name, consultant_name, logo_path

        except Exception as e:
            logging.error(f"Error getting student info: {str(e)}")
            self._log_error(user_id, "AG", str(e))
            raise

    def _validate_quiz_data(self, user_id: str, report_kind: str) -> None:
        """Validate that user has sufficient quiz data."""
        try:
            query = """
                SELECT COUNT(*) AS completed
                FROM quiz_attempt
                WHERE user_id = ? AND quiz_kind = ? AND state = 2
            """
            rows = db_helper.search_fetchall(
                conn=self.db_conn,
                cursor=self.db_cursor,
                query=query,
                field=(user_id, report_kind),
            )
            completed_count = int(rows[0]["completed"] or 0) if rows else 0

            if report_kind == "AG" and completed_count < 7:
                raise ValueError("Insufficient quiz data for report generation")
            if report_kind == "SCL" and completed_count < 4:
                raise ValueError("Insufficient quiz data for report generation")
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

    def _get_sorted_suggested_fields(self, fields: List) -> List:
        """Sort and group suggested fields by branch."""
        branch_groups = {}
        for item in fields:
            branch = item["BranchId"]
            branch_groups.setdefault(branch, []).append(item)

        def _c1_value(field: Dict) -> float:
            """Return numeric C1 value; fallback to 0 when missing/invalid."""
            try:
                return float(field.get("C1", 0) or 0)
            except (TypeError, ValueError):
                return 0.0

        # Ensure deterministic ordering by BranchId, so it aligns with FIELDS_BENCHMARK_NAME
        def _branch_sort_key(val):
            try:
                return int(val)
            except Exception:
                return val

        grouped_array = [branch_groups[k] for k in sorted(branch_groups.keys(), key=_branch_sort_key)]
        final_list = []

        for branch in grouped_array:
            suggested_list = [f for f in branch if _c1_value(f) > 0]
            other_list = [f for f in branch if _c1_value(f) <= 0]
            all_list = branch.copy()

            final_list.append((suggested_list, other_list, all_list))

        return final_list

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

    def _update_hedayat_fields(self, user_id: str, phone: str, suggested: str, other: str) -> None:
        """Update or insert hedayat_fields record."""
        try:
            query = 'SELECT user_id FROM hedayat_fields WHERE user_id = ?'
            exists = db_helper.search_table(self.db_conn, self.db_cursor, query, user_id)

            if exists is None:
                # Insert new record
                db_helper.insert_value(
                    self.db_conn, self.db_cursor,
                    "hedayat_fields",
                    "([user_id], [phone], [suggested], [other])",
                    (user_id, phone, suggested, other)
                )
            else:
                # Update existing record
                db_helper.update_record(
                    self.db_conn, self.db_cursor,
                    "hedayat_fields",
                    ['suggested', 'other', 'edited_time'],
                    [suggested, other, datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
                    "user_id = ?",
                    [str(user_id)]
                )
            logging.info(f"Updated hedayat_fields for user {user_id}")
        except Exception as e:
            logging.error(f"Error updating hedayat_fields for user {user_id}: {str(e)}")
            # Don't raise - this is not critical for report generation

    def _update_scl_scores(self, user_id: str, phone: str, scl_calc_data: Dict[str, float]) -> None:
        """Update or insert scl_scores record with JSON data containing value, name, color, chart_name, and image_name for each key."""
        try:

            scl_scores_json = {}
            for key, value in scl_calc_data.items():
                if key in CALC_DATA:
                    calc_data_info = CALC_DATA[key]

                    image_name = ""
                    if key in SCL_PIC_DICT:
                        if value >= 3:
                            image_index = 0
                        elif value >= 2:
                            image_index = 1
                        elif value >= 1:
                            image_index = 2
                        else:
                            image_index = 3

                        _, new_image_name = SCL_PIC_DICT[key][image_index]
                        image_name = new_image_name

                    scl_scores_json[key] = {
                        "value": value,
                        "name": calc_data_info.get("name", ""),
                        "color": calc_data_info.get("color", ""),
                        "chart_name": calc_data_info.get("chart_name", ""),
                        "image_name": image_name
                    }

            # Convert to JSON string
            scl_date_json = json.dumps(scl_scores_json, ensure_ascii=False)

            # Check if record exists
            query = 'SELECT user_id FROM scl_scores WHERE user_id = ?'
            exists = db_helper.search_table(self.db_conn, self.db_cursor, query, user_id)

            if exists is None:
                # Insert new record
                db_helper.insert_value(
                    self.db_conn, self.db_cursor,
                    "scl_scores",
                    "([user_id], [phone], [scl_date])",
                    (user_id, phone, scl_date_json)
                )
            else:
                # Update existing record
                db_helper.update_record(
                    self.db_conn, self.db_cursor,
                    "scl_scores",
                    ['scl_date', 'edited_time'],
                    [scl_date_json, datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
                    "user_id = ?",
                    [str(user_id)]
                )
            logging.info(f"Updated scl_scores for user {user_id}")
        except Exception as e:
            logging.error(f"Error updating scl_scores for user {user_id}: {str(e)}")
            # Don't raise - this is not critical for report generation

    def _generate_second_report_charts(self, data: Dict, categories: List, branches: List,
                                       suggested_other: List, user_directory: str,
                                       institute_name: str, consultant_name: str,
                                       user_id: str, phone: str) -> Tuple[
        List, Dict, List, List, List]:
        """Generate all charts for the second report."""
        report_pictures = []
        report_info = {
            "#name": data.get("student_name", ""),
            "#inst_name": institute_name,
            "#con_name": consultant_name,
            "سلااااااااااام": personality_info(data)
        }
        colors_tag = []
        colors_color = []

        try:
            # Category bar chart
            sorted_categories = sorted(categories, key=lambda x: x["Value"], reverse=True)
            values = [int(item["Value"]) for item in sorted_categories]
            category_names = [item["Category"] for item in sorted_categories]
            colors = [CATEGORY_DEF_COLOR[item] for item in category_names]

            bar_path = bar.create_bar_chart(
                categories=category_names,
                title='',
                values=values,
                colors=colors,
                rotation=90,
                size=9,
                path=user_directory,
                filename='secondbar'
            )
            report_pictures.append(f"{bar_path}.png")

            # Gauge charts for categories
            for index, cat in enumerate(categories):
                value = max(cat["Value"], 10)
                ranges = [(0, 30), (31, 70), (71, 100)]
                gauge_path = gauge.create_gauge_chart(
                    value=value,
                    labels=['', '', ''],
                    colors=['#42b74a', '#ffbb10', '#cf2020'],
                    ranges=ranges,
                    path=user_directory,
                    filename=f"gaugeSecond{index + 1}"
                )
                report_pictures.append(f"{gauge_path}.png")

            # Scatter chart
            scatter_data = self._prepare_scatter_data(branches, suggested_other, report_info, colors_tag, colors_color,
                                                      user_id, phone)
            scatter_path = scatter.create_scatter_chart(
                scatter_data["branch_lines"], scatter_data["current_x"],
                scatter_data["x_positions"], scatter_data["all_values"],
                scatter_data["all_diameters"], scatter_data["all_colors"],
                scatter_data["branch_labels"], path=user_directory, filename="scatter"
            )
            report_pictures.append(f"{scatter_path}.png")

            # Prepare field matches
            fields_matched = self._prepare_field_matches(suggested_other, report_info)

            return report_pictures, report_info, fields_matched, colors_tag, colors_color

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

        for index, branch in enumerate(branches):
            fields_match = get_fields_matches(branch["Value"])
            colors_tag.append(STATE_TAGS[index])
            colors_color.append(fields_match[1])

            tag_branch_color = f"#{index + 1}_branch_color"
            branch_name = branch["Branch"]
            branch_start_x = current_x
            branch_lines.append(current_x - 0.5)

            # Process fields in this branch
            for item in suggested_other[index][2]:
                x_positions.append(current_x)
                all_values.append(item["Personality"])
                all_diameters.append(item["Ratio"] * 400)
                all_colors.append(BRANCH_COLOR[int(item['BranchId'])])
                current_x += 1

            branch_end_x = current_x - 1
            branch_labels.append(((branch_start_x + branch_end_x) / 2, branch_name))
            report_info[STATE_TAGS[index]] = fields_match[0]
            state_data.append(fields_match[0])
            report_info[tag_branch_color] = fields_match[1]

        # Persist result_state once per user_id (avoid duplicates)
        query = "SELECT user_id FROM result_state WHERE user_id = ?"
        exists = db_helper.search_table(self.db_conn, self.db_cursor, query, user_id)

        if exists is None:
            db_helper.insert_value(
                self.db_conn, self.db_cursor,
                "result_state",
                "([user_id], [phone], [t_state], [r_state], [e_state], [a_state], [m_state], [f_state], [i_state])",
                (
                    user_id,
                    phone,
                    state_data[0],
                    state_data[1],
                    state_data[2],
                    state_data[3],
                    state_data[4],
                    state_data[5],
                    state_data[6],
                ),
            )
        else:
            db_helper.update_record(
                self.db_conn, self.db_cursor,
                "result_state",
                ["phone", "t_state", "r_state", "e_state", "a_state", "m_state", "f_state", "i_state", "edited_time"],
                [
                    phone,
                    state_data[0],
                    state_data[1],
                    state_data[2],
                    state_data[3],
                    state_data[4],
                    state_data[5],
                    state_data[6],
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                ],
                "user_id = ?",
                [str(user_id)],
            )
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

    def _prepare_field_matches(self, suggested_other: List, report_info: Dict) -> List:
        """Prepare field matches for report generation."""
        fields_matched = []

        for index, branch_data in enumerate(suggested_other):
            suggested_list = []
            other_list = []

            # Process suggested fields
            sorted_suggested = sorted(branch_data[0], key=lambda x: x['Personality'], reverse=True)
            top_field_tags = STATE_INFO[index][0]

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
            but_field_tags = STATE_INFO[index][1]

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

            fields_matched.append((suggested_list, other_list))

        return fields_matched

    def _compute_scl_scores(self, user_id: str) -> tuple[Dict, List[int]]:
        """Compute SCL labels for a user based on quiz question answer rows."""
        try:
            user_answers: Dict[str, Any] = answer_store.get_answers_for_user_kind(
                self.db_conn,
                self.db_cursor,
                int(user_id),
                "SCL",
            )

            labels, missing_questions = score_computation_scl(user_answers)
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

    def _handle_scl_report(self, user_id: str) -> None:
        """Handle SCL kind: compute labels and store result in redis_logs."""
        try:
            start_time = time.time()
            report_kind = "SCL"

            # Validate quiz data
            self._validate_quiz_data(user_id, report_kind)

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

            db_helper.update_record(
                self.db_conn,
                self.db_cursor,
                "redis_logs",
                ["result", "status", "edited_time"],
                [
                    "SCL computation started in scheduler",
                    1,
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                ],
                "user_id = ? AND kind = ?",
                [str(user_id), "SCL"],
            )

            labels, missing_questions = self._compute_scl_scores(user_id)
            scl_calc_data = self._calculate_scl_calc_data(labels)

            # Generate Report 3
            # Mapping from CALC_DATA keys to advice keys for get_report_text
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
            }
            gray_color = "CCCCCC"  # Gray color for values under 2.0
            colors_tag = []
            colors_color = []

            def calculate_color_from_value(value: float) -> str:
                """
                Map value to 4 discrete darker pastel colors:
                0–1  -> darker pastel green
                1–2  -> darker pastel yellow
                2–3  -> darker pastel orange
                3+   -> darker pastel red
                """
                # Clamp to non‑negative
                if value < 0:
                    value = 0.0

                if value < 1.0:
                    # Darker pastel green (#33CC33)
                    return "33CC33"
                if value < 2.0:
                    # Darker pastel yellow (#FFFF66)
                    return "FFFF66"
                if value < 3.0:
                    # Darker pastel orange (#FF9900)
                    return "FF9900"

                # 3 and above -> darker pastel red (#FF0000)
                return "FF0000"

            for color_tag_key in COLOR_TAGS.keys():
                calc_data_key = color_tag_key.replace("_so", "")
                if calc_data_key in scl_calc_data:
                    value = scl_calc_data[calc_data_key]
                    color_tag_info = COLOR_TAGS[color_tag_key]

                    if value < 2.0:
                        tag_tri = color_tag_info["tag_triangle"]
                        color_tri = gray_color
                        colors_tag.append(tag_tri)
                        colors_color.append(color_tri)
                    tag_cir = color_tag_info["tag_circle"]
                    color_cir = calculate_color_from_value(value)
                    colors_tag.append(tag_cir)
                    colors_color.append(color_cir)

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

            def round_to_quarter(value: float) -> float:
                """Round value to nearest quarter (x.0, x.25, x.5, x.75)."""
                return round(value * 4) / 4

            # Define tags and labels for 3 categories
            # Note: These tags are in diagram XML files (data2.xml, data4.xml, data6.xml), not document.xml
            # The generate_third_report_documents function handles replacement in both document.xml and diagram files
            skill_tag = ["vav", "vaav", "vaaav", "vaaaav", "vaaaaav", "vaaaaaav"]
            skill_label = ["body_problem", "game_addiction", "wage_future", "drug_addicion", "sleep_problem",
                           "study_problem"]

            psycho_tag = ["waw", "waaw", "waaaw", "waaaaw", "waaaaaw"]
            psycho_label = ["ocd", "depression", "motivation", "self_confident", "anxiety"]

            real_tag = ["zaz", "zaaz", "zaaaz", "zaaaaz", "zaaaaaz"]
            real_label = ["family_problem", "truma", "adhd", "interpersonal", "ideal"]

            report_text_replacements = {}
            needed = []
            unneeded = []
            for key in CALC_DATA.keys():
                if key not in scl_calc_data:
                    continue

                prefix = calc_key_to_prefix.get(key)
                if not prefix:
                    continue  # Skip if no prefix mapping found

                value = scl_calc_data[key]

                # Generate 4 tags for each key
                report_text_replacements[f"{prefix}statefast"] = get_statefast_value(value)
                report_text_replacements[f"{prefix}interfast"] = get_interfast_value(value)

                # Score: value * 2.5 rounded to quarters
                score_value = round_to_quarter(value * 2.5)
                report_text_replacements[f"{prefix}scorefast"] = str(score_value)

                # Fast: get text from get_report_text
                fast_label = f"{prefix}fast"
                report_text_replacements[f"{prefix}fast"] = get_report_text(fast_label, value)

                # Add advice text for each key

                advice_key = calc_key_to_advice.get(key)
                if advice_key:
                    labels = [
                        f"{advice_key}1",
                        f"{advice_key}2",
                        f"{advice_key}3",
                        f"{advice_key}4",
                    ]

                    if 0 <= value < 1:
                        keep_index = 0
                    elif 1 <= value < 2:
                        keep_index = 1
                    elif 2 <= value < 3:
                        keep_index = 2
                    else:
                        keep_index = 3

                    for i, label in enumerate(labels):
                        if i == keep_index:
                            needed.append(label)
                        else:
                            unneeded.append(label)

            # Sort labels by scl_calc_data values (ascending) and map to tags
            # For each category, filter labels that exist in scl_calc_data, sort by value, and map to tags
            def process_category(labels, tags):
                """Filter labels that exist in scl_calc_data, sort by value ascending, and map to tags."""
                # Filter labels that exist in scl_calc_data
                available_labels = [(label, scl_calc_data[label]) for label in labels if label in scl_calc_data]
                # Sort by value in ascending order
                available_labels.sort(key=lambda x: x[1], reverse=True)
                # Map sorted labels to tags (up to the number of available tags)
                for i, (label, value) in enumerate(available_labels):
                    if i < len(tags):
                        tag = tags[i]
                        # Get the name from CALC_DATA
                        calc_data_name = CALC_DATA.get(label, {}).get("name", "")
                        report_text_replacements[tag] = calc_data_name

            # Process each category
            process_category(skill_label, skill_tag)
            process_category(psycho_label, psycho_tag)
            process_category(real_label, real_tag)

            # Merge text replacements into user_info
            user_info.update(report_text_replacements)

            # Calculate image replacements based on scl_calc_data values
            image_replacements = []  # List of (old_image, new_image_path) tuples
            for key, value in scl_calc_data.items():
                if key not in SCL_PIC_DICT:
                    continue

                # Special handling for OCD: use ocd1, ocd2, ocd3, ocd4 from labels
                if key == "ocd" and "OCD" in labels and isinstance(labels["OCD"], dict):
                    ocd_data = labels["OCD"]
                    ocd1_val = ocd_data.get("ocd1", 0) / bookmark_scl_object["ocd1"]["count"]
                    ocd2_val = ocd_data.get("ocd2", 0) / bookmark_scl_object["ocd2"]["count"]
                    ocd3_val = ocd_data.get("ocd3", 0) / bookmark_scl_object["ocd3"]["count"]
                    ocd4_val = ocd_data.get("ocd4", 0) / bookmark_scl_object["ocd4"]["count"]

                    # Map max ocd to image index:
                    # ocd2 is max -> index 3, ocd1 is max -> index 0, 
                    # ocd3 is max -> index 1, ocd4 is max -> index 2
                    if ocd2_val > 2:
                        image_index = 3
                        old_image_name, new_image_name = SCL_PIC_DICT[key][image_index]
                        new_image_path = Path(PICS_WORD_SCL_DIR) / new_image_name
                        if new_image_path.exists():
                            image_replacements.append((old_image_name, new_image_path))
                        else:
                            logging.warning(f"Image replacement file not found: {new_image_path}")
                    elif ocd1_val > 2:
                        image_index = 0
                        old_image_name, new_image_name = SCL_PIC_DICT[key][image_index]
                        new_image_path = Path(PICS_WORD_SCL_DIR) / new_image_name
                        if new_image_path.exists():
                            image_replacements.append((old_image_name, new_image_path))
                        else:
                            logging.warning(f"Image replacement file not found: {new_image_path}")
                    elif ocd3_val > 2:
                        image_index = 1
                        old_image_name, new_image_name = SCL_PIC_DICT[key][image_index]
                        new_image_path = Path(PICS_WORD_SCL_DIR) / new_image_name
                        if new_image_path.exists():
                            image_replacements.append((old_image_name, new_image_path))
                        else:
                            logging.warning(f"Image replacement file not found: {new_image_path}")
                    elif ocd4_val > 2:
                        image_index = 2
                        old_image_name, new_image_name = SCL_PIC_DICT[key][image_index]
                        new_image_path = Path(PICS_WORD_SCL_DIR) / new_image_name
                        if new_image_path.exists():
                            image_replacements.append((old_image_name, new_image_path))
                        else:
                            logging.warning(f"Image replacement file not found: {new_image_path}")
                    else:
                        # Fallback to default if no match (shouldn't happen)
                        image_index = 3
                        old_image_name, new_image_name = SCL_PIC_DICT[key][image_index]
                        new_image_path = Path(PICS_WORD_SCL_DIR) / new_image_name
                        if new_image_path.exists():
                            image_replacements.append((old_image_name, new_image_path))
                        else:
                            logging.warning(f"Image replacement file not found: {new_image_path}")
                else:
                    # Select image index based on value range:
                    # 3-4: index 0, 2-3: index 1, 1-2: index 2, 0-1: index 3
                    if value >= 3:
                        image_index = 0
                    elif value >= 2:
                        image_index = 1
                    elif value >= 1:
                        image_index = 2
                    else:
                        image_index = 3

                    if key != "ideal":
                        # Get the image tuple (old_image_name, new_image_name)
                        old_image_name, new_image_name = SCL_PIC_DICT[key][image_index]
                        new_image_path = Path(PICS_WORD_SCL_DIR) / new_image_name

                        # Only add if the replacement image exists
                        if new_image_path.exists():
                            image_replacements.append((old_image_name, new_image_path))
                        else:
                            logging.warning(f"Image replacement file not found: {new_image_path}")

            with open(os.path.join(user_directory, f"labels.json"), "w", encoding="utf-8") as f:
                json.dump(labels, f, ensure_ascii=False, indent=2)
            with open(os.path.join(user_directory, f"user_info.json"), "w", encoding="utf-8") as f:
                json.dump(user_info, f, ensure_ascii=False, indent=2)
            with open(os.path.join(user_directory, f"report_text_replacements.json"), "w",
                      encoding="utf-8") as f:
                json.dump(report_text_replacements, f, ensure_ascii=False, indent=2)
            with open(os.path.join(user_directory, f"scl_calc_data.json"), "w", encoding="utf-8") as f:
                json.dump(scl_calc_data, f, ensure_ascii=False, indent=2)
            if logo_path:
                image_replacements.append(("image4.png", logo_path))
            generate_third_report_documents(
                user_directory=user_directory,
                user_report_info=user_info,
                colors_tag=colors_tag,
                colors_color=colors_color,
                report_text_replacements=report_text_replacements,
                image_replacements=image_replacements,
                needed=needed,
                unneeded=unneeded,
                phone=phone
            )
            logging.info(
                f"Generated Report3.pdf for user {user_id}"
            )

            # Determine report type based on max value of anxiety, ocd, depression
            report_keys = ["anxiety", "ocd", "depression"]
            report_values = {key: scl_calc_data.get(key, 0.0) for key in report_keys}
            max_report_key = max(report_values, key=report_values.get)
            max_report_value = report_values[max_report_key]

            # Generate report 4 if any of the three conditions have a value > 0
            if max_report_value > 0:
                # Logo replacement: anxiety and depression use image14.png, OCD uses image17.png
                report4_image_replacements = []
                if logo_path:
                    if max_report_key == "depression":
                        report4_image_replacements.append(("image12.png", logo_path))
                    elif max_report_key == "anxiety":
                        report4_image_replacements.append(("image14.png", logo_path))
                    elif max_report_key == "ocd":
                        report4_image_replacements.append(("image17.png", logo_path))
                generate_forth_report_documents(
                    user_directory=user_directory,
                    user_report_info=user_info,  # Pass as dict with USER_TAGS_INFO keys
                    report_name=max_report_key,  # "anxiety", "ocd", or "depression"
                    phone=phone,
                    image_replacements=report4_image_replacements
                )
                logging.info(
                    f"Generated Report4.pdf for user {user_id} with report type: {max_report_key} (value: {max_report_value:.2f})"
                )

            # Generate text replacements for all CALC_DATA keys
            report_text_replacements = {}
            needed = []
            unneeded = []
            for key in CALC_DATA.keys():
                if key not in scl_calc_data:
                    continue

                prefix = calc_key_to_prefix.get(key)
                if not prefix:
                    continue  # Skip if no prefix mapping found

                value = scl_calc_data[key]

                # Generate 4 tags for each key
                report_text_replacements[f"{prefix}statefast"] = get_statefast_value(value)
                report_text_replacements[f"{prefix}interfast"] = get_interfast_value(value)

                # Score: value * 2.5 rounded to quarters
                score_value = round_to_quarter(value * 2.5)
                report_text_replacements[f"{prefix}scorefast"] = str(score_value)

                # Fast: get text from get_report_text
                fast_label = f"{prefix}fast"
                labels = [
                    f"{fast_label}1",
                    f"{fast_label}2",
                    f"{fast_label}3",
                    f"{fast_label}4",
                ]

                if 0 <= value < 1:
                    keep_index = 0
                elif 1 <= value < 2:
                    keep_index = 1
                elif 2 <= value < 3:
                    keep_index = 2
                else:
                    keep_index = 3

                for i, label in enumerate(labels):
                    if i == keep_index:
                        needed.append(label)
                    else:
                        unneeded.append(label)
                # report_text_replacements[f"{prefix}fast"] = get_report_text(fast_label, value)

            # Merge text replacements into user_info
            user_info.update(report_text_replacements)

            # Prepare data for bar chart: categories (Persian names) and values
            categories = []
            values = []
            colors = []
            # Scale values from 0-3 range to 0-100 range and round to 2 decimal places
            # Mapping: 0 -> 0.00, 1 -> 33.33, 2 -> 66.66, 3 -> 100.00
            # Formula: value / 3 * 100
            for key in CALC_DATA.keys():
                if key in scl_calc_data:
                    categories.append(CALC_DATA[key]["chart_name"])
                    # Scale from 0-3 to 0-100: value / 3 * 100
                    scaled_value = round(scl_calc_data[key] / 4 * 100, 2)
                    values.append(scaled_value)
                    # colors.append(CALC_DATA.get(key, "#95A5A6"))  # Default gray if color not found
                    colors.append(CALC_DATA[key]["color"])
            # Create bar chart
            if categories and values:
                bar_chart_path = bar.create_bar_chart(
                    categories=categories,
                    title="ﯽﺘﺧﺎﻨﺸﻧﺍﻭﺭ ﻞﻣﺍﻮﻋ ﯼﻪﺴﯾﺎﻘﻣ ﺭﺍﺩﻮﻤﻧ",
                    values=values,
                    colors=colors,
                    rotation=45,
                    size=8,
                    path=user_directory,
                    filename="image1"
                )
                # Logo replacement for report 5: replace image18.png with logo if available
                report5_image_replacements = []
                if logo_path:
                    report5_image_replacements.append(("image21.png", logo_path))
                # Generate Report 5
                generate_fifth_report_documents(
                    user_directory=user_directory,
                    user_report_info=user_info,
                    image_names=["image4.png"],
                    user_report_pictures=[f"{bar_chart_path}.png"],
                    phone=phone,
                    image_replacements=report5_image_replacements,
                    needed=needed,
                    unneeded=unneeded
                )
                logging.info(
                    f"Generated Report5.pdf for user {user_id} with bar chart"
                )

            # Update or insert scl_scores record
            self._update_scl_scores(user_id, phone, scl_calc_data)

            db_helper.update_record(
                self.db_conn,
                self.db_cursor,
                "redis_logs",
                ["result", "status", "edited_time"],
                [
                    "user info checked in scheduler",
                    2,
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                ],
                "user_id = ? AND kind = ?",
                [str(user_id), "SCL"],
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

    def _handle_ag_report(self, user_id: str) -> None:
        """Main method to generate complete report for a user."""
        try:
            start_time = time.time()
            report_kind = "AG"

            # Validate quiz data
            self._validate_quiz_data(user_id, report_kind)

            # Get student information
            student, student_name, phone, institute_name, consultant_name, logo_path = self._get_student_info(user_id)

            # Create report directory
            user_directory = self._create_report_directory(phone)

            # Update log status for AG job
            db_helper.update_record(
                self.db_conn,
                self.db_cursor,
                "redis_logs",
                ["result", "status", "edited_time"],
                [
                    "user info check in scheduler",
                    1,
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                ],
                "user_id = ? AND kind = ?",
                [str(user_id), "AG"],
            )

            # Compute brain info
            master_file, master_sheet = load_master_excel()
            data, fields, categories, branches, correct, wrong, unanswered = compute_brain_info(
                self.db_conn, self.db_cursor, user_id,
                phone=phone,
                master_file=master_file,
                master_sheet=master_sheet
            )

            quiz_score_json = json.dumps(
                {"correct": correct, "wrong": wrong, "unanswered": unanswered},
                ensure_ascii=False,
            )
            brain_fields_json = json.dumps(fields, ensure_ascii=False)
            brain_categories_json = json.dumps(categories, ensure_ascii=False)
            brain_branches_json = json.dumps(branches, ensure_ascii=False)

            # Persist scores once per user_id (avoid duplicates)
            query = "SELECT user_id FROM scores WHERE user_id = ?"
            exists = db_helper.search_table(self.db_conn, self.db_cursor, query, user_id)

            if exists is None:
                db_helper.insert_value(
                    self.db_conn, self.db_cursor,
                    "scores",
                    "([user_id], [phone], [quiz_score], [brain_fields], [brain_categories], [brain_branches])",
                    (
                        user_id,
                        phone,
                        quiz_score_json,
                        brain_fields_json,
                        brain_categories_json,
                        brain_branches_json,
                    ),
                )
            else:
                db_helper.update_record(
                    self.db_conn, self.db_cursor,
                    "scores",
                    ["phone", "quiz_score", "brain_fields", "brain_categories", "brain_branches", "edited_time"],
                    [
                        phone,
                        quiz_score_json,
                        brain_fields_json,
                        brain_categories_json,
                        brain_branches_json,
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    ],
                    "user_id = ?",
                    [str(user_id)],
                )

            # Persist raw fields to JSON for debugging/inspection
            try:
                with open(os.path.join(user_directory, f"fields_{phone}.json"), "w", encoding="utf-8") as f:
                    json.dump(fields, f, ensure_ascii=False, indent=2)
            except Exception as exc:
                logging.warning("Could not save fields debug file: %s", exc)

            # Process and update hedayat_fields
            suggested_names, other_names = self._process_hedayat_fields(fields)
            self._update_hedayat_fields(user_id, phone, suggested_names, other_names)

            # Add student info to data
            data["student_name"] = student_name
            data["user_id"] = int(user_id)
            data["phone"] = phone
            data["correct"] = correct
            data["wrong"] = wrong
            data["unanswered"] = unanswered

            # Generate first report
            first_report_images = FIRST_REPORT_IMAGES.copy()
            first_report_pictures, first_report_info, effect, color_handle_tag, color_handle_color = \
                self._generate_first_report_charts(data, user_directory, institute_name, consultant_name)

            if logo_path:
                first_report_images.append('image53.jpeg')
                first_report_pictures.append(logo_path)

            generate_first_report_documents(
                list(first_report_info.keys()),
                list(first_report_info.values()),
                first_report_images,
                first_report_pictures,
                user_directory,
                effect,
                color_handle_tag,
                color_handle_color,
                phone
            )

            # Generate second report
            suggested_other = self._get_sorted_suggested_fields(fields)
            second_report_images = SECOND_REPORT_IMAGES.copy()
            second_report_pictures, second_report_info, fields_matched, colors_tag, colors_color = \
                self._generate_second_report_charts(data, categories, branches, suggested_other, user_directory,
                                                    institute_name, consultant_name, user_id, phone)

            if logo_path:
                second_report_images.append('image74.jpeg')
                second_report_pictures.append(logo_path)

            # Persist matched fields and benchmark names for debugging/traceability
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
            db_helper.update_record(
                self.db_conn,
                self.db_cursor,
                "redis_logs",
                ["result", "status", "edited_time"],
                [
                    "user info checked in scheduler",
                    2,
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                ],
                "user_id = ? AND kind = ?",
                [str(user_id), "AG"],
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

                    if kind == "AG":
                        self._handle_ag_report(user_id)
                    elif kind == "SCL":
                        self._handle_scl_report(user_id)
                    else:
                        logging.warning(
                            "Unknown kind '%s' for user %s, skipping job.", kind, user_id
                        )

                    time.sleep(10)

                except Exception as e:
                    logging.exception(f"Error processing user {user_id}: {str(e)}")
                    continue

        except KeyboardInterrupt:
            logging.info("AG Report scheduler stopped by user")
        except Exception as e:
            logging.error(f"AG Report scheduler crashed: {str(e)}")
            raise
        finally:
            self.db_conn.close()
            logging.info("Database connection closed")


if __name__ == "__main__":
    try:
        scheduler = AGReportScheduler()
        scheduler.run()
    except Exception as e:
        logging.critical(f"Fatal error in AG report scheduler: {str(e)}")
        raise
