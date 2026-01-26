# MacroAgent_V3 - Claude Code 실행 가이드
# ==========================================

## 📁 프로젝트 구조 (생성 완료)
```
MacroAgent_V3/
├── requirements.txt      # 의존성 (버전 고정됨)
├── config.py             # 설정 (환경변수 지원)
├── main.py               # 메인 실행 파일
├── modules/
│   ├── __init__.py       # 패키지 초기화
│   ├── schemas.py        # Pydantic 스키마
│   ├── fetcher.py        # 데이터 수집 (Rate Limiting 적용)
│   ├── processor.py      # 데이터 처리 (버그 수정됨)
│   ├── filter.py         # 필터 엔진 (로직 개선됨)
│   └── reporter.py       # 리포트 생성
└── output/               # 리포트 저장소
```

---

## 🚀 Claude Code 설치 명령어

아래 명령어를 순서대로 실행하세요:

```bash
# 1. 프로젝트 디렉토리로 이동
cd ~/MacroAgent_V3

# 2. 가상환경 생성 (권장)
python3 -m venv venv
source venv/bin/activate

# 3. 의존성 설치
pip install -r requirements.txt

# 4. FRED API 키 설정 (필수!)
export FRED_API_KEY="여기에_본인의_FRED_API_키_입력"

# 5. 실행
python main.py
```

---

## ⚙️ 수정 사항 요약 (원본 대비)

### 버그 수정
1. **processor.py - acc_weight 미사용 버그**
   - 기존: 선언만 하고 사용 안 함
   - 수정: priority_score 계산에 실제 반영

2. **fetcher.py - CoinGecko 인덱스 문제**
   - 기존: 타임스탬프 없이 값만 반환
   - 수정: pd.to_datetime으로 적절한 인덱스 생성

3. **processor.py - freshness 계산 불안정**
   - 수정: try-except로 안정화

### 로직 개선
4. **filter.py - 가속도 판단 기준**
   - 기존: value 대비 acceleration
   - 수정: velocity 대비 acceleration (더 의미있음)

5. **config.py - 환경변수 지원**
   - os.getenv()로 보안 강화

6. **fetcher.py - Rate Limiting 강화**
   - FRED: 0.5초, YF: 0.1초, CoinGecko: 1.0초

7. **requirements.txt - 버전 고정**
   - 재현 가능한 빌드 보장

### 구조 개선
8. **schemas.py**
   - z_score_short, z_score_long 분리
   - MarketRegime Enum 추가

9. **로깅 시스템**
   - print → logging 모듈 사용

---

## 📋 다음 단계 명령어 (Anomaly Detection 분리)

설치 완료 후, Claude Code에 다음 명령을 내리세요:

```
"Anomaly Detection 로직을 modules/anomaly_rules.py로 분리하고, 
다음 5개 규칙을 추가해줘:

1. 역레포(M3)와 TGA(M5) 동시 급감 → 유동성 경색 신호
2. 실업수당(I3)과 JOLTs(I8) 엇갈림 → 고용시장 이상
3. 구리(V4)와 원유(V5) 디커플링 → 수요 둔화 신호
4. BTC(V7)와 금(V3) 동반 급등 → 법정화폐 불신
5. SKEW(S2)와 VIX(S1) 괴리 확대 → 테일 리스크 증가

규칙은 클래스로 구조화하고 filter.py에서 import해서 사용하도록 해줘."
```

---

## 📊 예상 출력 형식

```
======================================================================
🚀 [MacroAgent V3] Strategic Intelligence Report
🕒 Generated: 2026-01-25 15:30:00
======================================================================

┌──────────────────────────────────────────────────────────────────────┐
│ SECTION 1. MARKET REGIME                                            │
└──────────────────────────────────────────────────────────────────────┘
  📢 Current Mode: [ RISK-OFF 🛡️ ]
  📊 Dynamic Threshold: ±2.10 σ

┌──────────────────────────────────────────────────────────────────────┐
│ SECTION 2. PRIORITY ALERTS (TOP 5)                                  │
└──────────────────────────────────────────────────────────────────────┘
  🔥 [S1] VIX 공포지수            | Z: +2.15 ▲ | 🔥역사적 상단 임계 돌파
  ...

======================================================================
```

---

## ❓ 트러블슈팅

### FRED API 키 오류
```
❌ ERROR: FRED API 키가 설정되지 않았습니다.
```
→ https://fred.stlouisfed.org/docs/api/api_key.html 에서 무료 발급

### yfinance 타임아웃
→ 네트워크 상태 확인, 또는 YF_API_DELAY 값 증가

### 데이터 부족 경고
→ 주말/공휴일에는 일부 지표가 업데이트되지 않음 (정상)
