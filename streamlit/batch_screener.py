"""
Batch Stock Screener Module
Provides filtering and batch analysis capabilities for stock universes
Designed for extensibility - easy to add new filter types
"""

import yfinance as yf
from typing import List, Dict, Optional, Callable, Any, Generator
from dataclasses import dataclass, field
from enum import Enum
import time


class FilterCategory(Enum):
    """Categories for organizing filters in the UI"""
    BASIC = "Basic Filters"
    MARKET = "Market Filters"
    PROFITABILITY = "Profitability Filters"
    GROWTH = "Growth Filters"
    QUALITY = "Quality Filters"


@dataclass
class FilterDefinition:
    """Definition of a filter parameter"""
    key: str
    label: str
    category: FilterCategory
    filter_type: str  # 'select', 'multiselect', 'range', 'number'
    options: List[Any] = field(default_factory=list)  # For select/multiselect
    min_value: float = None  # For range/number
    max_value: float = None  # For range/number
    default: Any = None
    help_text: str = ""
    requires_financial_data: bool = False  # If True, needs data fetch to apply


# ==================== SECTOR MAPPING ====================
# Map GICS sectors (from S&P 500/Yahoo) to our filter display names
GICS_SECTOR_MAP = {
    'Information Technology': 'Technology',
    'Technology': 'Technology',
    'Health Care': 'Healthcare',
    'Healthcare': 'Healthcare',
    'Financials': 'Financial Services',
    'Financial Services': 'Financial Services',
    'Consumer Discretionary': 'Consumer Cyclical',
    'Consumer Cyclical': 'Consumer Cyclical',
    'Consumer Staples': 'Consumer Defensive',
    'Consumer Defensive': 'Consumer Defensive',
    'Industrials': 'Industrials',
    'Energy': 'Energy',
    'Utilities': 'Utilities',
    'Real Estate': 'Real Estate',
    'Materials': 'Basic Materials',
    'Basic Materials': 'Basic Materials',
    'Communication Services': 'Communication Services',
    'Telecommunications': 'Communication Services',
}

def normalize_sector(sector: str) -> str:
    """Normalize sector name to our standard names"""
    if not sector or sector == 'N/A':
        return 'N/A'
    return GICS_SECTOR_MAP.get(sector, sector)


# ==================== FILTER DEFINITIONS ====================
# Add new filters here - they will automatically appear in the UI

FILTER_DEFINITIONS = [
    # Basic Filters
    FilterDefinition(
        key="sector",
        label="Sector",
        category=FilterCategory.BASIC,
        filter_type="multiselect",
        options=[
            "Technology", "Healthcare", "Financial Services", "Consumer Cyclical",
            "Consumer Defensive", "Industrials", "Energy", "Utilities",
            "Real Estate", "Basic Materials", "Communication Services"
        ],
        default=[],
        help_text="Filter by company sector"
    ),
    FilterDefinition(
        key="exchange",
        label="Exchange",
        category=FilterCategory.BASIC,
        filter_type="multiselect",
        options=["NASDAQ", "NYSE", "AMEX"],
        default=[],
        help_text="Filter by stock exchange"
    ),

    # Market Filters
    FilterDefinition(
        key="market_cap_universe",
        label="Market Cap Universe",
        category=FilterCategory.MARKET,
        filter_type="multiselect",
        options=["Mega Cap", "Large Cap", "Mid Cap", "Small Cap", "Micro Cap"],
        default=[],
        help_text="Filter by market capitalization tier"
    ),

    # Profitability Filters
    FilterDefinition(
        key="positive_fcf_last_year",
        label="Positive FCF (Last Year)",
        category=FilterCategory.PROFITABILITY,
        filter_type="select",
        options=["Any", "Yes", "No"],
        default="Any",
        help_text="Require positive FCF in the most recent year",
        requires_financial_data=True
    ),
    FilterDefinition(
        key="positive_fcf_years_3",
        label="Positive FCF Years (Last 3)",
        category=FilterCategory.PROFITABILITY,
        filter_type="number",
        min_value=0,
        max_value=3,
        default=0,
        help_text="Minimum years with positive FCF in last 3 years",
        requires_financial_data=True
    ),
    FilterDefinition(
        key="positive_fcf_years_5",
        label="Positive FCF Years (Last 5)",
        category=FilterCategory.PROFITABILITY,
        filter_type="number",
        min_value=0,
        max_value=5,
        default=0,
        help_text="Minimum years with positive FCF in last 5 years",
        requires_financial_data=True
    ),
    FilterDefinition(
        key="positive_fcf_years_10",
        label="Positive FCF Years (Last 10)",
        category=FilterCategory.PROFITABILITY,
        filter_type="number",
        min_value=0,
        max_value=10,
        default=0,
        help_text="Minimum years with positive FCF in last 10 years",
        requires_financial_data=True
    ),
    FilterDefinition(
        key="min_gross_margin",
        label="Minimum Gross Margin %",
        category=FilterCategory.PROFITABILITY,
        filter_type="number",
        min_value=0,
        max_value=100,
        default=0,
        help_text="Minimum gross margin percentage",
        requires_financial_data=True
    ),

    # Growth Filters
    FilterDefinition(
        key="revenue_growth_years_5",
        label="Revenue Growth Years (Last 5)",
        category=FilterCategory.GROWTH,
        filter_type="number",
        min_value=0,
        max_value=5,
        default=0,
        help_text="Minimum years with revenue growth in last 5 years",
        requires_financial_data=True
    ),
]


def get_filters_by_category() -> Dict[FilterCategory, List[FilterDefinition]]:
    """Group filters by category for UI organization"""
    result = {}
    for filter_def in FILTER_DEFINITIONS:
        if filter_def.category not in result:
            result[filter_def.category] = []
        result[filter_def.category].append(filter_def)
    return result


def get_market_cap_universe(market_cap: float) -> str:
    """Classify market cap into universe tier"""
    if not market_cap or market_cap == 0:
        return "Unknown"
    if market_cap >= 200e9:
        return "Mega Cap"
    elif market_cap >= 10e9:
        return "Large Cap"
    elif market_cap >= 2e9:
        return "Mid Cap"
    elif market_cap >= 300e6:
        return "Small Cap"
    elif market_cap >= 50e6:
        return "Micro Cap"
    else:
        return "Nano Cap"


class BatchScreener:
    """
    Batch stock screener with streaming results.
    Yields matched stocks as they're found for live display.
    """

    def __init__(self, data_source: str = "yahoo", api_key: str = None):
        self.data_source = data_source
        self.api_key = api_key

        # Initialize appropriate fetcher
        if data_source == "roic":
            from data_fetcher_roic import RoicDataFetcher
            self.fetcher = RoicDataFetcher(api_key)
        else:
            from data_fetcher_yahoo import YahooFinanceFetcher
            self.fetcher = YahooFinanceFetcher(api_key)

    def get_stock_universe(self, exchange: str = None) -> List[Dict]:
        """
        Get the universe of stocks to screen.
        Returns list of dicts with basic info: ticker, name, sector, exchange, market_cap
        """
        if self.data_source == "roic":
            return self._get_roic_universe(exchange)
        else:
            return self._get_yahoo_universe(exchange)

    def _get_yahoo_universe(self, exchange: str = None) -> List[Dict]:
        """
        Get stock universe using S&P 500 from Wikipedia.
        Already includes sector information from GICS.
        """
        stocks = []

        try:
            # Get S&P 500 tickers
            sp500_url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
            import pandas as pd
            tables = pd.read_html(sp500_url)
            sp500_df = tables[0]

            for _, row in sp500_df.iterrows():
                ticker = str(row['Symbol']).replace('.', '-')  # Yahoo format
                raw_sector = row.get('GICS Sector', 'N/A')
                normalized_sector = normalize_sector(raw_sector)

                stock_info = {
                    'ticker': ticker,
                    'name': row.get('Security', ticker),
                    'sector': normalized_sector,
                    'raw_sector': raw_sector,
                    'industry': row.get('GICS Sub-Industry', 'N/A'),
                    'exchange': 'NYSE',  # Most S&P 500 are NYSE, we'll verify later if needed
                    'market_cap': 0,  # Will be fetched during enrichment if needed
                    'market_cap_universe': 'Large Cap',  # S&P 500 are typically large cap+
                }

                stocks.append(stock_info)

            print(f"Loaded {len(stocks)} stocks from S&P 500")

        except Exception as e:
            print(f"Error fetching S&P 500 list: {e}")
            # Fallback to a small list of well-known tickers
            fallback_tickers = [
                ('AAPL', 'Apple Inc.', 'Technology'),
                ('MSFT', 'Microsoft Corp.', 'Technology'),
                ('GOOGL', 'Alphabet Inc.', 'Communication Services'),
                ('AMZN', 'Amazon.com Inc.', 'Consumer Cyclical'),
                ('META', 'Meta Platforms Inc.', 'Communication Services'),
                ('NVDA', 'NVIDIA Corp.', 'Technology'),
                ('TSLA', 'Tesla Inc.', 'Consumer Cyclical'),
                ('JPM', 'JPMorgan Chase', 'Financial Services'),
                ('JNJ', 'Johnson & Johnson', 'Healthcare'),
                ('V', 'Visa Inc.', 'Financial Services'),
                ('PG', 'Procter & Gamble', 'Consumer Defensive'),
                ('UNH', 'UnitedHealth Group', 'Healthcare'),
                ('HD', 'Home Depot', 'Consumer Cyclical'),
                ('MA', 'Mastercard', 'Financial Services'),
                ('DIS', 'Walt Disney', 'Communication Services'),
                ('PYPL', 'PayPal Holdings', 'Financial Services'),
                ('VZ', 'Verizon', 'Communication Services'),
                ('NFLX', 'Netflix Inc.', 'Communication Services'),
            ]
            for ticker, name, sector in fallback_tickers:
                stocks.append({
                    'ticker': ticker,
                    'name': name,
                    'sector': sector,
                    'exchange': 'NASDAQ',
                    'market_cap': 0,
                    'market_cap_universe': 'Large Cap',
                })

        return stocks

    def _get_roic_universe(self, exchange: str = None) -> List[Dict]:
        """Get stock universe from ROIC.ai"""
        try:
            tickers = self.fetcher.get_exchange_tickers(exchange)

            stocks = []
            for ticker in tickers:
                stocks.append({
                    'ticker': ticker,
                    'name': ticker,
                    'sector': 'N/A',  # Will be fetched later
                    'exchange': exchange or 'N/A',
                    'market_cap': 0,
                    'market_cap_universe': 'Unknown',
                })

            return stocks
        except Exception as e:
            print(f"Error fetching ROIC universe: {e}")
            return []

    def enrich_stock_info(self, stock: Dict) -> Dict:
        """
        Fetch additional info for a stock (market cap, etc.)
        Only called when needed for filtering.
        """
        try:
            ticker = stock['ticker']
            yf_ticker = yf.Ticker(ticker)
            info = yf_ticker.info

            stock['name'] = info.get('longName', stock.get('name', ticker))

            # Only update sector if it was N/A
            if stock.get('sector') == 'N/A':
                raw_sector = info.get('sector', 'N/A')
                stock['sector'] = normalize_sector(raw_sector)

            stock['industry'] = info.get('industry', stock.get('industry', 'N/A'))

            # Normalize exchange
            raw_exchange = info.get('exchange', stock.get('exchange', 'N/A'))
            if 'NASDAQ' in raw_exchange.upper() or 'NMS' in raw_exchange.upper() or 'NGM' in raw_exchange.upper():
                stock['exchange'] = 'NASDAQ'
            elif 'NYSE' in raw_exchange.upper() or 'NYQ' in raw_exchange.upper():
                stock['exchange'] = 'NYSE'
            elif 'AMEX' in raw_exchange.upper():
                stock['exchange'] = 'AMEX'
            else:
                stock['exchange'] = raw_exchange

            stock['market_cap'] = info.get('marketCap', 0) or 0
            stock['market_cap_universe'] = get_market_cap_universe(stock['market_cap'])

            # Additional quick metrics
            stock['gross_margin'] = (info.get('grossMargins', 0) or 0) * 100

        except Exception as e:
            print(f"Error enriching {stock['ticker']}: {e}")
            if 'market_cap_universe' not in stock:
                stock['market_cap_universe'] = 'Unknown'
            if 'gross_margin' not in stock:
                stock['gross_margin'] = 0

        return stock

    def get_financial_metrics(self, ticker: str, years: int = 10) -> Dict:
        """
        Fetch financial metrics needed for filtering.
        Returns metrics like FCF history, revenue growth, margins.
        """
        try:
            if self.data_source == "roic":
                data = self.fetcher.get_financial_data_complete(ticker, years_back=years)
            else:
                data = self.fetcher.get_financial_data_complete(ticker)

            # Extract FCF history
            fcf_history = []
            for cf in data.get('cash_flows', []):
                fcf = cf.get('freeCashFlow', 0)
                date = cf.get('date', '')
                if date:
                    year = int(date[:4])
                    fcf_history.append({'year': year, 'fcf': fcf})

            # Extract revenue history
            revenue_history = []
            for inc in data.get('income_statements', []):
                revenue = inc.get('revenue', 0)
                date = inc.get('date', '')
                if date:
                    year = int(date[:4])
                    revenue_history.append({'year': year, 'revenue': revenue})

            # Sort by year (newest first)
            fcf_history.sort(key=lambda x: x['year'], reverse=True)
            revenue_history.sort(key=lambda x: x['year'], reverse=True)

            # Calculate metrics
            positive_fcf_last_year = fcf_history[0]['fcf'] > 0 if fcf_history else False

            positive_fcf_count_3 = sum(1 for f in fcf_history[:3] if f['fcf'] > 0)
            positive_fcf_count_5 = sum(1 for f in fcf_history[:5] if f['fcf'] > 0)
            positive_fcf_count_10 = sum(1 for f in fcf_history[:10] if f['fcf'] > 0)

            # Revenue growth years
            revenue_growth_years = 0
            for i in range(min(5, len(revenue_history) - 1)):
                if revenue_history[i]['revenue'] > revenue_history[i + 1]['revenue']:
                    revenue_growth_years += 1

            return {
                'positive_fcf_last_year': positive_fcf_last_year,
                'positive_fcf_years_3': positive_fcf_count_3,
                'positive_fcf_years_5': positive_fcf_count_5,
                'positive_fcf_years_10': positive_fcf_count_10,
                'revenue_growth_years_5': revenue_growth_years,
                'fcf_history': fcf_history,
                'revenue_history': revenue_history,
                'full_data': data  # Keep for DCF analysis
            }

        except Exception as e:
            print(f"Error fetching financial metrics for {ticker}: {e}")
            return {
                'positive_fcf_last_year': False,
                'positive_fcf_years_3': 0,
                'positive_fcf_years_5': 0,
                'positive_fcf_years_10': 0,
                'revenue_growth_years_5': 0,
                'fcf_history': [],
                'revenue_history': [],
                'full_data': None
            }

    def passes_basic_filters(self, stock: Dict, filters: Dict) -> bool:
        """
        Check if stock passes basic filters.
        Empty filter list = pass all (SELECT ALL behavior).
        """
        # Sector filter - empty means all
        sector_filter = filters.get('sector', [])
        if sector_filter and len(sector_filter) > 0:
            stock_sector = stock.get('sector', 'N/A')
            if stock_sector not in sector_filter and stock_sector != 'N/A':
                return False
            # If sector is N/A but filter is active, we might still want to include it
            # Let's be permissive and include N/A sectors

        # Exchange filter - empty means all
        exchange_filter = filters.get('exchange', [])
        if exchange_filter and len(exchange_filter) > 0:
            stock_exchange = stock.get('exchange', 'N/A')
            # Normalize exchange
            if 'NASDAQ' in stock_exchange.upper() or 'NMS' in stock_exchange.upper():
                stock_exchange = 'NASDAQ'
            elif 'NYSE' in stock_exchange.upper() or 'NYQ' in stock_exchange.upper():
                stock_exchange = 'NYSE'
            elif 'AMEX' in stock_exchange.upper():
                stock_exchange = 'AMEX'

            if stock_exchange not in exchange_filter and stock_exchange != 'N/A':
                return False

        # Market cap universe filter - empty means all
        market_cap_filter = filters.get('market_cap_universe', [])
        if market_cap_filter and len(market_cap_filter) > 0:
            universe = stock.get('market_cap_universe', 'Unknown')
            # If unknown and filter is active, we should probably include it
            # and let enrichment determine the actual value
            if universe != 'Unknown' and universe not in market_cap_filter:
                return False

        return True

    def passes_financial_filters(self, stock: Dict, metrics: Dict, filters: Dict) -> bool:
        """
        Apply financial filters that require data fetch.
        Returns True if stock passes all filters.
        """
        # Positive FCF last year
        if filters.get('positive_fcf_last_year') == "Yes":
            if not metrics.get('positive_fcf_last_year', False):
                return False
        elif filters.get('positive_fcf_last_year') == "No":
            if metrics.get('positive_fcf_last_year', False):
                return False

        # Positive FCF years (3)
        min_fcf_3 = filters.get('positive_fcf_years_3', 0)
        if min_fcf_3 and min_fcf_3 > 0:
            if metrics.get('positive_fcf_years_3', 0) < min_fcf_3:
                return False

        # Positive FCF years (5)
        min_fcf_5 = filters.get('positive_fcf_years_5', 0)
        if min_fcf_5 and min_fcf_5 > 0:
            if metrics.get('positive_fcf_years_5', 0) < min_fcf_5:
                return False

        # Positive FCF years (10)
        min_fcf_10 = filters.get('positive_fcf_years_10', 0)
        if min_fcf_10 and min_fcf_10 > 0:
            if metrics.get('positive_fcf_years_10', 0) < min_fcf_10:
                return False

        # Revenue growth years
        min_rev_growth = filters.get('revenue_growth_years_5', 0)
        if min_rev_growth and min_rev_growth > 0:
            if metrics.get('revenue_growth_years_5', 0) < min_rev_growth:
                return False

        # Minimum gross margin
        min_gross_margin = filters.get('min_gross_margin', 0)
        if min_gross_margin and min_gross_margin > 0:
            if stock.get('gross_margin', 0) < min_gross_margin:
                return False

        return True

    def has_financial_filters(self, filters: Dict) -> bool:
        """Check if any financial filters are active"""
        if filters.get('positive_fcf_last_year') not in [None, "Any", ""]:
            return True
        if filters.get('positive_fcf_years_3', 0) > 0:
            return True
        if filters.get('positive_fcf_years_5', 0) > 0:
            return True
        if filters.get('positive_fcf_years_10', 0) > 0:
            return True
        if filters.get('revenue_growth_years_5', 0) > 0:
            return True
        if filters.get('min_gross_margin', 0) > 0:
            return True
        return False

    def needs_enrichment(self, filters: Dict) -> bool:
        """Check if we need to enrich stocks with additional data"""
        # Need enrichment if market cap filter is active
        if filters.get('market_cap_universe') and len(filters['market_cap_universe']) > 0:
            return True
        # Need enrichment if gross margin filter is active
        if filters.get('min_gross_margin', 0) > 0:
            return True
        return False

    def screen_stocks_streaming(self, filters: Dict,
                                progress_callback: Callable = None,
                                match_callback: Callable = None,
                                max_stocks: int = None) -> Generator[Dict, None, None]:
        """
        Screen stocks with streaming results.
        Yields matched stocks as they're found.

        Args:
            filters: Dict of filter values
            progress_callback: Function(current, total, message, is_filtering) for progress updates
            match_callback: Function(stock) called when a stock matches
            max_stocks: Maximum number of stocks to return

        Yields:
            Stock dicts that pass all filters
        """
        # Get initial universe
        if progress_callback:
            progress_callback(0, 100, "Fetching stock universe...", True)

        stocks = self.get_stock_universe()

        if not stocks:
            if progress_callback:
                progress_callback(100, 100, "No stocks found in universe", False)
            return

        total_stocks = len(stocks)
        matched_count = 0
        need_enrichment = self.needs_enrichment(filters)
        need_financial = self.has_financial_filters(filters)

        if progress_callback:
            progress_callback(5, 100, f"Screening {total_stocks} stocks...", True)

        for i, stock in enumerate(stocks):
            if max_stocks and matched_count >= max_stocks:
                break

            # Progress update
            if progress_callback and i % 5 == 0:
                pct = 5 + int((i / total_stocks) * 90)
                progress_callback(pct, 100, f"Checking {stock['ticker']}... ({matched_count} matched)", True)

            # Step 1: Basic filters (sector, exchange) - fast, no API call
            if not self.passes_basic_filters(stock, filters):
                continue

            # Step 2: Enrichment if needed (market cap universe, gross margin)
            if need_enrichment:
                stock = self.enrich_stock_info(stock)
                time.sleep(0.1)  # Rate limiting

                # Re-check market cap filter after enrichment
                market_cap_filter = filters.get('market_cap_universe', [])
                if market_cap_filter and len(market_cap_filter) > 0:
                    if stock.get('market_cap_universe', 'Unknown') not in market_cap_filter:
                        continue

            # Step 3: Financial filters if needed
            if need_financial:
                metrics = self.get_financial_metrics(stock['ticker'])
                time.sleep(0.2)  # Rate limiting

                if not self.passes_financial_filters(stock, metrics, filters):
                    continue

                stock['metrics'] = metrics

            # Stock passed all filters!
            matched_count += 1

            if match_callback:
                match_callback(stock)

            yield stock

        if progress_callback:
            progress_callback(100, 100, f"Screening complete: {matched_count} stocks matched", False)

    def screen_stocks(self, filters: Dict, progress_callback: Callable = None,
                     max_stocks: int = None) -> List[Dict]:
        """
        Screen stocks and return list (non-streaming version for compatibility).
        """
        results = list(self.screen_stocks_streaming(
            filters=filters,
            progress_callback=progress_callback,
            max_stocks=max_stocks
        ))
        return results


# Get all unique sectors from the filter definition
def get_all_sectors() -> List[str]:
    """Get list of all sectors for the filter dropdown"""
    for f in FILTER_DEFINITIONS:
        if f.key == 'sector':
            return f.options
    return []


def get_all_exchanges() -> List[str]:
    """Get list of all exchanges for the filter dropdown"""
    for f in FILTER_DEFINITIONS:
        if f.key == 'exchange':
            return f.options
    return []


def get_all_market_cap_universes() -> List[str]:
    """Get list of all market cap universes"""
    for f in FILTER_DEFINITIONS:
        if f.key == 'market_cap_universe':
            return f.options
    return []
