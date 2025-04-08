@app.route('/api/v1/tasks/<task_id>/status', methods=['GET'])
def get_find_status(task_id):
    """Retrieves the current status of a previously submitted task."""
    task = task_storage.get(task_id)
    if not task:
        return jsonify({"error": "Task not found"}), 404
    
    # Convert Task object to dictionary
    task_dict = task.dict() if hasattr(task, 'dict') else vars(task)
    return jsonify(task_dict) 