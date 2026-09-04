$ErrorActionPreference = "Stop"

ngrok config add-authtoken 3IE2kT6G690UGhl6IcW3w6ZoXVQ_5do9TK4828d8uUSQYWZVG
Write-Host "Da cau hinh ngrok authtoken thanh cong." -ForegroundColor Green
Write-Host "Chay dashboard bang lenh: python run_with_ngrok.py" -ForegroundColor Cyan
