# DCF Analyzer Configuration File
# Define preset parameter configurations for different analysis styles

import json


PRESET_CONFIGS = {
    "conservative": {
        "name": "Conservative",
        "description": "Conservative assumptions for cautious investors",
        "wacc": 0.12,  # Higher discount rate
        "terminal_growth_rate": 0.02,  # Lower terminal growth
        "projection_years": 5,
        "fcf_growth_rate": 0.05,  # Modest FCF growth (capped by historical)
        "conservative_adjustment": 0.15,  # 15% margin of safety
        "dcf_input_type": "fcf",  # Use Free Cash Flow
        "normalize_starting_value": True,  # Use average to smooth volatility
        "normalization_years": 5  # 5-year average
    },
    
    "moderate": {
        "name": "Moderate",
        "description": "Balanced assumptions for most situations",
        "wacc": 0.10,
        "terminal_growth_rate": 0.025,
        "projection_years": 5,
        "fcf_growth_rate": 0.08,  # Moderate FCF growth (capped by historical)
        "conservative_adjustment": 0.0,
        "dcf_input_type": "fcf",  # Use Free Cash Flow
        "normalize_starting_value": True,
        "normalization_years": 5
    },
    
    "aggressive": {
        "name": "Aggressive",
        "description": "Optimistic assumptions for growth stocks",
        "wacc": 0.08,
        "terminal_growth_rate": 0.03,
        "projection_years": 7,
        "fcf_growth_rate": 0.15,  # Higher FCF growth (capped by historical)
        "conservative_adjustment": 0.0,
        "dcf_input_type": "fcf",  # Use Free Cash Flow
        "normalize_starting_value": False,  # Use most recent for growth stocks
        "normalization_years": 3
    },
    
    "high_growth": {
        "name": "High Growth",
        "description": "For fast-growing tech companies",
        "wacc": 0.09,
        "terminal_growth_rate": 0.03,
        "projection_years": 10,
        "fcf_growth_rate": 0.20,  # Aggressive FCF growth (capped by historical)
        "conservative_adjustment": 0.05,
        "dcf_input_type": "fcf",  # Use Free Cash Flow
        "normalize_starting_value": False,  # Use most recent for high growth
        "normalization_years": 3
    },
    
    "value": {
        "name": "Value",
        "description": "For mature, stable businesses",
        "wacc": 0.09,
        "terminal_growth_rate": 0.02,
        "projection_years": 5,
        "fcf_growth_rate": 0.03,  # Conservative FCF growth (capped by historical)
        "conservative_adjustment": 0.10,
        "dcf_input_type": "fcf",  # Use Free Cash Flow
        "normalize_starting_value": True,  # Use average for stable businesses
        "normalization_years": 5
    }
}


SCREENING_PRESETS = {
    "deep_value": {
        "name": "Deep Value",
        "description": "Significantly undervalued stocks",
        "min_discount_pct": 40.0,
        "min_intrinsic_value": 10.0
    },
    
    "moderate_value": {
        "name": "Moderate Value",
        "description": "Moderately undervalued opportunities",
        "min_discount_pct": 20.0,
        "max_discount_pct": 60.0,
        "min_intrinsic_value": 5.0
    },
    
    "quality_value": {
        "name": "Quality Value",
        "description": "Undervalued with minimum quality standards",
        "min_discount_pct": 15.0,
        "min_intrinsic_value": 20.0
    },
    
    "small_cap_value": {
        "name": "Small Cap Value",
        "description": "Undervalued smaller companies",
        "min_discount_pct": 25.0,
        "max_current_price": 20.0,
        "min_intrinsic_value": 5.0
    },
    
    "overvalued": {
        "name": "Overvalued Stocks",
        "description": "Stocks trading above intrinsic value",
        "max_discount_pct": -20.0
    }
}


def get_dcf_preset(preset_name: str):
    """Get DCF parameter preset by name"""
    # First check built-in presets
    preset = PRESET_CONFIGS.get(preset_name.lower())
    if preset:
        return preset
    
    # Then check custom presets
    import os
    import json
    custom_file = os.path.join(os.path.dirname(__file__), 'custom_presets.json')
    if os.path.exists(custom_file):
        try:
            with open(custom_file, 'r') as f:
                custom_presets = json.load(f)
                return custom_presets.get(preset_name.lower())
        except:
            pass
    
    return None


def get_screening_preset(preset_name: str):
    """Get screening filter preset by name"""
    return SCREENING_PRESETS.get(preset_name.lower())


def list_presets():
    """List all available presets"""
    print("\nDCF Parameter Presets:")
    print("=" * 60)
    for key, config in PRESET_CONFIGS.items():
        print(f"{key}: {config['description']}")
    
    print("\nScreening Presets:")
    print("=" * 60)
    for key, config in SCREENING_PRESETS.items():
        print(f"{key}: {config['description']}")


if __name__ == "__main__":
    list_presets()
