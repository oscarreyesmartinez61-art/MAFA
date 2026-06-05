from machine import Pin, I2C, mem32, PWM, ADC
from machine import Pin, time_pulse_us
import math
import ssd1306
import time
import dht
import network
import urequests
import ujson

########################## REGISTROS GPIO ESP32 #######################################

GPIO_OUT_W1TS = 0x3FF44008 # Direccion del registro para poner en ALTO (ON) los pines
GPIO_OUT_W1TC = 0x3FF4400C # Direccion del registro para poner en BAJO (OFF) los pines

def led_on(pin):
    mem32[GPIO_OUT_W1TS] = (1 << pin) # Enciende el pin desplazando un bit a su posicion en memoria, bueno papu

def led_off(pin):
    mem32[GPIO_OUT_W1TC] = (1 << pin) # Apaga el pin desplazando un bit a su posicion en memoria


#############CONEXION A INTERNET####################

wifi = network.WLAN(network.STA_IF)
wifi.active(True)
wifi.connect("dilan", "123456789")

print("Conectando a WiFi...", end="")
while not wifi.isconnected():
    print("IP de la ESP32:", wifi.ifconfig()[0])
    print(".", end="")
    time.sleep(1)

print("\n CONECTADO A WIFI")
print(wifi.ifconfig())


SERVER = "http://10.181.90.208:5000/ingest"
API_KEY = "iot123"

def enviar_datos(temp, humi, magnitud, luz, distancia):
    try:
        # Se agregaron los datos de luz y distancia al payload para el servidor
        payload = {"device": "esp32", "temp": temp, "hum": humi, "gforce": magnitud, "luz": luz, "distancia": distancia}
        
        headers = {"X-API-Key": API_KEY, "Content-Type": "application/json"}
        
        # OJO: Aquí se usa data= en lugar de json=
        respuesta = urequests.post(
            SERVER,
            json=payload,
            headers=headers
        )
        print("Respuesta:", respuesta.status_code)
        respuesta.close()
    except Exception as e:
        print("Error:", e)

        
#--------------- TELEGRAM ----------------------#

TELEGRAM_TOKEN = "8759481974:AAH80Pkdsyr5wOljqqEuTMzy7wWx1-SSYvM"   # 👈 Pon aquí el token de tu bot
CHAT_ID = "7922643870"        # Chat ID

# URL de Telegram
TELEGRAM_SEND_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
TELEGRAM_GET_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"

ultimo_update_id = 0
ultimo_envio_alerta = 0
INTERVALO_ALERTA = 60 # Segundos entre alertas de Telegram

#------------Funciones telegram-----------------#

def enviar_telegram(mensaje):
    try:
        mensaje = mensaje.replace("&", "%26").replace("#", "%23")
        mensaje = mensaje.replace("°", "%C2%B0").replace(" ", "%20")
        mensaje = mensaje.replace("\n", "%0A")
        url = f"{TELEGRAM_SEND_URL}?chat_id={CHAT_ID}&text={mensaje}"#creacion del URL
        urequests.get(url).close()#abrir el enlace en internet
        print("📱 Mensaje enviado a Telegram")
        return True
    except Exception as e:
        print(f"❌ Error al enviar a Telegram: {e}")
        return False

def enviar_alerta_telegram(mensaje):
    """Envía alerta sin repetir demasiado rápido"""
    global ultimo_envio_alerta
    tiempo_actual = time.time()
    if tiempo_actual - ultimo_envio_alerta >= INTERVALO_ALERTA:
        enviar_telegram(mensaje)
        ultimo_envio_alerta = tiempo_actual

def recibir_mensajes():
    """Revisa si hay nuevos mensajes en Telegram"""
    global ultimo_update_id
    try:
        url = f"{TELEGRAM_GET_URL}?offset={ultimo_update_id + 1}&timeout=0"
        respuesta = urequests.get(url)
        datos = ujson.loads(respuesta.text)
        respuesta.close()
        
        if datos.get("ok") and datos.get("result"):
            for update in datos["result"]:
                ultimo_update_id = update["update_id"]
                mensaje = update.get("message", {}).get("text", "")
                responder_comando(mensaje)
    except Exception as e:
        pass

def responder_comando(texto):
    """Responde a comandos de Telegram"""
    texto = texto.lower().strip()
    
    if texto == "/start":
        enviar_telegram("🟢 Sistema ESP32 activo\n\nComandos:\n/temp - Temperatura\n/hum - Humedad\n/mov - Movimiento\n/estado - Todo\n/umbrales - Ver límites")
    
    elif texto == "/temp":
        enviar_telegram(f"🌡️ Temperatura: {temp:.1f}°C")
    
    elif texto == "/hum":
        enviar_telegram(f"💧 Humedad: {hum:.1f}%")
    
    elif texto == "/mov":
        enviar_telegram(f"🏃 Estado de movimiento: {estado_mov}")
    
    elif texto == "/estado":
        # Se añadieron Luz y Distancia para reportar los 4 sensores en el comando /estado
        enviar_telegram(f"📊 ESTADO ACTUAL\n\n🌡️ Temp: {temp:.1f}°C\n💧 Hum: {hum:.1f}%\n🏃 Mov: {estado_mov}\n💡 Luz: {luz:.0f}%\n📏 Dist: {distancia:.0f}cm")
    
    elif texto == "/umbrales":
        enviar_telegram(f"⚙️ UMBRALES\n🌡️ Temp: {TEMP_MIN}°C - {TEMP_MAX}°C\n💧 Hum: {HUM_MIN}% - {HUM_MAX}%")
    
    else:
        enviar_telegram("📱 Comandos disponibles:\n/temp\n/hum\n/mov\n/estado\n/umbrales")

# ---------------------- RELÉ ----------------------
rele = Pin(27, Pin.OUT)

# ------------------ ULTRASONICO ------------------
trig = Pin(12, Pin.OUT)
echo = Pin(14, Pin.IN)

# ------------------ LDR SENSOR DE LUZ ------------
LDR = ADC(Pin(34))
LDR.width(ADC.WIDTH_12BIT)
LDR.atten(ADC.ATTN_11DB)

# ------------------ OLED -------------------------
i2c = I2C(0, scl=Pin(22), sda=Pin(21))
oled = ssd1306.SSD1306_I2C(128, 64, i2c)

# ------------------ MPU6050 ------------------
MPU = 0x68
i2c.writeto_mem(MPU, 0x6B, b'\x00')

# ------------------ DHT 11 -----------------------
sensor = dht.DHT11(Pin(4))

# ------------------ SERVOS -----------------------
servo1_cerradura = PWM(Pin(13), freq=50)
servo2_puerta = PWM(Pin(25), freq=50)
servo3_puerta = PWM(Pin(26), freq=50)

# ------------------ LEDS -------------------------
Pin(18, Pin.OUT) 
Pin(19, Pin.OUT) 
Pin(23, Pin.OUT) 

ROJO = 18
AMARILLO = 19
VERDE = 23

# ------------------ BUZZER ------------------
buzzer = PWM(Pin(5))
buzzer.freq(1000)
buzzer.duty(0)

#--------------- VARIABLES GLOBALES ------------------------
TEMP_MAX = 30
TEMP_MIN = 18

HUM_MAX = 70
HUM_MIN = 30

# Enviar mensaje de inicio
enviar_telegram("🟢 Sistema ESP32 iniciado correctamente")
enviar_telegram(f"⚙️ Umbrales:\n🌡️ Temp: {TEMP_MIN}°C - {TEMP_MAX}°C\n💧 Hum: {HUM_MIN}% - {HUM_MAX}%")

#--------------------------- BYTE MANDADO POR EL SENSOR MPU
def leer_16bits(reg):
    data = i2c.readfrom_mem(MPU, reg, 2)
    valor = (data[0] << 8) | data[1] # lo que hace data[0]=(0byte alto) lo mueve 8 unidades para meter ek byte bajo(1)
                                     # lo que hace data[1]= une los dos numeros
                                     # para representar los nega
                                     # mueve a la izq 8 espacios para el otro byte, como lo hace, multiplicando por 256=8bytes y los une sumando el segundo numero
                                     
    if valor > 32767:
        valor -= 65536  #resta ese numero para cuando se haga la diferencia quede el neg
                        #ese 65536 es por 16 bytes
    return valor
#----------------------------------------------------

################################ FUNCION DEL BUZZER COMO PITUDO
def buzzer_encendido():
    buzzer.freq(3000)   # frecuencia continua
    buzzer.duty(512)    # intensidad media

def buzzer_apagado():
    buzzer.duty(0)   

POS_CERRADURA_CERRADA = 20
POS_CERRADURA_ABIERTA = 100

POS_PUERTA_CERRADA_1 = 20
POS_PUERTA_CERRADA_2 = 20

POS_PUERTA_ABIERTA_1 = 100
POS_PUERTA_ABIERTA_2 = 100

#----------------------------- SERVOS -----------------
def mover_servo(servo, angulo):
    min_duty = 30
    max_duty = 120
    duty = int((angulo / 180) * (max_duty - min_duty) + min_duty)
    servo.duty(duty)
def mover_suave(servo, inicio, fin, pasos=30):
    for i in range(pasos + 1):
        valor = inicio + (fin - inicio) * i / pasos
        mover_servo(servo, int(valor))
        time.sleep(0.02)
def mover_sincrono(s1, s2, s3, ini1, fin1, ini2, fin2, ini3, fin3, pasos=30):
    for i in range(pasos + 1):

        v1 = ini1 + (fin1 - ini1) * i / pasos
        v2 = ini2 + (fin2 - ini2) * i / pasos
        v3 = ini3 + (fin3 - ini3) * i / pasos
        mover_servo(s1, v1)
        mover_servo(s2, v2)
        mover_servo(s3, v3)
        time.sleep(0.02)
def abrir_sistema():
    global POS_CERRADURA_ABIERTA, POS_PUERTA_ABIERTA_1, POS_PUERTA_ABIERTA_2
    
    mover_suave(servo1_cerradura, POS_CERRADURA_CERRADA, POS_CERRADURA_ABIERTA)
    time.sleep(2)
    mover_sincrono(
        servo2_puerta,
        servo3_puerta,
        servo3_puerta,
        POS_PUERTA_CERRADA_1, POS_PUERTA_ABIERTA_1,
        POS_PUERTA_CERRADA_2, POS_PUERTA_ABIERTA_2,
        POS_PUERTA_CERRADA_2, POS_PUERTA_ABIERTA_2
    )
def cerrar_sistema():
    global POS_CERRADURA_ABIERTA, POS_PUERTA_ABIERTA_1, POS_PUERTA_ABIERTA_2

    mover_sincrono(   
        servo2_puerta,
        servo3_puerta,
        servo3_puerta,
        POS_PUERTA_ABIERTA_1, POS_PUERTA_CERRADA_1,
        POS_PUERTA_ABIERTA_2, POS_PUERTA_CERRADA_2,
        POS_PUERTA_ABIERTA_2, POS_PUERTA_CERRADA_2
    )
    time.sleep(2)
    mover_suave(servo1_cerradura, POS_CERRADURA_ABIERTA, POS_CERRADURA_CERRADA)
#---------------------------------------------


puerta_abierta = False  
tiempo_activacion = None
duracion_puerta_abierta = 5 #DURACION DE LA PUERTA ABIERTA PARA YA CERRAR
tiempo_puerta_abierta = None
TIEMPO_LIMITE = 10  # CON LA PUERTA ABIERTA
DIS_MIN = 10

LUZ_MAX = 50
tiempo_luz_detectada = None

MOV_MAX = 1.8    #MPU6050
MOV_MIN = 1.1
tiempo_estable = None
tiempo_movimiento = None
TIEMPO_MOV = 5

ESPERA_DESINFECCION = 3  # seg para la proxima desinfeccion
TIEMPO_UVC = 3          # seg que dura la desinfeccion
contador_desinfeccion = None
inicio_uvc = None
estado_uvc = "ESPERANDO_CIERRE"


while True:

#--------------------- MPU6050 --------------------------
    ax = leer_16bits(0x3B)
    ay = leer_16bits(0x3D)
    az = leer_16bits(0x3F)

    ax = ax / 16384
    ay = ay / 16384
    az = az / 16384

    magnitud = round(math.sqrt(ax**2 + ay**2 + az**2), 1)
    ##
    if magnitud > MOV_MAX:
        if tiempo_movimiento is None:
            tiempo_movimiento = time.time()
    else:
        tiempo_movimiento = None
    ##
    if (MOV_MIN <= magnitud <= MOV_MAX):
        if tiempo_estable is None:
            tiempo_estable = time.time()
    else:
        tiempo_estable = None

#-----------------LDR SENSOR DE LUZ-------------------  

    luz = round(100 * (4095 - LDR.read()) / 4095,0) # normalizamos para que se vea porcentaje
    if luz >= LUZ_MAX:
        if tiempo_luz_detectada is None:
            tiempo_luz_detectada = time.time()
    else:
        tiempo_luz_detectada = None

#-----------------ULTRASONICO--------------------------
    trig.off()
    time.sleep_us(2)
    trig.on()
    time.sleep_us(10)
    trig.off()
    duracion = time_pulse_us(echo, 1)
    distancia = round(duracion * 0.034 / 2, 0)

    if distancia <= DIS_MIN and estado_uvc != "DESINFECTANDO":
        if not puerta_abierta:
            abrir_sistema()
            puerta_abierta = True
            tiempo_activacion = time.time()

            contador_desinfeccion = None

            rele.value(0)  # apagar lámpara UV

    if puerta_abierta:

        if time.time() - tiempo_activacion >= duracion_puerta_abierta:
            
            cerrar_sistema()
            puerta_abierta = False
    
            contador_desinfeccion = time.time() #inicia cuenta regresiva
            estado_uvc = "CONTANDO"
    
#------------logica de desinfeccion------------
    ahora = time.time()
    if estado_uvc == "CONTANDO":
        if puerta_abierta:
            contador_desinfeccion = None
            estado_uvc = "ESPERANDO_CIERRE"

        elif ahora - contador_desinfeccion >= ESPERA_DESINFECCION:

            rele.value(1)  # ENCENDER UV-C

            inicio_uvc = ahora

            estado_uvc = "DESINFECTANDO"

    # -------- DESINFECTANDO 10 SEGUNDOS --------
    elif estado_uvc == "DESINFECTANDO":
        if ahora - inicio_uvc >= TIEMPO_UVC:

            rele.value(0)
            inicio_uvc = None
            contador_desinfeccion = None

            estado_uvc = "ESPERANDO_CIERRE"



#------------------DHT--------------------------------
    sensor.measure()
    temp = round(sensor.temperature() ,2)
    hum = round(sensor.humidity() ,2)   

    led_off(ROJO)
    led_off(AMARILLO)
    led_off(VERDE)
    buzzer_apagado()


#-------------------------------ESTADOS LEDS Y BUZZER----------------------
    if (temp >= TEMP_MAX or temp <= TEMP_MIN or
        hum >= HUM_MAX or hum <= HUM_MIN or
        (tiempo_luz_detectada is not None and
        time.time() - tiempo_luz_detectada >= TIEMPO_LIMITE)or
        (tiempo_movimiento is not None and
        time.time() - tiempo_movimiento >= TIEMPO_MOV)):
        
        estado_general = "ALERTA"
        led_off(VERDE)
        led_on(ROJO)
        buzzer_encendido()
        
        # Se incluyó la distancia medida por el ultrasonido en el reporte de alertas de Telegram
        enviar_alerta_telegram(f"⚠️ ALERTA GABINETE:\n🌡️ Temp: {temp}C\n💧 Hum: {hum}%\n💡 Luz: {luz}%\n🏃 Mov: {magnitud}g\n📏 Dist: {distancia}cm")
    else:
        estado_general = "NORMAL"
        led_off(ROJO)
        led_on(VERDE)
        buzzer_apagado()

#-------------------------------------------------------------------------


    # TEMPERATURA
    if TEMP_MAX <= temp:
        estado_temp = "CALIENTE"
    elif temp <= TEMP_MIN:
        estado_temp = "FRIO"
    else:
        estado_temp = "NORMAL"

    # HUMEDAD
    if HUM_MAX <= hum:
        estado_hum = "ALTA HUM"
    elif hum <= HUM_MIN:
        estado_hum = "BAJA HUM"
    else:
        estado_hum = "NORMAL"

    # DISTANCIA
    if DIS_MIN >= distancia:
        estado_dis = "ABIERTO"
    else:
        estado_dis = "CERRADO"
    
    # LUZ
    if LUZ_MAX <= luz:
        estado_luz = "ALERTA"
    elif luz < LUZ_MAX:
        estado_luz = "NORMAL"

    # ESTADO DE MOVIMIENTO
    if magnitud <= MOV_MIN:
        estado_mov = "REPOSO"
    elif magnitud <= MOV_MAX:
        estado_mov = "NORMAL"
    else:
        estado_mov = "ALERTA"


#-------------------------------------------------------------------------
    oled.fill(0)
    #---------------------------------DHT-------------------
    oled.text("RELE" + " - " + str(rele.value()), 0, 0)
    oled.text("PUERTA" +"  -  " + str(estado_dis), 0, 10)    
    oled.text("TEM:" + str(temp) + "C"+ " " + str(estado_temp), 0, 20)
    oled.text("HUM:" + str(hum) + "%"+ " " + str(estado_hum), 0, 30)
    oled.text("LUZ:" + str(luz) +"%"+ " " + str(estado_luz), 0, 40) 
    oled.text("MOV:" + str(magnitud) + "g"+"  " + str(estado_mov), 0, 50)          
    oled.show()

    # Se pasan las variables luz y distancia a la función para enviarlas al servidor
    enviar_datos(temp, hum, magnitud, luz, distancia)
    recibir_mensajes()

    time.sleep(2)