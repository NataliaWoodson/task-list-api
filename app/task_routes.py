from app import db
import requests
import json
from app.models.task import Task
import os
from datetime import datetime
from flask import Blueprint, jsonify, abort, make_response, request


tasks_bp = Blueprint("tasks_bp", __name__, url_prefix="/tasks")

# POST /tasks
@tasks_bp.route("", methods=['POST'])
def create_task():
    request_body = request.get_json()
    completed = request_body["completed_at"] if "completed_at" in request_body else None
    try:
        new_task = Task(title=request_body["title"],
                    description=request_body["description"],
                    completed_at = completed
                    ) 
    except KeyError as err:
        return make_response({"details": "Invalid data"}, 400)

    
    db.session.add(new_task)
    db.session.commit()

    return make_response({"task": {
                    "id": new_task.task_id,
                    "title": new_task.title,
                    "description": new_task.description,
                    "is_complete": new_task.is_complete()}} , 201)

# GET /tasks
@tasks_bp.route("", methods=["GET"])
def read_all_tasks():
    tasks_response = []
    sort_param = request.args.get("sort")
    if sort_param == "desc":
        tasks = Task.query.order_by(Task.title.desc())
    elif sort_param == "asc":
        tasks = Task.query.order_by(Task.title.asc())
    else:
        tasks = Task.query.all()

    for task in tasks:
        tasks_response.append(
            {
                "id": task.task_id,
                "title": task.title,
                "description": task.description,
                "is_complete": task.is_complete()
            }
        )
    return jsonify(tasks_response)

# GET /tasks/<task_id>
@tasks_bp.route("/<task_id>", methods=["GET"])
def read_one_task(task_id):
    task = validate_task(task_id)

    return {"task": {
            "id": task.task_id,
            "title": task.title,
            "description": task.description,
            "is_complete": task.is_complete()
    }
        }

# PUT /tasks/<task_id> 
@tasks_bp.route("/<task_id>", methods=["PUT"])
def replace_task_by_id(task_id):
    task = validate_task(task_id)
    request_body = request.get_json()

    task.title = request_body["title"]
    task.description = request_body["description"]
   
    db.session.commit()

    return {"task": {
            "id": task.task_id,
            "title": task.title,
            "description": task.description,
            "is_complete": task.is_complete()
    }
        }

# PATCH /tasks/<task_id>/mark_complete
@tasks_bp.route("/<task_id>/mark_complete", methods=["PATCH"])
def update_task_with_id(task_id):
    task = validate_task(task_id)
    task.completed_at = datetime.utcnow()

    slack_token = os.environ.get("SLACK_BOT_TOKEN")
    channel = "#task-notifications"
    
    r = requests.post('https://slack.com/api/chat.postMessage', {
        'token': slack_token,
        'channel': channel,
        'text': f'Someone just completed {task.title}'
        }).json()	
    
    db.session.commit()
    return {"task": {
            "id": task.task_id,
            "title": task.title,
            "description": task.description,
            "is_complete": task.is_complete()
    }
        }

# PATCH /tasks/<task_id>/mark_incomplete
@tasks_bp.route("/<task_id>/mark_incomplete", methods=["PATCH"])
def update_incomplete_task(task_id):
    task = validate_task(task_id)

    task.completed_at = None
    
    db.session.commit()
    return {"task": {
        "id": task.task_id,
        "title": task.title,
        "description": task.description,
        "is_complete": task.is_complete()
}
    }

@tasks_bp.route("/<task_id>", methods=['DELETE'])
def delete_task(task_id):
    task = validate_task(task_id)

    db.session.delete(task)
    db.session.commit()

    return make_response({"details": f'Task {task.task_id} "{task.title}" successfully deleted'})


def validate_task(task_id):
    try:
        task_id = int(task_id)
    except:
        abort(make_response({"message":f"task {task_id} invalid"}, 400))

    task = Task.query.get(task_id)

    if not task:
        abort(make_response({"message":f"task {task_id} not found"}, 404))

    return task