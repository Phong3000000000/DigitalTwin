"""
PC Monitor - Tích hợp với BaSyx
- Gọi trực tiếp BaSyx REST API để tạo và cập nhật AAS
- Data persistence trong MongoDB
"""
import requests
import psutil
import platform
import socket
import time
import json
import base64
from datetime import datetime
import sys

# ==================== CẤU HÌNH ====================
# BaSyx Server Configuration
BASYX_URL = "http://localhost:8081"

# Device Configuration - THAY ĐỔI THEO MÁY CỦA BẠN
DEVICE_ID = "PC001"  # ID duy nhất cho máy tính này
DEVICE_NAME = "Dell Precision 5820"
LOCATION = "Workshop Floor 1"
MANUFACTURER = "Dell Technologies"

# AAS và Submodel IDs
AAS_ID = f"https://example.com/ids/aas/{DEVICE_ID}"
ASSET_ID = f"https://example.com/ids/asset/{DEVICE_ID}"
SM_NAMEPLATE_ID = f"https://example.com/ids/sm/{DEVICE_ID}_Nameplate"
SM_TECHNICAL_ID = f"https://example.com/ids/sm/{DEVICE_ID}_TechnicalData"
SM_OPERATIONAL_ID = f"https://example.com/ids/sm/{DEVICE_ID}_OperationalData"

# Update Interval
UPDATE_INTERVAL = 5  # Cập nhật mỗi 5 giây

# ==================== HELPER FUNCTIONS ====================

def base64_encode(text):
    """Encode text sang base64 URL-safe (theo BaSyx spec)"""
    encoded = base64.urlsafe_b64encode(text.encode('utf-8')).decode('utf-8')
    return encoded.rstrip('=')

def check_aas_exists():
    """Kiểm tra xem AAS đã tồn tại chưa"""
    try:
        aas_id_encoded = base64_encode(AAS_ID)
        response = requests.get(f"{BASYX_URL}/shells/{aas_id_encoded}")
        return response.status_code == 200
    except Exception as e:
        return False

def check_submodel_exists(sm_id):
    """Kiểm tra xem Submodel đã tồn tại chưa"""
    try:
        sm_id_encoded = base64_encode(sm_id)
        response = requests.get(f"{BASYX_URL}/submodels/{sm_id_encoded}")
        return response.status_code == 200
    except Exception as e:
        return False

def create_aas():
    """Tạo Asset Administration Shell"""
    print(f"\nĐang tạo AAS cho {DEVICE_ID}...")
    
    aas_data = {
        "id": AAS_ID,
        "idShort": f"{DEVICE_ID}_AAS",
        "assetInformation": {
            "assetKind": "Instance",
            "globalAssetId": ASSET_ID,
            "assetType": "Computer/Workstation"
        },
        "description": [
            {
                "language": "en",
                "text": f"Asset Administration Shell for {DEVICE_NAME}"
            },
            {
                "language": "vi",
                "text": f"Digital Twin cho máy tính {DEVICE_NAME}"
            }
        ],
        "administration": {
            "version": "1",
            "revision": "0"
        }
    }
    
    try:
        response = requests.post(
            f"{BASYX_URL}/shells",
            json=aas_data,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code in [200, 201]:
            print(f"Đã tạo AAS thành công!")
            return True
        else:
            print(f"Lỗi tạo AAS: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"Exception khi tạo AAS: {e}")
        return False

def create_nameplate_submodel():
    """Tạo Nameplate Submodel (thông tin cơ bản)"""
    print(f"Đang tạo Nameplate Submodel...")
    
    # Lấy thông tin hệ thống
    hostname = socket.gethostname()
    
    submodel_data = {
        "id": SM_NAMEPLATE_ID,
        "idShort": "Nameplate",
        "kind": "Instance",
        "description": [
            {"language": "en", "text": f"Nameplate information of {DEVICE_ID}"},
            {"language": "vi", "text": f"Thông tin nhận dạng của {DEVICE_ID}"}
        ],
        "administration": {"version": "1", "revision": "0"},
        "submodelElements": [
            {
                "idShort": "ManufacturerName",
                "modelType": "Property",
                "valueType": "xs:string",
                "value": MANUFACTURER,
                "description": [{"language": "en", "text": "Manufacturer name"}],
                "category": "PARAMETER"
            },
            {
                "idShort": "SerialNumber",
                "modelType": "Property",
                "valueType": "xs:string",
                "value": hostname,
                "description": [{"language": "en", "text": "Serial number / Hostname"}],
                "category": "PARAMETER"
            },
            {
                "idShort": "ProductDesignation",
                "modelType": "Property",
                "valueType": "xs:string",
                "value": DEVICE_NAME,
                "description": [{"language": "en", "text": "Product designation"}],
                "category": "PARAMETER"
            },
            {
                "idShort": "YearOfConstruction",
                "modelType": "Property",
                "valueType": "xs:integer",
                "value": str(datetime.now().year),
                "description": [{"language": "en", "text": "Year of construction"}],
                "category": "PARAMETER"
            },
            {
                "idShort": "Location",
                "modelType": "Property",
                "valueType": "xs:string",
                "value": LOCATION,
                "description": [{"language": "en", "text": "Physical location"}],
                "category": "PARAMETER"
            }
        ]
    }
    
    return create_submodel_generic(submodel_data, "Nameplate")

def create_technical_submodel():
    """Tạo Technical Data Submodel (thông số kỹ thuật)"""
    print(f"Đang tạo Technical Data Submodel...")
    
    # Lấy thông tin phần cứng
    cpu_count = psutil.cpu_count()
    memory_total = round(psutil.virtual_memory().total / (1024**3), 2)
    disk_total = round(psutil.disk_usage('/').total / (1024**3), 2)
    
    submodel_data = {
        "id": SM_TECHNICAL_ID,
        "idShort": "TechnicalData",
        "kind": "Instance",
        "description": [
            {"language": "en", "text": f"Technical specifications of {DEVICE_ID}"},
            {"language": "vi", "text": f"Thông số kỹ thuật của {DEVICE_ID}"}
        ],
        "administration": {"version": "1", "revision": "0"},
        "submodelElements": [
            {
                "idShort": "OperatingSystem",
                "modelType": "Property",
                "valueType": "xs:string",
                "value": f"{platform.system()} {platform.release()}",
                "description": [{"language": "en", "text": "Operating system"}]
            },
            {
                "idShort": "Processor",
                "modelType": "Property",
                "valueType": "xs:string",
                "value": platform.processor(),
                "description": [{"language": "en", "text": "CPU model"}]
            },
            {
                "idShort": "CPUCores",
                "modelType": "Property",
                "valueType": "xs:integer",
                "value": str(cpu_count),
                "description": [{"language": "en", "text": "Number of CPU cores"}]
            },
            {
                "idShort": "RAMSize",
                "modelType": "Property",
                "valueType": "xs:double",
                "value": str(memory_total),
                "description": [{"language": "en", "text": "Total RAM in GB"}]
            },
            {
                "idShort": "DiskSize",
                "modelType": "Property",
                "valueType": "xs:double",
                "value": str(disk_total),
                "description": [{"language": "en", "text": "Total disk size in GB"}]
            },
            {
                "idShort": "Architecture",
                "modelType": "Property",
                "valueType": "xs:string",
                "value": platform.machine(),
                "description": [{"language": "en", "text": "System architecture"}]
            }
        ]
    }
    
    return create_submodel_generic(submodel_data, "TechnicalData")

def create_operational_submodel():
    """Tạo Operational Data Submodel (dữ liệu vận hành)"""
    print(f"Đang tạo Operational Data Submodel...")
    
    submodel_data = {
        "id": SM_OPERATIONAL_ID,
        "idShort": "OperationalData",
        "kind": "Instance",
        "description": [
            {"language": "en", "text": f"Real-time operational data of {DEVICE_ID}"},
            {"language": "vi", "text": f"Dữ liệu vận hành thời gian thực của {DEVICE_ID}"}
        ],
        "administration": {"version": "1", "revision": "0"},
        "submodelElements": [
            {
                "idShort": "Status",
                "modelType": "Property",
                "valueType": "xs:string",
                "value": "Running",
                "description": [{"language": "en", "text": "Operational status"}],
                "category": "VARIABLE"
            },
            {
                "idShort": "CPUUsage",
                "modelType": "Property",
                "valueType": "xs:double",
                "value": "0.0",
                "description": [{"language": "en", "text": "CPU usage percentage"}],
                "category": "VARIABLE"
            },
            {
                "idShort": "RAMUsed",
                "modelType": "Property",
                "valueType": "xs:double",
                "value": "0.0",
                "description": [{"language": "en", "text": "RAM used in GB"}],
                "category": "VARIABLE"
            },
            {
                "idShort": "RAMUsagePercent",
                "modelType": "Property",
                "valueType": "xs:double",
                "value": "0.0",
                "description": [{"language": "en", "text": "RAM usage percentage"}],
                "category": "VARIABLE"
            },
            {
                "idShort": "DiskUsed",
                "modelType": "Property",
                "valueType": "xs:double",
                "value": "0.0",
                "description": [{"language": "en", "text": "Disk used in GB"}],
                "category": "VARIABLE"
            },
            {
                "idShort": "DiskUsagePercent",
                "modelType": "Property",
                "valueType": "xs:double",
                "value": "0.0",
                "description": [{"language": "en", "text": "Disk usage percentage"}],
                "category": "VARIABLE"
            },
            {
                "idShort": "Uptime",
                "modelType": "Property",
                "valueType": "xs:integer",
                "value": "0",
                "description": [{"language": "en", "text": "System uptime in seconds"}],
                "category": "PARAMETER"
            },
            {
                "idShort": "LastUpdate",
                "modelType": "Property",
                "valueType": "xs:dateTime",
                "value": datetime.now().isoformat(),
                "description": [{"language": "en", "text": "Last update timestamp"}],
                "category": "PARAMETER"
            }
        ]
    }
    
    return create_submodel_generic(submodel_data, "OperationalData")

def create_submodel_generic(submodel_data, name):
    """Helper function để tạo Submodel"""
    try:
        response = requests.post(
            f"{BASYX_URL}/submodels",
            json=submodel_data,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code in [200, 201]:
            print(f"Đã tạo {name} Submodel thành công!")
            return True
        else:
            print(f"Lỗi tạo {name} Submodel: {response.status_code}")
            return False
    except Exception as e:
        print(f"Exception khi tạo {name} Submodel: {e}")
        return False

def link_submodel_to_aas(sm_id):
    """Gắn Submodel vào AAS"""
    aas_id_encoded = base64_encode(AAS_ID)
    
    submodel_ref = {
        "type": "ExternalReference",
        "keys": [
            {
                "type": "Submodel",
                "value": sm_id
            }
        ]
    }
    
    try:
        response = requests.post(
            f"{BASYX_URL}/shells/{aas_id_encoded}/submodel-refs",
            json=submodel_ref,
            headers={"Content-Type": "application/json"}
        )
        return response.status_code in [200, 201, 204]
    except Exception as e:
        print(f"Lỗi link Submodel: {e}")
        return False

def initialize_digital_twin():
    """Khởi tạo Digital Twin nếu chưa tồn tại"""
    print("\n" + "="*70)
    print("🚀 KHỞI TẠO DIGITAL TWIN")
    print("="*70)
    
    # Kiểm tra và tạo AAS
    if not check_aas_exists():
        if not create_aas():
            return False
    else:
        print(f"✓ AAS {DEVICE_ID} đã tồn tại")
    
    # Kiểm tra và tạo các Submodels
    submodels = [
        (SM_NAMEPLATE_ID, create_nameplate_submodel, "Nameplate"),
        (SM_TECHNICAL_ID, create_technical_submodel, "TechnicalData"),
        (SM_OPERATIONAL_ID, create_operational_submodel, "OperationalData")
    ]
    
    for sm_id, create_func, name in submodels:
        if not check_submodel_exists(sm_id):
            if not create_func():
                print(f"Không thể tạo {name} Submodel")
                return False
            # Link Submodel vào AAS
            if not link_submodel_to_aas(sm_id):
                print(f"Không thể link {name} Submodel vào AAS")
        else:
            print(f"✓ {name} Submodel đã tồn tại")
    
    print("="*70)
    print("Digital Twin đã sẵn sàng!")
    print("="*70)
    return True

def update_property(sm_id, property_path, value):
    """Cập nhật giá trị của một Property trong Submodel"""
    try:
        sm_id_encoded = base64_encode(sm_id)
        
        # PUT endpoint để update toàn bộ property (theo BaSyx API spec)
        url = f"{BASYX_URL}/submodels/{sm_id_encoded}/submodel-elements/{property_path}"
        
        # Lấy property hiện tại để giữ nguyên structure
        get_response = requests.get(url)
        if get_response.status_code == 200:
            property_data = get_response.json()
            # Chỉ update value
            property_data["value"] = str(value)
            
            # PUT lại toàn bộ property
            response = requests.put(
                url,
                json=property_data,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code not in [200, 204]:
                print(f"  Update {property_path} failed: {response.status_code}")
            
            return response.status_code in [200, 204]
        else:
            print(f"  Get {property_path} failed: {get_response.status_code}")
            return False
        
    except Exception as e:
        print(f"Lỗi update property {property_path}: {e}")
        return False

def collect_and_update_operational_data():
    """Thu thập và cập nhật dữ liệu vận hành"""
    try:
        # Thu thập dữ liệu
        cpu_usage = round(psutil.cpu_percent(interval=1), 2)
        
        memory = psutil.virtual_memory()
        memory_used_gb = round(memory.used / (1024**3), 2)
        memory_percent = round(memory.percent, 2)
        
        disk = psutil.disk_usage('/')
        disk_used_gb = round(disk.used / (1024**3), 2)
        disk_percent = round(disk.percent, 2)
        
        uptime = int(time.time() - psutil.boot_time())
        
        # Cập nhật tất cả properties
        updates = [
            ("CPUUsage", cpu_usage),
            ("RAMUsed", memory_used_gb),
            ("RAMUsagePercent", memory_percent),
            ("DiskUsed", disk_used_gb),
            ("DiskUsagePercent", disk_percent),
            ("Uptime", uptime),
            ("LastUpdate", datetime.now().isoformat())
        ]
        
        success_count = 0
        for prop_name, value in updates:
            if update_property(SM_OPERATIONAL_ID, prop_name, value):
                success_count += 1
        
        # Hiển thị thông tin
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Updated {success_count}/{len(updates)} properties:")
        print(f"   CPU: {cpu_usage}% | RAM: {memory_percent}% ({memory_used_gb}GB) | "
              f"Disk: {disk_percent}% ({disk_used_gb}GB) | Uptime: {uptime//3600}h")
        
        return success_count > 0
        
    except Exception as e:
        print(f"Lỗi collect và update: {e}")
        return False

# ==================== MAIN PROGRAM ====================

def main():
    """Main loop"""
    print("\n" + "="*70)
    print(f"PC MONITOR - BASYX INTEGRATED (Direct API)")
    print("="*70)
    print(f"Device ID: {DEVICE_ID}")
    print(f"Device Name: {DEVICE_NAME}")
    print(f"Location: {LOCATION}")
    print(f"BaSyx Server: {BASYX_URL}")
    print("="*70)
    
    # Kiểm tra kết nối BaSyx Server
    print("\nĐang kiểm tra kết nối BaSyx Server...")
    try:
        response = requests.get(f"{BASYX_URL}/shells", timeout=5)
        if response.status_code == 200:
            print("Kết nối BaSyx Server thành công!")
        else:
            print(f"BaSyx Server phản hồi: {response.status_code}")
    except Exception as e:
        print(f"Không thể kết nối BaSyx Server: {e}")
        print("Hãy chắc chắn rằng docker-compose đã chạy: docker-compose up -d")
        sys.exit(1)
    
    # Khởi tạo Digital Twin
    if not initialize_digital_twin():
        print("Không thể khởi tạo Digital Twin. Thoát...")
        sys.exit(1)
    
    print(f"Bắt đầu giám sát và cập nhật real-time (mỗi {UPDATE_INTERVAL}s)")
    print("   Nhấn Ctrl+C để dừng\n")
    
    try:
        while True:
            collect_and_update_operational_data()
            time.sleep(UPDATE_INTERVAL)
            
    except KeyboardInterrupt:
        print("\n\n⏹ Đang dừng PC Monitor...")
        
        # Cập nhật status = "Stopped" trước khi thoát
        update_property(SM_OPERATIONAL_ID, "Status", "Stopped")
        print("✓ Đã cập nhật status = Stopped")
        print("✓ Đã dừng PC Monitor\n")
        
    except Exception as e:
        print(f"\nLỗi không mong muốn: {e}")

if __name__ == "__main__":
    main()
