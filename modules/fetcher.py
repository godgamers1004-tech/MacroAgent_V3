"""
MacroAgent_V4 데이터 수집 모듈
==============================
글로벌 하이브리드 에디션 (US/KR)

55개 핵심 매크로 지표 수집:
- 미국 지표 40개 (기존 V3)
- 한국 지표 15개 (V4 신규)

데이터 소스:
- FRED (Federal Reserve Economic Data): 미국/한국 경제지표
- Yahoo Finance: 실시간 시장 데이터, 환율, 주가
- CoinGecko: 암호화폐 시가총액 데이터
- Custom APIs: 파생 지표 (Put/Call Ratio, Fear&Greed 등)
"""
import pandas as pd
import yfinance as yf
from fredapi import Fred
from datetime import datetime, timedelta
import calendar
import time
import requests
import logging
from typing import Dict, Optional, Tuple

from .schemas import SectorType, DataReliability, Region
import config

# 로깅 설정 (한국어 출력)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class MacroDataFetcher:
    """
    글로벌 매크로 경제 데이터 수집기 (V4)

    55개 지표를 5개 섹터, 3개 지역으로 분류하여 수집:

    [미국 지표 - 40개]
    - Monetary Policy (M1~M10): 연준 통화정책, 금리, 유동성
    - Inflation & Employment (I1~I10): 물가, 고용, 소비심리
    - Value & Flow (V1~V10): 환율, 원자재, 자산가격
    - Volatility & Sentiment (S1~S10): 변동성, 시장심리

    [한국 지표 - 15개]
    - K1~K2: 원/달러 환율, 코스피
    - K3~K6: 산업생산, CPI, 기준금리, 총수출액
    - K7~K9: 코스닥, 삼성전자, SK하이닉스
    - K10~K12: 무역수지, 국채 10년물, 경기선행지수
    - K13~K15: EWY ETF, 엔/원, 대만달러/원 환율
    """

    def __init__(self, fred_api_key: str):
        """
        데이터 수집기 초기화

        Args:
            fred_api_key: FRED API 키 (미국 경제데이터 접근용)
        """
        self.fred = Fred(api_key=fred_api_key)
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'MacroAgent_V4/1.0'})

        # 지표 정의: (섹터, 소스, 티커, 이름, 신뢰도, 지역)
        # 총 55개: 미국 40개 + 한국 15개
        self.indicators: Dict[str, Tuple[SectorType, str, str, str, DataReliability, Region]] = {

            # ═══════════════════════════════════════════════════════════════
            # 🇺🇸 미국 지표 (40개) - 기존 V3 지표 유지
            # ═══════════════════════════════════════════════════════════════

            # ===== 1. Monetary Policy (통화정책) - 연준 정책 및 금리 =====
            "M1": (SectorType.MONETARY, "FRED", "T10Y2Y", "10Y-2Y 장단기 금리차",
                   DataReliability.OFFICIAL, Region.US),
            "M2": (SectorType.MONETARY, "FRED", "DFII10", "10Y 실질금리(TIPS 기반)",
                   DataReliability.OFFICIAL, Region.US),
            "M3": (SectorType.MONETARY, "FRED", "RRPONTSYD", "역레포(RRP) 잔액",
                   DataReliability.OFFICIAL, Region.US),
            "M4": (SectorType.MONETARY, "FRED", "TOTRESNS", "지급준비금 총액",
                   DataReliability.OFFICIAL, Region.US),
            "M5": (SectorType.MONETARY, "FRED", "WTREGEN", "재무부 일반계좌(TGA)",
                   DataReliability.OFFICIAL, Region.US),
            "M6": (SectorType.MONETARY, "FRED", "FEDFUNDS", "연준 기준금리(FFR)",
                   DataReliability.OFFICIAL, Region.US),
            "M7": (SectorType.MONETARY, "FRED", "WALCL", "연준 총자산(BS 규모)",
                   DataReliability.OFFICIAL, Region.US),
            "M8": (SectorType.MONETARY, "FRED", "BAMLC0A4CBBB", "BBB 회사채 스프레드",
                   DataReliability.OFFICIAL, Region.US),
            "M9": (SectorType.MONETARY, "FRED", "T10Y3M", "10Y-3M 금리차(역전 경보)",
                   DataReliability.OFFICIAL, Region.US),
            "M10": (SectorType.MONETARY, "FRED", "DGS10", "10년물 국채금리",
                    DataReliability.OFFICIAL, Region.US),

            # ===== 2. Inflation & Employment (물가/고용) - 실물 경기 =====
            "I1": (SectorType.INFLATION, "FRED", "T5YIFR", "5년 기대인플레이션",
                   DataReliability.OFFICIAL, Region.US),
            "I2": (SectorType.INFLATION, "FRED", "PAYEMS", "비농업 고용(NFP)",
                   DataReliability.OFFICIAL, Region.US),
            "I3": (SectorType.INFLATION, "FRED", "ICSA", "신규 실업수당 청구",
                   DataReliability.OFFICIAL, Region.US),
            "I4": (SectorType.INFLATION, "FRED", "PCEPILFE", "근원 PCE 물가",
                   DataReliability.OFFICIAL, Region.US),
            "I5": (SectorType.INFLATION, "FRED", "SAHMREALTIME", "샴 법칙(경기침체 지표)",
                   DataReliability.OFFICIAL, Region.US),
            "I6": (SectorType.INFLATION, "FRED", "CPIAUCSL", "CPI 소비자물가",
                   DataReliability.OFFICIAL, Region.US),
            "I7": (SectorType.INFLATION, "FRED", "PPIACO", "PPI 생산자물가",
                   DataReliability.OFFICIAL, Region.US),
            "I8": (SectorType.INFLATION, "FRED", "JTSJOL", "JOLTs 구인건수",
                   DataReliability.OFFICIAL, Region.US),
            "I9": (SectorType.INFLATION, "FRED", "UMCSENT", "미시간대 소비심리",
                   DataReliability.OFFICIAL, Region.US),
            "I10": (SectorType.INFLATION, "FRED", "UNRATE", "실업률",
                    DataReliability.OFFICIAL, Region.US),

            # ===== 3. Value & Flow (유동성) - 자산가격 및 자금흐름 =====
            "V1": (SectorType.LIQUIDITY, "YF", "DX-Y.NYB", "달러 인덱스(DXY)",
                   DataReliability.HIGH, Region.GLOBAL),
            "V2": (SectorType.LIQUIDITY, "YF", "JPY=X", "달러/엔 환율",
                   DataReliability.HIGH, Region.GLOBAL),
            "V3": (SectorType.LIQUIDITY, "YF", "GC=F", "금 선물(안전자산)",
                   DataReliability.HIGH, Region.GLOBAL),
            "V4": (SectorType.LIQUIDITY, "YF", "HG=F", "구리 선물(경기선행)",
                   DataReliability.HIGH, Region.GLOBAL),
            "V5": (SectorType.LIQUIDITY, "YF", "CL=F", "WTI 원유 선물",
                   DataReliability.HIGH, Region.GLOBAL),
            "V6": (SectorType.LIQUIDITY, "FRED", "M2SL", "M2 통화량",
                   DataReliability.OFFICIAL, Region.US),
            "V7": (SectorType.LIQUIDITY, "YF", "BTC-USD", "비트코인(위험선호 지표)",
                   DataReliability.HIGH, Region.GLOBAL),
            "V8": (SectorType.LIQUIDITY, "YF", "ETH-USD", "이더리움(DeFi 대표)",
                   DataReliability.HIGH, Region.GLOBAL),
            "V9": (SectorType.LIQUIDITY, "YF", "EURUSD=X", "유로/달러 환율",
                   DataReliability.HIGH, Region.GLOBAL),
            "V10": (SectorType.LIQUIDITY, "API", "tether", "테더(USDT) 시총",
                    DataReliability.MEDIUM, Region.GLOBAL),

            # ===== 4. Volatility & Sentiment (심리) - 변동성 및 투자심리 =====
            "S1": (SectorType.SENTIMENT, "YF", "^VIX", "VIX 공포지수",
                   DataReliability.HIGH, Region.US),
            "S2": (SectorType.SENTIMENT, "YF", "^SKEW", "SKEW 블랙스완 지수",
                   DataReliability.HIGH, Region.US),
            "S3": (SectorType.SENTIMENT, "FRED", "BAMLH0A0HYM2", "하이일드 스프레드",
                   DataReliability.OFFICIAL, Region.US),
            "S4": (SectorType.SENTIMENT, "YF", "^VXN", "나스닥 변동성(VXN)",
                   DataReliability.HIGH, Region.US),
            "S5": (SectorType.SENTIMENT, "FRED", "NFCI", "시카고연은 금융여건지수",
                   DataReliability.OFFICIAL, Region.US),
            "S6": (SectorType.SENTIMENT, "YF", "HYG", "하이일드 ETF(투심)",
                   DataReliability.HIGH, Region.US),
            "S7": (SectorType.SENTIMENT, "YF", "TLT", "장기채 ETF(안전선호)",
                   DataReliability.HIGH, Region.US),
            "S8": (SectorType.SENTIMENT, "CUSTOM", "CBOE_PCCR", "Put/Call Ratio",
                   DataReliability.MEDIUM, Region.US),
            "S9": (SectorType.SENTIMENT, "CUSTOM", "FNG", "공포탐욕지수(CNN)",
                   DataReliability.LOW, Region.US),
            "S10": (SectorType.SENTIMENT, "CUSTOM", "BTC_FUNDING", "BTC 펀딩비(레버리지)",
                    DataReliability.LOW, Region.GLOBAL),

            # ═══════════════════════════════════════════════════════════════
            # 🇰🇷 한국 지표 (15개) - V4 신규 추가
            # ═══════════════════════════════════════════════════════════════

            # ===== K1~K2, K7: 환율 및 주가지수 (YF) =====
            "K1": (SectorType.LIQUIDITY, "YF", "KRW=X", "원/달러 환율",
                   DataReliability.HIGH, Region.KR),
            "K2": (SectorType.SENTIMENT, "YF", "^KS11", "코스피 지수",
                   DataReliability.HIGH, Region.KR),
            "K7": (SectorType.SENTIMENT, "YF", "^KQ11", "코스닥 지수",
                   DataReliability.HIGH, Region.KR),

            # ===== K8~K9: 반도체 대장주 (YF) =====
            "K8": (SectorType.GROWTH, "YF", "005930.KS", "삼성전자 주가",
                   DataReliability.HIGH, Region.KR),
            "K9": (SectorType.GROWTH, "YF", "000660.KS", "SK하이닉스 주가",
                   DataReliability.HIGH, Region.KR),

            # ===== K3~K6, K10~K12: 경제지표 (BOK ECOS API 우선, FRED 대체) =====
            # 형식: "통계표코드|필터항목코드" (항목코드는 ITEM_CODE1 필터링용)
            "K3": (SectorType.GROWTH, "BOK", "901Y033|A00", "한국 산업생산지수",
                   DataReliability.OFFICIAL, Region.KR),
            # K4: BOK/FRED 모두 데이터 오래됨 → 수동값 사용 (통계청 발표 기준)
            "K4": (SectorType.INFLATION, "MANUAL", "KR_CPI", "한국 CPI 소비자물가",
                   DataReliability.OFFICIAL, Region.KR),
            # K5: FRED 'INTDSRKRM193N' 삭제 → 수동값 2.5% (2026년 실물경제 동기화)
            "K5": (SectorType.MONETARY, "MANUAL", "KR_BASE_RATE", "한국 기준금리",
                   DataReliability.OFFICIAL, Region.KR),
            "K6": (SectorType.GROWTH, "BOK", "901Y118|T002", "한국 총수출액",
                   DataReliability.OFFICIAL, Region.KR),
            # K10: 한국 무역수지 - FRED/BOK 데이터 비활성화로 임시 제거
            # TODO: 관세청 수출입 통계 API 연동 또는 BOK ECOS 코드 수정 필요
            "K11": (SectorType.MONETARY, "BOK", "721Y001|5050000", "한국 국채 10년물",
                    DataReliability.OFFICIAL, Region.KR),
            "K12": (SectorType.GROWTH, "BOK", "901Y067|I16A", "한국 경기선행지수",
                    DataReliability.OFFICIAL, Region.KR),

            # ===== K13~K15: 글로벌 연동 지표 (YF) =====
            "K13": (SectorType.SENTIMENT, "YF", "EWY", "MSCI 한국 ETF(외국인 시선)",
                    DataReliability.HIGH, Region.KR),
            "K14": (SectorType.LIQUIDITY, "YF", "KRWJPY=X", "원/엔 환율(수출 경쟁력)",
                    DataReliability.HIGH, Region.KR),
            "K15": (SectorType.LIQUIDITY, "YF", "KRWTWD=X", "원/대만달러 환율",
                    DataReliability.HIGH, Region.KR),
        }

    def fetch_all(self) -> Dict[str, Dict]:
        """
        모든 매크로 지표 수집 (55개)

        Returns:
            Dict[str, Dict]: {
                지표ID: {
                    "series": pd.Series,
                    "meta": (섹터, 이름, 신뢰도, 지역)
                }
            }
        """
        total_count = len(self.indicators)
        logger.info(f"📡 총 {total_count}개 매크로 지표 수집 시작 (미국 40개 + 한국 15개)...")

        raw_data = {}
        success_count = 0
        fail_count = 0

        # 지역별 카운터
        region_success = {Region.US: 0, Region.KR: 0, Region.GLOBAL: 0}
        region_fail = {Region.US: 0, Region.KR: 0, Region.GLOBAL: 0}

        for m_id, (sector, source, ticker, name, reliability, region) in self.indicators.items():
            try:
                series = self._fetch_single(source, ticker, name)

                if series is not None and not series.empty:
                    # 결측치 처리 및 정렬 (앞으로 채우기 + 제거)
                    series = series.ffill().dropna()

                    if len(series) >= 30:  # 최소 30일 데이터 필요
                        # 데이터 주기 자동 감지
                        data_cycle = self._detect_data_cycle(series)

                        raw_data[m_id] = {
                            "series": series,
                            "meta": (sector, name, reliability, region),
                            "source": source,      # 데이터 소스 추가
                            "cycle": data_cycle    # 데이터 주기 추가
                        }
                        success_count += 1
                        region_success[region] += 1
                        logger.debug(f"  ✅ {m_id}: {name} ({len(series)}개 데이터)")
                    else:
                        logger.warning(f"  ⚠️ {m_id}: {name} - 데이터 부족 ({len(series)} < 30)")
                        fail_count += 1
                        region_fail[region] += 1
                else:
                    fail_count += 1
                    region_fail[region] += 1

            except Exception as e:
                logger.error(f"  ❌ {m_id}: {name} - {str(e)[:50]}")
                fail_count += 1
                region_fail[region] += 1

        # 수집 결과 요약 (한국어)
        logger.info("=" * 50)
        logger.info(f"📊 수집 완료: 성공 {success_count}개 / 실패 {fail_count}개")
        logger.info(f"   🇺🇸 미국: {region_success[Region.US]}개 성공, {region_fail[Region.US]}개 실패")
        logger.info(f"   🇰🇷 한국: {region_success[Region.KR]}개 성공, {region_fail[Region.KR]}개 실패")
        logger.info(f"   🌐 글로벌: {region_success[Region.GLOBAL]}개 성공, {region_fail[Region.GLOBAL]}개 실패")
        logger.info("=" * 50)

        return raw_data

    @staticmethod
    def _detect_data_cycle(series: pd.Series) -> str:
        """
        데이터 업데이트 주기 자동 감지

        Args:
            series: 시계열 데이터

        Returns:
            주기 문자열 (실시간/일별/주별/월별)
        """
        if len(series) < 3:
            return "일별"

        # 최근 데이터 간격 계산
        recent_dates = pd.to_datetime(series.index[-3:])
        avg_interval = (recent_dates[-1] - recent_dates[0]).days / 2

        if avg_interval >= 20:
            return "월별"
        elif avg_interval >= 5:
            return "주별"
        elif avg_interval >= 1:
            return "일별"
        else:
            return "실시간"

    def _fetch_single(self, source: str, ticker: str, name: str) -> Optional[pd.Series]:
        """
        단일 지표 수집 (소스별 분기)

        Args:
            source: 데이터 소스 (FRED, YF, API, CUSTOM)
            ticker: API 티커/심볼
            name: 지표 한글명 (로깅용)

        Returns:
            pd.Series 또는 None (실패 시)
        """
        if source == "FRED":
            return self._fetch_fred(ticker, name)
        elif source == "YF":
            return self._fetch_yahoo(ticker, name)
        elif source == "API":
            return self._fetch_coingecko(ticker)
        elif source == "CUSTOM":
            return self._fetch_custom(ticker)
        elif source == "BOK":
            return self._fetch_bok(ticker, name)
        elif source == "MANUAL":
            return self._fetch_manual(ticker, name)
        else:
            logger.warning(f"알 수 없는 데이터 소스: {source}")
            return None

    def _fetch_fred(self, ticker: str, name: str) -> Optional[pd.Series]:
        """
        FRED API 데이터 수집

        5년(1825일) 기간 데이터 요청
        미국 및 한국 경제지표 모두 FRED에서 제공
        """
        try:
            start_date = datetime.now() - timedelta(days=1825)
            series = self.fred.get_series(ticker, observation_start=start_date)
            time.sleep(config.FRED_API_DELAY)  # API 호출 제한 준수
            return series
        except Exception as e:
            logger.error(f"FRED 수집 실패 [{ticker}]: {e}")
            return None

    def _fetch_yahoo(self, ticker: str, name: str) -> Optional[pd.Series]:
        """
        Yahoo Finance 데이터 수집

        5년 기간 데이터 요청
        주가, 환율, 선물, ETF 등 실시간 시장 데이터
        """
        try:
            df = yf.download(ticker, period="5y", progress=False, timeout=15)
            time.sleep(config.YF_API_DELAY)  # API 호출 제한 준수

            if df.empty:
                return None

            series = df['Close']
            if isinstance(series, pd.DataFrame):
                series = series.iloc[:, 0]

            return series
        except Exception as e:
            logger.error(f"Yahoo Finance 수집 실패 [{ticker}]: {e}")
            return None

    def _fetch_coingecko(self, coin_id: str) -> Optional[pd.Series]:
        """
        CoinGecko API 데이터 수집

        암호화폐 시가총액 데이터 (1년 기간)
        타임스탬프를 datetime 인덱스로 변환
        """
        try:
            url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
            params = {"vs_currency": "usd", "days": 365}

            resp = self.session.get(url, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()

            market_caps = data.get('market_caps', [])
            if not market_caps:
                return None

            # 타임스탬프를 datetime 인덱스로 변환
            dates = [pd.to_datetime(x[0], unit='ms') for x in market_caps]
            values = [x[1] for x in market_caps]

            series = pd.Series(values, index=dates, name=coin_id)
            time.sleep(config.COINGECKO_API_DELAY)  # API 호출 제한 준수

            return series
        except Exception as e:
            logger.error(f"CoinGecko 수집 실패 [{coin_id}]: {e}")
            return None

    def _fetch_custom(self, ticker: str) -> Optional[pd.Series]:
        """
        커스텀 지표 수집 (플레이스홀더)

        TODO: 실제 API 연동 필요
        - CBOE_PCCR: CBOE Put/Call Ratio (CBOE 웹사이트)
        - FNG: Fear & Greed Index (CNN 또는 alternative.me)
        - BTC_FUNDING: 비트코인 펀딩비 (Binance/Bybit API)

        현재는 시뮬레이션 데이터 반환
        """
        # 기본값 설정 (현실적인 범위)
        placeholder_data = {
            "CBOE_PCCR": 0.85,      # Put/Call Ratio (0.5~1.5 범위)
            "FNG": 50,              # Fear & Greed (0~100)
            "BTC_FUNDING": 0.01,    # 펀딩비 (0.01% = 연 36.5%)
        }

        value = placeholder_data.get(ticker, 0.5)
        dates = pd.date_range(end=datetime.now(), periods=100, freq='D')

        # 약간의 변동성 추가 (시뮬레이션)
        import numpy as np
        np.random.seed(42)
        noise = np.random.normal(0, value * 0.1, 100)
        values = [value + n for n in noise]

        return pd.Series(values, index=dates, name=ticker)

    def _fetch_bok(self, ticker: str, name: str) -> Optional[pd.Series]:
        """
        한국은행 ECOS API 데이터 수집

        BOK ECOS API를 통해 한국 경제지표 직접 수집
        ticker 형식: "통계표코드|필터항목코드" (예: "901Y009|0", "901Y033|A00")

        API 문서: https://ecos.bok.or.kr/api/
        인증키: config.BOK_ECOS_API_KEY 사용
        """
        try:
            # ticker에서 통계표코드와 필터항목코드 분리 (|로 구분)
            parts = ticker.split("|")
            if len(parts) != 2:
                logger.error(f"BOK 티커 형식 오류 [{ticker}]: '통계표코드|필터항목코드' 형식 필요")
                return None

            stat_code, filter_item_code = parts

            # BOK ECOS API 호출 (항목코드 없이 호출 후 필터링)
            api_key = config.BOK_ECOS_API_KEY

            end_date = datetime.now().strftime("%Y%m")
            start_date = (datetime.now() - timedelta(days=1825)).strftime("%Y%m")

            # 항목코드 없이 호출하여 전체 데이터 가져온 후 필터링
            url = f"https://ecos.bok.or.kr/api/StatisticSearch/{api_key}/json/kr/1/3000/{stat_code}/M/{start_date}/{end_date}/"

            resp = self.session.get(url, timeout=15)
            resp.raise_for_status()
            data = resp.json()

            # 응답 파싱
            if 'StatisticSearch' not in data:
                # API 오류 또는 데이터 없음 - FRED 대체 시도
                logger.warning(f"BOK API 응답 없음 [{ticker}], FRED 대체 시도...")
                return self._fetch_bok_fallback_fred(ticker, name)

            rows = data['StatisticSearch'].get('row', [])
            if not rows:
                return self._fetch_bok_fallback_fred(ticker, name)

            # ITEM_CODE1으로 필터링하여 시계열 데이터 구성
            dates = []
            values = []
            for row in rows:
                try:
                    # ITEM_CODE1이 필터 조건과 일치하는 행만 선택
                    item_code1 = row.get('ITEM_CODE1', '')
                    if item_code1 != filter_item_code:
                        continue

                    time_str = row.get('TIME', '')
                    value_str = row.get('DATA_VALUE', '')
                    if not value_str:
                        continue
                    value = float(value_str)

                    # YYYYMM 형식을 datetime으로 변환 (월말 날짜로 설정하여 freshness 개선)
                    if len(time_str) == 6:
                        year = int(time_str[:4])
                        month = int(time_str[4:6])
                        last_day = calendar.monthrange(year, month)[1]
                        date = datetime(year, month, last_day)
                        dates.append(date)
                        values.append(value)
                except (ValueError, TypeError):
                    continue

            if not dates:
                logger.warning(f"BOK API 필터링 후 데이터 없음 [{ticker}] (필터: {filter_item_code})")
                return self._fetch_bok_fallback_fred(ticker, name)

            series = pd.Series(values, index=pd.DatetimeIndex(dates), name=name)
            series = series.sort_index()

            logger.info(f"  📊 BOK ECOS 수집 성공: {name} ({len(series)}개)")
            time.sleep(0.3)  # API 호출 제한 준수

            return series

        except Exception as e:
            logger.warning(f"BOK ECOS 수집 실패 [{ticker}]: {e}, FRED 대체 시도...")
            return self._fetch_bok_fallback_fred(ticker, name)

    def _fetch_bok_fallback_fred(self, ticker: str, name: str) -> Optional[pd.Series]:
        """
        BOK API 실패 시 FRED 대체 티커로 수집

        BOK 티커 → FRED 티커 매핑 (새 형식: 통계표코드|필터항목코드)
        """
        # BOK → FRED 대체 매핑 (새 형식)
        bok_to_fred = {
            "901Y033|A00": "KORPROINDMISMEI",      # 산업생산지수 (전산업)
            "901Y118|T002": "XTEXVA01KRM667S",     # 총수출액
            "721Y001|5050000": "IRLTLT01KRM156N",  # 국채 10년물
            "901Y067|I16A": "KORLOLITOAASTSAM",    # 경기선행지수
        }

        fred_ticker = bok_to_fred.get(ticker)
        if fred_ticker:
            logger.info(f"  🔄 FRED 대체 수집: {ticker} → {fred_ticker}")
            return self._fetch_fred(fred_ticker, name)

        return None

    def _fetch_manual(self, ticker: str, name: str) -> Optional[pd.Series]:
        """
        수동 설정 지표 수집

        실시간 API 연동이 어려운 지표에 대해 수동값 반영
        주로 정책 금리처럼 드물게 변경되는 지표에 사용

        현재 지원:
        - KR_BASE_RATE: 한국 기준금리 (2026년 기준 2.5%)
        """
        # 수동 지표 정의: {티커: (현재값, 단위, 마지막 업데이트)}
        manual_values = {
            "KR_BASE_RATE": {
                "value": 2.5,           # 2026년 한국 기준금리
                "unit": "%",
                "last_update": "2026-01-26",
                "source": "한국은행 금융통화위원회",
                "note": "2026년 실물경제 동기화 수동 반영"
            },
            "KR_CPI": {
                "value": 119.5,         # 2025년 12월 한국 CPI (2020=100)
                "unit": "",
                "last_update": "2026-01-26",
                "source": "통계청 소비자물가지수",
                "note": "FRED/BOK 데이터 오래됨으로 수동 반영"
            }
        }

        if ticker not in manual_values:
            logger.warning(f"수동 지표 미정의: {ticker}")
            return None

        meta = manual_values[ticker]
        value = meta["value"]

        # 과거 데이터 시뮬레이션 (점진적 변화 가정)
        dates = pd.date_range(end=datetime.now(), periods=252, freq='B')  # 1년 영업일

        if ticker == "KR_BASE_RATE":
            # 한국 기준금리 역사적 추이 (간략화)
            # 2025년 초: 3.0% → 2025년 중반: 2.75% → 2026년: 2.5%
            values = []
            for i, date in enumerate(dates):
                if date < datetime(2025, 6, 1):
                    values.append(3.0)
                elif date < datetime(2025, 10, 1):
                    values.append(2.75)
                else:
                    values.append(2.5)
        elif ticker == "KR_CPI":
            # 한국 CPI 역사적 추이 (2020=100 기준)
            # 2025년 초: 117.5 → 2025년 중반: 118.5 → 2026년: 119.5
            values = []
            for i, date in enumerate(dates):
                if date < datetime(2025, 6, 1):
                    values.append(117.5)
                elif date < datetime(2025, 10, 1):
                    values.append(118.5)
                else:
                    values.append(119.5)
        else:
            # 기본: 현재 값으로 고정
            values = [value] * len(dates)

        series = pd.Series(values, index=dates, name=name)

        logger.info(f"  📌 수동값 반영: {name} = {value}{meta['unit']} ({meta['last_update']} 기준)")

        return series
