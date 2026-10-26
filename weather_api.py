import json
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer

HOST = "127.0.0.1"
PORT = 8000
GEO_URL = "https://geocoding-api.open-meteo.com/v1/search"
WEATHER_URL = "https://api.open-meteo.com/v1/forecast"


def describe_weather(code):
    if code == 0:
        return "clear sky"
    if code <= 3:
        return "partly cloudy"
    if code <= 48:
        return "foggy"
    if code <= 57:
        return "drizzle"
    if code <= 67:
        return "rain"
    if code <= 77:
        return "snow"
    if code <= 82:
        return "rain showers"
    if code <= 86:
        return "snow showers"
    return "thunderstorm"


def get_json(url):
    with urllib.request.urlopen(url, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def get_weather(city):
    geo_query = urllib.parse.urlencode({"name": city, "count": 1})
    geo_data = get_json(GEO_URL + "?" + geo_query)

    if "results" not in geo_data:
        return "Sorry, I could not find a city named " + city + "."
    place = geo_data["results"][0]

    weather_query = urllib.parse.urlencode(
        {
            "latitude": place["latitude"],
            "longitude": place["longitude"],
            "current": "temperature_2m,weather_code,wind_speed_10m",
        },
        safe=",",
    )
    now = get_json(WEATHER_URL + "?" + weather_query)["current"]

    return (
        place["name"] + ", " + place.get("country", "") + ": "
        + str(now["temperature_2m"]) + " degrees C, "
        + describe_weather(now["weather_code"]) + ", wind "
        + str(now["wind_speed_10m"]) + " km/h"
    )


class WeatherHandler(BaseHTTPRequestHandler):
    def send_json(self, status, data):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        url = urllib.parse.urlparse(self.path)
        if url.path != "/weather":
            self.send_json(404, {"error": "Not found"})
            return

        city = urllib.parse.parse_qs(url.query).get("city", [""])[0].strip()
        if city == "" or len(city) > 100:
            self.send_json(400, {"error": "Missing or invalid city"})
            return

        try:
            self.send_json(200, {"message": get_weather(city)})
        except Exception:
            self.send_json(502, {"error": "Weather service failed"})


if __name__ == "__main__":
    server = HTTPServer((HOST, PORT), WeatherHandler)
    print("Weather API running at http://" + HOST + ":" + str(PORT))
    server.serve_forever()
