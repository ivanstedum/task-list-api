from flask import Blueprint, jsonify, abort, make_response, request
from app.models.task import Task
from app import db
from sqlalchemy import asc
from datetime import datetime
from datetime import timezone
import requests
from dotenv import load_dotenv
import os
load_dotenv()

task_bp = Blueprint("tasks", __name__, url_prefix="/tasks")

def validate_model(cls, model_id):
    try:
        model_id=int(model_id)
    except:
        abort(make_response({"message":f"{cls.__name__}{model_id} invalid"}, 400))
    model =  cls.query.get(model_id)
    if not model:
        abort(make_response({"message":f"{cls.__name__} {model_id} was not found"}, 404))
    return model

@task_bp.route("", methods = ["GET"])
def read_all_tasks():
    query_sort= request.args.get("sort")
    if query_sort:
        if query_sort == "asc":
            tasks = Task.query.order_by(Task.title.asc())
        elif query_sort == "desc":
            tasks = Task.query.order_by(Task.title.desc())
    else:
        tasks = Task.query.all()

    tasks_data=[task.to_dict() for task in tasks]
    return jsonify(tasks_data)

@task_bp.route("/<task_id>", methods = ["GET"])
def read_one_task(task_id):

    task = validate_model(Task, task_id)
    
    return {"task":task.to_dict()}

@task_bp.route("", methods = ["POST"])
def create_task():
    try:
        request_body = request.get_json()
        new_task = Task.from_dict(request_body)
    except:
        abort(make_response({"details": "Invalid data"}, 400))
    db.session.add(new_task)
    db.session.commit()
    return {"task":new_task.to_dict()}, 201

@task_bp.route("/<task_id>", methods=["PUT"])
def update_task(task_id):
    task = validate_model(Task, task_id)
    request_body = request.get_json()
    task.title = request_body["title"]
    task.description = request_body["description"]
    db.session.commit()
    return {"task":task.to_dict()}, 200

@task_bp.route("/<task_id>", methods=["DELETE"])
def delete_task(task_id):
    task = validate_model(Task, task_id)
    db.session.delete(task)
    db.session.commit()
    return make_response(jsonify({"details": f'Task {task.task_id} "{task.title}" successfully deleted'}),200)


def send_task_to_slack_api(task):
    text = f"Someone just completed the task {task.title}"
    SLACK_API_KEY =  os.environ.get("SLACKAPI_TOKEN")
    headers = {"Authorization":SLACK_API_KEY}
    query_params = {
        "channel": "task-notifications",
        "text": text
    }
    path = "https://slack.com/api/chat.postMessage"
    response = requests.post(path, params=query_params, headers=headers)
    

@task_bp.route("/<task_id>/mark_complete", methods=["PATCH"])
def mark_task_as_complete(task_id):

    task = validate_model(Task, task_id)
    task.completed_at = datetime.now(timezone.utc)
    db.session.commit()
    send_task_to_slack_api(task)
    return {"task":task.to_dict()}, 200
    


@task_bp.route("/<task_id>/mark_incomplete", methods=["PATCH"])
def mark_task_as_incomplete(task_id):
    task = validate_model(Task, task_id)
    task.completed_at = None
    db.session.commit()
    return {"task":task.to_dict()}, 200
    