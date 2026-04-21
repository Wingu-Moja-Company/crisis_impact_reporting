import azure.functions as func
from export.__init_func__ import cap_feed

def main(req: func.HttpRequest) -> func.HttpResponse:
    return cap_feed(req)
