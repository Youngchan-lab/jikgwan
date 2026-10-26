"""KBO 홈페이지에서 월별 경기 일정·결과를 받아 공통 형식으로 바꾼다.

KBO 홈페이지 '일정/결과' 화면이 내부에서 쓰는 주소를 그대로 호출한다.
사용법:  python kbo.py 2026 10
"""

import json
import re
import sys
import time
from datetime import date, datetime, timedelta, timezone

import requests
from bs4 import BeautifulSoup

from names import KBO_ID_CODES, stadium_code, team_code

URL = "https://www.koreabaseball.com/ws/Schedule.asmx/GetScheduleList"
HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://www.koreabaseball.com/Schedule/Schedule.aspx",
    "X-Requested-With": "XMLHttpRequest",
}

# 비고에 이 단어가 있으면 취소 경기 (예: 우천취소, 폭염취소, 그라운드사정)
CANCEL_KEYWORDS = ("취소", "사정", "연기", "노게임")

# 경기 구분 코드 (KBO 홈페이지 기준, 첫 실행 때 확인 필요)
SERIES = {
    "regular": "0,9,6",   # 정규시즌
    "post": "3,4,5,7",    # 포스트시즌
}


def fetch_month(year: int, month: int, series: str = "regular") -> list[dict]:
    """KBO 홈페이지에서 한 달치 원본 데이터를 받는다."""
    data = {
        "leId": "1",
        "srIdList": SERIES[series],
        "seasonId": str(year),
        "gameMonth": f"{month:02d}",
        "teamId": "",
    }
    res = requests.post(URL, data=data, headers=HEADERS, timeout=15)
    res.raise_for_status()
    return res.json().get("rows", [])


def _text(html: str) -> str:
    return BeautifulSoup(html or "", "html.parser").get_text(strip=True)


KST = timezone(timedelta(hours=9))


def _started(game_date: str | None, game_time: str) -> bool:
    """한국 시간 기준으로 경기 시작 시각이 지났는지 확인한다."""
    if not game_date or not re.match(r"^\d{2}:\d{2}$", game_time):
        return True  # 시각을 모르면 점수가 있는 것을 기준으로 진행중으로 본다
    start = datetime.fromisoformat(f"{game_date}T{game_time}:00").replace(tzinfo=KST)
    return datetime.now(KST) >= start


def parse_rows(rows: list[dict], year: int, series: str = "regular") -> list[dict]:
    """원본 데이터를 공통 형식(경기 1개 = dict 1개)으로 바꾼다."""
    games = []
    current_date = None  # 날짜 칸은 그날 첫 경기에만 있으므로 기억해 둔다

    for r in rows:
        cells = r.get("row", [])
        by_class = {c.get("Class"): c.get("Text", "") for c in cells if c.get("Class")}
        others = [c.get("Text", "") for c in cells if not c.get("Class")]

        # 날짜: "10.01(수)" -> "2026-10-01"
        if "day" in by_class:
            m = re.match(r"(\d{2})\.(\d{2})", _text(by_class["day"]))
            if m:
                current_date = f"{year}-{m.group(1)}-{m.group(2)}"

        if "play" not in by_class:
            continue  # 경기 없는 줄 (예: "경기가 없습니다")

        # 경기: 원정팀 [점수 vs 점수] 홈팀
        play = BeautifulSoup(by_class["play"], "html.parser")
        spans = play.find_all("span", recursive=False)
        away_name = spans[0].get_text(strip=True) if spans else ""
        home_name = spans[-1].get_text(strip=True) if len(spans) > 1 else ""

        score_spans = [s.get_text(strip=True) for s in play.select("em span")]
        scores = [s for s in score_spans if s.isdigit()]
        away_score = int(scores[0]) if len(scores) == 2 else None
        home_score = int(scores[1]) if len(scores) == 2 else None

        # 경기 고유번호: 게임센터 링크 안의 gameId (예: 20261001LGOB0, 끝자리 = 더블헤더 차수)
        game_id = None
        m = re.search(r"gameId=(\w+)", by_class.get("relay", ""))
        if m:
            game_id = m.group(1)
        elif current_date:
            # 취소 경기는 링크가 없으므로 KBO 형식(날짜+원정+홈+차수)으로 직접 만든다
            game_id = (current_date.replace("-", "")
                       + KBO_ID_CODES.get(away_name, "XX")
                       + KBO_ID_CODES.get(home_name, "XX") + "0")

        # 구장, 비고: 이름 없는 칸 중 뒤에서 두 번째, 첫 번째
        stadium = _text(others[-2]) if len(others) >= 2 else ""
        note = _text(others[-1]) if others else ""

        # 경기 당일에는 시작 전에도 0:0 점수가 표시되므로 점수만으로 종료를 판단하지 않는다.
        # 끝난 경기는 게임센터 링크가 '리뷰(section=REVIEW)'로 바뀐다.
        today = datetime.now(KST).date().isoformat()
        is_review = "section=REVIEW" in by_class.get("relay", "")
        if away_score is not None and (is_review or (current_date and current_date < today)):
            status = "종료"
        elif any(k in note for k in CANCEL_KEYWORDS):
            status = "취소"
        elif current_date and current_date < today:
            status = "취소"  # 지난 날짜인데 점수가 없으면 열리지 않은 경기로 본다
        elif away_score is not None and _started(current_date, _text(by_class.get("time", ""))):
            status = "진행중"  # 오늘 경기, 시작 시각이 지났고 아직 리뷰 링크가 없음
        else:
            status = "예정"    # 시작 전 0:0 표시도 여기로 온다
        if status in ("예정", "취소"):
            home_score = away_score = None

        games.append({
            "id": f"KBO-{game_id}" if game_id else None,
            "league": "KBO",
            "series": "정규시즌" if series == "regular" else "포스트시즌",
            "date": current_date,
            "time": _text(by_class.get("time", "")),
            "stadium": stadium_code(stadium),
            "home": team_code(home_name),
            "away": team_code(away_name),
            "home_score": home_score,
            "away_score": away_score,
            "status": status,
            "note": note if note not in ("-", "") else None,
        })
    return games


def collect(year: int, months: list[int]) -> list[dict]:
    games = []
    for month in months:
        for series in SERIES:
            rows = fetch_month(year, month, series)
            games += parse_rows(rows, year, series)
            time.sleep(1)  # 홈페이지 부담을 줄이기 위해 요청 사이 1초 대기
    return games


def summarize(games: list[dict]) -> None:
    """수집 결과 점검용 요약."""
    from collections import Counter
    from names import KBO_STADIUMS, KBO_TEAMS

    print(f"총 {len(games)}경기")
    print("구분별:", dict(Counter(g["series"] for g in games)))
    print("상태별:", dict(Counter(g["status"] for g in games)))

    ids = [g["id"] for g in games if g["id"]]
    dup = [i for i, n in Counter(ids).items() if n > 1]
    print("중복 ID:", dup or "없음")

    known_teams = set(KBO_TEAMS.values())
    known_stadiums = set(KBO_STADIUMS.values())
    unknown_t = {t for g in games for t in (g["home"], g["away"]) if t not in known_teams}
    unknown_s = {g["stadium"] for g in games if g["stadium"] not in known_stadiums}
    print("통일표에 없는 팀명:", unknown_t or "없음")
    print("통일표에 없는 구장명:", unknown_s or "없음")

    print("취소 사유별:", dict(Counter(g["note"] for g in games if g["status"] == "취소")))

    print("\n[점검 대상 경기: 포스트시즌, 예정 경기, ID 없는 경기]")
    for g in games:
        if g["series"] == "포스트시즌" or g["status"] == "예정" or not g["id"]:
            print(json.dumps(g, ensure_ascii=False))


if __name__ == "__main__":
    year = int(sys.argv[1]) if len(sys.argv) > 1 else 2026
    months = [int(m) for m in sys.argv[2:]] or [10]

    games = collect(year, months)
    summarize(games)

    out = f"kbo_{year}.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(games, f, ensure_ascii=False, indent=2)
    print(f"\n저장 완료: {out}")
