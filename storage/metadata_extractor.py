"""
SITESENSE - Metadata Extraction Utility (Feature 1.2, Week 1)
Extracts EXIF metadata (Timestamp, GPS Coordinates, Device Model, Resolution) 
from uploaded images, with fallbacks for browser/site metadata.
"""

from typing import Dict, Any, Optional, Tuple
from datetime import datetime
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS

def dms_to_decimal(dms: Tuple, ref: str) -> Optional[float]:
    """Converts Degrees, Minutes, Seconds GPS tuples to decimal coordinates."""
    if not dms or len(dms) < 3:
        return None
    try:
        degrees = float(dms[0])
        minutes = float(dms[1])
        seconds = float(dms[2])
        decimal = degrees + (minutes / 60.0) + (seconds / 3600.0)
        if ref in ["S", "W"]:
            decimal = -decimal
        return round(decimal, 6)
    except Exception:
        return None

def extract_image_metadata(
    file_path: str,
    site_id: str,
    user_id: str,
    fallback_lat: Optional[float] = None,
    fallback_lng: Optional[float] = None
) -> Dict[str, Any]:
    """
    Extracts embedded EXIF metadata from an uploaded image file:
    - Capture timestamp
    - GPS Latitude and Longitude
    - Device make & model
    - Image dimensions (width, height)
    """
    metadata: Dict[str, Any] = {
        "site_id": site_id,
        "uploaded_by": user_id,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "device": "Unknown",
        "gps": None,
        "resolution": None
    }

    try:
        with Image.open(file_path) as img:
            metadata["resolution"] = f"{img.width}x{img.height}"
            exif_data = img._getexif()

            if not exif_data:
                # Apply fallback GPS if provided from frontend browser geolocation
                if fallback_lat is not None and fallback_lng is not None:
                    metadata["gps"] = {"lat": fallback_lat, "lng": fallback_lng, "source": "browser_gps"}
                return metadata

            parsed_exif = {}
            for tag_id, value in exif_data.items():
                tag_name = TAGS.get(tag_id, tag_id)
                parsed_exif[tag_name] = value

            # 1. Device Make & Model
            make = str(parsed_exif.get("Make", "")).strip()
            model = str(parsed_exif.get("Model", "")).strip()
            if make or model:
                metadata["device"] = f"{make} {model}".strip()

            # 2. Capture Timestamp
            dt_str = parsed_exif.get("DateTimeOriginal") or parsed_exif.get("DateTime")
            if dt_str:
                try:
                    # Format standard: "YYYY:MM:DD HH:MM:SS"
                    dt_obj = datetime.strptime(str(dt_str), "%Y:%m:%d %H:%M:%S")
                    metadata["timestamp"] = dt_obj.isoformat() + "Z"
                except Exception:
                    pass

            # 3. GPS Coordinates
            gps_info = parsed_exif.get("GPSInfo")
            if gps_info:
                gps_parsed = {}
                for key in gps_info.keys():
                    gps_tag = GPSTAGS.get(key, key)
                    gps_parsed[gps_tag] = gps_info[key]

                lat = dms_to_decimal(gps_parsed.get("GPSLatitude"), gps_parsed.get("GPSLatitudeRef", "N"))
                lng = dms_to_decimal(gps_parsed.get("GPSLongitude"), gps_parsed.get("GPSLongitudeRef", "E"))

                if lat is not None and lng is not None:
                    metadata["gps"] = {"lat": lat, "lng": lng, "source": "exif_camera"}

            # Fallback to browser GPS if camera GPS was disabled/absent
            if not metadata["gps"] and fallback_lat is not None and fallback_lng is not None:
                metadata["gps"] = {"lat": fallback_lat, "lng": fallback_lng, "source": "browser_gps"}

    except Exception as e:
        metadata["error"] = f"EXIF extraction error: {str(e)}"

    return metadata

