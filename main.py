#!/usr/bin/env python3
"""
MacroAgent_V4 - Global Hybrid Edition (US/KR)
=============================================
QuantCommander 글로벌 매크로 데이터 수집 에이전트

V4 주요 변경사항:
- 55개 지표로 확장 (미국 40개 + 한국 15개)
- 국가/지역(Region) 구분 로직 도입 (US, KR, GLOBAL)
- Korea Snapshot (K-Macro) 섹션 신설

실행 방법:
    python main.py

사전 설정:
    1. FRED API 키 설정
       - 환경변수: export FRED_API_KEY="your_key_here"
       - 또는 config.py 직접 수정

    2. 의존성 설치
       pip install -r requirements.txt

출력:
    - 콘솔에 분석 리포트 출력
    - output/ 디렉토리에 텍스트 파일 저장
"""
import sys
import logging
from datetime import datetime

# 모듈 임포트
from modules.fetcher import MacroDataFetcher
from modules.processor import MacroProcessor
from modules.filter import MacroFilterEngine
from modules.reporter import IntelligenceReporter
from modules.schemas import SectorType, Region
import config

# 로깅 설정 (한국어 출력)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("MacroAgent")


def validate_config() -> bool:
    """
    설정 유효성 검증

    FRED API 키가 올바르게 설정되었는지 확인
    """
    if config.FRED_API_KEY == "YOUR_FRED_API_KEY_HERE":
        print("=" * 60)
        print("❌ 오류: FRED API 키가 설정되지 않았습니다.")
        print("=" * 60)
        print()
        print("해결 방법:")
        print("  1. https://fred.stlouisfed.org/docs/api/api_key.html 에서 API 키 발급")
        print()
        print("  2. 환경변수로 설정 (권장):")
        print('     export FRED_API_KEY="your_key_here"')
        print()
        print("  3. 또는 config.py 파일을 직접 수정:")
        print('     FRED_API_KEY = "your_key_here"')
        print()
        return False
    return True


def main():
    """
    메인 실행 함수

    MacroAgent V4 파이프라인 실행:
    1. 설정 검증
    2. 컴포넌트 초기화
    3. 데이터 수집 (55개 지표)
    4. 데이터 처리 (Z-Score, Velocity, Acceleration)
    5. 필터링 및 분석
    6. 리포트 생성
    """

    print()
    print("╔" + "═" * 62 + "╗")
    print("║  🚀 MacroAgent V4 - Global Hybrid (US/KR) System             ║")
    print("║  QuantCommander 글로벌 매크로 인텔리전스 파이프라인          ║")
    print("╚" + "═" * 62 + "╝")
    print()

    # 1. 설정 검증
    if not validate_config():
        sys.exit(1)

    logger.info("시스템 초기화 중...")
    logger.info("버전: V4 Global Hybrid Edition (US/KR)")

    # 2. 컴포넌트 초기화
    fetcher = MacroDataFetcher(config.FRED_API_KEY)
    processor = MacroProcessor()
    filter_engine = MacroFilterEngine()

    # 3. 데이터 수집 (55개 지표)
    logger.info("=" * 50)
    logger.info("Phase 1: 데이터 수집 시작 (총 55개 지표)")
    logger.info("=" * 50)
    raw_data_map = fetcher.fetch_all()

    if not raw_data_map:
        logger.error("수집된 데이터가 없습니다. 네트워크 연결을 확인하세요.")
        sys.exit(1)

    # 4. VIX 기반 시장 변동성 비율 계산
    vix_data = raw_data_map.get("S1")
    if vix_data and not vix_data["series"].empty:
        current_vix = float(vix_data["series"].iloc[-1])
    else:
        logger.warning("VIX 데이터 없음, 기본값(20.0) 사용")
        current_vix = config.MARKET_VIX_BASE

    market_vix_ratio = current_vix / config.MARKET_VIX_BASE
    logger.info(f"📊 VIX: {current_vix:.2f} (비율: {market_vix_ratio:.2f}x)")

    # 5. 데이터 처리
    logger.info("=" * 50)
    logger.info("Phase 2: 지표 계산 중 (Z-Score, Velocity, Acceleration)")
    logger.info("=" * 50)
    metrics_list = processor.process_all(raw_data_map, market_vix_ratio)

    if not metrics_list:
        logger.error("처리된 지표가 없습니다.")
        sys.exit(1)

    # 6. 필터링 및 분석
    logger.info("=" * 50)
    logger.info("Phase 3: 시그널 분석 중")
    logger.info("=" * 50)
    alerts, anomalies, heatmap, threshold = filter_engine.run_analysis(
        metrics_list, market_vix_ratio
    )

    # 7. 시장 국면 결정
    regime = filter_engine.get_regime_from_heatmap(heatmap)

    # 8. 리포트 생성 및 저장
    logger.info("=" * 50)
    logger.info("Phase 4: 리포트 생성 중")
    logger.info("=" * 50)
    print()

    filepath = IntelligenceReporter.generate_and_save_report(
        metrics=metrics_list,
        alerts=alerts,
        anomalies=anomalies,
        heatmap=heatmap,
        regime=regime,
        threshold=threshold
    )

    # 9. 실행 완료 요약
    print()
    logger.info("✅ MacroAgent V4 실행 완료")

    # 지역별 통계
    us_count = sum(1 for m in metrics_list if m.region == "US")
    kr_count = sum(1 for m in metrics_list if m.region == "KR")
    global_count = sum(1 for m in metrics_list if m.region == "GLOBAL")

    print()
    print("┌" + "─" * 50 + "┐")
    print("│ EXECUTION SUMMARY (실행 요약)                    │")
    print("├" + "─" * 50 + "┤")
    print(f"│ 처리된 지표 총계:              {len(metrics_list):>16} 개 │")
    print(f"│   🇺🇸 미국 지표:                {us_count:>16} 개 │")
    print(f"│   🇰🇷 한국 지표:                {kr_count:>16} 개 │")
    print(f"│   🌐 글로벌 지표:               {global_count:>16} 개 │")
    print("├" + "─" * 50 + "┤")
    print(f"│ 생성된 알림:                   {len(alerts):>16} 개 │")
    print(f"│ 탐지된 이상 징후:              {len(anomalies):>16} 개 │")
    print(f"│ 시장 국면:               {regime:>20}   │")
    print("└" + "─" * 50 + "┘")

    return 0


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⚠️ 사용자에 의해 실행 중단됨")
        sys.exit(130)
    except Exception as e:
        logger.exception(f"예상치 못한 오류 발생: {e}")
        sys.exit(1)
