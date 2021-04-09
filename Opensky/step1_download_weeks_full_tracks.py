##############################################################################

#airport_icao = "ESSA"
airport_icao = "ESGG"
#airport_icao = "EIDW" # Dublin
#airport_icao = "LOWW" # Vienna

#airport_icao = "ESNQ" # Kiruna, no flights
#airport_icao = "ESNN" #Sundsvall, no flights
#airport_icao = "ESNO" #Ovik, no flights
#airport_icao = "ESNU" #Umeo
#airport_icao = "ESMS" #Malmo


arrival = True

year = '2021'

#months = ['01', '02', '03', '04', '05', '06', '07', '08', '09', '10', '11', '12']
months = ['01', '02', '03']


##############################################################################

from datetime import datetime
from datetime import timezone
import calendar

import os

DATA_DIR = os.path.join("data", airport_icao)
DATA_DIR = os.path.join(DATA_DIR, year)
OUTPUT_DIR = os.path.join(DATA_DIR, "osn_" + airport_icao + "_tracks_" + year)

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

import requests
import math
import pandas as pd


log_filename = "dropped_flights_" + year + '.txt'
full_log_filename = os.path.join(OUTPUT_DIR, log_filename)


from opensky_credentials import USERNAME, PASSWORD

class LiveDataRetriever:
    API_URL = 'https://opensky-network.org/api'

    AUTH_DATA = (USERNAME, PASSWORD)

    def get_list_of_arriving_aircraft(self, timestamp_begin, timestamp_end):

        arriving_flights_url = self.API_URL + '/flights/arrival'

        request_params = {
            'airport': airport_icao,
            'begin': timestamp_begin,
            'end': timestamp_end
        }
        
        while True:
            try:
                print("request")
                res = requests.get(arriving_flights_url, params=request_params, auth=self.AUTH_DATA).json()
                break
            except Exception as str_error:
                print("Exception: ")
                print(str_error)
                pass

        print(res)
        return res

    def get_list_of_departure_aircraft(self, timestamp_begin, timestamp_end):

        departure_flights_url = self.API_URL + '/flights/departure'

        request_params = {
            'airport': airport_icao,
            'begin': timestamp_begin,
            'end': timestamp_end
        }
        
        while True:
            try:
                res = requests.get(departure_flights_url, params=request_params, auth=self.AUTH_DATA).json()
                break
            except Exception as str_error:
                print("Exception: ")
                print(str_error)
                pass

        return res

    def get_track_data(self, flight_icao24, flight_time):
        track_data_url = self.API_URL + '/tracks/all'

        request_params = {
            'time': flight_time,
            'icao24': flight_icao24
        }

        return requests.get(track_data_url, params=request_params, auth=self.AUTH_DATA).json()


# API does not allow longer than 7 days time periods
def get_tracks_data(data_retriever, flights, date_time_begin, date_time_end, month, week):
    
    dropped_flights_file = open(full_log_filename, 'a+')
    
    number_of_flights = len(flights)

    new_data = []

    dropped_flights_icao = 0
    dropped_flights_first_seen = 0
    dropped_flights_last_seen = 0
    dropped_flights_callsign = 0

    for i in range(number_of_flights):
        print(airport_icao, year, month, week, number_of_flights, i)

        if flights[i] == 'Start after end time or more than seven days of data requested': #ESSA 22.10.2018-29.10.2018 -> 28.10 to 5th week
            print(flights[i])
            continue

        if flights[i]['icao24'] is None:
            dropped_flights_icao = dropped_flights_icao + 1
            continue

        if flights[i]['firstSeen'] is None:
            dropped_flights_first_seen = dropped_flights_first_seen + 1
            continue

        if flights[i]['lastSeen'] is None:
            dropped_flights_last_seen = dropped_flights_last_seen + 1
            continue
 
        while True:
            try:
                #d: icao24, startTime, endTime, callsign, path (time, latitude, longitude, baro_altitude, true_track, on_ground)
                d = data_retriever.get_track_data(flights[i]['icao24'], math.ceil((flights[i]['firstSeen']+flights[i]['lastSeen'])/2))
                break
            except Exception as str_error:
                print("Exception: ")
                print(str_error)
                pass
            
        sequence = 0
        
        if (flights[i]['callsign'] is None) and (d['callsign'] is None):
            dropped_flights_callsign = dropped_flights_callsign + 1
            continue

        for element in d['path']:
            new_d = {}

            new_d['origin'] = flights[i]['estDepartureAirport']

            new_d['sequence'] = sequence
            sequence = sequence + 1

            end_timestamp = d['endTime']
            end_datetime = datetime.utcfromtimestamp(end_timestamp)
            new_d['endDate'] = end_datetime.strftime('%y%m%d')

            el_timestamp = element[0]    #time
            el_datetime = datetime.utcfromtimestamp(el_timestamp)

            new_d['date'] = el_datetime.strftime('%y%m%d')
            new_d['time'] = el_datetime.strftime('%H%M%S')
            new_d['timestamp'] = el_timestamp
            new_d['lat'] = element[1]
            new_d['lon'] = element[2]
            new_d['baroAltitude'] = element[3]


            new_d['callsign'] = d['callsign'].strip() if d['callsign'] else flights[i]['callsign'].strip()
            new_d['icao24'] = d['icao24'].strip() if d['icao24'] else flights[i]['icao24'].strip()

            new_data.append(new_d)

    print(month, week, file = dropped_flights_file)
    print("dropped_flights_icao", file = dropped_flights_file)
    print(dropped_flights_icao, file = dropped_flights_file)
    print("dropped_flights_first_seen", file = dropped_flights_file)
    print(dropped_flights_first_seen, file = dropped_flights_file)
    print("dropped_flights_last_seen", file = dropped_flights_file)
    print(dropped_flights_last_seen, file = dropped_flights_file)
    print("dropped_flights_callsign", file = dropped_flights_file)
    print(dropped_flights_callsign, file = dropped_flights_file)
    
    dropped_flights_file.close()

    data_df = pd.DataFrame(new_data, columns = ['sequence', 'origin', 'endDate', 'callsign', 'icao24', 'date','time', 'timestamp', 'lat', 'lon', 'baroAltitude'])

    return data_df


def assign_flight_ids(month, week, tracks_df, output_filename):

    tracks_df['flight_id'] = tracks_df.apply(lambda row: str(row['endDate']) + str(row['callsign']), axis = 1) 
    
    tracks_df.set_index(['flight_id', 'sequence'], inplace=True)
    
    tracks_df = tracks_df.groupby(level=tracks_df.index.names)
    
    tracks_df = tracks_df.first()
    
    tracks_df.to_csv(output_filename, sep=' ', encoding='utf-8', float_format='%.6f', index=True, header=None)


def download_tracks_week(month, week, date_time_begin, date_time_end):
    
    timestamp_begin = int(date_time_begin.timestamp())   #float -> int
    timestamp_end = int(date_time_end.timestamp())

    data_retriever = LiveDataRetriever()
    
    filename = 'osn_' + airport_icao + '_tracks_' + year + '_' + month + '_week' + str(week) + '.csv'
    
    if arrival:
        flights = data_retriever.get_list_of_arriving_aircraft(timestamp_begin, timestamp_end)
    else:
        flights = data_retriever.get_list_of_departure_aircraft(timestamp_begin, timestamp_end)
        filename = 'departure_' + filename

    if flights:
        opensky_df = get_tracks_data(data_retriever, flights, date_time_begin, date_time_end, month, week)

        opensky_df = opensky_df.astype({"time": str, "date": str})
        opensky_df.reset_index(drop=True, inplace=True)
    
        output_filename = os.path.join(OUTPUT_DIR, filename)
        assign_flight_ids(month, week, opensky_df, output_filename)
    else:
        print("No flights")

import time
start_time = time.time()

from multiprocessing import Process

for month in months:
    
    procs = []
    
    for week in range(0,4):

        print(week)
    
        DATE_TIME_BEGIN = datetime(int(year), int(month), week * 7 + 1, 0, 0, 0, 0, timezone.utc)
        if month == '02' and week == 3 and not calendar.isleap(int(year)):
            DATE_TIME_END = datetime(int(year), 3, 1, 0, 0, 0, 0)
        else:
            DATE_TIME_END = datetime(int(year), int(month), (week + 1) * 7 + 1, 0, 0, 0, 0, timezone.utc)
            
        proc = Process(target=download_tracks_week, args=(month, week + 1, DATE_TIME_BEGIN, DATE_TIME_END,))
        procs.append(proc)
        proc.start()

    if month == '02' and not calendar.isleap(int(year)):
        continue
    elif month == '12':
        DATE_TIME_BEGIN = datetime(int(year), 12, 29, 0, 0, 0, 0, timezone.utc)
        DATE_TIME_END = datetime(int(year) + 1, 1, 1, 0, 0, 0, 0, timezone.utc)
    else:
        DATE_TIME_BEGIN = datetime(int(year), int(month), 29, 0, 0, 0, 0, timezone.utc)
        DATE_TIME_END = datetime(int(year), int(month) + 1, 1, 0, 0, 0, 0, timezone.utc)
    
    proc = Process(target=download_tracks_week, args=(month, 5, DATE_TIME_BEGIN, DATE_TIME_END,))
    procs.append(proc)
    proc.start()
    
    # complete the processes
    for proc in procs:
        proc.join()

print((time.time()-start_time)/60)
