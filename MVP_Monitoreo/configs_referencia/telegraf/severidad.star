# Clasifica cada alerta según el nivel de la regla de Wazuh.
def apply(metric):
    nivel = metric.fields.get("nivel_num", 0)
    if nivel >= 12:
        metric.tags["severidad"] = "alta"
    elif nivel >= 7:
        metric.tags["severidad"] = "media"
    else:
        metric.tags["severidad"] = "baja"
    return metric
