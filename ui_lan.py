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

# DeviceForm
class DeviceForm(FlaskForm):
    hostname = StringField('Hostname', validators=[DataRequired()])
    submit = SubmitField('Search')

@dataclass
class Device:
    hostname: str
    ip_address: str = None
    task_id: str = None

@bp.route('/', methods=['GET'])
@login_required
async def index():
    user = read_user_from_session(session)
    return render_template("lan/index.html", user=user, theme=session["theme"])

@bp.route('/<string:id>', methods=['GET'])
@login_required
async def show_device(id):
    user = read_user_from_session(session)
    try:
        r = await dnac.get_devices({"id":[id]})
        data = r.get("response")[0]
        hostname = data["hostname"].upper().split(".")[0]
        ip = data["dnsResolvedManagementAddress"]
        print(json.dumps(data,indent=4))
    except Exception as err:
        return jsonify({"error": str(err)}), 400
    return render_template("lan/device.html", user=user, theme=session["theme"], id=id, hostname=hostname, data=data)

@bp.route('/<string:id>/<string:if_name>', methods=['GET'])
@login_required
async def show_interface(id,if_name):
    if_name = if_name.replace("_","/")
    user = read_user_from_session(session)
    try:
        r = await dnac.get_devices({"id":[id]})
        data = r.get("response")[0]
        hostname = data["hostname"].upper().split(".")[0]
        ip = data["dnsResolvedManagementAddress"]
        print(json.dumps(data,indent=4))
    except Exception as err:
        return jsonify({"error": str(err)}), 400
    return render_template("lan/interface.html", user=user, theme=session["theme"], id=id, hostname=hostname, data=data, if_name=if_name)