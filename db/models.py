from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime

Base = declarative_base()


class Patient(Base):
    __tablename__ = "patients"
    id = Column(Integer, primary_key=True)
    nhs_number = Column(String(10), unique=True, nullable=False)
    first_name = Column(String(100))
    last_name = Column(String(100))
    date_of_birth = Column(String(20))
    phone = Column(String(20))
    email = Column(String(200))
    created_at = Column(DateTime, default=datetime.utcnow)
    prescriptions = relationship("Prescription", back_populates="patient")


class Medication(Base):
    __tablename__ = "medications"
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    generic_name = Column(String(200))
    category = Column(String(100))
    unit = Column(String(50))
    interactions = Column(Text, default="")


class StockItem(Base):
    __tablename__ = "stock_items"
    id = Column(Integer, primary_key=True)
    medication_id = Column(Integer, ForeignKey("medications.id"))
    quantity = Column(Integer, default=0)
    reorder_threshold = Column(Integer, default=50)
    reorder_quantity = Column(Integer, default=200)
    expiry_date = Column(String(20))
    supplier = Column(String(200))
    unit_cost = Column(Float, default=0.0)
    medication = relationship("Medication")


class Prescription(Base):
    __tablename__ = "prescriptions"
    id = Column(Integer, primary_key=True)
    patient_id = Column(Integer, ForeignKey("patients.id"))
    medication_id = Column(Integer, ForeignKey("medications.id"))
    dosage = Column(String(100))
    frequency = Column(String(100))
    prescriber = Column(String(200))
    issue_date = Column(String(20))
    next_due_date = Column(String(20))
    active = Column(Boolean, default=True)
    patient = relationship("Patient", back_populates="prescriptions")
    medication = relationship("Medication")


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    agent = Column(String(100))
    action = Column(String(200))
    details = Column(Text)
    patient_id = Column(Integer, nullable=True)