from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
from geopy.geocoders import Nominatim

def get_image_location(image_path):
    def extract_gps_data(image):
        exif_data = image._getexif()
        if not exif_data:
            return None, None

        gps_info = {}
        for tag_id, value in exif_data.items():
            tag = TAGS.get(tag_id, tag_id)
            if tag == "GPSInfo":
                for key in value:
                    sub_tag = GPSTAGS.get(key, key)
                    gps_info[sub_tag] = value[key]

        if 'GPSLatitude' in gps_info and 'GPSLongitude' in gps_info:
            lat = convert_to_decimal(gps_info['GPSLatitude'], gps_info.get('GPSLatitudeRef'))
            lon = convert_to_decimal(gps_info['GPSLongitude'], gps_info.get('GPSLongitudeRef'))
            return lat, lon
        return None, None

    def convert_to_decimal(dms, ref):
        def to_float(val):
            try:
                return val[0] / val[1]  # Tuple form
            except TypeError:
                return float(val)  # IFDRational form

        degrees = to_float(dms[0])
        minutes = to_float(dms[1])
        seconds = to_float(dms[2])

        decimal = degrees + (minutes / 60.0) + (seconds / 3600.0)

        if ref in ['S', 'W']:
            decimal = -decimal
        return decimal

    def reverse_geocode(lat, lon):
        geolocator = Nominatim(user_agent="geoapi")
        location = geolocator.reverse((lat, lon), exactly_one=True, timeout=10)
        return location.address if location else "Address not found."

    try:
        img = Image.open(image_path)
        latitude, longitude = extract_gps_data(img)

        if latitude is not None and longitude is not None:
            address = reverse_geocode(latitude, longitude)
            return {
                'latitude': latitude,
                'longitude': longitude,
                'address': address
            }
        else:
            return {
                'error': 'GPS data not found in image.'
            }

    except Exception as e:
        return {'error': str(e)}

# === Example usage ===
result = get_image_location("images\loc.jpg")
print(result)
