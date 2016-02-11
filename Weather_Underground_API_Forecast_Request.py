
# coding: utf-8

# # Weather Underground API - Forecast Request
# 
# I developed this code based on a tutorial located at: http://www.pythonforbeginners.com/scraping/scraping-wunderground
# 
# Weather Underground API data features can be explored at: http://www.wunderground.com/weather/api/d/docs?d=data/index
# 
# I generated a Weather Underground API key using my personal email account. My account is limited to something like 500 daily calls to the API and some hourly value that is not of concern. Calling each hour of the day in eight homes will lead to 8*24 = 192 daily calls.
# 
# I used the online JSON editor (http://jsoneditoronline.org/) to assist in understanding JSON formatted responses from Weather Underground API. Simply take the API call URL (in requests.get() calls) and paste into the JSON editor. This helps in constructing the calls to the JSON objects (e.g.,  data['hourly_forecast']['hour']['FCTTIME']['hour_padded']).
# 
# ##Description of codes
# 
# Packages are imported, custom fucntions are defined, model coefficients are initialized, API calls are made for 3-day hourly forecasts, infiltration is estimated for forecast values, forecast array is written to file for use in cases where current conditions cannot be accessed.
# 
# * Forecast portion should be executed once every 4, 8 or 12 hours.
# * Current conditions portion will be executed once per hour.
# * If current conditions calculations fail for any reason, then the forecast data table should be opened, and values should be selected based on the matching date/time index.
# * Use hourly infiltration estimate in dose/exposure and RIVEC calculations.
# 
# It's worth noting that I was not able to export this .pynb file to .py script using the option under File>Download As>Python. Had to use the following at the command line (https://ipython.org/ipython-doc/1/interactive/nbconvert.html):
# 
# ipython nbconvert --to python Weather_Underground_API_infiltration.ipynb
# 

# In[2]:

import requests
import numpy as np
import datetime
import os
import sys
import time


# In[5]:

#Date time stamp function, WX_dates()
#Uses the hour index from the Weather Underground forecast to pull the hour, minute, day and year values. 
#Concatenates into legible date/time string. 

def WX_dates(hour):
    hours = str(data['hourly_forecast'][hour]['FCTTIME']['hour_padded'])
    minutes = str(data['hourly_forecast'][hour]['FCTTIME']['min'])
    days = str(data['hourly_forecast'][hour]['FCTTIME']['mday_padded'])
    months = str(data['hourly_forecast'][hour]['FCTTIME']['mon_padded'])
    years = str(data['hourly_forecast'][hour]['FCTTIME']['year'])
    return "%s/%s/%s %s:%s" %(years, months, days, hours, minutes) 

#Stack airflow rate, stack()
#c = house flow coeff, Cs = stack coeff, T (c), n

def stack(c, Cs, T, n=0.67):
    return c*Cs*T**n

#Wind airflow rate, wind()
#c = house flow coefficient, Cw = wind coefficient (varies with # stories and presence of flue), s = Shelter factor, 
#G = Wind Speed multiplier (by # stories), U = wind velocity (m/s), n = pressure exponent

def wind(c,Cw,s,G,U,n=0.67):
    return c*Cw*(s*G*U)**(2*n)

#Superposition calculation, superposition()
#stack = stack airflow, wind = wind airflow, mech_unbal = unbalanced mechanical airflows (defaults to 0), 
#mech_bal = balanced mechanical airflows (defaults to 0).

def superposition(stack, wind, mech_unbal = 0, mech_bal = 0):
    return mech_bal + (stack**2 + wind**2 + mech_unbal**2)**0.5


# In[6]:

#Set of infiltration model coefficients. Coef_array is 3x5. From 2013 ASHRAE Handbook of Fundamentals, Chapter 16, 
#pages 24-25, Tables 7, 8 and 9. 

#Or just specify them for each house. Use config file?

# assumes 3 ACH50 home, n=0.67, house volume of 250 m3. 1-story, with flue, crawlspace.

c = 0.015193229 
Cs = 0.069
Cw = 0.128
G = 0.48
s = 0.70
House_temp = 20

API_key = '74c40f9c6f3578a6'

#File path for reading/writing files
path = '/Users/brennanless/GoogleDrive/BPA_SmartVentilation/Weather_Underground_API'

#sets working directory to path string
os.chdir(path) 


# In[7]:

for attempt in range(10):

    if attempt < 9:

        try:
            #Request json data for the hourly 3-day forecast.
            r = requests.get("http://api.wunderground.com/api/%s/hourly/q/CA/San_Leandro.json" % API_key)
            #r = requests.get("fartsingspop")
            data = r.json()
            break

        except: 
            print "An error occurred connecting to the Weather Underground host. Will try again in a bit."
            time.sleep(60)
            
    else:
        #Maybe send an email if this occurrs...
        #Then close the script. We will just rely on the existing forecast data on file. This gives a 36-hour buffer.
        print "No connection to the Weather Underground server was available for 10 minutes. Will try again at next scheduled interval."
        sys.exit()


# In[8]:

#Import Date/time stamps and hourly forecasts for outdoor tempeature and windspeed. 
#Convert wind speed from km/h to m/s using (1000/3600), m/km, sec/hr.
#Estimate infiltration airflow using superposition function, with stack and wind estimates. 

#Create empty lists
wind_speeds = []
temps = []
dates = []
infiltration = []

#for-loop populates lists using .append() method. 
for hour in range(0,36):
    wind_speeds.append((float(1000)/3600)*int(data['hourly_forecast'][hour]['wspd']['metric'])) #converted from km/h to m/s
    temps.append(int(data['hourly_forecast'][hour]['temp']['metric']))
    dates.append(WX_dates(hour))
    infiltration.append(superposition(stack(c, Cs, (House_temp - temps[hour])), wind(c, Cw, s, G, wind_speeds[hour])))

#Convert lists to numpy arrays    
ws_np = np.array(wind_speeds)
temps_np = np.array(temps)
dates_np = np.array(dates)
infiltration_np = np.array(infiltration)

#Join integer values for temp and wind speed into one array.
vals = np.column_stack((dates_np, temps_np, ws_np, infiltration_np))

#Save forecast valus to local file system.
np.savetxt('Forecast_Values.txt', vals , delimiter = ',', fmt = '%s')

