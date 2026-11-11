1. Yêu cầu Môi trường
    - Python: 3.12.9 (Xem chi tiết tại tệp .python-version)
    - Hệ điều hành: Windows 10/11, macOS, hoặc Linux
    - Quản lý phiên bản: Git
2. Cài đặt & Thiết lập
    # Bước 1: Clone Repository
    - Thực hiện clone repo Git riêng tư của nhóm về máy cá nhân:
      git clone (https://github.com/NotaChtholly/2627-LTXLDL-Airbnb-Nhom02.git)
      cd 2627-LTXLDL-Airbnb-Nhom02
    # Bước 2: Tạo và kích hoạt môi trường ảo (Virtual Environment)
    - Trên Windows (PowerShell):
      python -m venv .venv
      .\.venv\Scripts\Activate.ps1
    - Trên macOS / Linux:
      python3 -m venv .venv
      source .venv/bin/activate
    # Bước 3: Cài đặt các thư viện phụ thuộc
      pip install --upgrade pip
      pip install -r requirements.txt
3. Cấu hình Biến Môi trường (API Key)
    Dự án hỗ trợ gọi AI API qua biến môi trường để trích xuất dữ liệu có cấu trúc từ đánh giá của khách hàng.
    1. Tạo tệp môi trường cục bộ từ tệp mẫu .env.example.
    2. Mở tệp và khai báo khóa API của bạn.
4. Hướng dẫn Chạy Quy trình (Pipeline)
    Quy trình được thiết kế để thực thi toàn bộ chỉ bằng 1 lệnh đơn duy nhất:
    # 1. Chạy đầy đủ từ đầu (Tải dữ liệu thô + Lọc + Kiểm tra Quotas + Mẫu LLM):
    python run_pipeline.py --config configs/melbourne.yaml
    # 2. Chạy nhanh khi đã có sẵn dữ liệu thô trong data/raw/ (Bỏ qua bước tải lại):
    python run_pipeline.py --config configs/melbourne.yaml --skip-download
    # 3. Chạy tra cứu LLM từ Bộ nhớ đệm (llm_cache.jsonl) không tốn Quota API:
    python run_pipeline.py --config configs/melbourne.yaml --skip-download --skip-llm