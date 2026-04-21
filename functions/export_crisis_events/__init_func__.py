import azure.functions as func
from export.__init_func__ import crisis_events

def main(req: func.HttpRequest) -> func.HttpResponse:
    return crisis_events(req)
