# GovEase AI Workflow Chatbot

Demo chatbot nho gon cho 2 nhom thu tuc:

- Dang ky khai sinh
- Dang ky cu tru (thuong tru, tam tru, tam vang, luu tru)

## Chay local

1. Kich hoat virtualenv trong `data-pipeline/.venv`
2. Dat bien moi truong `OPENAI_API_KEY`
3. Chay:

```powershell
python app.py
```

Mac dinh app chay tai `http://127.0.0.1:8010`

## Ghi chu

- Model mac dinh: `gpt-5-mini`
- Neu khong co API key, app van chay bang bo parser du phong theo keyword
- Backend giu session state va decision tree
- LLM chi dung de hieu cau tra loi tu nhien cua user va map vao slot
