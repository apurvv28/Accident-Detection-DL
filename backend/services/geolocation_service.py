"""
Geolocation service: reverse geocoding and camera coordinate mapping
"""
import os
from typing import Optional, Dict
from ..utils.logger import setup_logger

logger = setup_logger(__name__)

# Try to import googlemaps
try:
	import googlemaps
	GMAPS_AVAILABLE = True
except Exception:
	GMAPS_AVAILABLE = False
	logger.info("googlemaps not available; will use fallback geocoding if needed")

try:
	from geopy.geocoders import Nominatim
	GEOPY_AVAILABLE = True
except Exception:
	GEOPY_AVAILABLE = False


class GeoLocationService:
	"""Provides reverse geocoding and camera coordinate mapping."""

	def __init__(self, api_key_env: str = 'GOOGLE_MAPS_API_KEY'):
		self.api_key = os.getenv(api_key_env)
		self.gmaps = None
		if GMAPS_AVAILABLE and self.api_key:
			try:
				self.gmaps = googlemaps.Client(key=self.api_key)
			except Exception as e:
				logger.error(f"Failed to init Google Maps client: {e}")

		self.nominatim = None
		if GEOPY_AVAILABLE:
			try:
				self.nominatim = Nominatim(user_agent="accident_detection_app")
			except Exception as e:
				logger.error(f"Failed to init Nominatim: {e}")

	def reverse_geocode(self, lat: float, lon: float) -> Dict:
		"""Return a dict with address and formatted result.

		Falls back to Nominatim if Google Maps isn't available.
		"""
		try:
			if self.gmaps:
				res = self.gmaps.reverse_geocode((lat, lon))
				if res:
					best = res[0]
					return {
						'address': best.get('formatted_address'),
						'raw': best
					}

			if self.nominatim:
				loc = self.nominatim.reverse((lat, lon), exactly_one=True, language='en')
				if loc:
					return {
						'address': loc.address,
						'raw': loc.raw
					}

		except Exception as e:
			logger.error(f"Reverse geocode failed: {e}")

		# Fallback
		return {
			'address': f"{lat:.6f},{lon:.6f}",
			'raw': None
		}

	def camera_to_location(self, camera_doc: Dict) -> Dict:
		"""Map camera document to a location dict

		Expects camera_doc to potentially contain 'location' or 'latitude'/'longitude'.
		"""
		loc = camera_doc.get('location') if camera_doc else None
		if loc and 'latitude' in loc and 'longitude' in loc:
			return {'latitude': loc['latitude'], 'longitude': loc['longitude'], 'address': loc.get('address')}

		# Try other fields
		lat = camera_doc.get('latitude') or camera_doc.get('lat')
		lon = camera_doc.get('longitude') or camera_doc.get('lon')
		if lat is not None and lon is not None:
			data = self.reverse_geocode(lat, lon)
			return {'latitude': lat, 'longitude': lon, 'address': data.get('address')}

		return {'latitude': None, 'longitude': None, 'address': None}


# Backwards-compatible alias (older code expects `GeolocationService`)
GeolocationService = GeoLocationService

