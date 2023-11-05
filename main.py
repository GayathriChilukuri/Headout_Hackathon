from flask import Flask, render_template, request
# import mysql.connector
import os
import pandas as pd
from datetime import datetime, timedelta
import requests

places = pd.read_excel("dataset.xlsx", sheet_name='places')
flights = pd.read_excel("dataset.xlsx", sheet_name='flights')
airports = pd.read_excel("dataset.xlsx", sheet_name='airports')

flights['Departure Date'] = pd.to_datetime(flights['Departure Date'])
flights['Departure Date'] = flights['Departure Date'].dt.strftime('%d-%m-%Y')
flights['Arrival Date'] = pd.to_datetime(flights['Arrival Date'])
flights['Arrival Date'] = flights['Arrival Date'].dt.strftime('%d-%m-%Y')
flights['Departure Time'] = flights['Departure Time'].apply(lambda x: x.strftime('%H:%M'))
flights['Arrival Time'] = flights['Arrival Time'].apply(lambda x: x.strftime('%H:%M'))

city_place = {}
citylist = places["City"].tolist()
citylist = list(set(citylist))


for i in range(0,places.shape[0]):
    if places.iloc[i]['City'] not in city_place.keys():
        city_place[places.iloc[i]['City']] = [places.iloc[i]['Name']]
    elif places.iloc[i]['City'] in city_place.keys() and places.iloc[i]['Name'] not in city_place[places.iloc[i]['City']]:
        city_place[places.iloc[i]['City']].append(places.iloc[i]['Name'])


app = Flask(__name__)
app.secret_key = os.urandom(10)


selected_cities = []
selected_places = []
startdate = ""
enddate = ""
currentloc = ""
arrival_time = ""
departure_time = ""
airport_start = ""
airport_end = ""
airport_start_coord = ""
airport_end_coord = ""

def give_flights(cities, place, date):
    avail_flights=[]
    for i in range(len(flights)):
        if (flights['Departure City'][i] == place) and (flights['Destination City'][i] in cities) and (flights['Departure Date'][i] == date):
            avail_flights.append([place,flights['Destination City'][i],flights['Departure Time'][i],flights['Arrival Time'][i]])
    return avail_flights

def return_flights(cities, place, date):
    avail_flights=[]
    for i in range(len(flights)):
        if (flights['Departure City'][i] in cities) and (flights['Destination City'][i] == place) and (flights['Departure Date'][i] == date):
            avail_flights.append([flights['Departure City'][i], place, flights['Departure Time'][i],flights['Arrival Time'][i]])
    return avail_flights


def tsp(path, graph, visited, cost, min_cost, min_path, source, destination):
    if len(path) == len(graph) and path[-1] == destination:
        if cost < min_cost:
            min_cost = cost
            min_path = path
        return min_path, min_cost

    for node in range(len(graph)):
        if not visited[node]:
            visited[node] = True
            new_path = path + [node]
            new_cost = cost + graph[path[-1]][node]
            min_path, min_cost = tsp(new_path, graph, visited, new_cost, min_cost, min_path, source, destination)
            visited[node] = False
    return min_path, min_cost


def traveling_salesman(graph):
    source = 0
    destination = len(graph) - 1
    min_cost = float("inf")
    min_path = None
    visited = [False] * len(graph)

    visited[source] = True
    path, cost = tsp([source], graph, visited, 0, min_cost, min_path, source, destination)
    visited[source] = False

    travel_times = []
    for i in range(len(path) - 1):
        from_place = path[i]
        to_place = path[i + 1]
        travel_time = graph[from_place][to_place]
        travel_times.append(travel_time)

    return path, travel_times


def convert_to_24_hours(time_str):
    time_obj = datetime.strptime(time_str, '%I:%M %p')
    time_24h = time_obj.strftime('%H:%M')
    return time_24h


def add_hours_to_time(current_time, hours_to_add):
    try:
        input_datetime = datetime.strptime(current_time, "%H:%M")
        time_to_add = timedelta(hours=hours_to_add)
        new_datetime = input_datetime + time_to_add
        new_time = new_datetime.strftime("%H:%M")
        return new_time
    except ValueError:
        return "Invalid time format. Use 'HH:MM' (24-hour clock)."


def calculate_hours_difference(start_date_str, start_time_str, end_date_str, end_time_str):
    start_datetime_str = f"{start_date_str} {start_time_str}"
    end_datetime_str = f"{end_date_str} {end_time_str}"
    format_str = "%d-%m-%Y %H:%M"

    start_datetime = datetime.strptime(start_datetime_str, format_str)
    end_datetime = datetime.strptime(end_datetime_str, format_str)

    time_difference = end_datetime - start_datetime
    hours_difference = time_difference.total_seconds() / 3600
    return hours_difference


def count_days_between_dates(date1, date2):
    date1 = datetime.strptime(date1, "%d-%m-%Y")
    date2 = datetime.strptime(date2, "%d-%m-%Y")
    delta = date2 - date1
    days = delta.days
    return days + 1


def actsandtimes(path, travel_time):
    acts = ["travel"]
    total_time = [round(travel_time[0] / 3600, 2)]
    for i in range(1, len(path) - 1):
        place = selected_places[path[i] - 1]
        row_index = places[places['Name'] == place].index[0]
        acts.append(selected_places[path[i] - 1])
        acts.append("travel")
        total_time.append(int(places['Time Needed to Be Spent'][row_index].split()[0]))
        total_time.append(round(travel_time[i] / 3600, 2))
    return acts, total_time

def durations(intpla):
    locpoints = [airport_start_coord]
    for name in intpla:
        for i in range(len(places)):
            if places.at[i, "Name"] == name:
                locpoints.append(places.at[i, "Coordinates"])
    locpoints.append(airport_end_coord)
    auth = "d54e9ca2-0d9d-417d-8d98-b85cf17901f2"
    p1 = "https://apis.mapmyindia.com/advancedmaps/v1/"+auth+"/distance_matrix/driving/"
    p2 = "?sources="
    p3 = "&destinations="
    for i in range(len(locpoints)):
        if i == len(locpoints)-1:
            p1 = p1+locpoints[i]
            p2 = p2 + str(i)
            p3 = p3 + str(i)
        else:
            p1 = p1+locpoints[i]+";"
            p2 = p2 + str(i) + ";"
            p3 = p3 + str(i) + ";"
    response = requests.get(p1+p2+p3, headers={'Authorization': auth})
    t = response.json()
    print(t)
    dur = t['results']['durations']
    return dur


@app.route('/', methods=['GET', 'POST'])
def home():
    return render_template("home.html")


@app.route('/index', methods=['GET', 'POST'])
def index():
    return render_template("index.html")


@app.route('/plan', methods=['GET', 'POST'])
def plan():
    return render_template("plan.html")




# @app.route('/user_and_flights', methods=['GET', 'POST'])
# def user_and_flights():
#     global selected_cities, startdate, enddate, currentloc
#     currentloc = request.form.get('from')
#     selected_cities = request.form.getlist('selectedcities')
#     startdate = request.form.get('startdate')
#     enddate = request.form.get('enddate')
#     going_flights = give_flights(selected_cities, currentloc, startdate)
#     returning_flights = return_flights(selected_cities, currentloc, enddate)
#     return render_template('user_and_flights.html', goingflights=going_flights, returnflights=returning_flights, citieslist=citylist)

#
# @app.route('/user', methods=['GET', 'POST'])
# def user():
#     return render_template("user.html",citieslist = citylist)
#
# @app.route('/bookflight', methods=['GET', 'POST'])
# def bookflight():
#     global selected_cities, startdate, enddate, currentloc
#     currentloc = request.form.get('from')
#     selected_cities = request.form.getlist('selectedcities')
#     startdate = request.form.get('startdate')
#     enddate = request.form.get('enddate')
#     going_flights = give_flights(selected_cities, currentloc, startdate)
#     returning_flights = return_flights(selected_cities, currentloc, enddate)
#     return render_template('flight.html', goingflights=going_flights, returnflights=returning_flights)
#
#
# @app.route('/selectplaces', methods=['GET', 'POST'])
# def selectplaces():
#     global city_place
#     global arrival_time, departure_time, airport_start, airport_end, airport_start_coord, airport_end_coord
#     selected_flights = request.form.getlist('selectedflights')
#     airport_start = selected_flights[0][1]
#     airport_end = selected_flights[1][0]
#     airport_start_coord = airports[airports['City'] == airport_start]['Coordinates'].iloc[0]
#     airport_end_coord = airports[airports['City'] == airport_end]['Coordinates'].iloc[0]
#     arrival_time = selected_flights[0][3]
#     departure_time = selected_flights[1][2]
#     places_list = []
#     for city in selected_cities:
#         if city in city_place:
#             places_list.extend(city_place[city])
#     return render_template('places.html', placeslist=places_list)


# @app.route('/index')
# def index():
#     return render_template("index.html")




@app.route('/getplan', methods=['GET', 'POST'])
def getplan():
    global selected_places
    global arrival_time, departure_time
    selected_places = request.form.getlist('selectedplaces')

    dur = durations(selected_places)

    path, travel_time = traveling_salesman(dur)
    acts, total_time = actsandtimes(path, travel_time)

    days = count_days_between_dates(startdate, enddate)

    arrival_time = convert_to_24_hours(arrival_time)
    departure_time = convert_to_24_hours(departure_time)
    wehave = calculate_hours_difference(startdate, arrival_time, enddate, departure_time) - (days - 1) * 14

    if wehave < sum(total_time):
        while wehave < sum(total_time):
            print(sum(total_time))
            selected_places.pop()
            selected_places = selected_places
            dur = durations(selected_places)
            path, travel_time = traveling_salesman(dur)
            acts, total_time = actsandtimes(path, travel_time)

    st = '10:00'
    et = '20:00'
    day = 1
    fin_list = []
    if datetime.strptime(st, "%H:%M") < datetime.strptime(at, "%H:%M"):
        st = arrival_time
    for i in range(len(total_time)):
        aftertime = add_hours_to_time(st, total_time[i])
        fin_list.append([day, st, aftertime, acts[i]])
        st = aftertime
        if datetime.strptime('10:00', "%H:%M") > datetime.strptime(aftertime, "%H:%M") or datetime.strptime(aftertime,"%H:%M") > datetime.strptime(et, "%H:%M"):
            day = day + 1
            st = "10:00"

    return render_template("plan.html", plan=fin_list)


if __name__ == '__main__':
    app.run()