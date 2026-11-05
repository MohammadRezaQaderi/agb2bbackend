from helper.quiz.ag_quiz_data_info import ag_quiz_info as ag_quiz_full_info
from helper.quiz.scl_quiz_data_info import scl_quiz_info as scl_quiz_full_info
from helper.quiz_engine import StaticQuizPackageProvider, quiz_package_registry

# AG Pack Quiz Table Info (metadata used for quiz list / table)
ag_quiz_table_info = [
    {
        'id': 1,
        'quizName': "کتل",
        "voice": '1.m4a',
        "description": 'دستـور الــعمل آزمــون\nکاربر گرامی؛\nآزمون پیش رو از چهار بخش مجزا تشکیل شده که لازم است هر کدام از آنها در زمان هایی که گفته شده، انجام شود. سوالات این آزمون از آسان به دشوار تنظیم شده، در آخر هر بخش تعدادی سوال بسیار دشوار وجود دارد، به طوری که کمتر کسی می تواند در مدت تعیین شده به آنها پاسخ بدهد. با این حال تا آنجا که می توانید تلاش کنید و به تعداد بیشتری از سوالات پاسخ دهید.\nتوجه داشته باشید که برای پاسخ های غلط، نمره منفی در نظر گرفته نشده است. بنابراین بهتر است به همه سوالات پاسخ دهید.\nبه منظور فهم بهتر دستورالعمل آزمون، در ابتدای هر بخش سوال هایی به عنوان مثال مورد بررسی قرار می گیرد. لطفاً این مثال ها را با دقت بخوانید.',
        "pic": "default.png",
        "ImageURL": "1.jpg",
    },
    {
        'id': 2,
        'quizName': "گاردنر",
        "voice": '2.m4a',
        "description": 'دستـور الــعمل آزمــون\nپرسشنامه پیش رو به منظور بررسی هوش های چندگانه شما تهیه شده است، در این پرسشنامه سوال درست و غلط وجود ندارد و هر سوال به بررسی موضوعی درباره شما می پردازد. بنابراین به هر سوال آن گونه که هستید پاسخ دهید. به شما توصیه می گردد از پاسخ دادن به سوالات با گزینه "متوسط" اجتناب کنید و اگر موضوع مورد بحث برای شما حتما در حد متوسط بود از این گزینه استفاده کنید و در غیر این صورت تلاش کنید هر سوال را در طیف بیان شده درباره خود تحلیل و ارزیابی کرده و گزینه مناسب را انتخاب کنید.',
        "pic": "default.png",
        "ImageURL": "2.jpg",
    },
    {
        'id': 3,
        'quizName': "نئو",
        "voice": '3.m4a',
        "description": 'دستـور الــعمل آزمــون\nپرسشنامه پیش رو به منظور بررسی برخی از ابعاد شخصیت شما تهیه شده است، در این آزمون سوال درست و غلط وجود ندارد و هر سوال به بررسی موضوعی درباره شما می پردازد. پاسخ های شما به این سوالات به صورت کاملا محرمانه باقی می ماند و بنابراین به هر سوال آن گونه که هستید پاسخ دهید. به شما توصیه می گردد از پاسخ دادن به سوالات با گزینه "نه موافقم و نه مخالفم" اجتناب کنید و اگر موضوع مورد بحث برای شما حتما در حد متوسط بود از این گزینه استفاده کنید و در غیر این صورت تلاش کنید هر سوال را در طیف بیان شده درباره خود تحلیل و ارزیابی کرده و گزینه مناسب را انتخاب کنید.',
        "pic": "default.png",
        "ImageURL": "3.svg",
    },
    {
        'id': 4,
        'quizName': "کلیفتون",
        "voice": '4.m4a',
        "description": 'دستـور الــعمل آزمــون\nپرسشنامه پیش رو به منظور بررسی برخی از استعدادهای شما تهیه شده است، در این پرسشنامه سوال درست و غلط وجود ندارد و هر سوال به بررسی موضوعی درباره شما می پردازد.در این پرسشنامه در یک سر طیف یک جمله و در طرف مقابل جمله ای نسبتا مخالف و یا متفاوت با آن مطرح شده است. با بررسی هر دو جمله، گزینه ای که به بهترین شکل شما را توصیف می کند انتخاب کنید. پاسخ های شما به این سوالات به صورت کاملا محرمانه باقی می ماند و بنابراین به هر سوال آن گونه که هستید پاسخ دهید. به شما توصیه می گردد از پاسخ دادن به سوالات با گزینه "متوسط" اجتناب کنید و اگر موضوع مورد بحث برای شما حتما در حد متوسط بود از این گزینه استفاده کنید و در غیر این صورت تلاش کنید هر سوال را در طیف بیان شده درباره خود تحلیل و ارزیابی کرده و گزینه مناسب را انتخاب کنید.',
        "pic": "default.png",
        "ImageURL": "4.jpg",
    },
    {
        'id': 5,
        'quizName': "هالند",
        "voice": '5.m4a',
        "description": 'دستـور الــعمل آزمــون\nپرسشنامه پیش رو به منظور بررسی برخی از استعدادهای شما تهیه شده است، در این پرسشنامه سوال درست و غلط وجود ندارد و هر سوال به بررسی موضوعی درباره شما می پردازد. این پرسشنامه از 5 بخش تشکیل شده است که در ابتدای هر بخش دستورالعمل  آن قسمت توضیح داده شده است. با توجه به دستورالعمل بیان شده پاسخ های مناسب برای هر بخش را تعیین کنید.',
        "pic": "default.png",
        "ImageURL": "5.jpg",
    },
    {
        'id': 6,
        'quizName': "تعهد",
        "voice": '6.m4a',
        "description": 'دستـور الــعمل آزمــون\nپرسشنامه پیش رو به منظور بررسی نظرات شما پیرامون تحصیل و درس تهیه شده است، در این پرسشنامه سوال درست و غلط وجود ندارد و هر سوال به بررسی بخشی از این موضوعی درباره شما می پردازد. این پرسشنامه از 2 بخش تشکیل شده است که در ابتدای هر بخش دستورالعمل  آن قسمت توضیح داده شده است. پاسخ های شما در این پرسشنامه نیز به صورت کاملا محرمانه باقی می ماند بنابراین گزینه را انتخاب کنید که به بهترین شکل شما را توصیف می کند.',
        "pic": "default.png",
        "ImageURL": "6.jpg",
    },
    {
        'id': 7,
        'quizName': "پرسشنامه",
        "voice": '7.m4a',
        "description": 'دستـور الــعمل آزمــون\nپرسشنامه پیش رو به منظور بررسی انگیزه شما پیرامون تحصیل و درس تهیه شده است، در این پرسشنامه سوال درست و غلط وجود ندارد و هر سوال به بررسی بخشی از این موضوعی درباره شما می پردازد. پاسخ های شما در این پرسشنامه نیز به صورت کاملا محرمانه باقی می ماند بنابراین گزینه را انتخاب کنید که به بهترین شکل شما را توصیف می کند.',
        "pic": "default.png",
        "ImageURL": "7.jpg",
    }
]

# SCL Pack Quiz Table Info (metadata used for quiz list / table)
scl_quiz_table_info = [
    {
        'id': 1,
        'quizName': "زندگی شخصی",
        "voice": 'nan',
        "description": 'در این قسمت با چند آزمون مواجه هستید که درباره زندگی شخصی، ویژگی ها و تجاربی که در طول زندگی خود داشته اید از شما سوالاتی پرسیده خواهد شد. به این سوالات صادقانه پاسخ دهید و مطمئن باشید نتایج شما به صورت محرمانه باقی خواهند ماند. این سوالات چواب درست یا غلط ندارند بلکه درباره تجارب شما هستند بنابراین با خیالت راحت به این سوالات پاسخ دهید.',
        "pic": "default.png",
        "ImageURL": "1.jpg",
    },
    {
        'id': 2,
        'quizName': "زندگی روانشناختی",
        "voice": 'nan',
        "description": 'در این قسمت با چند آزمون مواجه هستید که درباره وضعیت روانشناختی، اختلالات احتمالی و یا مسائلی که ممکن است ذهن شما به خود درگیر کرده است از شما سوالاتی پرسیده خواهد شد. به این سوالات صادقانه پاسخ دهید و مطمئن باشید نتایج شما به صورت محرمانه باقی خواهند ماند. این سوالات چواب درست یا غلط ندارند بلکه درباره تجارب شما هستند بنابراین با خیالت راحت به این سوالات پاسخ دهید.',
        "pic": "default.png",
        "ImageURL": "2.jpg",
    },
    {
        'id': 3,
        'quizName': "زندگی تحصیلی",
        "voice": 'nan',
        "description": 'در این قسمت با چند آزمون مواجه هستید که درباره وضعیت تحصیلی و زندگی شما در مدرسه از شما سوالاتی پرسیده خواهد شد. به این سوالات صادقانه پاسخ دهید و مطمئن باشید نتایج شما به صورت محرمانه باقی خواهند ماند. این سوالات چواب درست یا غلط ندارند بلکه درباره تجارب شما هستند بنابراین با خیالت راحت به این سوالات پاسخ دهید.',
        "pic": "default.png",
        "ImageURL": "3.svg",
    },
    {
        'id': 4,
        'quizName': "زندگی اجتماعی",
        "voice": 'nan',
        "description": 'در این قسمت با چند آزمون مواجه هستید که درباره وضعیت روابط بین فردی و زندگی اجتماعی خود چه در خانواده و چه در اجتماع از شما سوالاتی پرسیده خواهد شد. به این سوالات صادقانه پاسخ دهید و مطمئن باشید نتایج شما به صورت محرمانه باقی خواهند ماند. این سوالات چواب درست یا غلط ندارند بلکه درباره تجارب شما هستند بنابراین با خیالت راحت به این سوالات پاسخ دهید.',
        "pic": "default.png",
        "ImageURL": "4.jpg",
    }
]


def get_ag_quiz_table_info():
    return ag_quiz_table_info


def get_scl_quiz_table_info():
    return scl_quiz_table_info


# Backward compatibility - keep old variable and function names pointing to AG pack
# quiz_info = ag_quiz_info
quiz_table_info = ag_quiz_table_info


def _register_static_packages():
    static_packages = (
        ("AG", ag_quiz_full_info, ag_quiz_table_info),
        ("SCL", scl_quiz_full_info, scl_quiz_table_info),
    )
    for package_name, quizzes, summaries in static_packages:
        if quiz_package_registry.get_optional(package_name) is None:
            quiz_package_registry.register(
                StaticQuizPackageProvider(
                    package_name=package_name,
                    definition_version="legacy-v1",
                    quizzes=quizzes,
                    quiz_summaries=summaries,
                )
            )


_register_static_packages()


def get_quiz_info(quiz_id, kind="AG"):
    """
    Return full quiz data (including sections and questions) for the given quiz_id and kind.
    Data is loaded from:
      - AG:  quiz.ag_quiz_data_info.ag_quiz_info
      - SCL: quiz.scl_quiz_data_info.quiz_data_info
    """
    provider = quiz_package_registry.get_optional(kind)
    return provider.get_quiz(quiz_id) if provider else None


def get_quiz_table_info(kind="AG"):
    provider = quiz_package_registry.get_optional(kind)
    if provider:
        return provider.list_quiz_summaries()
    # Preserve the legacy fallback until all callers validate package names.
    return quiz_package_registry.get("AG").list_quiz_summaries()


def get_quiz_name(quiz_id, kind="AG"):
    provider = quiz_package_registry.get_optional(kind)
    return provider.get_quiz_name(quiz_id) if provider else None


def get_last_question_id(kind="AG"):
    provider = quiz_package_registry.get_optional(kind)
    return provider.get_last_question_id() if provider else None


def get_definition_version(kind="AG"):
    provider = quiz_package_registry.get_optional(kind)
    return provider.definition_version if provider else None
