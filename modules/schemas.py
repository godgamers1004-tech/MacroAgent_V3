"""
MacroAgent_V4 데이터 스키마 정의
================================
글로벌 하이브리드 에디션 (US/KR)

시스템 전체에서 사용되는 데이터 구조 정의
- Region: 지역 구분 (미국, 한국, 글로벌)
- SectorType: 매크로 섹터 분류 (5개 섹터)
- QuantitativeMetric: 정량적 지표 분석 결과
"""
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class Region(str, Enum):
    """
    국가/지역 구분 열거형

    퀀트 분석 시 지역별 상관관계 및 영향도 파악에 활용
    - US: 미국 시장 지표 (글로벌 유동성의 원천)
    - KR: 한국 시장 지표 (이머징 대표, 반도체 벨웨더)
    - GLOBAL: 글로벌/크로스보더 지표 (환율, 원자재 등)
    """
    US = "US"
    KR = "KR"
    GLOBAL = "GLOBAL"


class SectorType(str, Enum):
    """
    매크로 데이터 섹터 분류

    V4 업데이트: 경기확장(Growth & Activity) 섹터 신설
    - 한국 산업/수출 지표 포함을 위해 추가됨
    """
    MONETARY = "1. Monetary Policy (통화정책)"
    INFLATION = "2. Inflation & Employment (물가/고용)"
    LIQUIDITY = "3. Value & Flow (유동성)"
    SENTIMENT = "4. Volatility & Sentiment (심리)"
    GROWTH = "5. Growth & Activity (경기확장)"


class DataReliability(str, Enum):
    """
    데이터 신뢰도 등급

    우선순위 점수 계산 시 가중치로 활용
    - OFFICIAL: 정부/중앙은행 공식 발표 (가장 신뢰)
    - HIGH: 거래소/공인기관 실시간 데이터
    - MEDIUM: 서드파티 API 제공 데이터
    - LOW: 비공식/추정/파생 데이터
    """
    OFFICIAL = "OFFICIAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class DataSource(str, Enum):
    """
    데이터 소스 구분

    리포트에서 데이터 출처 표시용
    """
    FRED = "FRED"           # 미국 연준 경제 데이터
    BOK = "BOK"             # 한국은행 ECOS
    YF = "YF"               # Yahoo Finance (실시간)
    API = "API"             # 외부 API (CoinGecko 등)
    CUSTOM = "CUSTOM"       # 커스텀 계산 지표
    MANUAL = "MANUAL"       # 수동 입력값


class DataCycle(str, Enum):
    """
    데이터 업데이트 주기
    """
    REALTIME = "실시간"      # 실시간/일중
    DAILY = "일별"          # 매일 업데이트
    WEEKLY = "주별"         # 주간 업데이트
    MONTHLY = "월별"        # 월간 업데이트
    MANUAL = "수동"         # 수동 업데이트


class QuantitativeMetric(BaseModel):
    """
    개별 매크로 지표의 정량적 분석 결과

    V4 업데이트: region 필드 추가로 국가별 분석 지원
    V4.1 업데이트: data_source, data_cycle 필드 추가
    모든 에이전트가 이 형식으로 데이터를 주고받음
    """
    id: str = Field(..., description="지표 고유 식별자 (예: M1, K5)")
    name: str = Field(..., description="지표 한글명")
    sector: SectorType = Field(..., description="소속 섹터")
    region: Region = Field(Region.US, description="국가/지역 구분")
    value: float = Field(..., description="현재값")

    # 통계적 위치 (역사적 분포에서의 위치)
    z_score_short: float = Field(0.0, description="단기 Z-Score (3개월, 급변 감지)")
    z_score_long: float = Field(0.0, description="장기 Z-Score (1년, 추세 이탈)")
    z_score: float = Field(0.0, description="대표 Z-Score (장기 기준)")

    # 동적 변화량 (모멘텀 분석)
    velocity: float = Field(0.0, description="1차 미분 (변화 속도)")
    acceleration: float = Field(0.0, description="2차 미분 (변화 가속도)")

    # 메타 정보
    reliability: DataReliability = Field(..., description="데이터 신뢰도 등급")
    freshness: float = Field(1.0, description="데이터 신선도 (0~1, 최신일수록 1)")
    priority_score: float = Field(0.0, description="종합 우선순위 점수 (높을수록 주목)")

    # 데이터 소스 정보 (V4.1 신규)
    data_source: DataSource = Field(DataSource.FRED, description="데이터 소스")
    data_cycle: DataCycle = Field(DataCycle.DAILY, description="업데이트 주기")

    # 해석
    trend_desc: str = Field("횡보", description="트렌드 요약 설명")

    class Config:
        use_enum_values = True


class MarketRegime(str, Enum):
    """
    시장 국면 분류

    히트맵 분석 결과로부터 도출되는 거시적 시장 상태
    """
    CRISIS = "CRISIS 🚨"
    RISK_OFF = "RISK-OFF 🛡️"
    NEUTRAL = "NEUTRAL ⚖️"
    RISK_ON = "RISK-ON 🚀"
