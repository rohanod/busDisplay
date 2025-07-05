import requests

LAT = 46.1925
LON = 6.17017
URL = "https://api.open-meteo.com/v1/forecast"
params = {
    "latitude": LAT,
    "longitude": LON,
    "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
    "timezone": "Europe/Zurich"
}

resp = requests.get(URL, params=params)
data = resp.json()

today = data["daily"]
min_temp = today["temperature_2m_min"][0]
max_temp = today["temperature_2m_max"][0]
rain_sum = today["precipitation_sum"][0]

print(f"Lowest temperature: {min_temp}°C")
print(f"Highest temperature: {max_temp}°C")
print("Will it rain today? " + ("Yes" if rain_sum > 0 else "No"))
