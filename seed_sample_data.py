from datetime import date
from decimal import Decimal

from app import create_app, db
from app.models import (
    Contract,
    ContractPosition,
    ContractPositionVersion,
    Customer,
    Supplier,
)


CUSTOMERS = [
    {
        "customer_no": "K-1001",
        "name": "Musterstadtwerke GmbH",
        "contact_name": "Julia Becker",
        "email": "julia.becker@musterstadtwerke.example",
        "street": "Energieallee 12",
        "postal_code": "24103",
        "city": "Kiel",
        "country": "Deutschland",
        "notes": "Rahmenkunde für wiederkehrende Beratungsleistungen.",
    },
    {
        "customer_no": "K-1002",
        "name": "Nordlicht Pflege AG",
        "contact_name": "Matthias Reuter",
        "email": "matthias.reuter@nordlicht-pflege.example",
        "street": "Hafenstraße 8",
        "postal_code": "23552",
        "city": "Lübeck",
        "country": "Deutschland",
        "notes": "Mehrere Standorte, Abrechnung quartalsweise prüfen.",
    },
    {
        "customer_no": "K-1003",
        "name": "Hoyer Handel & Service",
        "contact_name": "Michaela Hoyer",
        "email": "kontakt@hoyer-handel.example",
        "street": "Dorfstraße 4",
        "postal_code": "24646",
        "city": "Warder",
        "country": "Deutschland",
        "notes": "Demo-Kunde für Projekt- und Servicepositionen.",
    },
    {
        "customer_no": "K-1004",
        "name": "Baltic Events UG",
        "contact_name": "Svenja Krüger",
        "email": "svenja.krueger@baltic-events.example",
        "street": "Markt 2",
        "postal_code": "18055",
        "city": "Rostock",
        "country": "Deutschland",
        "notes": "Saisonale Leistungen, Vertrag endet automatisch.",
    },
]

SUPPLIERS = [
    {
        "supplier_no": "L-2001",
        "name": "CloudWerk Hosting GmbH",
        "contact_name": "Nina Schulte",
        "email": "billing@cloudwerk.example",
        "street": "Serverpark 1",
        "postal_code": "20457",
        "city": "Hamburg",
        "country": "Deutschland",
        "notes": "Hosting, Backups und Monitoring.",
    },
    {
        "supplier_no": "L-2002",
        "name": "OfficePro Leasing KG",
        "contact_name": "Jan Petersen",
        "email": "jan.petersen@officepro.example",
        "street": "Gewerbering 19",
        "postal_code": "24534",
        "city": "Neumünster",
        "country": "Deutschland",
        "notes": "Hardware-Leasing mit automatischer Verlängerung.",
    },
    {
        "supplier_no": "L-2003",
        "name": "TeleNord Connect GmbH",
        "contact_name": "Support Team",
        "email": "service@telenord.example",
        "street": "Funkweg 7",
        "postal_code": "28195",
        "city": "Bremen",
        "country": "Deutschland",
        "notes": "Internet- und Mobilfunkverträge.",
    },
    {
        "supplier_no": "L-2004",
        "name": "Versicherungskontor Hansen",
        "contact_name": "Ole Hansen",
        "email": "ole.hansen@vk-hansen.example",
        "street": "Alte Reihe 33",
        "postal_code": "24768",
        "city": "Rendsburg",
        "country": "Deutschland",
        "notes": "Jährliche Versicherungspolicen.",
    },
]

CONTRACTS = [
    {
        "partner_kind": "customer",
        "partner_name": "Musterstadtwerke GmbH",
        "contract_no": "V-2026-001",
        "title": "Wartung Vertragsdatenbank",
        "contract_type": "revenue",
        "status": "active",
        "start_date": date(2026, 1, 1),
        "end_date": date(2026, 12, 31),
        "cancellation_date": date(2026, 9, 30),
        "renewal_type": "automatic",
        "responsible": "Arne",
        "description": "Monatliche Wartung, kleinere Anpassungen und Support für interne Vertragsplanung.",
        "positions": [
            {
                "name": "Basiswartung",
                "amount": "1250.00",
                "recurrence": "monthly",
                "billing_day": 1,
                "account": "8400",
                "cost_center_1": "Software",
                "note": "Monatliche Pauschale.",
            },
            {
                "name": "Support-Kontingent 10h",
                "amount": "950.00",
                "recurrence": "monthly",
                "billing_day": 15,
                "account": "8400",
                "cost_center_1": "Support",
                "note": "Nicht genutzte Stunden verfallen zum Monatsende.",
            },
        ],
    },
    {
        "partner_kind": "customer",
        "partner_name": "Nordlicht Pflege AG",
        "contract_no": "V-2026-002",
        "title": "Standort-Lizenzpaket Pflegeplanung",
        "contract_type": "revenue",
        "status": "active",
        "start_date": date(2026, 2, 1),
        "end_date": date(2028, 1, 31),
        "cancellation_date": date(2027, 10, 31),
        "renewal_type": "automatic",
        "responsible": "Claudia",
        "description": "Lizenz- und Servicevertrag für mehrere Pflegeeinrichtungen.",
        "positions": [
            {
                "name": "Lizenzpaket 5 Standorte",
                "amount": "4200.00",
                "recurrence": "quarterly",
                "billing_day": 5,
                "account": "8300",
                "cost_center_1": "Lizenzen",
            },
            {
                "name": "Onboarding neuer Standort",
                "amount": "2800.00",
                "recurrence": "once",
                "billing_day": 10,
                "account": "8400",
                "cost_center_1": "Projekt",
                "note": "Einmalig im ersten Quartal.",
            },
        ],
    },
    {
        "partner_kind": "customer",
        "partner_name": "Hoyer Handel & Service",
        "contract_no": "V-2026-003",
        "title": "Servicevertrag Warenwirtschaft",
        "contract_type": "revenue",
        "status": "forecast",
        "start_date": date(2026, 8, 1),
        "end_date": date(2027, 7, 31),
        "cancellation_date": date(2027, 4, 30),
        "renewal_type": "manual",
        "responsible": "Arne",
        "description": "Geplanter Servicevertrag für Warenwirtschaft, Reporting und Datenpflege.",
        "positions": [
            {
                "name": "Servicepauschale",
                "amount": "680.00",
                "recurrence": "monthly",
                "billing_day": 1,
                "account": "8400",
                "cost_center_1": "Service",
            },
            {
                "name": "Berichtspaket Lagerumschlag",
                "amount": "1450.00",
                "recurrence": "once",
                "billing_day": 20,
                "account": "8400",
                "cost_center_1": "Reporting",
            },
        ],
    },
    {
        "partner_kind": "customer",
        "partner_name": "Baltic Events UG",
        "contract_no": "V-2025-014",
        "title": "Event-Support Sommersaison",
        "contract_type": "revenue",
        "status": "ended",
        "start_date": date(2025, 5, 1),
        "end_date": date(2025, 9, 30),
        "cancellation_date": None,
        "renewal_type": "none",
        "responsible": "Claudia",
        "description": "Abgeschlossener Saisonvertrag als Beispiel für beendete Verträge.",
        "positions": [
            {
                "name": "Saison-Support",
                "amount": "3600.00",
                "recurrence": "once",
                "billing_day": 1,
                "account": "8400",
                "cost_center_1": "Projekt",
            },
        ],
    },
    {
        "partner_kind": "supplier",
        "partner_name": "CloudWerk Hosting GmbH",
        "contract_no": "E-2026-101",
        "title": "Cloud-Hosting Produktionssysteme",
        "contract_type": "cost",
        "status": "active",
        "start_date": date(2026, 1, 1),
        "end_date": None,
        "cancellation_date": date(2026, 11, 30),
        "renewal_type": "automatic",
        "responsible": "Arne",
        "description": "Hosting, Datenbank-Backups, Monitoring und Basis-SLA.",
        "positions": [
            {
                "name": "Managed Server",
                "amount": "210.00",
                "recurrence": "monthly",
                "billing_day": 1,
                "account": "4900",
                "cost_center_1": "IT",
            },
            {
                "name": "Backup-Speicher 500 GB",
                "amount": "49.00",
                "recurrence": "monthly",
                "billing_day": 1,
                "account": "4900",
                "cost_center_1": "IT",
                "note": "Skaliert bei Bedarf.",
            },
        ],
    },
    {
        "partner_kind": "supplier",
        "partner_name": "OfficePro Leasing KG",
        "contract_no": "E-2026-102",
        "title": "Notebook-Leasing Team",
        "contract_type": "cost",
        "status": "active",
        "start_date": date(2026, 3, 1),
        "end_date": date(2029, 2, 28),
        "cancellation_date": date(2028, 11, 30),
        "renewal_type": "manual",
        "responsible": "Arne",
        "description": "Leasingvertrag für Arbeitsgeräte inkl. Austauschservice.",
        "positions": [
            {
                "name": "5x Business-Notebook",
                "amount": "375.00",
                "recurrence": "monthly",
                "billing_day": 3,
                "account": "4810",
                "cost_center_1": "Hardware",
            },
            {
                "name": "Austauschservice Premium",
                "amount": "540.00",
                "recurrence": "yearly",
                "billing_day": 3,
                "account": "4800",
                "cost_center_1": "Hardware",
            },
        ],
    },
    {
        "partner_kind": "supplier",
        "partner_name": "TeleNord Connect GmbH",
        "contract_no": "E-2026-103",
        "title": "Internet und Mobilfunk Büro",
        "contract_type": "cost",
        "status": "active",
        "start_date": date(2026, 4, 15),
        "end_date": date(2028, 4, 14),
        "cancellation_date": date(2028, 1, 14),
        "renewal_type": "automatic",
        "responsible": "Claudia",
        "description": "Festnetzanschluss, Routermiete und zwei Mobilfunkkarten.",
        "positions": [
            {
                "name": "Glasfaser 500 Mbit",
                "amount": "89.90",
                "recurrence": "monthly",
                "billing_day": 15,
                "account": "4920",
                "cost_center_1": "Kommunikation",
            },
            {
                "name": "Mobilfunkkarten",
                "amount": "59.80",
                "recurrence": "monthly",
                "billing_day": 15,
                "account": "4920",
                "cost_center_1": "Kommunikation",
            },
        ],
    },
    {
        "partner_kind": "supplier",
        "partner_name": "Versicherungskontor Hansen",
        "contract_no": "E-2026-104",
        "title": "Betriebshaftpflicht 2026",
        "contract_type": "cost",
        "status": "active",
        "start_date": date(2026, 1, 1),
        "end_date": date(2026, 12, 31),
        "cancellation_date": date(2026, 9, 30),
        "renewal_type": "automatic",
        "responsible": "Arne",
        "description": "Jährliche Betriebshaftpflicht inkl. Vermögensschaden-Zusatz.",
        "positions": [
            {
                "name": "Jahrespraemie Betriebshaftpflicht",
                "amount": "1320.00",
                "recurrence": "yearly",
                "billing_day": 1,
                "account": "4360",
                "cost_center_1": "Versicherung",
            },
        ],
    },
    {
        "partner_kind": "supplier",
        "partner_name": "CloudWerk Hosting GmbH",
        "contract_no": "E-2025-099",
        "title": "Altes Testsystem Hosting",
        "contract_type": "cost",
        "status": "cancelled",
        "start_date": date(2025, 1, 1),
        "end_date": date(2026, 6, 30),
        "cancellation_date": date(2026, 3, 31),
        "renewal_type": "none",
        "responsible": "Claudia",
        "description": "Gekündigtes Alt-System als Beispiel für Status cancelled.",
        "positions": [
            {
                "name": "Legacy VPS",
                "amount": "79.00",
                "recurrence": "monthly",
                "billing_day": 1,
                "account": "4900",
                "cost_center_1": "IT",
            },
        ],
    },
]


EXTRA_CONTRACTS = [
    {
        "partner_kind": "customer",
        "partner_name": "Musterstadtwerke GmbH",
        "contract_no": "V-2026-010",
        "title": "Energieportal Premium-Support",
        "contract_type": "revenue",
        "status": "active",
        "start_date": date(2026, 7, 1),
        "end_date": date(2027, 6, 30),
        "cancellation_date": None,
        "cancellation_period_value": 3,
        "cancellation_period_unit": "months",
        "renewal_type": "automatic",
        "responsible": "Arne",
        "description": "Demo-Vertrag mit dreimonatiger Kündigungsfrist und automatischer Verlängerung.",
        "positions": [
            {"name": "Premium-Support", "amount": "1850.00", "recurrence": "monthly", "billing_day": 1, "account": "8400", "cost_center_1": "Support"},
            {"name": "Quartals-Review", "amount": "1200.00", "recurrence": "quarterly", "billing_day": 15, "account": "8400", "cost_center_1": "Review"},
        ],
    },
    {
        "partner_kind": "customer",
        "partner_name": "Nordlicht Pflege AG",
        "contract_no": "V-2026-011",
        "title": "Datenschutz-Audit Pflegeverbund",
        "contract_type": "revenue",
        "status": "active",
        "start_date": date(2026, 5, 1),
        "end_date": date(2026, 10, 31),
        "cancellation_date": None,
        "cancellation_period_value": 6,
        "cancellation_period_unit": "weeks",
        "renewal_type": "manual",
        "responsible": "Claudia",
        "description": "Zeitlich begrenzter Audit-Vertrag mit sechswöchiger Kündigungsfrist.",
        "positions": [
            {"name": "Audit-Pauschale", "amount": "5400.00", "recurrence": "once", "billing_day": 1, "account": "8400", "cost_center_1": "Audit"},
        ],
    },
    {
        "partner_kind": "customer",
        "partner_name": "Baltic Events UG",
        "contract_no": "V-2026-012",
        "title": "Ticketing-Schnittstelle Festival",
        "contract_type": "revenue",
        "status": "forecast",
        "start_date": date(2026, 9, 1),
        "end_date": date(2027, 8, 31),
        "cancellation_date": None,
        "cancellation_period_value": 30,
        "cancellation_period_unit": "days",
        "renewal_type": "automatic",
        "responsible": "Arne",
        "description": "Forecast-Beispiel mit 30 Tagen Kündigungsfrist.",
        "positions": [
            {"name": "Schnittstellenbetrieb", "amount": "990.00", "recurrence": "monthly", "billing_day": 1, "account": "8400", "cost_center_1": "Integration"},
            {"name": "Einrichtung und Test", "amount": "3200.00", "recurrence": "once", "billing_day": 5, "account": "8400", "cost_center_1": "Projekt"},
        ],
    },
    {
        "partner_kind": "supplier",
        "partner_name": "CloudWerk Hosting GmbH",
        "contract_no": "E-2026-110",
        "title": "Monitoring Plus Paket",
        "contract_type": "cost",
        "status": "active",
        "start_date": date(2026, 6, 1),
        "end_date": date(2027, 5, 31),
        "cancellation_date": None,
        "cancellation_period_value": 60,
        "cancellation_period_unit": "days",
        "renewal_type": "automatic",
        "responsible": "Claudia",
        "description": "Lieferantenvertrag mit 60 Tagen Kündigungsfrist.",
        "positions": [
            {"name": "Monitoring Plus", "amount": "149.00", "recurrence": "monthly", "billing_day": 1, "account": "4900", "cost_center_1": "IT"},
        ],
    },
    {
        "partner_kind": "supplier",
        "partner_name": "TeleNord Connect GmbH",
        "contract_no": "E-2026-111",
        "title": "Mobilfunk Außendienst",
        "contract_type": "cost",
        "status": "active",
        "start_date": date(2026, 8, 1),
        "end_date": date(2028, 7, 31),
        "cancellation_date": None,
        "cancellation_period_value": 3,
        "cancellation_period_unit": "months",
        "renewal_type": "automatic",
        "responsible": "Arne",
        "description": "Mobilfunkvertrag mit klassischer dreimonatiger Kündigungsfrist.",
        "positions": [
            {"name": "5x Mobilfunk Allnet", "amount": "124.50", "recurrence": "monthly", "billing_day": 1, "account": "4920", "cost_center_1": "Kommunikation"},
        ],
    },
    {
        "partner_kind": "supplier",
        "partner_name": "Versicherungskontor Hansen",
        "contract_no": "E-2026-112",
        "title": "Cyberversicherung",
        "contract_type": "cost",
        "status": "active",
        "start_date": date(2026, 1, 1),
        "end_date": date(2026, 12, 31),
        "cancellation_date": None,
        "cancellation_period_value": 3,
        "cancellation_period_unit": "months",
        "renewal_type": "automatic",
        "responsible": "Claudia",
        "description": "Jährlicher Versicherungsvertrag, gut zum Testen der 90-Tage-Kündigungsansicht.",
        "positions": [
            {"name": "Jahresprämie Cyberversicherung", "amount": "980.00", "recurrence": "yearly", "billing_day": 1, "account": "4360", "cost_center_1": "Versicherung"},
        ],
    },
]


def upsert_party(model, key_field, data):
    existing = model.query.filter_by(name=data["name"]).first()
    if existing is None:
        existing = model()
        db.session.add(existing)

    for key, value in data.items():
        setattr(existing, key, value)

    if not getattr(existing, "status", None):
        existing.status = "active"

    return existing


def create_position(contract, position_data, sort_order):
    position = ContractPosition(
        contract=contract,
        name=position_data["name"],
        position_type=contract.contract_type,
        status="active",
        sort_order=sort_order,
    )
    version = ContractPositionVersion(
        position=position,
        valid_from=contract.start_date,
        amount=Decimal(position_data["amount"]),
        currency="EUR",
        account=position_data.get("account"),
        cost_center_1=position_data.get("cost_center_1"),
        cost_center_2=position_data.get("cost_center_2"),
        recurrence=position_data.get("recurrence", "monthly"),
        billing_day=position_data.get("billing_day"),
        is_active=True,
        note=position_data.get("note"),
    )
    db.session.add(position)
    db.session.add(version)


def seed_contract(contract_data, customers_by_name, suppliers_by_name):
    contract = Contract.query.filter_by(contract_no=contract_data["contract_no"]).first()
    if contract is None:
        contract = Contract(contract_no=contract_data["contract_no"])
        db.session.add(contract)

    contract.customer_id = None
    contract.supplier_id = None
    if contract_data["partner_kind"] == "customer":
        contract.customer = customers_by_name[contract_data["partner_name"]]
    else:
        contract.supplier = suppliers_by_name[contract_data["partner_name"]]

    for key in (
        "title",
        "contract_type",
        "status",
        "start_date",
        "end_date",
        "cancellation_date",
        "cancellation_period_value",
        "cancellation_period_unit",
        "renewal_type",
        "responsible",
        "description",
    ):
        setattr(contract, key, contract_data.get(key))

    safe_contract_no = contract_data["contract_no"].lower().replace("-", "")
    contract.contract_link = contract_data.get(
        "contract_link",
        f"https://example.com/demo/verträge/{safe_contract_no}",
    )
    contract.invoice_link = contract_data.get(
        "invoice_link",
        f"https://example.com/demo/rechnungen/{safe_contract_no}",
    )

    # Keep reruns deterministic: replace only demo positions for this demo contract.
    contract.positions.clear()
    for index, position_data in enumerate(contract_data["positions"], start=1):
        create_position(contract, position_data, index)

    return contract


def main():
    app = create_app()
    with app.app_context():
        db.create_all()

        customers_by_name = {
            data["name"]: upsert_party(Customer, "customer_no", data)
            for data in CUSTOMERS
        }
        suppliers_by_name = {
            data["name"]: upsert_party(Supplier, "supplier_no", data)
            for data in SUPPLIERS
        }

        for contract_data in CONTRACTS + EXTRA_CONTRACTS:
            seed_contract(contract_data, customers_by_name, suppliers_by_name)

        db.session.commit()

        print("Beispieldaten eingespielt:")
        print(f"- Kunden: {Customer.query.count()}")
        print(f"- Lieferanten: {Supplier.query.count()}")
        print(f"- Verträge: {Contract.query.count()}")
        print(f"- Positionen: {ContractPosition.query.count()}")
        print(f"- Positionsversionen: {ContractPositionVersion.query.count()}")


if __name__ == "__main__":
    main()
