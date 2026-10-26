"""팀명·구장명 통일표.

출처마다 표기가 달라도 앱에서는 아래 코드 하나로만 쓴다.
"""

# KBO 홈페이지 표기 -> 공통 코드
KBO_TEAMS = {
    "LG": "LG",
    "두산": "DOOSAN",
    "KIA": "KIA",
    "삼성": "SAMSUNG",
    "SSG": "SSG",
    "롯데": "LOTTE",
    "한화": "HANWHA",
    "NC": "NC",
    "KT": "KT",
    "키움": "KIWOOM",
}

# KBO 경기 ID에 쓰이는 2글자 팀 코드 (예: 20261001NCOB0 = NC 원정, 두산 홈)
KBO_ID_CODES = {
    "LG": "LG",
    "두산": "OB",
    "KIA": "HT",
    "삼성": "SS",
    "SSG": "SK",
    "롯데": "LT",
    "한화": "HH",
    "NC": "NC",
    "KT": "KT",
    "키움": "WO",
}

# KBO 홈페이지 구장 표기 -> 공통 코드
KBO_STADIUMS = {
    "잠실": "JAMSIL",
    "문학": "INCHEON",
    "사직": "SAJIK",
    "대구": "DAEGU",
    "광주": "GWANGJU",
    "대전": "DAEJEON",
    "창원": "CHANGWON",
    "수원": "SUWON",
    "고척": "GOCHEOK",
    "포항": "POHANG",
    "울산": "ULSAN",
    "청주": "CHEONGJU",
}


# K리그 홈페이지 구장 표기 -> 공통 코드 (KBO 구장 코드와 겹치지 않게 함)
KLEAGUE_STADIUMS = {
    "강릉하이원아레나": "GANGNEUNG_HIGH1",
    "광주 월드컵": "GWANGJU_WC",
    "김천 종합": "GIMCHEON",
    "대전 월드컵": "DAEJEON_WC",
    "부천 종합": "BUCHEON",
    "상주 시민": "SANGJU",
    "서울 월드컵": "SEOUL_WC",
    "안양 종합": "ANYANG",
    "울산 문수": "ULSAN_MUNSU",
    "인천 전용": "INCHEON_FOOTBALL",
    "전주 월드컵": "JEONJU_WC",
    "제주 월드컵": "JEJU_WC",
    "포항 스틸야드": "POHANG_STEELYARD",
}


def kleague_stadium_code(name: str) -> str:
    return KLEAGUE_STADIUMS.get((name or "").strip(), (name or "").strip())


def team_code(name: str) -> str:
    """통일표에 없으면 원래 이름을 그대로 돌려주고, 나중에 표에 추가한다."""
    return KBO_TEAMS.get(name.strip(), name.strip())


def stadium_code(name: str) -> str:
    return KBO_STADIUMS.get(name.strip(), name.strip())
