"""Integración con Mercado Pago Point (Orders API, type="point") para
cobros con tarjeta en la terminal física.

Implementado según la documentación oficial vigente de Mercado Pago
(Orders API para Point: POST /v1/orders, GET /v1/orders/{id},
GET /terminals/v1/list). IMPORTANTE: no ha podido probarse todavía contra
una cuenta ni una terminal real (no había credenciales disponibles al
construir esto) — antes de usarlo en producción, hay que validarlo con un
cobro de prueba real usando el Access Token de sandbox ("TEST-").

Mientras MP_ACCESS_TOKEN / MP_TERMINAL_ID no estén configurados en el
.env, el cobro con tarjeta usa un simulador de terminal (ver
ui/ventas/pago_tarjeta_view.py) para poder probar el flujo de
aprobar/rechazar sin cuenta ni hardware real.
"""
import uuid
from typing import Optional

import requests

from config import MP_ACCESS_TOKEN, MP_TERMINAL_ID

BASE_URL = "https://api.mercadopago.com"

# Estados posibles del campo "status" de una orden (documentación oficial):
# created, action_required -> en proceso; processed -> aprobada;
# canceled, expired, failed -> no completada; refunded -> reembolsada después.
ESTADOS_APROBADOS = ("processed",)
ESTADOS_RECHAZADOS = ("canceled", "expired", "failed")
ESTADOS_EN_PROCESO = ("created", "action_required")


class MercadoPagoError(Exception):
    """Mercado Pago no está configurado, o falló la comunicación con la API."""


def esta_configurado() -> bool:
    return bool(MP_ACCESS_TOKEN and MP_TERMINAL_ID)


def modo_sandbox() -> bool:
    return bool(MP_ACCESS_TOKEN and MP_ACCESS_TOKEN.startswith("TEST-"))


def _headers(con_idempotencia: bool = False) -> dict:
    headers = {
        "Authorization": f"Bearer {MP_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    if con_idempotencia:
        headers["X-Idempotency-Key"] = str(uuid.uuid4())
    return headers


def _requerir_access_token() -> None:
    if not MP_ACCESS_TOKEN:
        raise MercadoPagoError("Falta configurar MP_ACCESS_TOKEN en el archivo .env")


def _requerir_configuracion() -> None:
    _requerir_access_token()
    if not MP_TERMINAL_ID:
        raise MercadoPagoError(
            "Falta configurar MP_TERMINAL_ID en el archivo .env "
            "(usa listar_terminales() para obtenerlo)"
        )


def listar_terminales() -> list:
    """Utilidad para descubrir el terminal_id de la terminal Point asociada
    a la cuenta, una vez que ya se tiene el Access Token."""
    _requerir_access_token()
    try:
        resp = requests.get(f"{BASE_URL}/terminals/v1/list", headers=_headers(), timeout=15)
        resp.raise_for_status()
    except requests.RequestException as e:
        raise MercadoPagoError(f"No se pudo consultar las terminales: {e}") from e
    datos = resp.json()
    return datos.get("terminals", datos) if isinstance(datos, dict) else datos


def crear_orden_pago(monto: float, external_reference: str, expiracion: str = "PT5M") -> dict:
    """Crea una orden de cobro en la terminal Point. El monto ya debe
    incluir el descuento aplicado. Devuelve el JSON de la orden creada."""
    _requerir_configuracion()
    body = {
        "type": "point",
        "external_reference": external_reference,
        "expiration_time": expiracion,
        "transactions": {"payments": [{"amount": f"{monto:.2f}"}]},
        "config": {
            "point": {"terminal_id": MP_TERMINAL_ID, "print_on_terminal": "no_ticket"},
            "payment_method": {"default_type": "credit_card"},
        },
    }
    try:
        resp = requests.post(
            f"{BASE_URL}/v1/orders", json=body, headers=_headers(con_idempotencia=True), timeout=15
        )
        resp.raise_for_status()
    except requests.RequestException as e:
        raise MercadoPagoError(f"No se pudo iniciar el cobro en la terminal: {e}") from e
    return resp.json()


def consultar_orden(order_id: str) -> dict:
    _requerir_access_token()
    try:
        resp = requests.get(f"{BASE_URL}/v1/orders/{order_id}", headers=_headers(), timeout=15)
        resp.raise_for_status()
    except requests.RequestException as e:
        raise MercadoPagoError(f"No se pudo consultar el estado del cobro: {e}") from e
    return resp.json()


def cancelar_orden(order_id: str) -> None:
    """Intento best-effort de cancelar en la terminal. Si falla (por
    ejemplo porque el pago ya está en curso en la terminal y no admite
    cancelación por API), no pasa nada grave: la orden expira sola y de
    todas formas nunca se registra la venta si no llegó a 'processed'."""
    try:
        requests.post(f"{BASE_URL}/v1/orders/{order_id}/cancel", headers=_headers(), timeout=10)
    except requests.RequestException:
        pass


def extraer_resultado(orden: dict) -> tuple[str, Optional[str]]:
    """Devuelve (estado, payment_id) a partir del JSON de una orden."""
    estado = orden.get("status")
    payment_id = None
    pagos = orden.get("transactions", {}).get("payments", [])
    if pagos:
        payment_id = pagos[0].get("id")
    return estado, payment_id
