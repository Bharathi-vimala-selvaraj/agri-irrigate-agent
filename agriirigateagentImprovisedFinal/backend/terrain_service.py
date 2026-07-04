"""
Terrain & Topography Analysis Service.

Uses free public APIs to obtain elevation, slope, and terrain information
for given GPS coordinates. Falls back to estimated values if APIs are unavailable.
"""
import requests
import math

OPEN_METEO_ELEVATION_URL = "https://api.open-meteo.com/v1/elevation"


def get_terrain_data(latitude: float, longitude: float) -> dict:
    """
    Fetch terrain data for given coordinates.
    Returns elevation, slope, terrain_type, and drainage_characteristics.
    """
    try:
        # Try Open-Meteo Elevation API (free, no key required)
        params = {
            "latitude": latitude,
            "longitude": longitude,
        }
        resp = requests.get(OPEN_METEO_ELEVATION_URL, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        
        print(f"DEBUG: Full API response: {data}")
        
        # Open-Meteo returns elevation as a list in format {"elevation": [value]}
        elevation_data = data.get("elevation", [0])
        if isinstance(elevation_data, list):
            elevation = float(elevation_data[0]) if len(elevation_data) > 0 else 0.0
        else:
            elevation = float(elevation_data) if elevation_data is not None else 0.0
        
        print(f"DEBUG: Elevation data: {elevation_data}, Elevation: {elevation}, Type: {type(elevation)}")
        
        # Ensure elevation is a float
        elevation = float(elevation)
        
        # Estimate slope based on elevation and regional characteristics
        # This is a simplified estimation - for production, use a proper DEM API
        slope = estimate_slope(latitude, longitude, elevation)
        
        # Determine terrain type based on elevation and slope
        terrain_type = classify_terrain(elevation, slope)
        
        # Determine drainage characteristics
        drainage = classify_drainage(slope, terrain_type)
        
        return {
            "elevation": round(elevation, 1),
            "slope": round(slope, 2),
            "terrain_type": terrain_type,
            "drainage_characteristics": drainage,
        }
    except (requests.RequestException, KeyError, ValueError, TypeError) as e:
        print(f"Terrain API error: {e}, using fallback estimation")
        return estimate_terrain_fallback(latitude, longitude)


def estimate_slope(lat: float, lng: float, elevation: float) -> float:
    """
    Estimate slope based on elevation and location.
    This is a simplified estimation for demonstration.
    """
    # Base slope estimation - higher elevation generally means more variation
    base_slope = min(15.0, elevation / 100.0)
    
    # Add some regional variation based on latitude
    lat_factor = abs(lat) / 90.0 * 5.0
    
    return base_slope + lat_factor


def classify_terrain(elevation: float, slope: float) -> str:
    """Classify terrain type based on elevation and slope."""
    if elevation < 50:
        if slope < 2:
            return "flat_plain"
        elif slope < 5:
            return "gentle_plain"
        else:
            return "rolling_plain"
    elif elevation < 500:
        if slope < 5:
            return "plateau"
        elif slope < 15:
            return "hilly"
        else:
            return "steep_hills"
    else:
        if slope < 10:
            return "highland"
        elif slope < 25:
            return "mountainous"
        else:
            return "steep_mountain"


def classify_drainage(slope: float, terrain_type: str) -> str:
    """Classify drainage characteristics based on slope and terrain."""
    if slope < 2:
        return "poor - water may accumulate"
    elif slope < 5:
        return "moderate - adequate drainage"
    elif slope < 15:
        return "good - natural drainage"
    else:
        return "excellent - rapid drainage, potential erosion risk"


def estimate_terrain_fallback(lat: float, lng: float) -> dict:
    """
    Fallback estimation when APIs are unavailable.
    Uses basic heuristics based on location.
    """
    # Simple estimation based on latitude
    elevation = abs(lat) * 10  # Very rough approximation
    slope = 3.0  # Assume moderate slope
    terrain_type = classify_terrain(elevation, slope)
    drainage = classify_drainage(slope, terrain_type)
    
    return {
        "elevation": round(elevation, 1),
        "slope": round(slope, 2),
        "terrain_type": terrain_type,
        "drainage_characteristics": drainage,
    }
