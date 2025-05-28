import socket
import json
from dataclasses import dataclass, field, asdict

from flask import current_app, g, Blueprint, request, url_for, session, jsonify, json, make_response, render_template, redirect
from flask_wtf import FlaskForm, CSRFProtect
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired


from app import login_required, roles_required, read_user_from_session
from api_dnac import dnac


bp = Blueprint('ui_lan', __name__, url_prefix='/ui/lan')

# infer device type from platform
def check_device_type(platform:list[str])->str:
    match = ['N5K', 'N7K', 'N9K']
    found = any(item.startswith(prefix) for item in platform for prefix in match)
    if found:
        return "cisco_nxos_ssh"
    else:
        return "cisco_ios"

# DeviceForm
class DeviceForm(FlaskForm):
    hostname = StringField('Hostname', validators=[DataRequired()])
    submit = SubmitField('Search')

@dataclass
class Device:
    hostname: str
    ip_address: str = None
    task_id: str = None

# LAN devices index
@bp.route('/', methods=['GET'])
@login_required
async def index():
    user = read_user_from_session(session)
    return render_template("lan/index.html", user=user, theme=session["theme"], fabrics=list(dnac.keys()))

# LAN device page
@bp.route('/<string:fabric>/<string:id>', methods=['GET'])
@login_required
async def show_device(fabric,id):
    user = read_user_from_session(session)
    try:
        if not fabric in dnac.keys():
            return jsonify({"error": f"Invalid fabric {fabric}"}), 400
        r = await dnac[fabric].get_devices({"id":[id]})
        data = r[0]
        hostname = data.hostname
        device_type = check_device_type(data.platform)
    except Exception as err:
        return jsonify({"error": str(err)}), 400
    return render_template("lan/device.html", user=user, theme=session["theme"], id=id, hostname=hostname, device_type=device_type, data=data, fabric=fabric)

# LAN device interface page
@bp.route('/<string:fabric>/<string:id>/interface/<string:if_name>', methods=['GET'])
@login_required
async def show_interface(fabric,id,if_name):
    if_name = if_name.replace("_","/")
    user = read_user_from_session(session)
    try:
        r = await dnac[fabric].get_devices({"id":[id]})
        data = r[0]
        hostname = data.hostname
        device_type = check_device_type(data.platform)
    except Exception as err:
        return jsonify({"error": str(err)}), 400
    return render_template("lan/interface.html", user=user, theme=session["theme"], id=id, hostname=hostname, device_type=device_type, data=data, if_name=if_name)