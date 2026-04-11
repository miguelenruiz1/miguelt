"""EUDR Art. 2(28) GeoJSON validator — strict, precision-preserving.

Reglamento (UE) 2023/1115, Art. 2(28):
  "geolocalizacion (...) descrita por puntos de latitud y longitud, usando al
   menos seis cifras decimales (...). Para parcelas > 4 ha se proporcionara
   mediante poligonos con suficientes puntos para describir el perimetro."

Implementacion:
  - Coordenadas se validan como ``Decimal`` para preservar ceros finales (un
    JSON literal ``4.654400`` sobrevive como ``Decimal('4.654400')`` con
    exponente -6, mientras que un float colapsa a ``4.6544`` y pierde la
    declaracion de precision del usuario).
  - Validaciones aplicadas (en orden):
        1. Tipo de geometria soportado
        2. Estructura de coordinates
        3. Por-coordenada: numero, finito (no NaN/Inf), rango lat/lng,
           >= 6 decimales (ambas componentes)
        4. Cierre del anillo (auto-cerrado si falta)
        5. >= 3 vertices unicos
        6. Sin auto-interseccion (incluye casos colineales)
        7. Orientacion RFC 7946 (exterior CCW, holes CW; auto-corregido)
        8. Holes contenidos en el exterior (point-in-polygon ray casting)
  - Sin dependencias externas (sin shapely / pyproj).

Uso desde una ruta FastAPI:
    raw = await request.body()
    geom = parse_decimal_geojson_from_body(raw)  # preserva ceros finales
    normalized = validate_geojson_strict(geom, declared_area_ha=body.plot_area_ha)
"""
from __future__ import annotations

import json
import math
from decimal import Decimal, InvalidOperation
from typing import Any

# ---------------------------------------------------------------------------
# Constantes EUDR
# ---------------------------------------------------------------------------
EUDR_MIN_DECIMALS = 6
LAT_MIN, LAT_MAX = Decimal("-90"), Decimal("90")
LNG_MIN, LNG_MAX = Decimal("-180"), Decimal("180")
WGS84_RADIUS_M = 6378137.0  # semieje mayor

# Tolerancia entre el area dibujada del poligono y el area declarada por el
# operador. Si el ratio se sale de [1/AREA_MAX_RATIO, AREA_MAX_RATIO] rechazamos
# por considerar el poligono claramente erroneo (caso real: usuario subio
# poligono de 1.5M ha para parcela declarada de 13 ha → ratio ~118.000x).
# 5x deja margen para mediciones imprecisas pero atrapa errores groseros.
AREA_MAX_RATIO = Decimal("5")


class GeoJsonValidationError(ValueError):
    """Violacion del Art. 2(28) o de RFC 7946 en una geometria."""


# ---------------------------------------------------------------------------
# Helpers de Decimal
# ---------------------------------------------------------------------------
def _decimal_places(d: Decimal) -> int:
    """Numero de cifras decimales declaradas en *d*, preservando ceros finales.

    Solo es confiable si *d* fue parseado desde JSON con
    ``parse_float=Decimal`` (o construido desde un string).  Si proviene de
    un float, los ceros finales ya se perdieron y este conteo subestimara
    la precision real del usuario.
    """
    if not isinstance(d, Decimal):
        return 0
    sign, digits, exponent = d.as_tuple()
    if isinstance(exponent, int) and exponent < 0:
        return -exponent
    return 0


def _to_decimal_strict(v: Any, path: str) -> Decimal:
    """Convierte un valor JSON a Decimal preservando precision si es posible."""
    if isinstance(v, Decimal):
        return v
    if isinstance(v, bool):  # bool es subclase de int en Python
        raise GeoJsonValidationError(f"{path}: booleano usado como coordenada")
    if isinstance(v, int):
        return Decimal(v)
    if isinstance(v, float):
        # Los floats vienen de un parseo no-Decimal: ceros finales perdidos.
        # Convertimos por str() para no inventar precision falsa.
        return Decimal(str(v))
    if isinstance(v, str):
        try:
            return Decimal(v)
        except InvalidOperation as e:
            raise GeoJsonValidationError(f"{path}: string no numerico {v!r}") from e
    raise GeoJsonValidationError(
        f"{path}: tipo {type(v).__name__} no convertible a numero"
    )


# ---------------------------------------------------------------------------
# Validacion de coordenada
# ---------------------------------------------------------------------------
def _validate_coord(lng_raw: Any, lat_raw: Any, path: str) -> tuple[Decimal, Decimal]:
    lng = _to_decimal_strict(lng_raw, f"{path}.lng")
    lat = _to_decimal_strict(lat_raw, f"{path}.lat")

    # NaN / Infinity (Decimal soporta ambos)
    if not lng.is_finite() or not lat.is_finite():
        raise GeoJsonValidationError(
            f"{path}: coordenada NaN/Infinity no permitida"
        )

    if not (LAT_MIN <= lat <= LAT_MAX):
        raise GeoJsonValidationError(
            f"{path}: latitud {lat} fuera de rango [-90, 90]. "
            "Verifique que las coordenadas esten en WGS84 (EPSG:4326) y no en "
            "una proyeccion metrica (UTM, MAGNA, etc)."
        )
    if not (LNG_MIN <= lng <= LNG_MAX):
        raise GeoJsonValidationError(
            f"{path}: longitud {lng} fuera de rango [-180, 180]. "
            "Verifique que las coordenadas esten en WGS84 (EPSG:4326)."
        )

    lng_dp = _decimal_places(lng)
    lat_dp = _decimal_places(lat)
    if lng_dp < EUDR_MIN_DECIMALS:
        raise GeoJsonValidationError(
            f"{path}: longitud {lng} declara {lng_dp} decimales. "
            f"EUDR Art. 2(28) exige minimo {EUDR_MIN_DECIMALS} cifras decimales "
            f"(precision ~11 cm). Si el valor es exacto, escribalo padded con "
            f"ceros (ej: -74.123000)."
        )
    if lat_dp < EUDR_MIN_DECIMALS:
        raise GeoJsonValidationError(
            f"{path}: latitud {lat} declara {lat_dp} decimales. "
            f"EUDR Art. 2(28) exige minimo {EUDR_MIN_DECIMALS} cifras decimales "
            f"(precision ~11 cm). Si el valor es exacto, escribalo padded con "
            f"ceros (ej: 4.650000)."
        )

    return lng, lat


# ---------------------------------------------------------------------------
# Geometria 2D — segmento, interseccion, area, point-in-ring
# ---------------------------------------------------------------------------
def _ccw(ax: float, ay: float, bx: float, by: float, cx: float, cy: float) -> float:
    """Producto cruzado (B-A) x (C-A). Signo indica orientacion del giro."""
    return (bx - ax) * (cy - ay) - (by - ay) * (cx - ax)


def _on_segment_strict(
    ax: float, ay: float, bx: float, by: float, px: float, py: float,
) -> bool:
    """Punto P esta estrictamente dentro del segmento AB (no en sus extremos)."""
    if (px == ax and py == ay) or (px == bx and py == by):
        return False
    return (min(ax, bx) <= px <= max(ax, bx)) and (min(ay, by) <= py <= max(ay, by))


def _segments_intersect(
    p1: tuple[Decimal, Decimal], p2: tuple[Decimal, Decimal],
    p3: tuple[Decimal, Decimal], p4: tuple[Decimal, Decimal],
) -> bool:
    """Detecta si los segmentos p1-p2 y p3-p4 se cruzan o se tocan colinealmente."""
    ax, ay = float(p1[0]), float(p1[1])
    bx, by = float(p2[0]), float(p2[1])
    cx, cy = float(p3[0]), float(p3[1])
    dx, dy = float(p4[0]), float(p4[1])

    d1 = _ccw(cx, cy, dx, dy, ax, ay)
    d2 = _ccw(cx, cy, dx, dy, bx, by)
    d3 = _ccw(ax, ay, bx, by, cx, cy)
    d4 = _ccw(ax, ay, bx, by, dx, dy)

    # Cruce propio
    if ((d1 > 0 and d2 < 0) or (d1 < 0 and d2 > 0)) and \
       ((d3 > 0 and d4 < 0) or (d3 < 0 and d4 > 0)):
        return True

    # Endpoint de un segmento sobre el otro (caso colineal/touching)
    if d1 == 0 and _on_segment_strict(cx, cy, dx, dy, ax, ay):
        return True
    if d2 == 0 and _on_segment_strict(cx, cy, dx, dy, bx, by):
        return True
    if d3 == 0 and _on_segment_strict(ax, ay, bx, by, cx, cy):
        return True
    if d4 == 0 and _on_segment_strict(ax, ay, bx, by, dx, dy):
        return True

    return False


def _signed_area_planar(ring: list[tuple[Decimal, Decimal]]) -> float:
    """Area con signo via Shoelace en el plano lng/lat. Positivo = CCW."""
    n = len(ring) - 1  # excluir vertice de cierre
    s = 0.0
    for i in range(n):
        x1, y1 = float(ring[i][0]), float(ring[i][1])
        x2, y2 = float(ring[i + 1][0]), float(ring[i + 1][1])
        s += x1 * y2 - x2 * y1
    return s / 2.0


def _spherical_polygon_area_m2(ring: list[tuple[Decimal, Decimal]]) -> float:
    """Area geodesica del anillo sobre la esfera WGS84 (m²)."""
    n = len(ring) - 1
    if n < 3:
        return 0.0
    total = 0.0
    for i in range(n):
        lng1 = math.radians(float(ring[i][0]))
        lat1 = math.radians(float(ring[i][1]))
        lng2 = math.radians(float(ring[(i + 1) % n][0]))
        lat2 = math.radians(float(ring[(i + 1) % n][1]))
        total += (lng2 - lng1) * (2 + math.sin(lat1) + math.sin(lat2))
    return abs(total) * WGS84_RADIUS_M * WGS84_RADIUS_M / 2.0


def _polygon_area_ha(ring: list[tuple[Decimal, Decimal]]) -> float:
    return _spherical_polygon_area_m2(ring) / 10_000.0


def _point_in_ring(
    px: float, py: float, ring: list[tuple[Decimal, Decimal]],
) -> bool:
    """Test ray-casting clasico. Asume anillo cerrado."""
    n = len(ring) - 1
    inside = False
    j = n - 1
    for i in range(n):
        xi, yi = float(ring[i][0]), float(ring[i][1])
        xj, yj = float(ring[j][0]), float(ring[j][1])
        if ((yi > py) != (yj > py)) and \
           (px < (xj - xi) * (py - yi) / (yj - yi + 1e-30) + xi):
            inside = not inside
        j = i
    return inside


# ---------------------------------------------------------------------------
# Validacion de anillo
# ---------------------------------------------------------------------------
def _validate_ring(
    ring: Any, path: str, want_ccw: bool,
) -> list[tuple[Decimal, Decimal]]:
    if not isinstance(ring, list):
        raise GeoJsonValidationError(f"{path}: anillo no es una lista")
    if len(ring) < 4:
        raise GeoJsonValidationError(
            f"{path}: anillo con {len(ring)} posiciones; minimo 4 "
            "(3 vertices unicos + cierre). Un poligono GeoJSON requiere al "
            "menos 4 puntos."
        )

    coords: list[tuple[Decimal, Decimal]] = []
    for i, pt in enumerate(ring):
        if not isinstance(pt, (list, tuple)) or len(pt) < 2:
            raise GeoJsonValidationError(
                f"{path}[{i}]: posicion malformada, se esperaba [lng, lat]"
            )
        lng, lat = _validate_coord(pt[0], pt[1], f"{path}[{i}]")
        coords.append((lng, lat))

    # Auto-cierre si el usuario olvido repetir el primer vertice
    if coords[0] != coords[-1]:
        coords.append(coords[0])

    # Vertices unicos (excluyendo el cierre)
    unique = {(c[0], c[1]) for c in coords[:-1]}
    if len(unique) < 3:
        raise GeoJsonValidationError(
            f"{path}: anillo degenerado, solo {len(unique)} vertices unicos. "
            "Se requieren minimo 3 vertices distintos para definir un area."
        )

    # Sin auto-interseccion (O(n²); aceptable para parcelas con <500 vertices)
    n = len(coords) - 1
    for i in range(n):
        a1, a2 = coords[i], coords[i + 1]
        for j in range(i + 2, n):
            # adyacencia wrap-around: edge (n-1) toca edge 0 en el cierre
            if i == 0 and j == n - 1:
                continue
            b1, b2 = coords[j], coords[j + 1]
            if _segments_intersect(a1, a2, b1, b2):
                raise GeoJsonValidationError(
                    f"{path}: anillo auto-intersectante o auto-tocante "
                    f"(segmento {i}-{i+1} cruza con {j}-{j+1}). "
                    "GeoJSON RFC 7946 prohibe anillos que se cruzan a si mismos."
                )

    # Orientacion RFC 7946: exterior CCW, holes CW. Auto-corregimos.
    signed = _signed_area_planar(coords)
    is_ccw = signed > 0
    if want_ccw != is_ccw:
        coords.reverse()

    return coords


# ---------------------------------------------------------------------------
# Validadores por tipo de geometria
# ---------------------------------------------------------------------------
def _validate_polygon_geom(geom: dict, path: str) -> dict:
    rings = geom.get("coordinates")
    if not isinstance(rings, list) or not rings:
        raise GeoJsonValidationError(f"{path}: Polygon sin coordinates")

    # Detectar el error comun de pasar un anillo plano en lugar de una lista
    # de anillos. Polygon.coordinates debe ser [[ring1], [ring2]?, ...] donde
    # cada ring es [[lng,lat], [lng,lat], ...]. Si rings[0] parece una posicion
    # (par de numeros) en vez de una lista de posiciones, el usuario olvido
    # envolver en lista.
    first = rings[0] if rings else None
    if (
        isinstance(first, (list, tuple))
        and len(first) >= 2
        and all(isinstance(x, (int, float, Decimal)) for x in first[:2])
    ):
        raise GeoJsonValidationError(
            f"{path}: Polygon.coordinates debe ser una lista de anillos "
            "[[[lng,lat],...]], no una lista plana de posiciones. Envuelva "
            "los puntos en un array adicional: "
            '{"type":"Polygon","coordinates":[[[lng,lat],[lng,lat],...]]}'
        )

    # TRACES NT (EUDR GeoJSON File Description v1.5):
    #   "Polygons with holes (i.e. doughnut shapes) and shapes with crossing
    #    lines (like a figure eight for example) are not supported and will
    #    not be processed."
    # Por lo tanto rechazamos cualquier polygon con mas de un anillo, no solo
    # validamos que los holes esten contenidos.
    if len(rings) > 1:
        raise GeoJsonValidationError(
            f"{path}: TRACES NT no acepta poligonos con agujeros (doughnut "
            f"shapes). Recibido un Polygon con {len(rings)} anillos. Si la "
            "parcela tiene un area excluida, divida el polygon en multiples "
            "polygons o use MultiPolygon sin agujeros internos."
        )

    exterior = _validate_ring(rings[0], f"{path}.coordinates[0]", want_ccw=True)

    return {
        "type": "Polygon",
        "coordinates": [_ring_to_jsonable(exterior)],
    }


def _validate_multipolygon_geom(geom: dict, path: str) -> dict:
    polys = geom.get("coordinates")
    if not isinstance(polys, list) or not polys:
        raise GeoJsonValidationError(f"{path}: MultiPolygon sin coordinates")

    new_polys = []
    for i, poly in enumerate(polys):
        if not isinstance(poly, list) or not poly:
            raise GeoJsonValidationError(
                f"{path}.coordinates[{i}]: poligono malformado en MultiPolygon"
            )
        # _validate_polygon_geom ya rechaza polygons con agujeros (TRACES NT
        # no los acepta), asi que la verificacion es uniforme.
        sub = _validate_polygon_geom(
            {"type": "Polygon", "coordinates": poly},
            f"{path}.coordinates[{i}]",
        )
        new_polys.append(sub["coordinates"])

    return {"type": "MultiPolygon", "coordinates": new_polys}


def _validate_point_geom(geom: dict, path: str) -> dict:
    coords = geom.get("coordinates")
    if not isinstance(coords, (list, tuple)) or len(coords) < 2:
        raise GeoJsonValidationError(f"{path}: Point sin coordinates [lng, lat]")
    lng, lat = _validate_coord(coords[0], coords[1], path)
    return {"type": "Point", "coordinates": [_dec_to_jsonable(lng), _dec_to_jsonable(lat)]}


# ---------------------------------------------------------------------------
# Serializacion para JSONB — preserva digitos como strings
# ---------------------------------------------------------------------------
def _dec_to_jsonable(d: Decimal) -> float:
    """Convierte Decimal a un valor que JSONB acepta sin perder rango.

    Usamos float (los ceros finales se pierden, pero la magnitud es exacta a
    ~15 sig figs, mas que suficiente para coordenadas de 6-7 decimales).
    El export al DDS se encarga de paddear de nuevo a 6 decimales.
    """
    return float(d)


def _ring_to_jsonable(ring: list[tuple[Decimal, Decimal]]) -> list[list[float]]:
    return [[_dec_to_jsonable(c[0]), _dec_to_jsonable(c[1])] for c in ring]


# ---------------------------------------------------------------------------
# Entry points
# ---------------------------------------------------------------------------
def validate_geojson_strict(
    geojson: Any,
    *,
    path: str = "geojson",
    declared_area_ha: float | int | Decimal | None = None,
) -> dict:
    """Valida y normaliza una geometria GeoJSON contra el Art. 2(28) del EUDR.

    *geojson* debe venir de ``json.loads(..., parse_float=Decimal)`` para que
    el chequeo de precision sea estricto.  Si se le pasa un dict con floats
    nativos, los ceros finales declarados por el usuario ya se habran perdido
    y la validacion sera menos confiable.

    Si *declared_area_ha* viene seteado y la geometria es Polygon/MultiPolygon,
    se compara el area calculada del poligono contra el valor declarado.  Si
    el ratio supera ``AREA_MAX_RATIO`` (en cualquier direccion), se rechaza
    por considerar el poligono inconsistente con la parcela real.

    Acepta: Point, Polygon, MultiPolygon, Feature, FeatureCollection.
    Devuelve un dict con la geometria normalizada (anillos cerrados, orientacion
    RFC 7946, coordenadas como float listo para JSONB).
    """
    if not isinstance(geojson, dict):
        raise GeoJsonValidationError(
            f"{path}: se esperaba objeto JSON, recibido {type(geojson).__name__}"
        )
    gtype = geojson.get("type")
    if gtype is None:
        raise GeoJsonValidationError(f"{path}: falta campo 'type'")

    if gtype == "FeatureCollection":
        feats = geojson.get("features") or []
        if not feats:
            raise GeoJsonValidationError(
                f"{path}: FeatureCollection vacia. Se requiere al menos un Feature."
            )
        if len(feats) == 1:
            return validate_geojson_strict(
                feats[0], path=f"{path}.features[0]", declared_area_ha=declared_area_ha,
            )

        # Multi-feature FC: el spec EUDR (GeoJSON File Description v1.x) acepta
        # multiples features para describir componentes disconectos del mismo
        # productor. A nivel de una sola parcela los fusionamos en MultiPolygon
        # cuando todos son polygons; rechazamos casos heterogeneos o multi-Point
        # (cada parcela tiene UNA geometria semantica, no varias).
        inner_geoms: list[dict] = []
        for i, feat in enumerate(feats):
            if not isinstance(feat, dict):
                raise GeoJsonValidationError(
                    f"{path}.features[{i}]: feature no es un objeto"
                )
            if feat.get("type") != "Feature":
                raise GeoJsonValidationError(
                    f"{path}.features[{i}]: se esperaba 'Feature', recibido {feat.get('type')!r}"
                )
            geom = feat.get("geometry")
            if not isinstance(geom, dict):
                raise GeoJsonValidationError(
                    f"{path}.features[{i}]: Feature sin geometry"
                )
            inner_geoms.append(geom)

        types = {g.get("type") for g in inner_geoms}
        if "Point" in types:
            raise GeoJsonValidationError(
                f"{path}: FeatureCollection contiene features Point con {len(feats)} elementos. "
                "Cada parcela EUDR debe tener una sola geometria. Si quiere registrar varias "
                "parcelas, envielas en llamadas separadas. Si quiere agrupar zonas "
                "disconectas en una sola parcela, use Polygon o MultiPolygon."
            )
        if not types.issubset({"Polygon", "MultiPolygon"}):
            raise GeoJsonValidationError(
                f"{path}: FeatureCollection mezcla tipos {sorted(t for t in types if t)}. "
                "Solo se permiten Polygon o MultiPolygon en multi-feature."
            )

        # Aplanar todos los polygons (cada uno con UN solo anillo, ya que rechazamos holes)
        # y empaquetarlos como MultiPolygon. La validacion de cada anillo ocurre dentro
        # de _validate_polygon_geom / _validate_multipolygon_geom recursivamente.
        merged_polys: list[list[list[list[float]]]] = []
        for i, geom in enumerate(inner_geoms):
            sub_path = f"{path}.features[{i}].geometry"
            if geom.get("type") == "Polygon":
                normalized = _validate_polygon_geom(geom, sub_path)
                merged_polys.append(normalized["coordinates"])
            else:  # MultiPolygon
                normalized = _validate_multipolygon_geom(geom, sub_path)
                for poly_coords in normalized["coordinates"]:
                    merged_polys.append(poly_coords)

        merged = {"type": "MultiPolygon", "coordinates": merged_polys}
        _enforce_area_consistency(merged, declared_area_ha, path)
        return merged

    if gtype == "Feature":
        inner = geojson.get("geometry")
        if not isinstance(inner, dict):
            raise GeoJsonValidationError(f"{path}: Feature sin geometry")
        return validate_geojson_strict(
            inner, path=f"{path}.geometry", declared_area_ha=declared_area_ha,
        )

    if gtype == "Polygon":
        result = _validate_polygon_geom(geojson, path)
        _enforce_area_consistency(result, declared_area_ha, path)
        return result
    if gtype == "MultiPolygon":
        result = _validate_multipolygon_geom(geojson, path)
        _enforce_area_consistency(result, declared_area_ha, path)
        return result
    if gtype == "Point":
        # Para Point no se valida area declarada (no hay area medible).
        return _validate_point_geom(geojson, path)

    raise GeoJsonValidationError(
        f"{path}: tipo '{gtype}' no soportado por EUDR. "
        "Use Point (parcelas <= 4 ha) o Polygon/MultiPolygon (parcelas > 4 ha)."
    )


def _enforce_area_consistency(
    normalized_geom: dict,
    declared_area_ha: float | int | Decimal | None,
    path: str,
) -> None:
    """Compara el area calculada del poligono con la declarada y rechaza si
    el ratio se sale del rango aceptable. No-op si declared es None o no
    positivo (no hay nada con que comparar)."""
    if declared_area_ha is None:
        return
    try:
        declared = Decimal(str(declared_area_ha))
    except (ArithmeticError, TypeError, ValueError):
        return
    if declared <= 0:
        return

    polygon_area = polygon_area_ha_from_geojson(normalized_geom)
    if polygon_area <= 0:
        return

    poly_dec = Decimal(str(polygon_area))
    ratio = poly_dec / declared if poly_dec >= declared else declared / poly_dec
    if ratio > AREA_MAX_RATIO:
        raise GeoJsonValidationError(
            f"{path}: el area del poligono dibujado ({polygon_area:,.2f} ha) "
            f"no coincide con el area declarada de la parcela ({float(declared):,.2f} ha) "
            f"— diferencia de {float(ratio):,.0f}x. Verifique los vertices del poligono "
            "o corrija el campo plot_area_ha. EUDR exige que la geometria represente "
            "fielmente la parcela real."
        )


def parse_decimal_geojson_from_body(raw_body: bytes | str) -> Any | None:
    """Re-parsea el body crudo del request con ``parse_float=Decimal``.

    Devuelve el campo ``geojson_data`` con coordenadas como Decimal,
    preservando ceros finales que el usuario haya escrito (ej. ``4.654400``).
    Devuelve ``None`` si el body no tiene ``geojson_data``.

    También usa ``parse_int=Decimal`` para que un literal entero como ``4``
    se reciba como ``Decimal('4')`` en lugar de ``int 4``; sin esto el chequeo
    de precision lo trataria como 0 decimales y rechazaria coordenadas
    formalmente validas (ver tests).
    """
    if not raw_body:
        return None
    try:
        data = json.loads(raw_body, parse_float=Decimal, parse_int=Decimal)
    except (json.JSONDecodeError, ValueError, TypeError):
        return None
    if not isinstance(data, dict):
        return None
    return data.get("geojson_data")


def _iter_rings(geojson: dict):
    """Yield (ring_coords) for every outer ring in a Polygon/MultiPolygon/Feature[Collection]."""
    gtype = geojson.get("type")
    if gtype == "Feature":
        yield from _iter_rings(geojson.get("geometry") or {})
        return
    if gtype == "FeatureCollection":
        for feat in geojson.get("features") or []:
            yield from _iter_rings(feat)
        return
    if gtype == "Polygon":
        rings = geojson.get("coordinates") or []
        if rings:
            yield rings[0]
        return
    if gtype == "MultiPolygon":
        for poly in geojson.get("coordinates") or []:
            if poly:
                yield poly[0]
        return


def geojson_bbox(geojson: dict) -> tuple[float, float, float, float] | None:
    """Return (min_lng, min_lat, max_lng, max_lat) of any Polygon-like geometry."""
    min_lng = min_lat = float("inf")
    max_lng = max_lat = float("-inf")
    seen = False
    for ring in _iter_rings(geojson):
        for pt in ring:
            try:
                lng = float(pt[0])
                lat = float(pt[1])
            except (TypeError, ValueError, IndexError):
                continue
            seen = True
            if lng < min_lng:
                min_lng = lng
            if lng > max_lng:
                max_lng = lng
            if lat < min_lat:
                min_lat = lat
            if lat > max_lat:
                max_lat = lat
    if not seen:
        return None
    return (min_lng, min_lat, max_lng, max_lat)


def _bbox_area(bbox: tuple[float, float, float, float]) -> float:
    return max(0.0, bbox[2] - bbox[0]) * max(0.0, bbox[3] - bbox[1])


def bbox_overlap_ratio(
    a: tuple[float, float, float, float],
    b: tuple[float, float, float, float],
) -> float:
    """Return the fraction of bbox ``a`` covered by the intersection with ``b``.

    0.0 means disjoint, 1.0 means ``a`` is fully inside ``b``. Used as a
    cheap proximity heuristic before attempting a precise polygon overlap.
    """
    inter_lng = min(a[2], b[2]) - max(a[0], b[0])
    inter_lat = min(a[3], b[3]) - max(a[1], b[1])
    if inter_lng <= 0 or inter_lat <= 0:
        return 0.0
    inter_area = inter_lng * inter_lat
    a_area = _bbox_area(a)
    if a_area <= 0:
        return 0.0
    return inter_area / a_area


def polygon_area_ha_from_geojson(geojson: dict) -> float:
    """Devuelve el area total en hectareas del Polygon/MultiPolygon dado.

    Usa la formula esferica WGS84.  Para Point devuelve 0.  Util para
    sincronizar ``plot_area_ha`` con el poligono real.
    """
    gtype = geojson.get("type")
    if gtype == "Feature":
        return polygon_area_ha_from_geojson(geojson.get("geometry") or {})
    if gtype == "FeatureCollection":
        feats = geojson.get("features") or []
        if not feats:
            return 0.0
        return polygon_area_ha_from_geojson(feats[0])
    if gtype == "Polygon":
        rings = geojson.get("coordinates") or []
        if not rings:
            return 0.0
        ext = [(Decimal(repr(c[0])), Decimal(repr(c[1]))) for c in rings[0]]
        area = _polygon_area_ha(ext)
        for hole in rings[1:]:
            h = [(Decimal(repr(c[0])), Decimal(repr(c[1]))) for c in hole]
            area -= _polygon_area_ha(h)
        return max(0.0, area)
    if gtype == "MultiPolygon":
        total = 0.0
        for poly in geojson.get("coordinates") or []:
            if not poly:
                continue
            ext = [(Decimal(repr(c[0])), Decimal(repr(c[1]))) for c in poly[0]]
            sub = _polygon_area_ha(ext)
            for hole in poly[1:]:
                h = [(Decimal(repr(c[0])), Decimal(repr(c[1]))) for c in hole]
                sub -= _polygon_area_ha(h)
            total += max(0.0, sub)
        return total
    return 0.0
