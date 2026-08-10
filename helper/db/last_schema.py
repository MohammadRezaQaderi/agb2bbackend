LAST_TABLE_DEFINITIONS = {
    "users": """
        CREATE TABLE users (
            user_id INT IDENTITY(1, 1) PRIMARY KEY,
            phone NVARCHAR(12),
            password nvarchar(50),
            role NVARCHAR(100) NULL,
            DC_Created_Time DATETIME,
            DC_Edited_Time DATETIME
        )
    """,
    "ins": """
        CREATE TABLE ins (
            ins_id INT IDENTITY(1, 1),
            user_id int,
            phone NVARCHAR(12),
            name NVARCHAR(100),
            logo VARCHAR(MAX),
            password nvarchar(50),
            DC_Created_Time DATETIME,
            DC_Edited_Time DATETIME
        )
    """,
    "sch": """
        CREATE TABLE sch (
            sch_id INT IDENTITY(1, 1),
            user_id int,
            phone NVARCHAR(12),
            name NVARCHAR(100),
            logo VARCHAR(MAX),
            password nvarchar(50),
            DC_Created_Time DATETIME,
            DC_Edited_Time DATETIME
        )
    """,
    "wCon": """
        CREATE TABLE wCon (
            wCon_id INT IDENTITY(1, 1),
            user_id int,
            phone NVARCHAR(12),
            first_name NVARCHAR(50),
            last_name NVARCHAR(50),
            password nvarchar(50),
            DC_Created_Time DATETIME,
            DC_Edited_Time DATETIME
        )
    """,
    "con": """
        CREATE TABLE con (
            con_id INT IDENTITY(1, 1),
            user_id int,
            phone NVARCHAR(12),
            first_name NVARCHAR(50),
            last_name NVARCHAR(50),
            national_id nvarchar(10)
            ins_id INT,
            editor_id INT,
            password nvarchar(50),
            ins_role NVARCHAR(15),
            DC_Created_Time DATETIME,
            DC_Edited_Time DATETIME
        )
    """,
    "stu": """
        CREATE TABLE stu (
            stu_id INT IDENTITY(1, 1),
            user_id int,
            phone NVARCHAR(12),
            first_name NVARCHAR(50),
            last_name NVARCHAR(50),
            sex INT,
            national_id nvarchar(10)
            city NVARCHAR(100),
            permission int,
            finalize int,
            password nvarchar(50),
            comment varchar(MAX),
            birth_date NVARCHAR(4),
            ins_role NVARCHAR(15),
            ins_id INT,
            con_id INT,
            adder_id INT,
            editor_id INT,
            DC_Created_Time DATETIME,
            DC_Edited_Time DATETIME
        )
    """,
    "setting": """
        CREATE TABLE setting (
            setting_id INT IDENTITY(1, 1) PRIMARY KEY,
            user_id INT,
            description VARCHAR(MAX),
            voice NVARCHAR(MAX),
            quiz_id INT,
            editor_id INT,
            DC_Created_Time DATETIME,
            DC_Edited_Time DATETIME
        )
    """,
    "capacity": """
        CREATE TABLE capacity (
            capacity_id INT IDENTITY(1, 1) PRIMARY KEY,
            user_id INT,
            phone NVARCHAR(12),
            allowed_student int,
            used_student int,
            DC_Created_Time DATETIME,
            DC_Edited_Time DATETIME
        )
    """,
    "quiz_answer": """
        CREATE TABLE quiz_answer (
            quiz_answer_id INT IDENTITY(1, 1) PRIMARY KEY,
            user_id INT,
            quiz_id INT,
            answers NVARCHAR(MAX),
            state INT,
            ins_id INT,
            con_id INT,
            DC_Created_Time DATETIME,
            DC_Edited_Time DATETIME
        )
    """,
    "scores": """
        CREATE TABLE scores (
            scores_id INT IDENTITY(1, 1) PRIMARY KEY,
            user_id INT,
            phone NVARCHAR(12),
            quiz_score NVARCHAR(MAX),
            brain_fields NVARCHAR(MAX),
            brain_categories NVARCHAR(MAX),
            brain_branches NVARCHAR(MAX),
            DC_Created_Time DATETIME,
            DC_Edited_Time DATETIME
        )
    """,
    "result_state": """
        CREATE TABLE result_state (
            result_state_id INT IDENTITY(1, 1),
            user_id INT PRIMARY KEY,
            phone NVARCHAR(12),
            t_state NVARCHAR(100),
            r_state NVARCHAR(100),
            e_state NVARCHAR(100),
            a_state NVARCHAR(100),
            m_state NVARCHAR(100),
            f_state NVARCHAR(100),
            i_state NVARCHAR(100),
            DC_Created_Time DATETIME,
            DC_Edited_Time DATETIME
        )
    """,
    "tokens": """
        CREATE TABLE tokens (
            token_id INT IDENTITY(1, 1) PRIMARY KEY,
            token VARCHAR(MAX),
            user_id INT,
            phone NVARCHAR(12),
            DC_Created_Time DATETIME,
            DC_Edited_Time DATETIME
        )
    """,
    "redis_log": """
        CREATE TABLE redis_log (
            id INT IDENTITY(1, 1) PRIMARY KEY,
            user_id INT,
            result VARCHAR(MAX),
            status INT DEFAULT 0,
            phone NVARCHAR(12),
            DC_Created_Time DATETIME,
            DC_Edited_Time DATETIME
        )
    """,
    "error_log": """
        CREATE TABLE error_log (
            id INT IDENTITY(1, 1) PRIMARY KEY,
            user_id INT,
            q_id INT,
            DC_Created_Time DATETIME,
            DC_Edited_Time DATETIME
        )
    """,
}
