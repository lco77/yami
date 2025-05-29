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
@cache.cached(timeout=300, key_prefix=make_key)
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
@csrf.exempt
async def get_device_template_values(fabric,device_id,template_id):
    if not fabric in sdwan.keys():
        return jsonify({"error": f"Invalid fabric {fabric}"}), 400
    data = await sdwan[fabric].get_device_template_values(device_id, template_id)
    if data:
        return data
    else:
        return jsonify({"error": f"No data"}), 400

# set device template values
@bp.route("/<string:fabric>/device/<string:device_id>/template_values/<string:template_id>", methods=['POST'])
@roles_required(['admin'])
@csrf.exempt
async def set_device_template_values(fabric,device_id,template_id):
    if not fabric in sdwan.keys():
        return jsonify({"error": f"Invalid fabric {fabric}"}), 400
    payload = request.get_json()
    data = await sdwan[fabric].set_device_template_values(device_id, template_id, payload)
    if data:
        return data
    else:
        return jsonify({"error": f"No data"}), 400

# get device template definition
@bp.route("/<string:fabric>/device_template/<string:template_id>/definition", methods=['GET'])
@login_required
@cache.cached(timeout=300, key_prefix=make_key)
@csrf.exempt
async def get_device_template_definition(fabric,template_id):
    if not fabric in sdwan.keys():
        return jsonify({"error": f"Invalid fabric {fabric}"}), 400
    data = await sdwan[fabric].get_device_template_definition(template_id)
    if data:
        return data
    else:
        return jsonify({"error": f"No data"}), 400

# get device route table
@bp.route("/<string:fabric>/device/<string:device_id>/route_table", methods=['GET'])
@login_required
@cache.cached(timeout=60, key_prefix=make_key)
@csrf.exempt
async def get_device_route_table(fabric,device_id):
    if not fabric in sdwan.keys():
        return jsonify({"error": f"Invalid fabric {fabric}"}), 400
    data = await sdwan[fabric].get_device_route_table(device_id)
    if data:
        return data
    else:
        return jsonify({"error": f"No data"}), 400

# get device monitor actions
@bp.route("/<string:fabric>/device/<string:device_id>/monitor_actions", methods=['GET'])
@login_required
@cache.cached(timeout=86400, key_prefix=make_key)
@csrf.exempt
async def get_device_monitor_actions(fabric,device_id):
    if not fabric in sdwan.keys():
        return jsonify({"error": f"Invalid fabric {fabric}"}), 400
    data = await sdwan[fabric].get_device_monitor_actions()
    if data:
        return data
    else:
        return jsonify({"error": f"No data"}), 400

# get device monitor actions data
@bp.route("/<string:fabric>/device/<string:device_id>/monitor_actions", methods=['POST'])
@login_required
@csrf.exempt
async def get_device_monitor_actions_data(fabric,device_id):
    if not fabric in sdwan.keys():
        return jsonify({"error": f"Invalid fabric {fabric}"}), 400
    payload = request.get_json()
    data = await sdwan[fabric].get_device_monitor_actions(params=payload)
    if data:
        return data
    else:
        return jsonify({"error": f"No data"}), 400