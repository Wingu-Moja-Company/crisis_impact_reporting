import azure.functions as func
from main import telegram_webhook

async def main(req: func.HttpRequest) -> func.HttpResponse:
    return await telegram_webhook(req)
