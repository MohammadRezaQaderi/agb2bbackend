import time
from typing import List
import json
import os
import logging

import xlwings as XL

from helper.quiz.check_score import ag_score_computation


def CreateObject(objects):
    i = 0
    date = []
    for obj in objects:
        i += 1
        attrs = vars(obj)
        date.append(attrs)
    return date


"""فایل اکسل منبع برای انجام محاسبات"""


class CalculatorInput:
    """پارامترهای ورودی محاسبه نتیجه آزمون"""
    SES: float
    Visual_spatial: float
    Linguistic_verbal: float
    Logical_mathematical: float
    Body_kinesthetic: float
    Intrapersonal: float
    Interpersonal: float
    Naturalistic: float
    Musical: float
    Imigration: float
    Money: float
    Social_place: float
    Place: float
    Job: float
    Field: float
    Speed: float
    Analytical: float
    Futuristic: float
    Ideation: float
    Input: float
    Strategic: float
    Connectedness: float
    Empathy: float
    Individualization: float
    Activator: float
    Command: float
    Competition: float
    Self_assurance: float
    Arranger: float
    Consistency: float
    Focus: float
    Adaptability: float
    Harmony: float
    Neuroticism: float
    Extraversion: float
    Conscientiousness: float
    Openness: float
    Agreeableness: float
    Artistic: float
    Enterprising: float
    Conventional: float
    Social: float
    Investigative: float
    Realistic: float
    IQ_Number: float

    def __init__(self):
        pass

    def __init__(self, d=None):
        if d is not None:
            for key, value in d.items():
                setattr(self, key, value)


class FieldProperties:
    """مشخصات رشته تحصیلی"""
    Branch: str
    BranchId: int
    Field: str
    Women: int
    Man: int
    Theme: str
    ThemeId: int
    Ratio: int
    Capabilities: float
    Personality: float
    C1: float | None
    C2: float | None
    IQStars: str
    PersonalityStars: str
    Color: int
    Scatter: str

    def __init__(self):
        pass


class BranchProperties:
    """مشخصات شاخه تحصیلی"""
    Branch: str
    Value: float

    def __init__(self):
        pass


class CategoryProperties:
    """مشخصات تم رشته"""
    Category: str
    Value: float

    def __init__(self):
        pass


class CalculatorOutput:
    """خروجی محاسبه نتیجه آزمون"""
    Fields: List[FieldProperties]
    Branches: List[BranchProperties]
    Categories: List[CategoryProperties]

    def __init__(self):
        pass


def Calculate(master_sheet2, CI: CalculatorInput) -> CalculatorOutput:
    """بر اساس پارامترهای ورودی، نتیجه آزمون را محاسبه کرده و خروجی آن را برمی‌گرداند.
        ورودی:
            SourceFilename: نام فایل اکسل پایه حاوی داده‌ها و فرمول‌های محاسباتی
            TI: پارامترهای ورودی برای محاسبه نتیجه آزمون
        خروجی:
            نتیجه آزمون
    """
    # جایگذاری پارامترهای آزمون به عنوان ورودی
    WriteInput(master_sheet2, CI)
    rows = master_sheet2.range('B' + str(master_sheet2.cells.last_cell.row)).end('up').row
    CO = CalculatorOutput()
    CO.Fields = []
    CO.Branches = []
    CO.Categories = []

    # دریافت مشخصات رشته‌های تحصیلی
    for row in range(5, rows + 1):
        r = master_sheet2.range((row, 2), (row, 91))
        values = [r.raw_value[0][x] for x in [0, 1, 2, 3, 4, 5, 6, 7, 79, 80, 81, 82, 85, 86, 87, 88, 89]]
        F = FieldProperties()
        F.Branch = values[0]
        F.BranchId = int(values[1])
        F.Field = values[2]
        F.Women = values[3]
        F.Man = values[4]
        F.Theme = values[5]
        F.ThemeId = values[6]
        F.Ratio = int(values[7])
        F.Capabilities = values[8]
        F.Personality = values[9]
        if values[10] == '':
            F.C1 = None
        else:
            F.C1 = values[10]
        if values[11] == '':
            F.C2 = None
        else:
            F.C2 = values[11]
        F.IQStars = values[12]
        F.PersonalityStars = values[13]
        F.Color = values[14]
        F.Scatter = values[15]
        CO.Fields.append(F)
    # دریافت مشخصات شاخه‌های تحصیلی
    for row in range(1, 8):
        r = master_sheet2.range((row, 91), (row, 92))
        values = [r.raw_value[0][x] for x in [0, 1]]
        B = BranchProperties()
        B.Branch = values[0]
        B.Value = values[1]
        CO.Branches.append(B)

    # دریافت مشخصات تم رشته‌ها
    for row in range(10, 28):
        r = master_sheet2.range((row, 91), (row, 92))
        values = [r.raw_value[0][x] for x in [0, 1]]
        C = CategoryProperties()
        C.Category = values[0]
        C.Value = values[1]
        CO.Categories.append(C)

    return CO


def LoadExcelSourceFile(Filename: str) -> XL.Book:
    excel = XL.App(visible=False)
    excel.display_alerts = False
    excel.screen_updating = False
    excel_book = excel.books.open(Filename)
    return excel_book


def CloseExcelSourceFile(excel_book: XL.Book) -> None:
    """Close a workbook and its hidden Excel app without saving template changes."""
    app = getattr(excel_book, "app", None)
    excel_book.close()
    if app is not None:
        app.quit()


def ReadInput(master_sheet2, SheetName: str) -> CalculatorInput:
    # دریافت پارامترهای ورودی
    r = master_sheet2.range((2, 13), (2, 90))
    # سلول‌های اکسل حاوی پارامترهای ورودی
    values = [r.raw_value[0][x] for x in
              [0, 2, 4, 6, 8, 10, 12, 14, 15, 17, 18, 19, 20, 21, 22, 23, 24, 26, 27, 28, 30, 32, 34, 35, 37, 38, 39,
               41, 42, 44, 45, 47, 49,
               51, 52, 53, 54, 56, 58, 60, 62, 64, 66]]
    ci: CalculatorInput = CalculatorInput()
    ci.SES = values[0]
    ci.Visual_spatial = values[1]
    ci.Linguistic_verbal = values[2]
    ci.Logical_mathematical = values[3]
    ci.Body_kinesthetic = values[4]
    ci.Intrapersonal = values[5]
    ci.Interpersonal = values[6]
    ci.Naturalistic = values[7]
    ci.Musical = values[8]
    ci.Imigration = values[9]
    ci.Money = values[10]
    ci.Social_place = values[11]
    ci.Job = values[12]
    ci.Field = values[13]
    ci.Speed = values[14]
    ci.Analytical = values[15]
    ci.Futuristic = values[16]
    ci.Ideation = values[17]
    ci.Input = values[18]
    ci.Strategic = values[19]
    ci.Connectedness = values[20]
    ci.Empathy = values[21]
    ci.Individualization = values[22]
    ci.Activator = values[23]
    ci.Command = values[24]
    ci.Competition = values[25]
    ci.Self_assurance = values[26]
    ci.Arranger = values[27]
    ci.Consistency = values[28]
    ci.Focus = values[29]
    ci.Adaptability = values[30]
    ci.Harmony = values[31]
    ci.Neuroticism = values[32]
    ci.Extraversion = values[33]
    ci.Conscientiousness = values[34]
    ci.Openness = values[35]
    ci.Agreeableness = values[36]
    ci.Artistic = values[37]
    ci.Enterprising = values[38]
    ci.Conventional = values[39]
    ci.Social = values[40]
    ci.Investigative = values[41]
    ci.Realistic = values[42]
    return ci


def WriteInput(master_sheet2, CI: CalculatorInput):
    """در یک شیت از ورک بوک اکسل، مقادیر پارامترهای ورودی مربوط به آزمون را جایگذاری می‌نماید.
        ورودی:
            WB: ورک بوک اکسل
            TI: پارامترهای ورودی
        خروجی:
            در صورت صحت، مقدار درست و در غیر اینصورت نادرست را برمی‌گرداند.
    """
    # جایگذاری مقادیر در سلول‌های اکسل حاوی پارامترهای ورودی
    master_sheet2.range('K2').value = CI.IQ_Number
    master_sheet2.range('M2').value = CI.SES
    master_sheet2.range('O2').value = CI.Visual_spatial
    master_sheet2.range('Q2').value = CI.Linguistic_verbal
    master_sheet2.range('S2').value = CI.Logical_mathematical
    master_sheet2.range('U2').value = CI.Body_kinesthetic
    master_sheet2.range('W2').value = CI.Intrapersonal
    master_sheet2.range('Y2').value = CI.Interpersonal
    master_sheet2.range('AA2').value = CI.Naturalistic
    master_sheet2.range('AB2').value = CI.Musical
    master_sheet2.range('AD2').value = CI.Imigration
    master_sheet2.range('AE2').value = CI.Money
    master_sheet2.range('AF2').value = CI.Social_place
    master_sheet2.range('AG2').value = CI.Job
    master_sheet2.range('AH2').value = CI.Field
    master_sheet2.range('AI2').value = CI.Speed
    master_sheet2.range('AJ2').value = CI.Analytical
    master_sheet2.range('AK2').value = CI.Futuristic
    master_sheet2.range('AM2').value = CI.Ideation
    master_sheet2.range('AN2').value = CI.Input
    master_sheet2.range('AO2').value = CI.Strategic
    master_sheet2.range('AQ2').value = CI.Connectedness
    master_sheet2.range('AS2').value = CI.Empathy
    master_sheet2.range('AU2').value = CI.Individualization
    master_sheet2.range('AV2').value = CI.Activator
    master_sheet2.range('AX2').value = CI.Command
    master_sheet2.range('AY2').value = CI.Competition
    master_sheet2.range('AZ2').value = CI.Self_assurance
    master_sheet2.range('BB2').value = CI.Arranger
    master_sheet2.range('BC2').value = CI.Consistency
    master_sheet2.range('BE2').value = CI.Focus
    master_sheet2.range('BF2').value = CI.Adaptability
    master_sheet2.range('BH2').value = CI.Harmony
    master_sheet2.range('BJ2').value = CI.Neuroticism
    master_sheet2.range('BL2').value = CI.Extraversion
    master_sheet2.range('BM2').value = CI.Conscientiousness
    master_sheet2.range('BN2').value = CI.Openness
    master_sheet2.range('BO2').value = CI.Agreeableness
    master_sheet2.range('BQ2').value = CI.Artistic
    master_sheet2.range('BS2').value = CI.Enterprising
    master_sheet2.range('BU2').value = CI.Conventional
    master_sheet2.range('BW2').value = CI.Social
    master_sheet2.range('BY2').value = CI.Investigative
    master_sheet2.range('CA2').value = CI.Realistic


def exit_handler(SourceExcelFile):
    """عملیات ضروری حین خروج از برنامه"""
    # بستن فایل اکسل منبع
    SourceExcelFile.close()


def compute_brain_info(user_id, phone, master_file, master_sheet):
    master_sheet.copy(after=master_sheet, name=f'brain{phone}')
    master_sheet2 = master_file.sheets[f'brain{phone}']
    start = time.time()
    data, c, w, n = ag_score_computation(user_id, user_age=14)
    # user_directory = os.path.dirname(os.path.abspath(__file__))
    # try:
    #     with open(os.path.join(user_directory, f"data_{phone}.json"), "w", encoding="utf-8") as f:
    #         json.dump(data, f, ensure_ascii=False, indent=2)
    # except Exception as exc:
    #     print(f"Could not save data debug file: {exc}")
    ci = CalculatorInput(data)
    to = Calculate(master_sheet2, ci)
    fields = CreateObject(to.Fields)
    categories = CreateObject(to.Categories)
    branches = CreateObject(to.Branches)
    master_sheet2.delete()
    end = time.time()
    print("time to execute the brain: ", end - start)
    return data, fields, categories, branches, c, w, n
