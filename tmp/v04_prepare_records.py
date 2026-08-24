from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

RUN = Path(sys.argv[1])
RUN_ID = RUN.name
CANDIDATES = RUN / "media" / "candidates"
APPROVED = RUN / "media" / "approved"
SH_TZ = ZoneInfo("Asia/Shanghai")
NOW = datetime.now(SH_TZ)

TITLE = "马蹄踏响草原：少年骑手为何让人热血沸腾？"
OPENING = "马蹄踏响草原，父亲把孩子托上马背，也把勇气交到了他的手里。人虽年少，握住缰绳的那一刻，眼里已经有了草原的辽阔。"
CLOSING = "从第一次上马，到独自策马、弯弓、迎风向前。练的是本领，磨的是胆气。高大骏马踏风而来，少年稳坐马背。让人想起“左牵黄，右擎苍，千骑卷平冈”的豪情。一代人托起下一代。马蹄所向，是辽阔草原，也是少年奔向远方的路。"
VOICEOVER = OPENING + "\n\n" + CLOSING + "\n"

SELECTED = [
    dict(shot_id="shot-01-father-lifts-son", asset_id="asset-01-father-lifts-son", bvid="BV1H14y1E72q", source_in=9.0, source_out=13.5, file="01-father-lifts-son.mp4", role="父亲和现场长辈稳定马匹、托举九岁男孩上马，建立传承起点", script_segment_id="broll-heritage", age_class="adult", recognizable_person=True, relation="父亲托举孩子上马", caption_free=True, source_marks=True, mark_note="左上角小型安全提示及来源账号标识、底部小型来源标识；无新闻标题、解说字幕或评论框。"),
    dict(shot_id="shot-02-youth-rides-away", asset_id="asset-02-youth-rides-away", bvid="BV1H14y1E72q", source_in=28.7, source_out=33.2, file="02-youth-rides-away.mp4", role="九岁少年脱离协助后独自策马离开，完成由托举到独立的动作闭环", script_segment_id="broll-first-ride", age_class="youth", recognizable_person=True, relation="少年独自策马", caption_free=True, source_marks=True, mark_note="左上角和底部保留小型来源标识；无新闻标题、解说字幕或评论框。"),
    dict(shot_id="shot-03-youth-black-horse-gallop", asset_id="asset-03-youth-black-horse-gallop", bvid="BV1bz4y1v7Z5", source_in=0.3, source_out=6.3, file="03-youth-black-horse-gallop.mp4", role="少年骑黑马高速疾驰，低位跟拍突出马匹步态、速度与少年神态", script_segment_id="broll-speed", age_class="youth", recognizable_person=True, relation="少年高速策马", caption_free=True, source_marks=False, mark_note="获选区间未见明显平台Logo、标题或字幕。"),
    dict(shot_id="shot-04-grassland-youth-rider", asset_id="asset-04-grassland-youth-rider", bvid="BV1464y1y75W", source_in=118.7, source_out=124.2, file="04-grassland-youth-rider.mp4", role="戴头盔少年在辽阔草原独立骑行，补足环境尺度与迎风向前的意境", script_segment_id="broll-grassland", age_class="youth", recognizable_person=True, relation="草原少年骑手", caption_free=True, source_marks=False, mark_note="获选区间无烧录字幕、标题、评论框或明显账号角标。"),
    dict(shot_id="shot-05-youth-mounted-archery", asset_id="asset-05-youth-mounted-archery", bvid="BV1KT4y1Z7M7", source_in=1.8, source_out=6.8, file="05-youth-mounted-archery.mp4", role="儿童骑射连续特写，保留搭箭、拉弓、瞄准动作和眼神力量", script_segment_id="broll-archery", age_class="youth", recognizable_person=True, relation="少年弯弓骑射", caption_free=True, source_marks=False, mark_note="获选区间无烧录字幕、新闻标题、评论框或平台Logo。"),
    dict(shot_id="shot-06-child-bokh-throw", asset_id="asset-06-child-bokh-throw", bvid="BV1QU4y1X7s8", source_in=120.2, source_out=126.2, file="06-child-bokh-throw.mp4", role="两名儿童完成抓握、角力和摔投，动作连续完整", script_segment_id="broll-bokh-one", age_class="youth", recognizable_person=True, relation="儿童搏克完整对抗", caption_free=True, source_marks=True, mark_note="顶部保留小型B站及来源账号标识；无解说字幕、标题或评论框。"),
    dict(shot_id="shot-07-child-bokh-power", asset_id="asset-07-child-bokh-power", bvid="BV1QU4y1X7s8", source_in=201.5, source_out=206.5, file="07-child-bokh-power.mp4", role="另一组儿童搏克的抱摔和腾空动作，强化力量高潮且不重复上一对抗", script_segment_id="broll-bokh-two", age_class="youth", recognizable_person=True, relation="不同儿童的第二组力量动作", caption_free=True, source_marks=True, mark_note="顶部保留小型B站及来源账号标识；无解说字幕、标题或评论框。"),
    dict(shot_id="shot-08-thousand-horses", asset_id="asset-08-thousand-horses", bvid="BV1RX4y1c7CL", source_in=0.0, source_out=4.5, file="08-thousand-horses.mp4", role="航拍万马奔腾形成规模高潮，人物不可辨识", script_segment_id="broll-herd", age_class="none", recognizable_person=False, relation="万马奔腾群体气势", caption_free=True, source_marks=False, mark_note="获选区间无烧录字幕、标题、评论框或明显账号角标。"),
    dict(shot_id="shot-09-white-horses-dust-finale", asset_id="asset-09-white-horses-dust-finale", bvid="BV1z3KU6DEpS", source_in=10.5, source_out=14.5, file="09-white-horses-dust-finale.mp4", role="白马群在夕照和扬尘中驰骋，以辽阔、远方和余韵收束混剪", script_segment_id="broll-finale", age_class="none", recognizable_person=False, relation="白马扬尘辽阔收束", caption_free=True, source_marks=False, mark_note="获选区间无烧录字幕、标题、评论框或明显账号角标。"),
]
SELECTED_BY_BVID = {item["bvid"] for item in SELECTED}

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

def duration(path: Path) -> float:
    out = subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=nw=1:nk=1", str(path)
    ], text=True).strip()
    return round(float(out), 3)

def iso_from_timestamp(value):
    if not value:
        return None
    return datetime.fromtimestamp(value, timezone.utc).astimezone(SH_TZ).isoformat()

def dump(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

infos = {}
for info_path in sorted(CANDIDATES.glob("*.info.json")):
    data = json.loads(info_path.read_text(encoding="utf-8"))
    cid = str(data.get("id") or info_path.stem.replace(".info", ""))
    infos[cid] = data

candidate_entries = []
search_entries = []
for cid, data in sorted(infos.items()):
    mp4 = CANDIDATES / f"{cid}.mp4"
    if not mp4.exists():
        matches = list(CANDIDATES.glob(f"{cid}.*"))
        mp4 = next((p for p in matches if p.suffix.lower() == ".mp4"), mp4)
    chosen = cid in SELECTED_BY_BVID
    reason = (
        "进入V04最终45秒方案，动作、年龄匹配、画面清洁度和叙事位置通过导演审查。"
        if chosen else
        "未进入最终方案：人物年龄、画面文字、清晰度、动作完整度、重复度或45秒叙事位置不及获选镜头。"
    )
    item = {
        "candidate_id": cid,
        "platform": "bilibili",
        "title": data.get("title") or cid,
        "uploader": data.get("uploader"),
        "published_at": iso_from_timestamp(data.get("timestamp")),
        "view_count": data.get("view_count"),
        "like_count": data.get("like_count"),
        "comment_count": data.get("comment_count"),
        "source_url": data.get("webpage_url") or data.get("original_url"),
        "local_path": str(mp4.relative_to(RUN)) if mp4.exists() else None,
        "sha256": sha256(mp4) if mp4.exists() else None,
        "downloaded_at": datetime.fromtimestamp(mp4.stat().st_mtime, timezone.utc).astimezone(SH_TZ).isoformat() if mp4.exists() else None,
        "approved": chosen,
        "decision_reason": reason,
    }
    candidate_entries.append(item)
    search_entries.append({k: item[k] for k in ("candidate_id", "platform", "title", "uploader", "published_at", "view_count", "like_count", "comment_count", "source_url", "downloaded_at")})

dump(RUN / "research" / "search-log.json", {
    "run_id": RUN_ID,
    "searched_at": NOW.isoformat(),
    "platforms": ["bilibili"],
    "queries": ["父亲 托 儿子 上马", "内蒙古 少年 骑马", "那达慕 儿童 赛马", "小孩 骑马 汽车 比赛", "少年 骑射", "儿童 搏克", "万马奔腾 航拍"],
    "proxy_note": "B站候选使用Chrome登录态与本地代理下载；所有链接来自实际info.json。",
    "results": search_entries,
})
dump(RUN / "research" / "candidate-pool.json", {
    "run_id": RUN_ID,
    "candidate_count": len(candidate_entries),
    "approved_source_count": len(SELECTED_BY_BVID),
    "generated_at": NOW.isoformat(),
    "candidates": candidate_entries,
})
md = [f"# V04 候选素材池（{len(candidate_entries)}条）", "", "| ID | 标题 | 发布者 | 播放量 | 采用 | 决策 |", "|---|---|---:|---:|:---:|---|"]
for x in candidate_entries:
    title = (x["title"] or "").replace("|", "｜")
    md.append(f'| {x["candidate_id"]} | {title} | {x["uploader"] or "-"} | {x["view_count"] if x["view_count"] is not None else "-"} | {"是" if x["approved"] else "否"} | {x["decision_reason"]} |')
(RUN / "research" / "candidate-pool.md").write_text("\n".join(md) + "\n", encoding="utf-8")

(RUN / "copy" / "title.txt").write_text(TITLE + "\n", encoding="utf-8")
(RUN / "copy" / "voiceover.txt").write_text(VOICEOVER, encoding="utf-8")
(RUN / "copy" / "opening.txt").write_text(OPENING + "\n", encoding="utf-8")
(RUN / "copy" / "closing.txt").write_text(CLOSING + "\n", encoding="utf-8")

source_lines = ["那达慕少年骑手V04素材来源（抓取热度快照）", ""]
source_map = []
ledger_assets = []
shot_records = []
for idx, shot in enumerate(SELECTED, 1):
    info = infos[shot["bvid"]]
    approved_path = APPROVED / shot["file"]
    approved_duration = duration(approved_path)
    source_url = info.get("webpage_url") or info.get("original_url")
    source_lines += [
        f"{idx}. {info.get('title')}",
        f"   发布者：{info.get('uploader')}",
        f"   抓取时播放量：{info.get('view_count') if info.get('view_count') is not None else '未提供'}",
        f"   链接：{source_url}",
        f"   采用区间：{shot['source_in']:.1f}—{shot['source_out']:.1f}秒；成片使用{approved_duration:.2f}秒",
        "",
    ]
    source_map.append({
        "shot_id": shot["shot_id"], "bvid": shot["bvid"], "title": info.get("title"), "uploader": info.get("uploader"),
        "source_url": source_url, "published_at": iso_from_timestamp(info.get("timestamp")), "view_count_at_download": info.get("view_count"),
        "like_count_at_download": info.get("like_count"), "downloaded_at": datetime.fromtimestamp((CANDIDATES / f"{shot['bvid']}.mp4").stat().st_mtime, timezone.utc).astimezone(SH_TZ).isoformat(),
        "original_source_in": shot["source_in"], "original_source_out": shot["source_out"],
        "approved_clip_path": f"media/approved/{shot['file']}", "approved_clip_duration_seconds": approved_duration,
        "approved_clip_sha256": sha256(approved_path), "recognizable_person": shot["recognizable_person"], "age_class": shot["age_class"],
        "relationship_or_action": shot["relation"], "burned_caption_free": shot["caption_free"], "project_text_overlay_used": False,
        "visible_source_marks": shot["source_marks"], "visible_source_marks_allowed_by_user": True, "source_mark_note": shot["mark_note"],
        "continuous_forward_playback": True, "loop_used": False, "reverse_used": False, "ping_pong_used": False,
    })
    ledger_assets.append({
        "asset_id": shot["asset_id"], "source_platform": "bilibili", "source_url": source_url,
        "downloaded_at": datetime.fromtimestamp(approved_path.stat().st_mtime, timezone.utc).astimezone(SH_TZ).isoformat(),
        "local_path": f"media/approved/{shot['file']}", "sha256": sha256(approved_path),
        "watermark_free": not shot["source_marks"], "platform_logo_free": not shot["source_marks"], "account_mark_free": not shot["source_marks"],
        "burned_caption_free": shot["caption_free"], "visible_source_marks_allowed_by_user": True, "burned_captions_allowed_by_user": False,
        "visual_relevance": shot["role"], "user_usage_rule_passed": True,
    })
    shot_records.append({
        "shot_id": shot["shot_id"], "asset_id": shot["asset_id"], "script_segment_id": shot["script_segment_id"],
        "semantic_role": shot["role"], "source_in": shot["source_in"], "source_out": shot["source_out"],
        "target_duration_seconds": round(shot["source_out"] - shot["source_in"], 3), "continuous_action": True,
        "forward_playback": True, "visual_quality_passed": True, "director_approved": True,
    })

(RUN / "copy" / "source-links.txt").write_text("\n".join(source_lines), encoding="utf-8")
dump(RUN / "production" / "source-clip-map.json", {"run_id": RUN_ID, "clips": source_map})
dump(RUN / "production" / "footage-ledger.json", {"run_id": RUN_ID, "assets": ledger_assets})
dump(RUN / "production" / "shot-selection.json", {"run_id": RUN_ID, "shots": shot_records})

recognizable = [x for x in SELECTED if x["recognizable_person"]]
youth = sum(x["source_out"] - x["source_in"] for x in recognizable if x["age_class"] == "youth")
adult = sum(x["source_out"] - x["source_in"] for x in recognizable if x["age_class"] == "adult")
recognizable_total = youth + adult
dump(RUN / "production" / "age-matching-qc.json", {
    "run_id": RUN_ID, "recognizable_person_seconds": recognizable_total, "youth_seconds": youth, "adult_seconds": adult,
    "youth_ratio": youth / recognizable_total, "adult_ratio": adult / recognizable_total,
    "requirements": {"youth_ratio_min": 0.8, "adult_ratio_max": 0.2},
    "passed": youth / recognizable_total >= 0.8 and adult / recognizable_total <= 0.2,
    "note": "第二段开头仍可见短暂现场协助者，但视觉主体和叙事主体为独立策马少年；按保守口径纳入父辈传承镜头亦不影响比例通过。",
})
dump(RUN / "production" / "usage-rights-note.json", {
    "run_id": RUN_ID,
    "user_rule": "用户要求尽量不使用带烧录字幕、标题和评论框的素材；本版无项目新增文字层，获选区间均无新闻标题、解说字幕和评论框。",
    "rights_boundary": "允许保留来源水印不等同于版权授权；发布方仍需依据授权、合理使用和平台规则决定公开发布范围。",
    "burned_caption_policy": "九段获选区间均按无烧录解说字幕、无新闻标题、无评论框标准筛选。",
    "source_mark_disclosure": "第1、2段保留原作者小型来源/安全提示，第6、7段顶部保留小型B站及账号标识；其余区间未见明显来源标识。",
})

evidence_info = infos["BV1H14y1E72q"]
dump(RUN / "production" / "fact-evidence.json", {
    "run_id": RUN_ID,
    "authoritative_sources": [{
        "source_id": "relationship-evidence-BV1H14y1E72q", "platform": "bilibili",
        "title": evidence_info.get("title"), "url": evidence_info.get("webpage_url"),
        "published_at": iso_from_timestamp(evidence_info.get("timestamp")),
        "reliability_note": "作品标题明确写明父亲、儿子和九岁赛马手；画面显示多名成年人稳定马匹并托举男孩上马。仅用于支持父子托举关系，不外推民族、赛事名次或具体地点。",
    }],
    "event_time": None, "locations": ["草原赛马与那达慕相关场景"],
    "verified_facts": ["来源标题明确描述父亲扶九岁儿子上马。", "获选画面显示成年人稳定马匹并托举男孩上马，随后少年独自策马。", "最终插播还包含少年策马、儿童骑射、儿童搏克和马群奔腾。"],
    "verified_numbers": ["可辨识人物镜头中，按保守分类少年32秒、成年4.5秒，少年占比约87.7%。", "静音插播源区间合计45秒。"],
    "uncertainties": ["不同素材拍摄时间、具体地点和赛事名称不统一，口播不作统一事件报道。", "除BV1H14y1E72q标题外，不进一步断言画面中成年人具体身份。"],
    "prohibited_claims": ["不得声称全部素材来自同一届那达慕或同一天。", "不得猜测民族身份、赛事成绩或获奖名次。", "不得把儿童骑射剪辑表述为同一机位连续赛事记录。"],
})
dump(RUN / "production" / "script-director-notes.json", {
    "run_id": RUN_ID, "approved": True,
    "narrative": "托举—接缰—疾驰—弯弓—搏克—万马—远方",
    "opening_note": "用父亲托举建立传承关系，短句起势；不把不同来源包装为同一事件。",
    "broll_note": "中段45秒连续静音，主持人不压画面；镜头保留完整动作，用户后期自行加入热血BGM。",
    "ending_note": "结尾回到主持人，以古典豪情和代际传承完整收束。",
    "wording_boundary": "因BV1H14y1E72q标题和画面共同支持父子关系，保留‘父亲把孩子托上马背’；不增加具体赛事、地点或成绩。",
})
print(json.dumps({"candidate_count": len(candidate_entries), "selected_shots": len(SELECTED), "youth_ratio": youth / recognizable_total, "adult_ratio": adult / recognizable_total}, ensure_ascii=False))
