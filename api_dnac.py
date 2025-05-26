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

# get devices
@bp.route("/device", methods=['GET'])
@login_required
@cache.cached(timeout=300, key_prefix=make_key)
@csrf.exempt
async def get_devices():
    data = await dnac.get_devices(request.args)
    if data:
        return [ device.todict() for device in data ]
    else:
        return []
