from geopy.geocoders import Nominatim
from geopy.distance import geodesic
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable
import time

def get_coordinates(city_name):
    """
    Get coordinates (latitude, longitude) for a given city name.
    Returns None if city not found or error.
    """
    geolocator = Nominatim(user_agent="traffic_app_distance_calculator")
    try:
        # Appending "Brasil" to ensure we get cities in Brazil by default, 
        # but user can specify full address if needed.
        location = geolocator.geocode(f"{city_name}, Brasil", timeout=10)
        if location:
            return (location.latitude, location.longitude)
        return None
    except (GeocoderTimedOut, GeocoderUnavailable):
        return None

def calculate_distance(origin_city, destination_city):
    """
    Calculate distance in km between two cities.
    Returns distance as float or None if calculation fails.
    """
    if not origin_city or not destination_city:
        return None
        
    origin_coords = get_coordinates(origin_city)
    dest_coords = get_coordinates(destination_city)
    
    if origin_coords and dest_coords:
        distance = geodesic(origin_coords, dest_coords).kilometers
        return round(distance, 2)
    
    return None
