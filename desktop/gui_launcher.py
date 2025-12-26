#!/usr/bin/env python3
"""
DCF Stock Analyzer - Simple GUI Launcher
Makes it easy to run analyses without command line
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import threading
import subprocess
import sys
import os

class DCFAnalyzerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("DCF Stock Analyzer")
        self.root.geometry("900x650")
        
        # Load API key if exists
        self.api_key = self.load_api_key()
        
        # Load presets (built-in + custom)
        self.load_all_presets()
        
        # Create UI
        self.create_widgets()
        
        # Auto-select data source and load corresponding key
        self.auto_load_data_source()
    
    def load_all_presets(self):
        """Load both built-in and custom presets"""
        import os
        
        # Load built-in presets from config.py
        try:
            import sys
            current_dir = os.path.dirname(os.path.abspath(__file__))
            if current_dir not in sys.path:
                sys.path.insert(0, current_dir)
            
            from config import PRESET_CONFIGS
            self.preset_configs = PRESET_CONFIGS.copy()
        except:
            self.preset_configs = {}
        
        # Load custom presets from JSON file
        self.custom_presets_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'custom_presets.json')
        try:
            if os.path.exists(self.custom_presets_file):
                import json
                with open(self.custom_presets_file, 'r') as f:
                    custom_presets = json.load(f)
                    self.preset_configs.update(custom_presets)
                    print(f"Loaded {len(custom_presets)} custom presets")
        except Exception as e:
            print(f"Error loading custom presets: {e}")
        
    def load_api_key(self):
        """Load API key from file if it exists"""
        # Try roic key first (more likely to be set)
        if os.path.exists("roic_api_key.txt"):
            with open("roic_api_key.txt", "r") as f:
                return f.read().strip()
        # Fall back to generic api_key.txt
        if os.path.exists("api_key.txt"):
            with open("api_key.txt", "r") as f:
                return f.read().strip()
        return ""
    
    def save_api_key(self):
        """Save API key to file"""
        api_key = self.api_key_entry.get().strip()
        source = self.data_source_var.get()
        
        if api_key:
            filename = "roic_api_key.txt" if source == "roic" else "api_key.txt"
            with open(filename, "w") as f:
                f.write(api_key)
            messagebox.showinfo("Saved", f"API key saved to {filename}")
    
    def on_input_type_changed(self):
        """Update growth rate label when input type changes"""
        input_type = self.input_type_var.get()
        
        if input_type == "eps_cont_ops":
            self.growth_rate_label.config(text="EPS Growth Rate:")
        else:
            self.growth_rate_label.config(text="FCF Growth Rate:")
    
    def on_data_source_changed(self):
        """Handle data source selection change"""
        source = self.data_source_var.get()
        
        if source == "roic":
            self.api_key_status.config(
                text="⚠ Roic.ai requires API key (30+ years of data)",
                foreground="orange"
            )
            # Load roic API key if saved
            if os.path.exists("roic_api_key.txt"):
                with open("roic_api_key.txt", "r") as f:
                    key = f.read().strip()
                    self.api_key_entry.delete(0, tk.END)
                    self.api_key_entry.insert(0, key)
            
            # Enable EPS option for roic
            self.eps_radio.config(state='normal')
        else:  # yahoo
            self.api_key_status.config(
                text="✓ Yahoo Finance - No key required!",
                foreground="green"
            )
            self.api_key_entry.delete(0, tk.END)
            
            # Disable EPS option and force FCF for yahoo
            self.input_type_var.set("fcf")
            self.on_input_type_changed()  # Update label
            self.eps_radio.config(state='disabled')
    
    def auto_load_data_source(self):
        """Auto-select data source and load key on startup"""
        # If roic key exists, default to roic
        if os.path.exists("roic_api_key.txt"):
            self.data_source_var.set("roic")
            self.on_data_source_changed()
        # Otherwise default to yahoo
        else:
            self.data_source_var.set("yahoo")
            self.on_data_source_changed()
        
    def create_widgets(self):
        """Create all GUI widgets"""
        
        # API Key Section
        api_frame = ttk.LabelFrame(self.root, text="Data Source Configuration", padding=10)
        api_frame.pack(fill="x", padx=10, pady=5)
        
        # Data source selection
        ttk.Label(api_frame, text="Data Source:").grid(row=0, column=0, sticky="w", pady=3)
        self.data_source_var = tk.StringVar(value="yahoo")
        
        data_source_frame = ttk.Frame(api_frame)
        data_source_frame.grid(row=0, column=1, columnspan=3, sticky="w", pady=3)
        
        ttk.Radiobutton(data_source_frame, text="Yahoo Finance (Free, 4-5 years)", 
                       variable=self.data_source_var, value="yahoo",
                       command=self.on_data_source_changed).pack(side="left", padx=5)
        ttk.Radiobutton(data_source_frame, text="Roic.ai (Paid, 30+ years)", 
                       variable=self.data_source_var, value="roic",
                       command=self.on_data_source_changed).pack(side="left", padx=5)
        
        # API Key input
        ttk.Label(api_frame, text="API Key:").grid(row=1, column=0, sticky="w", pady=3)
        self.api_key_entry = ttk.Entry(api_frame, width=50)
        self.api_key_entry.grid(row=1, column=1, padx=5, pady=3)
        self.api_key_entry.insert(0, "")
        
        self.api_key_status = ttk.Label(api_frame, text="✓ Yahoo Finance - No key required!", foreground="green")
        self.api_key_status.grid(row=1, column=2, sticky="w", pady=3, padx=5)
        
        # Tabs for different operations
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Tab 1: Single Stock Analysis
        self.single_tab = ttk.Frame(notebook)
        notebook.add(self.single_tab, text="Analyze Stock")
        self.create_single_analysis_tab()
        
        # Tab 2: Batch Analysis
        self.batch_tab = ttk.Frame(notebook)
        notebook.add(self.batch_tab, text="Batch Analysis")
        self.create_batch_analysis_tab()
        
        # Tab 3: Screening
        self.screen_tab = ttk.Frame(notebook)
        notebook.add(self.screen_tab, text="Screen Stocks")
        self.create_screening_tab()
        
        # Tab 4: Trending
        self.trend_tab = ttk.Frame(notebook)
        notebook.add(self.trend_tab, text="View Trends")
        self.create_trending_tab()
        
        # Output Area
        output_frame = ttk.LabelFrame(self.root, text="Output", padding=10)
        output_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.output_text = scrolledtext.ScrolledText(output_frame, height=10)
        self.output_text.pack(fill="both", expand=True)
        
    def create_single_analysis_tab(self):
        """Create single stock analysis tab"""
        main_frame = ttk.Frame(self.single_tab, padding=20)
        main_frame.pack(fill="both", expand=True)
        
        # Left side - Stock and Preset selection
        left_frame = ttk.Frame(main_frame)
        left_frame.grid(row=0, column=0, sticky="nw", padx=(0, 20))
        
        ttk.Label(left_frame, text="Stock Ticker:").grid(row=0, column=0, sticky="w", pady=5)
        self.ticker_entry = ttk.Entry(left_frame, width=20)
        self.ticker_entry.grid(row=0, column=1, sticky="w", pady=5)
        self.ticker_entry.insert(0, "AAPL")
        
        ttk.Label(left_frame, text="Parameter Preset:").grid(row=1, column=0, sticky="w", pady=5)
        preset_names = list(self.preset_configs.keys())
        self.preset_combo = ttk.Combobox(left_frame, values=preset_names, width=18, state="readonly")
        self.preset_combo.grid(row=1, column=1, sticky="w", pady=5)
        self.preset_combo.set("moderate")
        self.preset_combo.bind("<<ComboboxSelected>>", self.on_preset_changed)
        
        # DCF Input Type
        ttk.Label(left_frame, text="DCF Input Type:").grid(row=2, column=0, sticky="w", pady=(10,5))
        self.input_type_var = tk.StringVar(value="fcf")
        input_type_frame = ttk.Frame(left_frame)
        input_type_frame.grid(row=2, column=1, sticky="w", pady=(10,5))
        self.fcf_radio = ttk.Radiobutton(input_type_frame, text="FCF", variable=self.input_type_var, 
                       value="fcf", command=self.on_input_type_changed)
        self.fcf_radio.pack(side="left")
        self.eps_radio = ttk.Radiobutton(input_type_frame, text="EPS (Cont Ops)", variable=self.input_type_var, 
                       value="eps_cont_ops", command=self.on_input_type_changed)
        self.eps_radio.pack(side="left", padx=(10,0))
        
        ttk.Button(left_frame, text="Analyze Stock", command=self.run_single_analysis, width=20).grid(row=3, column=0, columnspan=2, pady=20)
        
        ttk.Label(left_frame, text="Examples: AAPL, MSFT, GOOGL, TSLA, META", font=("", 9, "italic")).grid(row=4, column=0, columnspan=2, pady=5)
        
        # Right side - Parameter display and customization
        right_frame = ttk.LabelFrame(main_frame, text="DCF Parameters", padding=10)
        right_frame.grid(row=0, column=1, sticky="nsew", padx=(20, 0))
        
        # Parameter controls
        self.param_entries = {}
        
        row = 0
        # WACC
        ttk.Label(right_frame, text="WACC (Discount Rate):").grid(row=row, column=0, sticky="w", pady=3)
        self.param_entries['wacc'] = ttk.Entry(right_frame, width=10, state="readonly")
        self.param_entries['wacc'].grid(row=row, column=1, sticky="w", pady=3, padx=5)
        self.wacc_pct_label = ttk.Label(right_frame, text="", foreground="gray")
        self.wacc_pct_label.grid(row=row, column=2, sticky="w", pady=3)
        
        row += 1
        # Terminal Growth Rate
        ttk.Label(right_frame, text="Terminal Growth Rate:").grid(row=row, column=0, sticky="w", pady=3)
        self.param_entries['terminal_growth_rate'] = ttk.Entry(right_frame, width=10, state="readonly")
        self.param_entries['terminal_growth_rate'].grid(row=row, column=1, sticky="w", pady=3, padx=5)
        self.terminal_pct_label = ttk.Label(right_frame, text="", foreground="gray")
        self.terminal_pct_label.grid(row=row, column=2, sticky="w", pady=3)
        
        row += 1
        # FCF Growth Rate
        self.growth_rate_label = ttk.Label(right_frame, text="FCF Growth Rate:")
        self.growth_rate_label.grid(row=row, column=0, sticky="w", pady=3)
        self.param_entries['fcf_growth_rate'] = ttk.Entry(right_frame, width=10, state="readonly")
        self.param_entries['fcf_growth_rate'].grid(row=row, column=1, sticky="w", pady=3, padx=5)
        self.revenue_pct_label = ttk.Label(right_frame, text="", foreground="gray")
        self.revenue_pct_label.grid(row=row, column=2, sticky="w", pady=3)
        
        row += 1
        # Projection Years
        ttk.Label(right_frame, text="Projection Years:").grid(row=row, column=0, sticky="w", pady=3)
        self.param_entries['projection_years'] = ttk.Entry(right_frame, width=10, state="readonly")
        self.param_entries['projection_years'].grid(row=row, column=1, sticky="w", pady=3, padx=5)
        
        row += 1
        # Conservative Adjustment
        ttk.Label(right_frame, text="Conservative Adjustment:").grid(row=row, column=0, sticky="w", pady=3)
        self.param_entries['conservative_adjustment'] = ttk.Entry(right_frame, width=10, state="readonly")
        self.param_entries['conservative_adjustment'].grid(row=row, column=1, sticky="w", pady=3, padx=5)
        self.conserv_pct_label = ttk.Label(right_frame, text="", foreground="gray")
        self.conserv_pct_label.grid(row=row, column=2, sticky="w", pady=3)
        
        row += 1
        # Separator
        ttk.Separator(right_frame, orient='horizontal').grid(row=row, column=0, columnspan=3, sticky="ew", pady=10)
        
        row += 1
        # Years of Historical Data (only for roic.ai)
        ttk.Label(right_frame, text="Years of History (Roic only):").grid(row=row, column=0, sticky="w", pady=3)
        self.years_back_entry = ttk.Entry(right_frame, width=10, state="normal")
        self.years_back_entry.grid(row=row, column=1, sticky="w", pady=3, padx=5)
        self.years_back_entry.insert(0, "10")
        ttk.Label(right_frame, text="(1-30 years)", foreground="gray", font=("", 8)).grid(row=row, column=2, sticky="w", pady=3)
        
        row += 1
        # Status label
        self.param_status_label = ttk.Label(right_frame, text="Using preset: moderate", foreground="blue", font=("", 9, "italic"))
        self.param_status_label.grid(row=row, column=0, columnspan=3, sticky="w", pady=(10, 5))
        
        row += 1
        # Buttons frame
        button_frame = ttk.Frame(right_frame)
        button_frame.grid(row=row, column=0, columnspan=3, sticky="w", pady=5)
        
        self.customize_btn = ttk.Button(button_frame, text="Customize", command=self.enable_customization)
        self.customize_btn.pack(side="left", padx=(0, 5))
        
        self.save_preset_btn = ttk.Button(button_frame, text="Save As Preset", command=self.save_custom_preset, state="disabled")
        self.save_preset_btn.pack(side="left", padx=5)
        
        self.reset_btn = ttk.Button(button_frame, text="Reset to Preset", command=self.reset_to_preset, state="disabled")
        self.reset_btn.pack(side="left", padx=5)
        
        # Initialize with moderate preset
        self.is_custom_mode = False
        self.load_preset_parameters("moderate")
        
        # Configure grid weights
        main_frame.columnconfigure(1, weight=1)
    
    def on_preset_changed(self, event=None):
        """Handle preset selection change"""
        preset_name = self.preset_combo.get()
        self.load_preset_parameters(preset_name)
        
        # Reset to preset mode
        if self.is_custom_mode:
            self.disable_customization()
    
    def load_preset_parameters(self, preset_name):
        """Load preset parameters into the UI"""
        if preset_name not in self.preset_configs:
            return
        
        preset = self.preset_configs[preset_name]
        
        # Update entries
        for key, entry in self.param_entries.items():
            value = preset.get(key, 0)
            entry.config(state="normal")
            entry.delete(0, tk.END)
            entry.insert(0, str(value))
            entry.config(state="readonly")
        
        # Update percentage labels
        wacc = preset.get('wacc', 0)
        self.wacc_pct_label.config(text=f"({wacc*100:.1f}%)")
        
        terminal = preset.get('terminal_growth_rate', 0)
        self.terminal_pct_label.config(text=f"({terminal*100:.1f}%)")
        
        revenue = preset.get('fcf_growth_rate', 0)
        self.revenue_pct_label.config(text=f"({revenue*100:.1f}%)")
        
        conserv = preset.get('conservative_adjustment', 0)
        self.conserv_pct_label.config(text=f"({conserv*100:.1f}%)")
        
        # Update status
        self.param_status_label.config(text=f"Using preset: {preset_name}", foreground="blue")
        self.is_custom_mode = False
    
    def enable_customization(self):
        """Enable parameter editing"""
        for entry in self.param_entries.values():
            entry.config(state="normal")
        
        self.customize_btn.config(state="disabled")
        self.save_preset_btn.config(state="normal")
        self.reset_btn.config(state="normal")
        self.param_status_label.config(text="Custom parameters (modified)", foreground="orange")
        self.is_custom_mode = True
        
        # Bind change events to update percentage labels
        self.param_entries['wacc'].bind('<KeyRelease>', lambda e: self.update_percentage_labels())
        self.param_entries['terminal_growth_rate'].bind('<KeyRelease>', lambda e: self.update_percentage_labels())
        self.param_entries['fcf_growth_rate'].bind('<KeyRelease>', lambda e: self.update_percentage_labels())
        self.param_entries['conservative_adjustment'].bind('<KeyRelease>', lambda e: self.update_percentage_labels())
    
    def disable_customization(self):
        """Disable parameter editing"""
        for entry in self.param_entries.values():
            entry.config(state="readonly")
        
        self.customize_btn.config(state="normal")
        self.save_preset_btn.config(state="disabled")
        self.reset_btn.config(state="disabled")
        self.is_custom_mode = False
        
        # Reset to current preset
        self.load_preset_parameters(self.preset_combo.get())
    
    def reset_to_preset(self):
        """Reset parameters to selected preset"""
        self.disable_customization()
    
    def update_percentage_labels(self):
        """Update percentage labels when values change"""
        try:
            wacc = float(self.param_entries['wacc'].get())
            self.wacc_pct_label.config(text=f"({wacc*100:.1f}%)")
        except:
            pass
        
        try:
            terminal = float(self.param_entries['terminal_growth_rate'].get())
            self.terminal_pct_label.config(text=f"({terminal*100:.1f}%)")
        except:
            pass
        
        try:
            revenue = float(self.param_entries['fcf_growth_rate'].get())
            self.revenue_pct_label.config(text=f"({revenue*100:.1f}%)")
        except:
            pass
        
        try:
            conserv = float(self.param_entries['conservative_adjustment'].get())
            self.conserv_pct_label.config(text=f"({conserv*100:.1f}%)")
        except:
            pass
    
    def save_custom_preset(self):
        """Save custom parameters as a preset"""
        from tkinter import simpledialog
        import json
        import os
        
        # Ask user if they want to update existing or create new
        current_preset = self.preset_combo.get()
        
        # Check if current preset is a built-in one
        from config import PRESET_CONFIGS
        is_builtin = current_preset in PRESET_CONFIGS
        
        if is_builtin:
            # For built-in presets, only offer "Save As New"
            preset_name = simpledialog.askstring(
                "Save As New Preset",
                f"'{current_preset}' is a built-in preset and cannot be modified.\n\n"
                "Enter a name for your custom preset:",
                initialvalue=f"{current_preset}_custom"
            )
            if not preset_name:
                return
        else:
            # For custom presets, offer update or save as new
            choice = messagebox.askyesnocancel(
                "Save Preset",
                f"Update existing preset '{current_preset}'?\n\n"
                "Yes = Update existing\n"
                "No = Save as new preset\n"
                "Cancel = Don't save"
            )
            
            if choice is None:  # Cancel
                return
            
            if choice:  # Yes - update existing
                preset_name = current_preset
            else:  # No - create new
                preset_name = simpledialog.askstring(
                    "New Preset Name",
                    "Enter a name for this preset:",
                    initialvalue=f"{current_preset}_copy"
                )
                if not preset_name:
                    return
        
        # Collect parameters
        try:
            new_preset = {
                "name": preset_name.replace("_", " ").title(),
                "description": f"Custom preset - {preset_name}",
                "wacc": float(self.param_entries['wacc'].get()),
                "terminal_growth_rate": float(self.param_entries['terminal_growth_rate'].get()),
                "fcf_growth_rate": float(self.param_entries['fcf_growth_rate'].get()),
                "projection_years": int(self.param_entries['projection_years'].get()),
                "conservative_adjustment": float(self.param_entries['conservative_adjustment'].get())
            }
        except ValueError as e:
            messagebox.showerror("Invalid Values", f"Please enter valid numeric values.\n{e}")
            return
        
        # Load existing custom presets
        custom_presets = {}
        if os.path.exists(self.custom_presets_file):
            try:
                with open(self.custom_presets_file, 'r') as f:
                    custom_presets = json.load(f)
            except:
                pass
        
        # Add/update preset
        custom_presets[preset_name] = new_preset
        
        # Save to file
        try:
            with open(self.custom_presets_file, 'w') as f:
                json.dump(custom_presets, f, indent=4)
            
            # Reload presets immediately
            self.preset_configs.update(custom_presets)
            preset_names = list(self.preset_configs.keys())
            self.preset_combo['values'] = preset_names
            self.preset_combo.set(preset_name)
            
            # Load the new preset
            self.load_preset_parameters(preset_name)
            self.disable_customization()
            
            messagebox.showinfo("Success", f"Preset '{preset_name}' saved successfully!")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save preset: {e}")
    
    def save_preset_to_file(self, preset_name, preset_data):
        """Save preset to config.py file"""
        try:
            import os
            config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.py')
            
            print(f"Saving preset '{preset_name}' to {config_path}")
            
            # Read current config
            with open(config_path, 'r') as f:
                lines = f.readlines()
            
            # Find PRESET_CONFIGS section
            start_idx = None
            end_idx = None
            for i, line in enumerate(lines):
                if 'PRESET_CONFIGS = {' in line:
                    start_idx = i
                if start_idx is not None and line.strip() == '}':
                    # Make sure this is the closing brace for PRESET_CONFIGS
                    # Check if next non-empty line starts SCREENING_PRESETS
                    is_preset_end = False
                    for j in range(i+1, min(i+5, len(lines))):
                        if lines[j].strip():
                            if 'SCREENING_PRESETS' in lines[j]:
                                is_preset_end = True
                            break
                    if is_preset_end:
                        end_idx = i
                        break
            
            if start_idx is None or end_idx is None:
                print(f"Could not find PRESET_CONFIGS section. start={start_idx}, end={end_idx}")
                return False
            
            print(f"Found PRESET_CONFIGS from line {start_idx} to {end_idx}")
            
            # Build new preset entry
            new_entry = f'''    "{preset_name}": {{
        "name": "{preset_data['name']}",
        "description": "{preset_data['description']}",
        "wacc": {preset_data['wacc']},
        "terminal_growth_rate": {preset_data['terminal_growth_rate']},
        "projection_years": {preset_data['projection_years']},
        "fcf_growth_rate": {preset_data['fcf_growth_rate']},
        "conservative_adjustment": {preset_data['conservative_adjustment']}
    }},
'''
            
            # Check if preset already exists
            preset_exists = False
            preset_start = None
            preset_end = None
            
            for i in range(start_idx, end_idx):
                if f'"{preset_name}":' in lines[i]:
                    preset_exists = True
                    preset_start = i
                    print(f"Preset '{preset_name}' already exists at line {i}")
                    # Find end of this preset (next preset or closing brace)
                    indent_level = len(lines[i]) - len(lines[i].lstrip())
                    for j in range(i+1, end_idx):
                        # Check if this line starts a new preset (same indent, has quotes and colon)
                        if lines[j].strip() and not lines[j].strip().startswith('"'):
                            continue
                        line_indent = len(lines[j]) - len(lines[j].lstrip())
                        if line_indent == indent_level and '":' in lines[j]:
                            preset_end = j
                            break
                    if preset_end is None:
                        preset_end = end_idx
                    print(f"Preset ends at line {preset_end}")
                    break
            
            # Update or add preset
            if preset_exists:
                # Replace existing preset
                print(f"Replacing lines {preset_start} to {preset_end}")
                lines[preset_start:preset_end] = [new_entry]
            else:
                # Add new preset before closing brace
                print(f"Adding new preset at line {end_idx}")
                lines.insert(end_idx, new_entry)
            
            # Write back to file
            with open(config_path, 'w') as f:
                f.writelines(lines)
            
            print(f"Successfully saved preset '{preset_name}'")
            return True
        except Exception as e:
            print(f"Error saving preset: {e}")
            import traceback
            traceback.print_exc()
            return False
        
    def create_batch_analysis_tab(self):
        """Create batch analysis tab"""
        frame = ttk.Frame(self.batch_tab, padding=20)
        frame.pack(fill="both", expand=True)
        
        ttk.Label(frame, text="Exchange:").grid(row=0, column=0, sticky="w", pady=5)
        self.exchange_combo = ttk.Combobox(frame, values=["NASDAQ", "NYSE", "AMEX"], width=18)
        self.exchange_combo.grid(row=0, column=1, sticky="w", pady=5)
        self.exchange_combo.set("NASDAQ")
        
        ttk.Label(frame, text="Limit (number of stocks):").grid(row=1, column=0, sticky="w", pady=5)
        self.limit_entry = ttk.Entry(frame, width=20)
        self.limit_entry.grid(row=1, column=1, sticky="w", pady=5)
        self.limit_entry.insert(0, "20")
        
        ttk.Label(frame, text="Delay (seconds):").grid(row=2, column=0, sticky="w", pady=5)
        self.delay_entry = ttk.Entry(frame, width=20)
        self.delay_entry.grid(row=2, column=1, sticky="w", pady=5)
        self.delay_entry.insert(0, "1.0")
        
        ttk.Button(frame, text="Start Batch Analysis", command=self.run_batch_analysis, width=20).grid(row=3, column=0, columnspan=2, pady=20)
        
        ttk.Label(frame, text="Note: Free tier allows ~40 stocks per day", font=("", 9, "italic")).grid(row=4, column=0, columnspan=2, pady=5)
        
    def create_screening_tab(self):
        """Create screening tab"""
        frame = ttk.Frame(self.screen_tab, padding=20)
        frame.pack(fill="both", expand=True)
        
        ttk.Label(frame, text="Minimum Discount %:").grid(row=0, column=0, sticky="w", pady=5)
        self.discount_entry = ttk.Entry(frame, width=20)
        self.discount_entry.grid(row=0, column=1, sticky="w", pady=5)
        self.discount_entry.insert(0, "15")
        
        ttk.Label(frame, text="Show Top N Results:").grid(row=1, column=0, sticky="w", pady=5)
        self.top_entry = ttk.Entry(frame, width=20)
        self.top_entry.grid(row=1, column=1, sticky="w", pady=5)
        self.top_entry.insert(0, "20")
        
        ttk.Button(frame, text="Screen for Opportunities", command=self.run_screening, width=25).grid(row=2, column=0, columnspan=2, pady=20)
        
        ttk.Label(frame, text="Note: You must analyze stocks first before screening", font=("", 9, "italic")).grid(row=3, column=0, columnspan=2, pady=5)
        
    def create_trending_tab(self):
        """Create trending analysis tab"""
        frame = ttk.Frame(self.trend_tab, padding=20)
        frame.pack(fill="both", expand=True)
        
        ttk.Label(frame, text="Stock Ticker:").grid(row=0, column=0, sticky="w", pady=5)
        self.trend_ticker_entry = ttk.Entry(frame, width=20)
        self.trend_ticker_entry.grid(row=0, column=1, sticky="w", pady=5)
        self.trend_ticker_entry.insert(0, "AAPL")
        
        ttk.Label(frame, text="Number of Periods:").grid(row=1, column=0, sticky="w", pady=5)
        self.periods_entry = ttk.Entry(frame, width=20)
        self.periods_entry.grid(row=1, column=1, sticky="w", pady=5)
        self.periods_entry.insert(0, "5")
        
        ttk.Button(frame, text="View Trending Analysis", command=self.run_trending, width=25).grid(row=2, column=0, columnspan=2, pady=20)
        
        ttk.Label(frame, text="Note: Requires multiple analyses over time", font=("", 9, "italic")).grid(row=3, column=0, columnspan=2, pady=5)
    
    def open_api_website(self):
        """Open API key website"""
        import webbrowser
        webbrowser.open("https://financialmodelingprep.com/developer/docs/")
        
    def get_python_command(self):
        """Get the correct python command"""
        return sys.executable
    
    def run_command(self, cmd):
        """Run a command and show output"""
        self.output_text.delete(1.0, tk.END)
        self.output_text.insert(tk.END, f"Running: {' '.join(cmd)}\n\n")
        self.output_text.see(tk.END)
        
        def execute():
            try:
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    universal_newlines=True,
                    bufsize=1
                )
                
                for line in process.stdout:
                    self.output_text.insert(tk.END, line)
                    self.output_text.see(tk.END)
                    self.root.update()
                
                process.wait()
                
                if process.returncode == 0:
                    self.output_text.insert(tk.END, "\n✓ Command completed successfully!\n")
                else:
                    self.output_text.insert(tk.END, f"\n✗ Command failed with code {process.returncode}\n")
                    
            except Exception as e:
                self.output_text.insert(tk.END, f"\n✗ Error: {str(e)}\n")
            
            self.output_text.see(tk.END)
        
        thread = threading.Thread(target=execute, daemon=True)
        thread.start()
    
    def run_single_analysis(self):
        """Run single stock analysis"""
        api_key = self.api_key_entry.get().strip()
        ticker = self.ticker_entry.get().strip().upper()
        data_source = self.data_source_var.get()
        
        # API key handling based on source
        if data_source == "roic" and not api_key:
            messagebox.showwarning("API Key Required", "Roic.ai requires an API key. Please enter your key.")
            return
        
        if not api_key:
            api_key = "not_needed"
        
        if not ticker:
            messagebox.showwarning("No Ticker", "Please enter a stock ticker")
            return
        
        # Build command
        cmd = [
            self.get_python_command(),
            "main.py",
            "--api-key", api_key,
            "--data-source", data_source,
            "analyze", ticker
        ]
        
        # Add years-back parameter for roic
        if data_source == "roic":
            try:
                years_back = self.years_back_entry.get().strip()
                if years_back:
                    cmd.extend(["--years-back", years_back])
            except:
                pass  # Use default if error
        
        # If in custom mode, pass individual parameters
        if self.is_custom_mode:
            try:
                cmd.extend(["--wacc", self.param_entries['wacc'].get()])
                cmd.extend(["--growth", self.param_entries['fcf_growth_rate'].get()])
                cmd.extend(["--terminal", self.param_entries['terminal_growth_rate'].get()])
            except Exception as e:
                messagebox.showerror("Error", f"Invalid parameter values: {e}")
                return
        else:
            # Use preset
            preset = self.preset_combo.get().strip()
            if preset:
                cmd.extend(["--preset", preset])
        
        # Always send input type (works in both custom and preset mode)
        cmd.extend(["--input-type", self.input_type_var.get()])
        
        self.run_command(cmd)
    
    def run_batch_analysis(self):
        """Run batch analysis"""
        api_key = self.api_key_entry.get().strip()
        exchange = self.exchange_combo.get()
        limit = self.limit_entry.get().strip()
        delay = self.delay_entry.get().strip()
        
        # API key not needed with Yahoo Finance
        if not api_key:
            api_key = "not_needed_with_yahoo_finance"
        
        cmd = [
            self.get_python_command(),
            "main.py",
            "--api-key", api_key,
            "batch", exchange,
            "--limit", limit,
            "--delay", delay
        ]
        
        self.run_command(cmd)
    
    def run_screening(self):
        """Run screening"""
        discount = self.discount_entry.get().strip()
        top = self.top_entry.get().strip()
        
        cmd = [
            self.get_python_command(),
            "main.py",
            "screen",
            "--min-discount", discount,
            "--top", top
        ]
        
        self.run_command(cmd)
    
    def run_trending(self):
        """Run trending analysis"""
        ticker = self.trend_ticker_entry.get().strip().upper()
        periods = self.periods_entry.get().strip()
        
        if not ticker:
            messagebox.showwarning("No Ticker", "Please enter a stock ticker")
            return
        
        cmd = [
            self.get_python_command(),
            "main.py",
            "trending", ticker,
            "--periods", periods
        ]
        
        self.run_command(cmd)


def main():
    root = tk.Tk()
    app = DCFAnalyzerGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
