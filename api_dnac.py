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

# get device
@bp.route("/device/<string:id>", methods=['GET'])
@login_required
@cache.cached(timeout=300, key_prefix=make_key)
@csrf.exempt
async def get_device(id):
    data = await dnac.get_device(id)
    if data:
        return data
    else:
        return None