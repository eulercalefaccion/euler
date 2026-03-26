#!/usr/bin/env python3
"""
EULER - Generador de Presupuestos PDF
Backend Flask: recibe el PDF de Gesdatta + lista de equipos,
genera el PDF completo listo para enviar al cliente.

Uso:
    pip install flask flask-cors reportlab pypdf
    python euler_backend.py
    → Servidor en http://localhost:5050
"""

import io
import os
import sys
import json
import base64
import textwrap
from datetime import date
from flask import Flask, request, jsonify, send_file, send_from_directory
# flask-cors no es necesario, usamos after_request manual
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm, cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable, KeepTogether
)
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from pypdf import PdfWriter, PdfReader

# ─── Colores Euler ────────────────────────────────────────────────────────────
EULER_DARK   = colors.HexColor("#0D2A4E")
EULER_MID    = colors.HexColor("#1A4A7A")
EULER_ACCENT = colors.HexColor("#F5A623")
EULER_LIGHT  = colors.HexColor("#E8EFF7")
EULER_RED    = colors.HexColor("#D93025")
GRAY_TEXT    = colors.HexColor("#444444")
GRAY_LIGHT   = colors.HexColor("#F5F5F5")
GRAY_BORDER  = colors.HexColor("#CCCCCC")
WHITE        = colors.white
BLACK        = colors.black

W, H = A4  # 595.27 x 841.89 pts

# ─── Carpeta de folletos originales ───────────────────────────────────────────
_LOCAL_FOLLETOS = r"G:\Mi unidad\1 - EULER CALEFACCION\14 - PROCESOS Y CALIDAD\FOLLETOS Y NOTAS PRESUPUESTOS"
_CLOUD_FOLLETOS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "folletos")
FOLLETOS_DIR = _LOCAL_FOLLETOS if os.path.exists(_LOCAL_FOLLETOS) else _CLOUD_FOLLETOS

PORTADA_ARCHIVO = "PORTADA_ANTEPROYECTO_v3.pdf"

MAPEO_FOLLETOS = {
    "baxi_luna3":               "Caldera Baxi Luna 3 Confort.pdf",
    "baxi_eco_nova":            "Caldera Baxi Eco Nova.pdf",
    "baxi_luna_duo_tec":        "Caldera Baxi Luna Duo Tec E.pdf",
    "caldaia_top_s":            "Caldera Caldaia TOP S.pdf",
    "dd_nepto_atron":           "Caldera DemirDokum Nepto Atron.pdf",
    "radiador_rehau500":        "Radiador REHAU 500.pdf",
    "radiador_nereus":          "Radiador Nereus 500.pdf",
    "raubasic":                 "Sistema RAUBASIC REHAU.pdf",
    "piso_radiante_rehau":      "Piso Radiante REHAU.pdf",
    "caldera_electrica_advance":"Caldera Electrica Flowing Advance.pdf",
    "bowman":                   "Intercambiador Bowman.pdf",
    "ecopool":                  "Bomba Calor Heatcraft EcoPool.pdf",
    "toallero_kanah":           "Toallero Kanah 800.pdf",
}

# ─── Catálogo completo de equipos ────────────────────────────────────────────
CATALOGO = {
    "baxi_luna3": {
        "nombre": "Caldera Baxi Luna 3 Confort",
        "categoria": "Caldera mural a gas de alta gama",
        "descripcion": (
            "Caldera mural a gas de alta performance. Ideal para viviendas de mediana o gran "
            "superficie. Versiones solo calefaccion y doble servicio. Encendido electronico sin "
            "piloto. Control digital de ultima generacion que permite operar la caldera a distancia. "
            "Maximiza el ahorro energetico en conjunto con sistemas de energia solar termica."
        ),
        "specs": [
            ("Capacidad maxima nominal", "25.854 - 32.700 Kcal/h"),
            ("Maxima eficiencia (Dir. 92/42/CEE)", "92%"),
            ("Produccion ACS (Delta t 20°C)", "22 lts/min"),
            ("Rango temperatura calefaccion", "30 / 85 °C"),
            ("Rango temperatura ACS", "35 / 60 °C"),
            ("Tipo de ventilacion", "Tiro natural / Tiro forzado balanceado"),
            ("Diametro salida de humos", "120 mm (tiro natural) / 100 mm coaxial"),
            ("Peso", "33 - 40 kg"),
            ("Dimensiones (Al x An x Pr)", "763 x 450 x 345 mm"),
            ("Garantia", "2 anios"),
        ],
        "conexiones": "A. Mando Calef. 3/4\" · B. Salida ACS 1/2\" · C. Entrada Gas 3/4\" · D. Entrada Agua 1/2\" · E. Retorno Calef. 3/4\"",
        "nota": "Representante exclusivo en Argentina: Triangular S.A. | info@triangular.com.ar | triangular.com.ar",
        "color": "#1A4A7A",
    },
    "baxi_eco_nova": {
        "nombre": "Caldera Baxi Eco Nova",
        "categoria": "Caldera mural a gas doble servicio",
        "descripcion": (
            "Caldera mural BAXI doble servicio. Brinda calefaccion y agua caliente sanitaria, "
            "con ventilacion forzada para mayor seguridad. Tecnologia de extensa vida util "
            "fabricada bajo estrictas normas europeas. Gran rendimiento y flexibilidad por la "
            "modulacion de llama para viviendas pequenias, medianas y de gran superficie."
        ),
        "specs": [
            ("Modelos", "Eco Nova 24F / 31F"),
            ("Capacidad maxima nominal", "25.389 / 32.700 Kcal/h"),
            ("Rendimiento nominal", "90,8%"),
            ("Produccion ACS (Delta t 20°C)", "16 / 20,6 lts/min"),
            ("Rango temperatura ACS", "35 / 60 °C"),
            ("Rango temperatura calefaccion", "30 / 85 °C"),
            ("Diametro salida humos coaxial", "60/100 mm"),
            ("Diametro salida humos tubos separados", "80 mm"),
            ("Tipo de ventilacion", "Tiro forzado balanceado"),
            ("Peso equipo vacio", "29 / 35 kg"),
            ("Dimensiones 24F (Al x An x Pr)", "704 x 400 x 295 mm"),
            ("Dimensiones 31F (Al x An x Pr)", "780 x 450 x 340 mm"),
            ("Garantia", "2 anios"),
        ],
        "conexiones": "A. Mando Calef. 3/4\" · B. Salida ACS 1/2\" · C. Entrada Gas 3/4\" · D. Entrada Agua 1/2\" · E. Retorno Calef. 3/4\"",
        "nota": "Doble intercambiador. Apta para radiadores y piso radiante. Representante exclusivo: Triangular S.A.",
        "color": "#1A4A7A",
    },
    "baxi_luna_duo_tec": {
        "nombre": "Caldera Baxi Luna Duo Tec E (Condensacion)",
        "categoria": "Caldera mural a gas de condensacion",
        "descripcion": (
            "Caldera mural a gas de condensacion con bomba de circulacion modulante. "
            "Hasta 40.000 Kcal/h de potencia. Tecnologia de condensacion: al condensar los gases "
            "de combustion recupera su calor y lo reutiliza, ahorrando hasta 45% de energia "
            "vs. calderas convencionales. Hasta 90% menos de gases de efecto invernadero."
        ),
        "specs": [
            ("Modelos", "Solo calef. 1.24, 1.28 / Doble serv. 24, 28, 33, 40"),
            ("Capacidad maxima nominal", "24.273 - 40.548 Kcal/h"),
            ("Rendimiento nominal", "105,8%"),
            ("Produccion ACS (Delta t 20°C)", "20,2 - 33,8 lts/min"),
            ("Rango temperatura ACS", "35 - 60 °C"),
            ("Rango temperatura calefaccion", "25 - 80 °C"),
            ("Diametro salida humos coaxial", "60/100 mm"),
            ("Diametro salida humos tubos sep.", "80 mm"),
            ("Tipo ventilacion", "Tiro forzado balanceado"),
            ("Nivel eficiencia energetica", "Clase A*"),
            ("Peso", "34,5 - 41 kg"),
            ("Garantia", "2 anios"),
        ],
        "conexiones": "A-E iguales Luna 3. Adicional: Descarga condensacion 22mm",
        "nota": "Plug & play: detecta automaticamente el tipo de gas. Representante exclusivo: Triangular S.A.",
        "color": "#0D5C3A",
    },
    "caldaia_top_s": {
        "nombre": "Caldera Caldaia Digital TOP S",
        "categoria": "Caldera mural a gas digital",
        "descripcion": (
            "Primera caldera digital de America Latina. Control digital que permite seleccionar "
            "el servicio deseado facilmente, segun las opciones de agua caliente sanitaria o "
            "calefaccion. Regula las temperaturas del agua de consumo y del circuito de calefaccion "
            "de forma simple y precisa. Sin llama piloto."
        ),
        "specs": [
            ("Modelos", "DIGITAL TOP S26f / S26IP / S26fC / S26fPC / S26TC"),
            ("Potencia con modulacion", "8.700 - 26.000 Kcal/h (f/IP) / 8.700 - 19.800 Kcal/h (C/PC/TC)"),
            ("Dimensiones (Al x An x Pr)", "770 x 400 x 340 mm"),
            ("Sistema compatible", "Radiador / Fan Coil / Piso Radiante"),
            ("Salida de humos", "Tiro Balanceado Forzado / Tiro Forzado"),
        ],
        "conexiones": "Altura 77 cm - Ancho 40 cm - Profundidad 34 cm",
        "nota": "Sin llama piloto. Conexion para sonda anticipadora de piso radiante. Sistema antibloqueo de bomba. Fabricacion argentina. www.caldaia.com.ar",
        "color": "#1A4A7A",
    },
    "dd_nepto_atron": {
        "nombre": "Caldera DemirDokum / DD Nepto - Atron",
        "categoria": "Caldera residencial a gas",
        "descripcion": (
            "Calderas residenciales a gas para radiadores o piso radiante. "
            "Linea CALEFACCION por movimiento de AGUA. Monotermica Doble Servicio (ATRON) y "
            "Bitermica Doble servicio, Apta CABA (NEPTO). COP 80%/85%. "
            "Gas Natural o Comprimido. Procedencia: Turquia - Vaillant Group."
        ),
        "specs": [
            ("Modelos", "Nepto 20 / Atron 24 / Atron 28"),
            ("Tipo", "Bitermica T. Forzado (Nepto) / Monotermica T. Forzado (Atron)"),
            ("Capacidad calor", "20.000 / 24.000 / 28.000 W"),
            ("COP", "0,93"),
            ("Alimentacion", "220-1-50 Hz"),
            ("Consumo electrico", "95 / 98 / 98 W"),
            ("Gas", "G20 (Natural) - G31 (Envasado)"),
            ("Caudal ACS (salto 30°C)", "2,5 l/min"),
            ("Conexiones ACS", "1/2\""),
            ("Conexiones calefaccion / gas", "3/4\""),
            ("Dimensiones Nepto (An x Al x Pr)", "410 x 700 x 280 mm"),
            ("Dimensiones Atron 24 (An x Al x Pr)", "410 x 700 x 295 mm"),
            ("Dimensiones Atron 28 (An x Al x Pr)", "444 x 700 x 295 mm"),
            ("Peso unidad interior", "30 / 30 / 33 kg"),
        ],
        "conexiones": "Kit salida de gases metal disponible (cod. 893010). Cod. ANSAL: 893000 / 893020 / 893025",
        "nota": "Distribucion exclusiva Euler. www.euler.com.ar",
        "color": "#1A4A7A",
    },
    "radiador_rehau500": {
        "nombre": "Radiador REHAU 500",
        "categoria": "Radiador bimetalico de aluminio y acero",
        "descripcion": (
            "Radiador bimetalico con nucleo de acero y revestimiento de aluminio. "
            "Alta conductividad termica, diseno moderno y amplia durabilidad. "
            "Apto para instalaciones en hogar, edificios e industrias. "
            "Certificaciones ISO 9001-14001-EN 442."
        ),
        "specs": [
            ("Profundidad", "94 mm"),
            ("Altura", "557 mm"),
            ("Distancia entre ejes", "500 mm"),
            ("Longitud por elemento", "78 mm"),
            ("Diametro conexiones", "G1 pulgadas"),
            ("Contenido de agua", "0,2 litros/elemento"),
            ("Peso", "1,24 kg/elemento"),
            ("Potencia termica Delta 30k", "87,5 W/elemento"),
            ("Potencia termica Delta 50k", "112,5 W/elemento"),
            ("Potencia termica Delta 70k", "145 W/elemento"),
            ("Presion de trabajo", "2 MPa"),
            ("Presion maxima de ejercicio", "3 MPa"),
            ("MAT NR SAP", "13743011001"),
            ("ART NR LOGIC", "374301-001"),
        ],
        "conexiones": "REHAU S.A. - Cuyo 1900, Martinez, Pcia. de Buenos Aires. Tel: +54 11 4898-6000",
        "nota": "Facil limpieza y mantenimiento. Amplia durabilidad. www.rehau.com.ar",
        "color": "#7A3A0D",
    },
    "radiador_nereus": {
        "nombre": "Radiador Bimetalico Nereus 500",
        "categoria": "Radiador bimetalico - Diseno italiano",
        "descripcion": (
            "Radiador bimetalico Nereus 500. Composicion 56% Acero + 44% Aluminio. "
            "Pintado por electroforesis (E-coating) para maxima proteccion contra la corrosion. "
            "Diseno Italiano. Apto para instalaciones en hogar, edificios e industrias. "
            "Disponible de 2 a 12 secciones."
        ),
        "specs": [
            ("Modelo", "Nereus 500"),
            ("Tipo", "Radiador Bimetalico"),
            ("Composicion", "56% Acero + 44% Aluminio"),
            ("Acabado", "E-coating (pintado por electroforesis)"),
            ("Dimensiones por seccion", "560 x 78 x 80 mm"),
            ("Distancia entre ejes", "500 mm"),
            ("Contenido de agua", "0,20 litros/seccion"),
            ("Potencia termica nominal", "143 W (DeltaT=70°C)"),
            ("Working pressure", "2,0 MPa"),
            ("Testing pressure", "3,0 MPa"),
            ("Peso por seccion", "1,50 kg"),
            ("Disponible en", "2 a 12 secciones"),
            ("Garantia", "10 anios"),
        ],
        "conexiones": "Apto para instalaciones en hogar, edificios e industrias.",
        "nota": "Diseno italiano. E-coating aumenta la proteccion contra la corrosion.",
        "color": "#7A3A0D",
    },
    "raubasic": {
        "nombre": "Sistema RAUBASIC (REHAU)",
        "categoria": "Sistema de tuberias para instalaciones sanitarias y de calefaccion",
        "descripcion": (
            "Sistema de tuberias REHAU para instalaciones sanitarias y de calefaccion. "
            "Union por compresion radial: montaje facil, rapido y seguro en 3 pasos: "
            "1. Cortar tubo e insertar casquillo. 2. Insertar accesorio de union. 3. Comprimir casquillo. "
            "Herramientas RAUTOOL: no precisan calibracion ni mantenimiento."
        ),
        "specs": [
            ("Diametros disponibles", "16, 20, 25 y 32 mm"),
            ("Tipo de union", "Compresion radial (100% resistente a fugas)"),
            ("Herramienta manual RAUTOOL", "Pinzas de union 16, 20 y 25 mm"),
            ("Herramienta hidraulica manual", "Mordazas de 16, 20, 25 y 32 mm"),
            ("Aplicacion", "Instalaciones sanitarias y calefaccion"),
        ],
        "conexiones": "Componentes del sistema RAUBASIC PEX-a. Sin necesidad de calibracion ni mantenimiento de herramientas.",
        "nota": "REHAU - Engineering progress / Enhancing lives. www.rehau.com.ar",
        "color": "#2A4A0D",
    },
    "piso_radiante_rehau": {
        "nombre": "Piso Radiante REHAU (PE-RT + Colectores PHKV-D)",
        "categoria": "Sistema de calefaccion por suelo radiante",
        "descripcion": (
            "Sistema de calefaccion por suelo radiante con tuberias PE-RT de alta relacion "
            "precio-calidad, certificado por normas europeas. Colectores polimericos PHKV-D "
            "fabricados en poliamida reforzada con fibra de vidrio para instalaciones de hasta "
            "12 circuitos. Compatible con calderas, bombas de calor y paneles solares."
        ),
        "specs": [
            ("Tuberia", "PE-RT (Polietileno de alta resistencia termica)"),
            ("Diametros tubo", "16 y 20 mm"),
            ("Aplicacion", "Calefaccion por piso radiante exclusivamente"),
            ("Certificacion", "Normas europeas"),
            ("Colector modelo", "Linea PHKV-D"),
            ("Material colector", "Poliamida reforzada con fibra de vidrio"),
            ("Caudalimetro", "Grafico (0 a 5 l/min)"),
            ("Rango temperatura", "-10°C a 82°C"),
            ("Rango de salidas", "2 a 12 salidas"),
            ("Automatizable", "Si"),
        ],
        "conexiones": "Para instalacion de pisos radiantes y refrescantes. Compatible con calderas, bombas de calor y paneles solares.",
        "nota": "REHAU - Engineering progress / Enhancing lives. www.rehau.com.ar",
        "color": "#0D5C5A",
    },
    "caldera_electrica_advance": {
        "nombre": "Caldera Electrica Flowing Advance",
        "categoria": "Caldera electrica mural - Industria Argentina",
        "descripcion": (
            "Linea completa de calderas electricas murales FLOWING ADVANCE: modelos SC (solo "
            "calefaccion), DS (doble servicio: calefaccion y agua caliente) y BT (doble servicio: "
            "para trabajar con Boiler). Potencias de 10 a 40 kW. Industria Argentina."
        ),
        "specs": [
            ("Modelos", "ADVANCE SC / DS / BT"),
            ("Potencias disponibles", "10 kW (8.600 kcal/h) a 40 kW (34.400 kcal/h)"),
            ("Consumo 3x380V", "15 / 31 / 46 / 60 A"),
            ("Consumo 220V monofasico", "45 A (solo modelo 10kW)"),
            ("Superficie calefaccion aprox.", "Hasta 110 m2 (10kW) / Hasta 440 m2 (40kW)"),
            ("Bomba circuladora", "Grundfos UPS 15-60"),
            ("Dimensiones aprox.", "790 x 410 x 320 mm"),
            ("Garantia", "2 anios"),
        ],
        "conexiones": "AC: Alim. Calef. H 3/4\" BSP · HW: Agua Caliente M 1/2\" BSP · CW: Ingreso Agua Fria M 1/2\" BSP · RC: Retorno Calef. H 3/4\" BSP · LL: Llenado H 1/2\" BSP",
        "nota": "Resistencias blindadas AISI316 intercambiables. Tanque expansion cerrado. Valvula seguridad 3 bar. Industria Argentina. www.flowing.com.ar",
        "color": "#5A1A7A",
    },
    "bowman": {
        "nombre": "Intercambiador de Calor de Piscina Bowman",
        "categoria": "Intercambiador de calor - 100 anios de tecnologia",
        "descripcion": (
            "Intercambiadores de calor para piscinas y spas Bowman. 100 anios de tecnologia "
            "de transferencia de calor. Para calderas, paneles solares y bombas de calor. "
            "Decenas de miles de unidades operando en todo el mundo, desde spas hasta piscinas "
            "olimpicas. Calientan piscinas hasta 3 veces mas rapido que la competencia."
        ),
        "specs": [
            ("Tipos de pila", "Titanio / Acero inoxidable / Cupronicquel"),
            ("Conexiones", "BSP / PN6 / PN10 / PN16"),
            ("Gamas", "EC y FC con cubiertas finales de material compuesto"),
            ("Garantia pila titanio", "10 anios"),
            ("Aplicaciones", "Spas, baneras de hidromasaje, piscinas olimpicas"),
        ],
        "conexiones": "Cubiertas de extremo de ajuste universal. Pila y cubiertas desmontables para mantenimiento sencillo.",
        "nota": "Compatible con energia solar y renovable. Modelos EC y FC disponibles.",
        "color": "#4A2A0D",
    },
    "ecopool": {
        "nombre": "Bomba de Calor Heatcraft EcoPool",
        "categoria": "Climatizacion de piscinas - Bomba de calor",
        "descripcion": (
            "Bombas de Calor EcoPool Heatcraft. Los climatizadores de piscina mas eficientes. "
            "Conexion WiFi integrada para control desde smartphone. Gas ecologico R-410A. "
            "Versiones frio-calor y calor solamente. Ahorra hasta 50% vs. climatizador a gas. "
            "Funciona en todas las estaciones, incluso en dias nublados."
        ),
        "specs": [
            ("Modelos", "EP-30M / 50M / 75M / 75T / 110T / 150T / 220T"),
            ("Potencia calorica (Aire 26°C / Agua 26°C)", "7.000 - 43.000 Kcal/h"),
            ("Alimentacion", "Monofasica 220V (30M/50M/75M) / Trifasica 380V (75T-220T)"),
            ("Rango temp. operacion aire", "-10°C a 43°C"),
            ("Rango temp. operacion agua", "15°C a 40°C"),
            ("Intercambiador", "Titanio"),
            ("Ruido a 1m", "36 - 52 dB"),
            ("Piscina max. verano EP-30M", "20 m2 / 30 m3"),
            ("Piscina max. verano EP-220T", "150 m2 / 225 m3"),
            ("Garantia", "2 anios"),
        ],
        "conexiones": "Perdida de carga: 1,1 mCA. Geoterm S.A. - San Andres, Pcia. Buenos Aires. Tel: (5411) 4753-3265",
        "nota": "Compresor Toshiba Gmcc / Samsung / Copeland / Danfoss / Panasonic. 2 anios de garantia.",
        "color": "#0D3A7A",
    },
    "toallero_kanah": {
        "nombre": "Toallero Kanah 800 (Latyn Clima)",
        "categoria": "Toallero de acero - Calefaccion de bano",
        "descripcion": (
            "Toallero de acero Kanah 800 marca LatynClima. Transmitimos calidez, creamos momentos. "
            "Incluye soporte de pared, purgador, tapon y tornillos. "
            "Certificado Resolucion 599-E/2017. Normas ISO 14001:2004 / ISO 9001:2008."
        ),
        "specs": [
            ("Modelo", "Kanah 800"),
            ("Material", "Acero"),
            ("Dimensiones (Al x An x Tubo)", "800 x 500 x 18 mm"),
            ("Peso", "7,18 kg"),
            ("Emision termica Kanah 800 (T=50°C)", "358 W"),
            ("Emision termica Kanah 1200 (T=50°C)", "515 W"),
            ("Certificacion", "ISO 14001:2004 / ISO 9001:2008 / Res. 599-E/2017"),
        ],
        "conexiones": "Incluye: soporte de pared, purgador, tapon y tornillos.",
        "nota": "www.latyn.net",
        "color": "#4A4A0D",
    },
}

CONDICIONES = """1) FORMA DE PAGO

Efectivo, transferencia, cheques/echeqs. (consultar por tarjetas de credito).

- Canieria: Al aprobar la oferta.
- Equipos: A convenir.
- Mano de obra de instalacion de equipos: A convenir.

2) PLAZO DE ENTREGA

Provision de equipos: inmediato.
Canieria: Hasta 15 dias habiles a partir del comienzo del trabajo.
Instalacion de caldera y radiadores: 3 dias habiles segun tiempos de construccion.

3) NOTAS

a) El presente presupuesto tiene validez de 10 dias habiles a partir de la fecha de confeccionado.

b) Para la instalacion del termostato de ambiente, se debe dejar un cableado desde la caldera hasta
la ubicacion del mismo segun instrucciones nuestras.

c) Para el funcionamiento de la caldera se debe dejar una conexion de entrada de agua (a realizar por
el cliente segun instrucciones nuestras) y es excluyente que la presion de agua a la entrada sea igual
o superior a 1 kg/cm2. De no conseguir dicha presion por altura del tanque, se debe adicionar una
bomba presurizadora.

d) La instalacion no incluye la instalacion electrica del tomacorriente, necesaria para el
funcionamiento de la caldera.

e) El presente presupuesto NO incluye ningun trabajo ni material relacionado con la canieria de GAS,
agua fria ni agua caliente sanitaria necesaria y excluyente para el funcionamiento de la caldera.

f) El trabajo de instalacion de canieria incluye el canaleteo de pisos y paredes y se entrega con la
misma amurada y fijada, quedando a cargo del cliente el posterior tapado de las canaletas.

g) Puesta en marcha inicial (PEMIO): tiene por objetivo probar el sistema, ponerlo a punto, explicar
el funcionamiento a los propietarios y activar la garantia de los equipos. Se realiza inmediatamente
despues de finalizar la instalacion. Para realizarla se debe contar con todos los servicios (energia
electrica, gas y agua) y con la presencia de los propietarios o responsables. De no cumplirse alguno
de estos requisitos, la PEMIO se realizara en el momento que se cumplan dichos requisitos, con costo
a cargo del cliente.

h) Condiciones de garantia: Calderas: 12 meses a partir de la PEMIO. La garantia puede extenderse
12 meses adicionales (logrando 24 meses totales) contratando un servicio de mantenimiento preventivo
autorizado. Radiadores: 10 anios a partir de la PEMIO."""


# ─── PDF Generator ────────────────────────────────────────────────────────────

def draw_euler_logo(c, x, y, scale=1.0):
    """Dibuja el logo Euler con canvas directamente."""
    # Texto EULER
    c.setFont("Helvetica-Bold", 42 * scale)
    c.setFillColor(WHITE)
    c.drawString(x, y, "EULER")
    # Circulo con icono
    cx = x + 175 * scale
    cy = y + 16 * scale
    r  = 22 * scale
    c.setStrokeColor(WHITE)
    c.setLineWidth(2 * scale)
    c.circle(cx, cy, r, stroke=1, fill=0)
    # U / barras termicas
    bw = 6 * scale
    bh_izq = 22 * scale
    bh_der = 20 * scale
    c.setFillColor(EULER_ACCENT)
    c.rect(cx - 10*scale, cy - bh_izq/2, bw, bh_izq, fill=1, stroke=0)
    c.setFillColor(EULER_RED)
    c.rect(cx + 4*scale, cy - bh_der/2, bw, bh_der, fill=1, stroke=0)
    # Lineas de vapor
    c.setStrokeColor(WHITE)
    c.setLineWidth(1.5 * scale)
    for i, ox in enumerate([-7*scale, 0, 7*scale]):
        sy = cy + 11 * scale
        c.line(cx + ox, sy, cx + ox + 2*scale, sy + 5*scale)
    # Subtitulo
    c.setFont("Helvetica-Oblique", 11 * scale)
    c.setFillColor(colors.HexColor("#A8C4E0"))
    c.drawString(x, y - 18 * scale, "calefaccion por agua")


def build_portada_pdf(datos_presupuesto: dict) -> bytes:
    """Genera la portada Euler en un PDF de 1 página."""
    buf = io.BytesIO()
    c = rl_canvas.Canvas(buf, pagesize=A4)

    # Fondo azul oscuro completo
    c.setFillColor(EULER_DARK)
    c.rect(0, 0, W, H, fill=1, stroke=0)

    # Franja decorativa inferior
    c.setFillColor(EULER_MID)
    c.rect(0, 0, W, 60, fill=1, stroke=0)
    c.setFillColor(EULER_ACCENT)
    c.rect(0, 58, W, 4, fill=1, stroke=0)

    # Logo centrado
    logo_x = W/2 - 110
    logo_y = H/2 + 80
    draw_euler_logo(c, logo_x, logo_y, scale=1.0)

    # Línea separadora
    c.setStrokeColor(colors.HexColor("#2A5A8A"))
    c.setLineWidth(1)
    c.line(60, H/2 + 55, W - 60, H/2 + 55)

    # Título del documento
    c.setFont("Helvetica-Bold", 14)
    c.setFillColor(WHITE)
    c.drawCentredString(W/2, H/2 + 30, "PRESUPUESTO DE CALEFACCION POR AGUA")

    # Datos del presupuesto
    c.setFont("Helvetica", 11)
    c.setFillColor(colors.HexColor("#A8C4E0"))
    y_data = H/2 - 10
    campo_color = colors.HexColor("#6A9FC0")
    valor_color = WHITE

    campos = [
        ("Cliente:", datos_presupuesto.get("cliente", "")),
        ("Direccion de obra:", datos_presupuesto.get("direccion_obra", "")),
        ("N° Presupuesto:", datos_presupuesto.get("numero_presupuesto", "")),
        ("Fecha:", datos_presupuesto.get("fecha", date.today().strftime("%d/%m/%Y"))),
        ("Monto total:", datos_presupuesto.get("total", "")),
    ]
    for label, valor in campos:
        if valor:
            c.setFont("Helvetica-Bold", 10)
            c.setFillColor(campo_color)
            c.drawRightString(W/2 - 5, y_data, label)
            c.setFont("Helvetica", 10)
            c.setFillColor(valor_color)
            c.drawString(W/2 + 5, y_data, str(valor))
            y_data -= 22

    # Footer
    c.setFont("Helvetica", 9)
    c.setFillColor(colors.HexColor("#6A9FC0"))
    c.drawCentredString(W/2, 35, "www.euler.com.ar  |  info@euler.com.ar  |  CEL 341 5695849")

    c.save()
    buf.seek(0)
    return buf.read()


def build_condiciones_pdf() -> bytes:
    """Genera la página de condiciones comerciales."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2.2*cm, bottomMargin=2*cm
    )

    styles = getSampleStyleSheet()
    story = []

    # Header con logo pequeño
    header_style = ParagraphStyle("header", fontSize=9, textColor=EULER_DARK,
                                   alignment=TA_RIGHT, fontName="Helvetica")
    story.append(Paragraph("www.euler.com.ar  |  info@euler.com.ar", header_style))
    story.append(Spacer(1, 4*mm))

    # Título
    title_style = ParagraphStyle("title", fontSize=16, textColor=EULER_DARK,
                                  fontName="Helvetica-Bold", spaceAfter=4*mm)
    story.append(Paragraph("EULER — Calefaccion por Agua", title_style))
    story.append(HRFlowable(width="100%", thickness=2, color=EULER_ACCENT, spaceAfter=6*mm))

    sub_style = ParagraphStyle("sub", fontSize=13, textColor=EULER_MID,
                                fontName="Helvetica-Bold", spaceBefore=4*mm, spaceAfter=3*mm)
    body_style = ParagraphStyle("body", fontSize=10, textColor=GRAY_TEXT,
                                 fontName="Helvetica", leading=16, spaceAfter=3*mm)
    nota_style = ParagraphStyle("nota", fontSize=10, textColor=GRAY_TEXT,
                                 fontName="Helvetica", leading=16, leftIndent=10)

    # Forma de pago
    story.append(Paragraph("1) FORMA DE PAGO", sub_style))
    story.append(Paragraph(
        "Efectivo, transferencia, cheques/echeqs. (consultar por tarjetas de credito).", body_style))
    for item in ["Canieria: Al aprobar la oferta.",
                 "Equipos: A convenir.",
                 "Mano de obra de instalacion de equipos: A convenir."]:
        story.append(Paragraph(f"<bullet>&mdash;</bullet> {item}", nota_style))
    story.append(Spacer(1, 3*mm))

    # Plazo de entrega
    story.append(Paragraph("2) PLAZO DE ENTREGA", sub_style))
    for item in ["Provision de equipos: inmediato.",
                 "Canieria: Hasta 15 dias habiles a partir del comienzo del trabajo.",
                 "Instalacion de caldera y radiadores: 3 dias habiles segun tiempos de construccion."]:
        story.append(Paragraph(f"<bullet>&mdash;</bullet> {item}", nota_style))
    story.append(Spacer(1, 3*mm))

    # Notas
    story.append(Paragraph("3) NOTAS", sub_style))
    notas = [
        ("a)", "El presente presupuesto tiene validez de 10 dias habiles a partir de la fecha de confeccionado."),
        ("b)", "Para la instalacion del termostato de ambiente, se debe dejar un cableado desde la caldera hasta la ubicacion del mismo segun instrucciones nuestras."),
        ("c)", "Para el funcionamiento de la caldera se debe dejar una conexion de entrada de agua (a realizar por el cliente segun instrucciones nuestras) y es excluyente que la presion de agua a la entrada sea igual o superior a 1 kg/cm2. De no conseguir dicha presion por altura del tanque, se debe adicionar una bomba presurizadora."),
        ("d)", "La instalacion no incluye la instalacion electrica del tomacorriente, necesaria para el funcionamiento de la caldera."),
        ("e)", "El presente presupuesto NO incluye ningun trabajo ni material relacionado con la canieria de GAS, agua fria ni agua caliente sanitaria necesaria y excluyente para el funcionamiento de la caldera."),
        ("f)", "El trabajo de instalacion de canieria incluye el canaleteo de pisos y paredes y se entrega con la misma amurada y fijada, quedando a cargo del cliente el posterior tapado de las canaletas."),
        ("g)", "Puesta en marcha inicial (PEMIO): tiene por objetivo probar el sistema, ponerlo a punto, explicar el funcionamiento a los propietarios y activar la garantia de los equipos. Se realiza inmediatamente despues de finalizar la instalacion. Para realizarla se debe contar con todos los servicios (energia electrica, gas y agua) y con la presencia de los propietarios o responsables. De no cumplirse alguno de estos requisitos, la PEMIO se realizara en el momento que se cumplan dichos requisitos, con costo a cargo del cliente."),
        ("h)", "Condiciones de garantia: Calderas: 12 meses a partir de la PEMIO. La garantia puede extenderse 12 meses adicionales (logrando 24 meses totales) contratando un servicio de mantenimiento preventivo autorizado. Radiadores: 10 anios a partir de la PEMIO."),
    ]
    nota_label_style = ParagraphStyle("notalabel", fontSize=10, textColor=EULER_DARK,
                                       fontName="Helvetica-Bold")
    nota_text_style  = ParagraphStyle("notatext", fontSize=10, textColor=GRAY_TEXT,
                                       fontName="Helvetica", leading=15, leftIndent=18)

    for letra, texto in notas:
        story.append(Paragraph(letra, nota_label_style))
        story.append(Paragraph(texto, nota_text_style))
        story.append(Spacer(1, 2*mm))

    doc.build(story)
    buf.seek(0)
    return buf.read()


def build_cierre_pdf(datos_presupuesto: dict) -> bytes:
    """Genera la página de cierre con garantías y firma."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2.2*cm, bottomMargin=2*cm
    )
    styles = getSampleStyleSheet()
    story = []

    header_style = ParagraphStyle("header", fontSize=9, textColor=EULER_DARK,
                                   alignment=TA_RIGHT, fontName="Helvetica")
    story.append(Paragraph("www.euler.com.ar  |  info@euler.com.ar", header_style))
    story.append(Spacer(1, 4*mm))

    title_style = ParagraphStyle("title", fontSize=16, textColor=EULER_DARK,
                                  fontName="Helvetica-Bold", spaceAfter=4*mm)
    story.append(Paragraph("EULER — Garantias y Cierre", title_style))
    story.append(HRFlowable(width="100%", thickness=2, color=EULER_ACCENT, spaceAfter=6*mm))

    sub_style = ParagraphStyle("sub", fontSize=12, textColor=EULER_MID,
                                fontName="Helvetica-Bold", spaceBefore=5*mm, spaceAfter=3*mm)
    body_style = ParagraphStyle("body", fontSize=10, textColor=GRAY_TEXT,
                                 fontName="Helvetica", leading=16)

    # Garantías
    story.append(Paragraph("GARANTIAS", sub_style))
    garantias = [
        ("Calderas:", "12 meses de garantia a partir de la puesta en marcha inicial obligatoria (PEMIO). Extendible a 24 meses totales contratando servicio de mantenimiento preventivo autorizado."),
        ("Radiadores:", "10 anios de garantia a partir de la PEMIO."),
        ("Instalacion:", "Euler garantiza la correcta ejecucion de los trabajos. Cualquier inconveniente derivado de la instalacion sera atendido sin cargo durante el periodo de garantia."),
    ]
    for titulo, texto in garantias:
        t_style = ParagraphStyle("gt", fontSize=10, textColor=EULER_DARK,
                                  fontName="Helvetica-Bold", spaceBefore=4*mm)
        story.append(Paragraph(titulo, t_style))
        story.append(Paragraph(texto, body_style))

    story.append(Spacer(1, 8*mm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=GRAY_BORDER, spaceAfter=8*mm))

    # Datos del proyecto
    if datos_presupuesto.get("cliente"):
        story.append(Paragraph("PROYECTO", sub_style))
        tabla_datos = []
        campos = [
            ("Cliente", datos_presupuesto.get("cliente", "")),
            ("Direccion de obra", datos_presupuesto.get("direccion_obra", "")),
            ("N° Presupuesto", datos_presupuesto.get("numero_presupuesto", "")),
            ("Fecha", datos_presupuesto.get("fecha", date.today().strftime("%d/%m/%Y"))),
            ("Total", datos_presupuesto.get("total", "")),
        ]
        for label, val in campos:
            if val:
                tabla_datos.append([label + ":", val])

        if tabla_datos:
            t = Table(tabla_datos, colWidths=[4.5*cm, 12*cm])
            t.setStyle(TableStyle([
                ("FONTNAME", (0,0), (0,-1), "Helvetica-Bold"),
                ("FONTNAME", (1,0), (1,-1), "Helvetica"),
                ("FONTSIZE", (0,0), (-1,-1), 10),
                ("TEXTCOLOR", (0,0), (0,-1), EULER_DARK),
                ("TEXTCOLOR", (1,0), (1,-1), GRAY_TEXT),
                ("ROWBACKGROUNDS", (0,0), (-1,-1), [GRAY_LIGHT, WHITE]),
                ("TOPPADDING", (0,0), (-1,-1), 5),
                ("BOTTOMPADDING", (0,0), (-1,-1), 5),
                ("LEFTPADDING", (0,0), (-1,-1), 8),
            ]))
            story.append(t)
            story.append(Spacer(1, 8*mm))

    # Firma
    story.append(HRFlowable(width="100%", thickness=0.5, color=GRAY_BORDER, spaceAfter=6*mm))
    story.append(Spacer(1, 10*mm))

    firma_style = ParagraphStyle("firma", fontSize=10, textColor=GRAY_TEXT,
                                  fontName="Helvetica", alignment=TA_RIGHT, leading=18)
    story.append(Paragraph("Sin mas, saluda Atte.", firma_style))
    story.append(Spacer(1, 4*mm))

    nombre_style = ParagraphStyle("nombre", fontSize=12, textColor=EULER_DARK,
                                   fontName="Helvetica-Bold", alignment=TA_RIGHT)
    story.append(Paragraph("Ing. Nicolas F. Ayala", nombre_style))
    story.append(Paragraph("EULER CALEFACCION POR AGUA", ParagraphStyle(
        "emp", fontSize=10, textColor=EULER_MID, fontName="Helvetica-Bold", alignment=TA_RIGHT)))
    story.append(Paragraph("CEL 3415695849  |  www.euler.com.ar", ParagraphStyle(
        "contact", fontSize=9, textColor=GRAY_TEXT, fontName="Helvetica", alignment=TA_RIGHT)))

    doc.build(story)
    buf.seek(0)
    return buf.read()


def build_ficha_pdf(equipo_key: str) -> bytes:
    """Genera la ficha técnica de un equipo."""
    equipo = CATALOGO.get(equipo_key)
    if not equipo:
        return b""

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2.2*cm, bottomMargin=2*cm
    )
    story = []

    try:
        header_color = colors.HexColor(equipo["color"])
    except Exception:
        header_color = EULER_DARK

    # Header banner
    header_data = [[equipo["nombre"], equipo["categoria"]]]
    header_table = Table(header_data, colWidths=[W - 4*cm])
    header_table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), header_color),
        ("TEXTCOLOR", (0,0), (0,0), WHITE),
        ("FONTNAME", (0,0), (0,0), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (0,0), 14),
        ("TOPPADDING", (0,0), (-1,-1), 12),
        ("BOTTOMPADDING", (0,0), (-1,-1), 12),
        ("LEFTPADDING", (0,0), (-1,-1), 14),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 5*mm))

    # Encabezado Euler pequeño
    euler_style = ParagraphStyle("euler_hdr", fontSize=8, textColor=colors.HexColor("#888888"),
                                  alignment=TA_RIGHT, fontName="Helvetica-Oblique")
    story.append(Paragraph("EULER Calefaccion por Agua  |  www.euler.com.ar", euler_style))
    story.append(Spacer(1, 3*mm))

    # Descripción
    desc_style = ParagraphStyle("desc", fontSize=10, textColor=GRAY_TEXT,
                                 fontName="Helvetica", leading=16, spaceAfter=5*mm)
    story.append(Paragraph(equipo["descripcion"], desc_style))
    story.append(HRFlowable(width="100%", thickness=1, color=header_color, spaceAfter=4*mm))

    # Tabla de especificaciones
    spec_title = ParagraphStyle("stitle", fontSize=11, textColor=EULER_DARK,
                                 fontName="Helvetica-Bold", spaceBefore=3*mm, spaceAfter=3*mm)
    story.append(Paragraph("ESPECIFICACIONES TECNICAS", spec_title))

    specs = equipo.get("specs", [])
    if specs:
        # Dividir en 2 columnas si hay muchas specs
        if len(specs) > 8:
            mid = (len(specs) + 1) // 2
            col1 = specs[:mid]
            col2 = specs[mid:]
            while len(col2) < len(col1):
                col2.append(("", ""))
            table_data = []
            for (k1, v1), (k2, v2) in zip(col1, col2):
                table_data.append([k1, v1, k2, v2])
            col_widths = [4.2*cm, 4.8*cm, 4.2*cm, 4.8*cm]
        else:
            table_data = [[k, v] for k, v in specs]
            col_widths = [5.5*cm, 11.5*cm]

        spec_table = Table(table_data, colWidths=col_widths)
        row_count = len(table_data)
        ts = TableStyle([
            ("FONTNAME", (0,0), (0,-1), "Helvetica-Bold"),
            ("FONTNAME", (1,0), (1,-1), "Helvetica"),
            ("FONTSIZE", (0,0), (-1,-1), 9),
            ("TEXTCOLOR", (0,0), (0,-1), EULER_DARK),
            ("TEXTCOLOR", (1,0), (1,-1), GRAY_TEXT),
            ("ROWBACKGROUNDS", (0,0), (-1,-1), [GRAY_LIGHT, WHITE]),
            ("TOPPADDING", (0,0), (-1,-1), 4),
            ("BOTTOMPADDING", (0,0), (-1,-1), 4),
            ("LEFTPADDING", (0,0), (-1,-1), 7),
            ("GRID", (0,0), (-1,-1), 0.3, GRAY_BORDER),
        ])
        if len(col_widths) == 4:
            ts.add("FONTNAME", (2,0), (2,-1), "Helvetica-Bold")
            ts.add("FONTNAME", (3,0), (3,-1), "Helvetica")
            ts.add("TEXTCOLOR", (2,0), (2,-1), EULER_DARK)
            ts.add("TEXTCOLOR", (3,0), (3,-1), GRAY_TEXT)
        spec_table.setStyle(ts)
        story.append(spec_table)
        story.append(Spacer(1, 4*mm))

    # Conexiones
    if equipo.get("conexiones"):
        conn_title = ParagraphStyle("ctitle", fontSize=10, textColor=EULER_DARK,
                                     fontName="Helvetica-Bold", spaceBefore=3*mm, spaceAfter=2*mm)
        story.append(Paragraph("CONEXIONES / REFERENCIA", conn_title))
        conn_style = ParagraphStyle("conn", fontSize=9, textColor=GRAY_TEXT,
                                     fontName="Helvetica", leading=14,
                                     borderPad=6, backColor=GRAY_LIGHT)
        story.append(Paragraph(equipo["conexiones"], conn_style))
        story.append(Spacer(1, 3*mm))

    # Nota / Info adicional
    if equipo.get("nota"):
        nota_style = ParagraphStyle("nota", fontSize=8, textColor=colors.HexColor("#666666"),
                                     fontName="Helvetica-Oblique", leading=12,
                                     spaceBefore=4*mm)
        story.append(HRFlowable(width="100%", thickness=0.5, color=GRAY_BORDER, spaceBefore=4*mm, spaceAfter=3*mm))
        story.append(Paragraph(equipo["nota"], nota_style))

    doc.build(story)
    buf.seek(0)
    return buf.read()


def ensamblar_pdf_final(
    gesdatta_bytes: bytes,
    datos_presupuesto: dict,
    equipos_seleccionados: list
) -> bytes:
    """Ensambla el PDF final: portada + gesdatta + condiciones + cierre + fichas."""
    writer = PdfWriter()

    def add_pdf_bytes(pdf_bytes: bytes):
        reader = PdfReader(io.BytesIO(pdf_bytes))
        for page in reader.pages:
            writer.add_page(page)

    # 1. Portada Euler — usar original de la carpeta si existe
    ruta_portada = os.path.join(FOLLETOS_DIR, PORTADA_ARCHIVO)
    if os.path.exists(ruta_portada):
        with open(ruta_portada, "rb") as f:
            add_pdf_bytes(f.read())
    else:
        add_pdf_bytes(build_portada_pdf(datos_presupuesto))

    # 2. Presupuesto Gesdatta (sin modificar)
    add_pdf_bytes(gesdatta_bytes)

    # 3. Condiciones comerciales
    add_pdf_bytes(build_condiciones_pdf())

    # 4. Cierre y firma
    add_pdf_bytes(build_cierre_pdf(datos_presupuesto))

    # 5. Fichas técnicas — usar PDF original de la carpeta si existe
    for equipo_key in equipos_seleccionados:
        nombre_archivo = MAPEO_FOLLETOS.get(equipo_key)
        if nombre_archivo:
            ruta = os.path.join(FOLLETOS_DIR, nombre_archivo)
            if os.path.exists(ruta):
                with open(ruta, "rb") as f:
                    add_pdf_bytes(f.read())
                continue
        # Fallback: generar ficha con reportlab si no se encuentra el PDF
        ficha_bytes = build_ficha_pdf(equipo_key)
        if ficha_bytes:
            add_pdf_bytes(ficha_bytes)

    # Guardar
    output_buf = io.BytesIO()
    writer.write(output_buf)
    output_buf.seek(0)
    return output_buf.read()


# ─── Historial de presupuestos ────────────────────────────────────────────────
HISTORIAL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "historial")
HISTORIAL_JSON = os.path.join(HISTORIAL_DIR, "historial.json")
os.makedirs(HISTORIAL_DIR, exist_ok=True)

def historial_cargar():
    if os.path.exists(HISTORIAL_JSON):
        with open(HISTORIAL_JSON, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def historial_guardar(registro: dict, pdf_bytes: bytes):
    registros = historial_cargar()
    registros.insert(0, registro)
    with open(HISTORIAL_JSON, "w", encoding="utf-8") as f:
        json.dump(registros, f, ensure_ascii=False, indent=2)
    pdf_path = os.path.join(HISTORIAL_DIR, registro["archivo"])
    with open(pdf_path, "wb") as f:
        f.write(pdf_bytes)

# ─── Flask App ────────────────────────────────────────────────────────────────
app = Flask(__name__)
@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response

@app.route("/generar-pdf", methods=["OPTIONS"])
@app.route("/catalogo", methods=["OPTIONS"])
@app.route("/health", methods=["OPTIONS"])
def options_handler():
    return "", 204


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "message": "Euler PDF Backend activo"})


@app.route("/generar-pdf", methods=["POST"])
def generar_pdf():
    """
    Recibe JSON con:
      - gesdatta_pdf_base64: string (PDF en base64)
      - datos_presupuesto: dict {cliente, numero_presupuesto, fecha, total, direccion_obra}
      - equipos_seleccionados: list de keys del catalogo
    Devuelve el PDF final como archivo descargable.
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No se recibieron datos"}), 400

        gesdatta_b64    = data.get("gesdatta_pdf_base64", "")
        datos_presup    = data.get("datos_presupuesto", {})
        equipos         = data.get("equipos_seleccionados", [])

        if not gesdatta_b64:
            return jsonify({"error": "Falta el PDF de Gesdatta"}), 400

        # Decodificar PDF
        gesdatta_bytes = base64.b64decode(gesdatta_b64)

        # Generar PDF final
        pdf_final = ensamblar_pdf_final(gesdatta_bytes, datos_presup, equipos)

        # Nombre del archivo
        cliente = datos_presup.get("cliente", "cliente").replace(" ", "_")[:30]
        numero  = datos_presup.get("numero_presupuesto", "")
        nombre_archivo = f"Presupuesto_Euler_{cliente}"
        if numero:
            nombre_archivo += f"_{numero}"
        nombre_archivo += ".pdf"

        # Guardar en historial
        from datetime import datetime
        registro = {
            "id":       datetime.now().strftime("%Y%m%d_%H%M%S"),
            "fecha":    datetime.now().strftime("%d/%m/%Y %H:%M"),
            "cliente":  datos_presup.get("cliente", ""),
            "numero":   numero,
            "total":    datos_presup.get("total", ""),
            "equipos":  equipos,
            "archivo":  nombre_archivo,
        }
        try:
            historial_guardar(registro, pdf_final)
        except Exception:
            pass  # No interrumpir la descarga si falla el historial

        return send_file(
            io.BytesIO(pdf_final),
            mimetype="application/pdf",
            as_attachment=True,
            download_name=nombre_archivo
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/historial", methods=["GET"])
def get_historial():
    """Devuelve la lista de presupuestos generados."""
    return jsonify(historial_cargar())

@app.route("/historial/<id_registro>", methods=["GET"])
def descargar_historial(id_registro):
    """Descarga un presupuesto del historial por su ID."""
    registros = historial_cargar()
    registro = next((r for r in registros if r["id"] == id_registro), None)
    if not registro:
        return jsonify({"error": "No encontrado"}), 404
    pdf_path = os.path.join(HISTORIAL_DIR, registro["archivo"])
    if not os.path.exists(pdf_path):
        return jsonify({"error": "Archivo no disponible"}), 404
    return send_file(pdf_path, mimetype="application/pdf",
                     as_attachment=True, download_name=registro["archivo"])


@app.route("/catalogo", methods=["GET"])
def get_catalogo():
    """Devuelve el catálogo de equipos disponibles."""
    resumen = {
        key: {
            "nombre": eq["nombre"],
            "categoria": eq["categoria"],
        }
        for key, eq in CATALOGO.items()
    }
    return jsonify(resumen)


@app.route("/")
def index():
    return send_from_directory(os.path.dirname(os.path.abspath(__file__)), "euler_app.html")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5050))
    print("=" * 55)
    print("  EULER - Generador de Presupuestos PDF")
    print(f"  Backend iniciado en http://localhost:{port}")
    print("=" * 55)
    app.run(host="0.0.0.0", port=port, debug=False)
