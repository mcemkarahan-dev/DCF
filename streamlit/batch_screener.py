"""
Batch Stock Screener Module
Provides filtering and batch analysis capabilities for stock universes
Designed for extensibility - easy to add new filter types
"""

import yfinance as yf
import requests
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

    def get_stock_universe(self, exchange: str = None, filters: Dict = None) -> List[Dict]:
        """
        Get the universe of stocks to screen.
        Returns list of dicts with basic info: ticker, name, sector, exchange, market_cap

        Args:
            exchange: Optional exchange filter (legacy)
            filters: Dict of filter values for server-side filtering (sector, exchange, market_cap_universe)
        """
        if self.data_source == "roic":
            return self._get_roic_universe(exchange, filters)
        else:
            return self._get_yahoo_universe(exchange)

    def _get_yahoo_universe(self, exchange: str = None) -> List[Dict]:
        """
        Get stock universe - uses a reliable built-in list of stocks across market caps.
        Format: (ticker, name, sector, exchange)
        """
        # Mega/Large Cap stocks (S&P 500) with correct exchanges
        LARGE_CAP_STOCKS = [
            ('AAPL', 'Apple Inc.', 'Technology', 'NASDAQ'),
            ('MSFT', 'Microsoft Corp.', 'Technology', 'NASDAQ'),
            ('GOOGL', 'Alphabet Inc.', 'Communication Services', 'NASDAQ'),
            ('AMZN', 'Amazon.com Inc.', 'Consumer Cyclical', 'NASDAQ'),
            ('NVDA', 'NVIDIA Corp.', 'Technology', 'NASDAQ'),
            ('META', 'Meta Platforms Inc.', 'Communication Services', 'NASDAQ'),
            ('TSLA', 'Tesla Inc.', 'Consumer Cyclical', 'NASDAQ'),
            ('BRK-B', 'Berkshire Hathaway', 'Financial Services', 'NYSE'),
            ('UNH', 'UnitedHealth Group', 'Healthcare', 'NYSE'),
            ('JNJ', 'Johnson & Johnson', 'Healthcare', 'NYSE'),
            ('JPM', 'JPMorgan Chase', 'Financial Services', 'NYSE'),
            ('V', 'Visa Inc.', 'Financial Services', 'NYSE'),
            ('XOM', 'Exxon Mobil', 'Energy', 'NYSE'),
            ('PG', 'Procter & Gamble', 'Consumer Defensive', 'NYSE'),
            ('MA', 'Mastercard', 'Financial Services', 'NYSE'),
            ('HD', 'Home Depot', 'Consumer Cyclical', 'NYSE'),
            ('CVX', 'Chevron', 'Energy', 'NYSE'),
            ('MRK', 'Merck & Co.', 'Healthcare', 'NYSE'),
            ('LLY', 'Eli Lilly', 'Healthcare', 'NYSE'),
            ('ABBV', 'AbbVie Inc.', 'Healthcare', 'NYSE'),
            ('PEP', 'PepsiCo', 'Consumer Defensive', 'NASDAQ'),
            ('KO', 'Coca-Cola', 'Consumer Defensive', 'NYSE'),
            ('AVGO', 'Broadcom Inc.', 'Technology', 'NASDAQ'),
            ('COST', 'Costco', 'Consumer Defensive', 'NASDAQ'),
            ('MCD', 'McDonald\'s', 'Consumer Cyclical', 'NYSE'),
            ('WMT', 'Walmart', 'Consumer Defensive', 'NYSE'),
            ('CSCO', 'Cisco Systems', 'Technology', 'NASDAQ'),
            ('TMO', 'Thermo Fisher', 'Healthcare', 'NYSE'),
            ('ACN', 'Accenture', 'Technology', 'NYSE'),
            ('ABT', 'Abbott Labs', 'Healthcare', 'NYSE'),
            ('CRM', 'Salesforce', 'Technology', 'NYSE'),
            ('DHR', 'Danaher', 'Healthcare', 'NYSE'),
            ('ORCL', 'Oracle', 'Technology', 'NYSE'),
            ('NKE', 'Nike Inc.', 'Consumer Cyclical', 'NYSE'),
            ('AMD', 'AMD', 'Technology', 'NASDAQ'),
            ('INTC', 'Intel', 'Technology', 'NASDAQ'),
            ('DIS', 'Walt Disney', 'Communication Services', 'NYSE'),
            ('VZ', 'Verizon', 'Communication Services', 'NYSE'),
            ('NFLX', 'Netflix', 'Communication Services', 'NASDAQ'),
            ('ADBE', 'Adobe Inc.', 'Technology', 'NASDAQ'),
            ('TXN', 'Texas Instruments', 'Technology', 'NASDAQ'),
            ('PM', 'Philip Morris', 'Consumer Defensive', 'NYSE'),
            ('NEE', 'NextEra Energy', 'Utilities', 'NYSE'),
            ('UNP', 'Union Pacific', 'Industrials', 'NYSE'),
            ('RTX', 'Raytheon', 'Industrials', 'NYSE'),
            ('HON', 'Honeywell', 'Industrials', 'NASDAQ'),
            ('QCOM', 'Qualcomm', 'Technology', 'NASDAQ'),
            ('LOW', 'Lowe\'s', 'Consumer Cyclical', 'NYSE'),
            ('BA', 'Boeing', 'Industrials', 'NYSE'),
            ('CAT', 'Caterpillar', 'Industrials', 'NYSE'),
            ('GS', 'Goldman Sachs', 'Financial Services', 'NYSE'),
            ('MS', 'Morgan Stanley', 'Financial Services', 'NYSE'),
            ('BLK', 'BlackRock', 'Financial Services', 'NYSE'),
            ('SPGI', 'S&P Global', 'Financial Services', 'NYSE'),
            ('AXP', 'American Express', 'Financial Services', 'NYSE'),
            ('IBM', 'IBM', 'Technology', 'NYSE'),
            ('GE', 'General Electric', 'Industrials', 'NYSE'),
            ('AMGN', 'Amgen', 'Healthcare', 'NASDAQ'),
            ('GILD', 'Gilead Sciences', 'Healthcare', 'NASDAQ'),
            ('MDLZ', 'Mondelez', 'Consumer Defensive', 'NASDAQ'),
            ('DE', 'Deere & Co.', 'Industrials', 'NYSE'),
            ('LMT', 'Lockheed Martin', 'Industrials', 'NYSE'),
            ('NOW', 'ServiceNow', 'Technology', 'NYSE'),
            ('ISRG', 'Intuitive Surgical', 'Healthcare', 'NASDAQ'),
            ('BKNG', 'Booking Holdings', 'Consumer Cyclical', 'NASDAQ'),
            ('ADI', 'Analog Devices', 'Technology', 'NASDAQ'),
            ('SBUX', 'Starbucks', 'Consumer Cyclical', 'NASDAQ'),
            ('MMC', 'Marsh McLennan', 'Financial Services', 'NYSE'),
            ('VRTX', 'Vertex Pharma', 'Healthcare', 'NASDAQ'),
            ('REGN', 'Regeneron', 'Healthcare', 'NASDAQ'),
            ('ZTS', 'Zoetis', 'Healthcare', 'NYSE'),
            ('PLD', 'Prologis', 'Real Estate', 'NYSE'),
            ('AMT', 'American Tower', 'Real Estate', 'NYSE'),
            ('SYK', 'Stryker', 'Healthcare', 'NYSE'),
            ('SCHW', 'Charles Schwab', 'Financial Services', 'NYSE'),
            ('ADP', 'ADP', 'Industrials', 'NASDAQ'),
            ('LRCX', 'Lam Research', 'Technology', 'NASDAQ'),
            ('CB', 'Chubb Limited', 'Financial Services', 'NYSE'),
            ('MMM', '3M Company', 'Industrials', 'NYSE'),
            ('SO', 'Southern Company', 'Utilities', 'NYSE'),
            ('DUK', 'Duke Energy', 'Utilities', 'NYSE'),
            ('CL', 'Colgate-Palmolive', 'Consumer Defensive', 'NYSE'),
            ('EOG', 'EOG Resources', 'Energy', 'NYSE'),
            ('SLB', 'Schlumberger', 'Energy', 'NYSE'),
            ('PXD', 'Pioneer Natural', 'Energy', 'NYSE'),
            ('FCX', 'Freeport-McMoRan', 'Basic Materials', 'NYSE'),
            ('NEM', 'Newmont', 'Basic Materials', 'NYSE'),
            ('APD', 'Air Products', 'Basic Materials', 'NYSE'),
            ('SHW', 'Sherwin-Williams', 'Basic Materials', 'NYSE'),
            ('ECL', 'Ecolab', 'Basic Materials', 'NYSE'),
        ]

        # Mid Cap stocks with exchanges
        MID_CAP_STOCKS = [
            ('ETSY', 'Etsy Inc.', 'Consumer Cyclical', 'NASDAQ'),
            ('ROKU', 'Roku Inc.', 'Communication Services', 'NASDAQ'),
            ('SNAP', 'Snap Inc.', 'Communication Services', 'NYSE'),
            ('PINS', 'Pinterest', 'Communication Services', 'NYSE'),
            ('DKNG', 'DraftKings', 'Consumer Cyclical', 'NASDAQ'),
            ('CROX', 'Crocs Inc.', 'Consumer Cyclical', 'NASDAQ'),
            ('BILL', 'Bill.com', 'Technology', 'NYSE'),
            ('CFLT', 'Confluent', 'Technology', 'NASDAQ'),
            ('PATH', 'UiPath', 'Technology', 'NYSE'),
            ('GTLB', 'GitLab', 'Technology', 'NASDAQ'),
            ('NET', 'Cloudflare', 'Technology', 'NYSE'),
            ('DDOG', 'Datadog', 'Technology', 'NASDAQ'),
            ('ZS', 'Zscaler', 'Technology', 'NASDAQ'),
            ('OKTA', 'Okta Inc.', 'Technology', 'NASDAQ'),
            ('TWLO', 'Twilio', 'Technology', 'NYSE'),
            ('RNG', 'RingCentral', 'Technology', 'NYSE'),
            ('HUBS', 'HubSpot', 'Technology', 'NYSE'),
            ('DOCU', 'DocuSign', 'Technology', 'NASDAQ'),
            ('WIX', 'Wix.com', 'Technology', 'NASDAQ'),
            ('DBX', 'Dropbox', 'Technology', 'NASDAQ'),
        ]

        # Small Cap stocks ($300M - $2B) with exchanges
        SMALL_CAP_STOCKS = [
            ('APPS', 'Digital Turbine', 'Technology', 'NASDAQ'),
            ('BIGC', 'BigCommerce', 'Technology', 'NASDAQ'),
            ('UPST', 'Upstart Holdings', 'Financial Services', 'NASDAQ'),
            ('SOFI', 'SoFi Technologies', 'Financial Services', 'NASDAQ'),
            ('AFRM', 'Affirm Holdings', 'Financial Services', 'NASDAQ'),
            ('BMBL', 'Bumble Inc.', 'Communication Services', 'NASDAQ'),
            ('TUYA', 'Tuya Inc.', 'Technology', 'NYSE'),
            ('OPEN', 'Opendoor', 'Real Estate', 'NASDAQ'),
            ('WISH', 'ContextLogic', 'Consumer Cyclical', 'NASDAQ'),
            ('BIRD', 'Allbirds', 'Consumer Cyclical', 'NASDAQ'),
            ('RENT', 'Rent the Runway', 'Consumer Cyclical', 'NASDAQ'),
            ('PTON', 'Peloton', 'Consumer Cyclical', 'NASDAQ'),
            ('CHGG', 'Chegg Inc.', 'Consumer Cyclical', 'NYSE'),
            ('COUR', 'Coursera', 'Consumer Cyclical', 'NYSE'),
            ('DUOL', 'Duolingo', 'Consumer Cyclical', 'NASDAQ'),
            ('ABNB', 'Airbnb', 'Consumer Cyclical', 'NASDAQ'),
            ('LYFT', 'Lyft Inc.', 'Industrials', 'NASDAQ'),
            ('GRPN', 'Groupon', 'Consumer Cyclical', 'NASDAQ'),
            ('IRBT', 'iRobot', 'Consumer Cyclical', 'NASDAQ'),
            ('LMND', 'Lemonade', 'Financial Services', 'NYSE'),
        ]

        # Micro Cap stocks ($50M - $300M) with exchanges
        MICRO_CAP_STOCKS = [
            # NASDAQ Micro Caps
            ('SMSI', 'Smith Micro', 'Technology', 'NASDAQ'),
            ('CUEN', 'Cuentas Inc.', 'Technology', 'NASDAQ'),
            ('QNRX', 'Quoin Pharma', 'Healthcare', 'NASDAQ'),
            ('BIOR', 'Biora Therapeutics', 'Healthcare', 'NASDAQ'),
            ('DRUG', 'Bright Minds Bio', 'Healthcare', 'NASDAQ'),
            ('CRIS', 'Curis Inc.', 'Healthcare', 'NASDAQ'),
            ('OCGN', 'Ocugen Inc.', 'Healthcare', 'NASDAQ'),
            ('SNES', 'SenesTech', 'Healthcare', 'NASDAQ'),
            ('CTSO', 'Cytosorbents', 'Healthcare', 'NASDAQ'),
            ('NVAX', 'Novavax', 'Healthcare', 'NASDAQ'),
            ('IOVA', 'Iovance Bio', 'Healthcare', 'NASDAQ'),
            ('SAVA', 'Cassava Sciences', 'Healthcare', 'NASDAQ'),
            ('MNKD', 'MannKind Corp.', 'Healthcare', 'NASDAQ'),
            ('VERU', 'Veru Inc.', 'Healthcare', 'NASDAQ'),
            ('VYGR', 'Voyager Therapeutics', 'Healthcare', 'NASDAQ'),
            # NYSE Micro Caps
            ('BTG', 'B2Gold Corp', 'Basic Materials', 'NYSE'),
            ('HL', 'Hecla Mining', 'Basic Materials', 'NYSE'),
            ('CDE', 'Coeur Mining', 'Basic Materials', 'NYSE'),
            ('EGO', 'Eldorado Gold', 'Basic Materials', 'NYSE'),
            ('AG', 'First Majestic Silver', 'Basic Materials', 'NYSE'),
            ('PAAS', 'Pan American Silver', 'Basic Materials', 'NYSE'),
            ('NGD', 'New Gold Inc', 'Basic Materials', 'NYSE'),
            ('FSM', 'Fortuna Silver', 'Basic Materials', 'NYSE'),
            ('USAS', 'Americas Gold Silver', 'Basic Materials', 'NYSE'),
            ('GPL', 'Great Panther Mining', 'Basic Materials', 'NYSE'),
            ('MUX', 'McEwen Mining', 'Basic Materials', 'NYSE'),
            ('THM', 'International Tower Hill', 'Basic Materials', 'NYSE'),
            ('GATO', 'Gatos Silver', 'Basic Materials', 'NYSE'),
            ('SVM', 'Silvercorp Metals', 'Basic Materials', 'NYSE'),
            ('ASM', 'Avino Silver Gold', 'Basic Materials', 'NYSE'),
            ('REI', 'Ring Energy', 'Energy', 'NYSE'),
            ('SD', 'SandRidge Energy', 'Energy', 'NYSE'),
            ('NEXT', 'NextDecade Corp', 'Energy', 'NYSE'),
            ('NGL', 'NGL Energy Partners', 'Energy', 'NYSE'),
            ('PBF', 'PBF Energy', 'Energy', 'NYSE'),
            ('PUMP', 'ProPetro Holding', 'Energy', 'NYSE'),
            ('CPE', 'Callon Petroleum', 'Energy', 'NYSE'),
            ('CIVI', 'Civitas Resources', 'Energy', 'NYSE'),
            ('HPK', 'HighPeak Energy', 'Energy', 'NYSE'),
            ('GTE', 'Gran Tierra Energy', 'Energy', 'NYSE'),
            ('OII', 'Oceaneering Intl', 'Energy', 'NYSE'),
            ('BORR', 'Borr Drilling', 'Energy', 'NYSE'),
            ('VAL', 'Valaris Ltd', 'Energy', 'NYSE'),
            ('RIG', 'Transocean Ltd', 'Energy', 'NYSE'),
            ('GTN', 'Gray Television', 'Communication Services', 'NYSE'),
            ('MSGS', 'Madison Square Garden', 'Communication Services', 'NYSE'),
            ('EVC', 'Entravision Comms', 'Communication Services', 'NYSE'),
            ('SSP', 'E.W. Scripps', 'Communication Services', 'NYSE'),
            ('GCI', 'Gannett Co', 'Communication Services', 'NYSE'),
            ('NYT', 'New York Times', 'Communication Services', 'NYSE'),
            ('CMCSA', 'Comcast Corp', 'Communication Services', 'NYSE'),
            ('AHH', 'Armada Hoffler', 'Real Estate', 'NYSE'),
            ('LAND', 'Gladstone Land', 'Real Estate', 'NYSE'),
            ('GOOD', 'Gladstone Commercial', 'Real Estate', 'NYSE'),
            ('ORC', 'Orchid Island Cap', 'Real Estate', 'NYSE'),
            ('TWO', 'Two Harbors Inv', 'Real Estate', 'NYSE'),
            ('NYMT', 'New York Mortgage', 'Real Estate', 'NYSE'),
            ('MFA', 'MFA Financial', 'Real Estate', 'NYSE'),
            ('CIM', 'Chimera Investment', 'Real Estate', 'NYSE'),
            ('BXMT', 'Blackstone Mortgage', 'Real Estate', 'NYSE'),
            ('RC', 'Ready Capital', 'Real Estate', 'NYSE'),
            ('TRTX', 'TPG RE Finance', 'Real Estate', 'NYSE'),
            ('KREF', 'KKR Real Estate', 'Real Estate', 'NYSE'),
            ('BGS', 'B&G Foods', 'Consumer Defensive', 'NYSE'),
            ('THS', 'TreeHouse Foods', 'Consumer Defensive', 'NYSE'),
            ('JBSS', 'John B Sanfilippo', 'Consumer Defensive', 'NYSE'),
            ('CENTA', 'Central Garden Pet', 'Consumer Defensive', 'NYSE'),
            ('SENEA', 'Seneca Foods', 'Consumer Defensive', 'NYSE'),
            ('HRL', 'Hormel Foods', 'Consumer Defensive', 'NYSE'),
            # AMEX Micro Caps
            ('INUV', 'Inuvo Inc.', 'Technology', 'AMEX'),
            ('BTN', 'Ballantyne Strong', 'Technology', 'AMEX'),
            ('PETZ', 'TDH Holdings', 'Consumer Cyclical', 'AMEX'),
            ('REED', 'Reeds Inc', 'Consumer Defensive', 'AMEX'),
            ('HUSA', 'Houston American Energy', 'Energy', 'AMEX'),
            ('EPM', 'Evolution Petroleum', 'Energy', 'AMEX'),
            ('USEG', 'US Energy Corp', 'Energy', 'AMEX'),
            ('SNMP', 'Sanchez Midstream', 'Energy', 'AMEX'),
            ('GORO', 'Gold Resource Corp', 'Basic Materials', 'AMEX'),
            ('GSS', 'Golden Star Resources', 'Basic Materials', 'AMEX'),
            ('TGB', 'Taseko Mines', 'Basic Materials', 'AMEX'),
            ('SAND', 'Sandstorm Gold', 'Basic Materials', 'AMEX'),
            ('EXK', 'Endeavour Silver', 'Basic Materials', 'AMEX'),
            ('SILV', 'SilverCrest Metals', 'Basic Materials', 'AMEX'),
            ('AXU', 'Alexco Resource', 'Basic Materials', 'AMEX'),
            ('USAU', 'US Gold Corp', 'Basic Materials', 'AMEX'),
            ('FSR', 'Fisker Inc', 'Consumer Cyclical', 'NYSE'),
            ('GOEV', 'Canoo Inc', 'Consumer Cyclical', 'NYSE'),
            ('LCID', 'Lucid Group', 'Consumer Cyclical', 'NYSE'),
            ('RIVN', 'Rivian Automotive', 'Consumer Cyclical', 'NYSE'),
            ('PSNY', 'Polestar Automotive', 'Consumer Cyclical', 'NYSE'),
            ('NKLA', 'Nikola Corp', 'Industrials', 'NYSE'),
            ('RIDE', 'Lordstown Motors', 'Consumer Cyclical', 'NYSE'),
            ('ARVL', 'Arrival SA', 'Consumer Cyclical', 'NYSE'),
            ('WKHS', 'Workhorse Group', 'Industrials', 'NYSE'),
            ('HYLN', 'Hyliion Holdings', 'Industrials', 'NYSE'),
            ('XL', 'XL Fleet Corp', 'Industrials', 'NYSE'),
            ('ASTS', 'AST SpaceMobile', 'Technology', 'NYSE'),
            ('SPCE', 'Virgin Galactic', 'Industrials', 'NYSE'),
            ('RKLB', 'Rocket Lab USA', 'Industrials', 'NYSE'),
            ('RDW', 'Redwire Corp', 'Industrials', 'NYSE'),
            ('MNTS', 'Momentus Inc', 'Industrials', 'NYSE'),
            ('ASTR', 'Astra Space', 'Industrials', 'NYSE'),
            ('PL', 'Planet Labs', 'Technology', 'NYSE'),
            ('BKSY', 'BlackSky Technology', 'Technology', 'NYSE'),
            ('SATL', 'Satellogic Inc', 'Technology', 'NYSE'),
        ]

        stocks = []

        # Add Large Cap stocks
        for ticker, name, sector, exch in LARGE_CAP_STOCKS:
            stocks.append({
                'ticker': ticker,
                'name': name,
                'sector': sector,
                'exchange': exch,
                'market_cap': 50e9,  # Approximate for sorting
                'market_cap_universe': 'Large Cap',
            })

        # Add Mid Cap stocks
        for ticker, name, sector, exch in MID_CAP_STOCKS:
            stocks.append({
                'ticker': ticker,
                'name': name,
                'sector': sector,
                'exchange': exch,
                'market_cap': 5e9,
                'market_cap_universe': 'Mid Cap',
            })

        # Add Small Cap stocks
        for ticker, name, sector, exch in SMALL_CAP_STOCKS:
            stocks.append({
                'ticker': ticker,
                'name': name,
                'sector': sector,
                'exchange': exch,
                'market_cap': 500e6,
                'market_cap_universe': 'Small Cap',
            })

        # Add Micro Cap stocks
        for ticker, name, sector, exch in MICRO_CAP_STOCKS:
            stocks.append({
                'ticker': ticker,
                'name': name,
                'sector': sector,
                'exchange': exch,
                'market_cap': 100e6,
                'market_cap_universe': 'Micro Cap',
            })

        print(f"Loaded {len(stocks)} stocks from built-in list (Large: {len(LARGE_CAP_STOCKS)}, Mid: {len(MID_CAP_STOCKS)}, Small: {len(SMALL_CAP_STOCKS)}, Micro: {len(MICRO_CAP_STOCKS)})")
        return stocks

    def _fetch_nasdaq_tickers(self) -> List[Dict]:
        """
        Fetch comprehensive ticker list from NASDAQ (free, no API key needed).
        Returns ~11,000 stocks across NYSE, NASDAQ, AMEX.
        """
        url = 'https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqtraded.txt'

        try:
            print("Fetching ticker list from NASDAQ...")
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
            lines = resp.text.strip().split('\n')

            # Map market codes to exchange names
            market_map = {'N': 'NYSE', 'Q': 'NASDAQ', 'A': 'AMEX', 'P': 'NYSE'}

            stocks = []
            for line in lines[1:-1]:  # Skip header and footer
                parts = line.split('|')
                if len(parts) >= 6:
                    symbol = parts[1].strip()
                    name = parts[2].strip()
                    market = parts[3].strip()
                    is_etf = parts[5].strip() == 'Y'
                    test_issue = parts[7].strip() == 'Y' if len(parts) > 7 else False

                    # Skip ETFs, test issues, empty symbols, and symbols with special chars
                    if (symbol and
                        market in market_map and
                        not is_etf and
                        not test_issue and
                        symbol.isalpha() and  # Only letters (skip warrants, units, etc.)
                        len(symbol) <= 5):  # Standard stock symbols

                        stocks.append({
                            'ticker': symbol,
                            'name': name,
                            'sector': 'N/A',  # Will be enriched if needed
                            'exchange': market_map[market],
                            'market_cap': 0,  # Will be enriched if needed
                            'market_cap_universe': 'Unknown',
                        })

            # Count by exchange
            exchanges = {}
            for s in stocks:
                e = s['exchange']
                exchanges[e] = exchanges.get(e, 0) + 1
            print(f"Loaded {len(stocks)} stocks from NASDAQ: {exchanges}")

            return stocks

        except Exception as e:
            print(f"Error fetching from NASDAQ: {e}")
            print("Falling back to built-in list...")
            return None

    def _get_roic_universe(self, exchange: str = None, filters: Dict = None) -> List[Dict]:
        """
        Get stock universe from ROIC.ai with SERVER-SIDE filtering.
        This is much faster as filtering happens at data fetch time.
        Falls back to NASDAQ list or built-in list if ROIC fails.

        Args:
            exchange: Legacy exchange filter
            filters: Dict with sector, exchange, market_cap_universe lists
        """
        # Extract filter lists for server-side filtering
        sectors = filters.get('sector', []) if filters else []
        exchanges = filters.get('exchange', []) if filters else []
        market_caps = filters.get('market_cap_universe', []) if filters else []

        # Handle legacy exchange parameter
        if exchange and not exchanges:
            exchanges = [exchange]

        # Try ROIC.ai server-side filtered fetch first
        try:
            print(f"Fetching filtered tickers from ROIC.ai (sectors={len(sectors)}, exchanges={len(exchanges)}, caps={len(market_caps)})...")
            stocks = self.fetcher.get_filtered_tickers(
                sectors=sectors if sectors else None,
                exchanges=exchanges if exchanges else None,
                market_cap_universes=market_caps if market_caps else None
            )

            if stocks and len(stocks) > 0:
                # Convert to standard format expected by screener
                result = []
                for s in stocks:
                    result.append({
                        'ticker': s.get('ticker') or s.get('symbol'),
                        'name': s.get('name', ''),
                        'sector': s.get('sector', 'N/A'),
                        'exchange': s.get('exchange', 'N/A'),
                        'market_cap': s.get('market_cap') or s.get('marketCap') or 0,
                        'market_cap_universe': s.get('market_cap_universe', 'Unknown'),
                    })
                print(f"ROIC.ai returned {len(result)} pre-filtered tickers")
                return result

        except Exception as e:
            print(f"ROIC.ai filtered fetch failed: {e}")

        # Fallback: Try NASDAQ ticker list
        print("Falling back to NASDAQ ticker list...")
        stocks = self._fetch_nasdaq_tickers()

        if stocks:
            # Apply filters client-side for fallback
            if exchanges:
                stocks = [s for s in stocks if s['exchange'] in exchanges]
            return stocks

        # Final fallback to static list
        print("Using fallback built-in stock list...")
        return self._get_yahoo_universe(exchange)

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

            # Only update exchange if it was N/A (preserve our static data)
            if stock.get('exchange') == 'N/A':
                raw_exchange = info.get('exchange', 'N/A')
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
        # If filters is None or empty, pass all stocks
        if not filters:
            return True

        # Sector filter - empty/None means all
        sector_filter = filters.get('sector')
        if sector_filter and isinstance(sector_filter, list) and len(sector_filter) > 0:
            stock_sector = stock.get('sector', 'N/A')
            # If stock sector is N/A, let it pass (we don't know the sector)
            if stock_sector != 'N/A' and stock_sector not in sector_filter:
                return False

        # Exchange filter - empty/None means all
        exchange_filter = filters.get('exchange')
        if exchange_filter and isinstance(exchange_filter, list) and len(exchange_filter) > 0:
            stock_exchange = stock.get('exchange', 'N/A')
            # Normalize exchange name
            if stock_exchange and stock_exchange != 'N/A':
                stock_exchange_upper = stock_exchange.upper()
                if 'NASDAQ' in stock_exchange_upper or 'NMS' in stock_exchange_upper or 'NGM' in stock_exchange_upper:
                    stock_exchange = 'NASDAQ'
                elif 'NYSE' in stock_exchange_upper or 'NYQ' in stock_exchange_upper:
                    stock_exchange = 'NYSE'
                elif 'AMEX' in stock_exchange_upper:
                    stock_exchange = 'AMEX'

            # If stock exchange is N/A, let it pass
            if stock_exchange != 'N/A' and stock_exchange not in exchange_filter:
                return False

        # Market cap universe filter - empty/None means all
        # Note: This is checked again after enrichment if needed
        market_cap_filter = filters.get('market_cap_universe')
        if market_cap_filter and isinstance(market_cap_filter, list) and len(market_cap_filter) > 0:
            universe = stock.get('market_cap_universe', 'Unknown')
            # If unknown, let it pass (will be checked after enrichment)
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

    def needs_enrichment(self, filters: Dict, pre_filtered: bool = False) -> bool:
        """
        Check if we need to enrich stocks with additional data.

        Args:
            filters: Dict of filter values
            pre_filtered: If True, data was pre-filtered server-side (ROIC.ai)
                         so we don't need enrichment for sector/exchange/market_cap
        """
        # If data is pre-filtered from ROIC.ai, we don't need enrichment for basic filters
        if pre_filtered:
            # Only need enrichment for gross margin (not included in ticker metadata)
            if filters.get('min_gross_margin', 0) > 0:
                return True
            return False

        # For non-pre-filtered data (NASDAQ list), need enrichment for these filters
        # Need enrichment if sector filter is active (NASDAQ stocks don't have sector)
        if filters.get('sector') and len(filters['sector']) > 0:
            return True
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
                                checked_callback: Callable = None,
                                exclude_tickers: set = None,
                                max_stocks: int = None) -> Generator[Dict, None, None]:
        """
        Screen stocks with streaming results.
        Yields matched stocks as they're found.

        Args:
            filters: Dict of filter values
            progress_callback: Function(current, total, message, is_filtering) for progress updates
            match_callback: Function(stock) called when a stock matches
            checked_callback: Function(ticker, matched) called after each ticker is checked
            exclude_tickers: Set of tickers to skip (e.g., recently checked)
            max_stocks: Maximum number of stocks to return

        Yields:
            Stock dicts that pass all filters
        """
        # Get initial universe with SERVER-SIDE filtering for basic filters
        # This pre-filters by sector, exchange, and market cap at the API level
        if progress_callback:
            progress_callback(0, 100, "Fetching filtered stock universe...", True)

        stocks = self.get_stock_universe(filters=filters)

        # Filter out excluded tickers upfront for efficiency
        if exclude_tickers:
            original_count = len(stocks)
            stocks = [s for s in stocks if s['ticker'] not in exclude_tickers]
            skipped = original_count - len(stocks)
            if skipped > 0:
                print(f"Skipped {skipped} recently checked tickers")

        # print(f"DEBUG: Got {len(stocks)} stocks in universe")

        if not stocks:
            # print("DEBUG: No stocks in universe!")
            if progress_callback:
                progress_callback(100, 100, "No stocks found in universe", False)
            return

        total_stocks = len(stocks)
        matched_count = 0

        # Check if data was pre-filtered (ROIC.ai provides metadata, so basic filters already applied)
        # Pre-filtered data has market_cap_universe already set
        pre_filtered = (self.data_source == "roic" and
                       len(stocks) > 0 and
                       stocks[0].get('market_cap_universe') not in [None, 'Unknown'])

        if pre_filtered:
            print(f"Using pre-filtered data from ROIC.ai ({total_stocks} stocks)")

        need_enrichment = self.needs_enrichment(filters, pre_filtered=pre_filtered)
        need_financial = self.has_financial_filters(filters)

        if progress_callback:
            progress_callback(5, 100, f"Screening {total_stocks} pre-filtered stocks...", True)

        for i, stock in enumerate(stocks):
            if max_stocks and matched_count >= max_stocks:
                break

            # Progress update - pass actual count, not percentage
            if progress_callback:
                progress_callback(i + 1, total_stocks, f"Checking {stock['ticker']}...", True)

            # Step 1: Basic filters - SKIP if data was pre-filtered server-side
            if not pre_filtered:
                passes_basic = self.passes_basic_filters(stock, filters)
                if not passes_basic:
                    continue

            # Track if this ticker required slow operations (enrichment/financial)
            required_slow_check = need_enrichment or need_financial
            passed_all = True

            # Step 2: Enrichment if needed (only for gross margin when pre-filtered)
            if need_enrichment:
                stock = self.enrich_stock_info(stock)
                time.sleep(0.1)  # Rate limiting

                # Only re-check filters if data wasn't pre-filtered
                if not pre_filtered:
                    # Re-check sector filter after enrichment
                    sector_filter = filters.get('sector', [])
                    if sector_filter and len(sector_filter) > 0:
                        stock_sector = stock.get('sector', 'N/A')
                        if stock_sector != 'N/A' and stock_sector not in sector_filter:
                            passed_all = False

                    # Re-check market cap filter after enrichment
                    if passed_all:
                        market_cap_filter = filters.get('market_cap_universe', [])
                        if market_cap_filter and len(market_cap_filter) > 0:
                            if stock.get('market_cap_universe', 'Unknown') not in market_cap_filter:
                                passed_all = False

            # Step 3: Financial filters if needed
            if passed_all and need_financial:
                metrics = self.get_financial_metrics(stock['ticker'])
                time.sleep(0.2)  # Rate limiting

                if not self.passes_financial_filters(stock, metrics, filters):
                    passed_all = False
                else:
                    stock['metrics'] = metrics

            # Record that this ticker was checked (if it required slow operations)
            if required_slow_check and checked_callback:
                checked_callback(stock['ticker'], passed_all)

            # Skip if didn't pass all filters
            if not passed_all:
                continue

            # Stock passed all filters!
            matched_count += 1
            # print(f"DEBUG: {stock['ticker']} MATCHED! (count={matched_count})")

            if match_callback:
                match_callback(stock)

            yield stock

        # print(f"DEBUG: Screening complete, {matched_count} stocks matched")
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
