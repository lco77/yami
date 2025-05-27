import socket
import json
from dataclasses import dataclass, field, asdict

from flask import current_app, g, Blueprint, request, url_for, session, jsonify, json, make_response, render_template, redirect
from flask_wtf import FlaskForm, CSRFProtect
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired


from app import login_required, roles_required, read_user_from_session
from api_sdwan import sdwan_ww, sdwan_cn


bp = Blueprint('ui_sdwan', __name__, url_prefix='/ui/sdwan')

# DeviceForm
class DeviceForm(FlaskForm):
    hostname = StringField('Hostname', validators=[DataRequired()])
    submit = SubmitField('Search')

@dataclass
class Device:
    hostname: str
    ip_address: str = None
    task_id: str = None

# SDWAN devices index
@bp.route('/', methods=['GET'])
@login_required
async def index():
    user = read_user_from_session(session)
    return render_template("sdwan/index.html", user=user, theme=session["theme"])

# SDWAN device page
@bp.route('/<string:fabric>/<string:id>', methods=['GET'])
@login_required
async def show_device(fabric,id):
    user = read_user_from_session(session)
    try:
        match fabric:
            case sdwan_ww.host:
                r = await sdwan_ww.get_devices()
            case sdwan_cn.host:
                r = await sdwan_cn.get_devices()
            case _:
                return jsonify({"error": f"Invalid fabric {fabric}"}), 400
        if id in r.keys():
            data = r[id]
            hostname = data.hostname
        else:
            return jsonify({"error": f"Invalid device {id}"}), 400
    except Exception as err:
        return jsonify({"error": str(err)}), 400
    return render_template("sdwan/device.html", user=user, theme=session["theme"], id=id, hostname=hostname, data=data, fabric=fabric)

# LAN device interface page
@bp.route('/<string:fabric>/<string:id>/interface/<string:if_name>', methods=['GET'])
@login_required
async def show_interface(fabric,id,if_name):
    if_name = if_name.replace("_","/")
    user = read_user_from_session(session)
    try:
        match fabric:
            case sdwan_ww.host:
                r = await sdwan_ww.get_devices()
            case sdwan_cn.host:
                r = await sdwan_cn.get_devices()
            case _:
                return jsonify({"error": f"Invalid fabric {fabric}"}), 400
        if id in r.keys():
            data = r[id]
            hostname = data.hostname
        else:
            return jsonify({"error": f"Invalid device {id}"}), 400
    except Exception as err:
        return jsonify({"error": str(err)}), 400
    return render_template("sdwan/interface.html", user=user, theme=session["theme"], id=id, hostname=hostname, data=data, if_name=if_name, fabric=fabric)