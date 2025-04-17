from fastapi import FastAPI, Request
import requests

app = FastAPI()

@app.post("/send")
async def send_message(request: Request):
    data = await request.json()

    try:
        # Converte "true"/"false" string para booleano real
        info_value = data.get("info", "false")
        if isinstance(info_value, str):
            info_value = info_value.strip().lower() == "true"

        payload = {
            "queueId": 15,
            "apiKey": "testefluxIA",
            "chatId": int(data["chatId"]),  # Certifica que é número
            "text": data.get("text", ""),
            "info": info_value  # <-- Agora vem do request
        }

        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

        response = requests.post(
            "https://atendmedbh.atenderbem.com/int/sendmessagetochat",
            json=payload,
            headers=headers
        )

        return {
            "status": response.status_code,
            "response": response.text,
            "enviado": payload
        }

    except Exception as e:
        return {"error": str(e)}

