import os
import socket
import re
import json
from datetime import timedelta
from celery.result import AsyncResult
from flask import Blueprint, request, session, jsonify
from app import login_required, roles_required, read_user_from_session, csrf, cache, make_key
from lib.aiodnac import Dnac
from dotenv import load_dotenv

load_dotenv()
DNAC_FABRICS = json.loads(os.environ.get("DNAC_FABRICS"))

dnac = {}
for f in DNAC_FABRICS:
    dnac[f["name"]] = Dnac(f["host"],f["username"],f["password"])

bp = Blueprint('api_dnac', __name__, url_prefix='/api/dnac')

# get devices
@bp.route("/<string:fabric>/device", methods=['GET'])
@login_required
@cache.cached(timeout=300, key_prefix=make_key)
@csrf.exempt
async def get_devices(fabric):
    if not fabric in dnac.keys():
        return jsonify({"error": f"Invalid fabric {fabric}"}), 400
    data = await dnac[fabric].get_devices(request.args)
    if data:
        return [ device.todict() for device in data ]
    else:
        return []

# get device
@bp.route("/<string:fabric>/device/<string:id>", methods=['GET'])
@login_required
@cache.cached(timeout=300, key_prefix=make_key)
@csrf.exempt
async def get_device(fabric,id):
    if not fabric in dnac.keys():
        return jsonify({"error": f"Invalid fabric {fabric}"}), 400
    data = await dnac[fabric].get_device(id)
    if data:
        return data
    else:
        return None