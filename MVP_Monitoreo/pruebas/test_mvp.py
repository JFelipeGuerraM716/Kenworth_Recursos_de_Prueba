"""Pruebas del prototipo. Ejecutar desde la carpeta del paquete:

    python -m unittest discover -s MVP_Monitoreo/pruebas -v
"""
import importlib.util
import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pipeline"))

import anomalias  # noqa: E402
import notificaciones  # noqa: E402
import reglas  # noqa: E402
from comun import cargar_cambios, cargar_config, cargar_eventos, cargar_inventario  # noqa: E402

CFG = cargar_config()
INV = cargar_inventario()
CAMBIOS = cargar_cambios()
BASE = datetime(2026, 11, 21, 9, 0)


def evento(minuto, resultado="fallo", n=0, **extra):
    dt = BASE + timedelta(minutes=minuto)
    e = {"evento_id": f"T{n:03}", "fecha_hora": dt.isoformat(), "dt": dt, "tipo": "autenticacion",
         "origen_ip": "10.60.40.21", "destino_ip": "10.60.20.20", "puerto_destino": 22, "accion": "allow",
         "regla_id": "R02", "usuario_prueba": "usr_prueba_07", "resultado": resultado, "bytes": 1200}
    e.update(extra)
    return e


def reglas_disparadas(eventos):
    alertas, _ = reglas.evaluar(eventos, INV, CAMBIOS, CFG)
    return [r for a in alertas for r in a["coincidencias"]]


class CasosControlados(unittest.TestCase):
    """Los mismos cuatro casos de 07_Validacion/Casos_controlados.json."""

    def contar_100021(self, minutos):
        evs = [evento(m, n=i) for i, m in enumerate(minutos)]
        return sum(r.startswith("100021") for r in reglas_disparadas(evs))

    def test_cuatro_fallos_no_alertan(self):
        self.assertEqual(self.contar_100021([0, 1, 2, 3]), 0)

    def test_cinco_fallos_alertan(self):
        self.assertEqual(self.contar_100021([0, 1, 2, 3, 4]), 1)

    def test_fallos_fuera_de_ventana_no_alertan(self):
        self.assertEqual(self.contar_100021([0, 3, 6, 9, 12]), 0)

    def test_frontera_diez_minutos_incluida(self):
        self.assertEqual(self.contar_100021([0, 2, 4, 6, 10]), 1)


class ReglasDelEscenario(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.eventos = cargar_eventos()
        cls.alertas, cls.archivados = reglas.evaluar(cls.eventos, INV, CAMBIOS, CFG)
        cls.por_evento = {a["evento_id"]: a for a in cls.alertas}

    def test_una_decision_por_evento(self):
        self.assertEqual(len(self.alertas) + len(self.archivados), 324)
        self.assertEqual(len(self.por_evento), len(self.alertas))

    def test_exito_tras_fallos_es_alta(self):
        a = self.por_evento["E0308"]
        self.assertEqual((a["regla_id"], a["severidad"]), (100022, "alta"))

    def test_cambio_autorizado_baja_a_severidad_baja(self):
        for eid in ("E0321", "E0322", "E0323"):
            self.assertEqual(self.por_evento[eid]["regla_id"], 100031)
            self.assertEqual(self.por_evento[eid]["severidad"], "baja")

    def test_envio_externo_desde_respaldo_es_alta_y_conserva_inconsistencia(self):
        a = self.por_evento["E0324"]
        self.assertEqual(a["severidad"], "alta")
        self.assertIn("100050:7", a["coincidencias"])

    def test_reconocimiento_bloqueado_es_media(self):
        a = self.por_evento["E0313"]
        self.assertEqual((a["regla_id"], a["severidad"]), (100012, "media"))

    def test_trafico_web_normal_no_genera_alerta(self):
        self.assertTrue(all(a["regla_id"] == 100001 for a in self.archivados))

    def test_casos_correlacionados(self):
        casos = reglas.correlacionar(self.alertas, CFG)
        self.assertEqual([c["activo_clave"] for c in casos], ["BACKUP-LAB", "DB-LAB", "DB-LAB"])


class Notificaciones(unittest.TestCase):

    def test_enrutamiento_por_severidad(self):
        alertas = [
            {"alerta_id": "A1", "fecha_hora": "2026-11-21T09:00:00", "severidad": "alta", "nivel": 12,
             "regla_id": 1, "descripcion": "x"},
            {"alerta_id": "A2", "fecha_hora": "2026-11-21T09:05:00", "severidad": "media", "nivel": 8,
             "regla_id": 2, "descripcion": "y"},
            {"alerta_id": "A3", "fecha_hora": "2026-11-21T09:20:00", "severidad": "media", "nivel": 8,
             "regla_id": 2, "descripcion": "y"},
            {"alerta_id": "A4", "fecha_hora": "2026-11-21T09:06:00", "severidad": "baja", "nivel": 4,
             "regla_id": 3, "descripcion": "z"},
        ]
        envios, _ = notificaciones.enrutar(alertas, CFG)
        canales = sorted((e["canal"], e["n_alertas"]) for e in envios)
        self.assertEqual(canales, [("correo_agrupado", 2), ("correo_inmediato", 1),
                                   ("resumen_diario", 1), ("telegram", 1)])


@unittest.skipUnless(importlib.util.find_spec("sklearn"), "scikit-learn no instalado")
class IsolationForest(unittest.TestCase):

    def test_ventanas_conocidas_son_las_mas_anomalas(self):
        ventanas, alertas_ia = anomalias.detectar(cargar_eventos(), INV, CFG)
        cinco = {(v["origen_ip"], v["ventana_inicio"][11:16])
                 for v in sorted(ventanas, key=lambda v: v["puntaje"])[:4]}
        esperadas = {("10.60.0.20", "02:00"), ("10.60.30.10", "02:10"),
                     ("10.60.40.21", "09:00"), ("203.0.113.77", "10:00")}
        self.assertEqual(cinco, esperadas)

    def test_resultado_reproducible(self):
        a, _ = anomalias.detectar(cargar_eventos(), INV, CFG)
        b, _ = anomalias.detectar(cargar_eventos(), INV, CFG)
        self.assertEqual([v["puntaje"] for v in a], [v["puntaje"] for v in b])


if __name__ == "__main__":
    unittest.main()
