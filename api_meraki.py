import os
import socket
import re
import json
from datetime import timedelta
from celery.result import AsyncResult
from flask import Blueprint, request, session, jsonify
from app import login_required, roles_required, read_user_from_session, csrf, cache, make_key
from lib.aiomeraki import Meraki
from dotenv import load_dotenv

load_dotenv()

MERAKI_FABRICS = json.loads(os.environ.get("MERAKI_FABRICS"))
meraki = {}
for f in MERAKI_FABRICS:
    meraki[f["name"]] = Meraki(api_key = f["api_key"], org_id = f["org_id"])

bp = Blueprint('api_meraki', __name__, url_prefix='/api/meraki')

# get templates
@bp.route("/<string:fabric>/templates", methods = ['GET'])
@roles_required(["wlan_admin","wlan_operator"])
@cache.cached(timeout=300, key_prefix=make_key)
@csrf.exempt
async def get_templates(fabric):
    if not fabric in meraki.keys():
        return jsonify({"error": f"Invalid fabric {fabric}"}), 400
    data = await meraki[fabric].get_templates(request.args)
    if data:
        return [ e.to_dict() for e in data ]
    else:
        return jsonify({"error": f"No data"}), 400
    
# get networks
@bp.route("/<string:fabric>/networks", methods = ['GET'])
@roles_required(["wlan_admin","wlan_operator"])
@cache.cached(timeout=300, key_prefix=make_key)
@csrf.exempt
async def get_networks(fabric):
    if not fabric in meraki.keys():
        return jsonify({"error": f"Invalid fabric {fabric}"}), 400
    data = await meraki[fabric].get_networks(request.args)
    if data:
        return [ e.to_dict() for e in data ]
    else:
        return jsonify({"error": f"No data"}), 400

# get devices
@bp.route("/<string:fabric>/devices", methods = ['GET'])
@roles_required(["wlan_admin","wlan_operator"])
@cache.cached(timeout=60, key_prefix=make_key)
@csrf.exempt
async def get_devices(fabric):
    if not fabric in meraki.keys():
        return jsonify({"error": f"Invalid fabric {fabric}"}), 400
    data = await meraki[fabric].get_devices(request.args)
    if data:
        return [ e.to_dict() for e in data ]
    else:
        return jsonify({"error": f"No data"}), 400