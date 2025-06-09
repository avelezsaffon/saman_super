# Función para obtener el último valor de un ticker
def get_last_value(series):
    return series[-1]['value'] if series and 'value' in series[-1] else None
