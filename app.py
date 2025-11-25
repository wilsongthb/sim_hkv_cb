from flask import Flask, request, jsonify
import hashlib
import re
import json
import random
from datetime import datetime, timedelta
import base64
from dotenv import load_dotenv
import os

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))
app = Flask(__name__)


# Configuración del simulador
REALM = "DS-K1T341AMF"
USERNAME = os.getenv("BIOMETRIC_USER", "admin")
PASSWORD = os.getenv("BIOMETRIC_PASSWORD")  # Cambiar según sea necesario

# Configuración de empleados y sus horarios de trabajo
EMPLOYEES_CONFIG = {
    "1": {
        "name": "Wilson",
        "groupName": "Company",
        "groupID": 1,
        # Horarios de trabajo (hora_entrada_min, hora_entrada_max, hora_salida_min, hora_salida_max)
        "work_schedule": {
            "monday": (8, 9, 17, 18),    # Lunes: entrada 8-9, salida 17-18
            "tuesday": (8, 9, 17, 18),   # Martes
            "wednesday": (8, 9, 17, 18), # Miércoles
            "thursday": (8, 9, 17, 18),  # Jueves
            "friday": (8, 9, 17, 18),    # Viernes
            "saturday": (9, 11, 13, 15), # Sábado: horario reducido
            "sunday": None               # Domingo: no trabaja
        },
        # Probabilidad de asistencia (0.0 = nunca, 1.0 = siempre)
        "attendance_probability": 0.8
    },
    "2": {
        "name": "magk",
        "groupName": "Company",
        "groupID": 1,
        "work_schedule": {
            "monday": (7, 8, 16, 17),
            "tuesday": (7, 8, 16, 17),
            "wednesday": (7, 8, 16, 17),
            "thursday": (7, 8, 16, 17),
            "friday": (7, 8, 16, 17),
            "saturday": None,
            "sunday": None
        },
        "attendance_probability": 0.9
    },
    "3": {
        "name": "Carlos",
        "groupName": "Company",
        "groupID": 1,
        "work_schedule": {
            "monday": (8, 9, 17, 18),
            "tuesday": (8, 9, 17, 18),
            "wednesday": (8, 9, 17, 18),
            "thursday": (8, 9, 17, 18),
            "friday": (8, 9, 17, 18),
            "saturday": (10, 12, 14, 16),
            "sunday": None
        },
        "attendance_probability": 0.85
    },
    "7": {
        "name": "GIOVANNI ROSMERY VILCA FLOREZ",
        "groupName": "Company",
        "groupID": 1,
        "work_schedule": {
            "monday": (8, 9, 17, 18),
            "tuesday": (8, 9, 17, 18),
            "wednesday": (8, 9, 17, 18),
            "thursday": (8, 9, 17, 18),
            "friday": (8, 9, 17, 18),
            "saturday": (10, 12, 14, 16),
            "sunday": None
        },
        "attendance_probability": 0.85
    },
    "9": {
        "name": "CHRIST KATHERYNE CHAVEZ CHIPANA",
        "groupName": "Company",
        "groupID": 1,
        "work_schedule": {
            "monday": (8, 9, 17, 18),
            "tuesday": (8, 9, 17, 18),
            "wednesday": (8, 9, 17, 18),
            "thursday": (8, 9, 17, 18),
            "friday": (8, 9, 17, 18),
            "saturday": (10, 12, 14, 16),
            "sunday": None
        },
        "attendance_probability": 0.85
    },
    "13": {
        "name": "CHRIST KATHERYNE CHAVEZ CHIPANA",
        "groupName": "Company",
        "groupID": 1,
        "work_schedule": {
            "monday": (8, 9, 17, 20),
            "tuesday": (8, 9, 17, 20),
            "wednesday": (8, 9, 17, 20),
            "thursday": (8, 9, 17, 20),
            "friday": (8, 9, 17, 20),
            "saturday": (8, 9, 17, 20),
            "sunday": None
        },
        "attendance_probability": 0.99
    },
}

def time_to_minutes(hour, minute):
    """Convierte hora y minuto a minutos desde medianoche"""
    return hour * 60 + minute

def generate_random_times(schedule, ref_date=None, ref_end_date=None):
    """Genera horarios aleatorios basados en el rango configurado"""
    if not schedule:
        return []
    
    entrada_min, entrada_max, salida_min, salida_max = schedule
    
    # Generar hora de entrada aleatoria
    entrada_hour = random.randint(entrada_min, entrada_max)
    entrada_minute = random.randint(0, 59)
    entrada = time_to_minutes(entrada_hour, entrada_minute)
    
    # Generar hora de salida aleatoria
    salida_hour = random.randint(salida_min, salida_max)
    salida_minute = random.randint(0, 59)
    salida = time_to_minutes(salida_hour, salida_minute)
    
    # Algunas veces agregar marcas adicionales (ej: almuerzo)
    times = [entrada, salida]
    
    # 30% de probabilidad de tener marcas de almuerzo
    if random.random() < 0.99:
        almuerzo_salida = time_to_minutes(12, random.randint(0, 30))
        almuerzo_entrada = time_to_minutes(13, random.randint(0, 30))
        times.extend([almuerzo_salida, almuerzo_entrada])
    times = sorted(times)
    if ref_date == ref_end_date:
        # delete last item
        times.pop()
    return times

def get_weekday_name(day_num):
    """Convierte número de día a nombre"""
    days = {1: "monday", 2: "tuesday", 3: "wednesday", 4: "thursday", 
           5: "friday", 6: "saturday", 7: "sunday"}
    return days.get(day_num)

def generate_attendance_data(start_date_str, end_date_str):
    """Genera datos de asistencia simulados para el rango de fechas"""
    start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
    end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
    
    match_results = []
    
    for emp_id, config in EMPLOYEES_CONFIG.items():
        detail_info = []
        current_date = start_date
        
        while current_date <= end_date:
            day_of_week = current_date.isoweekday()  # 1=Monday, 7=Sunday
            weekday_name = get_weekday_name(day_of_week)
            
            # Verificar si el empleado trabaja este día
            schedule = config["work_schedule"].get(weekday_name)
            time_list = []
            
            if schedule and random.random() < config["attendance_probability"]:
                time_list = generate_random_times(schedule, current_date, end_date)
            
            detail_info.append({
                "dateTime": current_date.strftime("%Y-%m-%d"),
                "dayOfweek": day_of_week,
                "timeList": time_list
            })
            
            current_date += timedelta(days=1)
        
        match_results.append({
            "employeeNo": emp_id,
            "name": config["name"],
            "groupName": config["groupName"],
            "groupID": config["groupID"],
            "detailInfo": detail_info
        })
    
    return {
        "responseStatus": "OK",
        "numOfMatches": len(EMPLOYEES_CONFIG),
        "totalMatches": len(EMPLOYEES_CONFIG),
        "matchResults": match_results
    }

def generate_nonce():
    """Genera un nonce aleatorio para autenticación digest"""
    import time
    import secrets
    timestamp = str(time.time())
    random_value = secrets.token_hex(16)
    return hashlib.md5(f"{timestamp}{random_value}".encode()).hexdigest()

def verify_digest_auth(auth_header, method, uri):
    """Verifica la autenticación digest"""
    if not auth_header or not auth_header.startswith('Digest '):
        return False
    
    # Extraer parámetros del header Digest
    params = {}
    digest_params = auth_header[7:]  # Remover "Digest "
    
    for param in re.findall(r'(\w+)="?([^",]+)"?', digest_params):
        params[param[0]] = param[1]
    
    required_params = ['username', 'realm', 'nonce', 'uri', 'response']
    if not all(param in params for param in required_params):
        return False
    
    # Verificar credenciales
    if params['username'] != USERNAME or params['realm'] != REALM:
        return False
    
    # Calcular hash esperado
    ha1 = hashlib.md5(f"{USERNAME}:{REALM}:{PASSWORD}".encode()).hexdigest()
    ha2 = hashlib.md5(f"{method}:{uri}".encode()).hexdigest()
    expected_response = hashlib.md5(f"{ha1}:{params['nonce']}:{ha2}".encode()).hexdigest()
    
    return params['response'] == expected_response

@app.route('/ISAPI/AccessControl/LocalAttendance/SearchRecordSheet', methods=['POST'])
def search_record_sheet():
    """Endpoint que simula la respuesta del equipo biométrico"""
    
    # Verificar autenticación Digest
    auth_header = request.headers.get('Authorization')
    
    if not auth_header:
        # Primera solicitud sin autenticación - enviar desafío
        nonce = generate_nonce()
        challenge = f'Digest realm="{REALM}", nonce="{nonce}", algorithm="MD5", qop="auth"'
        
        response = app.response_class(
            response='',
            status=401,
            headers={'WWW-Authenticate': challenge}
        )
        return response
    
    # Verificar autenticación
    if not verify_digest_auth(auth_header, 'POST', request.path):
        return jsonify({"error": "Authentication failed"}), 401
    
    # Procesar solicitud
    try:
        data = request.get_data()
        #if not data:
            # Intentar parsear como form data si no es JSON
        data = json.loads(request.get_data().decode())
        
        # Extraer fechas de la solicitud
        start_date = data.get('duration', {}).get('startDate', '2025-08-01')
        end_date = data.get('duration', {}).get('endDate', '2025-08-31')
        
        # Generar datos de asistencia
        attendance_data = generate_attendance_data(start_date, end_date)
        
        return jsonify(attendance_data)
        
    except Exception as e:
        print(f"Error procesando solicitud: {e}")
        return jsonify({
            "responseStatus": "ERROR",
            "errorMsg": str(e)
        }), 400

@app.route('/health', methods=['GET'])
def health_check():
    """Endpoint para verificar que el servicio está funcionando"""
    return jsonify({
        "status": "OK",
        "message": "Simulador de control biométrico funcionando",
        "employees": len(EMPLOYEES_CONFIG),
        "port": 8035
    })

@app.route('/config', methods=['GET'])
def get_config():
    """Endpoint para ver la configuración actual"""
    config_info = {}
    for emp_id, config in EMPLOYEES_CONFIG.items():
        config_info[emp_id] = {
            "name": config["name"],
            "attendance_probability": config["attendance_probability"],
            "work_days": [day for day, schedule in config["work_schedule"].items() if schedule]
        }
    
    return jsonify({
        "employees": config_info,
        "auth": {
            "username": USERNAME,
            "realm": REALM
        }
    })

if __name__ == '__main__':
    print("🚀 Iniciando simulador de control biométrico...")
    print(f"📍 Servidor corriendo en: http://localhost:8035")
    print(f"👥 Empleados configurados: {len(EMPLOYEES_CONFIG)}")
    print(f"🔑 Usuario: {USERNAME}")
    print("📋 Endpoints disponibles:")
    print("   - POST /ISAPI/AccessControl/LocalAttendance/SearchRecordSheet")
    print("   - GET  /health")
    print("   - GET  /config")
    print("\n💡 Para probar el servicio:")
    print("   curl http://localhost:8035/health")
    
    app.run(host='0.0.0.0', port=8035, debug=True)