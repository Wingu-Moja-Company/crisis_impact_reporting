import azure.functions as func
from admin.events import update_event

def main(req: func.HttpRequest) -> func.HttpResponse:
    return update_event(req)
