#!/usr/bin/env python3
"""
统一代码规范层测试

验证：
1. detect_market 显式市场提示优先，无法判定时抛错而不是默认A股
2. normalize_symbol 港股归一为5位、A股归一为6位、美股大写
3. to_provider_symbol 按数据源输出正确格式
4. symbol_aliases 生成的别名可覆盖新闻正文里的各种写法
5. 核心不变量：任何港股输入都不得产出 001810 / 000700 / 006030 这类6位补零码

不依赖外网、MongoDB、pandas。
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tradingagents.utils.stock_utils import (  # noqa: E402
    MARKET_CN,
    MARKET_HK,
    MARKET_US,
    detect_market,
    normalize_symbol,
    symbol_aliases,
    to_provider_symbol,
)

# 港股绝对不能出现的补零结果
FORBIDDEN_HK_RESULTS = {"001810", "000700", "006030", "000175", "009988"}


def test_detect_market_with_explicit_hint():
    """显式市场提示优先，支持中文别名"""
    assert detect_market("001810", "HK") == MARKET_HK, "显式 HK 必须覆盖代码格式推断"
    assert detect_market("01810", "港股") == MARKET_HK
    assert detect_market("600519", "A股") == MARKET_CN
    assert detect_market("AAPL", "美股") == MARKET_US


def test_detect_market_from_code_format():
    """无提示时按代码格式推断，含带交易所后缀的写法"""
    assert detect_market("01810") == MARKET_HK
    assert detect_market("0700") == MARKET_HK
    assert detect_market("01810.HK") == MARKET_HK
    assert detect_market("600519") == MARKET_CN
    assert detect_market("600519.SH") == MARKET_CN
    assert detect_market("000001.SZ") == MARKET_CN
    assert detect_market("AAPL") == MARKET_US


def test_detect_market_raises_instead_of_defaulting_to_cn():
    """无法判定时必须抛错，不能默认成A股"""
    for bad_input in ["", "12345678", "不是代码", "TOOLONGSYMBOL"]:
        try:
            result = detect_market(bad_input)
        except ValueError:
            continue
        raise AssertionError(f"输入 {bad_input!r} 应当抛 ValueError，实际返回 {result}")

    try:
        detect_market("01810", "火星股")
    except ValueError:
        pass
    else:
        raise AssertionError("无法识别的市场提示应当抛 ValueError")


def test_normalize_symbol_hk_never_zfills_to_six():
    """港股统一5位，任何写法都不能变成6位"""
    for raw in ["01810", "1810", "01810.HK", "1810.hk", "0700", "700", "00700"]:
        result = normalize_symbol(raw, MARKET_HK)
        assert len(result) == 5, f"{raw} 归一后应为5位，实际 {result}"
        assert result not in FORBIDDEN_HK_RESULTS, f"{raw} 被错误补零成 {result}"

    assert normalize_symbol("01810", MARKET_HK) == "01810"
    assert normalize_symbol("1810", MARKET_HK) == "01810"
    assert normalize_symbol("0700", MARKET_HK) == "00700"


def test_normalize_symbol_cn_and_us():
    """A股补齐6位，美股大写并剥离后缀"""
    assert normalize_symbol("600519", MARKET_CN) == "600519"
    assert normalize_symbol("1", MARKET_CN) == "000001"
    assert normalize_symbol("000001.SZ", MARKET_CN) == "000001"
    assert normalize_symbol("600519.SH", MARKET_CN) == "600519"
    assert normalize_symbol("aapl", MARKET_US) == "AAPL"
    assert normalize_symbol("TSLA.US", MARKET_US) == "TSLA"


def test_normalize_symbol_rejects_invalid_input():
    """非法输入必须抛 ValueError"""
    bad_cases = [
        (None, MARKET_HK),
        ("", MARKET_HK),
        ("ABCDE", MARKET_HK),
        ("123456", MARKET_HK),
        ("1234567", MARKET_CN),
        ("01810", "MARS"),
    ]
    for raw, market in bad_cases:
        try:
            result = normalize_symbol(raw, market)
        except ValueError:
            continue
        raise AssertionError(f"normalize_symbol({raw!r}, {market!r}) 应抛错，实际返回 {result}")


def test_to_provider_symbol_hk():
    """港股各数据源出参格式"""
    assert to_provider_symbol("01810", MARKET_HK, "yahoo") == "1810.HK"
    assert to_provider_symbol("00700", MARKET_HK, "yahoo") == "0700.HK"
    assert to_provider_symbol("01810", MARKET_HK, "finnhub") == "1810.HK"
    assert to_provider_symbol("01810", MARKET_HK, "tushare") == "01810.HK"
    # AKShare / 东方财富使用5位纯数字
    assert to_provider_symbol("1810", MARKET_HK, "akshare") == "01810"
    assert to_provider_symbol("1810", MARKET_HK, "eastmoney") == "01810"


def test_to_provider_symbol_cn():
    """A股各数据源出参格式"""
    assert to_provider_symbol("600519", MARKET_CN, "tushare") == "600519.SH"
    assert to_provider_symbol("000001", MARKET_CN, "tushare") == "000001.SZ"
    assert to_provider_symbol("600519", MARKET_CN, "yahoo") == "600519.SS"
    assert to_provider_symbol("000001", MARKET_CN, "yahoo") == "000001.SZ"
    assert to_provider_symbol("600519", MARKET_CN, "akshare") == "600519"


def test_to_provider_symbol_never_zfills_hk():
    """任何数据源出参都不能出现港股6位补零码"""
    for provider in ["yahoo", "finnhub", "tushare", "akshare", "eastmoney"]:
        for raw in ["01810", "1810", "0700", "06030"]:
            result = to_provider_symbol(raw, MARKET_HK, provider)
            assert not any(bad in result for bad in FORBIDDEN_HK_RESULTS), \
                f"{provider} 出参 {result} 含非法补零码"


def test_symbol_aliases_hk():
    """港股别名应覆盖常见写法"""
    aliases = symbol_aliases("01810", MARKET_HK)
    for expected in ["01810", "1810", "01810.HK", "1810.HK"]:
        assert expected in aliases, f"别名列表缺少 {expected}: {aliases}"
    assert "001810" not in aliases, "别名中不能出现基金代码 001810"
    # 规范形态排首位，便于日志与落库直接取用
    assert aliases[0] == "01810"

    aliases_700 = symbol_aliases("0700", MARKET_HK)
    assert "00700" in aliases_700 and "700" in aliases_700 and "0700.HK" in aliases_700


def test_symbol_aliases_cn():
    """A股别名包含交易所后缀写法"""
    aliases = symbol_aliases("600519", MARKET_CN)
    assert aliases[0] == "600519"
    assert "600519.SH" in aliases and "600519.SZ" in aliases


if __name__ == "__main__":
    tests = [
        test_detect_market_with_explicit_hint,
        test_detect_market_from_code_format,
        test_detect_market_raises_instead_of_defaulting_to_cn,
        test_normalize_symbol_hk_never_zfills_to_six,
        test_normalize_symbol_cn_and_us,
        test_normalize_symbol_rejects_invalid_input,
        test_to_provider_symbol_hk,
        test_to_provider_symbol_cn,
        test_to_provider_symbol_never_zfills_hk,
        test_symbol_aliases_hk,
        test_symbol_aliases_cn,
    ]
    passed = 0
    for t in tests:
        try:
            t()
            print(f"[PASS] {t.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"[FAIL] {t.__name__}: {e}")
        except Exception as e:
            print(f"[ERROR] {t.__name__}: {type(e).__name__}: {e}")
    print(f"\n{'=' * 60}")
    print(f"测试结果: {passed}/{len(tests)} 通过")
    sys.exit(0 if passed == len(tests) else 1)
