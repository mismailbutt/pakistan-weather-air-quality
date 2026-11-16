# Pakistan Weather and Air Quality: ETL + EDA Pipeline

If you want to know the weather or air quality of a Pakistani city on a particular day, it is not easy to find. The data is spread across different places and is often messy. Our project makes this simple: you pick a city and a date, and you see the weather and air quality for that day.

## Dataset
We use the Open-Meteo API. We picked it because it is free, needs no API key, and gives a lot of hourly data. We collect data for five cities (Lahore, Karachi, Islamabad, Peshawar and Quetta) from January 2024 to December 2025. The same data can be reused in our other projects.

## Pipeline
- **Extract:** pull weather and air quality data from the API (`etl.py`).
- **Transform:** check every row with Pydantic and clean it with pandas (`etl.py`).
- **Load:** save the data in a SQLite database, `weather.db` (`etl.py`). We chose SQLite because it is simple, needs no server, and is easy to share with the team.

## EDA (`eda.ipynb`)
Missing values and outliers, temperature and rain over time, comparison of the cities, and the relation between weather and air quality. All shown with charts inside the notebook.

## Web app (`app.py`)
A simple Flask page where the user selects a city and a date and sees the weather and air quality for that day.

## How to run
pip install requests pandas pydantic matplotlib seaborn flask jupyter
python etl.py
jupyter notebook eda.ipynb
python app.py
Live link: https://pakistan-weather-air-quality.vercel.app
