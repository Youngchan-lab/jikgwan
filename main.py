"""KBO + K리그1 경기 데이터를 모아 앱이 읽을 파일(games_연도.json)을 만든다.

사용법
  python main.py full   # 시즌 전체 수집 (매일 새벽 1번)
  python main.py live   # 오늘 경기만 갱신 (경기 시간대에 5분마다)
"""

import json
import os
import sys
from datetime import datetime, timedelta, timezone

import kbo
import kleague

KST = timezone(timedelta(hours=9))
KBO_MONTHS = list(range(3, 12))       # 3~11월 (한국시리즈가 11월까지 갈 수 있음)
KLEAGUE_MONTHS = list(range(2, 13))   # 2~12월 (슈퍼컵 2월, 최종 라운드 12월)
DONE = ("종료", "취소")


def now() -> datetime:
    return datetime.now(KST)


def out_path(year: int) -> str:
    return f"games_{year}.json"


def load(year: int) -> list[dict]:
    path = out_path(year)
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return json.load(f)["games"]


def save(year: int, games: list[dict]) -> None:
    games = sorted(games, key=lambda g: (g["date"] or "", g["time"] or "", g["league"]))
    if games == load(year):
        print("경기 데이터 변경 없음 (파일 그대로 유지)")
        return
    data ={"updated": now().isoformat(timespec="seconds"), "games": games}
    with open(out_path(year), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print(f"저장 완료: {out_path(year)} ({len(games)}경기)")


def needs_refresh(g: dict, t: datetime) -> bool:
    """오늘 경기 중 아직 결과가 확정되지 않은 경기인지 판단한다."""
    if g["date"] != t.date().isoformat():
        return False
    if g["status"] not in DONE:
        return True
    # KBO는 경기 중에도 점수가 보여 '종료'로 잘못 표시될 수 있다.
    # 진행중 구분 규칙을 만들기 전까지는 시작 후 5시간 동안 계속 갱신한다.
    if g["league"] == "KBO" and g["status"] == "종료" and g["time"]:
        start = datetime.fromisoformat(f"{g['date']}T{g['time']}:00+09:00")
        return t < start + timedelta(hours=5)
    return False


def run_full(year: int) -> None:
    games = kbo.collect(year, KBO_MONTHS) + kleague.collect(year, KLEAGUE_MONTHS)
    save(year, games)


def run_live(year: int) -> None:
    t = now()
    games = load(year)
    if not games:
        print("기존 파일이 없어 전체 수집을 실행합니다.")
        return run_full(year)

    targets = [g for g in games if needs_refresh(g, t)]
    if not targets:
        print("갱신할 오늘 경기가 없습니다.")
        return

    leagues = {g["league"] for g in targets}
    print(f"갱신 대상 {len(targets)}경기: {sorted(leagues)}")

    fresh = []
    if "KBO" in leagues:
        fresh += kbo.collect(year, [t.month])
    if leagues & {"K1"}:
        fresh += kleague.collect(year, [t.month])

    # 다시 받은 리그·달의 기존 경기는 지우고 새 데이터로 바꾼다.
    # (예: 한국시리즈 'PO승리팀'이 실제 팀으로 바뀌면 경기 ID도 바뀌기 때문)
    month = t.strftime("%Y-%m")
    refreshed = leagues
    kept = [g for g in games
            if not (g["league"] in refreshed and (g["date"] or "").startswith(month))]
    save(year, kept + fresh)


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "full"
    year = int(sys.argv[2]) if len(sys.argv) > 2 else now().year
    run_full(year) if mode == "full" else run_live(year)
