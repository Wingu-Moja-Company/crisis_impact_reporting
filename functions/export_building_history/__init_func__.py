import azure.functions as func
from export.__init_func__ import building_history

def main(req: func.HttpRequest) -> func.HttpResponse:
    return building_history(req)
