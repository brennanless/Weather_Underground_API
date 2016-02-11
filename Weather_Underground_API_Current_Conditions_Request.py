
# coding: utf-8

# # Weather Underground API - Current Conditions Request
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
# Packages are imported, custom fucntions are defined, model coefficients are initialized, API call is made for current weather conditions, infiltration is estimated for current conditions, or forecast array is read from file and the nearest hourly forecast value is used in place of current infiltration. 
# 
# * Forecast portion should be executed once every 4, 8 or 12 hours.
# * Current conditions portion will be executed once per hour.
# * If current conditions calculations fail for any reason, then the forecast data table should be opened, and values should be selected based on the matching date/time index.
# * Use hourly infiltration estimate in dose/exposure and RIVEC calculations.
# 
# It's worth noting that I was not able to export this .pynb file to .py script using the option under File>Download As>Python. Had to use the following at the command line (https://ipython.org/ipython-doc/1/interactive/nbconvert.html):
# 
# ipython nbconvert --to python Weather_Underground_API_infiltration.ipynb

# In[2]:

import requests
import numpy as np
import datetime
import os
import sys
import time

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

#Set of infiltration model coefficients. Coef_array is 3x5. From 2013 ASHRAE Handbook of Fundamentals, Chapter 16, 
#pages 24-25, Tables 7, 8 and 9. 

#Row 0 = 1-story, 
#Row 1 = 2-story, 
#Row 3 = 3-story

#Col 0 = Wind Speed Multiplier (G), 
#Col 1 = Stack Coefficient (Cs, assumes flue), 
#Col 2 = Wind coefficient (Cw, assumes crawlspace + flue), 
#Col 3 = Wind Coefficient (Cw, assumes basement slab + flue), 
#Col 4 = Shelter Factor (s, assumes shelter class 4 + flue).

Coefficients = [0.48,0.59,0.67,0.069,0.089,0.107,0.128,0.142,0.154,0.142,0.156,0.167,0.7,0.64,0.61]
Coef_array = np.array(Coefficients).reshape(5, 3).T

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


# In[3]:

for attempt in range(10):

    if attempt < 9:

        try:

            #Request json data for current measured conditions.
            conditions = requests.get("http://api.wunderground.com/api/%s/conditions/q/CA/San_Leandro.json" % API_key)
            curr_cond = conditions.json()
            
            #Can also take this the route of ONLY using current conditions.
            #My goal would be for the controller to use the current conditions at the top of every hour to estimate infiltration,
            #For any instances where the internet connection is down, and current conditions cannot be retrieved,
            #The hourly forecast data table can be used. 

            temp_curr = curr_cond['current_observation']['temp_c']
            wind_curr = curr_cond['current_observation']['wind_kph'] * (float(1000)/3600)
            inf_curr = superposition(stack(c, Cs, (House_temp - temp_curr)), wind(c, Cw, s, G, wind_curr))

            break

        except: 

            print "An error occurred connecting to the Weather Underground host. Will try again in a bit."
            time.sleep(60)
            
    else:
        #Here is where we would then open the forecast data and use it in our predictions.
        
        #This sequence is used when current condition data are not available.
        #The 3-day hourly forecast data is opened from file, and the correct datetime is used to select a 
        #value for inf_curr (current infiltration estimate, m3/s).

        #Loads the forecast data from the local file system. 
        forecast_vals = np.loadtxt('Forecast_Values.txt', delimiter = ",", 
                                   dtype={'names': ('datetime', 'temp', 'wind_spd', 'inf'), 
                                          'formats': ('a18', 'i4', 'f8', 'f8')})

        #cpu time
        d = datetime.datetime.now()

        bool_vals = []

        for hour in range(len(forecast_vals)):
            #creates datetime obj for each entry in forecast_vals
            d_file = datetime.datetime.strptime(forecast_vals['datetime'][hour], '%Y/%m/%d %H:%M') 
            #creates list of boolean T/F values. Need to identify the entry in vals that is the last entry not greater than the current cpu time.
            bool_vals.append(d < d_file)  

        #creates indexes of True boolean values.    
        bool_vals_ind = np.where(bool_vals) 

        #identifies the minimum True index and steps back one row.
        #This is the most recent entry in the forecast_vals array. 
        current_time_index = np.amin(bool_vals_ind)-1 

        #Pulls current infiltration estimate from historical forecast estimates.  
        inf_curr = forecast_vals['inf'][current_time_index]


# In[7]:

#This gets us to a point where we have a current infiltration estimate, either from current values or prior forecast.
print inf_curr

