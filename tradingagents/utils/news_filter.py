"""
新闻相关性过滤器
用于过滤与特定股票/公司不相关的新闻，提高新闻分析质量
"""

import re
import unicodedata
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
import logging

# pandas 仅供 DataFrame 接口使用，在方法内部按需导入。
# dict/list 形式的相关性闸门位于落库与大模型之间的热路径上，不应为此拖入 pandas。

logger = logging.getLogger(__name__)

# 未知公司名的占位前缀，命中时说明公司名未解析成功
_UNKNOWN_NAME_PREFIXES = ('股票', '港股', '美股', 'STOCK')

# 公司名后缀，用于派生简称："小米集团" -> "小米"，可识别"小米汽车"这类只带简称的新闻
_COMPANY_NAME_SUFFIXES = (
    '集团股份有限公司', '股份有限公司', '有限公司', '控股集团',
    '集团', '控股', '股份', '公司', '-W', '-S', '-SW',
)

# 新闻条目里标题/正文可能使用的字段名（中英文数据源混用）
_TITLE_KEYS = ('title', '新闻标题', '标题')
_CONTENT_KEYS = ('content', '新闻内容', '内容', 'summary', '摘要')


def _normalize_text(value: str) -> str:
    """
    统一全角/半角形态

    港股名称常带全角后缀（"小米集团－Ｗ"），新闻正文里却写半角，
    不做归一会导致公司名匹配不上，相关性判定直接失效。
    """
    if not value:
        return ''
    return unicodedata.normalize('NFKC', str(value))


def _pick_field(item: Dict[str, Any], keys: Tuple[str, ...]) -> str:
    """从新闻条目中取第一个非空字段"""
    for key in keys:
        value = item.get(key)
        if value:
            return str(value)
    return ''


class NewsRelevanceFilter:
    """基于规则的新闻相关性过滤器"""

    def __init__(self, stock_code: str, company_name: str, market: Optional[str] = None):
        """
        初始化过滤器

        Args:
            stock_code: 股票代码，如 "600036"
            company_name: 公司名称，如 "招商银行"
            market: 市场码 CN/HK/US，用于生成代码别名；为 None 时按代码格式推断
        """
        self.stock_code = stock_code.upper()
        self.company_name = company_name
        self.market = market
        self.company_aliases = self._build_company_aliases(company_name)
        self.has_company_name = bool(self.company_aliases)
        self.code_patterns = self._build_code_patterns(stock_code, market)
        
        # 排除关键词 - 这些词出现时降低相关性
        self.exclude_keywords = [
            'etf', '指数基金', '基金', '指数', 'index', 'fund',
            '权重股', '成分股', '板块', '概念股', '主题基金',
            '跟踪指数', '被动投资', '指数投资', '基金持仓'
        ]
        
        # 包含关键词 - 这些词出现时提高相关性
        self.include_keywords = [
            '业绩', '财报', '公告', '重组', '并购', '分红', '派息',
            '高管', '董事', '股东', '增持', '减持', '回购',
            '年报', '季报', '半年报', '业绩预告', '业绩快报',
            '股东大会', '董事会', '监事会', '重大合同',
            '投资', '收购', '出售', '转让', '合作', '协议'
        ]
        
        # 强相关关键词 - 这些词出现时大幅提高相关性
        self.strong_keywords = [
            '停牌', '复牌', '涨停', '跌停', '限售解禁',
            '股权激励', '员工持股', '定增', '配股', '送股',
            '资产重组', '借壳上市', '退市', '摘帽', 'ST'
        ]

    @staticmethod
    def _build_company_aliases(company_name: str) -> List[str]:
        """
        生成公司名别名列表

        新闻标题常只写简称（"小米汽车交付量创新高"），因此除全称外还要派生去后缀的简称。
        公司名未解析成功（形如"港股01810"）时返回空列表，交由调用方降级处理。
        """
        if not company_name:
            return []

        name = _normalize_text(company_name).strip()
        if not name or name.upper().startswith(_UNKNOWN_NAME_PREFIXES):
            return []

        aliases = [name]
        candidate = name
        changed = True
        while changed:
            changed = False
            for suffix in _COMPANY_NAME_SUFFIXES:
                if candidate.endswith(suffix) and len(candidate) - len(suffix) >= 2:
                    candidate = candidate[: -len(suffix)]
                    if candidate not in aliases:
                        aliases.append(candidate)
                    changed = True
                    break

        return aliases

    @staticmethod
    def _build_code_patterns(stock_code: str, market: Optional[str]) -> List[re.Pattern]:
        """
        生成代码匹配正则

        必须带数字边界：港股 01810 若用朴素子串匹配，会命中基金代码 001810，
        正是本次问题里"小米集团"报告混入基金新闻的根源之一。
        """
        candidates = [str(stock_code).upper()]

        try:
            from tradingagents.utils.stock_utils import detect_market, symbol_aliases

            resolved_market = market or detect_market(stock_code)
            candidates = symbol_aliases(stock_code, resolved_market)
        except (ImportError, ValueError) as e:
            logger.debug(f"[过滤器] 代码别名生成失败，退化为原始代码匹配: {e}")

        patterns = []
        seen = set()
        for candidate in candidates:
            if not candidate or candidate in seen:
                continue
            seen.add(candidate)
            patterns.append(re.compile(rf'(?<!\d){re.escape(candidate)}(?!\d)', re.IGNORECASE))

        return patterns

    def _match_company(self, text: str) -> Optional[str]:
        """返回文本命中的公司名别名"""
        normalized = _normalize_text(text)
        for alias in self.company_aliases:
            if alias in normalized:
                return alias
        return None

    def _match_code(self, text: str) -> Optional[str]:
        """返回文本命中的代码别名"""
        normalized = _normalize_text(text)
        for pattern in self.code_patterns:
            if pattern.search(normalized):
                return pattern.pattern
        return None

    def is_noise(self, title: str, content: str) -> bool:
        """
        判断新闻是否为明显噪声：既不提本公司也不提本代码，却含基金/指数类排除词

        公司名未知时无法给出可靠评分，此时只用这条规则拦截噪声，避免误杀全部新闻。
        """
        title = title or ''
        content = content or ''
        combined = f"{title}\n{content}"

        if self._match_company(combined) or self._match_code(combined):
            return False

        lowered = combined.lower()
        return any(keyword in lowered for keyword in self.exclude_keywords)

    def calculate_relevance_score(self, title: str, content: str) -> float:
        """
        计算新闻相关性评分
        
        Args:
            title: 新闻标题
            content: 新闻内容
            
        Returns:
            float: 相关性评分 (0-100)
        """
        score = 0
        title = title or ''
        content = content or ''
        title_lower = title.lower()
        content_lower = content.lower()

        # 1. 直接提及公司名称（含简称别名，如"小米集团"的"小米"）
        title_company = self._match_company(title)
        content_company = self._match_company(content)
        if title_company:
            score += 50  # 标题中出现公司名称，高分
            logger.debug(f"[过滤器] 标题包含公司名称 '{title_company}': +50分")
        elif content_company:
            score += 25  # 内容中出现公司名称，中等分
            logger.debug(f"[过滤器] 内容包含公司名称 '{content_company}': +25分")

        # 2. 直接提及股票代码（带数字边界，01810 不会被 001810 误命中）
        title_code = self._match_code(title)
        content_code = self._match_code(content)
        if title_code:
            score += 40  # 标题中出现股票代码，高分
            logger.debug(f"[过滤器] 标题包含股票代码 '{self.stock_code}': +40分")
        elif content_code:
            score += 20  # 内容中出现股票代码，中等分
            logger.debug(f"[过滤器] 内容包含股票代码 '{self.stock_code}': +20分")
            
        # 3. 强相关关键词检查
        strong_matches = []
        for keyword in self.strong_keywords:
            if keyword in title_lower:
                score += 30
                strong_matches.append(keyword)
            elif keyword in content_lower:
                score += 15
                strong_matches.append(keyword)
        
        if strong_matches:
            logger.debug(f"[过滤器] 强相关关键词匹配: {strong_matches}")
            
        # 4. 包含关键词检查
        include_matches = []
        for keyword in self.include_keywords:
            if keyword in title_lower:
                score += 15
                include_matches.append(keyword)
            elif keyword in content_lower:
                score += 8
                include_matches.append(keyword)
        
        if include_matches:
            logger.debug(f"[过滤器] 相关关键词匹配: {include_matches[:3]}...")  # 只显示前3个
            
        # 5. 排除关键词检查（减分）
        exclude_matches = []
        for keyword in self.exclude_keywords:
            if keyword in title_lower:
                score -= 40  # 标题中出现排除词，大幅减分
                exclude_matches.append(keyword)
            elif keyword in content_lower:
                score -= 20  # 内容中出现排除词，中等减分
                exclude_matches.append(keyword)
        
        if exclude_matches:
            logger.debug(f"[过滤器] 排除关键词匹配: {exclude_matches[:3]}...")
            
        # 6. 特殊规则：如果标题完全不包含公司信息但包含排除词，严重减分
        if (not title_company and not title_code and
                any(keyword in title_lower for keyword in self.exclude_keywords)):
            score -= 30
            logger.debug(f"[过滤器] 标题无公司信息但含排除词: -30分")
        
        # 确保评分在0-100范围内
        final_score = max(0, min(100, score))
        
        logger.debug(f"[过滤器] 最终评分: {final_score}分 - 标题: {title[:30]}...")
        
        return final_score
    
    def filter_news(self, news_df: "pd.DataFrame", min_score: float = 30) -> "pd.DataFrame":
        """
        过滤新闻DataFrame
        
        Args:
            news_df: 原始新闻DataFrame
            min_score: 最低相关性评分阈值
            
        Returns:
            pd.DataFrame: 过滤后的新闻DataFrame，按相关性评分排序
        """
        import pandas as pd

        if news_df.empty:
            logger.warning("[过滤器] 输入新闻DataFrame为空")
            return news_df
        
        logger.info(f"[过滤器] 开始过滤新闻，原始数量: {len(news_df)}条，最低评分阈值: {min_score}")
        
        filtered_news = []
        
        for idx, row in news_df.iterrows():
            title = row.get('新闻标题', row.get('标题', ''))
            content = row.get('新闻内容', row.get('内容', ''))
            
            # 计算相关性评分
            score = self.calculate_relevance_score(title, content)
            
            if score >= min_score:
                row_dict = row.to_dict()
                row_dict['relevance_score'] = score
                filtered_news.append(row_dict)
                
                logger.debug(f"[过滤器] 保留新闻 (评分: {score:.1f}): {title[:50]}...")
            else:
                logger.debug(f"[过滤器] 过滤新闻 (评分: {score:.1f}): {title[:50]}...")
        
        # 创建过滤后的DataFrame
        if filtered_news:
            filtered_df = pd.DataFrame(filtered_news)
            # 按相关性评分排序
            filtered_df = filtered_df.sort_values('relevance_score', ascending=False)
            logger.info(f"[过滤器] 过滤完成，保留 {len(filtered_df)}条 新闻")
        else:
            filtered_df = pd.DataFrame()
            logger.warning(f"[过滤器] 所有新闻都被过滤，无符合条件的新闻")
            
        return filtered_df
    
    def get_filter_statistics(self, original_df: "pd.DataFrame",
                              filtered_df: "pd.DataFrame") -> Dict:
        """
        获取过滤统计信息
        
        Args:
            original_df: 原始新闻DataFrame
            filtered_df: 过滤后新闻DataFrame
            
        Returns:
            Dict: 统计信息
        """
        stats = {
            'original_count': len(original_df),
            'filtered_count': len(filtered_df),
            'filter_rate': (len(original_df) - len(filtered_df)) / len(original_df) * 100 if len(original_df) > 0 else 0,
            'avg_score': filtered_df['relevance_score'].mean() if not filtered_df.empty else 0,
            'max_score': filtered_df['relevance_score'].max() if not filtered_df.empty else 0,
            'min_score': filtered_df['relevance_score'].min() if not filtered_df.empty else 0
        }
        
        return stats


# 股票代码到公司名称的映射
STOCK_COMPANY_MAPPING = {
    # A股主要银行
    '600036': '招商银行',
    '000001': '平安银行', 
    '600000': '浦发银行',
    '601166': '兴业银行',
    '002142': '宁波银行',
    '601328': '交通银行',
    '601398': '工商银行',
    '601939': '建设银行',
    '601288': '农业银行',
    '601818': '光大银行',
    '600015': '华夏银行',
    '600016': '民生银行',
    
    # A股主要白酒股
    '000858': '五粮液',
    '600519': '贵州茅台',
    '000568': '泸州老窖',
    '002304': '洋河股份',
    '000596': '古井贡酒',
    '603369': '今世缘',
    '000799': '酒鬼酒',
    
    # A股主要科技股
    '000002': '万科A',
    '000858': '五粮液',
    '002415': '海康威视',
    '000725': '京东方A',
    '002230': '科大讯飞',
    '300059': '东方财富',
    
    # 更多股票可以继续添加...
}

def get_company_name(ticker: str, market: Optional[str] = None) -> str:
    """
    获取股票代码对应的公司名称

    港股不在 STOCK_COMPANY_MAPPING 中（该表只收录A股），需要走港股专用映射，
    否则港股会一直拿到"股票01810"这样的占位名，相关性判定形同虚设。

    Args:
        ticker: 股票代码
        market: 市场码 CN/HK/US，为 None 时按代码格式推断

    Returns:
        str: 公司名称，未解析成功时返回占位名
    """
    clean_ticker = ticker.split('.')[0]

    resolved_market = market
    if resolved_market is None:
        try:
            from tradingagents.utils.stock_utils import detect_market

            resolved_market = detect_market(ticker)
        except (ImportError, ValueError):
            resolved_market = None

    if resolved_market == 'HK':
        try:
            from tradingagents.dataflows.providers.hk.improved_hk import get_hk_company_name_improved

            hk_name = get_hk_company_name_improved(clean_ticker)
            if hk_name and not hk_name.upper().startswith(_UNKNOWN_NAME_PREFIXES):
                logger.debug(f"[公司映射] {ticker} -> {hk_name}")
                return hk_name
        except Exception as e:
            logger.warning(f"[公司映射] 港股公司名获取失败 {ticker}: {e}")

        default_name = f"港股{clean_ticker}"
        logger.warning(f"[公司映射] 未找到 {ticker} 的港股公司名称，使用默认: {default_name}")
        return default_name

    company_name = STOCK_COMPANY_MAPPING.get(clean_ticker)

    if company_name:
        logger.debug(f"[公司映射] {ticker} -> {company_name}")
        return company_name
    else:
        # 如果没有映射，返回默认名称
        default_name = f"股票{clean_ticker}"
        logger.warning(f"[公司映射] 未找到 {ticker} 的公司名称映射，使用默认: {default_name}")
        return default_name


def create_news_filter(ticker: str, market: Optional[str] = None,
                       company_name: Optional[str] = None) -> NewsRelevanceFilter:
    """
    创建新闻过滤器的便捷函数

    Args:
        ticker: 股票代码
        market: 市场码 CN/HK/US，为 None 时按代码格式推断
        company_name: 上游已知的公司名，缺省时自动查表

    Returns:
        NewsRelevanceFilter: 配置好的过滤器实例
    """
    resolved_name = company_name or get_company_name(ticker, market)
    return NewsRelevanceFilter(ticker, resolved_name, market=market)


def filter_news_items(items: List[Dict[str, Any]], symbol: str, market: Optional[str] = None,
                      company_name: Optional[str] = None,
                      min_score: float = 25) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    相关性闸门：过滤 dict/list 形式的新闻条目

    与 filter_news 的区别是不依赖 DataFrame，可直接作用于 MongoDB 文档和
    AKShare 转换后的字典列表，因此能在落库前和交给大模型前都拦一道。

    公司名未解析成功时退化为"仅拦截明显噪声"，避免把全部新闻误杀导致无新闻可分析。

    Args:
        items: 新闻条目列表，标题/正文字段兼容中英文命名
        symbol: 股票代码
        market: 市场码 CN/HK/US
        company_name: 公司名，缺省时自动查表
        min_score: 最低相关性评分阈值，25 对应"正文提及本公司"这一最低相关档

    Returns:
        Tuple[List[Dict], Dict]: (保留的新闻条目, 过滤统计信息)
    """
    original_count = len(items or [])
    news_filter = create_news_filter(symbol, market=market, company_name=company_name)
    strict = news_filter.has_company_name

    stats = {
        'symbol': symbol,
        'market': market,
        'company_name': news_filter.company_name,
        'strict_mode': strict,
        'min_score': min_score,
        'original_count': original_count,
        'filtered_count': 0,
        'rejected_count': 0,
        'max_score': 0.0,
        'avg_score': 0.0,
    }

    if not items:
        return [], stats

    if not strict:
        logger.warning(
            f"[相关性闸门] {symbol} 公司名未解析（{news_filter.company_name}），"
            f"降级为仅拦截基金/指数类噪声"
        )

    kept: List[Dict[str, Any]] = []
    scores: List[float] = []

    for item in items:
        title = _pick_field(item, _TITLE_KEYS)
        content = _pick_field(item, _CONTENT_KEYS)
        score = news_filter.calculate_relevance_score(title, content)

        if strict:
            keep = score >= min_score
        else:
            keep = score >= min_score or not news_filter.is_noise(title, content)

        if keep:
            enriched = dict(item)
            enriched['relevance_score'] = score
            kept.append(enriched)
            scores.append(score)
        else:
            logger.info(f"[相关性闸门] 拦截无关新闻 (评分 {score:.1f}): {title[:40]}")

    kept.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)

    stats['filtered_count'] = len(kept)
    stats['rejected_count'] = original_count - len(kept)
    stats['max_score'] = max(scores) if scores else 0.0
    stats['avg_score'] = sum(scores) / len(scores) if scores else 0.0

    logger.info(
        f"[相关性闸门] {symbol}({news_filter.company_name}) 相关性过滤: "
        f"{original_count} -> {len(kept)} 条, news_relevance_score_max={stats['max_score']:.1f}"
    )

    return kept, stats


# 使用示例
if __name__ == "__main__":
    # 测试过滤器
    import pandas as pd
    
    # 模拟新闻数据
    test_news = pd.DataFrame([
        {
            '新闻标题': '招商银行发布2024年第三季度业绩报告',
            '新闻内容': '招商银行今日发布第三季度财报，净利润同比增长8%...'
        },
        {
            '新闻标题': '上证180ETF指数基金（530280）自带杠铃策略',
            '新闻内容': '数据显示，上证180指数前十大权重股分别为贵州茅台、招商银行600036...'
        },
        {
            '新闻标题': '银行ETF指数(512730多只成分股上涨',
            '新闻内容': '银行板块今日表现强势，招商银行、工商银行等多只成分股上涨...'
        }
    ])
    
    # 创建过滤器
    filter = create_news_filter('600036')
    
    # 过滤新闻
    filtered_news = filter.filter_news(test_news, min_score=30)
    
    print(f"原始新闻: {len(test_news)}条")
    print(f"过滤后新闻: {len(filtered_news)}条")
    
    if not filtered_news.empty:
        print("\n过滤后的新闻:")
        for _, row in filtered_news.iterrows():
            print(f"- {row['新闻标题']} (评分: {row['relevance_score']:.1f})")