"""KBO 실시간 점수 데이터 주소 확인용 (테스트 전용, 앱에는 쓰지 않음).

KBO 홈페이지 첫 화면 '오늘의 경기' 점수판이 내부에서 쓰는 주소를 호출해
원본 응답을 그대로 저장한다.
사용법:  python live_probe.py            (오늘)
         python live_probe.py 20261026   (특정 날짜)
"""

import json
import os
import sys
from datetime import datetime, timedelta, timezone

import requests

KST = timezone(timedelta(hours=9))
URL = "https://www.koreabaseball.com/ws/Main.asmx/GetKboGameList"
HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://www.koreabaseball.com/",
    "X-Requested-With": "XMLHttpRequest",
}

now = datetime.now(KST)
day = sys.argv[1] if len(sys.argv) > 1 else now.strftime("%Y%m%d")

res = requests.post(
    URL,
    data={"leId": "1", "srId": "0,1,3,4,5,6,7,8,9", "date": day},
    headers=HEADERS,
    timeout=15,
)
print("응답 코드:", res.status_code)
data = res.json()

games = data.get("game", [])
print(f"경기 수: {len(games)}")
for g in games:
    # 점수·상태로 보이는 항목만 골라 한 줄로 출력
    picked = {k: v for k, v in g.items()
              if any(s in k for s in ("G_ID", "TM_NM", "SCORE", "STATE", "INN", "S_NM", "G_TM"))}
    print(json.dumps(picked, ensure_ascii=False))

os.makedirs("probe", exist_ok=True)

# 1) 실행할 때마다 한 줄씩 기록 (경기 중 점수 변화 확인용)
with open(f"probe/live_log_{day}.txt", "a", encoding="utf-8") as f:
    for g in games:
        f.write(f"{now.strftime('%H:%M:%S')} {g.get('G_ID')} "
                f"상태={g.get('GAME_STATE_SC')} 이닝={g.get('GAME_INN_NO')} "
                f"원정={g.get('T_SCORE_CN')} 홈={g.get('B_SCORE_CN')}\n")

# 2) 원본 전체는 날짜별 최신 1개만 저장
path = f"probe/kbo_live_{day}.json"
with open(path, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=1)
print("원본 저장:", path)
