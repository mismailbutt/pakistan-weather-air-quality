import os
import sqlite3
from flask import Flask, request, render_template_string

app = Flask(__name__)
DB = os.path.join(os.path.dirname(__file__), "weather.db")
CITIES = ["Lahore", "Karachi", "Islamabad", "Peshawar", "Quetta"]

PAGE = """
<h1>Pakistan Weather & Air Quality</h1>

<form>
  City:
  <select name="city">
    {% for c in cities %}<option {{ 'selected' if c == city }}>{{ c }}</option>{% endfor %}
  </select>
  Date:
  <input type="date" name="date" value="{{ date }}" min="2024-01-01" max="2025-12-31">
  <button>Show</button>
</form>

{% if s and s[0] is not none %}
  <h2>{{ city }} - {{ date }}</h2>
  <ul>
    <li>Average temperature: {{ s[0] }} °C (min {{ s[2] }}, max {{ s[1] }})</li>
    <li>Total rain: {{ s[3] }} mm</li>
    <li>Average humidity: {{ s[4] }} %</li>
    <li>Average PM2.5: {{ s[5] }}</li>
    <li>Average AQI: {{ s[6] }} ({{ level }})</li>
  </ul>

  <h3>Hourly data</h3>
  <table border="1" cellpadding="5">
    <tr><th>Time</th><th>Temp (°C)</th><th>Rain (mm)</th><th>PM2.5</th><th>AQI</th></tr>
    {% for r in rows %}<tr>{% for x in r %}<td>{{ x }}</td>{% endfor %}</tr>{% endfor %}
  </table>
{% else %}
  <p>No data for this date.</p>
{% endif %}
"""

def aqi_level(a):
    if a is None: return "unknown"
    if a <= 50: return "Good"
    if a <= 100: return "Moderate"
    if a <= 150: return "Unhealthy for sensitive groups"
    if a <= 200: return "Unhealthy"
    return "Very unhealthy"

@app.route("/")
def home():
    city = request.args.get("city", "Lahore")
    date = request.args.get("date", "2025-06-15")

    conn = sqlite3.connect(DB)
    s = conn.execute("""SELECT ROUND(AVG(temperature),1), MAX(temperature), MIN(temperature),
                        ROUND(SUM(rain),1), ROUND(AVG(humidity)), ROUND(AVG(pm25),1), ROUND(AVG(aqi))
                        FROM readings WHERE city=? AND date=?""", (city, date)).fetchone()
    rows = conn.execute("""SELECT substr(time,12,5), temperature, rain, pm25, aqi
                           FROM readings WHERE city=? AND date=? ORDER BY time""",
                        (city, date)).fetchall()
    conn.close()

    return render_template_string(PAGE, cities=CITIES, city=city, date=date,
                                  s=s, rows=rows, level=aqi_level(s[6]))

if __name__ == "__main__":
    app.run(debug=True)