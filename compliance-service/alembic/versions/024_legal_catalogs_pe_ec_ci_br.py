"""Additional legal requirement catalogs for Peru, Ecuador, Cote d'Ivoire, Brazil.

Extends migration 023 with 4 new country x commodity catalogs so operators
sourcing coffee from Peru, cocoa from Ecuador or Cote d'Ivoire, or soy from
Brazil have a baseline catalog to work from. As with 023, each catalog is
positioned as a Trace-internal draft — production deployments should replace
it with a country-vetted version (EFI, SAFE programme, national ministry).

Each catalog ships ~10 requirements covering the 6 EUDR ambitos.

Revision ID: 024_legal_catalogs_extra
Revises: 023_legal_catalog
"""
from __future__ import annotations

import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision = "024_legal_catalogs_extra"
down_revision = "023_legal_catalog"
branch_labels = None
depends_on = None


def _reqs_peru_coffee(catalog_id: uuid.UUID) -> list[dict]:
    return [
        dict(
            id=uuid.uuid4(), catalog_id=catalog_id,
            ambito="land_use_rights", code="PE-LUR-01",
            title="Titulo de propiedad SUNARP o titulo de posesion",
            description=(
                "Partida registral SUNARP o titulo de posesion reconocido por "
                "la comunidad campesina. En produccion cafetera en San Martin / "
                "Amazonas es comun la posesion formalizada por COFOPRI."
            ),
            legal_reference="Ley 29338 (Recursos Hidricos); D.Leg. 1089 (COFOPRI)",
            applies_to_scale="all",
            required_document_type="land_title",
            is_blocking=True, sort_order=1,
        ),
        dict(
            id=uuid.uuid4(), catalog_id=catalog_id,
            ambito="land_use_rights", code="PE-LUR-02",
            title="Habilitacion agricola y zonificacion",
            description=(
                "Verificar que la parcela este dentro de zonas de aptitud "
                "agricola segun el ZEE regional y no se superponga con Bosque "
                "de Produccion Permanente (BPP)."
            ),
            legal_reference="Ley 27308 (Forestal); DS 018-2015-MINAGRI",
            applies_to_scale="medium_or_industrial",
            required_document_type="zoning_certificate",
            is_blocking=True, sort_order=2,
        ),
        dict(
            id=uuid.uuid4(), catalog_id=catalog_id,
            ambito="environmental_protection", code="PE-ENV-01",
            title="No superposicion con ANP / ACR / ACP",
            description=(
                "La parcela no debe estar dentro de un Area Natural Protegida "
                "nacional, regional o privada. Verificable en geoSERNANP."
            ),
            legal_reference="Ley 26834 (ANP); DS 038-2001-AG",
            applies_to_scale="all",
            required_document_type="protected_area_check",
            is_blocking=True, sort_order=3,
        ),
        dict(
            id=uuid.uuid4(), catalog_id=catalog_id,
            ambito="environmental_protection", code="PE-ENV-02",
            title="Certificacion ambiental DIA / EIA-sd / EIA-d",
            description=(
                "Produccion agricola industrial requiere certificacion ambiental "
                "del SENACE o la DGAAA segun categoria."
            ),
            legal_reference="Ley 27446 (SEIA); DS 019-2009-MINAM",
            applies_to_scale="industrial",
            required_document_type="environmental_license",
            is_blocking=True, sort_order=4,
        ),
        dict(
            id=uuid.uuid4(), catalog_id=catalog_id,
            ambito="labor_rights", code="PE-LAB-01",
            title="Planilla electronica (PLAME)",
            description=(
                "Productores con trabajadores asalariados deben declarar "
                "PLAME mensualmente ante SUNAT."
            ),
            legal_reference="DS 018-2007-TR",
            applies_to_scale="medium_or_industrial",
            required_document_type="plame_statement",
            is_blocking=True, sort_order=5,
        ),
        dict(
            id=uuid.uuid4(), catalog_id=catalog_id,
            ambito="human_rights", code="PE-HR-01",
            title="Ausencia de trabajo forzoso (especialmente Amazonia)",
            description=(
                "Declaracion jurada + cruce con reportes del MINJUS y la OIT "
                "sobre zonas con prevalencia de trabajo forzoso en la Amazonia."
            ),
            legal_reference="Plan Nacional contra Trabajo Forzoso 2019-2022",
            applies_to_scale="all",
            required_document_type="forced_labor_affidavit",
            is_blocking=True, sort_order=6,
        ),
        dict(
            id=uuid.uuid4(), catalog_id=catalog_id,
            ambito="third_party_rights_fpic", code="PE-FPIC-01",
            title="Consulta previa (Ley 29785)",
            description=(
                "Si la parcela afecta tierras de comunidades nativas o "
                "campesinas, debe existir registro de proceso de consulta "
                "previa conforme a Ley 29785 y Convenio OIT 169."
            ),
            legal_reference="Ley 29785; DS 001-2012-MC",
            applies_to_scale="medium_or_industrial",
            required_document_type="fpic_record",
            is_blocking=True, sort_order=7,
        ),
        dict(
            id=uuid.uuid4(), catalog_id=catalog_id,
            ambito="fiscal_customs_anticorruption", code="PE-FCA-01",
            title="RUC activo del productor u organizacion",
            description=(
                "Registro Unico de Contribuyentes vigente ante SUNAT, con "
                "actividad economica agricola declarada."
            ),
            legal_reference="DS 133-2013-EF",
            applies_to_scale="all",
            required_document_type="ruc",
            is_blocking=False, sort_order=8,
        ),
        dict(
            id=uuid.uuid4(), catalog_id=catalog_id,
            ambito="fiscal_customs_anticorruption", code="PE-FCA-02",
            title="Guia de remision electronica (movimientos)",
            description=(
                "Los movimientos de cafe en bolas/pergamino hacia acopiadores "
                "deben respaldarse con guia de remision remitente electronica."
            ),
            legal_reference="RS 188-2010/SUNAT",
            applies_to_scale="all",
            required_document_type="gre_document",
            is_blocking=False, sort_order=9,
        ),
    ]


def _reqs_ecuador_cocoa(catalog_id: uuid.UUID) -> list[dict]:
    return [
        dict(
            id=uuid.uuid4(), catalog_id=catalog_id,
            ambito="land_use_rights", code="EC-LUR-01",
            title="Escritura publica o certificado de posesion",
            description=(
                "Titulo de propiedad inscrito en el Registro de la Propiedad "
                "o certificado de posesion reconocido por la junta parroquial."
            ),
            legal_reference="Codigo Civil Ecuador; Ley de Registro",
            applies_to_scale="all",
            required_document_type="land_title",
            is_blocking=True, sort_order=1,
        ),
        dict(
            id=uuid.uuid4(), catalog_id=catalog_id,
            ambito="land_use_rights", code="EC-LUR-02",
            title="Predio registrado en el Sistema de Tierras Rurales",
            description=(
                "MAG lleva un registro nacional de predios rurales. La parcela "
                "debe estar identificada ahi con su codigo catastral."
            ),
            legal_reference="LODAFPT (Ley Tierras Rurales 2016)",
            applies_to_scale="medium_or_industrial",
            required_document_type="cadastral_certificate",
            is_blocking=False, sort_order=2,
        ),
        dict(
            id=uuid.uuid4(), catalog_id=catalog_id,
            ambito="environmental_protection", code="EC-ENV-01",
            title="No superposicion con Patrimonio Nacional de Areas Protegidas",
            description=(
                "SNAP protege ~20% del territorio ecuatoriano. Cruzar la "
                "parcela contra el mapa oficial del MAATE."
            ),
            legal_reference="Codigo Organico del Ambiente (COA) Art. 36-40",
            applies_to_scale="all",
            required_document_type="protected_area_check",
            is_blocking=True, sort_order=3,
        ),
        dict(
            id=uuid.uuid4(), catalog_id=catalog_id,
            ambito="environmental_protection", code="EC-ENV-02",
            title="Registro ambiental / Licencia ambiental",
            description=(
                "SUIA categoriza proyectos agricolas. Industriales requieren "
                "Licencia Ambiental; medianos, Registro Ambiental."
            ),
            legal_reference="Acuerdo Ministerial 109/2018",
            applies_to_scale="medium_or_industrial",
            required_document_type="environmental_license",
            is_blocking=True, sort_order=4,
        ),
        dict(
            id=uuid.uuid4(), catalog_id=catalog_id,
            ambito="labor_rights", code="EC-LAB-01",
            title="Afiliacion al IESS de trabajadores",
            description=(
                "Todo trabajador agricola permanente debe estar afiliado al "
                "Instituto Ecuatoriano de Seguridad Social."
            ),
            legal_reference="Codigo del Trabajo Art. 42",
            applies_to_scale="medium_or_industrial",
            required_document_type="iess_statement",
            is_blocking=True, sort_order=5,
        ),
        dict(
            id=uuid.uuid4(), catalog_id=catalog_id,
            ambito="human_rights", code="EC-HR-01",
            title="Ausencia de trabajo infantil",
            description=(
                "Declaracion jurada + verificacion con reportes del Ministerio "
                "de Trabajo y UNICEF sobre zonas cacaoteras."
            ),
            legal_reference="Codigo de la Ninez y Adolescencia",
            applies_to_scale="all",
            required_document_type="child_labor_affidavit",
            is_blocking=True, sort_order=6,
        ),
        dict(
            id=uuid.uuid4(), catalog_id=catalog_id,
            ambito="third_party_rights_fpic", code="EC-FPIC-01",
            title="Consulta previa libre e informada",
            description=(
                "Si la parcela limita o se superpone con territorio indigena o "
                "afroecuatoriano, debe existir registro de consulta previa "
                "segun COIP y Convenio OIT 169."
            ),
            legal_reference="Constitucion Art. 57; Convenio OIT 169",
            applies_to_scale="all",
            required_document_type="fpic_record",
            is_blocking=True, sort_order=7,
        ),
        dict(
            id=uuid.uuid4(), catalog_id=catalog_id,
            ambito="fiscal_customs_anticorruption", code="EC-FCA-01",
            title="RUC SRI activo y actividad agricola registrada",
            description="Registro Unico de Contribuyentes del SRI vigente.",
            legal_reference="Ley de Registro Unico de Contribuyentes",
            applies_to_scale="all",
            required_document_type="ruc",
            is_blocking=False, sort_order=8,
        ),
    ]


def _reqs_civ_cocoa(catalog_id: uuid.UUID) -> list[dict]:
    return [
        dict(
            id=uuid.uuid4(), catalog_id=catalog_id,
            ambito="land_use_rights", code="CI-LUR-01",
            title="Certificat foncier ou attestation villageoise",
            description=(
                "Titre foncier rural (ACD) delivre par l'AFOR, ou attestation "
                "villageoise reconnue selon loi 98-750. Le cacao en CI est "
                "majoritairement produit sous regime coutumier — l'attestation "
                "est la forme la plus frequente."
            ),
            legal_reference="Loi 98-750 sur le domaine foncier rural",
            applies_to_scale="all",
            required_document_type="land_title",
            is_blocking=True, sort_order=1,
        ),
        dict(
            id=uuid.uuid4(), catalog_id=catalog_id,
            ambito="environmental_protection", code="CI-ENV-01",
            title="Hors Forets Classees et Parcs Nationaux",
            description=(
                "La parcelle ne doit pas se trouver dans une foret classee "
                "(234 au total) ni dans un parc national. L'OIPR et la SODEFOR "
                "publient les limites officielles. Le cacao sous foret classee "
                "est une cause majeure de refus EUDR."
            ),
            legal_reference="Code Forestier 2019-675; Loi Parcs Nationaux",
            applies_to_scale="all",
            required_document_type="protected_area_check",
            is_blocking=True, sort_order=2,
        ),
        dict(
            id=uuid.uuid4(), catalog_id=catalog_id,
            ambito="environmental_protection", code="CI-ENV-02",
            title="Etude d'impact environnemental (EIE)",
            description=(
                "Production cacaoyere de grande taille requiert EIE validee "
                "par l'ANDE selon le decret 96-894."
            ),
            legal_reference="Decret 96-894 (EIE); Loi 96-766",
            applies_to_scale="industrial",
            required_document_type="eia_report",
            is_blocking=True, sort_order=3,
        ),
        dict(
            id=uuid.uuid4(), catalog_id=catalog_id,
            ambito="labor_rights", code="CI-LAB-01",
            title="Contrats de travail ecrits (main d'oeuvre salariee)",
            description=(
                "Travailleurs permanents et saisonniers doivent etre "
                "declares a la CNPS et avoir un contrat ecrit."
            ),
            legal_reference="Code du Travail; Loi 95-15",
            applies_to_scale="medium_or_industrial",
            required_document_type="labor_contract",
            is_blocking=True, sort_order=4,
        ),
        dict(
            id=uuid.uuid4(), catalog_id=catalog_id,
            ambito="human_rights", code="CI-HR-01",
            title="Systeme de suivi du travail des enfants (CLMRS)",
            description=(
                "Zone cacaoyere classee a haut risque de travail infantile. "
                "Preuve de participation en CLMRS (Child Labour Monitoring "
                "and Remediation System) de l'ICI ou equivalent."
            ),
            legal_reference="Plan d'Action National Travail des Enfants",
            applies_to_scale="all",
            required_document_type="clmrs_enrollment",
            is_blocking=True, sort_order=5,
        ),
        dict(
            id=uuid.uuid4(), catalog_id=catalog_id,
            ambito="human_rights", code="CI-HR-02",
            title="Protection contre les pesticides (formation + EPI)",
            description=(
                "Usage d'intrants agrees par le CSP et formation documentee "
                "des applicateurs."
            ),
            legal_reference="Arrete 0043/2008/MAGRH",
            applies_to_scale="medium_or_industrial",
            required_document_type="epp_training_record",
            is_blocking=False, sort_order=6,
        ),
        dict(
            id=uuid.uuid4(), catalog_id=catalog_id,
            ambito="third_party_rights_fpic", code="CI-FPIC-01",
            title="Consentement communautaire (si conversion recente)",
            description=(
                "Pour toute extension de parcelle posterieure a 2020, preuve "
                "d'accord avec la chefferie villageoise et absence de conflit "
                "avec des utilisateurs coutumiers."
            ),
            legal_reference="Loi 98-750; coutume villageoise",
            applies_to_scale="all",
            required_document_type="community_agreement",
            is_blocking=True, sort_order=7,
        ),
        dict(
            id=uuid.uuid4(), catalog_id=catalog_id,
            ambito="fiscal_customs_anticorruption", code="CI-FCA-01",
            title="Immatriculation Conseil Cafe-Cacao",
            description=(
                "Producteurs et cooperatives doivent etre immatricules "
                "aupres du Conseil du Cafe-Cacao (CCC)."
            ),
            legal_reference="Ordonnance 2011-481",
            applies_to_scale="all",
            required_document_type="ccc_registration",
            is_blocking=True, sort_order=8,
        ),
    ]


def _reqs_brazil_soy(catalog_id: uuid.UUID) -> list[dict]:
    return [
        dict(
            id=uuid.uuid4(), catalog_id=catalog_id,
            ambito="land_use_rights", code="BR-LUR-01",
            title="Matricula do imovel rural (Cartorio de Registro)",
            description=(
                "Matricula atualizada do Cartorio de Registro de Imoveis "
                "comprovando titularidade da area produtora."
            ),
            legal_reference="Lei 6.015/1973",
            applies_to_scale="all",
            required_document_type="land_title",
            is_blocking=True, sort_order=1,
        ),
        dict(
            id=uuid.uuid4(), catalog_id=catalog_id,
            ambito="land_use_rights", code="BR-LUR-02",
            title="CAR — Cadastro Ambiental Rural ativo",
            description=(
                "Registro eletronico obrigatorio para todos os imoveis rurais. "
                "Inclui perimetro georreferenciado da propriedade e das "
                "areas de reserva legal / APP. Cruzable com EUDR."
            ),
            legal_reference="Lei 12.651/2012 (Codigo Florestal)",
            applies_to_scale="all",
            required_document_type="car_certificate",
            is_blocking=True, sort_order=2,
        ),
        dict(
            id=uuid.uuid4(), catalog_id=catalog_id,
            ambito="environmental_protection", code="BR-ENV-01",
            title="Reserva legal e APP cumpridas",
            description=(
                "Amazonia: 80% de reserva legal; Cerrado na Amazonia Legal: "
                "35%; demais: 20%. Areas de Preservacao Permanente tambem "
                "devem estar preservadas. PRA em andamento se houver passivo."
            ),
            legal_reference="Lei 12.651/2012 Art. 12 e 4",
            applies_to_scale="all",
            required_document_type="rl_app_declaration",
            is_blocking=True, sort_order=3,
        ),
        dict(
            id=uuid.uuid4(), catalog_id=catalog_id,
            ambito="environmental_protection", code="BR-ENV-02",
            title="Licenciamento ambiental",
            description=(
                "Licenca previa, de instalacao e operacao conforme resolucao "
                "CONAMA 237/1997 e legislacao estadual aplicavel (ex: "
                "SEMA-MT, IMASUL, SEMAS-PA)."
            ),
            legal_reference="Res. CONAMA 237/1997; Lei Complementar 140/2011",
            applies_to_scale="medium_or_industrial",
            required_document_type="environmental_license",
            is_blocking=True, sort_order=4,
        ),
        dict(
            id=uuid.uuid4(), catalog_id=catalog_id,
            ambito="environmental_protection", code="BR-ENV-03",
            title="Nao inclusao na 'Lista Suja' (embargos IBAMA)",
            description=(
                "Verificar que o imovel nao esteja na lista de areas "
                "embargadas do IBAMA por desmatamento ilegal."
            ),
            legal_reference="Decreto 6.514/2008",
            applies_to_scale="all",
            required_document_type="ibama_embargo_check",
            is_blocking=True, sort_order=5,
        ),
        dict(
            id=uuid.uuid4(), catalog_id=catalog_id,
            ambito="labor_rights", code="BR-LAB-01",
            title="Nao inclusao na 'Lista Suja' do Trabalho (MTE)",
            description=(
                "Cruzar CPF/CNPJ contra o Cadastro de Empregadores que "
                "tenham submetido trabalhadores a condicoes analogas a escravidao."
            ),
            legal_reference="Portaria MTE 540/2004",
            applies_to_scale="all",
            required_document_type="mte_slave_labor_check",
            is_blocking=True, sort_order=6,
        ),
        dict(
            id=uuid.uuid4(), catalog_id=catalog_id,
            ambito="human_rights", code="BR-HR-01",
            title="Compromisso com Moratoria da Soja (Amazonia)",
            description=(
                "Soja produzida em areas desmatadas apos 22/07/2008 na "
                "Amazonia nao pode ser comercializada pelos signatarios da "
                "Moratoria da Soja (ABIOVE, ANEC)."
            ),
            legal_reference="Moratoria da Soja 2006",
            applies_to_scale="all",
            required_document_type="soy_moratorium_declaration",
            is_blocking=True, sort_order=7,
        ),
        dict(
            id=uuid.uuid4(), catalog_id=catalog_id,
            ambito="third_party_rights_fpic", code="BR-FPIC-01",
            title="Nao sobreposicao com terras indigenas e quilombolas",
            description=(
                "Cruzar com bases oficiais da FUNAI (terras indigenas) e "
                "INCRA (territorios quilombolas reconhecidos)."
            ),
            legal_reference="Constituicao Art. 231; Decreto 4.887/2003",
            applies_to_scale="all",
            required_document_type="indigenous_quilombola_check",
            is_blocking=True, sort_order=8,
        ),
        dict(
            id=uuid.uuid4(), catalog_id=catalog_id,
            ambito="fiscal_customs_anticorruption", code="BR-FCA-01",
            title="CNPJ / CPF ativo e regularidade fiscal",
            description=(
                "Certidao Negativa de Debitos Federais e estaduais. Receita "
                "Federal mostra status do CNPJ."
            ),
            legal_reference="Lei 5.172/1966 (CTN)",
            applies_to_scale="all",
            required_document_type="rut",
            is_blocking=False, sort_order=9,
        ),
    ]


def upgrade() -> None:
    catalogs = sa.table(
        "legal_requirement_catalogs",
        sa.column("id", UUID(as_uuid=True)),
        sa.column("country_code", sa.Text()),
        sa.column("commodity", sa.Text()),
        sa.column("version", sa.Text()),
        sa.column("source", sa.Text()),
        sa.column("source_url", sa.Text()),
    )
    reqs = sa.table(
        "legal_requirements",
        sa.column("id", UUID(as_uuid=True)),
        sa.column("catalog_id", UUID(as_uuid=True)),
        sa.column("ambito", sa.Text()),
        sa.column("code", sa.Text()),
        sa.column("title", sa.Text()),
        sa.column("description", sa.Text()),
        sa.column("legal_reference", sa.Text()),
        sa.column("applies_to_scale", sa.Text()),
        sa.column("required_document_type", sa.Text()),
        sa.column("is_blocking", sa.Boolean()),
        sa.column("sort_order", sa.Integer()),
    )

    catalog_specs = [
        ("PE", "coffee", _reqs_peru_coffee),
        ("EC", "cocoa", _reqs_ecuador_cocoa),
        ("CI", "cocoa", _reqs_civ_cocoa),
        ("BR", "soy", _reqs_brazil_soy),
    ]

    catalog_rows: list[dict] = []
    req_rows: list[dict] = []

    for country, commodity, builder in catalog_specs:
        cat_id = uuid.uuid4()
        catalog_rows.append(
            dict(
                id=cat_id,
                country_code=country,
                commodity=commodity,
                version="2026.04-eudr-v1",
                source="Trace internal draft — EFI/SAFE-style mapping",
                source_url=None,
            )
        )
        req_rows.extend(builder(cat_id))

    op.bulk_insert(catalogs, catalog_rows)
    op.bulk_insert(reqs, req_rows)


def downgrade() -> None:
    op.execute(
        "DELETE FROM legal_requirement_catalogs "
        "WHERE version = '2026.04-eudr-v1' "
        "AND (country_code, commodity) IN "
        "(('PE','coffee'),('EC','cocoa'),('CI','cocoa'),('BR','soy'))"
    )
