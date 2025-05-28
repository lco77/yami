import os
import socket
import re
import json
from datetime import timedelta
from celery.result import AsyncResult
from flask import Blueprint, request, session, jsonify
from app import login_required, roles_required, read_user_from_session, csrf, cache, make_key
from lib.aiosdwan import Vmanage
from dotenv import load_dotenv

load_dotenv()

SDWAN_FABRICS = json.loads(os.environ.get("SDWAN_FABRICS"))

sdwan = {}
for f in SDWAN_FABRICS:
    sdwan[f["name"]] = Vmanage(f["host"],f["username"],f["password"])

bp = Blueprint('api_sdwan', __name__, url_prefix='/api/sdwan')

# get devices
@bp.route("/<string:fabric>/device", methods=['GET'])
@login_required
#@cache.cached(timeout=300, key_prefix=make_key)
@csrf.exempt
async def get_devices(fabric):
    if not fabric in sdwan.keys():
        return jsonify({"error": f"Invalid fabric {fabric}"}), 400
    data = await sdwan[fabric].get_devices()
    if data:
        return [ device.todict() for uuid,device in data.items() if device.hostname is not None ]
    else:
        return jsonify({"error": f"No data"}), 400

# get device template values
@bp.route("/<string:fabric>/device/<string:device_id>/template_values/<string:template_id>", methods=['GET'])
@login_required
#@cache.cached(timeout=300, key_prefix=make_key)
@csrf.exempt
async def get_device_template_values(fabric,device_id,template_id):
    if not fabric in sdwan.keys():
        return jsonify({"error": f"Invalid fabric {fabric}"}), 400
    data = await sdwan[fabric].get_device_template_values(device_id, template_id)
    if data:
        return data
    else:
        return jsonify({"error": f"No data"}), 400

# get device route table
@bp.route("/<string:fabric>/device/<string:device_id>/route_table", methods=['GET'])
@login_required
#@cache.cached(timeout=300, key_prefix=make_key)
@csrf.exempt
async def get_device_route_table(fabric,device_id):
    if not fabric in sdwan.keys():
        return jsonify({"error": f"Invalid fabric {fabric}"}), 400
    data = await sdwan[fabric].get_device_route_table(device_id)
    if data:
        return data
    else:
        return jsonify({"error": f"No data"}), 400