import socket
import json
from dataclasses import dataclass, field, asdict

from flask import current_app, g, Blueprint, request, url_for, session, jsonify, json, make_response, render_template, redirect
from flask_wtf import FlaskForm, CSRFProtect
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired


from app import login_required, roles_required, read_user_from_session
from api_meraki import meraki


bp = Blueprint('ui_wlan', __name__, url_prefix='/ui/wlan')




# WLAN index
@bp.route('/', methods=['GET'])
@roles_required(["wlan_admin","wlan_operator"])
async def index():
    user = read_user_from_session(session)
    return render_template("wlan/index.html", user=user, theme=session["theme"], fabrics=list(meraki.keys()))

# WLAN network page
@bp.route('/<string:fabric>/network/<string:id>', methods=['GET'])
@roles_required(["wlan_admin","wlan_operator"])
async def show_network(fabric,id):
    user = read_user_from_session(session)
    try:
        if not fabric in meraki.keys():
            return jsonify({"error": f"Invalid fabric {fabric}"}), 400
        data = await meraki[fabric].get_network(id)
    except Exception as err:
        return jsonify({"error": str(err)}), 400
    return render_template("wlan/network.html", user=user, theme=session["theme"], id=id, data=data, fabric=fabric)

# WLAN device page
@bp.route('/<string:fabric>/device/<string:id>', methods=['GET'])
@roles_required(["wlan_admin","wlan_operator"])
async def show_device(fabric,id):
    user = read_user_from_session(session)
    try:
        if not fabric in meraki.keys():
            return jsonify({"error": f"Invalid fabric {fabric}"}), 400
        device = await meraki[fabric].get_device(id)
        network = await meraki[fabric].get_network(device.network)
    except Exception as err:
        return jsonify({"error": str(err)}), 400
    return render_template("wlan/device.html", user=user, theme=session["theme"], id=id, device=device, network=network, fabric=fabric)