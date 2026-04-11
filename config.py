# config.py
GRADE_CLASSES = {
    "國一": ["甲", "乙", "丙", "丁", "戊"],
    "國二": ["甲", "乙", "丙", "丁", "戊", "己"],
    "國三": ["甲", "乙", "丙", "丁", "戊"],
    "高一": ["甲", "乙", "庚"],
    "高二": ["甲", "乙", "己", "庚"],
    "高三": ["甲", "乙", "己", "庚"],
}

JHS_GRADES = ["國一", "國二", "國三"]
SHS_GRADES = ["高一", "高二", "高三"]

JHS_SUBJECTS = ["國文", "英文", "數學", "公民", "歷史", "地理", "生物", "理化", "地科"]
SHS_SUBJECTS = ["國文", "英文", "數學", "物理", "化學", "生物", "地科", "地理", "公民", "歷史"]

PASSING_SCORE = 60
SCORE_BANDS = [(0, 59), (60, 69), (70, 79), (80, 89), (90, 100)]
SCORE_BAND_LABELS = ["59以下", "60-69", "70-79", "80-89", "90-100"]

ALERT_FAIL_RATE_THRESHOLD = 0.30
ALERT_EASY_THRESHOLD = 50.0
ALERT_REGRESSION_THRESHOLD = 10.0
ALERT_ANOMALY_STD_MULTIPLIER = 2.0
ALERT_ANOMALY_HISTORY_DIFF = 30.0

TUTORING_MIN_FAIL_SUBJECTS = 2
