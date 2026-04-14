"""National platform adapters — MITECO webinar 3 (Gustavo / Josil).

Several countries run national-level traceability or certification
platforms that EUDR operators can cross-check against:

  - Argentina: BISEC (Sistema Nacional de Trazabilidad Forestal / Agricola)
    — RENSPA + carta de porte electronica + DTA para ganaderia.
  - Malaysia: MSPO dashboard — public parcel lookup with coordinates.
  - Peru: SIMTRAMA — trazabilidad forestal.
  - Brazil: CAR (Cadastro Ambiental Rural) — federal database.
  - Colombia: SNIF / SUNL — trazabilidad forestal nacional.

This module ships STUB adapters that describe the capability of each
platform but don't actually hit external APIs yet — the real integrations
require bilateral agreements with the national operators. The pattern is
ready so those can be swapped in one adapter at a time.

Each adapter implements:

  - slug: stable identifier
  - name + country + description
  - is_available(): whether this adapter is wired to a live endpoint
  - lookup_producer(reference_id, tenant_id): returns a normalized result
    with {status, producer_name?, valid_until?, notes, raw?}
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class NationalLookupResult:
    status: str  # "found" | "not_found" | "unavailable" | "pending"
    producer_name: str | None = None
    valid_until: str | None = None
    notes: str | None = None
    raw: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class NationalPlatformMetadata:
    slug: str
    name: str
    country: str
    description: str
    reference_url: str | None = None
    supports: list[str] = field(default_factory=list)
    available: bool = False


class NationalPlatformAdapter(ABC):
    """Abstract adapter for a national traceability/compliance platform."""

    @property
    @abstractmethod
    def metadata(self) -> NationalPlatformMetadata: ...

    def is_available(self) -> bool:
        return self.metadata.available

    @abstractmethod
    async def lookup_producer(
        self,
        reference_id: str,
        *,
        tenant_id: str | None = None,
    ) -> NationalLookupResult: ...


class BisecAdapter(NationalPlatformAdapter):
    """Argentina — Sistema BISEC (stub)."""

    @property
    def metadata(self) -> NationalPlatformMetadata:
        return NationalPlatformMetadata(
            slug="bisec-ar",
            name="BISEC — Argentina",
            country="AR",
            description=(
                "Plataforma nacional argentina que agrega RENSPA (registro "
                "de establecimientos agropecuarios), cartas de porte "
                "electronicas y DTA (Documento de Transito Animal). Cobertura "
                "~230k productores, ~15 auditores acreditados. Gustavo "
                "(MITECO webinar 3) reporta que desde 2025 el 100% de las "
                "exportaciones de soja argentina se declaran libres de "
                "deforestacion usando BISEC."
            ),
            reference_url="https://www.argentina.gob.ar/senasa",
            supports=["soy", "beef", "wood"],
            available=False,  # stub: no live agreement yet
        )

    async def lookup_producer(
        self,
        reference_id: str,
        *,
        tenant_id: str | None = None,
    ) -> NationalLookupResult:
        return NationalLookupResult(
            status="unavailable",
            notes=(
                "BISEC adapter esta en modo stub — no hay integracion activa "
                "con el backend argentino. Para habilitarlo se requiere "
                "acuerdo bilateral con SENASA y credenciales OAuth2."
            ),
        )


class MspoAdapter(NationalPlatformAdapter):
    """Malaysia — MSPO public dashboard (stub)."""

    @property
    def metadata(self) -> NationalPlatformMetadata:
        return NationalPlatformMetadata(
            slug="mspo-my",
            name="MSPO Dashboard — Malaysia",
            country="MY",
            description=(
                "Malaysian Sustainable Palm Oil — certificacion nacional "
                "obligatoria con dashboard publico de parcelas georreferenciadas. "
                "Josil (MITECO webinar 3): el dashboard permite consultar "
                "coordenadas y reportes de auditoria, pero MSPO no cubre "
                "cadena de custodia (eso lo hace MTCS por separado)."
            ),
            reference_url="https://www.mpocc.org.my/",
            supports=["palm_oil"],
            available=False,  # stub
        )

    async def lookup_producer(
        self,
        reference_id: str,
        *,
        tenant_id: str | None = None,
    ) -> NationalLookupResult:
        return NationalLookupResult(
            status="unavailable",
            notes=(
                "MSPO adapter en modo stub. El dashboard publico de MPOCC "
                "no tiene API REST oficial — integracion requiere scraping "
                "autorizado o acuerdo formal con el Council."
            ),
        )


class SimtramaAdapter(NationalPlatformAdapter):
    """Peru — SIMTRAMA (Sistema de Trazabilidad Maderera) stub."""

    @property
    def metadata(self) -> NationalPlatformMetadata:
        return NationalPlatformMetadata(
            slug="simtrama-pe",
            name="SIMTRAMA — Peru",
            country="PE",
            description=(
                "Sistema nacional peruano para trazabilidad de productos "
                "maderables. Gestionado por SERFOR. Util para operadores "
                "madereros; no cubre cafe ni cacao."
            ),
            reference_url="https://www.serfor.gob.pe/",
            supports=["wood"],
            available=False,
        )

    async def lookup_producer(
        self,
        reference_id: str,
        *,
        tenant_id: str | None = None,
    ) -> NationalLookupResult:
        return NationalLookupResult(
            status="unavailable",
            notes="SIMTRAMA adapter en modo stub.",
        )


class CarBrazilAdapter(NationalPlatformAdapter):
    """Brazil — CAR (Cadastro Ambiental Rural) stub."""

    @property
    def metadata(self) -> NationalPlatformMetadata:
        return NationalPlatformMetadata(
            slug="car-br",
            name="CAR — Brasil",
            country="BR",
            description=(
                "Cadastro Ambiental Rural — registro federal obligatorio "
                "para todos los inmuebles rurales en Brasil. Incluye "
                "georreferenciacion de la propiedad, reservas legales y "
                "APPs. Gestionado por SFB/SICAR. Muy util para EUDR "
                "(tiene geometrias publicas) pero requiere procesamiento "
                "batch; no hay API de lookup por CPF."
            ),
            reference_url="https://www.car.gov.br/",
            supports=["soy", "beef", "wood", "coffee", "cocoa"],
            available=False,
        )

    async def lookup_producer(
        self,
        reference_id: str,
        *,
        tenant_id: str | None = None,
    ) -> NationalLookupResult:
        return NationalLookupResult(
            status="unavailable",
            notes=(
                "CAR adapter en modo stub. La consulta por recibo CAR se "
                "realiza actualmente via descarga masiva, no por API."
            ),
        )


# Registry -------------------------------------------------------------------
_REGISTRY: dict[str, NationalPlatformAdapter] = {
    "bisec-ar": BisecAdapter(),
    "mspo-my": MspoAdapter(),
    "simtrama-pe": SimtramaAdapter(),
    "car-br": CarBrazilAdapter(),
}


def list_adapters() -> list[NationalPlatformMetadata]:
    return [a.metadata for a in _REGISTRY.values()]


def get_adapter(slug: str) -> NationalPlatformAdapter | None:
    return _REGISTRY.get(slug)
