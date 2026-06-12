from app import create_app, db
import app.models

app = create_app()


def get_columns(connection, table_name):
    return {
        row[1]: {
            "type": row[2],
            "notnull": bool(row[3]),
        }
        for row in connection.exec_driver_sql(f"PRAGMA table_info({table_name})")
    }


def add_missing_party_columns(connection, table_name):
    columns = get_columns(connection, table_name)
    definitions = {
        "street": "VARCHAR(255)",
        "postal_code": "VARCHAR(20)",
        "city": "VARCHAR(255)",
        "country": "VARCHAR(100)",
    }

    for column_name, column_type in definitions.items():
        if column_name not in columns:
            connection.exec_driver_sql(
                f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"
            )


def migrate_contract_table(connection):
    columns = get_columns(connection, "contract")
    needs_supplier_id = "supplier_id" not in columns
    needs_nullable_customer = columns.get("customer_id", {}).get("notnull", False)

    if not needs_supplier_id and not needs_nullable_customer:
        return

    connection.exec_driver_sql("PRAGMA foreign_keys=OFF")
    connection.exec_driver_sql("""
        CREATE TABLE contract_new (
            id INTEGER NOT NULL PRIMARY KEY,
            customer_id INTEGER,
            supplier_id INTEGER,
            contract_no VARCHAR(50),
            title VARCHAR(255) NOT NULL,
            contract_type VARCHAR(20),
            status VARCHAR(50),
            start_date DATE NOT NULL,
            end_date DATE,
            cancellation_date DATE,
            renewal_type VARCHAR(50),
            responsible VARCHAR(255),
            description TEXT,
            created_at DATETIME,
            updated_at DATETIME,
            FOREIGN KEY(customer_id) REFERENCES customer (id),
            FOREIGN KEY(supplier_id) REFERENCES supplier (id)
        )
    """)
    connection.exec_driver_sql("""
        INSERT INTO contract_new (
            id,
            customer_id,
            contract_no,
            title,
            contract_type,
            status,
            start_date,
            end_date,
            cancellation_date,
            renewal_type,
            responsible,
            description,
            created_at,
            updated_at
        )
        SELECT
            id,
            customer_id,
            contract_no,
            title,
            contract_type,
            status,
            start_date,
            end_date,
            cancellation_date,
            renewal_type,
            responsible,
            description,
            created_at,
            updated_at
        FROM contract
    """)
    connection.exec_driver_sql("DROP TABLE contract")
    connection.exec_driver_sql("ALTER TABLE contract_new RENAME TO contract")
    connection.exec_driver_sql("PRAGMA foreign_keys=ON")


with app.app_context():
    db.create_all()
    with db.engine.begin() as connection:
        add_missing_party_columns(connection, "customer")
        add_missing_party_columns(connection, "supplier")
        migrate_contract_table(connection)

    print("Datenbank erzeugt oder aktualisiert")
