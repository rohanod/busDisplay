#!/usr/bin/env python3
import questionary
import requests
import csv
import io
import json
import os
import sys
import unicodedata

# Default values (matching busdisplay.py)
DEFAULT_COLS = 8
DEFAULT_ROWS = 2
DEFAULT_CELL_W = 140
DEFAULT_BAR_H = 320
DEFAULT_BAR_MARGIN = 30
DEFAULT_BAR_PADDING = 25
DEFAULT_CARD_PADDING = 15
DEFAULT_MINUTE_SIZE = 48
DEFAULT_NOW_SIZE = 30
DEFAULT_STOP_NAME_SIZE = 48
DEFAULT_LINE_SIZE = 40
DEFAULT_ICON_SIZE = 60
DEFAULT_BORDER_RADIUS = 16
DEFAULT_SHADOW_OFFSET = 6
DEFAULT_GRID_SHRINK = 0.7
DEFAULT_ICON_LINE_MULTIPLIER = 1.0
DEFAULT_HTTP_TIMEOUT = 10
DEFAULT_FETCH_INTERVAL = 60
DEFAULT_WIDGET_SIZE = 320
DEFAULT_WIDGET_TEXT_SIZE = 36
DEFAULT_WIDGET_ICON_SIZE = 48

ARRETS_CSV_URL = "https://raw.githubusercontent.com/rohanod/arrets/refs/heads/main/arrets.csv"
DEFAULT_CONFIG_PATH = os.path.expanduser("~/.config/busdisplay/config.json")

# Default values from busdisplay.py
DEFAULTS = {
    "stops": [],
    "cols": DEFAULT_COLS, "rows": DEFAULT_ROWS, "cell_w": DEFAULT_CELL_W, 
    "bar_h": DEFAULT_BAR_H, "bar_margin": DEFAULT_BAR_MARGIN,
    "bar_padding": DEFAULT_BAR_PADDING, "card_padding": DEFAULT_CARD_PADDING, 
    "minute_size": DEFAULT_MINUTE_SIZE, "now_size": DEFAULT_NOW_SIZE,
    "stop_name_size": DEFAULT_STOP_NAME_SIZE, "line_size": DEFAULT_LINE_SIZE, 
    "icon_size": DEFAULT_ICON_SIZE, "icon_line_multiplier": DEFAULT_ICON_LINE_MULTIPLIER,
    "border_radius": DEFAULT_BORDER_RADIUS, "shadow_offset": DEFAULT_SHADOW_OFFSET, 
    "grid_shrink": DEFAULT_GRID_SHRINK, "max_departures": 8, 
    "fetch_interval": DEFAULT_FETCH_INTERVAL, "http_timeout": DEFAULT_HTTP_TIMEOUT, 
    "max_minutes": 120, "show_clock": True, "show_weather": True,
    "widget_size": DEFAULT_WIDGET_SIZE, "widget_text_size": DEFAULT_WIDGET_TEXT_SIZE,
    "widget_icon_size": DEFAULT_WIDGET_ICON_SIZE
}

# Config option descriptions for better UX
CONFIG_DESCRIPTIONS = {
    "cols": "Maximum departure columns",
    "rows": "Maximum stop rows", 
    "cell_w": "Base cell width",
    "bar_h": "Stop card height",
    "bar_margin": "Margin between stop cards",
    "bar_padding": "Padding inside stop cards",
    "card_padding": "Padding between elements",
    "minute_size": "Departure time font size",
    "now_size": "NOW text font size",
    "stop_name_size": "Stop name font size",
    "line_size": "Line number font size",
    "icon_size": "Clock/tram icon size",
    "icon_line_multiplier": "Icon line thickness multiplier",
    "border_radius": "Card corner radius",
    "shadow_offset": "Card shadow offset",
    "grid_shrink": "Shrink multiplier for 3+ stops",
    "max_departures": "Maximum departures per stop",
    "fetch_interval": "Seconds between data fetches",
    "http_timeout": "HTTP request timeout in seconds",
    "max_minutes": "Hide departures beyond X minutes",
    "show_clock": "Show current time widget",
    "show_weather": "Show weather widgets (temperature + condition)",
    "widget_size": "Widget size (all widgets)",
    "widget_text_size": "Widget text font size",
    "widget_icon_size": "Widget icon size"
}

# Categories for organized configuration
CATEGORIES = {
    "Layout": ["cols", "rows", "bar_margin", "bar_padding", "card_padding", "border_radius", "shadow_offset"],
    "Sizing": ["cell_w", "bar_h", "minute_size", "now_size", "stop_name_size", "line_size", "icon_size", "icon_line_multiplier", "grid_shrink"],
    "Widgets": ["show_clock", "show_weather", "widget_size", "widget_text_size", "widget_icon_size"],
    "API & Behavior": ["max_departures", "fetch_interval", "http_timeout", "max_minutes"]
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

def get_stop_name_by_id(stops_data, stop_id):
    for stop in stops_data:
        if stop.get('Didoc Code') == stop_id:
            return stop.get('Stop', 'Unknown')
    return 'Unknown'

def find_stop(stops_data, prompt_text):
    while True:
        try:
            search_term = questionary.text(prompt_text).ask()
            if not search_term:
                print("Search term cannot be empty.")
                continue

            # Flexible search: try multiple variants of the search term
            search_variants = [
                normalize_str(search_term),
                normalize_str(search_term.replace(' ', '-')),
                normalize_str(search_term.replace('-', ' ')),
                normalize_str(search_term.replace(' ', '')),
                normalize_str(search_term.replace('-', ''))
            ]
            
            matches = []
            for stop in stops_data:
                stop_name_normalized = normalize_str(stop.get('Stop', ''))
                stop_name_variants = [
                    stop_name_normalized,
                    stop_name_normalized.replace(' ', '-'),
                    stop_name_normalized.replace('-', ' '),
                    stop_name_normalized.replace(' ', ''),
                    stop_name_normalized.replace('-', '')
                ]
                
                # Check if any search variant matches any stop name variant
                for search_var in search_variants:
                    for name_var in stop_name_variants:
                        if search_var in name_var:
                            matches.append(stop)
                            break
                    if stop in matches:
                        break

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
        try:
            action = questionary.select(
                "Manage Stops:",
                choices=["Add a new stop", "Edit an existing stop", "Remove a stop", "Back to main menu"]
            ).ask()
        except KeyboardInterrupt:
            break

        if action is None:  # ESC pressed
            break
        elif action == "Add a new stop":
            stop_config = build_stop_config(stops_data)
            if stop_config:
                config["stops"].append(stop_config)
                print("Stop added.")
        elif action == "Edit an existing stop":
            if not config["stops"]:
                print("No stops configured to edit.")
                continue
            
            # Show current stops with names
            choices = []
            for i, stop in enumerate(config["stops"]):
                stop_name = get_stop_name_by_id(stops_data, stop.get('ID', 'Unknown'))
                choices.append(f"Stop {i+1}: {stop_name} ({stop.get('ID', 'Unknown')})")
            choices.append("Back")
            
            try:
                selected = questionary.select("Select stop to edit:", choices=choices).ask()
                if selected is None or selected == "Back":
                    continue
                
                stop_index = int(selected.split(":")[0].split()[1]) - 1
                config["stops"][stop_index] = edit_stop_config(config["stops"][stop_index], stops_data)
            except (KeyboardInterrupt, ValueError, IndexError):
                continue
                
        elif action == "Remove a stop":
            if not config["stops"]:
                print("No stops configured to remove.")
                continue
            
            # Show current stops with names
            choices = []
            for i, stop in enumerate(config["stops"]):
                stop_name = get_stop_name_by_id(stops_data, stop.get('ID', 'Unknown'))
                choices.append(f"Stop {i+1}: {stop_name} ({stop.get('ID', 'Unknown')})")
            choices.append("Back")
            
            try:
                selected = questionary.select("Select stop to remove:", choices=choices).ask()
                if selected is None or selected == "Back":
                    continue
                
                stop_index = int(selected.split(":")[0].split()[1]) - 1
                stop_to_remove = config["stops"][stop_index]
                
                stop_name = get_stop_name_by_id(stops_data, stop_to_remove.get('ID', 'Unknown'))
                if questionary.confirm(f"Remove stop {stop_name} ({stop_to_remove.get('ID', 'Unknown')})?").ask():
                    config["stops"].pop(stop_index)
                    print("Stop removed.")
            except (KeyboardInterrupt, ValueError, IndexError):
                continue
        elif action == "Back to main menu":
            break
    return config

def edit_stop_config(stop_config, stops_data):
    """Edit specific parts of a stop configuration"""
    while True:
        try:
            stop_name = get_stop_name_by_id(stops_data, stop_config.get('ID', 'Unknown'))
            print(f"\nEditing stop: {stop_name} ({stop_config.get('ID', 'Unknown')})")
            print(f"Current config: {json.dumps(stop_config, indent=2)}")
            
            choices = ["Change stop ID", "Edit line filters", "Change API limit", "Done editing"]
            action = questionary.select("What would you like to edit?", choices=choices).ask()
            
            if action is None or action == "Done editing":
                break
            elif action == "Change stop ID":
                new_stop = find_stop(stops_data, "Enter new stop name:")
                if new_stop:
                    stop_config["ID"] = new_stop.get('Didoc Code')
                    print(f"Stop ID changed to {stop_config['ID']}")
            elif action == "Edit line filters":
                edit_line_filters(stop_config, stops_data)
            elif action == "Change API limit":
                current_limit = stop_config.get("Limit", 100)
                new_limit = questionary.text(f"Enter API limit [current: {current_limit}]:", default=str(current_limit)).ask()
                if new_limit:
                    try:
                        stop_config["Limit"] = int(new_limit)
                        print(f"API limit changed to {stop_config['Limit']}")
                    except ValueError:
                        print("Invalid limit value.")
        except KeyboardInterrupt:
            break
    return stop_config

def edit_line_filters(stop_config, stops_data):
    """Edit line include/exclude filters"""
    while True:
        try:
            has_include = "LinesInclude" in stop_config
            has_exclude = "LinesExclude" in stop_config
            
            choices = []
            if has_include:
                choices.append("Edit LinesInclude")
                choices.append("Remove LinesInclude")
            if has_exclude:
                choices.append("Edit LinesExclude")
                choices.append("Remove LinesExclude")
            if not has_include:
                choices.append("Add LinesInclude")
            if not has_exclude:
                choices.append("Add LinesExclude")
            choices.append("Done with filters")
            
            action = questionary.select("Line filter options:", choices=choices).ask()
            if action is None or action == "Done with filters":
                break
            elif action == "Edit LinesInclude":
                edit_lines_dict(stop_config, "LinesInclude", stops_data)
            elif action == "Edit LinesExclude":
                edit_lines_dict(stop_config, "LinesExclude", stops_data)
            elif action == "Add LinesInclude":
                stop_config["LinesInclude"] = {}
                edit_lines_dict(stop_config, "LinesInclude", stops_data)
            elif action == "Add LinesExclude":
                stop_config["LinesExclude"] = {}
                edit_lines_dict(stop_config, "LinesExclude", stops_data)
            elif action == "Remove LinesInclude":
                del stop_config["LinesInclude"]
                print("LinesInclude removed")
            elif action == "Remove LinesExclude":
                del stop_config["LinesExclude"]
                print("LinesExclude removed")
        except KeyboardInterrupt:
            break

def edit_lines_dict(stop_config, filter_type, stops_data):
    """Edit the lines dictionary for include/exclude filters"""
    lines_dict = stop_config.get(filter_type, {})
    
    while True:
        try:
            print(f"\nCurrent {filter_type}: {json.dumps(lines_dict, indent=2)}")
            choices = ["Add line", "Edit line destination", "Remove line", "Done"]
            action = questionary.select(f"Edit {filter_type}:", choices=choices).ask()
            
            if action is None or action == "Done":
                break
            elif action == "Add line":
                line = questionary.text("Enter line number:").ask()
                if line:
                    if questionary.confirm(f"Filter line '{line}' by destination?", default=False).ask():
                        dest_stop = find_stop(stops_data, f"Enter destination for line '{line}':")
                        lines_dict[line] = dest_stop.get('Didoc Code') if dest_stop else None
                    else:
                        lines_dict[line] = None
            elif action == "Edit line destination":
                if not lines_dict:
                    print("No lines to edit")
                    continue
                line_choices = list(lines_dict.keys()) + ["Back"]
                selected_line = questionary.select("Select line to edit:", choices=line_choices).ask()
                if selected_line and selected_line != "Back":
                    if questionary.confirm(f"Filter line '{selected_line}' by destination?", default=bool(lines_dict[selected_line])).ask():
                        dest_stop = find_stop(stops_data, f"Enter destination for line '{selected_line}':")
                        lines_dict[selected_line] = dest_stop.get('Didoc Code') if dest_stop else None
                    else:
                        lines_dict[selected_line] = None
            elif action == "Remove line":
                if not lines_dict:
                    print("No lines to remove")
                    continue
                line_choices = list(lines_dict.keys()) + ["Back"]
                selected_line = questionary.select("Select line to remove:", choices=line_choices).ask()
                if selected_line and selected_line != "Back":
                    del lines_dict[selected_line]
                    print(f"Line '{selected_line}' removed")
        except KeyboardInterrupt:
            break
    
    stop_config[filter_type] = lines_dict

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

def fuzzy_search_config(query, config_keys):
    """Simple fuzzy search for config keys"""
    query = query.lower()
    matches = []
    for key in config_keys:
        key_lower = key.lower()
        desc_lower = CONFIG_DESCRIPTIONS.get(key, "").lower()
        if query in key_lower or query in desc_lower:
            matches.append(key)
    return matches

def configure_single_option(config, key):
    """Configure a single config option"""
    default_val = DEFAULTS.get(key, "")
    current_val = config.get(key, default_val)
    description = CONFIG_DESCRIPTIONS.get(key, "")
    
    prompt = f"{key}"
    if description:
        prompt += f" ({description})"
    prompt += f" [current: {current_val}]:"
    
    try:
        new_val = questionary.text(prompt, default=str(current_val)).ask()
        if new_val is None:  # ESC pressed
            return config
        
        # Cast to correct type
        if isinstance(default_val, bool):
            config[key] = new_val.lower() in ['true', '1', 't', 'y', 'yes']
        elif isinstance(default_val, int):
            config[key] = int(new_val)
        elif isinstance(default_val, float):
            config[key] = float(new_val)
        else:
            config[key] = new_val
        print(f"Updated {key} to {config[key]}")
    except KeyboardInterrupt:
        pass
    except (ValueError, TypeError):
        print(f"Invalid input for {key}. Keeping current value: {current_val}")
    return config

def manage_category_settings(config, category_name, category_keys):
    """Manage settings within a specific category with browsable list"""
    page_size = 10
    current_page = 0
    search_mode = False
    search_results = []
    
    while True:
        try:
            if search_mode:
                # Search mode - show search results
                available_keys = search_results
                prompt = f"Search results for {category_name} (type to search again, Enter to browse all):"
            else:
                # Browse mode - show paginated list
                available_keys = category_keys
                prompt = f"Browse {category_name} options (type to search, Enter to continue):"
            
            # Get user input
            user_input = questionary.text(prompt).ask()
            if user_input is None:  # ESC pressed
                break
            
            if user_input.strip():
                # User typed something - switch to search mode
                matches = fuzzy_search_config(user_input, category_keys)
                if not matches:
                    print(f"No {category_name.lower()} options found matching '{user_input}'")
                    continue
                search_results = matches
                search_mode = True
                current_page = 0
            else:
                # User pressed Enter - show current page
                search_mode = False
            
            # Paginate results
            start_idx = current_page * page_size
            end_idx = start_idx + page_size
            page_keys = available_keys[start_idx:end_idx]
            
            # Create choices with descriptions
            choices = []
            for key in page_keys:
                desc = CONFIG_DESCRIPTIONS.get(key, "")
                current_val = config.get(key, DEFAULTS.get(key, ""))
                choice_text = f"{key}: {desc} [current: {current_val}]"
                choices.append(choice_text)
            
            # Add navigation options
            if current_page > 0:
                choices.append("← Previous page")
            if end_idx < len(available_keys):
                choices.append("→ Next page")
            if search_mode:
                choices.append("Browse all options")
            choices.append("Back to main menu")
            
            selected = questionary.select(f"Select {category_name.lower()} option to configure:", choices=choices).ask()
            if selected is None or selected == "Back to main menu":
                break
            elif selected == "← Previous page":
                current_page = max(0, current_page - 1)
            elif selected == "→ Next page":
                current_page += 1
            elif selected == "Browse all options":
                search_mode = False
                current_page = 0
            else:
                # Extract key from choice text and configure
                selected_key = selected.split(":")[0]
                config = configure_single_option(config, selected_key)
            
        except KeyboardInterrupt:
            break
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

        try:
            choice = questionary.select(
                "What would you like to configure?",
                choices=["Manage Stops", "Layout", "Sizing", "API & Behavior", "Save and Restart", "Save and Exit", "Exit Without Saving"]
            ).ask()
        except KeyboardInterrupt:
            print("\nExiting configurator...")
            break

        if choice is None:  # ESC pressed
            break
        elif choice == "Manage Stops":
            if stops_data is None:
                stops_data = download_and_parse_stops()
                if stops_data is None:
                    print("Could not load stops data. Please check your internet connection.")
                    continue
            config = manage_stops(config, stops_data)
        elif choice in CATEGORIES:
            config = manage_category_settings(config, choice, CATEGORIES[choice])
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