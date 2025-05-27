import socket
from celery.result import AsyncResult
from flask import Blueprint, request, session, jsonify

from app import login_required, roles_required, read_user_from_session, csrf
from tasks import hello, run_ssh_command

bp = Blueprint('api_tasks', __name__, url_prefix='/api/tasks')



# submit Celery task
@bp.route('/', methods=['POST'])
@login_required
@csrf.exempt
def create_task():
    user = read_user_from_session(session)
    payload = request.get_json()
    task_type = payload.get("type", None)
    task_data = payload.get("data", None)

    if task_type is None or task_data is None:
        return jsonify({"error": "Missing task type or data"}), 400

    match task_type:
        # Hello task
        case "hello":
            result = hello.apply_async(
                kwargs = task_data,
                headers = { "owner": user.username }
            )
        # ssh_cmd
        case "ssh_cmd":
            result = run_ssh_command.apply_async(
                kwargs = {
                    "username": user.username,
                    "password": user.password,
                    "host": task_data.get("ip_address"),
                    "command": task_data.get("cmd"),
                    "device_type": task_data.get("device_type"),
                    "use_textfsm": task_data.get("use_textfsm",False)
                },
                headers = { "owner": user.username }
            )

    return jsonify({"task_id": result.id}), 202

# get Celery task status
@bp.route("/<string:task_id>", methods=["GET"])
@login_required
@csrf.exempt
def get_task(task_id):
    result = AsyncResult(task_id)

    response = {
        "task_id": task_id,
        "status": result.status,
        "success": result.successful(),
        "ready": result.ready(),
        "result": result.result if result.ready() and result.successful() else None,
    }

    return jsonify(response)

