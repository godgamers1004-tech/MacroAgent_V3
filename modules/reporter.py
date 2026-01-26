"""
MacroAgent_V4 리포트 생성 모듈
==============================
글로벌 하이브리드 에디션 (US/KR)

분석 결과를 구조화된 리포트로 출력

출력 형식:
- 콘솔 출력 (컬러/이모지 지원)
- 텍스트 파일 저장 (output/)

V4 신규 섹션:
- SECTION 3: KOREA SNAPSHOT (K-Macro) - 한국 시장 전용 요약
- 국가별 플래그 표시 (🇺🇸, 🇰🇷, 🌐)
"""
import os
from datetime import datetime
from typing import List, Dict, Any
import logging

from .schemas import QuantitativeMetric, SectorType, Region

logger = logging.getLogger(__name__)


class IntelligenceReporter:
    """
    매크로 인텔리전스 리포트 생성기

    V4 업데이트:
    - 한국 스냅샷 섹션 추가
    - 국가별 플래그 표시
    - 글로벌 하이브리드 레이아웃
    """

    OUTPUT_DIR = "output"

    # 국가/지역별 플래그 이모지 매핑
    REGION_FLAGS = {
        "US": "🇺🇸",
        "KR": "🇰🇷",
        "GLOBAL": "🌐"
    }

    @classmethod
    def generate_and_save_report(
        cls,
        metrics: List[QuantitativeMetric],
        alerts: List[QuantitativeMetric],
        anomalies: List[str],
        heatmap: Dict[SectorType, Dict],
        regime: str,
        threshold: float
    ) -> str:
        """
        리포트 생성 및 저장

        Args:
            metrics: 처리된 전체 지표 목록
            alerts: 상위 우선순위 알림 목록
            anomalies: 이상 징후 목록
            heatmap: 섹터별 히트맵 데이터
            regime: 시장 국면
            threshold: 동적 임계값

        Returns:
            저장된 파일 경로
        """
        # 1. 리포트 내용 생성
        report_content = cls._build_report(
            metrics, alerts, anomalies, heatmap, regime, threshold
        )

        # 2. 콘솔 출력
        print(report_content)

        # 3. 파일 저장
        filepath = cls._save_to_file(report_content)

        return filepath

    @classmethod
    def _get_region_flag(cls, region: str) -> str:
        """국가/지역 플래그 이모지 반환"""
        return cls.REGION_FLAGS.get(region, "🌐")

    @classmethod
    def _build_report(
        cls,
        metrics: List[QuantitativeMetric],
        alerts: List[QuantitativeMetric],
        anomalies: List[str],
        heatmap: Dict[SectorType, Dict],
        regime: str,
        threshold: float
    ) -> str:
        """리포트 전체 문자열 생성"""

        lines = []
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # 지역별 지표 분류
        us_metrics = [m for m in metrics if m.region == "US"]
        kr_metrics = [m for m in metrics if m.region == "KR"]
        global_metrics = [m for m in metrics if m.region == "GLOBAL"]

        # === Header ===
        lines.append("=" * 82)
        lines.append("🚀 [MacroAgent V4] Global Hybrid Intelligence Report (US/KR)")
        lines.append(f"🕒 생성 시각: {timestamp}")
        lines.append(f"📊 총 지표: {len(metrics)}개 (🇺🇸 {len(us_metrics)} | 🇰🇷 {len(kr_metrics)} | 🌐 {len(global_metrics)})")
        lines.append("=" * 82)
        lines.append("")

        # === Section 1: Market Regime ===
        lines.append("┌" + "─" * 80 + "┐")
        lines.append("│ SECTION 1. MARKET REGIME (시장 국면)                                            │")
        lines.append("└" + "─" * 80 + "┘")
        lines.append(f"  📢 현재 국면: [ {regime} ]")
        lines.append(f"  📊 동적 임계값: ±{threshold:.2f} σ (VIX 연동)")
        lines.append("")

        # === Section 2: Priority Alerts ===
        lines.append("┌" + "─" * 80 + "┐")
        lines.append("│ SECTION 2. PRIORITY ALERTS (우선순위 알림 TOP 5)                                │")
        lines.append("└" + "─" * 80 + "┘")

        if alerts:
            for i, m in enumerate(alerts, 1):
                flag = cls._get_region_flag(m.region)
                icon = "🔥" if m.z_score > 0 else "❄️"
                direction = "▲" if m.velocity > 0 else "▼"
                # 업데이트 주기 표시
                cycle_str = m.data_cycle if isinstance(m.data_cycle, str) else m.data_cycle.value
                lines.append(
                    f"  {icon} {flag} [{m.id}] {m.name[:20]:<20} | "
                    f"Z: {m.z_score:+.2f} {direction} | [{cycle_str}] {m.trend_desc}"
                )
        else:
            lines.append("  ✅ 현재 주요 알림 없음 (안정 구간)")
        lines.append("")

        # === Section 3: Korea Snapshot (V4 신규) ===
        lines.append("┌" + "─" * 80 + "┐")
        lines.append("│ SECTION 3. KOREA SNAPSHOT (K-Macro 한국 시장)                                   │")
        lines.append("└" + "─" * 80 + "┘")

        if kr_metrics:
            # 한국 지표 중 주요 항목 표시
            lines.append(f"  {'ID':<5} {'지표명':<22} {'현재값':>12} {'Z-Score':>8} {'주기':<6} {'트렌드':<16}")
            lines.append("  " + "-" * 76)

            # 우선순위 점수 기준 정렬
            kr_sorted = sorted(kr_metrics, key=lambda x: x.priority_score, reverse=True)

            for m in kr_sorted:
                # 값 포맷팅 (크기에 따라)
                if abs(m.value) >= 1000000000:
                    val_str = f"{m.value/1e9:.1f}B"
                elif abs(m.value) >= 1000000:
                    val_str = f"{m.value/1e6:.1f}M"
                elif abs(m.value) >= 1000:
                    val_str = f"{m.value/1e3:.1f}K"
                else:
                    val_str = f"{m.value:.2f}"

                # 업데이트 주기 표시
                cycle_str = m.data_cycle if isinstance(m.data_cycle, str) else m.data_cycle.value

                lines.append(
                    f"  {m.id:<5} {m.name[:20]:<22} {val_str:>12} "
                    f"{m.z_score:>+8.2f} {cycle_str:<6} {m.trend_desc:<16}"
                )

            # 한국 시장 요약 통계
            kr_avg_z = sum(m.z_score for m in kr_metrics) / len(kr_metrics)
            kr_hot = sum(1 for m in kr_metrics if m.z_score > 1.0)
            kr_cold = sum(1 for m in kr_metrics if m.z_score < -1.0)

            lines.append("")
            lines.append(f"  📈 K-Macro 요약: 평균 Z-Score {kr_avg_z:+.2f} | "
                        f"Hot(>1σ): {kr_hot}개 | Cold(<-1σ): {kr_cold}개")
        else:
            lines.append("  ⚠️ 한국 지표 데이터 없음")
        lines.append("")

        # === Section 4: Anomaly Detection ===
        lines.append("┌" + "─" * 80 + "┐")
        lines.append("│ SECTION 4. ANOMALY DETECTION (이상 징후 탐지)                                   │")
        lines.append("└" + "─" * 80 + "┘")

        if anomalies:
            for anomaly in anomalies:
                lines.append(f"  {anomaly}")
        else:
            lines.append("  ✅ 이상 징후 미탐지 (상관관계 정상)")
        lines.append("")

        # === Section 5: Sector Heatmap ===
        lines.append("┌" + "─" * 80 + "┐")
        lines.append("│ SECTION 5. SECTOR HEATMAP (섹터별 온도)                                         │")
        lines.append("└" + "─" * 80 + "┘")

        for sector, data in heatmap.items():
            heat = data.get("heat", 0)
            sync = data.get("sync", 0)
            count = data.get("count", 0)

            # 온도 상태 결정
            if heat > 1.0:
                status = "HOT  🔥"
            elif heat < -1.0:
                status = "COLD 🧊"
            else:
                status = "NEUTRAL"

            # 섹터 이름 정리
            sector_name = sector.value.split("(")[0].strip()[:22]

            lines.append(
                f"  • {sector_name:<22} : {status:<10} "
                f"(Temp: {heat:+.2f} | Sync: {sync*100:>3.0f}% | n={count})"
            )
        lines.append("")

        # === Section 6: Full Indicator Matrix ===
        lines.append("┌" + "─" * 82 + "┐")
        lines.append("│ SECTION 6. FULL INDICATOR MATRIX (전체 지표 매트릭스)                               │")
        lines.append("└" + "─" * 82 + "┘")
        lines.append(
            f"  {'Flag':<4} {'ID':<5} {'Name':<20} {'Value':>12} {'Z-Score':>8} "
            f"{'Vel':>8} {'Fresh':>6} {'Cycle':<8}"
        )
        lines.append("  " + "-" * 78)

        # ID 순 정렬 (M -> I -> V -> S -> K)
        def sort_key(m):
            prefix = m.id[0]
            num = int(m.id[1:]) if m.id[1:].isdigit() else 0
            prefix_order = {'M': 0, 'I': 1, 'V': 2, 'S': 3, 'K': 4}
            return (prefix_order.get(prefix, 9), num)

        sorted_metrics = sorted(metrics, key=sort_key)

        for m in sorted_metrics:
            flag = cls._get_region_flag(m.region)

            # 값 포맷팅 (크기에 따라)
            if abs(m.value) >= 1000000000:
                val_str = f"{m.value/1e9:.1f}B"
            elif abs(m.value) >= 1000000:
                val_str = f"{m.value/1e6:.1f}M"
            elif abs(m.value) >= 1000:
                val_str = f"{m.value/1e3:.1f}K"
            else:
                val_str = f"{m.value:.2f}"

            # 업데이트 주기 표시
            cycle_str = m.data_cycle if isinstance(m.data_cycle, str) else m.data_cycle.value

            lines.append(
                f"  {flag:<4} {m.id:<5} {m.name[:18]:<20} {val_str:>12} "
                f"{m.z_score:>+8.2f} {m.velocity:>+8.4f} {m.freshness:>6.2f} {cycle_str:<8}"
            )

        lines.append("")
        lines.append("=" * 82)
        lines.append("📌 범례 (Legend)")
        lines.append("   Z-Score: 평균으로부터의 표준편차 (±2σ 이상 = 극단값)")
        lines.append("   Vel: 변화 속도 (양수=상승, 음수=하락)")
        lines.append("   Fresh: 데이터 신선도 (1.0=최신, 0=오래됨)")
        lines.append("   Cycle: 업데이트 주기 (실시간/일별/주별/월별/수동)")
        lines.append("   Flag: 🇺🇸=미국, 🇰🇷=한국, 🌐=글로벌")
        lines.append("=" * 82)

        return "\n".join(lines)

    @classmethod
    def _save_to_file(cls, content: str) -> str:
        """리포트 파일 저장"""

        # 출력 디렉토리 생성
        os.makedirs(cls.OUTPUT_DIR, exist_ok=True)

        # 파일명 생성 (타임스탬프 포함)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"macro_report_{timestamp}.txt"
        filepath = os.path.join(cls.OUTPUT_DIR, filename)

        # 파일 저장
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        logger.info(f"📄 리포트 저장 완료: {filepath}")
        print(f"\n📄 리포트 저장 완료: {filepath}")

        return filepath
