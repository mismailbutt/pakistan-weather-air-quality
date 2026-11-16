# Pakistan Weather and Air Quality: ETL + EDA Pipeline

If you want to know the weather or air quality of a Pakistani city on a particular day, it is not easy to find. The data is spread across different places and is often messy. Our project makes this simple: you pick a city and a date, and you see the weather and air quality for that day.

## Dataset
We use the Open-Meteo API. We picked it because it is free, needs no API key, and gives a lot of hourly data. We collect data for five cities (Lahore, Karachi, Islamabad, Peshawar and Quetta) from January 2024 to December 2025. The same data can be reused in our other projects.

## Pipeline
- **Extract:** pull weather and air quality data from the API (`etl.py`).
- **Transform:** check every row with Pydantic and clean it with pandas (`etl.py`).
- **Load:** save the data in a SQLite database, `weather.db` (`etl.py`). We chose SQLite because it is simple, needs no server, and is easy to share with the team.

## Website and exploratory data analysis
Choose a city and date for daily and hourly readings. The website also displays monthly temperature and rainfall trends, a five-city AQI comparison, post-cleaning missing-value counts, PM2.5 outliers and weather–pollution correlations.

## Run the dashboard (Python 3.10+)
```sh
pip install -r requirements.txt
python app.py
```
The included weather.db is ready to use. To rebuild it from Open-Meteo:
```sh
pip install requests pandas "pydantic>=2,<3"
python etl.py
```
Live website: https://pakistan-weather-air-quality.vercel.app/
