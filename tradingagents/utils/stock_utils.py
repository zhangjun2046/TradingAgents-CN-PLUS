"""
股票工具函数
提供股票代码识别、分类和处理功能
"""

import re
from typing import Dict, List, Optional, Tuple
from enum import Enum

# 导入统一日志系统
from tradingagents.utils.logging_init import get_logger
logger = get_logger("default")


class StockMarket(Enum):
    """股票市场枚举"""
    CHINA_A = "china_a"      # 中国A股
    HONG_KONG = "hong_kong"  # 港股
    US = "us"                # 美股
    UNKNOWN = "unknown"      # 未知


# 市场标识常量（内部规范形态使用的市场码）
MARKET_CN = "CN"
MARKET_HK = "HK"
MARKET_US = "US"

# 上游可能传入的市场提示别名（前端/API 使用中文，内部统一为市场码）
_MARKET_HINT_ALIASES = {
    "CN": MARKET_CN,
    "A股": MARKET_CN,
    "沪深": MARKET_CN,
    "CHINA": MARKET_CN,
    "CHINA_A": MARKET_CN,
    "HK": MARKET_HK,
    "港股": MARKET_HK,
    "HONG_KONG": MARKET_HK,
    "HONGKONG": MARKET_HK,
    "US": MARKET_US,
    "美股": MARKET_US,
    "USA": MARKET_US,
}

_STOCK_MARKET_TO_CODE = {
    StockMarket.CHINA_A: MARKET_CN,
    StockMarket.HONG_KONG: MARKET_HK,
    StockMarket.US: MARKET_US,
}

# 各市场需要剥离的代码后缀
_CN_SUFFIXES = ('.SH', '.SZ', '.SS', '.XSHE', '.XSHG', '.BJ')
_HK_SUFFIXES = ('.HK',)
_US_SUFFIXES = ('.US', '.N', '.O', '.NYSE', '.NASDAQ')


class StockUtils:
    """股票工具类"""
    
    @staticmethod
    def identify_stock_market(ticker: str) -> StockMarket:
        """
        识别股票代码所属市场

        Args:
            ticker: 股票代码

        Returns:
            StockMarket: 股票市场类型
        """
        if not ticker:
            return StockMarket.UNKNOWN

        ticker = str(ticker).strip().upper()

        # 中国A股：6位数字
        if re.match(r'^\d{6}$', ticker):
            return StockMarket.CHINA_A

        # 港股：4-5位数字.HK 或 纯4-5位数字（支持0700.HK、09988.HK、00700、9988格式）
        if re.match(r'^\d{4,5}\.HK$', ticker) or re.match(r'^\d{4,5}$', ticker):
            return StockMarket.HONG_KONG

        # 美股：1-5位字母
        if re.match(r'^[A-Z]{1,5}$', ticker):
            return StockMarket.US

        return StockMarket.UNKNOWN
    
    @staticmethod
    def is_china_stock(ticker: str) -> bool:
        """
        判断是否为中国A股
        
        Args:
            ticker: 股票代码
            
        Returns:
            bool: 是否为中国A股
        """
        return StockUtils.identify_stock_market(ticker) == StockMarket.CHINA_A
    
    @staticmethod
    def is_hk_stock(ticker: str) -> bool:
        """
        判断是否为港股
        
        Args:
            ticker: 股票代码
            
        Returns:
            bool: 是否为港股
        """
        return StockUtils.identify_stock_market(ticker) == StockMarket.HONG_KONG
    
    @staticmethod
    def is_us_stock(ticker: str) -> bool:
        """
        判断是否为美股
        
        Args:
            ticker: 股票代码
            
        Returns:
            bool: 是否为美股
        """
        return StockUtils.identify_stock_market(ticker) == StockMarket.US
    
    @staticmethod
    def get_currency_info(ticker: str) -> Tuple[str, str]:
        """
        根据股票代码获取货币信息
        
        Args:
            ticker: 股票代码
            
        Returns:
            Tuple[str, str]: (货币名称, 货币符号)
        """
        market = StockUtils.identify_stock_market(ticker)
        
        if market == StockMarket.CHINA_A:
            return "人民币", "¥"
        elif market == StockMarket.HONG_KONG:
            return "港币", "HK$"
        elif market == StockMarket.US:
            return "美元", "$"
        else:
            return "未知", "?"
    
    @staticmethod
    def get_data_source(ticker: str) -> str:
        """
        根据股票代码获取推荐的数据源
        
        Args:
            ticker: 股票代码
            
        Returns:
            str: 数据源名称
        """
        market = StockUtils.identify_stock_market(ticker)
        
        if market == StockMarket.CHINA_A:
            return "china_unified"  # 使用统一的中国股票数据源
        elif market == StockMarket.HONG_KONG:
            return "yahoo_finance"  # 港股使用Yahoo Finance
        elif market == StockMarket.US:
            return "yahoo_finance"  # 美股使用Yahoo Finance
        else:
            return "unknown"
    
    @staticmethod
    def normalize_hk_ticker(ticker: str) -> str:
        """
        标准化港股代码格式
        
        Args:
            ticker: 原始港股代码
            
        Returns:
            str: 标准化后的港股代码
        """
        if not ticker:
            return ticker
            
        ticker = str(ticker).strip().upper()
        
        # 如果是纯4-5位数字，添加.HK后缀
        if re.match(r'^\d{4,5}$', ticker):
            return f"{ticker}.HK"

        # 如果已经是正确格式，直接返回
        if re.match(r'^\d{4,5}\.HK$', ticker):
            return ticker
            
        return ticker
    
    @staticmethod
    def get_market_info(ticker: str) -> Dict:
        """
        获取股票市场的详细信息
        
        Args:
            ticker: 股票代码
            
        Returns:
            Dict: 市场信息字典
        """
        market = StockUtils.identify_stock_market(ticker)
        currency_name, currency_symbol = StockUtils.get_currency_info(ticker)
        data_source = StockUtils.get_data_source(ticker)
        
        market_names = {
            StockMarket.CHINA_A: "中国A股",
            StockMarket.HONG_KONG: "港股",
            StockMarket.US: "美股",
            StockMarket.UNKNOWN: "未知市场"
        }
        
        return {
            "ticker": ticker,
            "market": market.value,
            "market_name": market_names[market],
            "currency_name": currency_name,
            "currency_symbol": currency_symbol,
            "data_source": data_source,
            "is_china": market == StockMarket.CHINA_A,
            "is_hk": market == StockMarket.HONG_KONG,
            "is_us": market == StockMarket.US
        }


def _strip_suffixes(value: str, suffixes: Tuple[str, ...]) -> str:
    """剥离代码后缀（不区分大小写，已在调用前转大写）"""
    for suffix in suffixes:
        if value.endswith(suffix):
            return value[: -len(suffix)]
    return value


def detect_market(ticker: str, market_hint: Optional[str] = None) -> str:
    """
    确定股票所属市场，显式提示优先于代码格式推断。

    代码格式推断存在歧义（例如被错误补零后的 001810 会被当成A股），
    因此上游一旦掌握真实市场就必须通过 market_hint 传入。

    Args:
        ticker: 股票代码
        market_hint: 上游传入的市场提示，支持 CN/HK/US 及中文别名

    Returns:
        str: 市场码 CN / HK / US

    Raises:
        ValueError: 市场提示无法识别，或代码格式无法推断出市场
    """
    if market_hint:
        normalized_hint = str(market_hint).strip().upper()
        if normalized_hint in _MARKET_HINT_ALIASES:
            return _MARKET_HINT_ALIASES[normalized_hint]
        raise ValueError(f"无法识别的市场提示: {market_hint}")

    market = StockUtils.identify_stock_market(ticker)
    if market in _STOCK_MARKET_TO_CODE:
        return _STOCK_MARKET_TO_CODE[market]

    # identify_stock_market 不认带交易所后缀的写法（如 600519.SH），按后缀补充判定
    value = str(ticker).strip().upper()
    for suffixes, market_code in (
        (_HK_SUFFIXES, MARKET_HK),
        (_CN_SUFFIXES, MARKET_CN),
        (_US_SUFFIXES, MARKET_US),
    ):
        if value.endswith(suffixes):
            return market_code

    raise ValueError(f"无法根据代码推断市场，请显式传入 market: {ticker}")


def normalize_symbol(ticker: str, market: str) -> str:
    """
    生成内部规范形态的股票代码，仅用于状态传递、数据库主键与日志。

    A股补齐到6位，港股补齐到5位，美股转大写。
    严禁对港股使用6位补零：01810 一旦变成 001810 就会与基金代码冲突。

    Args:
        ticker: 原始股票代码，可带市场后缀
        market: 市场码 CN / HK / US

    Returns:
        str: 规范形态代码

    Raises:
        ValueError: 代码为空、市场未知或代码与市场不匹配
    """
    if ticker is None or not str(ticker).strip():
        raise ValueError("股票代码不能为空")

    value = str(ticker).strip().upper()

    if market == MARKET_HK:
        value = _strip_suffixes(value, _HK_SUFFIXES)
        if not value.isdigit() or len(value) > 5:
            raise ValueError(f"无效港股代码: {ticker}")
        return value.zfill(5)

    if market == MARKET_CN:
        value = _strip_suffixes(value, _CN_SUFFIXES)
        if not value.isdigit() or len(value) > 6:
            raise ValueError(f"无效A股代码: {ticker}")
        return value.zfill(6)

    if market == MARKET_US:
        return _strip_suffixes(value, _US_SUFFIXES)

    raise ValueError(f"未知市场: {market}")


def to_provider_symbol(ticker: str, market: str, provider: str) -> str:
    """
    把规范形态代码转换为具体数据源需要的格式。

    各数据源期望格式并不统一，例如同一只小米集团：
    Yahoo/FinnHub 用 1810.HK，AKShare 新浪系用 01810，Tushare 用 01810.HK。

    Args:
        ticker: 股票代码（任意常见形态）
        market: 市场码 CN / HK / US
        provider: 数据源标识，如 yahoo / finnhub / akshare / eastmoney / tushare

    Returns:
        str: 目标数据源可直接使用的代码

    Raises:
        ValueError: 市场未知或代码非法
    """
    symbol = normalize_symbol(ticker, market)
    provider_key = str(provider).strip().lower()

    if market == MARKET_HK:
        if provider_key in ('yahoo', 'yahoo_finance', 'yfinance', 'finnhub'):
            # Yahoo/FinnHub 使用去前导零后补到4位的形式：01810 -> 1810.HK，00700 -> 0700.HK
            return f"{(symbol.lstrip('0') or '0').zfill(4)}.HK"
        if provider_key in ('tushare',):
            return f"{symbol}.HK"
        # AKShare 新浪系、东方财富等使用5位纯数字
        return symbol

    if market == MARKET_CN:
        if provider_key in ('tushare',):
            return f"{symbol}.SH" if symbol.startswith(('60', '68', '9')) else f"{symbol}.SZ"
        if provider_key in ('yahoo', 'yahoo_finance', 'yfinance'):
            return f"{symbol}.SS" if symbol.startswith(('60', '68')) else f"{symbol}.SZ"
        return symbol

    return symbol


def symbol_aliases(ticker: str, market: str) -> List[str]:
    """
    生成同一只股票的常见代码写法，供新闻相关性判定使用。

    港股 01810 会返回 01810 / 1810 / 01810.HK / 1810.HK，
    这样正文里写成任意一种形式都能被识别为命中。

    Args:
        ticker: 股票代码
        market: 市场码 CN / HK / US

    Returns:
        List[str]: 去重后的代码别名列表，规范形态排在首位
    """
    symbol = normalize_symbol(ticker, market)
    candidates = [symbol]

    if market == MARKET_HK:
        stripped = symbol.lstrip('0') or '0'
        candidates.extend([
            stripped,
            stripped.zfill(4),
            f"{symbol}.HK",
            f"{stripped}.HK",
            f"{stripped.zfill(4)}.HK",
        ])
    elif market == MARKET_CN:
        candidates.extend([f"{symbol}.SH", f"{symbol}.SZ"])

    unique_aliases = []
    for candidate in candidates:
        if candidate and candidate not in unique_aliases:
            unique_aliases.append(candidate)

    return unique_aliases


# 便捷函数，保持向后兼容
def is_china_stock(ticker: str) -> bool:
    """判断是否为中国A股（向后兼容）"""
    return StockUtils.is_china_stock(ticker)


def is_hk_stock(ticker: str) -> bool:
    """判断是否为港股"""
    return StockUtils.is_hk_stock(ticker)


def is_us_stock(ticker: str) -> bool:
    """判断是否为美股"""
    return StockUtils.is_us_stock(ticker)


def get_stock_market_info(ticker: str) -> Dict:
    """获取股票市场信息"""
    return StockUtils.get_market_info(ticker)
