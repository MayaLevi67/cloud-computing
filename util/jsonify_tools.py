import json
from flask import Response

def custom_jsonify(data):
    try:
        response_data = json.dumps(data, ensure_ascii=False)
        return Response(response_data, mimetype='application/json; charset=utf-8')
    except Exception as e:
        return Response(json.dumps({"error": "Failed to serialize data to JSON", "details": str(e)}),
                        mimetype='application/json; charset=utf-8'), 500
