# Bus Display Terminology

This document defines the standard terminology used throughout the Bus Display project.

## Display Components

**Stop Card**: The main rectangular card displaying information for a single bus/tram stop. Contains the stop name, icons, and timing cards. Maximum of 4 stop cards can be displayed simultaneously.

**Timing Card**: The small vertical rectangular cards within each stop card that show departure information. Each timing card displays:
- Minutes until departure (top)
- Bus/tram line number (bottom)
- Color-coded background (red for NOW, orange for ≤2 minutes, gray for >2 minutes)

**Clock Display**: The time display showing current time in HH:MM:SS format. Position varies based on number of stops:
- 1 stop: Bottom center
- 2 stops: Left side
- 3+ stops: Top corner

**Weather Display**: Shows current weather information including rain status and temperature range. Position varies based on number of stops:
- 1 stop: Bottom center (below clock)
- 2 stops: Left side (below clock)
- 3+ stops: Bottom center

## Layout Terms

**Stop Layout**: The arrangement of stop cards on screen:
- 1 stop: Centered at top with info at bottom
- 2 stops: Vertical stack on right side with info on left
- 3 stops: Two on top, one centered below
- 4+ stops: 2x2 grid

**Grid Scale**: Size multiplier applied to stop cards:
- 1 stop: 1.0 (full size)
- 2 stops: 0.9 (slightly smaller for weather space)
- 3+ stops: 0.7 (shrunk to fit more cards)

## Configuration Terms

**Lines Include**: Filter to show only specific bus/tram lines from a stop, optionally filtered by destination terminal.

**Lines Exclude**: Filter to hide specific bus/tram lines from a stop, optionally filtered by destination terminal.

**API Limit**: Maximum number of departures to fetch from the API for busy stops (default: 100).

**Fetch Interval**: Time in seconds between API data updates (default: 60).

**Max Minutes**: Hide departures beyond this many minutes in the future (default: 120).

## Technical Terms

**Stop ID**: The unique identifier for a bus/tram stop in the Search.ch API system.

**Terminal ID**: The unique identifier for a destination terminal/station.

**Departure Time**: The scheduled departure time including any real-time delays.

**Loading Spinner**: Animated character sequence (|/-\) shown during data fetching.