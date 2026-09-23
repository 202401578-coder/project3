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

        # 주요 지표 추출
        total_infos = {item["code"]: item["value"] for item in data.get("totalInfos", [])}
        
        # basic 정보 조회 (등락 상태 파악)
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
            "open_price": "-",
            "high_price": "-",
            "low_price": "-",
            "volume": "-",
            "market_cap": "-",
        }

def get_stock_news(query: str, max_count: int = 4) -> list:
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
            
            # 언론사 추출 (보통 '제목 - 언론사' 포맷)
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

def build_markdown_report(stocks_data: list) -> str:
    """마크다운 포맷 브리핑 리포트 생성"""
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    now_kst = now_utc + datetime.timedelta(hours=9)
    date_str = now_kst.strftime("%Y-%m-%d %H:%M:%S KST")

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
    else:
        print("README.md에 리포트 태그가 없어 대시보드 삽입을 건너뜁니다.")

def send_discord_alert(report_md: str, webhook_url: str):
    """(선택) 디스코드 웹훅으로 메시지 전송"""
    if not webhook_url:
        return
    try:
        # 디스코드 메시지 최대 2000자 제한 대응
        payload = {
            "content": report_md[:1950]
        }
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

    # 마크다운 리포트 생성
    report_md = build_markdown_report(stocks_data)
    print("\n--- 생성된 브리핑 리포트 ---")
    print(report_md)

    # reports 디렉토리에 저장
    os.makedirs("reports", exist_ok=True)
    
    # 1) latest.md
    with open("reports/latest.md", "w", encoding="utf-8") as f:
        f.write(report_md)

    # 2) 날짜별 파일 저장 (KST 기준)
    now_kst = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=9)
    today_filename = f"reports/{now_kst.strftime('%Y-%m-%d')}.md"
    with open(today_filename, "w", encoding="utf-8") as f:
        f.write(report_md)

    # 3) README.md 자동 업데이트
    update_readme_dashboard(report_md)

    # 4) 디스코드 웹훅 전송 (환경변수 세팅되어 있는 경우)
    discord_webhook = os.getenv("DISCORD_WEBHOOK_URL")
    if discord_webhook:
        send_discord_alert(report_md, discord_webhook)

    print("\n=== 모든 작업 완료 ===")

if __name__ == "__main__":
    main()
