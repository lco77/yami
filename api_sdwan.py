import os
import socket
import re
from datetime import timedelta
from celery.result import AsyncResult
from flask import Blueprint, request, session, jsonify
from app import login_required, roles_required, read_user_from_session, csrf, cache, make_key
from lib.aiosdwan import Vmanage
from dotenv import load_dotenv

load_dotenv()

SDWAN_WW_HOST = os.environ.get("SDWAN_WW_HOST")
SDWAN_WW_USERNAME = os.environ.get("SDWAN_WW_USERNAME")
SDWAN_WW_PASSWORD = os.environ.get("SDWAN_WW_PASSWORD")

SDWAN_CN_HOST = os.environ.get("SDWAN_CN_HOST")
SDWAN_CN_USERNAME = os.environ.get("SDWAN_CN_USERNAME")
SDWAN_CN_PASSWORD = os.environ.get("SDWAN_CN_PASSWORD")

sdwan_ww = Vmanage(SDWAN_WW_HOST,SDWAN_WW_USERNAME,SDWAN_WW_PASSWORD)
sdwan_cn = Vmanage(SDWAN_CN_HOST,SDWAN_CN_USERNAME,SDWAN_CN_PASSWORD)

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


bp = Blueprint('api_sdwan', __name__, url_prefix='/api/sdwan')

# get devices
@bp.route("/device", methods=['GET'])
@login_required
@cache.cached(timeout=300, key_prefix=make_key)
@csrf.exempt
async def get_devices():
    data_ww = await sdwan_ww.get_devices()
    data_cn = await sdwan_cn.get_devices()
    data = data_ww | data_cn
    if data:
        return [ device.todict() for uuid,device in data.items() ]
    else:
        return []
