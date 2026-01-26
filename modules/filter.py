"""
MacroAgent_V4 필터 엔진 모듈
============================
글로벌 하이브리드 에디션 (US/KR)

수집/처리된 지표에서 핵심 시그널 추출

주요 기능:
- Dynamic Alert 생성 (Z-Score + 가속도 기반)
- Anomaly Detection (상관관계 이탈 감지, 한국 시장 규칙 추가)
- Sector Heatmap 계산 (5개 섹터: Growth 포함)
"""
import numpy as np
from typing import List, Dict, Tuple, Any
import logging

from .schemas import QuantitativeMetric, SectorType
import config

logger = logging.getLogger(__name__)


class MacroFilterEngine:
    """
    매크로 데이터 필터링 및 시그널 추출 엔진

    V4 업데이트:
    - Growth & Activity 섹터 지원
    - 한국 시장 이상 징후 규칙 추가
    """

    def run_analysis(
        self,
        metrics: List[QuantitativeMetric],
        market_vix_ratio: float
    ) -> Tuple[List[QuantitativeMetric], List[str], Dict[SectorType, Dict], float]:
        """
        종합 분석 실행

        Args:
            metrics: 처리된 지표 목록
            market_vix_ratio: VIX 비율 (변동성 조정용)

        Returns:
            - alerts: 상위 N개 우선순위 알림
            - anomalies: 이상 징후 목록
            - heatmap: 섹터별 온도 맵
            - threshold: 동적 임계값
        """
        # 1. 동적 임계값 계산 (VIX 연동)
        dynamic_threshold = self._calculate_dynamic_threshold(market_vix_ratio)

        # 2. 우선순위 알림 추출
        alerts = self._extract_alerts(metrics, dynamic_threshold)

        # 3. 이상 징후 탐지 (미국 + 한국 규칙)
        anomalies = self._detect_anomalies(metrics)

        # 4. 섹터 히트맵 생성
        heatmap = self._generate_heatmap(metrics)

        return alerts, anomalies, heatmap, dynamic_threshold

    def _calculate_dynamic_threshold(self, market_vix_ratio: float) -> float:
        """
        VIX 기반 동적 임계값 계산

        - VIX 높음 → 임계값 상승 (노이즈 필터링 강화)
        - VIX 낮음 → 임계값 하락 (민감도 증가)

        Args:
            market_vix_ratio: 현재 VIX / 기준 VIX

        Returns:
            동적 임계값 (σ 단위)
        """
        base = config.BASE_THRESHOLD

        # VIX 비율을 0.8 ~ 1.5 범위로 제한 (극단값 방어)
        vix_factor = max(0.8, min(1.5, market_vix_ratio))

        return round(base * vix_factor, 2)

    def _extract_alerts(
        self,
        metrics: List[QuantitativeMetric],
        threshold: float
    ) -> List[QuantitativeMetric]:
        """
        우선순위 알림 추출

        선별 조건:
        1. Z-Score가 동적 임계값 초과 (Critical Zone)
        2. Z-Score > 1.0 AND 가속 상태 (Accelerating Alert)

        Args:
            metrics: 처리된 지표 목록
            threshold: 동적 임계값

        Returns:
            상위 N개 우선순위 알림 목록
        """
        alerts = []

        for m in metrics:
            is_critical = abs(m.z_score) > threshold
            is_accelerating = self._is_accelerating(m)

            if is_critical or (abs(m.z_score) > 1.0 and is_accelerating):
                alerts.append(m)

        # 우선순위 점수 기준 정렬, 상위 N개 반환
        alerts = sorted(alerts, key=lambda x: x.priority_score, reverse=True)
        return alerts[:config.ALERT_TOP_N]

    def _is_accelerating(self, metric: QuantitativeMetric) -> bool:
        """
        가속 상태 판단

        Velocity 대비 Acceleration 비율로 판단
        (가속도는 속도의 변화이므로 속도 대비 비율이 의미 있음)

        Args:
            metric: 개별 지표

        Returns:
            가속 상태 여부
        """
        # 절대 가속도 최소 임계값
        if abs(metric.acceleration) < 0.001:
            return False

        # 속도 대비 가속도 비율 계산
        velocity_safe = abs(metric.velocity) + 1e-9  # 0 나눗셈 방지
        acc_ratio = abs(metric.acceleration) / velocity_safe

        # 가속도가 속도의 10% 이상이면 가속 상태로 판단
        return acc_ratio > 0.1

    def _detect_anomalies(self, metrics: List[QuantitativeMetric]) -> List[str]:
        """
        이상 징후 탐지

        정상적인 상관관계가 붕괴된 경우를 탐지
        - 미국 시장 규칙 (기존)
        - 한국 시장 규칙 (V4 신규)

        Args:
            metrics: 처리된 지표 목록

        Returns:
            이상 징후 설명 문자열 목록
        """
        anomalies = []
        m_dict = {m.id: m for m in metrics}

        # ═══════════════════════════════════════════════════════════
        # 🇺🇸 미국 시장 규칙
        # ═══════════════════════════════════════════════════════════

        # === Rule 1: VIX-금리 동반 급등 (Crisis Signal) ===
        if "S1" in m_dict and "M10" in m_dict:
            vix = m_dict["S1"]
            rate = m_dict["M10"]
            if vix.z_score > 1.0 and rate.z_score > 1.0:
                anomalies.append(
                    f"⚠️ [위기 신호] 공포지수({vix.value:.1f})와 "
                    f"국채금리({rate.value:.2f}%) 동반 급등 → 현금 선호 현상 감지"
                )

        # === Rule 2: 달러-금 동반 상승 (상관관계 붕괴) ===
        if "V1" in m_dict and "V3" in m_dict:
            dxy = m_dict["V1"]
            gold = m_dict["V3"]
            if dxy.z_score > 1.0 and gold.z_score > 1.0:
                anomalies.append(
                    f"⚠️ [상관관계 붕괴] 달러(DXY Z:{dxy.z_score:+.2f})와 "
                    f"금(Z:{gold.z_score:+.2f}) 동반 상승 → 전통적 역상관 관계 붕괴"
                )

        # === Rule 3: 장단기 금리 역전 심화 ===
        if "M1" in m_dict:
            spread = m_dict["M1"]
            if spread.value < -0.5 and spread.z_score < -1.5:
                anomalies.append(
                    f"🚨 [경기침체 경보] 장단기 금리차({spread.value:.2f}%) 역전 심화 "
                    f"→ 역사적 저점 구간 (Z:{spread.z_score:+.2f})"
                )

        # ═══════════════════════════════════════════════════════════
        # 🇰🇷 한국 시장 규칙 (V4 신규)
        # ═══════════════════════════════════════════════════════════

        # === Rule K1: 원/달러 급등 + 코스피 급락 (외국인 이탈) ===
        if "K1" in m_dict and "K2" in m_dict:
            usdkrw = m_dict["K1"]
            kospi = m_dict["K2"]
            if usdkrw.z_score > 1.5 and kospi.z_score < -1.0:
                anomalies.append(
                    f"🇰🇷 [외국인 이탈 신호] 원/달러({usdkrw.value:.0f}원) 급등 + "
                    f"코스피({kospi.value:.0f}) 급락 → 자본 유출 경계"
                )

        # === Rule K2: 삼성전자-SK하이닉스 디커플링 ===
        if "K8" in m_dict and "K9" in m_dict:
            samsung = m_dict["K8"]
            hynix = m_dict["K9"]
            z_diff = abs(samsung.z_score - hynix.z_score)
            if z_diff > 1.5:
                leader = "삼성전자" if samsung.z_score > hynix.z_score else "SK하이닉스"
                anomalies.append(
                    f"🇰🇷 [반도체 디커플링] 삼성전자(Z:{samsung.z_score:+.2f}) vs "
                    f"SK하이닉스(Z:{hynix.z_score:+.2f}) 괴리 확대 → {leader} 선도"
                )

        # === Rule K3: 코스피-코스닥 괴리 (대형주/중소형주 차별화) ===
        if "K2" in m_dict and "K7" in m_dict:
            kospi = m_dict["K2"]
            kosdaq = m_dict["K7"]
            z_diff = kospi.z_score - kosdaq.z_score
            if abs(z_diff) > 1.0:
                if z_diff > 0:
                    anomalies.append(
                        f"🇰🇷 [대형주 선호] 코스피(Z:{kospi.z_score:+.2f}) > "
                        f"코스닥(Z:{kosdaq.z_score:+.2f}) → 안전자산 선호 국면"
                    )
                else:
                    anomalies.append(
                        f"🇰🇷 [위험선호 강화] 코스닥(Z:{kosdaq.z_score:+.2f}) > "
                        f"코스피(Z:{kospi.z_score:+.2f}) → 중소형주 랠리 가능성"
                    )

        # === Rule K4: 원/엔 환율 급변 (수출 경쟁력 변화) ===
        if "K14" in m_dict:
            krwjpy = m_dict["K14"]
            if abs(krwjpy.z_score) > 2.0:
                direction = "원화 강세" if krwjpy.z_score > 0 else "원화 약세"
                impact = "수출 불리" if krwjpy.z_score > 0 else "수출 유리"
                anomalies.append(
                    f"🇰🇷 [원/엔 환율 경고] {direction} 극단 구간 "
                    f"(Z:{krwjpy.z_score:+.2f}) → 대일본 {impact}"
                )

        # === Rule K5: 한국 수출-경기선행지수 디버전스 ===
        if "K6" in m_dict and "K12" in m_dict:
            exports = m_dict["K6"]
            cli = m_dict["K12"]
            if exports.z_score > 1.0 and cli.z_score < -0.5:
                anomalies.append(
                    f"🇰🇷 [수출-경기 디버전스] 수출(Z:{exports.z_score:+.2f}) 호조 but "
                    f"선행지수(Z:{cli.z_score:+.2f}) 부진 → 내수 경기 둔화 우려"
                )

        return anomalies

    def _generate_heatmap(self, metrics: List[QuantitativeMetric]) -> Dict[SectorType, Dict[str, Any]]:
        """
        섹터별 히트맵 생성

        각 섹터에 대해:
        - heat: 평균 Z-Score (양수=Hot/과열, 음수=Cold/침체)
        - sync: 동조화율 (같은 방향으로 움직이는 비율)
        - acceleration: 평균 가속도
        - count: 섹터 내 지표 수

        Args:
            metrics: 처리된 지표 목록

        Returns:
            섹터별 히트맵 데이터
        """
        heatmap = {}

        for sector in SectorType:
            sector_metrics = [m for m in metrics if m.sector == sector]

            if not sector_metrics:
                continue

            # 평균 Z-Score (섹터 온도)
            avg_z = np.mean([m.z_score for m in sector_metrics])

            # 동조화율 계산 (같은 방향 움직임 비율)
            positive_velocity = sum(1 for m in sector_metrics if m.velocity > 0)
            negative_velocity = sum(1 for m in sector_metrics if m.velocity < 0)
            sync_rate = max(positive_velocity, negative_velocity) / len(sector_metrics)

            # 평균 가속도
            avg_acc = np.mean([m.acceleration for m in sector_metrics])

            heatmap[sector] = {
                "heat": round(avg_z, 3),
                "sync": round(sync_rate, 3),
                "acceleration": round(avg_acc, 6),
                "count": len(sector_metrics)
            }

        return heatmap

    def get_regime_from_heatmap(self, heatmap: Dict[SectorType, Dict]) -> str:
        """
        히트맵에서 시장 국면(Regime) 도출

        SENTIMENT 섹터의 온도로 주요 판단:
        - > 2.0: CRISIS (위기)
        - > 1.0: RISK-OFF (위험회피)
        - < -1.0: RISK-ON (위험선호, 과도한 낙관)
        - else: NEUTRAL (중립)

        Args:
            heatmap: 섹터별 히트맵 데이터

        Returns:
            시장 국면 문자열
        """
        sentiment_data = heatmap.get(SectorType.SENTIMENT, {})
        sent_heat = sentiment_data.get("heat", 0)

        if sent_heat > 2.0:
            return "CRISIS 🚨"
        elif sent_heat > 1.0:
            return "RISK-OFF 🛡️"
        elif sent_heat < -1.0:
            return "RISK-ON 🚀"
        else:
            return "NEUTRAL ⚖️"
