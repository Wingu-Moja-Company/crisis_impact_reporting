import azure.functions as func
from export.__init_func__ import reports

def main(req: func.HttpRequest) -> func.HttpResponse:
    return reports(req)
