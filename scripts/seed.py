"""
Seed script — populates PharmAgent database with realistic Scottish pharmacy data.
Run: python scripts/seed.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.database import SessionLocal, init_db
from db.models import Patient, Medication, StockItem, Prescription
from datetime import datetime, timedelta


def seed():
    init_db()
    db = SessionLocal()

    # Clear existing data
    db.query(Prescription).delete()
    db.query(StockItem).delete()
    db.query(Patient).delete()
    db.query(Medication).delete()
    db.commit()

    # --- Medications with known interactions ---
    medications = [
        Medication(name="Warfarin 5mg", generic_name="warfarin", category="Anticoagulant",
                   unit="tablets", interactions="aspirin,ibuprofen,naproxen"),
        Medication(name="Aspirin 75mg", generic_name="aspirin", category="Antiplatelet",
                   unit="tablets", interactions="warfarin,ibuprofen,clopidogrel"),
        Medication(name="Metformin 500mg", generic_name="metformin", category="Antidiabetic",
                   unit="tablets", interactions="contrast_dye"),
        Medication(name="Lisinopril 10mg", generic_name="lisinopril", category="ACE Inhibitor",
                   unit="tablets", interactions="potassium,spironolactone"),
        Medication(name="Atorvastatin 20mg", generic_name="atorvastatin", category="Statin",
                   unit="tablets", interactions="clarithromycin,erythromycin"),
        Medication(name="Amoxicillin 500mg", generic_name="amoxicillin", category="Antibiotic",
                   unit="capsules", interactions="methotrexate"),
        Medication(name="Omeprazole 20mg", generic_name="omeprazole", category="PPI",
                   unit="capsules", interactions="clopidogrel"),
        Medication(name="Ibuprofen 400mg", generic_name="ibuprofen", category="NSAID",
                   unit="tablets", interactions="warfarin,aspirin,lisinopril"),
        Medication(name="Amlodipine 5mg", generic_name="amlodipine", category="Calcium Channel Blocker",
                   unit="tablets", interactions="simvastatin"),
        Medication(name="Sertraline 50mg", generic_name="sertraline", category="SSRI",
                   unit="tablets", interactions="tramadol,linezolid,monoamine_oxidase_inhibitors"),
        Medication(name="Salbutamol Inhaler", generic_name="salbutamol", category="Bronchodilator",
                   unit="inhaler", interactions=""),
        Medication(name="Levothyroxine 50mcg", generic_name="levothyroxine", category="Thyroid Hormone",
                   unit="tablets", interactions="calcium,iron,antacids"),
        Medication(name="Clopidogrel 75mg", generic_name="clopidogrel", category="Antiplatelet",
                   unit="tablets", interactions="aspirin,omeprazole,warfarin"),
        Medication(name="Spironolactone 25mg", generic_name="spironolactone", category="Diuretic",
                   unit="tablets", interactions="lisinopril,potassium"),
        Medication(name="Clarithromycin 500mg", generic_name="clarithromycin", category="Antibiotic",
                   unit="tablets", interactions="atorvastatin,simvastatin,warfarin"),
    ]
    db.add_all(medications)
    db.commit()

    # --- Patients ---
    patients_data = [
        ("4823719056", "Margaret", "Campbell",  "1948-03-12", "07700900001", "m.campbell@email.co.uk"),
        ("3917284650", "James",    "Morrison",  "1955-07-24", "07700900002", "j.morrison@email.co.uk"),
        ("6012847391", "Patricia", "Henderson", "1962-11-08", "07700900003", "p.henderson@email.co.uk"),
        ("7384920156", "Robert",   "MacLeod",   "1971-04-30", "07700900004", "r.macleod@email.co.uk"),
        ("2847563019", "Susan",    "Graham",    "1958-09-15", "07700900005", "s.graham@email.co.uk"),
        ("5019283746", "William",  "Stevenson", "1943-12-03", "07700900006", "w.stevenson@email.co.uk"),
        ("8374650192", "Dorothy",  "Reid",      "1967-02-19", "07700900007", "d.reid@email.co.uk"),
        ("1092837465", "George",   "Fraser",    "1980-06-27", "07700900008", "g.fraser@email.co.uk"),
        ("9283746501", "Helen",    "Murray",    "1953-08-11", "07700900009", "h.murray@email.co.uk"),
        ("4756019283", "Thomas",   "Robertson", "1938-01-22", "07700900010", "t.robertson@email.co.uk"),
    ]
    patients = []
    for nhs, fn, ln, dob, phone, email in patients_data:
        p = Patient(nhs_number=nhs, first_name=fn, last_name=ln,
                    date_of_birth=dob, phone=phone, email=email)
        db.add(p)
        patients.append(p)
    db.commit()

    # --- Prescriptions (some with deliberate interaction risks) ---
    today = datetime.today()
    med = {m.generic_name: m for m in medications}

    prescriptions = [
        # Margaret — Warfarin + Aspirin (INTERACTION RISK)
        Prescription(patient=patients[0], medication=med["warfarin"], dosage="5mg daily",
                     frequency="Once daily", prescriber="Dr A. MacKenzie",
                     issue_date=(today - timedelta(days=60)).strftime("%Y-%m-%d"),
                     next_due_date=(today + timedelta(days=5)).strftime("%Y-%m-%d"), active=True),
        Prescription(patient=patients[0], medication=med["aspirin"], dosage="75mg daily",
                     frequency="Once daily", prescriber="Dr A. MacKenzie",
                     issue_date=(today - timedelta(days=30)).strftime("%Y-%m-%d"),
                     next_due_date=(today + timedelta(days=2)).strftime("%Y-%m-%d"), active=True),

        # James — Atorvastatin + Clarithromycin (INTERACTION RISK)
        Prescription(patient=patients[1], medication=med["atorvastatin"], dosage="20mg nightly",
                     frequency="Once daily at night", prescriber="Dr B. Thomson",
                     issue_date=(today - timedelta(days=90)).strftime("%Y-%m-%d"),
                     next_due_date=(today + timedelta(days=10)).strftime("%Y-%m-%d"), active=True),
        Prescription(patient=patients[1], medication=med["clarithromycin"], dosage="500mg twice daily",
                     frequency="Twice daily", prescriber="Dr B. Thomson",
                     issue_date=(today - timedelta(days=3)).strftime("%Y-%m-%d"),
                     next_due_date=(today + timedelta(days=4)).strftime("%Y-%m-%d"), active=True),

        # Patricia — Lisinopril + Spironolactone (INTERACTION RISK)
        Prescription(patient=patients[2], medication=med["lisinopril"], dosage="10mg daily",
                     frequency="Once daily", prescriber="Dr C. Wilson",
                     issue_date=(today - timedelta(days=120)).strftime("%Y-%m-%d"),
                     next_due_date=(today + timedelta(days=7)).strftime("%Y-%m-%d"), active=True),
        Prescription(patient=patients[2], medication=med["spironolactone"], dosage="25mg daily",
                     frequency="Once daily", prescriber="Dr C. Wilson",
                     issue_date=(today - timedelta(days=14)).strftime("%Y-%m-%d"),
                     next_due_date=(today + timedelta(days=7)).strftime("%Y-%m-%d"), active=True),

        # Robert — Metformin (safe)
        Prescription(patient=patients[3], medication=med["metformin"], dosage="500mg twice daily",
                     frequency="Twice daily with meals", prescriber="Dr D. Scott",
                     issue_date=(today - timedelta(days=45)).strftime("%Y-%m-%d"),
                     next_due_date=(today + timedelta(days=15)).strftime("%Y-%m-%d"), active=True),

        # Susan — Sertraline (due soon)
        Prescription(patient=patients[4], medication=med["sertraline"], dosage="50mg daily",
                     frequency="Once daily in the morning", prescriber="Dr E. Hamilton",
                     issue_date=(today - timedelta(days=55)).strftime("%Y-%m-%d"),
                     next_due_date=(today + timedelta(days=3)).strftime("%Y-%m-%d"), active=True),

        # William — Levothyroxine
        Prescription(patient=patients[5], medication=med["levothyroxine"], dosage="50mcg daily",
                     frequency="Once daily, 30 min before food", prescriber="Dr F. Paterson",
                     issue_date=(today - timedelta(days=80)).strftime("%Y-%m-%d"),
                     next_due_date=(today + timedelta(days=12)).strftime("%Y-%m-%d"), active=True),

        # Dorothy — Amlodipine
        Prescription(patient=patients[6], medication=med["amlodipine"], dosage="5mg daily",
                     frequency="Once daily", prescriber="Dr G. Bell",
                     issue_date=(today - timedelta(days=70)).strftime("%Y-%m-%d"),
                     next_due_date=(today + timedelta(days=8)).strftime("%Y-%m-%d"), active=True),

        # George — Omeprazole + Clopidogrel (INTERACTION RISK)
        Prescription(patient=patients[7], medication=med["omeprazole"], dosage="20mg daily",
                     frequency="Once daily before food", prescriber="Dr H. Young",
                     issue_date=(today - timedelta(days=20)).strftime("%Y-%m-%d"),
                     next_due_date=(today + timedelta(days=10)).strftime("%Y-%m-%d"), active=True),
        Prescription(patient=patients[7], medication=med["clopidogrel"], dosage="75mg daily",
                     frequency="Once daily", prescriber="Dr H. Young",
                     issue_date=(today - timedelta(days=50)).strftime("%Y-%m-%d"),
                     next_due_date=(today + timedelta(days=10)).strftime("%Y-%m-%d"), active=True),

        # Helen — Salbutamol
        Prescription(patient=patients[8], medication=med["salbutamol"], dosage="100mcg as needed",
                     frequency="PRN (as required)", prescriber="Dr I. Black",
                     issue_date=(today - timedelta(days=100)).strftime("%Y-%m-%d"),
                     next_due_date=(today + timedelta(days=20)).strftime("%Y-%m-%d"), active=True),

        # Thomas — Warfarin + Ibuprofen (CRITICAL INTERACTION)
        Prescription(patient=patients[9], medication=med["warfarin"], dosage="5mg daily",
                     frequency="Once daily", prescriber="Dr J. Duncan",
                     issue_date=(today - timedelta(days=150)).strftime("%Y-%m-%d"),
                     next_due_date=(today + timedelta(days=1)).strftime("%Y-%m-%d"), active=True),
        Prescription(patient=patients[9], medication=med["ibuprofen"], dosage="400mg three times daily",
                     frequency="Three times daily with food", prescriber="Dr J. Duncan",
                     issue_date=(today - timedelta(days=5)).strftime("%Y-%m-%d"),
                     next_due_date=(today + timedelta(days=2)).strftime("%Y-%m-%d"), active=True),
    ]
    db.add_all(prescriptions)
    db.commit()

    # --- Stock (some low, some expiring soon) ---
    stock_items = [
        StockItem(medication=med["warfarin"],      quantity=240, reorder_threshold=100, reorder_quantity=500, expiry_date=(today + timedelta(days=365)).strftime("%Y-%m-%d"), supplier="Phoenix Healthcare",  unit_cost=0.12),
        StockItem(medication=med["aspirin"],        quantity=18,  reorder_threshold=100, reorder_quantity=500, expiry_date=(today + timedelta(days=400)).strftime("%Y-%m-%d"), supplier="AAH Pharmaceuticals", unit_cost=0.04),
        StockItem(medication=med["metformin"],      quantity=320, reorder_threshold=100, reorder_quantity=500, expiry_date=(today + timedelta(days=20)).strftime("%Y-%m-%d"),  supplier="Colorcon",            unit_cost=0.08),
        StockItem(medication=med["lisinopril"],     quantity=90,  reorder_threshold=80,  reorder_quantity=300, expiry_date=(today + timedelta(days=300)).strftime("%Y-%m-%d"), supplier="Phoenix Healthcare",  unit_cost=0.10),
        StockItem(medication=med["atorvastatin"],   quantity=55,  reorder_threshold=80,  reorder_quantity=300, expiry_date=(today + timedelta(days=250)).strftime("%Y-%m-%d"), supplier="AAH Pharmaceuticals", unit_cost=0.15),
        StockItem(medication=med["amoxicillin"],    quantity=12,  reorder_threshold=60,  reorder_quantity=200, expiry_date=(today + timedelta(days=180)).strftime("%Y-%m-%d"), supplier="Unichem",             unit_cost=0.22),
        StockItem(medication=med["omeprazole"],     quantity=200, reorder_threshold=80,  reorder_quantity=300, expiry_date=(today + timedelta(days=14)).strftime("%Y-%m-%d"),  supplier="Phoenix Healthcare",  unit_cost=0.18),
        StockItem(medication=med["ibuprofen"],      quantity=145, reorder_threshold=100, reorder_quantity=500, expiry_date=(today + timedelta(days=500)).strftime("%Y-%m-%d"), supplier="AAH Pharmaceuticals", unit_cost=0.05),
        StockItem(medication=med["amlodipine"],     quantity=180, reorder_threshold=80,  reorder_quantity=300, expiry_date=(today + timedelta(days=400)).strftime("%Y-%m-%d"), supplier="Colorcon",            unit_cost=0.09),
        StockItem(medication=med["sertraline"],     quantity=95,  reorder_threshold=80,  reorder_quantity=300, expiry_date=(today + timedelta(days=350)).strftime("%Y-%m-%d"), supplier="Unichem",             unit_cost=0.20),
        StockItem(medication=med["salbutamol"],     quantity=30,  reorder_threshold=40,  reorder_quantity=150, expiry_date=(today + timedelta(days=200)).strftime("%Y-%m-%d"), supplier="Phoenix Healthcare",  unit_cost=3.50),
        StockItem(medication=med["levothyroxine"],  quantity=280, reorder_threshold=80,  reorder_quantity=300, expiry_date=(today + timedelta(days=380)).strftime("%Y-%m-%d"), supplier="AAH Pharmaceuticals", unit_cost=0.11),
        StockItem(medication=med["clopidogrel"],    quantity=160, reorder_threshold=80,  reorder_quantity=300, expiry_date=(today + timedelta(days=290)).strftime("%Y-%m-%d"), supplier="Colorcon",            unit_cost=0.35),
        StockItem(medication=med["spironolactone"], quantity=70,  reorder_threshold=60,  reorder_quantity=200, expiry_date=(today + timedelta(days=25)).strftime("%Y-%m-%d"),  supplier="Unichem",             unit_cost=0.14),
        StockItem(medication=med["clarithromycin"], quantity=45,  reorder_threshold=60,  reorder_quantity=200, expiry_date=(today + timedelta(days=150)).strftime("%Y-%m-%d"), supplier="Phoenix Healthcare",  unit_cost=0.45),
    ]
    db.add_all(stock_items)
    db.commit()
    db.close()

    print("✅ Seed complete:")
    print(f"   {len(patients_data)} patients")
    print(f"   {len(medications)} medications")
    print(f"   {len(prescriptions)} prescriptions (4 interaction risks seeded)")
    print(f"   {len(stock_items)} stock items (4 low stock, 3 expiring soon)")


if __name__ == "__main__":
    seed()