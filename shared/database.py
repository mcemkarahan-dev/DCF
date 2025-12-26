"""
Database module for DCF stock analyzer
Handles storage of financial data, DCF calculations, and historical tracking
"""

import sqlite3
from datetime import datetime
from typing import List, Dict, Optional
import json


class DCFDatabase:
    def __init__(self, db_path: str = "dcf_analysis.db"):
        self.db_path = db_path
        self.init_database()
    
    def get_connection(self):
        return sqlite3.connect(self.db_path)
    
    def init_database(self):
        """Initialize database schema"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Stocks table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS stocks (
                ticker TEXT PRIMARY KEY,
                company_name TEXT,
                exchange TEXT,
                sector TEXT,
                industry TEXT,
                last_updated TIMESTAMP
            )
        """)
        
        # Financial data table (raw data from API)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS financial_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT,
                period_date DATE,
                period_type TEXT,
                revenue REAL,
                operating_income REAL,
                net_income REAL,
                free_cash_flow REAL,
                total_debt REAL,
                cash_and_equivalents REAL,
                shares_outstanding REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (ticker) REFERENCES stocks(ticker)
            )
        """)
        
        # DCF calculations table (historical tracking)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS dcf_calculations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT,
                calculation_date TIMESTAMP,
                model_type TEXT,
                parameters TEXT,
                intrinsic_value REAL,
                current_price REAL,
                discount_pct REAL,
                wacc REAL,
                terminal_growth_rate REAL,
                projection_years INTEGER,
                fcf_projections TEXT,
                terminal_value REAL,
                enterprise_value REAL,
                equity_value REAL,
                shares_outstanding REAL,
                FOREIGN KEY (ticker) REFERENCES stocks(ticker)
            )
        """)
        
        # Screening results table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS screening_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                screen_date TIMESTAMP,
                screen_name TEXT,
                filter_criteria TEXT,
                results_count INTEGER,
                tickers TEXT
            )
        """)
        
        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ticker ON financial_data(ticker)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_calc_ticker ON dcf_calculations(ticker)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_calc_date ON dcf_calculations(calculation_date)")
        
        conn.commit()
        conn.close()
    
    def add_stock(self, ticker: str, company_name: str = None, 
                  exchange: str = None, sector: str = None, industry: str = None):
        """Add or update stock information"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO stocks (ticker, company_name, exchange, sector, industry, last_updated)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (ticker, company_name, exchange, sector, industry, datetime.now()))
        
        conn.commit()
        conn.close()
    
    def add_financial_data(self, ticker: str, period_date: str, period_type: str,
                          revenue: float, operating_income: float, net_income: float,
                          free_cash_flow: float, total_debt: float, 
                          cash_and_equivalents: float, shares_outstanding: float):
        """Add financial data for a specific period"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO financial_data 
            (ticker, period_date, period_type, revenue, operating_income, net_income,
             free_cash_flow, total_debt, cash_and_equivalents, shares_outstanding)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (ticker, period_date, period_type, revenue, operating_income, net_income,
              free_cash_flow, total_debt, cash_and_equivalents, shares_outstanding))
        
        conn.commit()
        conn.close()
    
    def save_dcf_calculation(self, ticker: str, model_type: str, parameters: Dict,
                           intrinsic_value: float, current_price: float,
                           wacc: float, terminal_growth_rate: float,
                           projection_years: int, fcf_projections: List[float],
                           terminal_value: float, enterprise_value: float,
                           equity_value: float, shares_outstanding: float):
        """Save DCF calculation results with full historical tracking"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        discount_pct = ((intrinsic_value - current_price) / current_price * 100) if current_price > 0 else None
        
        cursor.execute("""
            INSERT INTO dcf_calculations 
            (ticker, calculation_date, model_type, parameters, intrinsic_value,
             current_price, discount_pct, wacc, terminal_growth_rate, projection_years,
             fcf_projections, terminal_value, enterprise_value, equity_value, shares_outstanding)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (ticker, datetime.now(), model_type, json.dumps(parameters),
              intrinsic_value, current_price, discount_pct, wacc, terminal_growth_rate,
              projection_years, json.dumps(fcf_projections), terminal_value,
              enterprise_value, equity_value, shares_outstanding))
        
        conn.commit()
        conn.close()
    
    def get_latest_dcf(self, ticker: str) -> Optional[Dict]:
        """Get the most recent DCF calculation for a ticker"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM dcf_calculations
            WHERE ticker = ?
            ORDER BY calculation_date DESC
            LIMIT 1
        """, (ticker,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            columns = [desc[0] for desc in cursor.description]
            return dict(zip(columns, row))
        return None
    
    def get_dcf_history(self, ticker: str, limit: int = None) -> List[Dict]:
        """Get historical DCF calculations for a ticker"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        query = """
            SELECT * FROM dcf_calculations
            WHERE ticker = ?
            ORDER BY calculation_date DESC
        """
        
        if limit:
            query += f" LIMIT {limit}"
        
        cursor.execute(query, (ticker,))
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        conn.close()
        
        return [dict(zip(columns, row)) for row in rows]
    
    def get_all_latest_dcf(self) -> List[Dict]:
        """Get the latest DCF calculation for all stocks"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT d1.* FROM dcf_calculations d1
            INNER JOIN (
                SELECT ticker, MAX(calculation_date) as max_date
                FROM dcf_calculations
                GROUP BY ticker
            ) d2 ON d1.ticker = d2.ticker AND d1.calculation_date = d2.max_date
            ORDER BY d1.discount_pct DESC
        """)
        
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        conn.close()
        
        return [dict(zip(columns, row)) for row in rows]
    
    def get_financial_data(self, ticker: str, limit: int = 5) -> List[Dict]:
        """Get historical financial data for a ticker"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM financial_data
            WHERE ticker = ?
            ORDER BY period_date DESC
            LIMIT ?
        """, (ticker, limit))
        
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        conn.close()
        
        return [dict(zip(columns, row)) for row in rows]
