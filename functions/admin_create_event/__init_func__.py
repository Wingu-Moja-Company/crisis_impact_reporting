import azure.functions as func
from admin.events import create_event

def main(req: func.HttpRequest) -> func.HttpResponse:
    return create_event(req)
