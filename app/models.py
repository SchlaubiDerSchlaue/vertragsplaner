from datetime import datetime
from app import db


class Customer(db.Model):
    __tablename__ = "customer"

    id = db.Column(db.Integer, primary_key=True)
    customer_no = db.Column(db.String(50))
    name = db.Column(db.String(255), nullable=False, unique=True)
    status = db.Column(db.String(50), default="active")
    contact_name = db.Column(db.String(255))
    email = db.Column(db.String(255))
    street = db.Column(db.String(255))
    postal_code = db.Column(db.String(20))
    city = db.Column(db.String(255))
    country = db.Column(db.String(100))
    notes = db.Column(db.Text)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    contracts = db.relationship("Contract", back_populates="customer", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Customer {self.name}>"


class Supplier(db.Model):
    __tablename__ = "supplier"

    id = db.Column(db.Integer, primary_key=True)
    supplier_no = db.Column(db.String(50))
    name = db.Column(db.String(255), nullable=False, unique=True)
    status = db.Column(db.String(50), default="active")
    contact_name = db.Column(db.String(255))
    email = db.Column(db.String(255))
    street = db.Column(db.String(255))
    postal_code = db.Column(db.String(20))
    city = db.Column(db.String(255))
    country = db.Column(db.String(100))
    notes = db.Column(db.Text)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    contracts = db.relationship("Contract", back_populates="supplier", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Supplier {self.name}>"


class Contract(db.Model):
    __tablename__ = "contract"

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("customer.id"))
    supplier_id = db.Column(db.Integer, db.ForeignKey("supplier.id"))

    contract_no = db.Column(db.String(50))
    title = db.Column(db.String(255), nullable=False)

    # revenue / cost
    contract_type = db.Column(db.String(20), default="revenue")

    # draft / active / forecast / cancelled / ended
    status = db.Column(db.String(50), default="draft")

    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date)
    cancellation_date = db.Column(db.Date)
    renewal_type = db.Column(db.String(50), default="none")

    responsible = db.Column(db.String(255))
    description = db.Column(db.Text)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    customer = db.relationship("Customer", back_populates="contracts")
    supplier = db.relationship("Supplier", back_populates="contracts")
    positions = db.relationship("ContractPosition", back_populates="contract", cascade="all, delete-orphan")

    @property
    def partner(self):
        return self.customer or self.supplier

    @property
    def partner_name(self):
        return self.partner.name if self.partner else ""

    @property
    def partner_type(self):
        if self.customer_id:
            return "Kunde"
        if self.supplier_id:
            return "Lieferant"
        return ""

    def __repr__(self):
        return f"<Contract {self.title}>"


class ContractPosition(db.Model):
    __tablename__ = "contract_position"

    id = db.Column(db.Integer, primary_key=True)
    contract_id = db.Column(db.Integer, db.ForeignKey("contract.id"), nullable=False)

    name = db.Column(db.String(255), nullable=False)

    # revenue / cost
    position_type = db.Column(db.String(20), default="revenue")

    # active / inactive
    status = db.Column(db.String(50), default="active")
    sort_order = db.Column(db.Integer, default=0)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    contract = db.relationship("Contract", back_populates="positions")
    versions = db.relationship(
        "ContractPositionVersion",
        back_populates="position",
        cascade="all, delete-orphan",
        order_by="ContractPositionVersion.valid_from"
    )

    def __repr__(self):
        return f"<ContractPosition {self.name}>"


class ContractPositionVersion(db.Model):
    __tablename__ = "contract_position_version"

    id = db.Column(db.Integer, primary_key=True)
    position_id = db.Column(db.Integer, db.ForeignKey("contract_position.id"), nullable=False)

    valid_from = db.Column(db.Date, nullable=False)
    valid_to = db.Column(db.Date)

    amount = db.Column(db.Numeric(12, 2), nullable=False)
    currency = db.Column(db.String(3), default="EUR")

    # v1: Freitext, später optional Stammdatenbindung
    account = db.Column(db.String(50))
    cost_center_1 = db.Column(db.String(100))
    cost_center_2 = db.Column(db.String(100))

    # monthly / quarterly / yearly / once
    recurrence = db.Column(db.String(20), default="monthly")
    billing_day = db.Column(db.Integer)
    is_active = db.Column(db.Boolean, default=True)
    note = db.Column(db.Text)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    position = db.relationship("ContractPosition", back_populates="versions")

    def __repr__(self):
        return f"<ContractPositionVersion {self.position_id} {self.valid_from}>"
