import requests

def obtener_conversion_dinamica(moneda_destino):
    """
    Obtiene la tasa de cambio de COP hacia la moneda seleccionada.
    """
    url = "https://api.exchangerate-api.com/v4/latest/COP"
    try:
        response = requests.get(url, timeout=2)
        if response.status_code == 200:
            datos = response.json()
            # Retornamos la tasa específica pedida (ej: 'USD', 'EUR', 'MXN')
            return datos['rates'].get(moneda_destino)
    except:
        return None
    return None