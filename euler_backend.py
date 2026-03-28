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
from reportlab.lib.utils import ImageReader
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

# ─── Logo Euler (imagen real embebida en base64) ─────────────────────────────
EULER_LOGO_B64 = (
    "/9j/4AAQSkZJRgABAQAAAQABAAD/4gHYSUNDX1BST0ZJTEUAAQEAAAHIAAAAAAQwAABtbnRyUkdC"
    "IFhZWiAH4AABAAEAAAAAAABhY3NwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAQAA9tYAAQAA"
    "AADTLQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAlk"
    "ZXNjAAAA8AAAACRyWFlaAAABFAAAABRnWFlaAAABKAAAABRiWFlaAAABPAAAABR3dHB0AAABUAAA"
    "ABRyVFJDAAABZAAAAChnVFJDAAABZAAAAChiVFJDAAABZAAAAChjcHJ0AAABjAAAADxtbHVjAAAA"
    "AAAAAAEAAAAMZW5VUwAAAAgAAAAcAHMAUgBHAEJYWVogAAAAAAAAb6IAADj1AAADkFhZWiAAAAAA"
    "AABimQAAt4UAABjaWFlaIAAAAAAAACSgAAAPhAAAts9YWVogAAAAAAAA9tYAAQAAAADTLXBhcmEA"
    "AAAAAAQAAAACZmYAAPKnAAANWQAAE9AAAApbAAAAAAAAAABtbHVjAAAAAAAAAAEAAAAMZW5VUwAA"
    "ACAAAAAcAEcAbwBvAGcAbABlACAASQBuAGMALgAgADIAMAAxADb/2wBDAAUDBAQEAwUEBAQFBQUG"
    "BwwIBwcHBw8LCwkMEQ8SEhEPERETFhwXExQaFRERGCEYGh0dHx8fExciJCIeJBweHx7/2wBDAQUF"
    "BQcGBw4ICA4eFBEUHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4e"
    "Hh4eHh7/wAARCADmAzoDASIAAhEBAxEB/8QAHQABAAIDAQEBAQAAAAAAAAAAAAcIAQYJBQIEA//E"
    "AF0QAAEDAgMEAwYODwUFCAIDAAEAAgMEBQYHEQgSITFBUWETIjdxdYEUFRcYMlJWcpGUsrPR0iMz"
    "NkJVYnN0gpKTlaGisRY1tMLDQ1ODwfAkJjRFY2WE4VTxJUSj/8QAHAEBAAIDAQEBAAAAAAAAAAAA"
    "AAMEAQIFBgcI/8QANhEAAgEDAgUDAwIFBAIDAAAAAAECAwQREjEUITJBUQUiMwYTcTRhNUJyscEj"
    "gYKRobJS0fD/2gAMAwEAAhEDEQA/ALloiIAiHkvJxHiXD+HIoZb/AHqgtbJiWxOq52xh5HMDU8US"
    "yD1kWn+qhlx7ucO/vCP6U9VDLj3c4d/eEf0rbRLwY1Lybgi0/wBVDLj3c4d/eEf0p6qGXHu5w7+8"
    "I/pTRLwY1Lybgi0/1UMuPdzh394R/SnqoZce7nDv7wj+lNEvA1Lybgi0/wBVDLj3c4d/eEf0p6qG"
    "XHu5w7+8I/pTRLwNS8m4ItP9VDLj3c4d/eEf0p6qGXHu5w7+8I/pTRLwNS8m4ItP9VDLj3c4d/eE"
    "f0rbKeaKogjngkbLFI0PY9p1Dmkagg9Sw01uZTT2P6Ii1q8Y9wTZrlLbbtiuy0NZDp3WCesYx7NQ"
    "CNQTqNQQfOiTewbwbKi0/wBVDLj3c4d/eEf0p6qGXHu5w7+8I/pWdEvA1Lybgi8LDuMMK4iqpKWw"
    "YitdzniZ3SSOlqWSOa3XTUgHlqRx7V7qw01uZzkIiLACIiAIi16/Y3wfYa80F7xPaLdVhoeYamrZ"
    "G/dPI6E66LKTexhvBsKLT/VQy493OHf3hH9Keqhlx7ucO/vCP6VnRLwNS8m4ItesON8HX64C32XE"
    "9ouNWWlwhpqtkjyBzOgOugWwrDTW4TyEReXiLEFjw7Sx1d+u9FbKeSTubJaqZsbXO0J0BJ56AnTs"
    "WNzJ6iLT/VQy493OHf3hH9Keqhlx7ucO/vCP6Vtol4Mal5NwRaizM7LqR7WMxxh5znEBoFfHqT8K"
    "20cdFhprcJp7GURFgyEREAREQBERAEQ8lqlbmPgGhrZ6KsxlYqepp5HRTRSV0bXRvadHNI14EEEE"
    "LKTexhtI2tFp/qoZce7nDv7wj+lPVQy493OHf3hH9Kzol4GpeTcEWn+qhlx7ucO/vCP6U9VDLj3c"
    "4d/eEf0pol4Mal5NwRaf6qGXHu5w7+8I/pT1UMuPdzh394R/SmiXgal5NwRaf6qGXHu5w7+8I/pT"
    "1UMuPdzh394R/SmiXgal5NwRaf6qGXHu5w7+8I/pT1UMuPdzh394R/SmiXgzqXk3BF4GH8aYSxBX"
    "GhseJbTcqprDIYaWqZI8NGgJ0B104jj2he+sNNbmc5CIeS085oZcA6HHOHeH/uEf0oot7GG0jcEW"
    "n+qhlx7ucO/vCP6U9VDLj3c4d/eEf0rOiXgal5NwRaf6qGXHu5w7+8I/pT1UMuPdzh394R/SmiXg"
    "xqXk3BFp/qoZce7nDv7wj+lZGZ+XBOgxzh394RfSmiXgzqXk29F4Ftxrg25PDLfiyw1bydA2G4RP"
    "J8wcveDmkAggg9Kw01uMoyiIsGQiIgCIiAIiIAiIgCIiAIiIAiIgCJqvw3K82e2jW43Who/y9QyP"
    "5RCYyYyj9yLVajMfL6BxbJjjDTXDmPTOEn+DliHMnL2ZwDMc4aJ6AbnCP6uW2mXgal5NrRedbb7Y"
    "7kQLdebdW68vQ9SyT5JK9HULDTQygiIsGQiIgCIiAIiIAiIgCIiAIiIAq17dv3PYX/O5/kNVlFWv"
    "bt+57C/53P8AIap7b5YkVboZU5ERdc54REWQERFgBERZAREQBdLsE/cbZPJ8HzbVzRXS7BX3G2Ty"
    "fB821UL7aJatu5645KhG1N4esS++p/8ADRK+/QqEbU3h6xL76n/w0Sisvkf4N7jpIxREXTZS7lhN"
    "hjwhXvyT/qxq4Kp9sMeEK9+Sf9WNXBXKu/lZfodAREVYmCIiAKkW2X4Z5PJ1P/mV3VSLbL8M8nk6"
    "n/zKzafIV7npIXREXWZSJm2N/DVT/mM/yQrvqkGxv4aqf8xn+SFd9cq8+QvW/QFX7bl8Gtn8sN+Z"
    "lVgVX7bl8Gtn8sN+ZlUdv8qN6vSynaIi7BzkfqtH960f5dnygunQXMW0f3rR/l2fKC6dBUL7sW7b"
    "uZCIEVAtBERAEREAREQArnFm34VsX+XK35966Olc4s2/Cti/y5W/PvV2y6mVrnZGroiLolMIiIAi"
    "IsgIiIAshYWQhgnHYm8L9T5Hm+ciV01SzYm8L9T5Hm+ciV01yrvrL9v0Arl4/wBk7xrqGVy8f7J3"
    "jUtjuzS57HyiIr5UCIiAIiIDP/XNbBhbG2LsLytfYMRXGgDePc45j3I+OM96fOFryI4qS5oym1sW"
    "Wy62pK+CSKjxza46qEnQ19C3ckaOt0Z713bulviKsthLE1ixXao7rh+5QV9I/hvxu4sPtXNPFruw"
    "6Fc01sOA8Z4hwRfWXjD1e+mmBAljPfRTt9q9vJw/iOgg8VTq2kZLMeTJ4V2tzpJ0oo8yUzTsuZNl"
    "MtOG0d3p2j0bQudq5n4zT98wnp6DwPbIa50ouLwy5FprKCIiwZCIiAIiIAiIUAKw4jTmtAzWzYwp"
    "l3Tbt0qTVXN7N6G3U5Blf1F3Qxvae3QHkqjZoZ2Y0x0+WlkrDarQ46Cgo3FrXN/9R/Bz/EdG9gU9"
    "K3nU2Ip1YwLVZgZ5ZfYPfJTS3T00r2ag0tvAlLT1OfqGN48xrr2KCsY7UmLa9z4sN2mgs0B4CSXW"
    "om8ep0YPEWnxqvwGumnBe/hHBeK8WTdyw5Ya64cd10kUZ7mw/jPPejzkK7G2p0+cis605bH7cQ5k"
    "Y9xA53pti27zsdxMTagxxn9Bmjf4LVHOc9xc4kuJ1JPNT7hjZaxpXtbLfLtbLOx3NjdaiVvjDdG/"
    "A4qQLRspYThaPTXEd6q3Dn3BscLT5iHn+Ky7ijHYKlUkVBRXep9mnLCIAPprrMet9aQT+qAsz7NO"
    "WEjSGUlzhJ6WVrj/AFBWOMpjh5FIRqDqDoesLZsP5gY3sDmm0Yru9KxmmkYqXOj/AFHEtPwKzV22"
    "VMHSscbZiC+UbyP9t3KZo8wa0/xWg4l2V8W0TXSWG+2y6sbyZM11NI7xDvm/C4LKuKMtzH2qkT82"
    "EdqHGtteyPEFBb75APZvDfQ8x/SaNz+RTngDP3L7Fbo6aS4Osle/h3C4aRtcfxZPYHs1IJ6lTfGG"
    "A8YYQeRiLD1dQMB07u5m9CT2SN1Yfh1Wt/8AR7FiVvSqdJlVZw3OoTHNcA5rg5p4gjkQvrVc+8sc"
    "38aYCkjgt1eay2NPf2+sJfFp1N6WH3vDrBVusos5cKZhxspaeX0tvO7q+3VDxvnpJjdykHPlx4HU"
    "BUqttOnz3RYhWjIkpFhZUBMEREAREQBERAEREAVa9u37nsL/AJ3P8hqsoq17dv3PYX/O5/kNU9t8"
    "sSKt0MqciIuuc8IvXwZSwV2MLLRVUQlp6i4QRSsJ0DmukaCPgKvMMjcqvcdSft5vrqCtXVJrKJad"
    "NzKBIr/eoblT7j6X9vN9dPUNyq9x1L+3m+uouNh4N+GZQFFf71DcqvcdS/t5vrp6huVXuOpf2831"
    "04yHgcPIoCiv96huVXuOpf283109Q3Kr3HUv7eb66cZDwOHkUBXS3BPHBtk8nwfNtWoeoblV7j6X"
    "9vN9dSDR08VHSw0tPH3OGFjY42A67rQNAPgVa4rxq4SRNSpOB/VUJ2pvD1iX31P/AIaJX3VCNqbw"
    "9Yl99T/4aJbWXX/sYuOlEYoiLpspdywmwx4Qr35J/wBWNXBVPthjwhXvyT/qxq4K5V38rL9DoCIi"
    "rEwREQBUi2y/DPJ5Op/8yu6qRbZfhnk8nU/+ZWbT5Cvc9JC6Ii6zKRM2xv4aqf8AMZ/khXfVINjf"
    "w1U/5jP8kK765V58het+gKv23L4NbP5Yb8zKrAqv23L4NbP5Yb8zKo7f5Ub1ellO0RF2DnI/VaP7"
    "1o/y7PlBdOguYto/vWj/AC7PlBdOgqF92Ldt3MhECKgWgiIgCIiAIiIAVzizb8K2L/Llb8+9dHSu"
    "cWbfhWxf5crfn3q7ZdTK1zsjV0RF0u5TCKwOyDgXCmM4sTHE1miuJo3Uog33vbub3dd7TdcOe634"
    "FPvqG5Ve46l/bzfXVWpdRhLS0TRoOSyUBRX+9Q3Kr3HUv7eb66eoblV7jqX9vN9dacZDwbcPIoCi"
    "v96huVXuOpf283109Q3Kr3HUv7eb66cZDwOHkUBWVf31DcqvcfS/t5vrocjcqvcfS/tpvrpxkPA4"
    "ZldNibwv1Pkeb5yJXSWoYPy1wRhK6uumHcPwW+sdEYTKyR7juEgkd849LQtvVOtUVSWUWaUNEcAr"
    "l4/2TvGuoZXLx/sneNWbHdkNz2PlERXyoEVoNlDLfBOMMuq654jsEFwq47rLA2V8kjSGCKIhveuA"
    "0BcfhUveoblV7jqX9vN9dVZ3cYyw0TxoNrJQFFf71DcqvcdS/t5vrrByMyqI0/sfS+aeb661V7Dw"
    "Z4aRQNYV3MSbNWW1zhcLbT19lm0719NUukbr2tl3uHiIVeM3MjsW4AjluIDbxZGHU1tMwgxDoMrO"
    "JZ4xqO3oUsLmE3jY0lRlEipFlYU5Eevg3El2wniOkv8AZagwVdM7eb7V7eljx0tI1B7CugmVuNLb"
    "j7B1HiG3Hc7oNyogJ1MEwA32Hxagg9IIPSucimXZNx4/CmYcVmrJt21XxzaeQOPexz8on+cndPvg"
    "ehVbqjrjqW6JqNTS8F3xp1rKwFlcsvhERAERYPHUIA5V0z+2gobI6fDOBpoqi5t1ZU3EaOjpjyLY"
    "+hz+3kO066eRtPZ3SMmqsD4OrCwtJiuVfE7iD0wxkfA5w8Q6VV09en8Vet7bPukVatbtE/vX1dXX"
    "1k1bXVM1XUzPL5ZZXlz3uPSSTqSe1bNlzl3ivH1xNLh63ukijcBNWS95BD753X+KASR0KUMhMgKz"
    "FLYMR4xbNRWR2j4KQatmqx0EnmyM9fMjloCCrdWW1W6y22C22mhgoqOBu7FDCwNa0eIdPbzKkrXS"
    "h7YGlOi5c2Q7lts34Ow62OsxEP7R3EcSJmbtMw9Qj++6u+JHYFNVHTU9HTx01LBHBDGN1kcbQ1rR"
    "1ADgAv6rOi586kpPmy3GCjsERFqbBERAEPJE1HWgP5zRRzRPimjbJG9u65jhqHDqIPMKHcydnfBG"
    "KGy1VohGHbkdSJKSMdwc78aLgP1d3zqZisEjRbRnKLzFmsoqW5zxzOyvxbl7V7t7oO6UTnbsNfT9"
    "/A/qGumrT2EA+PmtNpppqaeOemlkilicHMfG4tcxw4ggjkdV03uNFR3GimobhSw1dLMwskhmYHse"
    "09BB4FVSz62eJrTFPiPAcMtTQNBfUWzUvlgHS6LXUub+Ke+HaOXQo3SlymVZ0NPOJ7OQW0N6IfT4"
    "azAqWtlOkdLd3nQO6mzHoP4/63S5WbaQ4BwIII1BC5fHXXt/6/8ApWL2ZM75LRNS4MxfWF1seRFb"
    "66V3/hieUbyf9n0A/e+99jpXtv5oG1Kt2kW4BWV8tX0qBaCIiAIiIAiIgCrXt2/c9hf87n+Q1WUV"
    "a9u37nsL/nc/yGqe2+WJFW6GVOREXXOee7l7932HfKlN861dJ1zYy9+77DvlSm+dauk6597ui5bb"
    "MDmsrHSsqiWQiIgCIiAIiIAqEbU3h6xL76n/AMNEr7qhG1N4esS++p/8NErll8j/AAV7npRGKIi6"
    "TKXcsJsMeEK9+Sf9WNXBVPthjwhXvyT/AKsauCuVd/Ky/Q6AiIqxMEREAVItsvwzyeTqf/MruqkW"
    "2X4Z5PJ1P/mVm0+Qr3PSQuiIusykTNsb+Gqn/MZ/khXfVINjfw1U/wCYz/JCu+uVefIXrfoCr9ty"
    "+DWz+WG/MyqwKr9ty+DWz+WG/MyqO3+VG9XpZTtERdg5yP1Wj+9aP8uz5QXToLmLaP71o/y7PlBd"
    "OgqF92Ldt3MhECKgWgiIgCIiAIiIAVzizb8K2L/Llb8+9dHSucWbfhWxf5crfn3q7ZdTK1zsjV0R"
    "F0e5UW5abYL+0Yw99Rf0nVn1WDYL+0Yx99Rf0nVn1yLn5WX6HQgiIoCUIiajrQBERAEREAK5eP8A"
    "ZO8a6hlcvH+yd41fsd2VbnsfKyFhZCvlQuXsPeCa5eW5vmYFPKgbYe8E1y8tzfMwKeVxq3yM6NLo"
    "QREURIF8TxMmhfDIxr2PaWua4agg8wR0hfaHkgKU7UmU8WCbszEdgg7nYbjKWuiaOFJNxO57xw1L"
    "erQj2qhBdIMzcMwYwwHd8PTsBdV0zhC4/eSjjG7zODSucDmuY4se0tcDoWnmCOhdW1quccPsUa0F"
    "F5RhfUb3xSNlje5j2EOa5p0II4ghfKKzuiHJ0eyrxH/a3Lyx4hJBkrKRpm05d1b3sgHZvtctnUF7"
    "FFzfWZT1NDI7U0FzljYNeTHNY/5TnqdFxKkdM2jo03mKYREWhuYdyUE7VWbDsI2g4UsFSG324REy"
    "ysPfUkJ4a9j3cQOoan2qlTMnFlBgnBdxxHcCHMpo/sUW9oZpDwYweMkeIanoXO/E17uWI7/W3y7T"
    "metrZjNK48tT0AdAA4AdQVu1o65ansivXqaVhHnE6niSde3irKbMGSLLiymxvjCkDqQ6SW2hkbwm"
    "6ppAfvOlrT7LmeGmuobMGVYx1iJ17vMBOH7ZIO6NI4VU3AiLtaBoXdhA6dVdxjQxgY1oaANAAOAU"
    "t1Xa9kTSjSz7mZaNF9IEXPLYREQBDyROhYYKmbUmamJrTmpS2TD1ynt8diEU7xGft072h/fjk5u4"
    "9o3Tw4u15qwWTeL6nHWAaDElXa5LdNOHMcwnVkhadC+PjruEg6a8RoRx5msW2jhiotuZEOJWxl1H"
    "eKZgL+gTRNDC39QMI6+PUpG2L8eR3LDU2Bq14FZaw6ajJ/2lO52rh42vd8Dh1K7Upp0VKKK0JNVG"
    "mTtim6x2LDV0vczC+O30ctU9oOhcI2FxHn0VQMmc78Zw5mkXN1TfaW/VjWS0TDxie4hrTCCdG7o0"
    "G7wBA46EAq4GJ7XFfMN3OzTuLYq+klpXnqD2FpP8Vzngdd8D43je5ncLrZK4EtcOAkifyPW06ecF"
    "YtoRnGSe4rNxaaOk+ihLa8xzcsJ4Io7XZ6iSlrL1M+J08btHshYAXhp6CS5o16iVKOA8S0GMMI27"
    "EdtJ9D1sIfuE6mN3J7D2tcCD4lEu2jheovGXdHfaVjpH2WpL5gByhkAa53mIZ5tSoaKSqJSJKj9m"
    "UfeydmZfMa2irsl9pZqqe0xs0umuola7UNZJrx7pwPEa6gHXiNXToepUi2Ssdx4SzA9J694Zbr9u"
    "U7nnlHOCe5OPYS5zT74HoV3QtrmGifJGKMtUSs207kgyphqcb4Pow2oYDLcqCJvCUczLGPbcy5vT"
    "zHHXWqh6/h0XUR3JU22r8qmYXu39sLDTBtmuEulVCwd7SznpHUx3R1HUcAWhWLWvn2SIq1L+ZG/b"
    "JObD7zSR4ExFU71xpYz6WzyO4zxNH2snpc0cR1tH4vGxfSuYtpuFZabpTXO3TyU9XSytlhkYeLHt"
    "OoI866E5O43pcwMC0N/h3I6kgw1sDT9qnb7IeI8HDscFpdUdD1LY3oVNSwzckTgiplgIiIAiIgCr"
    "Xt2/c9hf87n+Q1WUVa9u37nsL/nc/wAhqntvliRVuhlTkRF1znno4YuEdqxLa7pKx746OshqHtZz"
    "cGPDiB8CtYNq3CfuZvf60X1lUJFFUoRqbkkKkobFvvXXYT9zV7/Wi+snrrsJ+5q9/rRfWVQUWnCU"
    "/Bv9+Xkt9667Cfuavf60X1k9ddhL3NXv4YvrKoKLHCUvBj78/J0JydzLtmZdsrq+2W+somUc4he2"
    "oLdXEt11G6TwW+Kuewp9x+IvKDPmwrGLn1oqE2kXKcnKOWERFEbhUI2pvD1iX31P/holfdUI2pvD"
    "1iX31P8A4aJXLL5H+Cvc9KIxREXSZS7lhNhjwhXvyT/qxq4Kp9sMeEK9+Sf9WNXBXKu/lZfodARE"
    "VYmCIiAKkW2X4Z5PJ1P/AJld1Ui2y/DPJ5Op/wDMrNp8hXuekhdERdZlImbY38NVP+Yz/JCu+qQb"
    "G/hqp/zGf5IV31yrz5C9b9AVftuXwa2fyw35mVWBVftuXwa2fyw35mVR2/yo3q9LKdoiLsHOR+q0"
    "f3rR/l2fKC6dBcxbR/etH+XZ8oLp0FQvuxbtu5kIgRUC0EREAREQBERACucWbfhWxf5crfn3ro6V"
    "zizb8K2L/Llb8+9XbLqZWudkauiIuj3KZMGzjmxaMsY7426WyurfTEwGP0MWjd7n3TXXeI5745KX"
    "vXXYT9zV7/Wi+sqgooZW1OTyyWNaUVgt9667Cfuavf60X1k9ddhP3NXv9aL6yqCi14Sl4Nvvy8lv"
    "vXXYT9zV7/Wi+ssHauwnp9zV7+GL6yqEhWHaU8bD78snUKM6tDusL7X84PtTPehf0XKxgurYIiIZ"
    "BXLx/sneNdQyuXj/AGTvGr9juyrc9j5WQsLIV8qFy9h7wTXLy3N8zAp5UDbD3gmuXlub5mBTyuNW"
    "+RnRpdCCIiiJAiIgB5Fc0scMijxrfY4QBG241DWae1EjtF0Xxhe6bDmFbnfqtzRDQUr5yCfZFo1D"
    "R2k6AdpXNSpmkqamSomdvSyvL3k9JJ1J/ir9knzZVuXsfzREXQKiLa7Cbnf2XxK0+xFbER49w6/0"
    "CsgoD2ILe6nyyuVe9unou6P3O1rY2DX4S4eZT4uNcPNRnQo9CBWCsnkvHxpfafDOE7riCq0MVBSv"
    "nLSdN8gcGjtJ0A8ahSy8EjeOZVLbOxw674vgwdRza0Nn0kqd08H1Lm8v0GHTxucFCWFbHX4lxHb7"
    "DbI+6VldM2KIHkNebj+KBqSeoFfmu1fVXW6Vd0rZTLVVcz55nnm5znbzj8JVktiPBjZai545rIQe"
    "5E0VDqOTtAZHjzFrQfxnBdZtUKRRSdSZYvAOGLbg7Cdvw7a2aU9HEGl5Ghkf9893a46nz6cl7ywB"
    "xWVyW2+bLyWFgIiIZCIiAHksDksogI12lrRbLrkzf3XMxs9BQ+i6aV2mrJmexAPW7Xc/SVStmitq"
    "aHO7Db6Yu1lndDIB98x8bgdewc/MFe/EVot+ILHW2W6QNnoqyIxTMPSD0jqI5g9BAKgrITIitwXm"
    "JcMRXyaKaGgfJDZ90gulDhoZnD73vSW7vPUu6ANbVGrGNOUWQVKbc00WE6CqdbblotdDj61XOkMb"
    "a64UZNZG3mSwhrJCO0at/wCGriaqItpXKs5g4cirrPDGcQ2/hTkkNE8RPfROcdAPbAnkdR0lR281"
    "CabNq0dUcI1rYbramXL680UjnOgprlvREnlvRt3gOzVuvnKn2vpaeuoZ6KshZPTVEbopY3jVr2OG"
    "hBHUQStNyRwJFl3gKlsRlZPWPeaitmbyfM4DXTsADWjrDdeGq3joWtWSc20ZgmoJM5oYopaa1Ytu"
    "lFa6ozUtHXzRU07H6l7GSODHh3aADquj2F6ueuw1a66pGk9RRwyyDqc5gJ/iVX3GWzkLpnHT3K3d"
    "ypsK1b/RVfG1wa6J4cC+KNo6H8wRwb33UAbIRMbGxrGMDWNGgaBoAprirGajgjpQcW8n9CvLxRZL"
    "fiPD9bYrrAJqKthMUzenQ9IPQQdCD0EAr01kqqnjmifc5s5g4XrcGYxuWG7gN6WjlLWvA0EkZ4se"
    "OxzSD2a6dakvZFxy7DOYrbFVy7tuvu7TkOPBlQPtTvOSWfpDqUk7beDBVWS343o4fs1E4UlaQOJh"
    "efsbj715Lf8AiDqVT4JZIJmTwyOjljcHMe06FpB4EeJdaDVelgoNfamdQBzX0tXyqxOzGOX1lxGN"
    "3ulXTAztHJszdWyAeJ7XLaFymsPDL6eVkIiLBkIiIAq17dv3PYX/ADuf5DVZRVr27fuewv8Anc/y"
    "Gqe2+WJFW6GVOREXXOeEX0xjpHtYxpc9xAa0DUknkAvQ9Ib5+Brj8Vf9CNpbmUmzzUXpekN8/A1x"
    "+Kv+hPSG+fga4/FX/Qsal5GlnmovS9Ib5+Brj8Vf9CekN8/A1x+Kv+hNS8mcMtPsKfcfiLygz5sK"
    "xir1sQUVZRYSxAyspJ6Zzq9haJYywkdzHLVWFXIuPkZeo9CCIihJQqEbU3h6xL76n/w0SvuVQjam"
    "8PWJffU/+GiVyy+R/gr3PSiMURF0il3LCbDHhCvfkn/VjVwVT7YY8IV78k/6sauCuVd/Ky/Q6AiI"
    "qxMEREAVItsvwzyeTqf/ADK7qpFtl+GeTydB/mVm0+Qr3HSQuiIusUiZtjfw1U/5jP8AJCu+qQbG"
    "/hqp/wAwqP6BXfXKvPkL1v0BV+25fBrZ/LDfmZVYFV+25fBrZ/LDfmZVHb/Kjer0sp2iIuwc5H6r"
    "R/etH+XZ8oLp0FzFtH960f5dnygunQVC+7Fu27mQiBFQLQREQBERAEREAK5xZt+FbF/lyt+feujp"
    "XOLNvwrYv8uVvz71dsupla52Rq6Ii6JTCL9NFQV1cHmioqmp3NN/uMTn7uvLXQcORX6fSG+fga4/"
    "FX/QsakZwzzUXpekN8/A1x+Kv+hPSG+fga4/FX/QmpeRpZ5qFel6Q3z8DXH4q/6Fj0hvn4GuPxV/"
    "0LDkvIUWdMYPtLPehfa+IPtLPehfa4b3OogiIgBXLx/sneNdQyuXj/ZO8av2O7Ktz2PlZCwshXyo"
    "XL2HvBNcvLc3zMCnlV72KrnbaPKu4RVlwpKeQ3qVwbLM1pI7jDx0J5cD8CnP0+sf4Zt3xln0rj1o"
    "v7jOhSa0o9FF53p9Y/wzbvjLPpWHX+xAam9W4D86Z9Ki0vwSZR6SwTwWm4kzSy9w/A+S54utQc3n"
    "FBOJ5PFuR6u/gq6ZwbSdwvdLPZsEQT2qikBZJXy6Cpe08CGAHSMdupPL2JUkKE6jwkaTqxij922D"
    "mhBcX+p/Y6hssMMofdZWHVrpGnvYe3dPF3aAOgqtSySS4lxJJOpJPM9awutSpqnHCKM5ankIsqSd"
    "nHBD8b5mUUFRAX2y3uFZXEjVpa097Gffu0GnVvHoWZy0RcmYjHLwXFyNw4/CuVWH7PLGWTspRNUN"
    "I4tlkJkcD4i4t8y3ZYCyuJJ5bZ0orCwCoF218QG25a0diifpJd6wB415xRd+7+cxKejyVOduC7Gq"
    "zFtVoa/ejobcJCOp8r3a/wArGKa2hqqIjrPESARxI6+S6L5PYabhHLWx2Ix7k0FK11QNP9s/v5P5"
    "nEeIBUTydszb/mlhu1PbvxTXCJ0reuNh33j9Vrl0YCnvZ7RIraPcyeSx0LJ5LB4DkqBaA5rOijK/"
    "4xvVHequlhfD3OKUtbrHqdAvw/27v/8AvKf9kvNVfquypzcHnK/Y7VP0G6qQU1jD/cloool/t3f/"
    "APeU/wCyUgYLuNTdMPw1lUWmVznAlo0HBxCt+neu23qFR0qWc4zzRXvPSq9pBTqYxse0iaIu2c0d"
    "Kf8AXJQNmrmfirD2PLjaLdLSNpYO57gfDvHvo2uOp8ZK1f1aMb/7+h+L/wD2ubU9UoU5OLzyPVW3"
    "0d6jc0Y1oYxJJrn5LQrGnFVf9WjG/wDv6H4v/wDak7IbGt8xfJeG3h8DxSiExdzj3dN7f11/VC2o"
    "epUa01CO7IfUPpW+sLeVxVxpWO/l4JTCzqtIz0xLdMIZV3nEVmdE2vpO4dyMrN9vfTxsOo6eDiqr"
    "+uWzQ/8AybX8SH0rq0qEqiyjy06sYPDLvoqQeuWzQ/8AyrX8SH0r1MIbRGZFzxbZ7bVVNsNPV18E"
    "EobRgHdfI1p0OvUVI7Solk1VeLLlosNWVWJzxcdWCDFGDrth6pDQyvpXwhxGu44jvX+MO0PmXNmq"
    "glpqqWlqGGKaF5jkYebXA6EfCCuoB5Ln7tHWZtjzpxJSxs0imqRVs6B9laJDp+k5w8yvWUubiVbm"
    "OzJz2GsQGpw1fMNTP1dRVLauEE/eSDdcB2AsB8b1Y9Uk2NLsbfnLHQl+jbnQTU+nWWgSjz6Rn4Sr"
    "tqG6jpqMkoSzAIiKuTBERAFWvbt+57C/53P8hqsoq17dv3PYX/O5/kNU9t8sSKt0MqciIuuc893L"
    "37vsPeVKb51q6TAdnFc2cvfu+w75UpvnWrpOufe7ot22zCaIs6KiWcGNEIWdEQYMALKIhkIiIAeS"
    "ojtaUzoM9r5I4cKiOmkb4u4Mb/VpV7jyVQ9uWyOp8Z2TEDGfYq2idTOIH38TydT4xIPgVm0lioQX"
    "CzArsiIutsUScdiq5xUWbk1FK4N9MLZLDGCeb2uZIP5WPV1DouaODb/WYWxTbcQ0B/7RQVDZmjXQ"
    "PAPFp7CNQewrovhC/wBuxRhugv1pmEtHWwiSM9Letp6nA6gjoIK5l5BqWou28uWD10TqRUywEREA"
    "KoftXXOO5Z3XkQuD2UjIaXeB5ubGC74HOcPMrl5m4vt+B8GV+Ibg5pFPGRBEToZpT7Bg8Z+AanoX"
    "Om719VdbrV3SulMtXVzPnmefvnvcXE/CSr1lD3ORWuJcsH5URF0CmTfsV0zp84pJWjvae1TSHzuj"
    "b/mV1lVvYUsbw/EmI5GEM+xUULus8XyD5v4VaRcq7earL9BYiFX7bl8Gtn8sN+ZlVgVX7bl8Gtn8"
    "sN+ZlWlv8qNqvSynaIi7BzkfqtH960f5dnygunQXMW0f3rR/l2fKC6dBUL7sW7buZCIEVAtBERAE"
    "REAREQArnFm34VsX+XK35966Olc4s2/Cti/y5W/PvV2y6mVrnZGroiLolPuWl2DPtGMPfUXDq+3q"
    "z+irBsF/aMY++ov6Tq0Gi5Fz8rL9BexGNE0WdE0UBLgxohHBZ0RBgwBosoiGQiIgBXLx/sneNdQy"
    "uXj/AGTvGr9juyrc9j5TxoivlQcelERORkIiLGEMsysIiyYCIv12i2XC8XKC2WujmrKyofuRQxML"
    "nPPi/wCuCN4GPB822hrLlcKe32+mkqauokbFDFG3Vz3k6AAeNX5yEy6p8ucFR29+5Jdaoia4zN5O"
    "k04MB9q0HQdZ1PStZ2d8lKbAVO2/X0RVWJZmaDQ7zKNhHFjD0vIJBd5hw1LpoA4rmXNfX7VsXaNL"
    "TzZkIiKoWAqF7VNYavPXEHHVsBghb2BsEev8xKvoVz42hiXZ14qJ5iuPwBrQrlks1Cvcv2mybHlC"
    "2rztopyP/B0dRMPGWbn+orxDxKmew+0OzZuJOne2SYjx93gH/NXNWt281DNusRCx0LKx0KoychHF"
    "n3TXH8u7+q8tepiz7prj+Xd/VeWviN9+pqfln06z+CH4X9gFLuWn3I03v3/KKiIKXctPuRpvfv8A"
    "lFeh+jv1z/pf90cj6j/Sr8/4ZsyweaysHmvpp4gqjn34V7x/wfmWLRVvWffhXvH/AAfmWLRV4q7+"
    "ef5Z9+9D/htD+mP9kFOOyh9uxH72m/rKoOU5bKH27Efvab+sqn9L/Ux/3/sc/wCr/wCEVf8Aj/7I"
    "2faq8AmJP/jf4qJUKV9dqrwCYl/+N/iolQpfQrLof5Pglz1Be9l34QMOeVaX51q8Fe9l34QMOeVa"
    "X51qsz2ZAtzpOEQIuGdQFUy23KJtPmpQVbAAKq0xl3a5skjf6bquaeSqRt1tAxXhx401NDID4g/h"
    "/UqzaP8A1UQ117SLNn+sdQ50YVmadC64Mh80gMZ+UuhIXOLKVxbmrhJw11F7ouX5di6Ohb3q9yNL"
    "bYyiIqZZCIiAKte3b9z2F/zuf5DVZRVr27fuewv+dz/Iap7b5YkVboZU5ERdc557uXv3fYd8qU3z"
    "rV0nC5iWytnttypbjSkNqKWZk0RI1Ac1wcOHjClj1yOaQ/8AMbf8RYqlzQlUawWKNRQ3LyJqqOeu"
    "SzS/CFv+IsT1yeaX4Rt/xFircHUJuIgXj1TVUc9cnml+Ebf8RYnrk80vwjb/AIixOCqDiIF49U1V"
    "HPXJ5pfhG3/EWJ65PNL8I2/4ixOCqDiIF404Kjnrks0j/wCY2/4ixXRwzVTV2HbbW1BDpqikilkI"
    "GgLnMBPi4lRVaEqW5vCop7Honkot2oMHuxdlPXCmi7pXWs+j6doHF24CHtHTxYXaDpIClJCNQVHG"
    "TjLJvJalg5eLClbaXy4kwHjiSpooC2xXRzp6JzR3sTidXw9m6TqPxSOoqKV24TU1lHNlHS8BSpkJ"
    "nBcct7i+kqmSV2H6qQOqKYHv4ncu6R9GummrTwcAOIPFRWspOCmsSEZOLyjpNgvF2HsYWptzw7da"
    "eugPB4YdHxH2r2nvmnsIC97VcxrPdbnZq5ldaLhVUFUzg2ammdG8Dq1bodFI9q2gc1aCJsX9o21T"
    "GjQeiaSJ5/W3d4+clUJ2Uv5WWY3K7l8SeC1jH+PML4FthrsRXOKmJaTFTtO9NMepjOZ8fIdJCpje"
    "c+81LnC6F2JnUkbhoRS08cTvM4N3h8Kjm411bcqySsuFZUVlTIdXzTyOe9x7XE6lIWTz7mZlcLsb"
    "znZmld8yr62adrqO00pIoqEO1DNeb3dDnnr5AcB0kx6iLoRiorCKjbbywstBc4NAJJOgA6VhTdsn"
    "ZbyYrxg3EtygJstmlDxvN72eoGhYztDeDj5h98tak1COWZhHU8Fm8hcIOwTlhabPPHuVr2GpreHH"
    "u0nEg9rRoz9Fb4sDnyWVxZNyeWdJLCwFX7bl8Gtn8sN+ZlVgVX7bl8Gtn8sN+ZlUtv8AKjSr0sp2"
    "iIuwc5H6rR/etJ+XZ8oLp01cvoJHQzMmYQHscHNJGvEHVS965HNL8IW74ixVbmjKrjST0aihuXjW"
    "dVRz1yWaX4Qt/wARYnrk80vwjb/iLFV4OoT8RAvHqmqo565PNL8I2/4ixPXJ5pfhG3/EWJwVQcRA"
    "vHqmqo565PNL8I2/4ixPXJ5pfhG3/EWJwVQcRAvGsaqjvrks0j/5hb/iLFYzZhxtf8e4DrrviKaG"
    "aqhuklMx0UQjG4IonDgOnV7lHUt5U1lm0K0ZPCJX6Fzizb8K2L/Llb8+9dHehc4s2/Cti/y5W/Pv"
    "U9l1MjudkauiIuiyn3LS7Bf2jGHvqL+k6tBqudmW2ZeKsvhXjDVRTQ+jjGZ+6wCTXc3t3TXl7Mrc"
    "PXJ5pfhG3/EWKhWtZzm5It068YxSZePVNVRz1yeaX4Rt/wARYnrk80vwjb/iLFFwVQ34iBePVNVR"
    "z1yeaX4Rt/xFieuTzS/CNv8AiLE4KoOIgXjRUc9clml+ELf8RYnrks0vwhbviLE4OoOIgXjCKtez"
    "Pm9jXHWYc9mxDV0ktIy3yVDWxUzYzvtfGAdR2OKsooJ03TeGSxkpLKBXLx/sneNdQyuXj/ZO8auW"
    "O7K9z2PlZWEV8qBFY/ZiykwXjzAVbeMRUdTPVRXOSmY6OpdGNxscTgNAet5UrDZwysH/AJVXH/50"
    "v0qtK6hF4JlQk1lFGkV5xs45VfgasPjr5frL69bplSP/ACOqPjr5vrLXjYGVbyKLIpE2g8CR5f5i"
    "1Nroo3stVTG2poN5xdow6gt1PMtcHDr00PSo7VqMlJakQtNPDCtTsN1lhlor5QegKZl+ge2X0Tu6"
    "yyU7tBugnkGuHEDQd83mqrLd8jsXuwRmbab3JIWUZk9D1vbBJwcT706O8bQo68HKDSN6UsSWToaO"
    "ayvljg4BwIII1BC+lxjohERACuf+0tTmmzyxRGeGtQyT9aJjv8y6AFUj2y7c6izmkq93hX2+CcEd"
    "Om9Gfmwrdm8VCvcr2n9tiypEGcUsROhqLVNEPHvRv/yK6yoBs03QWjO/DU73aMmqHUruPPurHRt/"
    "mc1X+S8WKhm3eYmVjoWVjoVNk5COLPumuP5d39V5a9TFn3S3H8u7+q8tfEb79TU/L/ufTrP4IfhA"
    "KXctPuRpvfv+UVEQUu5afcjTe/f8or0P0d+uf9L/ALo5H1H+lX5/wzZlg81lYPNfTTxBVHPvwr3j"
    "/g/MsWires+/CteP+D8yxaKvFXfzz/LPv3of8Nof0x/sgpx2UPt2I/e03+qoOU5bKHCTEevtab/V"
    "U/pf6mP+/wDY531f/CKv/H/2Rs+1V4BMS+Km/wAVEqFK+u1V4BMS+Km/xUSoUvoVl0P8nwW56gve"
    "y78IGHPKtL861eCvey78IGHPKtL861WZbMgW50nCIEXDOoCqf7c9SH4/sdJrxitfdD+lK8f5FcA8"
    "lRfa6uguOdtxha7ebQU8FKDzGu4HkfC8/ArNos1CCu8RNSyVpzU5vYSjA4i8U0n6sjXf8l0UHJUO"
    "2U7abjnjYzu70dIJql/ZuxOAP6xar5La9eZo1tl7QOSIiqFkIiIAq17dv3PYX/O5/kNVlCq17dv3"
    "P4X/ADuf5DVPbfLEirdDKnIiLrnPCIiAIiIAiIgCIiALpdgn7jbJ5Pg+bauaK6XYK+42yD/2+D5t"
    "qo32yLVt3PXHJDyToRc8tmu5hYQtGN8K1WHrzEXQTDeZI32cEg9jI09BH9CRyKoNmdgS+Zf4kks1"
    "6h1bxdTVTQe51Eftmn+o5jp6F0aOui8DHeD7DjWxS2bEFC2pp3cWOB0khf0PY7m1w/8Ao6jgrFCu"
    "6b57ENWkpnNpFMWbmQWK8GSTV9oilv1kHfCanj1mhb/6kY48PbN1HSd3kodPA6FdSE4zWUylKDjy"
    "YREW5qERFgBF9Ma572sY0ueTo0AaklThlBs7YkxPJDcsVNmsVnJDu5vbpVTt6mtPsBz753HqBWs6"
    "kYLMjaMHLY0XJ7LW95j4jbQUDXQUELga6uc3VkDeoe2eehvw8NSr64Qw7asKYeo7DZaYU9FSR7jG"
    "8y48y5x6XE6kntX1hPDtmwtZYLNYaCKiooR3sbBzPS5xPFzj0k8V62i5Veu6r/YvU6SgYCyiKAlC"
    "r9ty+DWz+WG/MyqwKr9tyeDWzH/3hvzMqmt/lRHV6WU7REXYOcgiIgCIiAIiIAiIgCuVsOeCm6eX"
    "ZfmIFTVXK2HPBTdPLsvzECrXfxk9DqJ76Fzizb8K2L/Llb8+9dHehc4s3PCvi/y5W/PvVey6mS3O"
    "yNXREXRKYREQBERAEREAWQsLI5oCcdibwv1Pkeb5yJXTVLNibwv1Pkeb5yJXTXLu+svUOgFcvH+y"
    "d411DK5eP9kfGpbHdmlz2PlZCwivlQuZsPeCa5eW5vmYFPKgbYe8E1x8tzfMwKeVxq3yM6NLoQKw"
    "VlPMoSQhDbCwacQZbi/UsO9XWJ5nOg4up3aCUebRrvE09apV0di6e19NBW0U9HVQtmp543RyxuGo"
    "e1w0IPYQVzlzOwtPgzHl2w5PvkUk5EL3c5IXd9G7ztI8/iXRs6mVpZTuIYepGtoiK9+SsXx2XcYj"
    "FuVVC2ol36+0/wDYanU8SGAdzcfGwt49JDlKipFsh4x/s5mcyz1Mu5Q31gpnAnvROOMTvGTvN/TV"
    "3Bz1XHuKeibOhRlqiZREUJKFWPbqsZfRYcxJHHwikloZne+AfGP5ZPhVnDyWgbQOGHYsylvdtij3"
    "6qKH0VSgDUmSLvwB2uAc39JSUZ6JpmlSOYsoHaK6otd1o7nSHSopJ2TxHqcxwcP4gLpbYLlTXmx0"
    "N3o3b1NW08dREfxXtDh/ArmR0q6mxvi5t8y1dYZ5Qauxy9y0J4mB+roz5jvt8TQrt7DK1eCtbyw8"
    "E4r5PJZ1QrmlxEJ4wYWYnuAPD7O4j+q8lbZmjQOpr/6MDfsdUwHX8ZoAI+DRamvi/q1CVC8qQl5Z"
    "9K9OqKrawa8IKV8rpmyYYbGDxilc0+fvv+aigc9VuWVt0bS3OS3TODWVI1YSeG+Ojzj+i6P0xdRo"
    "X8dT5S5FP12g6to8duZJ6yeSLzMU3ensWH627VTgI6aIvI103j0NHaToB2lfV5SSWWeDpwlUkoxX"
    "NlWc56tlbmde5YzqGzNj87GNYf4hagv7VtTLW1k9ZO7elnkdLIetzjqT8K/ivDVp/cqOXk/Q9jQ4"
    "a2p0f/ikv+kFO2ylC4MxDOR3jzTtB7R3Qn+oUE9OnJWj2e7I60ZfU9RKzdmuLzVEfikAM+FoB866"
    "HpEHK41eDzX1tcxpemOm95tL/p5/wfg2r5WR5DYgaToZHUzW9p9ExH+gKogrebcGII6TBVpw2x47"
    "vcKz0Q9o6Iom9Pjc9unvSqhL31nHFM+G3DzMLYMtmOkzFw1G0audd6VoHaZmrwFJWzHYZL/nRYmh"
    "hdDQSGvmI+9EQ3mn9fcHnU9R4g2RQWZIvyFlYWehcQ6Z/KrnhpqWWpnkbHFEwve9x4NaBqSfEua2"
    "NL1JiLF13v0oINwrJagN19iHOJDfMCArp7VmLW4YynraWGXdrrwfQEIB0IY4HurvFuBw7C4KivZo"
    "F0bKGE5FS4llpFk9haxmbEWIMRvZ3tNTMo43HkXSO3naeIRt/WVslFWyxhk4ayftpnjLKq6E3CYE"
    "cdHgCP8A/wA2sPjJUqqpXlqqNk1FYggiIoSUIiIAeIUN7TuXGIsxbTZabDxoxJRTySS+iZiwaOa0"
    "DTgdeSmRY0W0ZuEso1lHUsMpP62PMv21k+OH6qetjzL9tZPjh+qrshFY4yoRcPApN62PMv21k+OH"
    "6qetjzL9tZPjh+qrsonGVBw8Ck3rY8y/bWT44fqp62PMv21k+OH6quyicZUHDwKTetjzL9tZPjh+"
    "qnrY8y/bWT44fqq7KJxlQcPApN62PMv21k+OH6qetjzL9tZPjh+qrs8E4JxlQcPApN62PMv21k+O"
    "O+qrk4cpJaDD9toZ9O601LFE/dOo3msAOnnC9BFDUrSqbm8KahsAiIoyQIiIDDuSj/HuTuAMZvfU"
    "XOyR09a/nWUR7jKT1u04PPa4FSCUWVJxfJmGk9yreItk52+6TD2L+8+9irqbiPG9h4/qrUqrZczF"
    "icRFW4eqB1sqpB8OsYV0UU6uqi7kToQZTCj2W8xJXATXHD1O3XjvVMpPwNj/AOa3HDeydTte2TEW"
    "LZZG699DQUwYfNI8n5Ks8iSuqj7hUII0jAeVeBsFbsljsULatv8A/cqPss+vY53sfE3Qdi3YDis9"
    "KKByb3JUktgiIsGQiIgB5KKNpjAN9zCwdb7Vh80gqae4NqH+iJSxu4I3t4HQ8dXBSui2hJxllGJL"
    "UsMpN62PMv21k+OH6qetjzL9tZPjh+qrspwVjjKhDw8Ck3rY8y/bWT44fqp62PMv21k+OH6quzwT"
    "gnGVBw8Ck3rY8y/bWT44fqp62PMv21k+OH6quyicZUHDwKTetjzL9tZPjh+qnrY8y/bWT44fqq7K"
    "JxlQcPApN62PMv21k+OH6qetjzL9tZPjh+qrsonGVBw8Ck3rY8y/bWT4476qsNsz4EvmX2B66zX/"
    "ANC+iZrm+qZ6Hk327joomjU6Djqw/wAFKaBR1LidRYZtClGLygeSqBjzZ2zCveOb/eaM2cU1fc6m"
    "qh36oh24+Vzm6jd4HQhW/Ra06sqbyjadNT3KTetjzL9tZPjh+qnrY8y/bWT44fqq7KKXjKhHw8Ck"
    "3rY8y/bWT44fqp62PMv21k+OH6quyizxlQcPApN62PMv21k+OH6qetjzL9tZPjh+qrsonGVBw8Ck"
    "3rY8y/bWT44fqp62PMv21k+OH6quyicZUHDwKTetjzL9tZPjh+qnrY8y+uyfHHfVV2UTjKg4eBXP"
    "ZvyaxjgHMCa934240j7fJTt7hUF7t9z4yOBaOGjSrGIignUdR5ZLCKisIw7kdFSh2zHmUXEg2T42"
    "fqq7CLanWlT6TWdNT3KTetjzL9tZPjh+qg2Y8y9fZWT44fqq7KKXjKhpw8CLdmnAt8y+wLV2W/8A"
    "oU1U1ykqW+h5N9u46ONo1Og46sKlJOlFWlJyeWSxSisIIiLBsDyUEbTOTd1zAudrvWGvQbLhDG6n"
    "qhUSFgfGDvMIIB4glw8RHUp3WFtCbhLKNZRUlhlJ/Wx5l+2snxw/VT1seZftrJ8cP1VdlFY4yoRc"
    "PApXS7NWaNLVRVVPNZopoXtkje2tILXA6gg7nPVXHshuDrPRuu0cMVwMDPRTYnbzBLuje3T0t110"
    "X7U6VDUqyqdRvCmobBERRkgKw7iCFkrB8SwDn5tCYMdgnM+526KLct9U70ZQ6DRvcnk96Peu3m/o"
    "jrWdn/HRwHmRRXKolLbbVD0JXjoETiO//RcA7xAjpVotqnL5+NMAOuNvgMl3su9UQNA76WIj7LGO"
    "0gBw6dWgdKo30a9AXWoyVWnhlCpFwnlHUKN7HsbJG5rmuGrXA6ghfR6VX7ZDzNbfbAMEXio//lLZ"
    "H/2N73cZ6ccN3tczl2t06irA6rm1IOEnFlyMtSyeTiizQ3q1vpZDuPHfRv09i4ciocuNFU26rfSV"
    "cRjlZwI6x1jrCnjTgvNvljoLxB3KtgDiPYyN4Ob4j/yXl/XfQI+of6lN4mv/ACdz0r1V2b0T5xf/"
    "AIIQ58F6VhtF0ulS30vhf3jgTMeDWHr16/Et6tuXtFBVmWsqpKmEHVkZG7r749Pm0WyVtbaLDbTL"
    "V1FLQUkI01e4MaOwLz/p30nV1a7qWlLx/wDZ2Lv1+MvZbR1N/wD7Y/RQNqIqGJlbM2WdjAJJGt0D"
    "j16Kvm0Djtl5rRhu1Tb9DSv3qmRh4SyD70dYH8T4hr/bNTOCW6xS2fC7pKejeC2WsI3ZJR1MH3re"
    "08T2dMPeJeiv7+Oj7NJ5Xk7v0t9Lzp1FeXccP+WP+X/hGFnsHM8k7VteX+Ar5jCsa2khMFCDpLWS"
    "N7xvWB7Y9nwrj06UqjUYLJ726vKNpTdWtJJI+8qsHz4vxNFTFjhb4C2SskHIM6G69bjw8Wp6Fa+p"
    "morTa5KiolipaOlhL5HuO6yNjRqSeoABeHZ7dhvLvCbmvqaegt9ON+oqqh4aXu6XOPSTyA8QA5BV"
    "R2ic75scb+HMNmWmw6x32WRwLX1zhyLh97HrxDengT1D2XpnpzpRx3e58Q+pvX36ncalyguUV/lm"
    "kZ345lzAzBrb23fbQs0p6CNw4thaTukjoLiXOPa4joWjrPwr6hjkmlbFCx8kj3BrWsBJcTwAAHSv"
    "TRSgsLsePcnJ5PhXS2Rcu5cK4RlxJdYO5XS9Na5jHDvoaYcWA9RcTvEdW7rxBWlbPOz/AFBqqbFW"
    "PaTuUcZEtJapB3zndDph0DpDOevsuo2mHDmqF1XUlpiWqFLHuZlDohUKbVOZrcHYUdh61VG7frtE"
    "WgsPfU0B1DpOwni1vnP3qpwg5tJFiUtKyyvu1BjxuNcx5oaKfulptAdSUhB1a92v2WQeNwAB6Qxp"
    "WrZP4QmxxmHasPta808sokq3D7yBvF57CQNAeshaj4uhXO2P8v3Ybwe/FVxhLble2AxBzdDHTA6t"
    "87z33i3O1dSpJUaeEUoJ1J5ZOcEUcMTIYmNZGxoa1rRoGgDQAL+iBFyS+EREAREQBERAETVNUARE"
    "QBERAETUdaahADyWs4KxzhXGbq1uGbs24Ghc1tSWwyMDC7e0GrmgHXdPLXkv7Zk3f0hy/v8AeQ/d"
    "fSW+aWM/jhh3f5tFE2xNaPQWV9ZdHt0kuNweWu6442tYP5t9SKHscjRy9yRPHSsoEUZuERYOhGiA"
    "yeXNaDirOHLfDFyfbrviimZVxndkigiknMZHMO7m1wB7DxX4tpbFtVg/KW41tumMFfVvZRU0rToW"
    "Ok13nA9BDGvIPQdCtayEyewjRZfWy7X+w0V3u1zp21cz66ETBgkG81jWv1DdGkannrr0cBLGEdOq"
    "RG5POEShgvGWF8Y0klVhq9UtxjiIEgjJD49eW8x2jm68dNRx0WwLXsIYMwxhF9c7Dlnp7b6PkElQ"
    "IQQHEDQADoA46AcOJ61sOo61G8Z5G6z3CImo61gyEREARNR1ogCImo60AKIh0QHlYpxFZcMWeS7X"
    "+5QW+ijIBllPDU8gAOJPYNSv72S62692qnutpq4ayiqW78U8TtWvHL+oI7NNFr2a+AbRmNhlljvE"
    "9VBHHUNqYpadwD2Pa1zRwIII0ceBC9LA2GbZg7C1DhyziUUVGwtYZXBz3EuLnOcQACSSTyW2I6f3"
    "Neef2PcQ8k6NFoma9vzDvVJFZ8E1tts8FQN2suc0r/RETSeIiYGka6ffag9WnNYissy3g9iTHOEG"
    "Yi/s6cQ2913EnczRslDpd7nu7o469i2PpWi5V5YYay+oSLZAam5TD/tVxqADPKTxIB+9br96OzXU"
    "8VvQWZYzyCzjmZRNQmoWpkImo60QBERAEREAREQBERAERNQgCImoQBE1CIAiJqEARNR1ogCImo60"
    "ARNQiAIiajrQBERAEREARNQmo60AREQBERAEREAPJUn2qcr3YPxM7EtopyLFdJS4tY3vaWc8Szsa"
    "eJb5x0BXYPJeXiexWzElhrLJeaVtTQ1cZjljPVzBB6CDoQeYIUtGq6cskdSCmsHNyxXW4WO80t3t"
    "VU+lrqSUSwys5tcP+R6RyPLpV9MjszrZmRhsVDDFT3imaG19GD7B3t268Sx3Qejke2m+c2W92y3x"
    "Q6gqw+e3TEuoK0N72Zg6D1PGvEfBwIK13B+JLzhLEFPe7FWPpa2A8CDq17TzY4ffNPDUH+q6FWlG"
    "vHUipCbpPDOloRRpknm7Ycx7c2JrmUF9iZrU0D38TpzfGT7Jn8R09BMl6hcuUXF4Zei01lA8lGeP"
    "co6HE9Y6ubfLnBUH2LZpTPGzsaHHVo7AdOxSYsaKGrShVWma5Fu0va1nU+5RlhldqnIO/tcfQ15t"
    "0reuRr2E/ACv6UeQV7eR6MvlDE3/ANKN0h/juqwqyqa9Lts5wd5/WPquMa1/0iL8MZK4Vtb2T3Du"
    "92nbx0nIEevvBz8RJUk01PDTQMgp4WRRMG61jBoAOgABf2KaK5SoU6SxBYOFd39zeS1V5uX5Ijzg"
    "ySp8xK30bNi+9UkjftdPIRPSxdrIu90Pbqopn2Tb0JSIMYUD2e2fRvafg3j/AFVsllWoV6kVhMoS"
    "pRk8srHY9k2kZI198xjPNH99FR0YjPme9zvkqZMv8qcD4HLZrJZYzWAaejKk91n6uDj7HXqaAFvC"
    "LEq057sRpxR88uhZJTULQc380cPZb2ju1wkFVc5mk0lvjcO6SnoJ9ozrcfNqeC0jFyeEbtqO5+nN"
    "/MO0ZdYWkutwc2Wrk1ZQ0Ydo6ok05djRzc7oHaQDQbF2ILrinEdZfbzUGorauQvkd0N6A1o6AAAB"
    "2BfrzBxjfMcYjnvt+qTLPJ3scbeEcDOOkbB0AfCSdSSdSv2ZV4CvOYWKIrNaYyyJpD6uqLdWU0ev"
    "Fx7epvSezVdSjSjRjqluUak3UeEbXs15YS4/xc2suEDv7P2x7X1biO9neOLYR4+bupvaQr0xtbG1"
    "rGNDWtGgAGgAXj4GwvacHYZo8P2Wn7lSUzdNT7KRx9k9x6XE8T8A0AAXuKhXqupLPYt06aggERFC"
    "SBERAEREAKwVk8l/KolZBTyTSndjjaXOJ6ABqSncwyMs783rfl62ntdFSem2I6wD0LQsJ70OOgc/"
    "TjoTyaOLtOGnNaJRYa2jcZRNuV0xdTYVilG9HRw/Y3sB4+xjaSP0nk9a83Zht/8Ab7M3FGZ99j7v"
    "NDPuUTJOIje/Xl7yMNaPfdYVngOtWJNUvalzIktfN7FZMQzbQGVFP6eV16pcWWOE61TXDum43rdq"
    "0SNHaCQOlT3gLE9Ni3BlBiWKlqKGGrhMjoqlpa6MjgeJ01bqDo7kRoV70zI5YXxSsZJG9pa5rhqH"
    "A8wR0hRHtZ4lnw3lBVQ0Ujoai7TtoA9h0LWODnP+FrC39Ja6vutRxzM40Js1XFecuL8Y4rnwjk1b"
    "GVToSRPdpWBzBpw3m73etZ1OdrvdA5a5Zlpn/Iz0XNmtDHV+y7k2aTuevVwYB/KpB2dcHUmD8r7V"
    "DHC1tdcIGVtbJp3zpHtDg0nqaCGgdh6ypGKzKqoPEUYjDUstldbfmxjnANZW4ZzZpYTUmhnntl2h"
    "aAyoexhcGHdAadSABoAQSAR3wK2XZLvOJsRYBrr3ia71VxkmuDoqd0xB3Y2Mbrpw6XOd8C/DtqUN"
    "JPlNBWysb6IpblF3F+nHvmuDm+Ijj5gty2dLR6S5LYZpnN0fNSei3nTTUzOMvHzPA8y2k4unqxzE"
    "U1PBr+2Bd/SzJWspQ7dfc6qCkbpz03u6H+EZHnW05D2j0jyfwxQFu480DKh7dOTpdZXA+d5UR7Zs"
    "0l3vuCcF0zz3StqnPc0e2e5kUZ/jIp1xldYcJYCut3ijbuWu3ySxR9BLGHdb5yAFq8qnGPlmV1t+"
    "CN8384q20YkjwLgC1i+YplO68aF0dMSNdCB7JwHE6kNaOJPMLwosvM/7vH6Ou2Z8VsqX98KamJDW"
    "finca1o07N7xlR9s35iYCwcLzf8AF9dVS4ludQd+UUrpSIuDid4Dm55cT71qmP1yWVv4RuHxF6kc"
    "ZQ5QRompc5M0848zVyhvtFS5mmHEGG6uURNuVM0F8Z58HANJIGp3XjU6HQ8FYKpkkuWH5ZrNVQ90"
    "qqUuo6jXVmr26sfqOY4gqu+eedGWuM8sLtYaGprJq6ZrH0oko3NAka9rtd48uAI8RUrbOFRUVOSW"
    "F5Kol0gpDGCfaNkc1v8AKGrSpHMVLGGbQfu0orTnxh7Me33HDuFsVY1GIX3So3qaBu9uxv1bG1x1"
    "aOe+R8KlSnyvz1p6eOCDNiCOKNoYxg39GtHAD2C8vHGmKts3D9q9nDZYYnvHQDGx9RqfO5g+BWVl"
    "e2ON0khDWsaS4noAW9So4xijWEE22RTm/mxSZZ2igssTHXzE88DGw05ceP3vdZNOPE8gOLjy05rS"
    "qHDO0bjKJtzuuLoMLRS99HRx/Y5GNPEatjaSP0nFw6V5mzVQ+qHmxijM29M7u+mnAoWSDURvfru6"
    "dscbWtHVva8wrQjh4lpJqlyS5m0U582VuulVnzlRD6d3a5UmM8PQHeq2jUyxM6XEloe3x6uaOZC+"
    "rDmXdcd7SNmoMN3urjwu2iZPPTs0DXEQmRweOsPc1h48xorFVcENVSy01RG2WGVhZIxw1DmkaEHs"
    "IVVdi+wxNzFxXc4xvw26D0HE48ftkpIPj0h/itoNShKTXNGJJxkkti0V5udBZrTVXW6VUdLRUsZl"
    "mmedAxo5/wD66eSr0/MzNPNW71VFlTbY7PZYH9zfdatrd4+MuDg3h961rnDXXUL9G2VeK6qZhnAN"
    "tk3X3mqD5xrpvaOayJp6wXOJ8bQVOOC8OW3CeGaDD9qiEdLRxBg4cXu++e7rc46knrKjWKcFJrmz"
    "aWZSx2RCE2Wu0BTRmspc04aiqaN7uD5pAwnqGrC34QAvXyTzQxjW40qcu8w7NLFfKeNzm1cMGjXA"
    "DX7IGd6ARxa9ujTwHMjWcV/MRxiV0wjaJHtDXPA4kDXQE9Q1PwlYdXUsSQUMc0zRM5sz7LlrY2VV"
    "e01lxqd4UdCxwDpSObnH71g6Tp4gVF1to9orMSFt1kvVJg22zDfgpw0xSFp5HQNdJ+s4dYC87AlK"
    "zNLakv17uzfRNsw65zaWF3Fmsb9yHh1Eh8nvuxWgHatm1SSSXMxhz5vYrVfLPtE5fUj75S4rhxTQ"
    "0w36imeDM/cHEkte0O0947eUw5NY6ZmFgmC/i3T0Eu+YZontO5vjTUxuI75p159B1B5LdCvmKOOG"
    "JkUTGxxsaGtY0aBoHQB1LSVTWsNczaMNLIGzlxdiUZ/YMwVh68VNFTT9xkr2QHTfa6U7wPijjJ/S"
    "U8VEsVPBJPPIyKKNpc973BrWgDUkk8hoq14M/wC9W2jfrpxfDY4ZWs14hro420+n6znn4VtW2Tie"
    "oseV8dqo5HRzXmpFPIWnQ9xaC54HjO609jipJQy4xRrGTSbPCvmb+Ocf4lqMNZN2xhp6c6T3iojG"
    "gHthv96xvA6bwc53QBov6Oyxz+cz0Uc14RV8+5CaURa9XsNP5VKWSuDqTBGXdrs8MLWVLoWzVsmn"
    "GSdwBcSekD2I7AFup4rEqqi8RXIyoaubK64JzbxthDHNPgbN+liDqpzW010Y1rQd46Nc4t0a5hPD"
    "eABaefTpYnoVfNuShpJMv7LcnsZ6Lhuogjd07j4nlw6+cbPgU2YKqZ63Blkq6sudUT26nklLuZe6"
    "NpOvn1WKiTipLuIPDaZXrNfN674a2hnUTK2vmstsp2MktlMRpVzuhLmt5dL5GA9jTwJ4L2DZtovG"
    "7Bcam/2/BlJL30VDGS2ZgPLXda52unMOePEFrez9aabHG0Hi/G9WxtRT26rklpN4ajukkjmwu7d1"
    "jHadR0KtQpKk1TaSXM1hFzWWVXxPX59ZO9xvl3v0OJbEJAycueZmDU8A8uaJGE8g4EjUgE66A2Nw"
    "FiWhxfhG24ktwc2nrod8Md7KNwJDmHThq1wI4dS1baUnp6fJDE76gNLXU7GNBH37pGBv8SD5l+DZ"
    "PpJaTIuxGUOBmdUStB6GmZ+nwga+daTanT1dzaOYy0kqFZPJCsKuSletqvMK74WxVhW02m9VVrgk"
    "3qi4uptC58Je1o4dgbJ8KxTXfPPNNvplhk0mCsNy8aaWo09EVDOh2u653HrAa3qJ5nX8X2imzH2w"
    "RZa5ontlop4/RDDxD2RMEhYewyS7p7CVaSNrWMaxjA1oGjQBoAFalKMIpJcyBJybeeRXG6YO2i8L"
    "QPu1oxyzEJhG++kc7uj5AOJDWSN0PiBB6lvuQGbMWY1uqqO4UrLfiC3geiqduu49uundGA8QNeBB"
    "1IOnHipTKrDYImWjbkuFHbWiOGrjkdUNaOGr6RsztevWTQ+dYTVWLTW3My1oawWFxria0YQw3VX6"
    "+VIgo6dup0GrnuPsWNHS4ngB/QalQHb8X53ZuTS1OCYaXCuHA8sjq59N6TQ+3LS5x940AHgSv57S"
    "ElTjjO7CWWMc747eCyeqDDx3n7xcdOWrYmEj3561Y+1UNHbLfTW+308dNSU0Yihijbo1jWjQALHK"
    "nFPGWzPOcsdiv1Vl9tDWeF1facyorpURje9DSyk7/Y0StLPh0HatlyGzfrMV3erwdjC3tteKaIOB"
    "YGFjZwzg7vT7F45kdI1I4AgTMeSrHm5Ey17YOC6y3N7nUVrKU1O6OLt6SSFxPjjAHmWYyVTKkjDj"
    "ow0yzb3NawucQ1rRqSToAqjZfZ24xqL5iJlCyuxJdrnVblhtjxrFAwue5z3aaaNaNwaajhrxABVj"
    "84bv6RZW4lujX7kkNulETuqRzS1n8zgop2LMIU1uwNUYumgaa26zPihkI4tp43bug8bw7Xr3W9Sx"
    "S0qDlJCeXJJH7cIYUz5r8W2u9YuxjRU1tiqWTVNtpZtwlgOvcyGM3XAnhxceHSp0A06E6VlRSm5E"
    "kY4Rhw1aoRzgzoq7ViVuBsvrWL5ieQ9zkcGl8dO7pboPZOA4nUhrenXQgSXmhiB2Fsvb7iCPTu1F"
    "RvfDry7oRozX9ItURbGuFIYMJVeOq5pnul4qJGsqJO+cImO0doT0ukDiT07o6lJTSSc5I1m23pR+"
    "amy/2hrwwV92zJhtU7++FNBIe87CI2hnwahfEWNc1sprxRQ5nOp79hirmEHppTt1dTk8tSGtJ6SQ"
    "9up0OhOisWeS0rPahpbhk7iuGsY1zGWuadm90SRtL2H9ZoWY1dTw1uYcMLKZHGz3jDEeNs2sbVk9"
    "7qKvD1G97KOmLgYmh8x7kRw9pG74SpZzFxnZcCYZnv18mc2Bh3I4mDWSeQ8mMHSTofEASeAUS7EV"
    "o9CZb3O7vbuvuFxLWnrjjY0D+Zz1r2cjHZi7T9hy/qnv9KbaxrqiIO4O1j7vJ4i5gYzXoW0oRlUa"
    "7I1jJqCfk/Ra7/n1m0HXLDTqTCGHnuPcJZOBkHY8tL3n8Zoa34F6EmA9oewxmvtOYtPeZYxvOpKh"
    "5d3T8Ud1aW8e0t8asFTQw00EdPTxMihiYGRxsaA1rQNAAByGnQv6HTlotHW58ksGyp+WVVzAz5vt"
    "TlfJRAS4cxtR3SOlroYwWuDA2QuewO1IG8wNI1Omo48QrL4ShrYMLWqG5zyVFeyihbUyyeyklDBv"
    "OPaTqqu7QGHqS7bU+HrZTxNJuTaJ1boOf2VzXE/8NjfgVtexbVlFRjhbmKbbk8kC48xdiWq2osNY"
    "Ksl4qqS3RxwyV9PERuykb8zw7sMYaFPY58lWjJfXFO1bjTErvskNvbNDE8ctQ5sLD52McrMLWslF"
    "pfsZpvKyfErmxxPke4NY1pLnHkB0lQPsrYrxPjS74uvV5u1VU25lQxlDTyOG5Fvue8gDTobuDzqS"
    "86rv6R5T4muQfuPZb5Y43dT3jcYf1nBaNsb2j0uyZirXN0dc62ap1PPdaREPmz8KRSVNtmW/ekb1"
    "mlj2y5e4Zferw9zy525TU0ZHdKiTTXdb1DpLjwA8wUL2iu2gc1YxdrXWUmDrDN31PqNx0rOhzTuu"
    "kdw6e9aehfkxhTjNHaxp8M1+stjw9HrJAT3rgxrXv1H40jmsPYB2Kz8bGRsaxjWtY0ANa0aADqWX"
    "ilFcubNVmb35Fd6rCm0VhGF10tWM6bE7IRvSUM5Mj5QOYDZGjXzODupaxmDnffcWWnCNBhOsqbDf"
    "autkpbpTRHvo5NY2MA14lpLyR08NOYVsCqmVeGqWq23fQdLC1sEVZHcpmtHBr20zZiT45ND43KSl"
    "JTy5LYxOLjjBbKFpYxrS5ztBpq7me0r7WG6rKqE6CIiAHksdCyiA8HHOE7LjTDtRYr/SCopZRq1w"
    "4Pif0PYfvXDr8YOoJCoxnJlXfst7uY6trqu0zOIo69jCGSfiu9q/sPPiQSugp5L8N6tVuvVsqLXd"
    "qKGtoqhm5LDMwOa4eJT0a7pP9iKpSU/yc0LfW1luroa6gqp6SqgcHxTQvLHsPQQQRoVZ3J/aXjey"
    "K0ZhM3HjRjLrBHqHdsrBy980eYcSvCzm2brpaHz3jAbZblb+Ln24neqYR+J/vB1D2XId9zVep4pY"
    "ZXwzRujkY4tcx4ILSOYIPHn0FdDFO4RU99JnTa0XKgu1BFcLXW09bSTDejmgkD2OHYRwX7NVzbwV"
    "jbFODa01WG71VUDidXxtdvRSe+jOrXeMhT9gfarexsdPjLD5f0GrtrtCfHE8/CQ7zKlUtJx25lmN"
    "eL3LTIo9wvnRlpiANFLiuhppXf7KuJpnA9X2TQE+Ilb3R1lJWwiejqoKmI8nxSB7T5wqzjJbomUk"
    "9j+6IiwZCL+VVU09NC6apnihjbzfI8NaPOVo+Js4MtsPtcK7FtulkaPtVG81D9erSPe0Pj0WVFvY"
    "w5Jbm+L+Fwq6Who5auuqYaWmibvSTTSBjGDrLjwAVacbbVVOwPp8HYefK/k2quTt1o7RGwknzuHi"
    "UAY6zAxdjaq7riO91FXGHaspwdyFnijbo3z8+slWadpOXVyRDOvGOxYvN7aXt9Cya1ZfsZX1fFrr"
    "lKz7BH0fY2n2Z7T3vvgqsXq6XG93Oe6Xatnr62c70k87y5zz2nq5DTkF+Roc4hrQXOJ4ADiSp4yb"
    "2db5iR8N3xg2ay2gkObTFulVOPEftY7XcezjqrijToLLKzc6r5EdZUZb4hzGvgobREYqSMj0XXyM"
    "PcoG/wDNx6GjiewalXpy1wPYsA4cistjp91o76ed+hkqH6cXvP8AQcgOAXq4ZsNow1Z4LPY6CGho"
    "YBoyKIcPGTzJPSTqSvTVCtcOq/2LVOkoBERQEwREQBERAEREAK/Jd6U1tpq6IODTUQPi1PRvNI1/"
    "iv1rCZBWrYoucNtOJsF3DSmu0FX3fuMnBzt0dzkAHW0tGvvlZUqGs28j4cT4gGLsJ3iXDmJGkPdN"
    "GXBkrgNA4lvfMdpw3hrr1dK1tuGdqGJvoFmM7M+IDcE5EROnXvGDf8/NWJqNV6s4IY5gtOCdLxiK"
    "xWi40Fvul2o6OquMhjo4ppA10zh0D+A8ZA5kKHNti11NZlbR3CnY57KC5xyT6fescx7N4/pOYPOv"
    "7YCyFdFiWPFmY+IJcVXiNwfHE8udAxwOoJL+LwOgaNaOoqZ7zbaG72qqtdypWVVHVROimheNWvaR"
    "oQtE4wmmuZthyjzPAymxBQ4ly7sl2t8rHsfRxsla0/a5GtAew9RBBH8VtRPBVvmyPzEwRdqisynx"
    "q2mo53b5o615GnUCN10chHtnAHT+P6xgLaCxO30FinMKjtdtfwmFC1olc3pH2JjNQeWhd5lmVOLe"
    "UzClJcmjVdrnG9PijEFpy6sFQypdBWh1XJGd5vok94yMacy3edr2uA5gq09so4bfbaWgpm7sNNCy"
    "GMdTWtAH8AoAp9ns2nM3ClxsfoQYfs/cpquSomcaqpnY9z98gN3dNRGANQAAeHXYYjglVx0qMRTT"
    "y2ytGJP+9e2taqI/ZILFDGXHmGmOJ0wPj35Gj/8ASmrOa11N6yqxLbaNjpKma3S9yY0al7mt3g0d"
    "pI0860vK3LPENjzmxVjvEE1BIy592bRsglc97GvlDhvatGmjWtHA9amIhKk1qWOwhHk89yBdjysw"
    "/eMr/SqSloZbha6qVs7ZImukLHuL2v4jkdSPG0qa/SWz/gmg+Ls+hQvjzIaubimXF2WWInYausrn"
    "PlgJcyFzidTuubqWgnm3dc3xDgvPGHdqOZvoSTGVlijPemfdiB069RBvfBxW0kpvUpYMRbisNE3y"
    "UeGo7hFb30lqbVzRukjgMcYkexugc4N5kDeGp7QvUhiigibFDGyKNo0a1gAAHYFEWVuS8uHcUNxn"
    "izE1diLEgaQyV0jxHFvNLSNSS5/AkDXQDX2PIqV7q2sdbKttBuCsMLxAXnRvdN07up0Og106CopY"
    "zhPJJF98FctnX/vNtE4+xcfskMBlhhd1B8ukf8kRCshcaf0Vb6im3t3u0Tma9Wo0UW7NOWl2y4sF"
    "2hvstHLcK+ra8upZHPb3NrAG6ktB13nP/gpa8y2rSzPl2NaaajzKy7FVyhtVZijBNy0prtDUiYQv"
    "4OduaskAHW0gfCrMlQxnBkdFim/jF2E7u/D2JGkPdK3URzPA0DiW98x+n3w116R0rXqfDO1Cxoof"
    "7aWURDve7vETjp173cC/4eK3mo1fdk1i3BYwSRnpmFQZf4Iqqx1RGLrUxuittPr3z5SNN/T2rdQ4"
    "nzcyFo+xNaTSZY112kae6XK4vLXHm6ONrWj+bfXlXzZ6vNdhe6V1zxEMSY0rWMjiqq+V7aembvgu"
    "3eDiTuhzRqABrwA5qYcocLzYMy4s2G6l0T6ijhPd3RElhkc5z3aEgHTVx6FiTjGnhPmEpOeWQptc"
    "CWx5k4CxpLE+Sho6hgkLRro6KZsu74yCdOvdPUrH22spbhQQV9DUR1FLPG2SKWM6te0jUEHq0Xk4"
    "6wpZsaYbqLBfaXu1HNx1adHxOHsXsPQ4dfjB1BIUGUeUmc+BS+ly8x7TTWreJjp6zhuanXhG9j2D"
    "nxII156J7akEm8NGXmEs43LHzSMjidJI9rGNbvOcToAOklebhu/2bEltFxsVzpbjSF7md1p5A5oc"
    "DoR2H6QelQNV5WZ3Y3aKLHuYFNS2p3CWnohqZB1OYxjGnzk9eimjLvBFhwHh5llsFM5kWu/NNId6"
    "Wd+mhe93Sf4DoC0lCMVyeWbRlJvYgXZyqosKZ+43wjdnCnqq2d/oUycO6lkjnNA98x++OsDxKz55"
    "KK86cmrVmDUQ3mjrZLNiGmaBFXRN1Dw06tDwNDqDycCCO0ABaTDhXaetbBQUeNrTV07eDJpTHI7T"
    "rLpIS4nx6qSSjV92cM0jmHLBOuI8Q2TDtPDUXy60luinmbBE+olDA57jwA1/6A4lfuq6mGmo5qyZ"
    "4bDDG6V7ugNA1J+BQPh7IS83u/Q37NrFkuIZoTqyhhe8wjjroXEDRvW1jW+PoUu49tNfcsv7zY7C"
    "2ngq6q3yUlMHnucce83c5gHQAE6aBRyjFNJPJunJrYg/Ytp5bnXYzxjVs1mrqxsbXfjEvkkH8zF+"
    "rbktVTUYMsV3hYXw0Na+ObT70SNGjj2asA/SHWpE2fcCV2XuXzLJc300lfJVS1FQ6neXR6u0DdCQ"
    "D7FrehbpiGzW6/2Wqs13pGVVDVRmOaJ/Ijs6iDxBHEEArd1F93V2NFBunhn58G3+gxRhe3362ysk"
    "pq2Bsjd067p075p7QdQR0EFeueSriMlczMDV9RLlZjlsVvmcX+g646FvjBY6N5/GIaV91WXe0Hi6"
    "M0GKsf0Nvtr+9mbS6B72nmN2JjA4djnaLDpRb6uRlTl4PHz2u3quZr2LLXDE3omioZnPuFVEdWNd"
    "wEjteWkbNRr0ucR1KweObjFhnL28XKDSJlutsr4QOGhZGdwDzgALyMpsscN5cWt9PZ4nz1k4Hoqu"
    "n0MsunRw9i3qaP4nivvO7Dl7xblrc8OWCSlira7ubN+okLGBgka53EAniG6culJSi3GK2QUWk33Z"
    "HOxHaDSZa3C7vZpJcLk4Nd1xxsa0fzGRT4tRydwtNgvLezYaqnRPqaSJ3d3RElpke9z3aEgEjVxH"
    "HqW2nktKstU2zaCxFIgXbau/oPLKgtTH6PuFxbvDrjja5x/mLFLmXlo9IMB2Kylu66it8MLxp9+1"
    "gDj5zqVHeemWeIcwMa4TqKaWgZZLVLv1bJpXCR4dIwybrQ0g94waakcSphbr1LaUl9uMUYinqbZ9"
    "FYPALJWtZp3f0iy4xFdg7dfT26Z0Z/HLCGfzEKOKy8G7eFkqxkPjWh9cvc73cJmxwX+WrggledGt"
    "MkofGNe3ca0e+CuV06qrmQ2UtnxxkFLHdt+nqq25y1NFWxtHdIdxrY+Gvsmktfq3hr2EAj2ocE7S"
    "OHYhbrFju3XGhYN2J9TuvkDRy17rG4jxbxVqtGM5cnjBBTbitidMXYhtGFsP1V8vdWymoqZhc5zj"
    "xcehrR0uPIBV/wBmC33HGWZuJs2rpTuhgnfJBRBw++eRrunpDGNazXp3uwr9dJkTjXF92guGbONn"
    "3CCF282io3uLT2AlrWx69O606jpHNT9ZLXb7Laqa02qjipKKlYI4oYxo1rf+faTxJOpUbcacWk8t"
    "m6Tk8srbmrUswbtd4dxTdSIrbVwsHd38GMBjfA4k8u91Dj1AhWdY4OaHNIII1BHIrUc1MvbFmJh7"
    "0pvUb2Pidv0tVF9sgfppqOgg9LTwPjAIh+35c7QODYW23CWOqCutcY3YGVOhcxo5ANljfuDsa4hP"
    "bUiueGjHOLbwWHutfR2u3T3C41UVLSU7DJLNK4NYxo5kkqtOVhnzZ2j67MJsMjbBZG9zo3PboHkN"
    "LYm8eni6Q9XAdS9N2S+aGOamI5o4+D7cxwcaOg4736IYyNrvxtHKdMIYbs2E7FBZLDQspKKAd61v"
    "EucebnE8XOPSSmY04vDy2Zw5vmRZtmXf0vyedQtfo6518MBA57rdZSfhjb8K37Jy0ekeVmGbWWbj"
    "4rdC6VvVI9u+/wDmcVpe0ZlriPMisw5TWyooYbbQzSPre7yua928WDvQGnUhrXacRzUwMYGNa1oD"
    "WtGgAHALWUl9tJGUve2fSLCyoiQ0TaBtdTecmsT0FIx0kxojK1jeJd3NwkIHWSGlansfX+hueUFJ"
    "aIZWejLTNNFUxa6OAfI+RjtOoh+mvW09SmZwBBBGoVfsZZB3e34plxTlTiT+z1ZKSZKR73RxDU6k"
    "Nc0HvSfvHNI16QAApoOMo6JPBFJNPUiwBUDbXuYVDZsFzYMoqlkt3uoa2eNjuMFPqCS7qLtA0A8w"
    "XHoC/JHhXabubfQVwx1aKCncNHzRNjD9PxSyEO184XlY12a66awUVPY7pDc7zPVmou11ukz2ySDd"
    "0AYAHcO+cTqdSdNSeGm1OEIzTkzEpSa5IlzZ7tHpLkxhikLd10lEKp3DjrMTLx7e/wBFDGZ9Ycud"
    "rO340uzHiz3OJm9MGkhre4eh3+MtIa8gcdD2hWeoaaKioYKOFu7DBG2Ng6mtAA/gF4uPMHYfxvYn"
    "WfEVCKmn13o3g7skL9NA9jhxaf4HkQRwWsKiU233MyhmKS7HsW6spLhQw1tvqoaqlmaHxTRPD2Pa"
    "ekEcCvIxzjDD2DLLJdcQ3GKlhaCY2agyTO9qxvNxPUPPoNSoWbs1V9sqJBhfM+82ile7XuQhdved"
    "0crA74AvTteReDsJsqcX45vddieWghdUSSV50hAYCSSzUlx4ci4jsKaKedzOqWNiOMirpWZkbUFT"
    "i+ugMXoeCaqjhPERRhghjb2kB4PadSreHXQ6DUqumxrbqm41WLseVkO466VncoTp+M6STTrGr2D9"
    "Eqxh5LNw/fhdjFFe0rFsO1MPpjjOCqeG3OV9PI9jj3xaDKHHr4OcNfGFZ46Kv+Y2RN7/ALaS41yy"
    "xA2yXOd7pZqeR7o277uLyx7QdA48SwgjUniBwH8IMI7S91b6CumPbbb6U8HywiMSgfimOIHX9IeN"
    "bVIxqPUpGIOUVho/LtpY8ooMOxYEoahstdVysnr2tdr3KJvfMa7qc526dOpvaFNOVNo9IstcOWlz"
    "dySC3QiUf+oWgv8A5iVB+KtmyokksMNnroa0tqnT3243CVwqKrVzODGgOAAAkOhOpLuJKsqBo0AD"
    "QAaABa1HFQUYmYKWpuRWHDdXDgzbLvcV4cKeK9seynmkOjSZtyRmh7XM3PHwVn+lR3nTlNZcy7fC"
    "amV9vu1K0ilro27xaDx3Ht4bzdePMEHkeJBjehwXtK2CJtttON7ZWUbBuxSTubK4Do1MsRd5tSsy"
    "01UnnDMLMHsTxi3ENowvh6qvl7rGUtFTMLnvceJPQ1o6XHkB0quWyvV1GNc68Y4+q4t0ug3WNPHu"
    "XdXjcbr1hkW75ls1vyRxVf6wXrNHFpxFV07HPpLbG8tpBLp3u+d0d7rpqGsGvSSOB2TZpy0uuXGH"
    "brT3ySikuFdViQupXl7e5tYA0aloOu8X8PEi0QhJJ5YalKSb2JZROlFXRMEREAREQBERADyWg5l5"
    "S4Lx8x8t3toguJGjbhS6RzjTlqdNHjscD2aLflgrMZOLyjDSe5SzMDZqxtYjJUYefFiKiaSQIvsV"
    "Q0dsZOh/RJJ6goZuttuNqrX0d0oKqhqWezhqInRvHjDgCunJ5L8F7slovlJ6FvNrorjB/u6qBsrf"
    "gcDoVbheyXKRXlbp7HMtf1paqppJRLS1E0Ento3lp+EFXjxFs7ZX3Yl8VpqbVI7iXUNS5o/VfvNH"
    "mAWj3TZNs8jibXjGvpm9AqaNkx85a5isK7pvci+xNbFbqfG+M6dm5T4uxBE0cmsuUwA+By+psc41"
    "qG7s+MMQyt6Q+5zOH8XKc6jZMuwce4YzopG9BfQuaf4PKxDsm3hxHdsZULB+JRvcf4uC2+9RMfbq"
    "Fc6ysrK2TulZVz1L/bSyF5+ElfwVrbZsmWyMg3PGVZUDpFPQti/i5z1u2H9nHLG1uD6i3191eORr"
    "at2mvvY9wHzgrV3dNbGVQm9ykdvoqy4VbKSgpKirqHnRkUEZe9x6gACSpfwBs448xC6OovMceHKF"
    "2hLqob05HZEDrr2OLVcqwYesWH6UU1is1BbItNN2lp2xg+PQcfOvT07FXneyfSsEsbZLcjjLLJnB"
    "WA+51VDQmvurRr6PrdHyA9bB7FnTxA105kqRwOOqyiqSk5PLLCilsERFgyEREAREQBERAEREAREQ"
    "BERAEREAREQBERAEREAREQBERAEREAREQBERAEREAREQBERAEREAREQBERAEREAREQBERACoj2s5"
    "bicnaq22yiqqye4VcMBZTxOkcGh3dCSGjXT7GB5+1S4eS+dOhZjLTJMxJZWDUMk7M6wZUYatckTo"
    "pY6CN8sbm6Fskg33g9oc4hbisBZRvLyEsLAREWDIREQBERAEREAREQBERAEREBhw1Crpfa3P3LzF"
    "VzuLKQY1sVZUOmayGJz+5A8msjad+LQADTvm9PE6lWMKwfEt4T09smso5K7N2krsG9xmyqvLavl3"
    "ITv5+eLUfAvLvEOced8kVqrLI7BmFDI19R3drmvlAOo1DtHydYADW6ga8grOaceSzxW6qxjzjHma"
    "6G92eRgzDtswnhqhw9Z4TFRUUXc4w7i5x5uc49LnEkk9ZXsJ0ooct82SJYCIiAIiIAiIgCIiAIiI"
    "AiIgCIiAIiIAiIgCIiAIiIAiIgCIiAIiIAiIgCIiAIiIAiIgCIiAadqadqIsGBp2pp2oiAadqadq"
    "IgGnamnaiIBp2pp2oiAadqadqIgGnamnaiIBp2pp2oiAadqadqIgGnamnaiIBp2pp2oiAadqadqI"
    "gGnamnaiIBp2pp2oiAadqadqIgGnamnaiIBp2pp2oiAadqadqIgGnamnaiIBp2pp2oiAadqadqIg"
    "GnamnaiIBp2pp2oiAadqadqIgGnamnaiIBp2pp2oiAadqadqIgGnamnaiIBp2pp2oiAadqadqIgG"
    "namnaiIBp2pp2oiAadqadqIgGnamnaiIBp2pp2oiAadqadqIgGnamnaiIBp2pp2oiAadqadqIgGn"
    "amnaiIBp2pp2oiAadqadqIgGnamnaiIBp2pp2oiAadqadqIgGnamnaiIBp2pp2oiAadqadqIgGna"
    "mnaiIBp2pp2oiAadqadqIgGnamnaiID/2Q=="
)

# ─── Carpeta de folletos originales ───────────────────────────────────────────
_LOCAL_FOLLETOS = r"G:\Mi unidad\1 - EULER CALEFACCION\14 - PROCESOS Y CALIDAD\FOLLETOS Y NOTAS PRESUPUESTOS"
_CLOUD_FOLLETOS = os.path.dirname(os.path.abspath(__file__))
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
    """Dibuja el logo Euler real (imagen embebida en base64)."""
    import base64
    img_data = base64.b64decode(EULER_LOGO_B64)
    img_reader = ImageReader(io.BytesIO(img_data))
    # Imagen original: 826 x 230 px → aspecto ~3.59:1
    logo_w = 240 * scale
    logo_h = logo_w * (230 / 826)
    # Centrar horizontalmente en la página
    draw_x = W / 2 - logo_w / 2
    c.drawImage(img_reader, draw_x, y, width=logo_w, height=logo_h,
                preserveAspectRatio=True, mask='auto')


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
        ("N\u00b0 Presupuesto:", datos_presupuesto.get("numero_presupuesto", "")),
        ("Fecha:", datos_presupuesto.get("fecha", date.today().strftime("%d/%m/%Y"))),
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
