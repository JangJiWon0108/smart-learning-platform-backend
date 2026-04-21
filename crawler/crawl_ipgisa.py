#!/usr/bin/env python3
"""
정보처리기사 실기 기출문제 크롤러
Source: chobopark.tistory.com
Output: data/ipgisa_questions.jsonl
"""
from __future__ import annotations

import json
import time
import re
import urllib.request
import urllib.error
from bs4 import BeautifulSoup, NavigableString, Tag
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple

# ──────────────────────────────────────────
# 시험 목록 (year, round, url)
# ──────────────────────────────────────────
EXAMS = [
    # 2020 (4회)
    (2020, 1, "https://chobopark.tistory.com/196"),
    (2020, 2, "https://chobopark.tistory.com/195"),
    (2020, 3, "https://chobopark.tistory.com/194"),
    (2020, 4, "https://chobopark.tistory.com/192"),
    # 2021 (3회)
    (2021, 1, "https://chobopark.tistory.com/191"),
    (2021, 2, "https://chobopark.tistory.com/210"),
    (2021, 3, "https://chobopark.tistory.com/217"),
    # 2022 (3회)
    (2022, 1, "https://chobopark.tistory.com/271"),
    (2022, 2, "https://chobopark.tistory.com/423"),
    (2022, 3, "https://chobopark.tistory.com/424"),
    # 2023 (3회)
    (2023, 1, "https://chobopark.tistory.com/372"),
    (2023, 2, "https://chobopark.tistory.com/420"),
    (2023, 3, "https://chobopark.tistory.com/453"),
    # 2024 (3회)
    (2024, 1, "https://chobopark.tistory.com/476"),
    (2024, 2, "https://chobopark.tistory.com/483"),
    (2024, 3, "https://chobopark.tistory.com/495"),
    # 2025 (3회)
    (2025, 1, "https://chobopark.tistory.com/540"),
    (2025, 2, "https://chobopark.tistory.com/554"),
    (2025, 3, "https://chobopark.tistory.com/558"),
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "ko-KR,ko;q=0.9",
}


def fetch_html(url: str) -> str:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.read().decode("utf-8")


def clean_text(text: str) -> str:
    text = text.replace("\xa0", " ").replace("&nbsp;", " ")
    text = re.sub(r" {2,}", " ", text)
    return text.strip()


def extract_images(container: Tag) -> List[Dict[str, str]]:
    imgs = []
    for img in container.find_all("img"):
        src = img.get("src") or img.get("data-src") or ""
        if not src:
            continue
        imgs.append({
            "src": src,
            "alt": img.get("alt", ""),
            "width": img.get("width", ""),
            "height": img.get("height", ""),
        })
    return imgs


def is_code_table(table: Tag) -> bool:
    """코드 하이라이터 테이블 여부 판별."""
    classes = table.get("class") or []
    if "colorscripter-code-table" in classes:
        return True
    style = table.get("style", "")
    if "#fafafa" in style or "fafafa" in style.lower():
        return True
    return False


def extract_code_table(table: Tag) -> str:
    """
    코드 하이라이터 테이블에서 코드만 추출.
    구조: td[0]=줄번호, td[1]=코드내용, (td[2]=언어식별자)
    """
    tbody = table.find("tbody") or table
    trs = tbody.find_all("tr", recursive=False)
    if not trs:
        return clean_text(table.get_text(separator="\n"))
    tr = trs[0]
    tds = tr.find_all("td", recursive=False)
    if len(tds) < 2:
        return clean_text(table.get_text(separator="\n"))

    lang = clean_text(tds[-1].get_text()) if len(tds) >= 3 else ""
    # 언어 식별자 td는 짧은 텍스트 (cs, java, python 등)
    if lang and len(lang) > 10:
        lang = ""

    code_td = tds[1]
    # 각 라인 div를 줄 단위로 결합
    line_divs = code_td.find_all("div", recursive=False)
    if line_divs:
        lines = []
        for div in line_divs:
            line = div.get_text(separator="").replace("\xa0", " ").rstrip()
            lines.append(line)
        code = "\n".join(lines).strip()
    else:
        code = clean_text(code_td.get_text(separator="\n"))

    if lang:
        return f"[{lang}]\n{code}"
    return code


def find_code_table(node: Tag):
    """node 내에서 첫 번째 코드 테이블을 반환 (없으면 None)."""
    for table in node.find_all("table"):
        if is_code_table(table):
            return table
    return None


def node_to_text(node) -> str:
    """Tag or NavigableString → clean text."""
    if isinstance(node, NavigableString):
        return clean_text(str(node))
    if isinstance(node, Tag):
        if node.name == "table":
            if is_code_table(node):
                return extract_code_table(node)
            # 일반 표: 행 단위 변환
            rows = []
            for tr in node.find_all("tr"):
                cells = [clean_text(td.get_text(separator=" ")) for td in tr.find_all(["td", "th"])]
                row = " | ".join(c for c in cells if c)
                if row:
                    rows.append(row)
            return "\n".join(rows)
        if node.name == "div":
            # 코드 래퍼 div 감지: 내부에 코드 테이블 포함 여부
            code_table = find_code_table(node)
            if code_table:
                return extract_code_table(code_table)
        return clean_text(node.get_text(separator="\n"))
    return ""


def split_answer_explanation(ml_div: Tag) -> Tuple[str, str]:
    """
    moreless-content 내 정답(#009a87)과 해설(#006dd7) 분리.
    색상 기준:
      청록(#009a87, rgb(0,154,135), #00897b 등) → 정답
      파랑(#006dd7, rgb(0,109,215)) → 해설
    색상 없는 텍스트는 정답이 없으면 정답으로, 있으면 해설로.
    """
    content_div = ml_div.find("div", class_="moreless-content")
    if not content_div:
        return "", ""

    GREEN_RE = re.compile(r"#009a87|#00897b|#00b4a4|rgb\(0,\s*1[45]\d", re.I)
    BLUE_RE  = re.compile(r"#006dd7|#0070d1|rgb\(0,\s*1[01]\d", re.I)

    answer_parts: List[str] = []
    explanation_parts: List[str] = []

    def collect(node, depth=0):
        if isinstance(node, NavigableString):
            txt = clean_text(str(node))
            if not txt:
                return
            # 부모 체인 전체에서 모든 color 수집 (조상 우선순위: 녹색 > 파랑)
            has_green = False
            has_blue = False
            parent = node.parent
            while parent and parent != content_div:
                s = parent.get("style", "") if isinstance(parent, Tag) else ""
                if "color" in s:
                    if GREEN_RE.search(s):
                        has_green = True
                    elif BLUE_RE.search(s):
                        has_blue = True
                parent = parent.parent

            if has_green:
                answer_parts.append(txt)
            elif has_blue:
                explanation_parts.append(txt)
            else:
                if answer_parts:
                    explanation_parts.append(txt)
                else:
                    answer_parts.append(txt)
        elif isinstance(node, Tag):
            if node.name in ("script", "style"):
                return
            for child in node.children:
                collect(child, depth + 1)

    for child in content_div.children:
        collect(child)

    return "\n".join(answer_parts).strip(), "\n".join(explanation_parts).strip()


def find_body(soup: BeautifulSoup) -> Optional[Tag]:
    """실제 문제 본문 컨테이너를 반환."""
    # 1순위: tt_article_useless_p_margin (tistory 본문 컨테이너)
    body = soup.find("div", class_="tt_article_useless_p_margin")
    if body:
        return body
    # 2순위: contents_style
    body = soup.find("div", class_="contents_style")
    if body:
        return body
    # 3순위: entry-content
    return soup.find(class_="entry-content")


def is_moreless(node) -> bool:
    return (
        isinstance(node, Tag)
        and node.get("data-ke-type") == "moreLess"
    )


def nodes_before_moreless(wrapper: Tag) -> List[Any]:
    """wrapper div 안에서 moreLess div 이전 노드들만 반환."""
    result = []
    for child in wrapper.children:
        if is_moreless(child):
            break
        result.append(child)
    return result


def parse_exam_page(html: str, year: int, round_: int, url: str) -> List[Dict[str, Any]]:
    soup = BeautifulSoup(html, "lxml")
    body = find_body(soup)
    if not body:
        print(f"  [WARN] body not found: {url}")
        return []

    # 페이지 제목 추출
    title_tag = body.find(["h2", "h3", "h4"])
    page_title = clean_text(title_tag.get_text()) if title_tag else f"{year}년 {round_}회"

    # 순차 탐색: h3 이후부터 수집
    h3_passed = False
    current_q_nodes: List[Any] = []
    question_blocks: List[Tuple[List[Any], Tag]] = []  # (question_nodes, moreless_div)

    for child in body.children:
        if not h3_passed:
            if isinstance(child, Tag) and child.name in ("h2", "h3", "h4"):
                h3_passed = True
            continue

        if is_moreless(child):
            # 직접 moreLess: 누적된 노드가 문제 텍스트
            question_blocks.append((current_q_nodes, child))
            current_q_nodes = []
        elif isinstance(child, Tag) and child.find("div", attrs={"data-ke-type": "moreLess"}):
            # 래퍼 div: 안에 코드표 + moreLess 포함
            inner_ml = child.find("div", attrs={"data-ke-type": "moreLess"})
            pre_nodes = nodes_before_moreless(child)
            question_blocks.append((current_q_nodes + pre_nodes, inner_ml))
            current_q_nodes = []
        else:
            current_q_nodes.append(child)

    questions = []

    for i, (q_nodes, ml_div) in enumerate(question_blocks):
        # 문제 텍스트 + 이미지 수집
        text_parts: List[str] = []
        q_images: List[Dict] = []

        for node in q_nodes:
            if isinstance(node, NavigableString):
                t = clean_text(str(node))
                if t:
                    text_parts.append(t)
            elif isinstance(node, Tag):
                q_images.extend(extract_images(node))
                t = node_to_text(node)
                if t:
                    text_parts.append(t)

        # 연속 빈줄 정리
        lines: List[str] = []
        for block in text_parts:
            for line in block.split("\n"):
                line = line.strip()
                if line:
                    lines.append(line)

        q_text = "\n".join(lines)

        # 문제 번호: 텍스트 앞에서 추출, 없으면 순서로
        q_num = i + 1
        m = re.match(r"^\s*(\d+)\s*[.．]\s*", q_text)
        if m:
            q_num = int(m.group(1))

        # 정답 + 해설
        answer, explanation = split_answer_explanation(ml_div)

        # moreless 안 이미지 (답안 다이어그램 등)
        answer_images = extract_images(ml_div)

        q_id = f"{year}_{round_:02d}_{q_num:02d}"

        questions.append({
            "id": q_id,
            "year": year,
            "round": round_,
            "exam_title": page_title,
            "question_number": q_num,
            "question": q_text,
            "images": q_images,
            "answer": answer,
            "answer_images": answer_images,
            "explanation": explanation,
            "source_url": url,
            "crawled_at": datetime.utcnow().isoformat() + "Z",
        })

    return questions


def main():
    out_dir = Path(__file__).parent.parent / "data"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "정보처리기사_실기_기출문제.jsonl"

    total = 0
    errors = []

    with out_path.open("w", encoding="utf-8") as fout:
        for year, round_, url in EXAMS:
            print(f"Fetching {year}년 {round_}회 ... {url}")
            try:
                html = fetch_html(url)
            except Exception as e:
                print(f"  [ERROR] fetch failed: {e}")
                errors.append((year, round_, url, str(e)))
                time.sleep(2)
                continue

            questions = parse_exam_page(html, year, round_, url)
            print(f"  -> {len(questions)} questions parsed")

            for q in questions:
                fout.write(json.dumps(q, ensure_ascii=False) + "\n")
            total += len(questions)

            time.sleep(1.5)

    print(f"\nDone. {total} questions saved to {out_path}")
    if errors:
        print(f"Errors ({len(errors)}):")
        for e in errors:
            print(f"  {e}")


if __name__ == "__main__":
    main()
