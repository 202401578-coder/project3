import os
import sys
import json
import re
import datetime
import xml.etree.ElementTree as ET
import requests

# Windows 콘솔 및 다양한 환경에서 utf-8 이모지/한글 출력 지원
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

TARGET_STOCKS = [
    {"name": "삼성전자", "code": "005930"},
    {"name": "SK하이닉스", "code": "000660"},
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def get_stock_quote(code: str) -> dict:
    """네이버 모바일 증권 API를 통해 주가 시세 정보 조회"""
    try:
        url = f"https://m.stock.naver.com/api/stock/{code}/integration"
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        total_infos = {item["code"]: item["value"] for item in data.get("totalInfos", [])}
        
        basic_url = f"https://m.stock.naver.com/api/stock/{code}/basic"
        basic_resp = requests.get(basic_url, headers=HEADERS, timeout=10)
        basic_data = basic_resp.json() if basic_resp.status_code == 200 else {}

        close_price = basic_data.get("closePrice", total_infos.get("closePrice", "0"))
        diff_price = basic_data.get("compareToPreviousClosePrice", "0")
        diff_ratio = basic_data.get("fluctuationsRatio", "0.00")
        compare_info = basic_data.get("compareToPreviousPrice", {})
        compare_type = compare_info.get("name", "")

        sign = "▲" if compare_type == "RISING" else ("▼" if compare_type == "FALLING" else "-")

        return {
            "name": basic_data.get("stockName", data.get("stockName", code)),
            "code": code,
            "close_price": close_price,
            "diff_price": diff_price,
            "diff_ratio": diff_ratio,
            "sign": sign,
            "direction": "up" if sign == "▲" else ("down" if sign == "▼" else "flat"),
            "open_price": total_infos.get("openPrice", "-"),
            "high_price": total_infos.get("highPrice", "-"),
            "low_price": total_infos.get("lowPrice", "-"),
            "volume": total_infos.get("accumulatedTradingVolume", "-"),
            "market_cap": total_infos.get("marketValue", "-"),
        }
    except Exception as e:
        print(f"[{code}] 주가 정보 조회 실패: {e}")
        return {
            "name": code,
            "code": code,
            "close_price": "-",
            "diff_price": "-",
            "diff_ratio": "-",
            "sign": "-",
            "direction": "flat",
            "open_price": "-",
            "high_price": "-",
            "low_price": "-",
            "volume": "-",
            "market_cap": "-",
        }

def get_stock_news(query: str, max_count: int = 5) -> list:
    """Google News RSS (한국어)를 통해 특정 종목 최신 뉴스 수집"""
    try:
        encoded_query = requests.utils.quote(f"{query} 주식 OR 반도체 OR 실적")
        rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=ko&gl=KR&ceid=KR:ko"
        resp = requests.get(rss_url, headers=HEADERS, timeout=10)
        resp.raise_for_status()

        root = ET.fromstring(resp.content)
        news_items = []
        for item in root.findall(".//item")[:max_count]:
            raw_title = item.find("title").text or ""
            link = item.find("link").text or ""
            pub_date = item.find("pubDate").text or ""
            
            parts = raw_title.rsplit(" - ", 1)
            title = parts[0]
            publisher = parts[1] if len(parts) > 1 else "언론사"

            news_items.append({
                "title": title,
                "publisher": publisher,
                "link": link,
                "pub_date": pub_date
            })
        return news_items
    except Exception as e:
        print(f"[{query}] 뉴스 수집 실패: {e}")
        return []

def build_markdown_report(stocks_data: list, date_str: str) -> str:
    """마크다운 포맷 브리핑 리포트 생성"""
    md = []
    md.append(f"## 📊 [브리핑] 국장 반도체(삼성전자·SK하이닉스) 시세 및 뉴스")
    md.append(f"> 기준 일시: **{date_str}**  *(GitHub Actions 자동 생성)*\n")

    # 1. 주가 요약 표
    md.append("### 📈 주가 요약")
    md.append("| 종목명 | 종목코드 | 현재가 (원) | 전일대비 | 등락률 | 시가 | 고가 | 저가 | 거래량(주) |")
    md.append("| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |")
    for s in stocks_data:
        quote = s["quote"]
        sign_color = "🔴" if quote["sign"] == "▲" else ("🔵" if quote["sign"] == "▼" else "⚪")
        diff_str = f"{sign_color} {quote['sign']} {quote['diff_price']}"
        ratio_str = f"{quote['diff_ratio']}%"
        md.append(f"| **{quote['name']}** | `{quote['code']}` | **{quote['close_price']}** | {diff_str} | {ratio_str} | {quote['open_price']} | {quote['high_price']} | {quote['low_price']} | {quote['volume']} |")
    md.append("")

    # 2. 종목별 최신 뉴스
    md.append("### 📰 최신 주요 뉴스")
    for s in stocks_data:
        quote = s["quote"]
        news_list = s["news"]
        md.append(f"#### 🔹 {quote['name']} (`{quote['code']}`)")
        if news_list:
            for item in news_list:
                md.append(f"- [{item['title']}]({item['link']}) `[{item['publisher']}]`")
        else:
            md.append("- 최신 뉴스를 가져오지 못했습니다.")
        md.append("")

    return "\n".join(md)

def update_readme_dashboard(report_md: str):
    """README.md 내의 특정 주석 구간을 최신 리포트로 갱신"""
    readme_path = "README.md"
    if not os.path.exists(readme_path):
        return

    with open(readme_path, "r", encoding="utf-8") as f:
        content = f.read()

    start_tag = "<!-- STOCK_REPORT_START -->"
    end_tag = "<!-- STOCK_REPORT_END -->"

    pattern = re.compile(rf"{re.escape(start_tag)}[\s\S]*?{re.escape(end_tag)}")
    replacement = f"{start_tag}\n\n{report_md}\n\n{end_tag}"

    if pattern.search(content):
        new_content = pattern.sub(replacement, content)
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        print("README.md 대시보드 업데이트 완료.")

def generate_html_dashboard(stocks_data: list, date_str: str):
    """GitHub Pages용 모던 웹 대시보드 index.html 자동 생성"""
    
    # HTML 카드 생성
    stock_cards_html = ""
    news_sections_html = ""

    for s in stocks_data:
        q = s["quote"]
        news_list = s["news"]
        is_up = q["direction"] == "up"
        is_down = q["direction"] == "down"
        
        badge_class = "bg-rose-500/10 text-rose-500 border-rose-500/20" if is_up else (
            "bg-sky-500/10 text-sky-500 border-sky-500/20" if is_down else "bg-slate-500/10 text-slate-400 border-slate-500/20"
        )
        sign_symbol = "▲" if is_up else ("▼" if is_down else "-")

        stock_cards_html += f"""
        <div class="bg-slate-800/80 border border-slate-700/60 rounded-2xl p-6 shadow-xl backdrop-blur-sm hover:border-slate-600 transition-all">
          <div class="flex items-center justify-between mb-4">
            <div>
              <span class="text-xs font-semibold px-2.5 py-1 rounded-md bg-slate-700 text-slate-300 mr-2">{q["code"]}</span>
              <h3 class="text-2xl font-bold text-white inline">{q["name"]}</h3>
            </div>
            <span class="inline-flex items-center gap-1 text-sm font-semibold px-3 py-1 rounded-full border {badge_class}">
              {sign_symbol} {q["diff_price"]}원 ({q["diff_ratio"]}%)
            </span>
          </div>
          
          <div class="mb-6">
            <div class="text-xs text-slate-400 font-medium">현재가</div>
            <div class="text-4xl font-extrabold text-white tracking-tight">{q["close_price"]} <span class="text-xl font-normal text-slate-400">원</span></div>
          </div>

          <div class="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs bg-slate-900/50 p-4 rounded-xl border border-slate-700/40">
            <div><span class="text-slate-500 block">시가</span><span class="font-medium text-slate-200">{q["open_price"]}</span></div>
            <div><span class="text-slate-500 block">고가</span><span class="font-medium text-rose-400">{q["high_price"]}</span></div>
            <div><span class="text-slate-500 block">저가</span><span class="font-medium text-sky-400">{q["low_price"]}</span></div>
            <div><span class="text-slate-500 block">거래량</span><span class="font-medium text-slate-200">{q["volume"]}주</span></div>
          </div>
        </div>
        """

        # 뉴스 리스트 렌더링
        news_items_html = ""
        for n in news_list:
            news_items_html += f"""
            <a href="{n['link']}" target="_blank" rel="noopener noreferrer" class="group block p-4 rounded-xl bg-slate-800/50 border border-slate-700/40 hover:bg-slate-700/50 hover:border-indigo-500/50 transition-all">
              <div class="flex items-start justify-between gap-3">
                <div class="text-sm font-medium text-slate-200 group-hover:text-indigo-400 leading-snug line-clamp-2">{n['title']}</div>
                <span class="shrink-0 text-xs px-2 py-0.5 rounded bg-slate-900/80 text-slate-400 border border-slate-700/40 font-mono">{n['publisher']}</span>
              </div>
            </a>
            """

        news_sections_html += f"""
        <div class="mb-8">
          <div class="flex items-center gap-2 mb-4">
            <div class="w-2.5 h-2.5 rounded-full bg-indigo-500"></div>
            <h4 class="text-lg font-bold text-white">{q["name"]} 최신 뉴스</h4>
          </div>
          <div class="space-y-3">
            {news_items_html}
          </div>
        </div>
        """

    html_template = f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>국장 반도체 브리핑 | 삼성전자 & SK하이닉스</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Pretendard:wght@300;400;600;700;800&display=swap" rel="stylesheet">
  <style>
    body {{ font-family: 'Pretendard', sans-serif; }}
  </style>
</head>
<body class="bg-slate-950 text-slate-100 min-h-screen antialiased selection:bg-indigo-500 selection:text-white">

  <!-- Background Decorative Gradient -->
  <div class="fixed inset-0 pointer-events-none z-0 overflow-hidden">
    <div class="absolute -top-40 -left-40 w-96 h-96 bg-indigo-600/15 rounded-full blur-3xl"></div>
    <div class="absolute top-1/3 -right-40 w-96 h-96 bg-rose-600/10 rounded-full blur-3xl"></div>
  </div>

  <div class="relative z-10 max-w-5xl mx-auto px-4 py-10 sm:py-16">
    <!-- Header -->
    <header class="mb-10 text-center sm:text-left sm:flex sm:items-end sm:justify-between border-b border-slate-800/80 pb-8">
      <div>
        <div class="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 text-xs font-semibold mb-3">
          <span class="relative flex h-2 w-2">
            <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-indigo-400 opacity-75"></span>
            <span class="relative inline-flex rounded-full h-2 w-2 bg-indigo-500"></span>
          </span>
          GitHub Actions 자동 갱신 중
        </div>
        <h1 class="text-3xl sm:text-4xl font-extrabold text-white tracking-tight">국장 반도체 브리핑</h1>
        <p class="text-slate-400 text-sm mt-1">삼성전자 & SK하이닉스 일일 시세 및 주요 뉴스 대시보드</p>
      </div>

      <div class="mt-6 sm:mt-0 flex flex-wrap items-center gap-3 justify-center sm:justify-end">
        <div class="text-xs text-slate-400 font-mono bg-slate-900 border border-slate-800 px-3 py-1.5 rounded-lg">
          기준: {date_str}
        </div>
        <a href="https://github.com/hanjisubusiness22222/project3" target="_blank" class="text-xs font-semibold px-4 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white transition-all shadow-lg shadow-indigo-600/20">
          GitHub 레포 ↗
        </a>
      </div>
    </header>

    <!-- Stock Cards Grid -->
    <section class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-12">
      {stock_cards_html}
    </section>

    <!-- Content Sections (News & Comparison) -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
      <!-- News Column (2 cols) -->
      <section class="lg:col-span-2">
        <h3 class="text-xl font-bold text-white mb-6 flex items-center gap-2">
          <span>📰</span> 실시간 주요 뉴스
        </h3>
        {news_sections_html}
      </section>

      <!-- Side Column: US Market Comparison Highlight -->
      <section class="lg:col-span-1">
        <div class="sticky top-6 bg-gradient-to-br from-slate-900 to-indigo-950/40 border border-indigo-500/20 rounded-2xl p-6 shadow-xl">
          <span class="text-xs font-bold uppercase tracking-wider text-indigo-400 block mb-2">💡 심층 분석 요약</span>
          <h3 class="text-lg font-bold text-white mb-3">미국장이 더 좋은가?</h3>
          <p class="text-xs text-slate-300 leading-relaxed mb-4">
            엔지니어링(API 무료 생태계)과 펀더멘털(자사주 소각·주주환원, AI 칩 독점력, 달러 환율 방어) 측면에서 <strong>미국장이 확실히 우위</strong>에 있습니다.
          </p>
          <ul class="text-xs text-slate-400 space-y-2 mb-6">
            <li class="flex items-start gap-2">
              <span class="text-emerald-400">✓</span> <span><strong>자본 환원:</strong> 美 빅테크는 이익 증가 시 자사주 소각으로 주가 부양</span>
            </li>
            <li class="flex items-start gap-2">
              <span class="text-emerald-400">✓</span> <span><strong>플랫폼 권력:</strong> 엔비디아(마진 70%) vs 메모리 공급사</span>
            </li>
            <li class="flex items-start gap-2">
              <span class="text-emerald-400">✓</span> <span><strong>달러 자산:</strong> 경제 위기 시 환차익 헷지 기능</span>
            </li>
          </ul>
          <a href="https://github.com/hanjisubusiness22222/project3/blob/main/market_review_and_feasibility.md" target="_blank" class="block w-full text-center py-2.5 px-4 rounded-xl bg-slate-800 hover:bg-slate-700 text-white font-medium text-xs border border-slate-700/80 transition-all">
            전체 비교 보고서 읽기 📄
          </a>
        </div>
      </section>
    </div>

    <!-- Footer -->
    <footer class="mt-16 pt-8 border-t border-slate-900 text-center text-xs text-slate-500">
      <p>Powered by GitHub Actions & Pages · 매일 장 마감 후 자동 갱신됩니다.</p>
    </footer>
  </div>

</body>
</html>
"""
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_template)
    print("index.html 대시보드 웹페이지 생성 완료.")

def send_discord_alert(report_md: str, webhook_url: str):
    """(선택) 디스코드 웹훅으로 메시지 전송"""
    if not webhook_url:
        return
    try:
        payload = {"content": report_md[:1950]}
        res = requests.post(webhook_url, json=payload, timeout=10)
        print(f"디스코드 웹훅 전송 결과: {res.status_code}")
    except Exception as e:
        print(f"디스코드 웹훅 전송 실패: {e}")

def main():
    print("=== [삼성전자 & SK하이닉스 주식/뉴스 수집 시작] ===")
    stocks_data = []
    for stock in TARGET_STOCKS:
        print(f"[{stock['name']}] 시세 및 뉴스 수집 중...")
        quote = get_stock_quote(stock["code"])
        news = get_stock_news(stock["name"], max_count=4)
        stocks_data.append({
            "quote": quote,
            "news": news
        })

    now_utc = datetime.datetime.now(datetime.timezone.utc)
    now_kst = now_utc + datetime.timedelta(hours=9)
    date_str = now_kst.strftime("%Y-%m-%d %H:%M:%S KST")

    # 1. 마크다운 리포트 생성
    report_md = build_markdown_report(stocks_data, date_str)

    # 2. reports 디렉토리 저장
    os.makedirs("reports", exist_ok=True)
    with open("reports/latest.md", "w", encoding="utf-8") as f:
        f.write(report_md)
    today_filename = f"reports/{now_kst.strftime('%Y-%m-%d')}.md"
    with open(today_filename, "w", encoding="utf-8") as f:
        f.write(report_md)

    # 3. README.md 자동 업데이트
    update_readme_dashboard(report_md)

    # 4. GitHub Pages용 모던 웹 대시보드 index.html 생성
    generate_html_dashboard(stocks_data, date_str)

    # 5. 디스코드 웹훅 전송 (환경변수 세팅되어 있는 경우)
    discord_webhook = os.getenv("DISCORD_WEBHOOK_URL")
    if discord_webhook:
        send_discord_alert(report_md, discord_webhook)

    print("\n=== 모든 작업 완료 ===")

if __name__ == "__main__":
    main()
