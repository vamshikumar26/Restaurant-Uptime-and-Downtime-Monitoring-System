# monitoring_uptime-downtime_of_restaurant

This is FastAPI-based backend system ingests restaturant polling data contains store_status, menu_hours and timezones

- Uptime/Downtime reporting for last hour, day, week
- CSV output with per-store summary
- Asynchronous report generation and retrieval


How to Run

Requirements 

- Python 3.9+
- MongoDB (local or cloud)
- 'requirements.txt' packages

Installation

git clone https://github.com/vamshikumar26/vamshi_13_06_2025.git

cd monitoring_uptime-downtime_of_restaurant

pip install -r requirements.txt

uvicorn main:app --reload

Ideas for Improvement
- Add JWT auth to secure endpoints
- UI to upload CSV and monitor report generation live

Sample Output

A sample report CSV has been uploaded [here on Google Drive](https://drive.google.com/file/d/1_VG8MkasFc3qsCAkyx11qQwF1YOyq2eK/view?usp=drive_link](https://drive.google.com/file/d/1_VG8MkasFc3qsCAkyx11qQwF1YOyq2eK/view?usp=sharing)

