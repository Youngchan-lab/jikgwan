"""K리그 홈페이지에서 월별 경기 일정·결과를 받아 공통 형식으로 바꾼다.

K리그 홈페이지 '일정/결과' 화면이 내부에서 쓰는 주소를 그대로 호출한다.
사용법:  python kleague.py 2026 2 3 4 5 6 7 8 9 10 11 12
"""

import json
import sys
import time
from collections import Counter

import requests

from names import kleague_stadium_code

URL = "https://www.kleague.com/getScheduleList.do"
HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/json; charset=utf-8",
    "Referer": "https://www.kleague.com/schedule.do",
}

# K리그 홈페이지 경기 상태 코드 -> 공통 상태
STATUS_MAP = {
    "FE": "종료",
    "NS": "예정",
    "LIVE": "진행중",
    "IN": "진행중",
    "HT": "진행중",   # 하프타임
    "PP": "취소",     # 연기
    "CAN": "취소",
}


def fetch_month(year: int, month: int, league_id: int = 1) -> dict:
    """K리그 홈페이지에서 한 달치 원본 데이터를 받는다. league_id: 1=K리그1, 2=K리그2"""
    body = {"year": str(year), "month": f"{month:02d}", "leagueId": league_id}
    res = requests.post(URL, json=body, headers=HEADERS, timeout=15)
    res.raise_for_status()
    return res.json().get("data", {})


def _num(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def parse(data: dict, league_id: int = 1) -> list[dict]:
    """원본 데이터를 공통 형식(경기 1개 = dict 1개)으로 바꾼다."""
    games = []
    for item in data.get("scheduleList", []):
        code = item.get("gameStatus") or ("FE" if item.get("endYn") == "Y" else "NS")
        status = STATUS_MAP.get(code, "종료" if item.get("endYn") == "Y" else "예정")

        home_score = _num(item.get("homeGoal"))
        away_score = _num(item.get("awayGoal"))
        if status in ("예정", "취소"):
            home_score = away_score = None  # 경기 전에는 0:0으로 올 수 있으므로 비운다

        games.append({
            "id": f"K{league_id}-{item.get('year')}-{item.get('meetSeq')}-{item.get('gameId')}",
            "league": f"K{league_id}",
            "series": item.get("meetName"),        # 대회명 (예: 하나은행 K리그1 2026)
            "round": _num(item.get("roundId")),
            "date": (item.get("gameDate") or "").replace(".", "-"),
            "time": item.get("gameTime"),
            "stadium": kleague_stadium_code(item.get("fieldName")),
            "home": item.get("homeTeam"),          # 팀 코드 (예: K09 = FC서울)
            "away": item.get("awayTeam"),
            "home_name": item.get("homeTeamName"),
            "away_name": item.get("awayTeamName"),
            "home_score": home_score,
            "away_score": away_score,
            "status": status,
            "status_code": code,                   # 점검용 원본 상태 코드
        })
    return games


def collect(year: int, months: list[int], league_id: int = 1) -> list[dict]:
    games = []
    for month in months:
        games += parse(fetch_month(year, month, league_id), league_id)
        time.sleep(1)  # 홈페이지 부담을 줄이기 위해 요청 사이 1초 대기

    # 여러 달 요청에 같은 경기가 겹쳐 나올 수 있으므로 ID 기준으로 하나만 남긴다
    unique = {g["id"]: g for g in games}
    return sorted(unique.values(), key=lambda g: (g["date"], g["time"] or ""))


def summarize(games: list[dict]) -> None:
    print(f"총 {len(games)}경기")
    print("대회별:", dict(Counter(g["series"] for g in games)))
    print("상태별:", dict(Counter(g["status"] for g in games)))
    print("원본 상태 코드별:", dict(Counter(g["status_code"] for g in games)))
    teams = {g["home"]: g["home_name"] for g in games} | {g["away"]: g["away_name"] for g in games}
    print("팀 코드:", dict(sorted(teams.items())))
    print("구장명:", sorted({g["stadium"] for g in games if g["stadium"]}))

    print("\n[점검 대상 경기: 종료가 아닌 경기]")
    for g in games:
        if g["status"] != "종료":
            print(json.dumps(g, ensure_ascii=False))


if __name__ == "__main__":
    year = int(sys.argv[1]) if len(sys.argv) > 1 else 2026
    months = [int(m) for m in sys.argv[2:]] or [10]

    # 원본 확인용: 첫 경기 1개를 그대로 출력
    first = fetch_month(year, months[0]).get("scheduleList", [])[:1]
    print("=== 원본 데이터 첫 경기 ===")
    print(json.dumps(first, ensure_ascii=False, indent=2))
    print()

    games = collect(year, months)
    summarize(games)

    out = f"kleague_{year}.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(games, f, ensure_ascii=False, indent=2)
    print(f"\n저장 완료: {out}")
