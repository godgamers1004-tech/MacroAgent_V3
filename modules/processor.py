"""
MacroAgent_V4 데이터 처리 모듈
==============================
글로벌 하이브리드 에디션 (US/KR)

수집된 원시 데이터를 정량적 지표로 변환하는 핵심 엔진

주요 계산:
- Z-Score (단기 63일 / 장기 252일): 역사적 위치 파악
- Velocity (1차 미분): 변화 속도 측정
- Acceleration (2차 미분): 변화 가속도 (모멘텀 전환 감지)
- Priority Score: 종합 우선순위 (주목해야 할 지표 선별)
"""
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, Optional, List
import logging

from .schemas import QuantitativeMetric, SectorType, DataReliability, Region, DataSource, DataCycle
import config

logger = logging.getLogger(__name__)


class MacroProcessor:
    """
    매크로 데이터 처리 및 정량적 지표 계산 엔진

    V4 업데이트: Region 필드 지원으로 국가별 분석 가능
    """

    # 신뢰도별 가중치 (우선순위 점수 계산에 활용)
    RELIABILITY_WEIGHTS = {
        "OFFICIAL": 1.2,   # 정부/중앙은행 공식 데이터
        "HIGH": 1.0,       # 거래소 실시간 데이터
        "MEDIUM": 0.8,     # 서드파티 API
        "LOW": 0.5         # 비공식/추정 데이터
    }

    @classmethod
    def calculate_metrics(
        cls,
        m_id: str,
        data: Dict,
        market_vix_ratio: float
    ) -> Optional[QuantitativeMetric]:
        """
        개별 지표의 정량적 메트릭 계산

        Args:
            m_id: 지표 ID (예: M1, K5)
            data: {
                "series": pd.Series (시계열 데이터),
                "meta": (sector, name, reliability, region)
            }
            market_vix_ratio: 현재 VIX / 기준 VIX (변동성 조정 계수)

        Returns:
            QuantitativeMetric 객체 또는 None (데이터 부족 시)
        """
        series = data["series"]
        meta = data["meta"]

        # V4: 메타데이터에서 region 추출 (하위 호환성 유지)
        if len(meta) == 4:
            sector, name, reliability, region = meta
        else:
            # V3 하위 호환: region이 없는 경우 US로 기본값 설정
            sector, name, reliability = meta
            region = Region.US

        # V4.1: 데이터 소스 및 업데이트 주기 추출
        data_source = data.get("source", "FRED")
        data_cycle = data.get("cycle", "일별")

        # 최소 데이터 검증 (30일 이상 필요)
        if len(series) < 30:
            logger.warning(f"{m_id}: 데이터 부족 ({len(series)} < 30개)")
            return None

        try:
            # 1. 현재값 추출
            current_val = float(series.iloc[-1])

            # 2. Z-Score 계산 (단기/장기)
            z_score_short, z_score_long = cls._calculate_z_scores(series)

            # 3. Velocity & Acceleration 계산 (이동평균 기반)
            velocity, acceleration = cls._calculate_dynamics(series)

            # 4. 데이터 신선도 계산 (최신 데이터일수록 높음)
            freshness = cls._calculate_freshness(series)

            # 5. 우선순위 점수 계산 (VIX 반영)
            priority_score = cls._calculate_priority(
                z_score_long, acceleration, reliability, freshness, market_vix_ratio
            )

            # 6. 트렌드 설명 문자열 생성
            trend_desc = cls._generate_trend_description(z_score_long, velocity, acceleration)

            # 데이터 소스 Enum 변환
            source_map = {
                "FRED": DataSource.FRED,
                "BOK": DataSource.BOK,
                "YF": DataSource.YF,
                "API": DataSource.API,
                "CUSTOM": DataSource.CUSTOM,
                "MANUAL": DataSource.MANUAL
            }
            source_enum = source_map.get(data_source, DataSource.FRED)

            # 데이터 주기 Enum 변환
            cycle_map = {
                "실시간": DataCycle.REALTIME,
                "일별": DataCycle.DAILY,
                "주별": DataCycle.WEEKLY,
                "월별": DataCycle.MONTHLY,
                "수동": DataCycle.MANUAL
            }
            cycle_enum = cycle_map.get(data_cycle, DataCycle.DAILY)

            return QuantitativeMetric(
                id=m_id,
                name=name,
                sector=sector,
                region=region,  # V4: 국가/지역 정보 추가
                value=current_val,
                z_score_short=z_score_short,
                z_score_long=z_score_long,
                z_score=z_score_long,  # 대표 Z-Score는 장기 기준
                velocity=velocity,
                acceleration=acceleration,
                reliability=reliability,
                freshness=freshness,
                priority_score=priority_score,
                data_source=source_enum,    # V4.1: 데이터 소스 추가
                data_cycle=cycle_enum,      # V4.1: 업데이트 주기 추가
                trend_desc=trend_desc
            )

        except Exception as e:
            logger.error(f"{m_id} 처리 실패: {e}")
            return None

    @staticmethod
    def _calculate_z_scores(series: pd.Series) -> tuple:
        """
        단기/장기 Z-Score 계산

        Z-Score = (현재값 - 평균) / 표준편차

        - 단기 (63일, 약 3개월): 최근 급변 감지에 유리
        - 장기 (252일, 약 1년): 역사적 위치 파악에 유리

        Returns:
            (z_score_short, z_score_long)
        """
        current_val = series.iloc[-1]

        # 단기 Z-Score (63 거래일 ≈ 3개월)
        short_window = min(config.Z_SCORE_SHORT_WINDOW, len(series))
        short_series = series.tail(short_window)
        short_mean = short_series.mean()
        short_std = short_series.std()
        z_short = (current_val - short_mean) / short_std if short_std > 0 else 0.0

        # 장기 Z-Score (252 거래일 ≈ 1년)
        long_window = min(config.Z_SCORE_LONG_WINDOW, len(series))
        long_series = series.tail(long_window)
        long_mean = long_series.mean()
        long_std = long_series.std()
        z_long = (current_val - long_mean) / long_std if long_std > 0 else 0.0

        return round(z_short, 4), round(z_long, 4)

    @staticmethod
    def _calculate_dynamics(series: pd.Series) -> tuple:
        """
        Velocity (1차 미분) 및 Acceleration (2차 미분) 계산

        5일 이동평균 기반으로 노이즈 감소
        - Velocity: 가격/지표의 변화 속도
        - Acceleration: 변화 속도의 변화 (모멘텀 전환 신호)

        Returns:
            (velocity, acceleration)
        """
        # 5일 이동평균 (노이즈 제거)
        ma5 = series.rolling(window=5, min_periods=3).mean()

        # Velocity: 이동평균의 일간 변화량
        velocity_series = ma5.diff()
        velocity = float(velocity_series.iloc[-1]) if not pd.isna(velocity_series.iloc[-1]) else 0.0

        # Acceleration: Velocity의 변화량 (2차 미분)
        velocity_prev = float(velocity_series.iloc[-2]) if len(velocity_series) > 1 and not pd.isna(velocity_series.iloc[-2]) else velocity
        acceleration = velocity - velocity_prev

        return round(velocity, 6), round(acceleration, 6)

    @staticmethod
    def _calculate_freshness(series: pd.Series) -> float:
        """
        데이터 신선도 계산 (지수 감쇠 함수, 데이터 주기 자동 감지)

        Freshness = exp(-λ × periods_old)

        데이터 주기 자동 감지:
        - 일별 데이터 (간격 < 7일): 일 단위 감쇠
        - 주별 데이터 (7일 <= 간격 < 20일): 주 단위 감쇠
        - 월별 데이터 (간격 >= 20일): 월 단위 감쇠

        Returns:
            신선도 점수 (0 ~ 1)
        """
        try:
            last_date = pd.to_datetime(series.index[-1])
            days_diff = (datetime.now() - last_date.to_pydatetime()).days
            days_diff = max(0, days_diff)  # 음수 방지 (미래 날짜 방어)

            # 데이터 주기 자동 감지 (최근 데이터 간격 기준)
            if len(series) >= 3:
                recent_dates = pd.to_datetime(series.index[-3:])
                avg_interval = (recent_dates[-1] - recent_dates[0]).days / 2
            else:
                avg_interval = 1  # 기본값: 일별

            # 주기에 따라 감쇠 단위 조정
            if avg_interval >= 20:  # 월별 데이터
                # 월 단위로 변환 (30일 = 1기간)
                periods_diff = days_diff / 30.0
                decay_lambda = config.FRESHNESS_DECAY_LAMBDA * 3  # 월별은 더 관대하게
            elif avg_interval >= 7:  # 주별 데이터
                periods_diff = days_diff / 7.0
                decay_lambda = config.FRESHNESS_DECAY_LAMBDA * 2
            else:  # 일별 데이터
                periods_diff = days_diff
                decay_lambda = config.FRESHNESS_DECAY_LAMBDA

            freshness = np.exp(-decay_lambda * periods_diff)

        except Exception:
            freshness = 0.5  # 오류 시 기본값

        return round(max(freshness, 0.01), 4)  # 최소 0.01 보장

    @classmethod
    def _calculate_priority(
        cls,
        z_score: float,
        acceleration: float,
        reliability: DataReliability,
        freshness: float,
        market_vix_ratio: float
    ) -> float:
        """
        우선순위 점수 계산

        높은 점수 = 더 주목해야 할 지표

        Components:
        - Z-Score: 통계적 극단값일수록 높음
        - Acceleration: 변화 가속도 (VIX 비율로 가중)
        - Reliability: 데이터 신뢰도 가중치
        - Freshness: 데이터 신선도 반영

        Returns:
            우선순위 점수 (0 이상)
        """
        # 신뢰도 가중치
        rel_weight = cls.RELIABILITY_WEIGHTS.get(reliability.value, 1.0)

        # 가속도 가중치 (시장 변동성에 비례)
        # VIX가 높을수록 가속도 변화에 민감하게 반응
        acc_weight = 3.0 * market_vix_ratio

        # 원시 점수 계산
        z_component = abs(z_score) * 1.5  # Z-Score 기여
        acc_component = abs(acceleration * 10) * acc_weight  # 가속도 기여

        raw_score = z_component + acc_component

        # 최종 점수 (신뢰도, 신선도 반영)
        priority_score = raw_score * rel_weight * freshness

        return round(priority_score, 4)

    @staticmethod
    def _generate_trend_description(z_score: float, velocity: float, acceleration: float) -> str:
        """
        트렌드 설명 문자열 생성

        퀀트 분석가가 한눈에 파악할 수 있는 간결한 상태 표현

        Returns:
            트렌드 설명 (이모지 + 한글)
        """
        # 1. 극단값 체크 (최우선)
        if abs(z_score) > 2.0:
            direction = "상단" if z_score > 0 else "하단"
            return f"🔥역사적 {direction} 임계 돌파"

        if abs(z_score) > 1.5:
            direction = "상단" if z_score > 0 else "하단"
            return f"⚠️{direction} 주의 구간 진입"

        # 2. 동적 변화 체크 (모멘텀 분석)
        if acceleration > 0 and velocity > 0:
            return "🚀상승 가속"
        elif acceleration < 0 and velocity < 0:
            return "📉하락 가속"
        elif acceleration > 0 and velocity < 0:
            return "📈하락 둔화 (반등 조짐)"
        elif acceleration < 0 and velocity > 0:
            return "📉상승 둔화 (조정 조짐)"

        # 3. 기본값 (횡보)
        return "➡️횡보"

    @classmethod
    def process_all(
        cls,
        raw_data_map: Dict[str, Dict],
        market_vix_ratio: float
    ) -> List[QuantitativeMetric]:
        """
        전체 데이터 일괄 처리

        Args:
            raw_data_map: fetcher.fetch_all() 결과
            market_vix_ratio: VIX 비율 (변동성 조정용)

        Returns:
            List[QuantitativeMetric]: 처리된 지표 목록
        """
        metrics_list = []

        for m_id, data in raw_data_map.items():
            metric = cls.calculate_metrics(m_id, data, market_vix_ratio)
            if metric:
                metrics_list.append(metric)

        # 지역별 처리 결과 로깅
        us_count = sum(1 for m in metrics_list if m.region == "US")
        kr_count = sum(1 for m in metrics_list if m.region == "KR")
        global_count = sum(1 for m in metrics_list if m.region == "GLOBAL")

        logger.info(f"📈 {len(metrics_list)}개 지표 처리 완료")
        logger.info(f"   🇺🇸 미국: {us_count}개 | 🇰🇷 한국: {kr_count}개 | 🌐 글로벌: {global_count}개")

        return metrics_list
