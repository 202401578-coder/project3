# 🇺🇸 미국장 담당 팀원을 위한 연동 가이드

> 이 문서는 프로젝트에 **미국 주식(빅테크, 반도체 등)** 기능을 추가/확장할 팀원을 위한 개발 가이드입니다.

---

## 📌 현재 아키텍처 개요
- **파이프라인 실행:** `main.py`가 실행되면 국장(삼성전자, SK하이닉스)과 미장 데이터를 동시에 수집합니다.
- **배포 및 리포트:**
  - `README.md` 메인 대시보드 자동 갱신
  - `index.html` GitHub Pages 웹사이트([링크](https://hanjisubusiness22222.github.io/project3/)) 실시간 렌더링
  - `reports/latest.md` 및 일자별 아카이빙 파일 자동 저장

---

## 🛠️ 팀원이 수정/추가할 수 있는 부분

### 1. 관심 종목 추가 및 변경 (`main.py`)
`main.py`의 상단에 위치한 `TARGET_US_STOCKS` 리스트에 원하는 티커와 한글명을 자유롭게 추가하시면 됩니다:

```python
# main.py 상단
TARGET_US_STOCKS = [
    {"name": "엔비디아", "ticker": "NVDA"},
    {"name": "애플", "ticker": "AAPL"},
    {"name": "마이크로소프트", "ticker": "MSFT"},
    {"name": "TSMC", "ticker": "TSM"},        # 추가 예시
    {"name": "마이크론", "ticker": "MU"},         # 추가 예시
]
```

### 2. 시세 수집 엔진 (`get_us_stock_quote`)
- 현재 가볍고 빠른 Yahoo Finance Chart API (`query1.finance.yahoo.com/v8/finance/chart/{ticker}`)를 통해 실시간 시세(현재가, 전일비, 등락률, 고가, 저가, 거래량)를 수집하도록 기본 모듈이 탑재되어 있습니다.
- 만약 `yfinance` 라이브러리나 Finnhub, Alpha Vantage 등 외부 API 키를 도입하고자 한다면 `get_us_stock_quote` 함수 내부만 변경하시면 됩니다.

### 3. 미국 주식 뉴스 피드 확장 (`get_stock_news`)
- 미국 종목 뉴스도 수집하고 싶다면 `get_stock_news(query="NVIDIA stock", lang="en")` 형태로 호출하시면 영문 글로벌 뉴스를 손쉽게 가져올 수 있습니다.

---

## 🧪 로컬 테스트 방법
```bash
# 가상환경 또는 로컬 터미널
pip install -r requirements.txt
python main.py
```
실행 후 `index.html`을 더블클릭하여 브라우저에서 열면 변경된 카드들이 즉시 반영된 것을 확인하실 수 있습니다.
