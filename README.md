# GeoAI Hydraulic Dashboard

Dashboard phân tích bảng kết quả nút/hố ga

## Cấu trúc

```text
hydraulic-dashboard/
├── api.py
├── run_with_ngrok.py
├── setup_ngrok.ps1
├── data/Bang thong ke.csv
├── templates/
├── static/css/
├── static/js/
├── tests/test_api.py
└── requirements.txt
```

## Chạy nội bộ

```powershell
python api.py
```

Mở `http://127.0.0.1:8000`.
# Chạy bằng ngrok (Windows PowerShell)
https://sermon-strict-handbag.ngrok-free.dev/


Quy tắc cảnh báo: Nguy cấp khi có tràn/ngập hoặc HGL vượt nắp; Cảnh báo khi tỷ lệ đầy ≥ 75% hoặc biên HGL < 0,5 m; các trường hợp còn lại là Bình thường. Cột `Depth (Surcharged)` trong dữ liệu nguồn có cùng giá trị 0,5 m cho toàn bộ 139 nút nên không được dùng riêng để phân loại.
