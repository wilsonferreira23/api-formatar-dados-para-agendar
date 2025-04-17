from fastapi import FastAPI, Request
import requests

app = FastAPI()

@app.post("/send")
async def send_message(request: Request):
    data = await request.json()

    try:
        payload = {
            "queueId": 15,
            "apiKey": "testefluxIA",
            "chatId": int(data["chatId"]),  # Certifica que é número
            "text": data.get("text", ""),
            "info": False  # <-- Aqui é booleano real, não string
        }

        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

        response = requests.post(
            "https://atendmedbh.atenderbem.com/int/sendmessagetochat",
            json=payload,  # <-- Envia como JSON real
            headers=headers
        )

        return {
            "status": response.status_code,
            "response": response.text,
            "enviado": payload
        }

    except Exception as e:
        return {"error": str(e)}
