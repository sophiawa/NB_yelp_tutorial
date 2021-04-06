# setup library imports
import json
import requests
from bs4 import BeautifulSoup
import re
import numpy as np
import pandas as pd


# Determine if a restaurant opens in AM and get list of amenities (webscraping)
def get_info(url):
    
    r = requests.get(url)
    content = r.content
    soup = BeautifulSoup(content, 'html.parser')

    # Determine if the restaurant opens in the AM on Saturdays
    hours = soup.find_all('p', class_=re.compile(r'no-wrap__373c0__2vNX7 css-1h1j0y3'))
    opens_in_am = False
    if len(hours) > 6:
        saturday_hours = hours[5].getText()
        M_index = saturday_hours.find('M')
        open_AM_or_PM = saturday_hours[M_index - 1]
        opens_in_am = (open_AM_or_PM == 'A')
    
    # Get the list of amenities (ex: good for groups, vegan options, requires masks, etc.)
    amenities_find = soup.find_all('span', attrs={'class': 'css-1h1j0y3'})
    amenities = []
    for am in amenities_find:
        amenities.append(am.get_text())

    return opens_in_am, amenities


# Use Yelp API to get all restaurants in a location (query),
# and store them in json file to be used by parse_data()
def all_restaurants(query):
    
    d = dict()
    
    params_dict = { 'location' : query, 'categories' : 'restaurants, All', 'limit' : 20, 'offset' : 0 }
    headers_dict = { 'authorization' : 'Bearer iHsDztyGVvY1fjrD8y9mrOUrpm-PoLpQe5EzKI4rcvvXRvG1DIcWUC8TlXJW3VU2nVoE7AUr-rDx090Zn2vwf49BQzW3S_RCWd312sUz9l-JJCNmeWBzkxRucY0oYHYx' }
    url = 'https://api.yelp.com/v3/businesses/search'
    
    r = requests.get(url, params=params_dict, headers=headers_dict)
    response = r.json()
    total = response['total']
    businesses = []
    businesses.extend(response['businesses'])
    
    while len(businesses) < total:
        params_dict['offset'] += 20
        r = requests.get(url, params=params_dict, headers=headers_dict)
        response = r.json()
        if 'businesses' in response:
            businesses.extend(response['businesses'])

    l = dict()
    l['businesses'] = businesses
    with open('pittsburgh_yelp_restaurants.txt', 'w') as f:
        json.dump(l, f)

    return businesses


# Use restaurant data from above to create a dictionary for each business,
# storing their information (such as if they take reservations, prices, etc.)
# Also stores all dictionaries in a json file to be used by further_parsing()
def parse_data():
    with open('pittsburgh_yelp_restaurants.txt') as json_file:
        data = json.load(json_file)
        businesses = data['businesses']
        restaurants = []

        for bus in businesses:
            d = dict()
            d['name'] = bus['name']
            d['has_delivery'] = ('delivery' in bus['transactions'])
            d['has_pickup'] = ('pickup' in bus['transactions'])
            d['has_takeout'] = ('takeout' in bus['transactions'])
            d['has_reservations'] = ('restaurant_reservation' in bus['transactions'])
            d['categories'] = [ cat['alias'] for cat in bus['categories'] ]
            if 'price' in bus:
                d['price'] = len(bus['price'])
            d['rating'] = bus['rating']
            opens_in_am, amenities = get_info(bus['url'])
            d['opens_in_am'] = opens_in_am
            d['amenities'] = amenities
            restaurants.append(d)
        
        final_dict = dict()
        final_dict['businesses'] = restaurants

        with open('pittsburgh_yelp_data.txt', 'w') as f:
            json.dump(final_dict, f)

# For each restaurant, stores feature values that will be used in the classifier
# Stores results in json file
def further_parsing():
    with open('pittsburgh_yelp_data.txt') as json_file:
        bus = json.load(json_file)['businesses']
        for b in bus:
            b['rating'] = int(b['rating'])
            if b['rating'] >= 4.0:
                b['rating'] = 1
            else:
                b['rating'] = 0
            # high_prices
            b['high_prices'] = False
            if 'price' in b and b['price'] >= 3:
                b['high_prices'] = True
            
            # has_bar
            b['has_bar'] = False
            b['has_pizza'] = False
            b['has_breakfast'] = False
            b['has_asian'] = False
            b['has_mexican'] = False
            b['has_vegan'] = False
            b['has_icecream'] = False
            b['is_bakery'] = False
            b['has_italian'] = False
            b['has_outdoor_seating'] = False
            b['covid_concerned'] = False
            for cat in b['categories']:
                if 'bar' in cat or 'pub' in cat:
                    b['has_bar'] = True
                if 'pizza' in cat:
                    b['has_pizza'] = True
                if 'breakfast' in cat:
                    b['has_breakfast'] = True
                if 'asian' in cat or 'thai' in cat or 'sushi' in cat or 'korean' in cat or 'chinese' in cat or 'vietnamese' in cat or 'japanese' in cat or 'ramen' in cat:
                    b['has_breakfast'] = True
                if 'tacos' in cat or 'mexican' in cat:
                    b['has_mexican'] = True
                if 'vegan' in cat:
                    b['has_vegan'] = True
                if 'icecream' in cat:
                    b['has_icecream'] = True
                if 'bakeries' in cat:
                    b['is_bakery'] = True
                if 'has_italian' in cat:
                    b['has_italian'] = True

            for am in b['amenities']:
                if 'Outdoor' in am:
                    b['has_outdoor_seating'] = True
                if 'Sanitizing' in am or 'Distancing' in am or 'Masks' in am or 'masks' in am:
                    b['covid_concerned'] = True

    with open('more_parsing.txt', 'w') as f:
        json.dump(bus, f)    
                

# Loads feature and label data from further_parsing() into dataframes,
# and stores them in csv files to be loaded into google colab tutorial
def load_data_into_arrays():
    
    with open('more_parsing.txt') as json_file:
        restaurants = json.load(json_file)
        features = ['has_delivery', 'has_pickup', 'has_takeout', 'has_reservations', 'high_prices', 'opens_in_am', 'has_bar', 'has_pizza', 'has_breakfast', 'has_asian', 'has_mexican', 'has_vegan', 'has_icecream', 'is_bakery', 'has_italian', 'has_outdoor_seating', 'covid_concerned']
        d, n = len(features), len(restaurants)
        XTrain = np.zeros((n, d))
        yTrain = np.zeros(n)

        for ri in range(n):
            for i in range(d):
                feature = features[i]
                XTrain[ri][i] = 1 if restaurants[ri][feature] else 0
            yTrain[ri] = restaurants[ri]['rating']

        count_zeros = np.count_nonzero(yTrain == 0.0)
        count_ones = np.count_nonzero(yTrain == 1.0)
        where_ones = np.where(yTrain == 1.0)[0][:count_zeros]
        where_zeros = np.where(yTrain == 0.0)
        where = np.append(where_ones, where_zeros)
        yTrain = yTrain[where]
        XTrain = XTrain[where]
    
    XTrain_df = pd.DataFrame(data=XTrain)
    yTrain_df = pd.DataFrame(data=yTrain)

    XTrain_df.to_csv('XTrain.csv', index=False)
    yTrain_df.to_csv('yTrain.csv', index=False)

    return XTrain_df, yTrain_df
        


further_parsing()
load_data_into_arrays()
