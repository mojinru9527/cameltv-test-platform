# -*- coding: utf-8 -*-
"""
Batch 27 M5.2 -- AI Interaction Recognition POC
================================================
Validates DeepSeek multimodal ability to identify interactive elements
(buttons, links, tabs, form controls) from lanhu prototype screenshots.

Method:
  1. Select 5 page screenshots from lanhu evidence data
  2. Define ground truth from DOM text extraction (known UI elements)
  3. Send each screenshot to DeepSeek vision API
  4. Compare AI results vs ground truth (precision / recall / F1)
  5. Threshold: >= 50% F1 -> continue with AI; < 50% -> fallback to CV + manual

POC script -- NOT committed to repo (per PM plan).
"""

from __future__ import annotations

import io
import json
import os
import sqlite3
import sys
import time
from base64 import b64encode
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Force UTF-8 stdout on Windows
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ── Configuration ──

# Add backend to path so we can import app.core.config
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import settings

DEEPSEEK_BASE = settings.ai_api_base_url  # https://api.deepseek.com/v1
DEEPSEEK_KEY = settings.ai_api_key
DEEPSEEK_MODEL = "deepseek-chat"  # multimodal-capable

DB_PATH = BACKEND_DIR / "data" / "platform.db"

# Ground truth: page_id -> set of known interactive element labels
# Extracted from lanhu_evidence_page.dom_text for each page.
# These are UI elements that a human would recognize as clickable/interactive.
GROUND_TRUTH: dict[int, dict] = {
    # Page 11: APP端 首页 (sports app home screen)
    11: {
        "page_name": "APP端-首页",
        "folder": "首页",
        "elements": {
            # Bottom tab bar
            "首页", "预测", "资讯", "我的",
            # Top nav
            "赛事", "球队", "联赛",
            # Filter/chip tabs
            "收藏分组", "比赛", "联赛",
            # Match cards (clickable)
            "视频/动画", "LIVE", "HD",
            # Action icons
            "icon",
        },
    },
    # Page 22: APP端 资讯列表 (news list)
    22: {
        "page_name": "APP端-资讯列表",
        "folder": "资讯",
        "elements": {
            # Bottom tab bar
            "首页", "预测", "资讯", "我的",
            # Top nav
            "赛事", "球队", "联赛",
            # Category filter tabs
            "全部", "独家情报", "热门前瞻", "球员花边",
            # Action icons
            "展开", "我的收藏",
            # Article cards (clickable)
            "置顶", "icon",
        },
    },
    # Page 25: APP端 搜索结果页 (search results)
    25: {
        "page_name": "APP端-搜索结果页",
        "folder": "搜索",
        "elements": {
            # Search bar
            "清空", "取消",
            # Action
            "更多",
            # Match cards (clickable)
            "视频/动画", "LIVE",
            # Section headers
            "赛事", "球队", "联赛",
        },
    },
    # Page 340: 运营后台 新增/编辑资讯 (admin article editor form)
    340: {
        "page_name": "运营后台-新增编辑资讯",
        "folder": "内容管理",
        "elements": {
            # Form controls
            "封面(cover)", "是否上线", "标题(title)", "关键字(keywords)",
            "内容", "富文本编辑器",
            # Buttons
            "取消", "保存",
            # Select/dropdown
            "请选择", "所属分类(Categories)",
            # Fields
            "文章id(newsid)", "描述(Description)", "是否置顶(Pin)",
            # Related entity fields
            "关联比赛(Related Matches)", "关联联赛(Related League)",
            "关联球队(Related Teams)",
            # Sidebar navigation (admin)
            "内容管理", "用户管理", "联赛及球队管理", "财务管理",
            "装扮管理", "商城", "银钻任务", "风控管理",
            "赛事预测", "消息管理", "广告管理", "热门搜索管理", "FAQ管理",
            # Sub-nav
            "资讯列表", "资讯分类",
            # Radio buttons
            "Yes", "No",
        },
    },
    # Page 395: 运营后台 聊天室消息 (admin chat room messages table)
    395: {
        "page_name": "运营后台-聊天室消息",
        "folder": "消息管理",
        "elements": {
            # Sidebar navigation
            "内容管理", "用户管理", "联赛及球队管理", "财务管理",
            "装扮管理", "商城", "银钻任务", "风控管理",
            "赛事预测", "消息管理", "广告管理",
            # Sub-nav under 消息管理
            "推送消息", "直播间消息", "聊天室消息",
            # Table headers
            "英语内容", "发送条件", "显示顺序", "操作",
            # Row actions
            "编辑", "删除",
            # Buttons
            "新增", "确认",
            # Dialog buttons
            "进入直播间",
            # Send condition badge
            "定时发送",
        },
    },
}

# ── POC prompt template ──

SYSTEM_PROMPT = """You are a UI interaction analyst. Your task is to identify all interactive (clickable/tappable) elements in a mobile app or web admin screenshot.

An interactive element is any UI component that a user can click, tap, or otherwise interact with to trigger an action or navigation. This includes:
- Buttons (text buttons, icon buttons, action buttons)
- Navigation tabs (bottom tab bar, top tab bar, sidebar menu items)
- Links / clickable text
- List items / cards that navigate to detail pages
- Form controls (text inputs, dropdowns, checkboxes, radio buttons, toggles)
- Filter chips / category tabs
- Icons that trigger actions (search, menu, close, etc.)
- Expandable sections / accordions

For each element you identify, provide:
1. The visible text/label of the element
2. The element type (button, tab, link, card, input, chip, icon, etc.)
3. Your confidence (0.0-1.0)

Return ONLY a JSON array. No markdown, no explanation.

Format:
[{"label": "首页", "type": "tab", "confidence": 0.95}, ...]

If no interactive elements are visible, return [].
"""

USER_PROMPT_TEMPLATE = """Identify ALL interactive elements visible in this {page_type} screenshot.

Page context: {page_name} (folder: {folder})
Platform: {platform}

Return JSON array of interactive elements."""


# ── API call ──

def encode_image(path: str) -> str:
    """Read image file and return base64 data URI."""
    with open(path, "rb") as f:
        data = b64encode(f.read()).decode("utf-8")
    # Detect MIME type from extension
    ext = os.path.splitext(path)[1].lower()
    mime = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg"}.get(ext, "image/png")
    return f"data:{mime};base64,{data}"


def call_deepseek_vision(
    image_path: str,
    page_name: str,
    folder: str,
    platform: str = "mobile_app",
) -> list[dict]:
    """Send screenshot to DeepSeek vision model, return detected interactive elements."""
    import urllib.request
    import urllib.error

    image_uri = encode_image(image_path)
    user_text = USER_PROMPT_TEMPLATE.format(
        page_type="mobile app" if "APP" in folder else "web admin",
        page_name=page_name,
        folder=folder,
        platform=platform,
    )

    body = {
        "model": DEEPSEEK_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": user_text},
                    {"type": "image_url", "image_url": {"url": image_uri}},
                ],
            },
        ],
        "temperature": 0.1,
        "max_tokens": 4096,
    }

    req = urllib.request.Request(
        f"{DEEPSEEK_BASE}/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {DEEPSEEK_KEY}",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            content = result["choices"][0]["message"]["content"]
            # Parse JSON from response (strip markdown code fences if present)
            content = content.strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[1]
                if content.endswith("```"):
                    content = content[:-3]
            return json.loads(content)
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8") if e.fp else str(e)
        print(f"    [ERROR] HTTP {e.code}: {error_body[:300]}")
        return []
    except (json.JSONDecodeError, KeyError, IndexError) as e:
        print(f"    [ERROR] Parse failed: {e}")
        return []


# ── Evaluation ──

@dataclass
class EvalResult:
    page_id: int
    page_name: str
    ground_truth_count: int
    ai_detected_count: int
    true_positives: list[str]  # elements found by both
    false_positives: list[str]  # AI found but not in ground truth
    false_negatives: list[str]  # in ground truth but AI missed
    precision: float = 0.0
    recall: float = 0.0
    f1: float = 0.0

    @property
    def passed(self) -> bool:
        return self.f1 >= 0.50


def evaluate_page(
    page_id: int,
    gt_elements: set[str],
    ai_results: list[dict],
) -> EvalResult:
    """Compare AI detections against ground truth using fuzzy matching."""
    gt = {e.lower().strip() for e in gt_elements}

    ai_labels: set[str] = set()
    for item in ai_results:
        if isinstance(item, dict) and "label" in item:
            ai_labels.add(item["label"].lower().strip())

    # True positives: exact match OR one contains the other (fuzzy)
    tp: set[str] = set()
    remaining_gt = set(gt)
    remaining_ai = set(ai_labels)

    # Exact matches first
    exact = gt & ai_labels
    tp.update(exact)
    remaining_gt -= exact
    remaining_ai -= exact

    # Fuzzy: AI label is substring of GT or vice versa
    for ai_lbl in list(remaining_ai):
        for gt_lbl in list(remaining_gt):
            if ai_lbl in gt_lbl or gt_lbl in ai_lbl:
                tp.add(gt_lbl)
                remaining_gt.discard(gt_lbl)
                remaining_ai.discard(ai_lbl)
                break

    fp = remaining_ai  # AI detected but not in ground truth
    fn = remaining_gt  # In ground truth but AI missed

    precision = len(tp) / len(ai_labels) if ai_labels else 0.0
    recall = len(tp) / len(gt) if gt else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    return EvalResult(
        page_id=page_id,
        page_name=GROUND_TRUTH[page_id]["page_name"],
        ground_truth_count=len(gt),
        ai_detected_count=len(ai_labels),
        true_positives=sorted(tp),
        false_positives=sorted(fp),
        false_negatives=sorted(fn),
        precision=round(precision, 3),
        recall=round(recall, 3),
        f1=round(f1, 3),
    )


# ── Database helpers ──

def get_screenshot_path(page_id: int) -> str | None:
    """Get first screenshot asset path for a page."""
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()
    cur.execute(
        "SELECT a.file_path FROM lanhu_evidence_asset a "
        "WHERE a.page_id = ? AND a.asset_type = 'screenshot' "
        "ORDER BY a.id LIMIT 1",
        (page_id,),
    )
    row = cur.fetchone()
    conn.close()
    if row and row[0] and os.path.exists(row[0]):
        return row[0]
    return None


# ── Main ──

def main() -> int:
    print("=" * 70)
    print("Batch 27 M5.2: AI Interaction Recognition POC")
    print(f"Model: {DEEPSEEK_MODEL}")
    print(f"API: {DEEPSEEK_BASE}")
    print("=" * 70)

    if not DEEPSEEK_KEY:
        print("\n[ERROR] DeepSeek API key not configured. Set AI_API_KEY in .env")
        return 1

    results: list[EvalResult] = []
    page_ids = list(GROUND_TRUTH.keys())

    for pid in page_ids:
        gt = GROUND_TRUTH[pid]
        print(f"\n{'─' * 50}")
        print(f"[PAGE {pid}] {gt['page_name']} (folder: {gt['folder']})")
        print(f"  Ground truth elements: {len(gt['elements'])}")
        print(f"  Elements: {sorted(gt['elements'])[:10]}..."
              if len(gt['elements']) > 10 else f"  Elements: {sorted(gt['elements'])}")

        # Find screenshot
        ss_path = get_screenshot_path(pid)
        if not ss_path:
            print(f"  [SKIP] No screenshot found for page {pid}")
            continue

        print(f"  Screenshot: {ss_path}")
        file_size_kb = os.path.getsize(ss_path) / 1024
        print(f"  File size: {file_size_kb:.1f} KB")

        # Call DeepSeek
        print(f"  Calling DeepSeek vision API...")
        t0 = time.time()
        ai_elements = call_deepseek_vision(
            ss_path, gt["page_name"], gt["folder"],
        )
        elapsed = time.time() - t0
        print(f"  Response time: {elapsed:.1f}s")
        print(f"  AI detected: {len(ai_elements)} elements")

        if ai_elements:
            for el in ai_elements[:5]:
                print(f"    - {el.get('label', '?')} ({el.get('type', '?')}) "
                      f"confidence={el.get('confidence', '?')}")

        # Evaluate
        eval_result = evaluate_page(pid, gt["elements"], ai_elements)
        results.append(eval_result)

        print(f"\n  [EVAL] Precision={eval_result.precision:.1%} "
              f"Recall={eval_result.recall:.1%} F1={eval_result.f1:.1%}")
        print(f"  True Positives ({len(eval_result.true_positives)}): "
              f"{eval_result.true_positives[:5]}..."
              if len(eval_result.true_positives) > 5 else
              f"{eval_result.true_positives}")
        if eval_result.false_positives:
            print(f"  False Positives ({len(eval_result.false_positives)}): "
                  f"{eval_result.false_positives[:5]}..."
                  if len(eval_result.false_positives) > 5 else
                  f"{eval_result.false_positives}")
        if eval_result.false_negatives:
            print(f"  False Negatives ({len(eval_result.false_negatives)}): "
                  f"{eval_result.false_negatives[:5]}..."
                  if len(eval_result.false_negatives) > 5 else
                  f"{eval_result.false_negatives}")

    # ── Summary ──
    print(f"\n{'=' * 70}")
    print("SUMMARY")
    print(f"{'=' * 70}")

    if not results:
        print("\n[ABORT] No pages were evaluated.")
        return 1

    print(f"\n{'Page':<35} {'GT':>5} {'AI':>5} {'Prec':>6} {'Rec':>6} {'F1':>6} {'Verdict'}")
    print(f"{'-'*35} {'-'*5} {'-'*5} {'-'*6} {'-'*6} {'-'*6} {'-'*7}")
    for r in results:
        verdict = "PASS" if r.passed else "FAIL"
        print(f"{r.page_name:<35} {r.ground_truth_count:>5} {r.ai_detected_count:>5} "
              f"{r.precision:>6.1%} {r.recall:>6.1%} {r.f1:>6.1%} {verdict:>7}")

    # Aggregate metrics
    avg_precision = sum(r.precision for r in results) / len(results)
    avg_recall = sum(r.recall for r in results) / len(results)
    avg_f1 = sum(r.f1 for r in results) / len(results)
    pass_count = sum(1 for r in results if r.passed)

    print(f"\n{'─'*70}")
    print(f"  Average Precision: {avg_precision:.1%}")
    print(f"  Average Recall:    {avg_recall:.1%}")
    print(f"  Average F1:         {avg_f1:.1%}")
    print(f"  Pages passing (F1 >= 50%): {pass_count}/{len(results)}")

    # Decision
    print(f"\n{'=' * 70}")
    if avg_f1 >= 0.50:
        print("DECISION: CONTINUE WITH AI")
        print("  AI interaction recognition meets the >= 50% F1 threshold.")
        print("  Proceed with NavigatesToExtractor using DeepSeek multimodal as primary strategy.")
        print("  Recommendation: Combine AI with CV heuristic (color/contrast-based")
        print("  hotspot detection) as fallback for low-confidence detections.")
    else:
        print("DECISION: FALLBACK TO CV + MANUAL")
        print("  AI interaction recognition does NOT meet the >= 50% F1 threshold.")
        print("  Downgrade strategy: use CV heuristic detection (edge detection,")
        print("  contrast analysis) as primary, with manual annotation UI as fallback.")
        print("  Keep AI as optional enhancement for high-contrast pages only.")

    print(f"{'=' * 70}")

    # Save detailed results
    out_path = BACKEND_DIR / "data" / "poc_interaction_results.json"
    summary = {
        "model": DEEPSEEK_MODEL,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "threshold": 0.50,
        "results": [
            {
                "page_id": r.page_id,
                "page_name": r.page_name,
                "gt_count": r.ground_truth_count,
                "ai_count": r.ai_detected_count,
                "tp": r.true_positives,
                "fp": r.false_positives,
                "fn": r.false_negatives,
                "precision": r.precision,
                "recall": r.recall,
                "f1": r.f1,
                "passed": r.passed,
            }
            for r in results
        ],
        "aggregate": {
            "avg_precision": round(avg_precision, 3),
            "avg_recall": round(avg_recall, 3),
            "avg_f1": round(avg_f1, 3),
            "pass_count": pass_count,
            "total": len(results),
            "decision": "CONTINUE_WITH_AI" if avg_f1 >= 0.50 else "FALLBACK_TO_CV_MANUAL",
        },
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"\nDetailed results saved to: {out_path}")

    return 0 if avg_f1 >= 0.50 else 2


if __name__ == "__main__":
    raise SystemExit(main())
