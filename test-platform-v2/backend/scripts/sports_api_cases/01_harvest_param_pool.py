# -*- coding: utf-8 -*-
"""收割 Test5 真实业务 id，形成「真实参数池」用于接口用例参数回填。"""
import json, urllib.request, ssl, time

GW = "http://camel-api-gateway05.svc.elelive.cn"
ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE

def get(url, timeout=40):
    req = urllib.request.Request(url, headers={"User-Agent": "camel-qa", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
        return r.status, json.loads(r.read().decode("utf-8", "replace"))

def call(svc, path, timeout=40):
    try:
        st, j = get(f"{GW}/{svc}{path}", timeout)
        return j
    except Exception as e:
        return {"_err": repr(e)[:120]}

def collect_ids(obj, key, into, limit=9999):
    """recursively collect values for fields named like key (id / *_id / *_team_id ...)"""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == key and isinstance(v, (str, int)):
                if len(into) < limit and v not in ("", None):
                    into.append(str(v))
            else:
                collect_ids(v, key, into, limit)
    elif isinstance(obj, list):
        for x in obj:
            collect_ids(x, key, into, limit)

def harvest(svc):
    pool = {"matchId": [], "competitionId": [], "seasonId": [], "teamId": [], "playerId": [],
            "articleId": [], "stageId": [], "venueId": [], "refereeId": [], "authorId": []}
    # 1. home_match (real matches)
    for day in ["20260825", "20260826", "20260827"]:
        j = call(svc, f"/ee/sports_live/home_match?day={day}")
        for k in ["matchId", "competitionId", "seasonId", "teamId", "stageId", "venueId", "refereeId"]:
            # collect by field name: id -> matchId; competition_id -> competitionId; home_team_id/away_team_id -> teamId
            pass
        # custom extraction
        if isinstance(j, dict) and j.get("status") == 200:
            data = j.get("data", {})
            for g in (data.get("hot_group") or []) + (data.get("living_group") or []) + (data.get("obs_group") or []):
                for m in (g.get("match") or []):
                    if m.get("id"): pool["matchId"].append(m["id"])
                    if m.get("competition_id"): pool["competitionId"].append(m["competition_id"])
                    if m.get("season_id"): pool["seasonId"].append(m["season_id"])
                    if m.get("home_team_id"): pool["teamId"].append(m["home_team_id"])
                    if m.get("away_team_id"): pool["teamId"].append(m["away_team_id"])
                    if m.get("stage_id"): pool["stageId"].append(m.get("stage_id"))
                    if m.get("venue_id"): pool["venueId"].append(m.get("venue_id"))
                    if m.get("referee_id"): pool["refereeId"].append(m.get("referee_id"))
                    if m.get("round", {}).get("stage_id"): pool["stageId"].append(m["round"]["stage_id"])
    # 2. hot_match
    j = call(svc, "/ee/sports_live/hot_match?page=1&size=20")
    if isinstance(j, dict) and j.get("status") == 200:
        collect_ids(j.get("data", {}), "id", pool["matchId"])
    # 3. list_competition
    j = call(svc, "/ee/sports_live/list_competition")
    if isinstance(j, dict) and j.get("status") == 200:
        d = j.get("data", {})
        for rec in (d.get("hotRecords") or []) + (d.get("records") or []):
            if rec.get("id"): pool["competitionId"].append(rec["id"])
            if rec.get("seasonId") or rec.get("season_id"): pool["seasonId"].append(rec.get("seasonId") or rec.get("season_id"))
    # 4. season_teams (use first harvested seasonId)
    if pool["seasonId"]:
        j = call(svc, f"/ee/sports_live/season_teams?seasonId={pool['seasonId'][0]}")
        if isinstance(j, dict) and j.get("status") == 200:
            collect_ids(j.get("data", {}), "teamId", pool["teamId"])
            collect_ids(j.get("data", {}), "id", pool["teamId"])
    # 5. player hot-players
    j = call(svc, "/ee/sports_live/player/hot-players")
    if isinstance(j, dict) and j.get("status") == 200:
        collect_ids(j.get("data", {}), "playerId", pool["playerId"])
        collect_ids(j.get("data", {}), "id", pool["playerId"])
    # 6. article home (articleId / authorId)
    j = call(svc, "/ee/article/home?page=1&size=20")
    if isinstance(j, dict) and j.get("status") == 200:
        collect_ids(j.get("data", {}), "articleId", pool["articleId"])
        collect_ids(j.get("data", {}), "authorId", pool["authorId"])
    # 7. hot_team (teamId)
    j = call(svc, "/ee/sports_live/hot_team")
    if isinstance(j, dict) and j.get("status") == 200:
        collect_ids(j.get("data", {}), "id", pool["teamId"])
        collect_ids(j.get("data", {}), "teamId", pool["teamId"])
    # 8. group_competition (competitionId)
    j = call(svc, "/ee/sports_live/group_competition")
    if isinstance(j, dict) and j.get("status") == 200:
        collect_ids(j.get("data", {}), "id", pool["competitionId"])
        collect_ids(j.get("data", {}), "competitionId", pool["competitionId"])

    # dedupe preserving order
    for k in pool:
        seen = set(); out = []
        for v in pool[k]:
            if v not in seen:
                seen.add(v); out.append(v)
        pool[k] = out
    return pool

result = {}
for svc in ["camel-service", "basketball-service"]:
    result[svc] = harvest(svc)
    print(f"=== {svc} ===")
    for k, v in result[svc].items():
        print(f"  {k}: {len(v)} -> {v[:5]}")
    print()

with open("F:\\CamelTv\\_tmp_real_param_pool.json", "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=1)
print("saved _tmp_real_param_pool.json")
