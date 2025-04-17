from fastapi import FastAPI, Request
import requests
import json

app = FastAPI()

@app.post("/send")
async def send_message(request: Request):
    data = await request.json()

    try:
        payload = {
            "queueId": 15,
            "apiKey": "testefluxIA",
            "chatId": int(data["chatId"]),  # aqui a gente força que vire número
            "text": data.get("text", ""),
            "info": False
        }

        response = requests.post(
            "https://atendmedbh.atenderbem.com/int/sendmessage",
            data=json.dumps(payload),  # força json puro
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json"
            }
        )

        return {
            "status": response.status_code,
            "response": response.text,
            "enviado": payload  # só pra debug
        }
    except Exception as e:
        return {"error": str(e)}
