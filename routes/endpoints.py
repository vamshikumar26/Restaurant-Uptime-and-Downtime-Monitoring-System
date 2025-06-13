from fastapi import APIRouter, BackgroundTasks
from schema.database import db
import pandas as pd
from datetime import timedelta, datetime
from pytz import timezone
import os
import uuid
import csv
from concurrent.futures import ThreadPoolExecutor

#creating instance for APIrouter
router = APIRouter()

#creating file directory for storing the generated reports
REPORT_DIR = 'reports'
os.makedirs(REPORT_DIR, exist_ok=True)


#Converting the UTC datetime string to local datetime
def convert_to_local(utc_dt_str, timezone_str):
    if isinstance(utc_dt_str, datetime):
        utc_dt = utc_dt_str
    else:
        if utc_dt_str.endswith(" UTC"):
            utc_dt_str = utc_dt_str.replace(" UTC", "+00:00")
        elif utc_dt_str.endswith("Z"):
            utc_dt_str = utc_dt_str.replace("Z", "+00:00")
        utc_dt = datetime.fromisoformat(utc_dt_str)
    tz = timezone(timezone_str)
    return utc_dt.astimezone(tz)


#Checks whether a given local datetime fall in restaurant's menu hours
def is_within_menu_hours(dt_local, menuhrs, is24by7):
    if is24by7:
        return True
    day = dt_local.weekday()
    for entry in menuhrs:
        if entry['day'] == day:
            #Parse the start and end times into time objects
            start = datetime.strptime(entry['start_time_local'], '%H:%M:%S').time()
            end = datetime.strptime(entry['end_time_local'], '%H:%M:%S').time()
            if start <= dt_local.time() <= end:
                return True
    return False

def interpolate_and_calculate(logs, menuhours_doc, timezone_str, window_start_local, current_time_local, is24by7):
    #sorting logs based on timestamp
    logs = sorted(logs, key=lambda x: x['timestamp_utc'])
    
    #if there are no logs then return 0 minutes for uptime/downtime
    if not logs:
        return 0.0, 0.0

    #converting timestamps to local timezone
    logs_local = [
        {
            'timestamp': convert_to_local(log['timestamp_utc'], timezone_str),
            'status': log['status']
        } for log in logs
    ]

    #Interpolation logic: If first log starts after window start then assume the store has the same status from start of the window
    if logs_local[0]['timestamp'] > window_start_local:
        logs_local.insert(0, {
            'timestamp': window_start_local,
            'status': logs_local[0]['status']
        })
    #If last log ends before the window end,extend it to current time
    if logs_local[-1]['timestamp'] < current_time_local:
        logs_local.append({
            'timestamp': current_time_local,
            'status': logs_local[-1]['status']
        })
    #we are initializing counters for uptime/Downtime
    uptime = timedelta()
    downtime = timedelta()
    
    #Go through the pairs of logs for calculating duration in each status
    for i in range(len(logs_local) - 1):
        start = max(logs_local[i]['timestamp'], window_start_local)
        end = min(logs_local[i + 1]['timestamp'], current_time_local)
        if start >= end:
            continue

        curr = start
        #Move minute-b-minute to check status within menu_hours
        while curr < end:
            if is_within_menu_hours(curr, menuhours_doc, is24by7):
                next_min = min(end, curr + timedelta(minutes=1))
                duration = next_min - curr
                if logs_local[i]['status'] == 'active':
                    uptime += duration
                else:
                    downtime += duration
            curr += timedelta(minutes=1)
    #return rounded uptime/downtime in minutes
    return round(uptime.total_seconds() / 60, 2), round(downtime.total_seconds() / 60, 2)

#Loading csv files
menu_hours_csv = pd.read_csv(r'#path to your input menu_hours csv')
store_status_csv = pd.read_csv(r'#path to your input store_status.csv')
timezone_csv = pd.read_csv(r'#path to your input timezone.csv')

#creating collections for csv files
menu_hours_collection = db["menu_hours_logs"]
status_collection = db['status_logs']
timezone_collection = db["time_zone_logs"]
report_collection = db["report_logs"]

#loading the csv data into collections
if menu_hours_collection.estimated_document_count() == 0:
    menu_hours_collection.insert_many(menu_hours_csv.to_dict('records'))
if status_collection.estimated_document_count() == 0:
    status_collection.insert_many(store_status_csv.to_dict('records'))
if timezone_collection.estimated_document_count() == 0:
    timezone_collection.insert_many(timezone_csv.to_dict('records'))

#creating index for collections for faster retireval
status_collection.create_index([("store_id", 1), ("timestamp_utc", 1)])
timezone_collection.create_index("store_id")
menu_hours_collection.create_index("store_id")

def process_store(store_id, current_time):
    #getting timezone for store from MongoDB
    timezone_doc = timezone_collection.find_one({'store_id': store_id})
    timezone_str = timezone_doc['timezone_str'] if timezone_doc else 'America/Chicago'
    
    #Get the menu hours (i.e., business hours) for this store
    menuhours_doc_cursor = menu_hours_collection.find({'store_id': store_id})
    menu_hours = [
        {
            'day': entry['dayOfWeek'],
            'start_time_local': entry['start_time_local'],
            'end_time_local': entry['end_time_local']
        } for entry in menuhours_doc_cursor
    ]
    #If no menu hours found, assume the store is open 24/7
    is24by7 = False if menu_hours else True
    #Define the time windows for report
    time_windows = {
        "last_hour": current_time - timedelta(hours=1),
        "last_day": current_time - timedelta(days=1),
        "last_week": current_time - timedelta(weeks=1)
    }
    #Result dict for this store
    store_data = {'store_id': store_id}
    #For each window (last hour/day/week), compute uptime and downtime
    for label, start_time in time_windows.items():
        logs = list(status_collection.find({"store_id": store_id,'timestamp_utc': {'$gte': start_time.isoformat(), '$lte': current_time.isoformat()}}))
        
        # Convert both start and end of window to the store's local time
        window_start_local = convert_to_local(start_time.isoformat(), timezone_str)
        current_time_local = convert_to_local(current_time.isoformat(), timezone_str)
        
        # Interpolate and calculate uptime/downtime within business hours
        up, down = interpolate_and_calculate(logs, menu_hours, timezone_str, window_start_local, current_time_local, is24by7)
        
        # Save results in minutes (for hour) or in hours (for day/week)
        if 'hour' in label:
            store_data[f'uptime_{label}'] = up
            store_data[f'downtime_{label}'] = down
        else:
            store_data[f'uptime_{label}'] = round(up / 60, 2)
            store_data[f'downtime_{label}'] = round(down / 60, 2)
    return store_data

def run_report_in_background(report_id: str):
    try:
        #retreiving the latest timestamp from any log entry
        latest_doc = status_collection.find_one(sort=[('timestamp_utc', -1)])
        timestamp_str = latest_doc.get('timestamp_utc')
        if not timestamp_str:
            raise ValueError("Missing 'timestamp_utc' in latest status log")
        
        #converting timestamp string to datetime object
        if isinstance(timestamp_str, datetime):
            current_time = timestamp_str
        elif isinstance(timestamp_str, str):
            #normalizing to ISO format
            if timestamp_str.endswith(' UTC'):
                timestamp_str = timestamp_str.replace(' UTC', '+00:00')
            elif timestamp_str.endswith('Z'):
                timestamp_str = timestamp_str.replace('Z', '+00:00')
            current_time = datetime.fromisoformat(timestamp_str)
        else:
            raise ValueError(f"Unrecognized timestamp format: {timestamp_str}")
        
        #get all distinct store_ids
        store_ids = status_collection.distinct('store_id')
        
        #Process each store's report data concurrently using threads
        with ThreadPoolExecutor(max_workers=10) as executor:
            rows = list(executor.map(lambda store_id: process_store(store_id, current_time), store_ids))
        #write the results rows to a CSV file
        path = os.path.join(REPORT_DIR, f'{report_id}.csv')
        fieldnames = [
            'store_id',
            'uptime_last_hour',
            'uptime_last_day',
            'uptime_last_week',
            'downtime_last_hour',
            'downtime_last_day',
            'downtime_last_week'
        ]
        with open(path, 'w', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
            
        #updating report as complete in MongoDB collection
        report_collection.update_one(
            {"report_id": report_id},
            {"$set": {"status": "complete", "path": path}},
            upsert=True
        )
    except Exception as e:
        report_collection.update_one(
            {"report_id": report_id},
            {"$set": {"status": "failed", "error": str(e)}}
        )

#Trigger-Report endpoint
@router.post('/trigger_report')
def trigger_report(background_tasks: BackgroundTasks):
    #generating random id's for reports
    report_id = str(uuid.uuid4())
    report_collection.insert_one({
        "report_id": report_id,
        "status": "running",
        "path": None
    })
    background_tasks.add_task(run_report_in_background, report_id)
    return {"report_id": report_id}

#Get-report status 
@router.get('/get_report')
def get_report(report_id: str):
    report = report_collection.find_one({'report_id': report_id})
    if not report:
        return {"status": "not_found"}
    if report['status'] == 'complete':
        return {'status': "complete", 'report_url': report['path']}
    elif report['status'] == 'running':
        return {'status': "running"}
    elif report['status'] == 'failed':
        return {'status': "failed", 'error': report.get('error', 'Unknown error')}
    else:
        return {'status': report['status']}
