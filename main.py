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
            "chatId": int(data["chatId"]),
            "text": data.get("text", ""),
            "info": "false"  # como string, pq em x-www-form-urlencoded é tudo string
        }

        # Envia como form-urlencoded
        response = requests.post(
            "https://atendmedbh.atenderbem.com/int/sendmessagetochat",
            data=payload,  # <- aqui é o pulo do gato
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json"
            }
        )

        return {
            "status": response.status_code,
            "response": response.text,
            "enviado": payload
        }

    except Exception as e:
        return {"error": str(e)}
