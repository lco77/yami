import os
import socket
import re
from datetime import timedelta
from celery.result import AsyncResult
from flask import Blueprint, request, session, jsonify
from app import login_required, roles_required, read_user_from_session, csrf, cache, make_key
from lib.aiodnac import Dnac
from dotenv import load_dotenv

load_dotenv()
DNAC_HOST = os.environ.get("DNAC_HOST")
DNAC_USERNAME = os.environ.get("DNAC_USERNAME")
DNAC_PASSWORD = os.environ.get("DNAC_PASSWORD")

dnac = Dnac(DNAC_HOST,DNAC_USERNAME,DNAC_PASSWORD)

def uptime_to_days(uptime_str):
    # Pattern: optional "xxx days, ", then H:MM:SS(.XX)
    match = re.match(r'(?:(\d+)\s+days?,\s+)?(\d+):(\d+):(\d+)(?:\.\d+)?', uptime_str)
    if not match:
        raise ValueError(f"Invalid uptime format: {uptime_str}")

    days = int(match.group(1)) if match.group(1) else 0
    hours = int(match.group(2))
    minutes = int(match.group(3))
    seconds = int(match.group(4))

    # Total time as timedelta
    total_time = timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds)
    return total_time.days


bp = Blueprint('api_dnac', __name__, url_prefix='/api/dnac')

# get sites
@bp.route("/site", methods=['GET'])
@login_required
#@cache.cached(timeout=60)
@csrf.exempt
async def get_sites():
    try:
        result = []
        data = await dnac.get_sites(request.args)
        if data:
            for site in data.get("response"):
                additional_info = site.get("additionalInfo")
                for info in additional_info:
                    if "nameSpace" in info and info.get("nameSpace") == "Location":
                        result.append({
                            "name": site.get("name"),
                            "country": info.get("attributes").get("country"),
                            "address": info.get("attributes").get("address"),
                            "latitude": info.get("attributes").get("latitude"),
                            "longitude": info.get("attributes").get("longitude")
                        })
        return result
    except Exception as err:
        return jsonify({"error": str(err)}), 400

# get devices
@bp.route("/device", methods=['GET'])
@login_required
@cache.cached(timeout=300, key_prefix=make_key)
@csrf.exempt
async def get_devices():
    try:
        result = []
        data = await dnac.get_devices(request.args)
        if data:
            for device in data.get("response"):
                platform = [e.strip() for e in device.get("platformId").split(",")] if device.get("platformId") else device.get("platformId")
                serial = [e.strip() for e in device.get("serialNumber").split(",")] if device.get("serialNumber") else device.get("serialNumber")
                if platform:
                    stack = len(serial)
                else:
                    stack = 0
                result.append({
                    "id": device.get("id"),
                    "hostname": device.get("hostname").upper().split(".")[0],
                    "ip_address": device.get("managementIpAddress"),
                    "platform": platform,
                    "serial": serial,
                    "stack": stack,
                    "version": device.get("softwareVersion"),
                    "uptime": uptime_to_days(device.get("upTime")),
                    "status": device.get("reachabilityStatus")

                })
        return result
    except Exception as err:
        return jsonify({"error": str(err)}), 400