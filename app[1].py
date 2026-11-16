import os
from statistics import correlation, quantiles, StatisticsError
import sqlite3
from flask import Flask, request, render_template_string

app = Flask(__name__)
DB = os.path.join(os.path.dirname(__file__), "weather.db")
CITIES = ["Lahore", "Karachi", "Islamabad", "Peshawar", "Quetta"]

PAGE = """
<!doctype html>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Pakistan Weather &amp; Air Quality</title>
<style>
body {font: 16px/1.5 system-ui,sans-serif; color:#183642; max-width:960px; margin:auto; padding:20px}
figure {margin:16px 0; padding:14px; border:1px solid #ccd8dc; border-radius:8px}
figure svg {display:block; width:100%; height:auto} figcaption {font-weight:600}
table {border-collapse:collapse} th,td {padding:5px 10px}
</style>
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

  <h2>Monthly trends in {{ city }} · 2024–2025</h2>
  {% for chart in charts %}
  <figure><figcaption>{{ chart.title }}</figcaption>
    <svg viewBox="0 0 760 180" role="img" aria-label="{{ chart.title }} for {{ city }}, January 2024 through December 2025">
      {% for y, label in chart.ticks %}
      <line x1="54" x2="738" y1="{{ y }}" y2="{{ y }}" stroke="#d8e2e4"/>
      <text x="48" y="{{ y+4 }}" text-anchor="end" font-size="12">{{ label }}</text>
      {% endfor %}
      {% if chart.line %}<polyline points="{{ chart.line }}" fill="none" stroke="#ad4d19" stroke-width="3"/>{% endif %}
      {% for x,y,month,value in chart.points %}
        {% if chart.line %}<circle cx="{{ x }}" cy="{{ y }}" r="4" fill="#ad4d19"><title>{{ month }}: {{ value }} °C</title></circle>
        {% else %}<rect x="{{ x-9 }}" y="{{ y }}" width="18" height="{{ 144-y }}" fill="#217699"><title>{{ month }}: {{ value }} mm</title></rect>{% endif %}
        {% if loop.first or loop.index0 in [6,12,18,23] %}<text x="{{ x }}" y="166" text-anchor="middle" font-size="12">{{ month }}</text>{% endif %}
      {% endfor %}
    </svg>
  </figure>
  {% endfor %}
  <h3>Air quality across five cities · 2024–2025</h3>
  <table><tr><th>City</th><th>Mean hourly AQI</th></tr>
  {% for name, avg in comparisons %}<tr><td>{{ name }}</td><td><meter min="0" max="{{ comparisons[0][1] }}" value="{{ avg }}"></meter> {{ avg }}</td></tr>{% endfor %}</table>
  <h3>Data checks for {{ city }} · 2024–2025</h3>
  <p>{{ missing }} missing measurement values across {{ count }} cleaned hourly records (7 measurements per record).</p>
  <p>{{ outliers }} hourly PM2.5 readings fall outside the 1.5 × IQR limits. An extreme reading can represent a real pollution event.</p>
  <h3>How does weather relate to PM2.5 in {{ city }}?</h3>
  <p>Pearson correlation across hourly records. Positive values mean the measurements tend to rise together. Values close to zero indicate little linear association.</p>
  <table><tr><th>Weather measurement</th><th>Correlation with PM2.5</th></tr>
  {% for label, value in correlations %}<tr><td>{{ label }}</td><td>{{ value }}</td></tr>{% endfor %}</table>
  <h3>Hourly data for {{ date }}</h3>
  <table border="1" cellpadding="5">
    <tr><th>Time</th><th>Temp (°C)</th><th>Rain (mm)</th><th>PM2.5</th><th>AQI</th></tr>
    {% for r in rows %}<tr>{% for x in r %}<td>{{ x }}</td>{% endfor %}</tr>{% endfor %}
  </table>
{% else %}
  <p>No data for this date.</p>
{% endif %}
"""

def aqi_level(a):
    if a is None:
        return "unknown"
    if a <= 50:
        return "Good"
    if a <= 100:
        return "Moderate"
    if a <= 150:
        return "Unhealthy for sensitive groups"
    if a <= 200:
        return "Unhealthy"
    if a <= 300:
        return "Very unhealthy"
    return "Hazardous"

def monthly_chart(rows, column, title, line=False):
    values = [row[column] for row in rows if row[column] is not None]
    low = min([0] + values)
    high = max([1] + values)
    points = []
    for index, row in enumerate(rows):
        value = row[column]
        if value is not None:
            x = 62 + index * 666 / max(1, len(rows) - 1)
            y = 144 - 128 * (value - low) / (high - low)
            points.append((x, y, row[0], value))
    ticks = [(144 - 32*i, round(low + (high-low)*i/4, 1)) for i in range(5)]
    return dict(title=title, ticks=ticks, points=points,
                line=" ".join(f"{x},{y}" for x, y, _, _ in points) if line else "")


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
    monthly = conn.execute("""
        SELECT substr(date, 1, 7), ROUND(AVG(temperature), 1), ROUND(SUM(rain), 1)
        FROM readings WHERE city = ? GROUP BY substr(date, 1, 7) ORDER BY 1
    """, (city,)).fetchall()
    charts = [monthly_chart(monthly, 1, "Average temperature (°C)", line=True),
              monthly_chart(monthly, 2, "Total rainfall (mm)")]
    comparisons = conn.execute("""
        SELECT city, ROUND(AVG(aqi),1) FROM readings GROUP BY city ORDER BY AVG(aqi) DESC
    """).fetchall()
    samples = conn.execute("""
        SELECT temperature,humidity,rain,wind,pm25,pm10,aqi FROM readings WHERE city=?
    """, (city,)).fetchall()
    conn.close()
    missing = sum(row.count(None) for row in samples)
    pm = [row[4] for row in samples if row[4] is not None]
    outliers = 0
    if len(pm) >= 2:
        q1, _, q3 = quantiles(pm, method="inclusive")
        spread = 1.5 * (q3 - q1)
        outliers = sum(v < q1 - spread or v > q3 + spread for v in pm)
    correlations = []
    for idx, label in enumerate(["Temperature", "Humidity", "Rainfall", "Wind speed"]):
        pairs = [(r[idx], r[4]) for r in samples if r[idx] is not None and r[4] is not None]
        try:
            value = round(correlation(*zip(*pairs)), 2) if len(pairs) >= 2 else "Unavailable"
        except StatisticsError:
            value = "Unavailable"
        correlations.append((label, value))

    return render_template_string(PAGE, cities=CITIES, city=city, date=date,
                                  s=s, rows=rows, charts=charts, comparisons=comparisons, missing=missing,
                                  count=len(samples), outliers=outliers, correlations=correlations, level=aqi_level(s[6]))

if __name__ == "__main__":
    app.run(debug=True)
