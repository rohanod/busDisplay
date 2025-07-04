#!/usr/bin/env python3
import questionary
import requests
import csv
import io
import json
import os
import sys
import unicodedata

ARRETS_CSV_URL = "https://raw.githubusercontent.com/rohanod/arrets/refs/heads/main/arrets.csv"
DEFAULT_CONFIG_PATH = os.path.expanduser("~/.config/busdisplay/config.json")

# Default values from busdisplay.py
DEFAULTS = {
    "stops": [],
    "cols": 8, "rows": 2, "cell_w": 140, "bar_h": 320, "bar_margin": 30,
    "bar_padding": 25, "card_padding": 15, "number_size": 48, "now_size": 30,
    "stop_name_size": 48, "line_size": 36, "icon_size": 40, "border_radius": 16,
    "shadow_offset": 6, "scale_multiplier": 1.0, "max_departures": 8,
    "api_request_interval": 60, "max_minutes": 120, "show_clock": True
}

def load_config():
    if os.path.exists(DEFAULT_CONFIG_PATH):
        try:
            with open(DEFAULT_CONFIG_PATH, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Could not read existing config file: {e}. Starting with defaults.")
    return DEFAULTS.copy()

def save_config(config):
    try:
        os.makedirs(os.path.dirname(DEFAULT_CONFIG_PATH), exist_ok=True)
        with open(DEFAULT_CONFIG_PATH, 'w') as f:
            json.dump(config, f, indent=4)
        print(f"Configuration successfully saved to {DEFAULT_CONFIG_PATH}")
    except IOError as e:
        print(f"Error saving configuration file: {e}")

def download_and_parse_stops():
    try:
        print("Downloading stops data from GitHub...")
        response = requests.get(ARRETS_CSV_URL)
        response.raise_for_status()
        content = response.text
        reader = csv.DictReader(io.StringIO(content), delimiter=';')
        stops = [row for row in reader if row.get('Actif') == 'Y' and row.get('Didoc Code')]
        print(f"Successfully loaded {len(stops)} active stops.")
        return stops
    except requests.exceptions.RequestException as e:
        print(f"Error downloading stops file: {e}")
        return None
    except Exception as e:
        print(f"An error occurred while parsing stops data: {e}")
        return None

def normalize_str(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s.lower()) if unicodedata.category(c) != 'Mn')

def find_stop(stops_data, prompt_text):
    while True:
        try:
            search_term = questionary.text(prompt_text).ask()
            if not search_term:
                print("Search term cannot be empty.")
                continue

            normalized_search = normalize_str(search_term)
            matches = [s for s in stops_data if normalized_search in normalize_str(s.get('Stop', ''))]

            if not matches:
                print(f"No stops found matching '{search_term}'. Please try again.")
                continue

            if len(matches) == 1:
                stop = matches[0]
                if questionary.confirm(f"Is this the correct stop? {stop['Stop']} ({stop['Municipality']}, {stop['Country']})").ask():
                    return stop
                else:
                    print("Search cancelled. Please try again.")
                    continue
            
            choices = [f"{s['Stop']} ({s['Municipality']}, {s['Country']})" for s in matches]
            selected = questionary.select("Multiple stops found. Please choose one:", choices=choices).ask()
            if not selected: return None
            
            return next(s for s in matches if selected == f"{s['Stop']} ({s['Municipality']}, {s['Country']})")

        except (KeyboardInterrupt, TypeError):
            print("\nOperation cancelled.")
            return None

def manage_stops(config, stops_data):
    while True:
        action = questionary.select(
            "Manage Stops:",
            choices=["Add a new stop", "Edit an existing stop", "Remove a stop", "Back to main menu"]
        ).ask()

        if action == "Add a new stop":
            stop_config = build_stop_config(stops_data)
            if stop_config:
                config["stops"].append(stop_config)
                print("Stop added.")
        elif action == "Edit an existing stop":
            # Placeholder for edit functionality
            print("Edit functionality not yet implemented.")
            pass
        elif action == "Remove a stop":
            # Placeholder for remove functionality
            print("Remove functionality not yet implemented.")
            pass
        elif action == "Back to main menu":
            break
    return config

def build_stop_config(stops_data):
    print("\n--- Adding a new stop configuration ---")
    main_stop = find_stop(stops_data, "Enter the name of the stop to display:")
    if not main_stop: return None

    stop_id = main_stop.get('Didoc Code')
    if not stop_id:
        print(f"Error: Selected stop '{main_stop.get('Stop')}' has no Didoc Code.")
        return None

    config_entry = {"ID": stop_id}
    filter_type = questionary.select(
        f"For '{main_stop.get('Stop')}', include or exclude specific lines?",
        choices=["LinesInclude", "LinesExclude"]
    ).ask()
    if not filter_type: return None

    lines_str = questionary.text("Enter line numbers (comma-separated, e.g., 10, 22, F):").ask()
    if not lines_str:
        print("No lines entered. Skipping.")
        return None

    lines = [line.strip() for line in lines_str.split(',')]
    lines_dict = {}
    for line in lines:
        if questionary.confirm(f"For line '{line}', filter by a specific destination?", default=False).ask():
            dest_stop = find_stop(stops_data, f"Enter destination for line '{line}':")
            lines_dict[line] = dest_stop.get('Didoc Code') if dest_stop else None
        else:
            lines_dict[line] = None
    
    config_entry[filter_type] = lines_dict
    
    # Ask about API limit for busy stops
    if questionary.confirm(f"Is '{main_stop.get('Stop')}' a busy stop that needs more API results? (default: 100)", default=False).ask():
        limit = questionary.text("Enter API limit (e.g., 300 for very busy stops):", default="300").ask()
        try:
            config_entry["Limit"] = int(limit)
        except ValueError:
            print("Invalid limit value. Using default (100).")
    
    return config_entry

def manage_settings(config, section_name, settings):
    print(f"\n--- Configuring {section_name} Settings ---")
    for key, default_val in settings.items():
        current_val = config.get(key, default_val)
        new_val = questionary.text(f"{key} (current: {current_val}):", default=str(current_val)).ask()
        try:
            # Attempt to cast to the correct type (int, float, bool)
            if isinstance(default_val, bool):
                config[key] = new_val.lower() in ['true', '1', 't', 'y', 'yes']
            elif isinstance(default_val, int):
                config[key] = int(new_val)
            elif isinstance(default_val, float):
                config[key] = float(new_val)
            else:
                config[key] = new_val
        except (ValueError, TypeError):
            print(f"Invalid input for {key}. Keeping current value: {current_val}")
    return config

import subprocess

def main():
    print("Welcome to the Bus Display Config Generator!")
    config = load_config()
    stops_data = None # Lazy load stops data

    while True:
        print("\n--- Current Configuration ---")
        print(json.dumps(config, indent=2))
        print("---------------------------\n")

        choice = questionary.select(
            "What would you like to configure?",
            choices=["Stops", "Layout", "Sizing", "API & Behavior", "Save and Restart", "Save and Exit", "Exit Without Saving"]
        ).ask()

        if choice == "Stops":
            if stops_data is None:
                stops_data = download_and_parse_stops()
                if stops_data is None:
                    print("Could not load stops data. Please check your internet connection.")
                    continue
            config = manage_stops(config, stops_data)
        elif choice == "Layout":
            config = manage_settings(config, "Layout", {
                "cols": DEFAULTS["cols"], "rows": DEFAULTS["rows"], "bar_margin": DEFAULTS["bar_margin"],
                "bar_padding": DEFAULTS["bar_padding"], "card_padding": DEFAULTS["card_padding"],
                "border_radius": DEFAULTS["border_radius"], "shadow_offset": DEFAULTS["shadow_offset"]
            })
        elif choice == "Sizing":
            config = manage_settings(config, "Sizing", {
                "cell_w": DEFAULTS["cell_w"], "bar_h": DEFAULTS["bar_h"], "number_size": DEFAULTS["number_size"],
                "now_size": DEFAULTS["now_size"], "stop_name_size": DEFAULTS["stop_name_size"],
                "line_size": DEFAULTS["line_size"], "icon_size": DEFAULTS["icon_size"],
                "grid_shrink": 0.8
            })
        elif choice == "API & Behavior":
            config = manage_settings(config, "API & Behavior", {
                "max_departures": DEFAULTS["max_departures"], "api_request_interval": DEFAULTS["api_request_interval"],
                "max_minutes": DEFAULTS["max_minutes"], "show_clock": DEFAULTS["show_clock"]
            })
        elif choice == "Save and Restart":
            save_config(config)
            if questionary.confirm("Do you want to restart the bus display service now?").ask():
                print("Attempting to restart the service...")
                try:
                    subprocess.run(["sudo", "systemctl", "restart", "busdisplay"], check=True)
                    print("Service restarted successfully.")
                except (subprocess.CalledProcessError, FileNotFoundError) as e:
                    print(f"Failed to restart service: {e}")
                    print("Please ensure the service is installed and you are running this script on the Raspberry Pi.")
            break
        elif choice == "Save and Exit":
            save_config(config)
            break
        elif choice == "Exit Without Saving":
            if questionary.confirm("Are you sure you want to exit without saving your changes?").ask():
                break
        elif choice is None: # User pressed Ctrl+C
            break


if __name__ == "__main__":
    main()