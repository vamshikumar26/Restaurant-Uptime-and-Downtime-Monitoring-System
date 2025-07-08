# Restaurant Uptime/Downtime Monitoring System

A backend system built using **FastAPI** to monitor and analyze restaurant availability. The system ingests polling data (`store_status`, `menu_hours`, and `timezones`) and generates **uptime/downtime reports** for the last hour, day, and week.

### Features

-  **Uptime/Downtime Analysis** (Hourly, Daily, Weekly)
-  **CSV Report Generation** per store
-  **Asynchronous Processing** for efficient report handling
-  **Summary Export** in downloadable format
-  Timezone-aware calculations

---

## Tech Stack

- **FastAPI** - Web framework for building APIs
- **MongoDB** - For storing polling and metadata
- **Python 3.9+**
- **Asyncio/Aiofiles** - For non-blocking I/O and background tasks

---
## Project Structure
restaurant-uptime-monitor/

├── reports/ # Logic to generate and store report files (CSV)

├── routes/ # FastAPI API routes

├── schema/ # Pydantic models and request/response schemas

├── config.py # MongoDB connection settings and configs

├── main.py # FastAPI app entry point

├── requirements.txt # Python dependencies

├── README.md # Project documentation


## Requirements

- Python 3.9 or higher
- MongoDB (local instance or cloud via MongoDB Atlas)
- Install dependencies from `requirements.txt`
pip install -r requirements.txt


## How to Run

Clone the Repository
git clone https://github.com/yourusername/restaurant-uptime-tracker.git
cd restaurant-uptime-tracker

## Run the FastAPI Server 

uvicorn main:app --reload


### Access the API Docs
Swagger UI: http://localhost:8000/docs

Redoc: http://localhost:8000/redoc

### Sample Reports
The API allows generating and downloading uptime/downtime reports:

Last 1 hour
Last 1 day
Last 7 days
CSV downloadable summaries

Async Report Generation
Trigger reports using a background task and retrieve them later

Hourly: Performance in the last 60 minutes
Daily: Availability for the past 24 hours
Weekly: Uptime across the last 7 days
