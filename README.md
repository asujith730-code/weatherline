# Weatherline

A single-file weather app: current conditions, hourly details, a 7-day forecast, saved cities, and an interactive 3D weather map.

## Features
- Search any city and see its current weather
- Hourly forecast for the next 8 hours
- 7-day outlook with highs, lows, and rain chance
- Save up to 8 cities (stored in your browser's localStorage)
- 3D map with weather markers for saved cities (MapLibre GL + OpenFreeMap)
- Responsive layout for desktop and mobile

## Run it
No build step needed. Open `weather-app.html` in a browser, or serve the folder:

```bash
python -m http.server 8000
```

Then visit `http://localhost:8000/weather-app.html`.

## Data sources
- Weather and city search: [Open-Meteo](https://open-meteo.com/) (no API key required)
- Map: MapLibre GL JS with OpenFreeMap tiles, © OpenStreetMap contributors
- Fonts: Manrope and DM Mono (Google Fonts)

## Other projects in this repo
- `AI_CCTV_Attendance/`: AI-based attendance system using CCTV footage (add a short description here)

## Author
Vas Sujith
