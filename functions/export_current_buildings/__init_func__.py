import azure.functions as func
from export.__init_func__ import current_buildings

def main(req: func.HttpRequest) -> func.HttpResponse:
    return current_buildings(req)
