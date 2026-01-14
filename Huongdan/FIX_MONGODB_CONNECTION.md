# ⚠️ LƯU Ý QUAN TRỌNG VỀ CONNECTION STRING MONGODB

## VẤN ĐỀ

Connection string của bạn có password chứa ký tự đặc biệt `@`:
```
mongodb+srv://sa:Admin@123@cluster0.wrpp0cf.mongodb.net/DigitalTwinDB
                      ↑
                   Ký tự @ này gây lỗi!
```

MongoDB parser không phân biệt được:
- `@` trong password (`Admin@123`)
- `@` phân cách username/password với hostname

## GIẢI PHÁP

### Cách 1: Encode Password (KHUYẾN NGHỊ)

Sử dụng URL encoding cho password:

**Password gốc:** `Admin@123`  
**Password sau encode:** `Admin%40123` (@ → %40)

**Connection string đúng:**
```
mongodb+srv://sa:Admin%40123@cluster0.wrpp0cf.mongodb.net/DigitalTwinDB
```

### Cách 2: Đổi Password (Đơn giản hơn)

Vào MongoDB Atlas → Database Access → Edit User → Change Password

**Đổi thành password không có ký tự đặc biệt:**
- ❌ `Admin@123` (có @)
- ❌ `Pass#word` (có #)
- ❌ `Test$123` (có $)
- ✅ `AdminPassword123` (không có ký tự đặc biệt)
- ✅ `Admin123456` (không có ký tự đặc biệt)

**Connection string mới:**
```
mongodb+srv://sa:Admin123456@cluster0.wrpp0cf.mongodb.net/DigitalTwinDB
```

## CẬP NHẬT SAU KHI SỬA

Cần sửa connection string ở **3 vị trí:**

### 1. docker-compose.yml (2 nơi)

```yaml
aas-registry:
  environment:
    - BASYX_MONGODB_CONNECTIONURL=mongodb+srv://sa:Admin%40123@cluster0.wrpp0cf.mongodb.net/DigitalTwinDB

aas-server:
  environment:
    - BASYX_MONGODB_CONNECTIONURL=mongodb+srv://sa:Admin%40123@cluster0.wrpp0cf.mongodb.net/DigitalTwinDB
```

### 2. databridge.py

```python
MONGODB_URI = "mongodb+srv://sa:Admin%40123@cluster0.wrpp0cf.mongodb.net/DigitalTwinDB"
```

### 3. check_system.py

```python
MONGODB_URI = "mongodb+srv://sa:Admin%40123@cluster0.wrpp0cf.mongodb.net/DigitalTwinDB"
```

## BẢNG ENCODE CÁC KÝ TỰ ĐẶC BIỆT

| Ký tự | URL Encoded |
|-------|-------------|
| `@`   | `%40`       |
| `#`   | `%23`       |
| `$`   | `%24`       |
| `%`   | `%25`       |
| `&`   | `%26`       |
| `+`   | `%2B`       |
| `/`   | `%2F`       |
| `=`   | `%3D`       |
| `?`   | `%3F`       |

## TEST CONNECTION

### Python
```python
from pymongo import MongoClient
from urllib.parse import quote_plus

username = "sa"
password = "Admin@123"

# Encode password
password_encoded = quote_plus(password)
print(f"Password encoded: {password_encoded}")  # Admin%40123

# Connection string
uri = f"mongodb+srv://{username}:{password_encoded}@cluster0.wrpp0cf.mongodb.net/DigitalTwinDB"

# Test
client = MongoClient(uri)
print("✓ Kết nối thành công!")
print(client.list_database_names())
```

### MongoDB Compass

**Connection String:**
```
mongodb+srv://sa:Admin%40123@cluster0.wrpp0cf.mongodb.net/DigitalTwinDB
```

## SAU KHI SỬA

1. Sửa 3 files (docker-compose.yml, databridge.py, check_system.py)
2. Restart containers:
   ```powershell
   docker-compose down
   docker-compose up -d
   ```
3. Test lại:
   ```powershell
   python check_system.py
   ```

## KHUYẾN NGHỊ

🔐 **Best Practice:**
- Không dùng ký tự đặc biệt trong password
- Hoặc luôn encode password khi sử dụng trong URL
- Sử dụng `.env` file để lưu credentials (không commit lên Git)

**Ví dụ .env file:**
```env
MONGODB_USERNAME=sa
MONGODB_PASSWORD=Admin123456
MONGODB_CLUSTER=cluster0.wrpp0cf.mongodb.net
MONGODB_DATABASE=DigitalTwinDB
```

**Load trong Python:**
```python
import os
from dotenv import load_dotenv

load_dotenv()

MONGODB_URI = f"mongodb+srv://{os.getenv('MONGODB_USERNAME')}:{os.getenv('MONGODB_PASSWORD')}@{os.getenv('MONGODB_CLUSTER')}/{os.getenv('MONGODB_DATABASE')}"
```
