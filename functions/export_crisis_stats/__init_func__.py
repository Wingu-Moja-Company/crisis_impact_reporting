import json
import azure.functions as func
from export.__init_func__ import crisis_event_stats

def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        return crisis_event_stats(req)
    except Exception as exc:
        return func.HttpResponse(
            json.dumps({"error": str(exc)}),
            status_code=500,
            mimetype="application/json",
        )
