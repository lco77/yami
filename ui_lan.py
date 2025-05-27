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

# LAN devices index
@bp.route('/', methods=['GET'])
@login_required
async def index():
    user = read_user_from_session(session)
    return render_template("lan/index.html", user=user, theme=session["theme"])

# LAN device page
@bp.route('/<string:id>', methods=['GET'])
@login_required
async def show_device(id):
    user = read_user_from_session(session)
    try:
        r = await dnac.get_devices({"id":[id]})
        data = r[0]
        hostname = data.hostname
    except Exception as err:
        return jsonify({"error": str(err)}), 400
    return render_template("lan/device.html", user=user, theme=session["theme"], id=id, hostname=hostname, data=data)

# LAN device interface page
@bp.route('/<string:id>/interface/<string:if_name>', methods=['GET'])
@login_required
async def show_interface(id,if_name):
    if_name = if_name.replace("_","/")
    user = read_user_from_session(session)
    try:
        r = await dnac.get_devices({"id":[id]})
        data = r[0]
        hostname = data.hostname
    except Exception as err:
        return jsonify({"error": str(err)}), 400
    return render_template("lan/interface.html", user=user, theme=session["theme"], id=id, hostname=hostname, data=data, if_name=if_name)