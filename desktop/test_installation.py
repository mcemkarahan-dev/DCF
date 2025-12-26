#!/usr/bin/env python3
"""
Test script to verify DCF Analyzer installation
"""

import sys
import os

def test_imports():
    """Test that all modules can be imported"""
    print("Testing imports...")
    try:
        from database import DCFDatabase
        from data_fetcher import DataFetcher
        from dcf_calculator import DCFCalculator
        from screener import StockScreener
        from main import DCFAnalyzer
        import config
        print("✓ All imports successful")
        return True
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False


def test_database():
    """Test database creation"""
    print("\nTesting database...")
    try:
        from database import DCFDatabase
        import tempfile
        import os
        
        # Use a temporary file for testing
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        temp_file.close()
        
        db = DCFDatabase(temp_file.name)  # This will initialize the schema
        
        # Test adding a stock
        db.add_stock('TEST', 'Test Company', 'NYSE', 'Technology', 'Software')
        
        # Test adding financial data
        db.add_financial_data(
            ticker='TEST',
            period_date='2024-01-01',
            period_type='annual',
            revenue=1000000,
            operating_income=200000,
            net_income=150000,
            free_cash_flow=180000,
            total_debt=500000,
            cash_and_equivalents=300000,
            shares_outstanding=10000000
        )
        
        print("✓ Database operations successful")
        
        # Clean up temp file
        os.unlink(temp_file.name)
        return True
    except Exception as e:
        print(f"✗ Database error: {e}")
        return False


def test_dcf_calculator():
    """Test DCF calculations"""
    print("\nTesting DCF calculator...")
    try:
        from dcf_calculator import DCFCalculator
        
        calc = DCFCalculator()
        
        # Test simple DCF calculation
        historical_fcf = [5000000000, 4500000000, 4000000000]
        params = {
            'wacc': 0.10,
            'terminal_growth_rate': 0.025,
            'projection_years': 5,
            'fcf_growth_rate': 0.05
        }
        
        result = calc.calculate_dcf_simple(historical_fcf, params)
        
        if result and 'enterprise_value' in result:
            print(f"✓ DCF calculation successful (EV: ${result['enterprise_value']:,.0f})")
            return True
        else:
            print("✗ DCF calculation failed")
            return False
    except Exception as e:
        print(f"✗ DCF calculator error: {e}")
        return False


def test_screener():
    """Test screening functionality"""
    print("\nTesting screener...")
    try:
        from database import DCFDatabase
        from screener import StockScreener
        import tempfile
        import os
        
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        temp_file.close()
        
        db = DCFDatabase(temp_file.name)
        screener = StockScreener(db)
        
        # Test filtering (should return empty list with no data)
        results = screener.filter_by_discount(min_discount_pct=10.0)
        
        print("✓ Screener operations successful")
        os.unlink(temp_file.name)
        return True
    except Exception as e:
        print(f"✗ Screener error: {e}")
        return False


def test_config():
    """Test configuration presets"""
    print("\nTesting configuration...")
    try:
        from config import get_dcf_preset, get_screening_preset
        
        conservative = get_dcf_preset('conservative')
        moderate_value = get_screening_preset('moderate_value')
        
        if conservative and moderate_value:
            print("✓ Configuration presets loaded")
            return True
        else:
            print("✗ Configuration presets not found")
            return False
    except Exception as e:
        print(f"✗ Configuration error: {e}")
        return False


def run_all_tests():
    """Run all tests"""
    print("="*60)
    print("DCF ANALYZER - INSTALLATION TEST")
    print("="*60)
    
    tests = [
        ("Imports", test_imports),
        ("Database", test_database),
        ("DCF Calculator", test_dcf_calculator),
        ("Screener", test_screener),
        ("Configuration", test_config)
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"✗ {test_name} test crashed: {e}")
            failed += 1
    
    print("\n" + "="*60)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("="*60)
    
    if failed == 0:
        print("\n✓ All tests passed! Installation is successful.")
        print("\nNext steps:")
        print("1. Get an API key from https://financialmodelingprep.com/developer/docs/")
        print("2. Run: python main.py --api-key YOUR_KEY analyze AAPL")
        print("3. Check README.md for more examples")
    else:
        print("\n✗ Some tests failed. Please check the error messages above.")
        print("Try: pip install -r requirements.txt")
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
