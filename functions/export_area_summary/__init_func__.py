import azure.functions as func
from export.__init_func__ import area_summary

def main(req: func.HttpRequest) -> func.HttpResponse:
    return area_summary(req)
