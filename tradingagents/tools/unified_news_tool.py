#!/usr/bin/env python3
"""
统一新闻分析工具
整合A股、港股、美股等不同市场的新闻获取逻辑到一个工具函数中
让大模型只需要调用一个工具就能获取所有类型股票的新闻数据
"""

import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class UnifiedNewsAnalyzer:
    """统一新闻分析器，整合所有新闻获取逻辑"""
    
    def __init__(self, toolkit):
        """初始化统一新闻分析器
        
        Args:
            toolkit: 包含各种新闻获取工具的工具包
        """
        self.toolkit = toolkit
        # 最近一次相关性闸门统计，用于区分"没有新闻"与"新闻全部不相关"
        self._last_gate_stats = None
        
    # 市场码到内部股票类型名称的映射
    MARKET_TO_STOCK_TYPE = {"CN": "A股", "HK": "港股", "US": "美股"}

    def get_stock_news_unified(self, stock_code: str, market: str = None,
                               company_name: str = None, max_news: int = 10,
                               model_info: str = "") -> str:
        """
        统一新闻获取接口
        根据上游传入的市场（缺省时按代码格式推断）路由到对应市场的新闻获取逻辑

        Args:
            stock_code: 股票代码
            market: 市场码 CN/HK/US，上游已知市场时必须传入
            company_name: 公司名称，用于港股按公司名检索与相关性判定
            max_news: 最大新闻数量
            model_info: 当前使用的模型信息，用于特殊处理

        Returns:
            str: 格式化的新闻内容
        """
        logger.info(f"[统一新闻工具] 开始获取 {stock_code} 的新闻，模型: {model_info}")
        logger.info(f"[统一新闻工具] 🤖 当前模型信息: {model_info}")

        # 每次调用重置相关性闸门诊断信息
        self._last_gate_stats = None

        # 识别股票类型
        stock_type = self._identify_stock_type(stock_code, market)
        logger.info(f"[统一新闻工具] 股票类型: {stock_type} (market={market})")

        # 根据股票类型调用相应的获取方法
        if stock_type == "A股":
            result = self._get_a_share_news(stock_code, max_news, model_info, company_name)
        elif stock_type == "港股":
            result = self._get_hk_share_news(stock_code, max_news, model_info, company_name)
        elif stock_type == "美股":
            result = self._get_us_share_news(stock_code, max_news, model_info)
        else:
            # 不再默认按A股处理：港股代码一旦被当作A股，就会被补零命中别的证券
            logger.error(f"[统一新闻工具] ❌ 无法识别 {stock_code} 所属市场，拒绝猜测")
            result = f"❌ 无法识别股票代码 {stock_code} 所属市场，未获取新闻"

        # 🔍 添加详细的结果调试日志
        logger.info(f"[统一新闻工具] 📊 新闻获取完成，结果长度: {len(result)} 字符")
        logger.info(f"[统一新闻工具] 📋 返回结果预览 (前1000字符): {result[:1000]}")

        # 如果结果为空或过短，记录警告
        if not result or len(result.strip()) < 50:
            logger.warning(f"[统一新闻工具] ⚠️ 返回结果异常短或为空！")
            logger.warning(f"[统一新闻工具] 📝 完整结果内容: '{result}'")

        return result

    def _identify_stock_type(self, stock_code: str, market: str = None) -> str:
        """
        识别股票类型

        显式 market 优先，其次按代码格式推断；无法确定时返回"未知"而不是默认A股。

        Args:
            stock_code: 股票代码
            market: 市场码 CN/HK/US 或中文市场名

        Returns:
            str: A股 / 港股 / 美股 / 未知
        """
        from tradingagents.utils.stock_utils import detect_market

        try:
            return self.MARKET_TO_STOCK_TYPE[detect_market(stock_code, market)]
        except (ValueError, KeyError) as e:
            logger.error(f"[统一新闻工具] 市场识别失败 {stock_code} (market={market}): {e}")
            return "未知"

    def _resolve_symbol_and_name(self, stock_code: str, market: str,
                                 company_name: str = None) -> tuple:
        """
        解析规范代码与公司名

        Args:
            stock_code: 原始股票代码
            market: 市场码 CN/HK/US
            company_name: 上游已知公司名

        Returns:
            tuple: (规范代码, 公司名)
        """
        from tradingagents.utils.news_filter import get_company_name
        from tradingagents.utils.stock_utils import normalize_symbol

        symbol = normalize_symbol(stock_code, market)
        resolved_name = company_name or get_company_name(symbol, market)
        return symbol, resolved_name

    def _safe_detect_market(self, stock_code: str) -> str:
        """按代码格式推断市场，失败时返回 None（不猜测为A股）"""
        from tradingagents.utils.stock_utils import detect_market

        try:
            return detect_market(stock_code)
        except ValueError:
            logger.warning(f"[统一新闻工具] 无法推断 {stock_code} 的市场")
            return None

    def _apply_relevance_gate(self, items: list, symbol: str, market: str,
                              company_name: str = None) -> list:
        """
        相关性闸门：拦截与目标股票无关的新闻

        东方财富新闻接口是关键词搜索，即使代码正确也可能返回其他证券的新闻，
        因此在落库前和交给大模型前都要过一遍相关性判定。

        Args:
            items: 新闻条目列表
            symbol: 规范代码
            market: 市场码
            company_name: 公司名

        Returns:
            list: 保留下来的新闻条目
        """
        try:
            from tradingagents.utils.news_filter import filter_news_items

            kept, stats = filter_news_items(
                items, symbol, market=market, company_name=company_name
            )
            self._last_gate_stats = stats

            if items and not kept:
                logger.warning(
                    f"[统一新闻工具] 🚫 {symbol} 共 {len(items)} 条候选新闻全部被相关性闸门拦截"
                )
            return kept
        except Exception as e:
            # 闸门本身异常不应阻断主流程，退化为不过滤
            logger.error(f"[统一新闻工具] 相关性闸门执行失败，跳过过滤: {e}")
            return items

    def _build_gate_failure_message(self, stock_code: str) -> str:
        """
        构造"全部新闻不相关"的失败文案

        文案刻意保持简短（< 100 字符），以命中新闻分析师的"内容过短"降级判断，
        避免把无关新闻或空报告交给大模型。
        """
        stats = self._last_gate_stats or {}
        name = stats.get('company_name', '')
        total = stats.get('original_count', 0)
        return f"❌ 未获取到与 {stock_code}（{name}）相关的可靠新闻：{total} 条候选全部被相关性过滤拦截"

    def _get_news_from_database(self, stock_code: str, max_news: int = 10,
                                market: str = None, company_name: str = None) -> str:
        """
        从数据库获取新闻

        Args:
            stock_code: 股票代码
            max_news: 最大新闻数量
            market: 市场码 CN/HK/US，用于按市场维度隔离查询
            company_name: 公司名，用于相关性闸门

        Returns:
            str: 格式化的新闻内容，如果没有新闻则返回空字符串
        """
        try:
            from tradingagents.dataflows.cache.app_adapter import get_mongodb_client
            from datetime import timedelta

            # 🔧 确保 max_news 是整数（防止传入浮点数）
            max_news = int(max_news)

            client = get_mongodb_client()
            if not client:
                logger.warning(f"[统一新闻工具] 无法连接到MongoDB")
                return ""

            db = client.get_database('tradingagents')
            collection = db.stock_news

            # 按市场归一代码：港股保持5位，A股补齐6位
            resolved_market = market or self._safe_detect_market(stock_code)
            if resolved_market:
                clean_code, resolved_name = self._resolve_symbol_and_name(
                    stock_code, resolved_market, company_name
                )
            else:
                clean_code = stock_code.replace('.SH', '').replace('.SZ', '').replace('.SS', '')\
                                       .replace('.XSHE', '').replace('.XSHG', '').replace('.HK', '')
                resolved_name = company_name

            # 查询最近30天的新闻（扩大时间范围）
            thirty_days_ago = datetime.now() - timedelta(days=30)

            # 市场维度必须参与查询，否则港股 01810 会命中历史上被补零写入的 A 股/基金脏数据。
            # 不再保留"不限时间"的宽松兜底查询，避免捞出早期错误数据。
            market_filter = (
                {'$or': [{'markets': resolved_market}, {'market': resolved_market}]}
                if resolved_market else {}
            )

            query_list = []
            for symbol_filter in ({'symbol': clean_code}, {'symbols': clean_code}):
                query = dict(symbol_filter)
                query['publish_time'] = {'$gte': thirty_days_ago}
                if market_filter:
                    query.update(market_filter)
                query_list.append(query)

            news_items = []
            for query in query_list:
                cursor = collection.find(query).sort('publish_time', -1).limit(max_news)
                news_items = list(cursor)
                if news_items:
                    logger.info(f"[统一新闻工具] 📊 使用查询 {query} 找到 {len(news_items)} 条新闻")
                    break

            if not news_items:
                logger.info(f"[统一新闻工具] 数据库中没有找到 {stock_code} 的新闻")
                return ""

            # 相关性闸门：数据库里可能残留历史脏数据，读取时再拦一道
            if resolved_market:
                news_items = self._apply_relevance_gate(
                    news_items, clean_code, resolved_market, resolved_name
                )
                if not news_items:
                    return ""

            # 格式化新闻
            report = f"# {stock_code} 最新新闻 (数据库缓存)\n\n"
            report += f"📅 查询时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            report += f"📊 新闻数量: {len(news_items)} 条\n\n"

            for i, news in enumerate(news_items, 1):
                title = news.get('title', '无标题')
                content = news.get('content', '') or news.get('summary', '')
                source = news.get('source', '未知来源')
                publish_time = news.get('publish_time', datetime.now())
                sentiment = news.get('sentiment', 'neutral')

                # 情绪图标
                sentiment_icon = {
                    'positive': '📈',
                    'negative': '📉',
                    'neutral': '➖'
                }.get(sentiment, '➖')

                report += f"## {i}. {sentiment_icon} {title}\n\n"
                report += f"**来源**: {source} | **时间**: {publish_time.strftime('%Y-%m-%d %H:%M') if isinstance(publish_time, datetime) else publish_time}\n"
                report += f"**情绪**: {sentiment}\n\n"

                if content:
                    # 限制内容长度
                    content_preview = content[:500] + '...' if len(content) > 500 else content
                    report += f"{content_preview}\n\n"

                report += "---\n\n"

            logger.info(f"[统一新闻工具] ✅ 成功从数据库获取并格式化 {len(news_items)} 条新闻")
            return report

        except Exception as e:
            logger.error(f"[统一新闻工具] 从数据库获取新闻失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return ""

    def _sync_news_from_akshare(self, stock_code: str, max_news: int = 10,
                                company_name: str = None) -> bool:
        """
        从AKShare同步A股新闻到数据库（同步方法）
        使用同步的数据库客户端和新线程中的事件循环，避免事件循环冲突

        Args:
            stock_code: 股票代码
            max_news: 最大新闻数量
            company_name: 公司名，用于相关性闸门

        Returns:
            bool: 是否同步成功
        """
        try:
            import asyncio
            import concurrent.futures

            # A股代码归一为6位
            clean_code, resolved_name = self._resolve_symbol_and_name(
                stock_code, "CN", company_name
            )

            logger.info(f"[统一新闻工具] 🔄 开始同步 {clean_code} 的新闻...")

            # 🔥 在新线程中运行，使用同步数据库客户端
            def run_sync_in_new_thread():
                """在新线程中创建新的事件循环并运行同步任务"""
                # 创建新的事件循环
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)

                try:
                    # 定义异步获取新闻任务
                    async def get_news_task():
                        try:
                            # 动态导入 AKShare provider（正确的导入路径）
                            from tradingagents.dataflows.providers.china.akshare import AKShareProvider

                            # 创建 provider 实例
                            provider = AKShareProvider()

                            # 调用 provider 获取新闻（该方法仅服务A股分支）
                            news_data = await provider.get_stock_news(
                                symbol=clean_code,
                                limit=max_news,
                                market="CN"
                            )

                            return news_data

                        except Exception as e:
                            logger.error(f"[统一新闻工具] ❌ 获取新闻失败: {e}")
                            import traceback
                            logger.error(traceback.format_exc())
                            return None

                    # 在新的事件循环中获取新闻
                    news_data = new_loop.run_until_complete(get_news_task())

                    if not news_data:
                        logger.warning(f"[统一新闻工具] ⚠️ 未获取到新闻数据")
                        return False

                    logger.info(f"[统一新闻工具] 📥 获取到 {len(news_data)} 条新闻")

                    # 相关性闸门：关键词搜索可能夹带其他证券的新闻，落库前先拦一道
                    news_data = self._apply_relevance_gate(
                        news_data, clean_code, "CN", resolved_name
                    )
                    if not news_data:
                        logger.warning(f"[统一新闻工具] ⚠️ {clean_code} 新闻全部与该股票无关，不落库")
                        return False

                    # 🔥 使用同步方法保存到数据库（不依赖事件循环）
                    from app.services.news_data_service import NewsDataService

                    news_service = NewsDataService()
                    saved_count = news_service.save_news_data_sync(
                        news_data=news_data,
                        data_source="akshare",
                        market="CN"
                    )

                    logger.info(f"[统一新闻工具] ✅ 同步成功: {saved_count} 条新闻")
                    return saved_count > 0

                finally:
                    # 清理事件循环
                    new_loop.close()

            # 在线程池中执行
            logger.info(f"[统一新闻工具] 在新线程中运行同步任务，避免事件循环冲突")
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(run_sync_in_new_thread)
                result = future.result(timeout=30)  # 30秒超时
                return result

        except concurrent.futures.TimeoutError:
            logger.error(f"[统一新闻工具] ❌ 同步新闻超时（30秒）")
            return False
        except Exception as e:
            logger.error(f"[统一新闻工具] ❌ 同步新闻失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False

    def _build_hk_search_keywords(self, symbol: str, raw_code: str, company_name: str) -> list:
        """
        构造港股新闻检索关键词，公司名优先

        东方财富新闻接口本质是关键词搜索而非按代码精确查询，
        用"小米集团"能拿到的相关新闻远多于用"01810"，
        所以公司名放在第一位，代码变体作为兜底。

        Args:
            symbol: 规范化的5位港股代码
            raw_code: 用户输入去后缀后的原始代码（可能是4位）
            company_name: 公司名，未解析成功时形如"港股01810"

        Returns:
            list: 去重后的检索关键词
        """
        keywords = []

        if company_name and not company_name.startswith(('港股', '股票')):
            keywords.append(company_name)

        keywords.append(symbol)

        # 保留用户输入的原始位数写法（如 0700），部分新闻正文只用这种写法
        if raw_code and raw_code != symbol:
            keywords.append(raw_code)

        unique_keywords = []
        for keyword in keywords:
            if keyword and keyword not in unique_keywords:
                unique_keywords.append(keyword)

        return unique_keywords

    def _fetch_em_news_by_keyword(self, keyword: str, max_retries: int = 3):
        """
        按关键词调用东方财富新闻接口，失败时指数退避重试

        Args:
            keyword: 检索关键词（公司名或代码）
            max_retries: 最大重试次数

        Returns:
            DataFrame 或 None
        """
        import time

        import akshare as ak

        retry_delay = 1
        for attempt in range(max_retries):
            try:
                return ak.stock_news_em(symbol=keyword)
            except Exception as inner_e:
                if attempt < max_retries - 1:
                    logger.warning(
                        f"[统一新闻工具] ⚠️ 关键词 {keyword} 第{attempt + 1}次获取新闻失败: "
                        f"{inner_e}，{retry_delay}秒后重试..."
                    )
                    time.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    logger.error(f"[统一新闻工具] ❌ 关键词 {keyword} 获取新闻失败: {inner_e}")
        return None

    def _sync_hk_news_from_akshare(self, stock_code: str, max_news: int = 10,
                                   company_name: str = None) -> bool:
        """
        从AKShare同步港股新闻到数据库（同步方法）

        与 _sync_news_from_akshare 的关键区别：
        - 港股代码归一为 5 位后直接检索，绝不走 A 股的 zfill(6)
          （006030 会被东方财富当成别的证券，01810 更会命中基金 001810）。
        - 公司名优先的多关键词检索，代码变体兜底，结果按标题去重合并。
        - 落库前经过相关性闸门，保证入库数据确实属于该港股。
        - 保存时 market="HK"，与 A 股的 "CN" 区分，便于后续按市场维度查询/统计。

        Args:
            stock_code: 港股代码（如 06030.HK 或 06030）
            max_news: 最大新闻数量
            company_name: 公司名，缺省时自动查表

        Returns:
            bool: 是否成功同步并保存了至少一条新闻
        """
        try:
            max_news = int(max_news)

            raw_code = stock_code.replace('.HK', '').replace('.hk', '').strip()
            if not raw_code:
                logger.warning(f"[统一新闻工具] 港股代码标准化后为空: {stock_code}")
                return False

            clean_code, resolved_name = self._resolve_symbol_and_name(
                stock_code, "HK", company_name
            )

            try:
                import akshare  # noqa: F401
            except ImportError:
                logger.error(f"[统一新闻工具] ❌ akshare 未安装，无法同步港股新闻")
                return False

            keywords = self._build_hk_search_keywords(clean_code, raw_code, resolved_name)
            logger.info(
                f"[统一新闻工具] 🔄 开始同步港股 {clean_code}（{resolved_name}）的新闻，"
                f"检索关键词: {keywords}"
            )

            # 多关键词检索并按标题去重合并
            news_data = []
            seen_titles = set()

            for keyword in keywords:
                news_df = self._fetch_em_news_by_keyword(keyword)
                if news_df is None or news_df.empty:
                    logger.info(f"[统一新闻工具] 关键词 {keyword} 未返回新闻")
                    continue

                logger.info(f"[统一新闻工具] 📥 关键词 {keyword} 返回 {len(news_df)} 条原始新闻")

                for _, row in news_df.head(max_news).iterrows():
                    title = str(row.get('新闻标题', '') or row.get('标题', '')).strip()
                    content = str(row.get('新闻内容', '') or row.get('内容', '')).strip()
                    url = str(row.get('新闻链接', '') or row.get('链接', '')).strip()
                    publish_time = str(row.get('发布时间', '') or row.get('时间', '')).strip()
                    source = str(row.get('文章来源', '') or row.get('来源', '') or '东方财富').strip()

                    # 跳过空标题或明显的噪声短标题（< 5 字符基本无信息量）
                    if not title or len(title) < 5 or title in seen_titles:
                        continue

                    seen_titles.add(title)
                    news_data.append({
                        'symbol': clean_code,
                        'market': 'HK',
                        'title': title,
                        'content': content,
                        'summary': content[:200] if content else '',
                        'url': url,
                        'source': source,
                        'publish_time': publish_time,
                        'category': 'general',
                        'sentiment': 'neutral',
                        'sentiment_score': 0.0,
                        'keywords': [],
                        'importance': 'medium',
                        'search_keyword': keyword,
                    })

                if len(news_data) >= max_news:
                    break

            if not news_data:
                logger.warning(
                    f"[统一新闻工具] ⚠️ 港股 {clean_code} 所有关键词均未获取到有效新闻"
                )
                return False

            # 相关性闸门：关键词搜索可能夹带其他证券（尤其是基金）的新闻
            news_data = self._apply_relevance_gate(news_data, clean_code, "HK", resolved_name)
            if not news_data:
                logger.warning(f"[统一新闻工具] ⚠️ 港股 {clean_code} 新闻全部与该股票无关，不落库")
                return False

            # 保存到数据库
            from app.services.news_data_service import NewsDataService
            news_service = NewsDataService()
            saved_count = news_service.save_news_data_sync(
                news_data=news_data[:max_news],
                data_source="akshare",
                market="HK"
            )

            logger.info(f"[统一新闻工具] ✅ 港股新闻同步成功: {saved_count} 条")
            return saved_count > 0

        except Exception as e:
            logger.error(f"[统一新闻工具] ❌ 同步港股新闻失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False

    def _get_a_share_news(self, stock_code: str, max_news: int, model_info: str = "",
                          company_name: str = None) -> str:
        """获取A股新闻"""
        logger.info(f"[统一新闻工具] 获取A股 {stock_code} 新闻")

        # 获取当前日期
        curr_date = datetime.now().strftime("%Y-%m-%d")

        # 优先级0: 从数据库获取新闻（最高优先级）
        try:
            logger.info(f"[统一新闻工具] 🔍 优先从数据库获取 {stock_code} 的新闻...")
            db_news = self._get_news_from_database(
                stock_code, max_news, market="CN", company_name=company_name
            )
            if db_news:
                logger.info(f"[统一新闻工具] ✅ 数据库新闻获取成功: {len(db_news)} 字符")
                return self._format_news_result(db_news, "数据库缓存", model_info)
            else:
                logger.info(f"[统一新闻工具] ⚠️ 数据库中没有 {stock_code} 的新闻，尝试同步...")

                # 🔥 数据库没有数据时，调用同步服务同步新闻
                try:
                    logger.info(f"[统一新闻工具] 📡 调用同步服务同步 {stock_code} 的新闻...")
                    synced_news = self._sync_news_from_akshare(stock_code, max_news, company_name)

                    if synced_news:
                        logger.info(f"[统一新闻工具] ✅ 同步成功，重新从数据库获取...")
                        # 重新从数据库获取
                        db_news = self._get_news_from_database(
                            stock_code, max_news, market="CN", company_name=company_name
                        )
                        if db_news:
                            logger.info(f"[统一新闻工具] ✅ 同步后数据库新闻获取成功: {len(db_news)} 字符")
                            return self._format_news_result(db_news, "数据库缓存(新同步)", model_info)
                    else:
                        logger.warning(f"[统一新闻工具] ⚠️ 同步服务未返回新闻数据")

                except Exception as sync_error:
                    logger.warning(f"[统一新闻工具] ⚠️ 同步服务调用失败: {sync_error}")

                logger.info(f"[统一新闻工具] ⚠️ 同步后仍无数据，尝试其他数据源...")
        except Exception as e:
            logger.warning(f"[统一新闻工具] 数据库新闻获取失败: {e}")

        # 优先级1: 东方财富实时新闻
        try:
            if hasattr(self.toolkit, 'get_realtime_stock_news'):
                logger.info(f"[统一新闻工具] 尝试东方财富实时新闻...")
                # 使用LangChain工具的正确调用方式：.invoke()方法和字典参数
                result = self.toolkit.get_realtime_stock_news.invoke({"ticker": stock_code, "curr_date": curr_date})
                
                # 🔍 详细记录东方财富返回的内容
                logger.info(f"[统一新闻工具] 📊 东方财富返回内容长度: {len(result) if result else 0} 字符")
                logger.info(f"[统一新闻工具] 📋 东方财富返回内容预览 (前500字符): {result[:500] if result else 'None'}")
                
                if result and len(result.strip()) > 100:
                    logger.info(f"[统一新闻工具] ✅ 东方财富新闻获取成功: {len(result)} 字符")
                    return self._format_news_result(result, "东方财富实时新闻", model_info)
                else:
                    logger.warning(f"[统一新闻工具] ⚠️ 东方财富新闻内容过短或为空")
        except Exception as e:
            logger.warning(f"[统一新闻工具] 东方财富新闻获取失败: {e}")
        
        # 优先级2: Google新闻（中文搜索）
        try:
            if hasattr(self.toolkit, 'get_google_news'):
                logger.info(f"[统一新闻工具] 尝试Google新闻...")
                query = f"{stock_code} 股票 新闻 财报 业绩"
                # 使用LangChain工具的正确调用方式：.invoke()方法和字典参数
                result = self.toolkit.get_google_news.invoke({"query": query, "curr_date": curr_date})
                if result and len(result.strip()) > 50:
                    logger.info(f"[统一新闻工具] ✅ Google新闻获取成功: {len(result)} 字符")
                    return self._format_news_result(result, "Google新闻", model_info)
        except Exception as e:
            logger.warning(f"[统一新闻工具] Google新闻获取失败: {e}")
        
        # 优先级3: OpenAI全球新闻
        try:
            if hasattr(self.toolkit, 'get_global_news_openai'):
                logger.info(f"[统一新闻工具] 尝试OpenAI全球新闻...")
                # 使用LangChain工具的正确调用方式：.invoke()方法和字典参数
                result = self.toolkit.get_global_news_openai.invoke({"curr_date": curr_date})
                if result and len(result.strip()) > 50:
                    logger.info(f"[统一新闻工具] ✅ OpenAI新闻获取成功: {len(result)} 字符")
                    return self._format_news_result(result, "OpenAI全球新闻", model_info)
        except Exception as e:
            logger.warning(f"[统一新闻工具] OpenAI新闻获取失败: {e}")

        # 区分"没有新闻"与"新闻全部不相关"：后者必须明确失败，不能把无关新闻交给大模型
        if self._last_gate_stats and self._last_gate_stats.get('original_count'):
            return self._build_gate_failure_message(stock_code)

        return "❌ 无法获取A股新闻数据，所有新闻源均不可用"

    def _get_hk_share_news(self, stock_code: str, max_news: int, model_info: str = "",
                           company_name: str = None) -> str:
        """获取港股新闻

        优先级（与 A 股保持一致的"数据库缓存 + AKShare 同步"骨架，但保留独立分支
        便于针对港股特性单独扩展，如港股 5 位代码、不同新闻源覆盖差异等）：
            优先级 0:   MongoDB 数据库缓存（去除 .HK 后缀按 symbol 查询）
            优先级 0.5: AKShare 同步港股新闻到数据库（_sync_hk_news_from_akshare）
            优先级 1:   东方财富实时新闻聚合器（含港股回退分支）
            优先级 2:   Google 新闻（中文 query）
            优先级 3:   OpenAI 全球新闻
        """
        logger.info(f"[统一新闻工具] 获取港股 {stock_code} 新闻")

        curr_date = datetime.now().strftime("%Y-%m-%d")

        # 优先级0: 从数据库获取新闻（最高优先级，与 A 股保持一致）
        try:
            logger.info(f"[统一新闻工具] 🔍 优先从数据库获取港股 {stock_code} 的新闻...")
            db_news = self._get_news_from_database(
                stock_code, max_news, market="HK", company_name=company_name
            )
            if db_news:
                logger.info(f"[统一新闻工具] ✅ 港股数据库新闻获取成功: {len(db_news)} 字符")
                return self._format_news_result(db_news, "数据库缓存(港股)", model_info)
            else:
                logger.info(f"[统一新闻工具] ⚠️ 数据库中没有港股 {stock_code} 的新闻，尝试同步...")

                # 数据库没有数据时，调用同步服务同步新闻（港股专用同步方法，不走 zfill）
                try:
                    logger.info(f"[统一新闻工具] 📡 调用 AKShare 同步港股 {stock_code} 的新闻...")
                    synced_news = self._sync_hk_news_from_akshare(
                        stock_code, max_news, company_name
                    )

                    if synced_news:
                        logger.info(f"[统一新闻工具] ✅ 港股新闻同步成功，重新从数据库获取...")
                        db_news = self._get_news_from_database(
                            stock_code, max_news, market="HK", company_name=company_name
                        )
                        if db_news:
                            logger.info(
                                f"[统一新闻工具] ✅ 港股同步后数据库新闻获取成功: {len(db_news)} 字符"
                            )
                            return self._format_news_result(db_news, "数据库缓存(新同步-港股)", model_info)
                    else:
                        logger.warning(f"[统一新闻工具] ⚠️ AKShare 港股新闻同步未返回数据")

                except Exception as sync_error:
                    logger.warning(f"[统一新闻工具] ⚠️ AKShare 港股新闻同步调用失败: {sync_error}")

                logger.info(f"[统一新闻工具] ⚠️ 港股同步后仍无数据，尝试其他数据源...")
        except Exception as e:
            logger.warning(f"[统一新闻工具] 港股数据库新闻获取失败: {e}")

        # 优先级1: 实时新闻聚合器（内部含港股 → 东方财富回退分支）
        try:
            if hasattr(self.toolkit, 'get_realtime_stock_news'):
                logger.info(f"[统一新闻工具] 尝试实时港股新闻聚合器...")
                result = self.toolkit.get_realtime_stock_news.invoke(
                    {"ticker": stock_code, "curr_date": curr_date}
                )
                if result and len(result.strip()) > 100:
                    logger.info(f"[统一新闻工具] ✅ 实时港股新闻获取成功: {len(result)} 字符")
                    return self._format_news_result(result, "实时港股新闻", model_info)
                else:
                    logger.warning(f"[统一新闻工具] ⚠️ 实时港股新闻内容过短或为空")
        except Exception as e:
            logger.warning(f"[统一新闻工具] 实时港股新闻获取失败: {e}")

        # 优先级2: Google 新闻（备份，在代理可用时才有效）
        try:
            if hasattr(self.toolkit, 'get_google_news'):
                logger.info(f"[统一新闻工具] 尝试 Google 港股新闻...")
                query = f"{stock_code} 港股 香港股票 新闻"
                result = self.toolkit.get_google_news.invoke({"query": query, "curr_date": curr_date})
                if result and len(result.strip()) > 50:
                    logger.info(f"[统一新闻工具] ✅ Google 港股新闻获取成功: {len(result)} 字符")
                    return self._format_news_result(result, "Google港股新闻", model_info)
        except Exception as e:
            logger.warning(f"[统一新闻工具] Google 港股新闻获取失败: {e}")

        # 优先级3: OpenAI 全球新闻（备份，依赖有效的 OPENAI_API_KEY 与代理）
        try:
            if hasattr(self.toolkit, 'get_global_news_openai'):
                logger.info(f"[统一新闻工具] 尝试 OpenAI 港股新闻...")
                result = self.toolkit.get_global_news_openai.invoke({"curr_date": curr_date})
                if result and len(result.strip()) > 50:
                    logger.info(f"[统一新闻工具] ✅ OpenAI 港股新闻获取成功: {len(result)} 字符")
                    return self._format_news_result(result, "OpenAI港股新闻", model_info)
        except Exception as e:
            logger.warning(f"[统一新闻工具] OpenAI 港股新闻获取失败: {e}")

        # 区分"没有新闻"与"新闻全部不相关"：后者必须明确失败，不能把基金新闻当成小米新闻
        if self._last_gate_stats and self._last_gate_stats.get('original_count'):
            return self._build_gate_failure_message(stock_code)

        return "❌ 无法获取港股新闻数据，所有新闻源均不可用"
    
    def _get_us_share_news(self, stock_code: str, max_news: int, model_info: str = "") -> str:
        """获取美股新闻"""
        logger.info(f"[统一新闻工具] 获取美股 {stock_code} 新闻")
        
        # 获取当前日期
        curr_date = datetime.now().strftime("%Y-%m-%d")
        
        # 优先级1: OpenAI全球新闻
        try:
            if hasattr(self.toolkit, 'get_global_news_openai'):
                logger.info(f"[统一新闻工具] 尝试OpenAI美股新闻...")
                # 使用LangChain工具的正确调用方式：.invoke()方法和字典参数
                result = self.toolkit.get_global_news_openai.invoke({"curr_date": curr_date})
                if result and len(result.strip()) > 50:
                    logger.info(f"[统一新闻工具] ✅ OpenAI美股新闻获取成功: {len(result)} 字符")
                    return self._format_news_result(result, "OpenAI美股新闻", model_info)
        except Exception as e:
            logger.warning(f"[统一新闻工具] OpenAI美股新闻获取失败: {e}")
        
        # 优先级2: Google新闻（英文搜索）
        try:
            if hasattr(self.toolkit, 'get_google_news'):
                logger.info(f"[统一新闻工具] 尝试Google美股新闻...")
                query = f"{stock_code} stock news earnings financial"
                # 使用LangChain工具的正确调用方式：.invoke()方法和字典参数
                result = self.toolkit.get_google_news.invoke({"query": query, "curr_date": curr_date})
                if result and len(result.strip()) > 50:
                    logger.info(f"[统一新闻工具] ✅ Google美股新闻获取成功: {len(result)} 字符")
                    return self._format_news_result(result, "Google美股新闻", model_info)
        except Exception as e:
            logger.warning(f"[统一新闻工具] Google美股新闻获取失败: {e}")
        
        # 优先级3: FinnHub新闻（如果可用）
        try:
            if hasattr(self.toolkit, 'get_finnhub_news'):
                logger.info(f"[统一新闻工具] 尝试FinnHub美股新闻...")
                # 使用LangChain工具的正确调用方式：.invoke()方法和字典参数
                result = self.toolkit.get_finnhub_news.invoke({"symbol": stock_code, "max_results": min(max_news, 50)})
                if result and len(result.strip()) > 50:
                    logger.info(f"[统一新闻工具] ✅ FinnHub美股新闻获取成功: {len(result)} 字符")
                    return self._format_news_result(result, "FinnHub美股新闻", model_info)
        except Exception as e:
            logger.warning(f"[统一新闻工具] FinnHub美股新闻获取失败: {e}")
        
        return "❌ 无法获取美股新闻数据，所有新闻源均不可用"
    
    def _format_news_result(self, news_content: str, source: str, model_info: str = "") -> str:
        """格式化新闻结果"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 🔍 添加调试日志：打印原始新闻内容
        logger.info(f"[统一新闻工具] 📋 原始新闻内容预览 (前500字符): {news_content[:500]}")
        logger.info(f"[统一新闻工具] 📊 原始内容长度: {len(news_content)} 字符")
        
        # 检测是否为Google/Gemini模型
        is_google_model = any(keyword in model_info.lower() for keyword in ['google', 'gemini', 'gemma'])
        original_length = len(news_content)
        google_control_applied = False
        
        # 🔍 添加Google模型检测日志
        if is_google_model:
            logger.info(f"[统一新闻工具] 🤖 检测到Google模型，启用特殊处理")
        
        # 对Google模型进行特殊的长度控制
        if is_google_model and len(news_content) > 5000:  # 降低阈值到5000字符
            logger.warning(f"[统一新闻工具] 🔧 检测到Google模型，新闻内容过长({len(news_content)}字符)，进行长度控制...")
            
            # 更严格的长度控制策略
            lines = news_content.split('\n')
            important_lines = []
            char_count = 0
            target_length = 3000  # 目标长度设为3000字符
            
            # 第一轮：优先保留包含关键词的重要行
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                # 检查是否包含重要关键词
                important_keywords = ['股票', '公司', '财报', '业绩', '涨跌', '价格', '市值', '营收', '利润', 
                                    '增长', '下跌', '上涨', '盈利', '亏损', '投资', '分析', '预期', '公告']
                
                is_important = any(keyword in line for keyword in important_keywords)
                
                if is_important and char_count + len(line) < target_length:
                    important_lines.append(line)
                    char_count += len(line)
                elif not is_important and char_count + len(line) < target_length * 0.7:  # 非重要内容更严格限制
                    important_lines.append(line)
                    char_count += len(line)
                
                # 如果已达到目标长度，停止添加
                if char_count >= target_length:
                    break
            
            # 如果提取的重要内容仍然过长，进行进一步截断
            if important_lines:
                processed_content = '\n'.join(important_lines)
                if len(processed_content) > target_length:
                    processed_content = processed_content[:target_length] + "...(内容已智能截断)"
                
                news_content = processed_content
                google_control_applied = True
                logger.info(f"[统一新闻工具] ✅ Google模型智能长度控制完成，从{original_length}字符压缩至{len(news_content)}字符")
            else:
                # 如果没有重要行，直接截断到目标长度
                news_content = news_content[:target_length] + "...(内容已强制截断)"
                google_control_applied = True
                logger.info(f"[统一新闻工具] ⚠️ Google模型强制截断至{target_length}字符")
        
        # 计算最终的格式化结果长度，确保总长度合理
        base_format_length = 300  # 格式化模板的大概长度
        if is_google_model and (len(news_content) + base_format_length) > 4000:
            # 如果加上格式化后仍然过长，进一步压缩新闻内容
            max_content_length = 3500
            if len(news_content) > max_content_length:
                news_content = news_content[:max_content_length] + "...(已优化长度)"
                google_control_applied = True
                logger.info(f"[统一新闻工具] 🔧 Google模型最终长度优化，内容长度: {len(news_content)}字符")
        
        formatted_result = f"""
=== 📰 新闻数据来源: {source} ===
获取时间: {timestamp}
数据长度: {len(news_content)} 字符
{f"模型类型: {model_info}" if model_info else ""}
{f"🔧 Google模型长度控制已应用 (原长度: {original_length} 字符)" if google_control_applied else ""}

=== 📋 新闻内容 ===
{news_content}

=== ✅ 数据状态 ===
状态: 成功获取
来源: {source}
时间戳: {timestamp}
"""
        return formatted_result.strip()


def create_unified_news_tool(toolkit):
    """创建统一新闻工具函数"""
    analyzer = UnifiedNewsAnalyzer(toolkit)
    
    def get_stock_news_unified(stock_code: str, market: str = None, company_name: str = None,
                               max_news: int = 100, model_info: str = ""):
        """
        统一新闻获取工具

        Args:
            stock_code (str): 股票代码 (支持A股如000001、港股如0700.HK、美股如AAPL)
            market (str): 市场码 CN/HK/US，上游已知市场时应显式传入
            company_name (str): 公司名称，港股用于按公司名检索新闻
            max_news (int): 最大新闻数量，默认100
            model_info (str): 当前使用的模型信息，用于特殊处理

        Returns:
            str: 格式化的新闻内容
        """
        if not stock_code:
            return "❌ 错误: 未提供股票代码"

        return analyzer.get_stock_news_unified(
            stock_code,
            market=market,
            company_name=company_name,
            max_news=max_news,
            model_info=model_info,
        )
    
    # 设置工具属性
    get_stock_news_unified.name = "get_stock_news_unified"
    get_stock_news_unified.description = """
统一新闻获取工具 - 根据股票代码自动获取相应市场的新闻

功能:
- 支持显式传入 market（CN/HK/US），缺省时按代码格式识别，识别不出时明确报错
- 根据股票类型选择最佳新闻源
- A股: 数据库缓存 -> AKShare(东方财富)同步 -> 东方财富实时新闻 -> Google中文 -> OpenAI
- 港股: 数据库缓存 -> AKShare(东方财富)按公司名+代码检索同步 -> 实时新闻聚合器 -> Google中文 -> OpenAI
- 美股: 优先OpenAI -> Google英文 -> FinnHub
- 所有新闻经过相关性闸门过滤，拦截基金/指数等其他证券的新闻
- 返回格式化的新闻内容
- 支持Google模型的特殊长度控制
"""
    
    return get_stock_news_unified