"""
MacroAgent_V3 Configuration
===========================
시스템 전역 설정값 관리
"""
import os

# ============================================
# 1. API 키 설정 (HARD CODED)
# ============================================
# ⚠️ 사령관님의 실제 키 (절대 유출 주의)
FRED_API_KEY = "2ed5065f762d5627e409a6faa1b0d583"

# (확장 대비용)
NEWS_API_KEY = "15rvadMEFjH7hfHuZgAPS2c5XghrLzHafW"
COINGECKO_API_KEY = "CG-rmbdAqdkX33LdWXnQk9V9vaa"

# 한국은행 ECOS API 키 (https://ecos.bok.or.kr/api/)
BOK_ECOS_API_KEY = "8OJUHPYCUWT49WQDUIHD"

# ============================================
# 2. 퀀트 분석 파라미터 (Quant Parameters)
# ============================================

# VIX 기준점: 동적 임계값 계산의 기준
MARKET_VIX_BASE = 20.0

# 데이터 신선도 감쇠 계수 (데이터가 오래될수록 점수 차감)
FRESHNESS_DECAY_LAMBDA = 0.1

# 📌 Z-Score 윈도우 설정 (거래일 기준)
# 63일(약 1분기): 단기 급등락 감지용
Z_SCORE_SHORT_WINDOW = 63  
# 252일(약 1년): 장기 추세 이탈 감지용 (메인)
Z_SCORE_LONG_WINDOW = 252  

# ============================================
# 3. API 속도 제한 (Rate Limiting) - 차단 방지
# ============================================

# FRED: 0.5초 대기 (안정적)
FRED_API_DELAY = 0.5

# Yahoo Finance: 0.1초 대기 (비교적 관대함)
YF_API_DELAY = 0.1

# CoinGecko: 1.0초 대기 (무료 티어는 엄격함)
COINGECKO_API_DELAY = 1.0

# BOK ECOS: 0.3초 대기 (비교적 관대함)
BOK_API_DELAY = 0.3

# ============================================
# 4. 시스템 제어 (System Control)
# ============================================

# 상위 N개 알림 표시
ALERT_TOP_N = 5

# 기본 위험 임계값 (Z-Score)
BASE_THRESHOLD = 2.0
