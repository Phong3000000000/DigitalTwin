"""
Device Manager Web Application
- Web interface để quản lý và giám sát thiết bị
- Sử dụng API từ BaSyx Java server
- Hiển thị trạng thái on/off của thiết bị
- Hỗ trợ dynamic templates cho nhiều domain khác nhau
"""
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import requests
import base64
from datetime import datetime, timedelta
import json
import os

app = Flask(__name__)
CORS(app)

# Configuration
BASYX_URL = "http://localhost:8081"
DEVICE_TIMEOUT = 60  # Thiết bị được coi là offline sau 60 giây không cập nhật

# Load templates
TEMPLATES_FILE = os.path.join(os.path.dirname(__file__), 'device_templates.json')
with open(TEMPLATES_FILE, 'r', encoding='utf-8') as f:
    DEVICE_TEMPLATES = json.load(f)

def base64_encode(text):
    """Encode text sang base64 URL-safe"""
    encoded = base64.urlsafe_b64encode(text.encode('utf-8')).decode('utf-8')
    return encoded.rstrip('=')

def base64_decode(encoded_text):
    """Decode base64 URL-safe về text"""
    # Thêm padding nếu cần
    padding = 4 - len(encoded_text) % 4
    if padding != 4:
        encoded_text += '=' * padding
    decoded = base64.urlsafe_b64decode(encoded_text.encode('utf-8')).decode('utf-8')
    return decoded

# ==================== API Endpoints ====================

@app.route('/')
def index():
    """Trang chủ - Advanced Dashboard với multi-domain support"""
    return render_template('dashboard_advanced.html')

@app.route('/simple')
def simple_dashboard():
    """Dashboard đơn giản (legacy)"""
    return render_template('dashboard.html')

@app.route('/api/templates', methods=['GET'])
def get_templates():
    """Lấy danh sách templates"""
    return jsonify(DEVICE_TEMPLATES), 200

@app.route('/api/devices', methods=['GET'])
def get_all_devices():
    """Lấy danh sách tất cả thiết bị từ BaSyx server"""
    try:
        # Lấy tất cả AAS từ server
        response = requests.get(f"{BASYX_URL}/shells")
        
        if response.status_code != 200:
            return jsonify({"error": "Cannot connect to BaSyx server"}), 500
        
        aas_list = response.json().get('result', [])
        devices = []
        
        for aas in aas_list:
            device_id = aas.get('idShort', 'Unknown')
            aas_id = aas.get('id', '')
            
            # Lấy thông tin operational data để xác định trạng thái
            operational_sm_id = f"https://example.com/ids/sm/{device_id.replace('_AAS', '')}_OperationalData"
            status = check_device_status(operational_sm_id)
            
            # Lấy thông tin nameplate
            nameplate_info = get_nameplate_info(device_id.replace('_AAS', ''))
            
            device_info = {
                "id": device_id.replace('_AAS', ''),
                "name": nameplate_info.get('DeviceName', 'Unknown Device'),
                "manufacturer": nameplate_info.get('ManufacturerName', 'Unknown'),
                "location": nameplate_info.get('Location', 'Unknown'),
                "status": status['status'],
                "lastUpdate": status['lastUpdate'],
                "aasId": aas_id
            }
            devices.append(device_info)
        
        return jsonify({"devices": devices, "total": len(devices)}), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/devices/<device_id>', methods=['GET'])
def get_device_detail(device_id):
    """Lấy thông tin chi tiết của một thiết bị"""
    try:
        aas_id = f"https://example.com/ids/aas/{device_id}"
        aas_id_encoded = base64_encode(aas_id)
        
        # Lấy AAS
        response = requests.get(f"{BASYX_URL}/shells/{aas_id_encoded}")
        if response.status_code != 200:
            return jsonify({"error": "Device not found"}), 404
        
        aas_data = response.json()
        
        # Lấy các submodels
        nameplate = get_nameplate_info(device_id)
        technical = get_technical_info(device_id)
        operational = get_operational_info(device_id)
        
        device_detail = {
            "id": device_id,
            "aas": aas_data,
            "nameplate": nameplate,
            "technical": technical,
            "operational": operational,
            "status": check_device_status(f"https://example.com/ids/sm/{device_id}_OperationalData")
        }
        
        return jsonify(device_detail), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/devices', methods=['POST'])
def create_device():
    """Tạo thiết bị mới với dynamic template"""
    try:
        data = request.json
        device_id = data.get('deviceId')
        template_name = data.get('template', 'custom')
        asset_type = data.get('assetType', 'Unknown')
        
        # Lấy dữ liệu từ các submodels
        nameplate_data = data.get('nameplate', {})
        technical_data = data.get('technicalData', {})
        operational_data = data.get('operationalData', {})
        
        if not device_id:
            return jsonify({"error": "deviceId is required"}), 400
        
        device_name = nameplate_data.get('DeviceName', 'Unknown Device')
        
        # Tạo AAS
        aas_id = f"https://example.com/ids/aas/{device_id}"
        asset_id = f"https://example.com/ids/asset/{device_id}"
        
        aas_data = {
            "id": aas_id,
            "idShort": f"{device_id}_AAS",
            "assetInformation": {
                "assetKind": "Instance",
                "globalAssetId": asset_id,
                "assetType": asset_type
            },
            "description": [
                {
                    "language": "en",
                    "text": f"Asset Administration Shell for {device_name}"
                }
            ]
        }
        
        response = requests.post(
            f"{BASYX_URL}/shells",
            json=aas_data,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code not in [200, 201]:
            return jsonify({"error": f"Failed to create AAS: {response.text}"}), 500
        
        # Tạo các Submodels với dữ liệu động và link vào AAS
        submodels_created = []
        
        if nameplate_data:
            sm_id = f"https://example.com/ids/sm/{device_id}_Nameplate"
            if create_dynamic_submodel(device_id, "Nameplate", nameplate_data, template_name):
                if link_submodel_to_aas(aas_id, sm_id):
                    submodels_created.append("Nameplate")
        
        if technical_data:
            sm_id = f"https://example.com/ids/sm/{device_id}_TechnicalData"
            if create_dynamic_submodel(device_id, "TechnicalData", technical_data, template_name):
                if link_submodel_to_aas(aas_id, sm_id):
                    submodels_created.append("TechnicalData")
        
        if operational_data:
            sm_id = f"https://example.com/ids/sm/{device_id}_OperationalData"
            if create_dynamic_submodel(device_id, "OperationalData", operational_data, template_name):
                if link_submodel_to_aas(aas_id, sm_id):
                    submodels_created.append("OperationalData")
        else:
            # Tạo operational data mặc định với timestamp
            sm_id = f"https://example.com/ids/sm/{device_id}_OperationalData"
            default_operational = {"Timestamp": datetime.utcnow().isoformat() + "Z"}
            if create_dynamic_submodel(device_id, "OperationalData", default_operational, template_name):
                if link_submodel_to_aas(aas_id, sm_id):
                    submodels_created.append("OperationalData")
        
        return jsonify({
            "message": "Device created successfully",
            "deviceId": device_id,
            "aasId": aas_id,
            "submodels": submodels_created
        }), 201
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/devices/<device_id>', methods=['DELETE'])
def delete_device(device_id):
    """Xóa thiết bị"""
    try:
        aas_id = f"https://example.com/ids/aas/{device_id}"
        aas_id_encoded = base64_encode(aas_id)

        response = requests.delete(f"{BASYX_URL}/shells/{aas_id_encoded}")

        # Accept both 200 OK and 204 No Content as successful deletion
        if response.status_code in [200, 204]:
            # Xóa các submodels
            delete_submodels(device_id)
            return jsonify({"message": "Device deleted successfully"}), 200
        else:
            return jsonify({"error": f"Failed to delete device: {response.text}"}), response.status_code

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/devices/<device_id>/operational', methods=['PUT', 'PATCH'])
def update_operational_data(device_id):
    """Cập nhật operational data của thiết bị"""
    try:
        data = request.json
        sm_id = f"https://example.com/ids/sm/{device_id}_OperationalData"
        sm_id_encoded = base64_encode(sm_id)
        
        # Tự động thêm Timestamp nếu không có
        if 'Timestamp' not in data:
            data['Timestamp'] = datetime.utcnow().isoformat() + "Z"
        
        # Cập nhật từng property
        updated = []
        failed = []
        
        for key, value in data.items():
            try:
                # Lấy property hiện tại
                url = f"{BASYX_URL}/submodels/{sm_id_encoded}/submodel-elements/{key}"
                get_response = requests.get(url)
                
                if get_response.status_code == 200:
                    property_data = get_response.json()
                    property_data["value"] = str(value)
                    
                    # PUT lại property
                    put_response = requests.put(
                        url,
                        json=property_data,
                        headers={"Content-Type": "application/json"}
                    )
                    
                    if put_response.status_code in [200, 204]:
                        updated.append(key)
                    else:
                        failed.append(key)
                else:
                    failed.append(key)
            except Exception as e:
                failed.append(key)
        
        return jsonify({
            "message": f"Updated {len(updated)}/{len(data)} properties",
            "updated": updated,
            "failed": failed
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ==================== Helper Functions ====================

def check_device_status(submodel_id):
    """Kiểm tra trạng thái thiết bị dựa trên operational data"""
    try:
        sm_id_encoded = base64_encode(submodel_id)
        response = requests.get(f"{BASYX_URL}/submodels/{sm_id_encoded}")
        
        if response.status_code != 200:
            return {"status": "unknown", "lastUpdate": None}
        
        submodel_data = response.json()
        
        # Tìm property Timestamp
        timestamp = None
        for element in submodel_data.get('submodelElements', []):
            if element.get('idShort') == 'Timestamp':
                timestamp = element.get('value')
                break
        
        if not timestamp:
            return {"status": "unknown", "lastUpdate": None}
        
        # Parse timestamp và kiểm tra
        try:
            last_update = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            now = datetime.now(last_update.tzinfo)
            diff_seconds = (now - last_update).total_seconds()
            
            if diff_seconds < DEVICE_TIMEOUT:
                status = "online"
            else:
                status = "offline"
            
            return {
                "status": status,
                "lastUpdate": timestamp,
                "secondsSinceUpdate": int(diff_seconds)
            }
        except:
            return {"status": "unknown", "lastUpdate": timestamp}
            
    except Exception as e:
        return {"status": "error", "lastUpdate": None, "error": str(e)}

def get_nameplate_info(device_id):
    """Lấy thông tin nameplate"""
    try:
        sm_id = f"https://example.com/ids/sm/{device_id}_Nameplate"
        sm_id_encoded = base64_encode(sm_id)
        response = requests.get(f"{BASYX_URL}/submodels/{sm_id_encoded}")
        
        if response.status_code != 200:
            return {}
        
        submodel_data = response.json()
        info = {}
        
        for element in submodel_data.get('submodelElements', []):
            id_short = element.get('idShort')
            value = element.get('value')
            if id_short and value:
                info[id_short] = value
        
        return info
    except:
        return {}

def get_technical_info(device_id):
    """Lấy thông tin technical"""
    try:
        sm_id = f"https://example.com/ids/sm/{device_id}_TechnicalData"
        sm_id_encoded = base64_encode(sm_id)
        response = requests.get(f"{BASYX_URL}/submodels/{sm_id_encoded}")
        
        if response.status_code != 200:
            return {}
        
        submodel_data = response.json()
        info = {}
        
        for element in submodel_data.get('submodelElements', []):
            id_short = element.get('idShort')
            value = element.get('value')
            if id_short and value:
                info[id_short] = value
        
        return info
    except:
        return {}

def get_operational_info(device_id):
    """Lấy thông tin operational"""
    try:
        sm_id = f"https://example.com/ids/sm/{device_id}_OperationalData"
        sm_id_encoded = base64_encode(sm_id)
        response = requests.get(f"{BASYX_URL}/submodels/{sm_id_encoded}")
        
        if response.status_code != 200:
            return {}
        
        submodel_data = response.json()
        info = {}
        
        for element in submodel_data.get('submodelElements', []):
            id_short = element.get('idShort')
            value = element.get('value')
            if id_short and value:
                info[id_short] = value
        
        return info
    except:
        return {}

def link_submodel_to_aas(aas_id, sm_id):
    """Gắn Submodel vào AAS (tham khảo từ pc_monitor_integrated.py)"""
    try:
        aas_id_encoded = base64_encode(aas_id)
        
        submodel_ref = {
            "type": "ExternalReference",
            "keys": [
                {
                    "type": "Submodel",
                    "value": sm_id
                }
            ]
        }
        
        response = requests.post(
            f"{BASYX_URL}/shells/{aas_id_encoded}/submodel-refs",
            json=submodel_ref,
            headers={"Content-Type": "application/json"}
        )
        
        return response.status_code in [200, 201, 204]
    except Exception as e:
        print(f"Lỗi link Submodel {sm_id} vào AAS: {e}")
        return False

def create_dynamic_submodel(device_id, submodel_type, data_dict, template_name):
    """Tạo Submodel động từ template và data"""
    sm_id = f"https://example.com/ids/sm/{device_id}_{submodel_type}"
    
    # Lấy template definition nếu có
    template_fields = []
    if template_name in DEVICE_TEMPLATES.get('templates', {}):
        template = DEVICE_TEMPLATES['templates'][template_name]
        if submodel_type == "Nameplate":
            template_fields = template.get('nameplate', [])
        elif submodel_type == "TechnicalData":
            template_fields = template.get('technicalData', [])
        elif submodel_type == "OperationalData":
            template_fields = template.get('operationalData', [])
    
    # Tạo submodel elements từ data
    submodel_elements = []
    
    for key, value in data_dict.items():
        # Tìm field definition trong template
        field_def = next((f for f in template_fields if f.get('idShort') == key), None)
        
        if field_def:
            element = {
                "idShort": key,
                "modelType": "Property",
                "valueType": field_def.get('valueType', 'xs:string'),
                "value": str(value)
            }
            
            # Thêm description nếu có tooltip
            if field_def.get('tooltip'):
                element["description"] = [{
                    "language": "en",
                    "text": field_def['tooltip']
                }]
            
            # Thêm category nếu có
            if field_def.get('category'):
                element["category"] = field_def['category']
        else:
            # Không có trong template, tự động detect type
            element = {
                "idShort": key,
                "modelType": "Property",
                "valueType": detect_value_type(value),
                "value": str(value)
            }
        
        submodel_elements.append(element)
    
    # Tạo submodel data
    submodel_data = {
        "id": sm_id,
        "idShort": f"{device_id}_{submodel_type}",
        "kind": "Instance",
        "submodelElements": submodel_elements
    }
    
    # Thêm semantic ID cho Nameplate
    if submodel_type == "Nameplate":
        submodel_data["semanticId"] = {
            "type": "ExternalReference",
            "keys": [{
                "type": "GlobalReference",
                "value": "https://admin-shell.io/zvei/nameplate/1/0/Nameplate"
            }]
        }
    
    try:
        response = requests.post(
            f"{BASYX_URL}/submodels",
            json=submodel_data,
            headers={"Content-Type": "application/json"}
        )
        return response.status_code in [200, 201]
    except Exception as e:
        print(f"Error creating {submodel_type}: {e}")
        return False

def detect_value_type(value):
    """Tự động detect kiểu dữ liệu"""
    if isinstance(value, bool):
        return "xs:boolean"
    elif isinstance(value, int):
        return "xs:integer"
    elif isinstance(value, float):
        return "xs:double"
    else:
        return "xs:string"

def delete_submodels(device_id):
    """Xóa các submodels của device"""
    submodel_ids = [
        f"https://example.com/ids/sm/{device_id}_Nameplate",
        f"https://example.com/ids/sm/{device_id}_TechnicalData",
        f"https://example.com/ids/sm/{device_id}_OperationalData"
    ]
    
    for sm_id in submodel_ids:
        try:
            sm_id_encoded = base64_encode(sm_id)
            requests.delete(f"{BASYX_URL}/submodels/{sm_id_encoded}")
        except:
            pass

if __name__ == '__main__':
    print("=" * 60)
    print("Device Manager Web Application")
    print("=" * 60)
    print(f"BaSyx Server: {BASYX_URL}")
    print(f"Web Server: http://localhost:5000")
    print("=" * 60)
    app.run(host='0.0.0.0', port=5000, debug=True)
