#!/usr/bin/env python3
import questionary
import requests
import csv
import io
import json
import os
import sys

ARRETS_CSV_URL = "https://raw.githubusercontent.com/rohanod/arrets/refs/heads/main/arrets.csv"
DEFAULT_CONFIG_PATH = os.path.expanduser("~/.config/busdisplay/config.json")

def download_and_parse_stops():
    """Downloads and parses the TPG stops CSV file."""
    try:
        print("Downloading stops data from GitHub...")
        response = requests.get(ARRETS_CSV_URL)
        response.raise_for_status()
        
        content = response.text
        # The first line of the CSV is the header, so we can read it directly.
        reader = csv.DictReader(io.StringIO(content), delimiter=';')
        
        stops = [row for row in reader if row.get('Actif') == 'Y' and row.get('Didoc Code')]
        print(f"Successfully loaded {len(stops)} active stops.")
        return stops
    except requests.exceptions.RequestException as e:
        print(f"Error downloading stops file: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"An error occurred while parsing stops data: {e}")
        sys.exit(1)

def find_stop(stops_data, prompt_text):
    """Interactively prompts the user to find and select a stop."""
    while True:
        try:
            search_term = questionary.text(prompt_text).ask()
            if not search_term:
                print("Search term cannot be empty.")
                continue

            matches = [
                stop for stop in stops_data 
                if search_term.lower() in stop.get('Stop', '').lower()
            ]

            if not matches:
                print(f"No stops found matching '{search_term}'. Please try again.")
                continue
            
            if len(matches) == 1:
                return matches[0]

            choices = [
                f"{stop['Stop']} ({stop['Municipality']}, {stop['Country']})" 
                for stop in matches
            ]
            selected_choice = questionary.select(
                "Multiple stops found. Please choose one:",
                choices=choices
            ).ask()
            
            if not selected_choice:
                return None

            for stop in matches:
                if selected_choice == f"{stop['Stop']} ({stop['Municipality']}, {stop['Country']})":
                    return stop
        except (KeyboardInterrupt, TypeError):
             print("\nOperation cancelled.")
             return None

def build_stop_config(stops_data):
    """Builds a single stop configuration entry."""
    print("\n--- Adding a new stop configuration ---")
    
    main_stop = find_stop(stops_data, "Enter the name of the stop to display:")
    if not main_stop:
        return None

    stop_id = main_stop.get('Didoc Code')
    if not stop_id:
        print(f"Error: Selected stop '{main_stop.get('Stop')}' has no Didoc Code.")
        return None

    config_entry = {"ID": stop_id}
    
    filter_type = questionary.select(
        f"For '{main_stop.get('Stop')}', do you want to include only specific lines or exclude certain lines?",
        choices=["LinesInclude", "LinesExclude"]
    ).ask()

    if not filter_type:
        return None

    lines_str = questionary.text(
        "Enter the line numbers to include/exclude (comma-separated, e.g., 10, 22, F):"
    ).ask()
    
    if not lines_str:
        print("No lines entered. Skipping this stop configuration.")
        return None

    lines = [line.strip() for line in lines_str.split(',')]
    lines_dict = {}

    for line in lines:
        add_destination = questionary.confirm(
            f"For line '{line}', do you want to filter by a specific destination?",
            default=False
        ).ask()

        if add_destination:
            destination_stop = find_stop(stops_data, f"Enter destination for line '{line}':")
            if destination_stop and destination_stop.get('Didoc Code'):
                lines_dict[line] = destination_stop.get('Didoc Code')
            else:
                print(f"Could not find a valid destination for line '{line}'. It will not be filtered by destination.")
                lines_dict[line] = None
        else:
            lines_dict[line] = None

    config_entry[filter_type] = lines_dict
    return config_entry

def main():
    """Main function to run the config generator."""
    print("Welcome to the Bus Display Config Generator!")
    
    stops_data = download_and_parse_stops()
    
    final_config = {"stops": []}
    if os.path.exists(DEFAULT_CONFIG_PATH):
        load_existing = questionary.confirm(
            f"An existing config was found at {DEFAULT_CONFIG_PATH}. Do you want to load it and add to it?",
            default=True
        ).ask()
        if load_existing:
            try:
                with open(DEFAULT_CONFIG_PATH, 'r') as f:
                    existing_data = json.load(f)
                    if "stops" in existing_data and isinstance(existing_data["stops"], list):
                         final_config = existing_data
                         print(f"Loaded {len(final_config['stops'])} existing stop configurations.")
                    else:
                         print("Existing config is in an unknown format. Starting fresh.")
            except (json.JSONDecodeError, IOError) as e:
                print(f"Could not read existing config file: {e}. Starting fresh.")

    while True:
        new_stop_config = build_stop_config(stops_data)
        if new_stop_config:
            final_config["stops"].append(new_stop_config)
            print("\n--- Current Configuration ---")
            print(json.dumps(final_config, indent=2))
            print("---------------------------\n")

        add_another = questionary.confirm("Add another stop?").ask()
        if not add_another:
            break
    
    if not final_config["stops"]:
        print("No configurations were created. Exiting.")
        sys.exit(0)

    save_config = questionary.confirm(
        f"Do you want to save this configuration to {DEFAULT_CONFIG_PATH}?",
        default=True
    ).ask()

    if save_config:
        try:
            os.makedirs(os.path.dirname(DEFAULT_CONFIG_PATH), exist_ok=True)
            with open(DEFAULT_CONFIG_PATH, 'w') as f:
                json.dump(final_config, f, indent=4)
            print(f"Configuration successfully saved to {DEFAULT_CONFIG_PATH}")
        except IOError as e:
            print(f"Error saving configuration file: {e}")

if __name__ == "__main__":
    main()
