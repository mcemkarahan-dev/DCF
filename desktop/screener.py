"""
Screening and filtering module
Find mispriced opportunities based on DCF analysis
"""

from typing import List, Dict, Callable
from datetime import datetime, timedelta


class StockScreener:
    def __init__(self, db):
        self.db = db
    
    def filter_by_discount(self, min_discount_pct: float = 20.0,
                          max_discount_pct: float = None) -> List[Dict]:
        """
        Filter stocks by discount to intrinsic value
        min_discount_pct: minimum discount % (e.g., 20 = trading 20% below intrinsic value)
        """
        all_dcf = self.db.get_all_latest_dcf()
        
        results = []
        for calc in all_dcf:
            if calc['discount_pct'] is None:
                continue
            
            if calc['discount_pct'] >= min_discount_pct:
                if max_discount_pct is None or calc['discount_pct'] <= max_discount_pct:
                    results.append(calc)
        
        return sorted(results, key=lambda x: x['discount_pct'], reverse=True)
    
    def filter_by_criteria(self, filters: Dict) -> List[Dict]:
        """
        Apply multiple filter criteria
        
        Example filters:
        {
            'min_discount_pct': 20,
            'max_discount_pct': 80,
            'min_intrinsic_value': 10,
            'max_current_price': 500,
            'min_fcf': 1000000000,  # $1B minimum FCF
            'calculation_recency_days': 7  # Calculated within last 7 days
        }
        """
        all_dcf = self.db.get_all_latest_dcf()
        results = []
        
        for calc in all_dcf:
            # Check discount range
            if 'min_discount_pct' in filters:
                if calc['discount_pct'] is None or calc['discount_pct'] < filters['min_discount_pct']:
                    continue
            
            if 'max_discount_pct' in filters:
                if calc['discount_pct'] is None or calc['discount_pct'] > filters['max_discount_pct']:
                    continue
            
            # Check intrinsic value range
            if 'min_intrinsic_value' in filters:
                if calc['intrinsic_value'] < filters['min_intrinsic_value']:
                    continue
            
            if 'max_intrinsic_value' in filters:
                if calc['intrinsic_value'] > filters['max_intrinsic_value']:
                    continue
            
            # Check current price range
            if 'min_current_price' in filters:
                if calc['current_price'] < filters['min_current_price']:
                    continue
            
            if 'max_current_price' in filters:
                if calc['current_price'] > filters['max_current_price']:
                    continue
            
            # Check calculation recency
            if 'calculation_recency_days' in filters:
                calc_date = datetime.fromisoformat(calc['calculation_date'])
                cutoff_date = datetime.now() - timedelta(days=filters['calculation_recency_days'])
                if calc_date < cutoff_date:
                    continue
            
            results.append(calc)
        
        return results
    
    def get_top_opportunities(self, n: int = 20, 
                            min_discount: float = 15.0) -> List[Dict]:
        """
        Get top N opportunities by discount percentage
        """
        filtered = self.filter_by_discount(min_discount)
        return filtered[:n]
    
    def get_value_traps(self, max_discount: float = -50.0) -> List[Dict]:
        """
        Find stocks trading significantly ABOVE intrinsic value
        Negative discount means overvalued
        """
        all_dcf = self.db.get_all_latest_dcf()
        
        results = []
        for calc in all_dcf:
            if calc['discount_pct'] is not None and calc['discount_pct'] < max_discount:
                results.append(calc)
        
        return sorted(results, key=lambda x: x['discount_pct'])
    
    def analyze_trending(self, ticker: str, periods: int = 5) -> Dict:
        """
        Analyze how intrinsic value has changed over time
        Useful for spotting improving or deteriorating businesses
        """
        history = self.db.get_dcf_history(ticker, limit=periods)
        
        if len(history) < 2:
            return {
                'ticker': ticker,
                'trend': 'insufficient_data',
                'history': history
            }
        
        # Calculate trend
        intrinsic_values = [h['intrinsic_value'] for h in reversed(history)]
        discounts = [h['discount_pct'] for h in reversed(history)]
        
        # Simple trend detection
        if intrinsic_values[0] < intrinsic_values[-1]:
            iv_trend = 'increasing'
        elif intrinsic_values[0] > intrinsic_values[-1]:
            iv_trend = 'decreasing'
        else:
            iv_trend = 'stable'
        
        # Calculate average change
        changes = []
        for i in range(1, len(intrinsic_values)):
            pct_change = ((intrinsic_values[i] - intrinsic_values[i-1]) / intrinsic_values[i-1]) * 100
            changes.append(pct_change)
        
        avg_change = sum(changes) / len(changes) if changes else 0
        
        return {
            'ticker': ticker,
            'intrinsic_value_trend': iv_trend,
            'avg_iv_change_pct': avg_change,
            'current_intrinsic_value': intrinsic_values[-1],
            'oldest_intrinsic_value': intrinsic_values[0],
            'current_discount': discounts[-1] if discounts[-1] else None,
            'history': history
        }
    
    def get_improving_stocks(self, min_avg_change: float = 5.0,
                           min_periods: int = 3) -> List[Dict]:
        """
        Find stocks where intrinsic value is improving over time
        """
        all_dcf = self.db.get_all_latest_dcf()
        improving = []
        
        for calc in all_dcf:
            trend_analysis = self.analyze_trending(calc['ticker'], periods=min_periods)
            
            if (trend_analysis['intrinsic_value_trend'] == 'increasing' and 
                trend_analysis['avg_iv_change_pct'] >= min_avg_change):
                improving.append({
                    **calc,
                    'trend_data': trend_analysis
                })
        
        return sorted(improving, key=lambda x: x['trend_data']['avg_iv_change_pct'], reverse=True)
    
    def custom_screen(self, screen_function: Callable) -> List[Dict]:
        """
        Apply a custom screening function
        screen_function should accept a DCF calculation dict and return True/False
        """
        all_dcf = self.db.get_all_latest_dcf()
        return [calc for calc in all_dcf if screen_function(calc)]
    
    def get_stats_summary(self) -> Dict:
        """
        Get summary statistics of all DCF calculations
        """
        all_dcf = self.db.get_all_latest_dcf()
        
        if not all_dcf:
            return {'total_stocks': 0}
        
        discounts = [c['discount_pct'] for c in all_dcf if c['discount_pct'] is not None]
        intrinsic_values = [c['intrinsic_value'] for c in all_dcf]
        
        undervalued = len([d for d in discounts if d > 0])
        overvalued = len([d for d in discounts if d < 0])
        fairly_valued = len([d for d in discounts if -5 <= d <= 5])
        
        return {
            'total_stocks': len(all_dcf),
            'undervalued_count': undervalued,
            'overvalued_count': overvalued,
            'fairly_valued_count': fairly_valued,
            'avg_discount': sum(discounts) / len(discounts) if discounts else 0,
            'max_discount': max(discounts) if discounts else 0,
            'min_discount': min(discounts) if discounts else 0,
            'avg_intrinsic_value': sum(intrinsic_values) / len(intrinsic_values)
        }
    
    def generate_report(self, filters: Dict = None, top_n: int = 20) -> str:
        """
        Generate a text report of screening results
        """
        if filters:
            results = self.filter_by_criteria(filters)
        else:
            results = self.get_top_opportunities(n=top_n)
        
        stats = self.get_stats_summary()
        
        report = []
        report.append("=" * 80)
        report.append("DCF STOCK SCREENING REPORT")
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("=" * 80)
        report.append("")
        
        report.append("SUMMARY STATISTICS:")
        report.append(f"  Total stocks analyzed: {stats['total_stocks']}")
        report.append(f"  Undervalued: {stats['undervalued_count']}")
        report.append(f"  Overvalued: {stats['overvalued_count']}")
        report.append(f"  Fairly valued: {stats['fairly_valued_count']}")
        report.append(f"  Average discount: {stats['avg_discount']:.2f}%")
        report.append("")
        
        if filters:
            report.append("FILTER CRITERIA:")
            for key, value in filters.items():
                report.append(f"  {key}: {value}")
            report.append("")
        
        report.append(f"TOP {len(results)} OPPORTUNITIES:")
        report.append("")
        report.append(f"{'Ticker':<10} {'Current':<10} {'Intrinsic':<12} {'Discount':<10} {'Model':<15}")
        report.append("-" * 80)
        
        for calc in results[:top_n]:
            report.append(
                f"{calc['ticker']:<10} "
                f"${calc['current_price']:<9.2f} "
                f"${calc['intrinsic_value']:<11.2f} "
                f"{calc['discount_pct']:<9.1f}% "
                f"{calc['model_type']:<15}"
            )
        
        report.append("")
        report.append("=" * 80)
        
        return "\n".join(report)


# Example usage
if __name__ == "__main__":
    from database import DCFDatabase
    
    db = DCFDatabase()
    screener = StockScreener(db)
    
    # Get top opportunities
    top = screener.get_top_opportunities(n=10, min_discount=15)
    
    print("Top 10 Opportunities:")
    for stock in top:
        print(f"{stock['ticker']}: {stock['discount_pct']:.1f}% discount")
