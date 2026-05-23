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
                   unit="tablets", interactions="aspirin,ibuprofen,naproxen,clarithromycin,amiodarone"),
        Medication(name="Aspirin 75mg", generic_name="aspirin", category="Antiplatelet",
                   unit="tablets", interactions="warfarin,ibuprofen,clopidogrel,naproxen"),
        Medication(name="Metformin 500mg", generic_name="metformin", category="Antidiabetic",
                   unit="tablets", interactions="contrast_dye,alcohol"),
        Medication(name="Lisinopril 10mg", generic_name="lisinopril", category="ACE Inhibitor",
                   unit="tablets", interactions="potassium,spironolactone,ibuprofen,naproxen"),
        Medication(name="Atorvastatin 20mg", generic_name="atorvastatin", category="Statin",
                   unit="tablets", interactions="clarithromycin,erythromycin,amiodarone"),
        Medication(name="Amoxicillin 500mg", generic_name="amoxicillin", category="Antibiotic",
                   unit="capsules", interactions="methotrexate"),
        Medication(name="Omeprazole 20mg", generic_name="omeprazole", category="PPI",
                   unit="capsules", interactions="clopidogrel,sertraline"),
        Medication(name="Ibuprofen 400mg", generic_name="ibuprofen", category="NSAID",
                   unit="tablets", interactions="warfarin,aspirin,lisinopril,prednisolone"),
        Medication(name="Amlodipine 5mg", generic_name="amlodipine", category="Calcium Channel Blocker",
                   unit="tablets", interactions="simvastatin"),
        Medication(name="Sertraline 50mg", generic_name="sertraline", category="SSRI",
                   unit="tablets", interactions="tramadol,linezolid,monoamine_oxidase_inhibitors,amitriptyline"),
        Medication(name="Salbutamol Inhaler", generic_name="salbutamol", category="Bronchodilator",
                   unit="inhaler", interactions="propranolol,atenolol"),
        Medication(name="Levothyroxine 50mcg", generic_name="levothyroxine", category="Thyroid Hormone",
                   unit="tablets", interactions="calcium,iron,antacids,sertraline"),
        Medication(name="Clopidogrel 75mg", generic_name="clopidogrel", category="Antiplatelet",
                   unit="tablets", interactions="aspirin,omeprazole,warfarin"),
        Medication(name="Spironolactone 25mg", generic_name="spironolactone", category="Diuretic",
                   unit="tablets", interactions="lisinopril,potassium,ramipril"),
        Medication(name="Clarithromycin 500mg", generic_name="clarithromycin", category="Antibiotic",
                   unit="tablets", interactions="atorvastatin,simvastatin,warfarin,digoxin"),
        Medication(name="Digoxin 125mcg", generic_name="digoxin", category="Cardiac Glycoside",
                   unit="tablets", interactions="amiodarone,clarithromycin,furosemide,spironolactone"),
        Medication(name="Furosemide 40mg", generic_name="furosemide", category="Loop Diuretic",
                   unit="tablets", interactions="digoxin,lithium,gentamicin"),
        Medication(name="Prednisolone 5mg", generic_name="prednisolone", category="Corticosteroid",
                   unit="tablets", interactions="ibuprofen,naproxen,aspirin,warfarin"),
        Medication(name="Bisoprolol 2.5mg", generic_name="bisoprolol", category="Beta Blocker",
                   unit="tablets", interactions="verapamil,diltiazem,salbutamol"),
        Medication(name="Beclometasone Inhaler", generic_name="beclometasone", category="Inhaled Corticosteroid",
                   unit="inhaler", interactions=""),
        Medication(name="Montelukast 10mg", generic_name="montelukast", category="Leukotriene Antagonist",
                   unit="tablets", interactions=""),
        Medication(name="Alendronic Acid 70mg", generic_name="alendronate", category="Bisphosphonate",
                   unit="tablets", interactions="calcium,antacids,iron"),
        Medication(name="Calcium + Vit D", generic_name="calcium_vitd", category="Supplement",
                   unit="tablets", interactions="alendronate,levothyroxine,iron"),
        Medication(name="Amiodarone 200mg", generic_name="amiodarone", category="Antiarrhythmic",
                   unit="tablets", interactions="warfarin,digoxin,atorvastatin,simvastatin"),
        Medication(name="Ramipril 5mg", generic_name="ramipril", category="ACE Inhibitor",
                   unit="tablets", interactions="potassium,spironolactone,ibuprofen"),
    ]
    db.add_all(medications)
    db.commit()

    # --- Patients ---
    patients_data = [
        # Original patient
        ("1203480016", "Margaret",  "Campbell",   "1948-03-12", "07700900001", "m.campbell@email.co.uk"),
        # New patients
        ("2407550013", "James",     "Morrison",   "1955-07-24", "07700900002", "j.morrison@email.co.uk"),
        ("0811620018", "Patricia",  "Henderson",  "1962-11-08", "07700900003", "p.henderson@email.co.uk"),
        ("3004710013", "Robert",    "MacLeod",    "1971-04-30", "07700900004", "r.macleod@email.co.uk"),
        ("1509580018", "Susan",     "Graham",     "1958-09-15", "07700900005", "s.graham@email.co.uk"),
        ("0312430019", "William",   "Stevenson",  "1943-12-03", "07700900006", "w.stevenson@email.co.uk"),
        ("1902670019", "Dorothy",   "Reid",       "1967-02-19", "07700900007", "d.reid@email.co.uk"),
        ("2706800011", "George",    "Fraser",     "1980-06-27", "07700900008", "g.fraser@email.co.uk"),
        ("1108530028", "Helen",     "Murray",     "1953-08-11", "07700900009", "h.murray@email.co.uk"),
        ("2201380015", "Thomas",    "Robertson",  "1938-01-22", "07700900010", "t.robertson@email.co.uk"),
    ]
    patients = []
    for nhs, fn, ln, dob, phone, email in patients_data:
        p = Patient(nhs_number=nhs, first_name=fn, last_name=ln,
                    date_of_birth=dob, phone=phone, email=email)
        db.add(p)
        patients.append(p)
    db.commit()

    # --- Prescriptions ---
    today = datetime.today()
    med = {m.generic_name: m for m in medications}

    prescriptions = [
        # ── Margaret Campbell (4823719056) ──────────────────────────────────────
        # ON: Warfarin + Aspirin
        # TEST: Ibuprofen → HIGH (GI bleed, triple hit)
        # TEST: Naproxen  → HIGH (same risk)
        # TEST: Amiodarone → HIGH (raises Warfarin levels)
        # TEST: Paracetamol → LOW (safe)
        Prescription(patient=patients[0], medication=med["warfarin"], dosage="5mg daily",
                     frequency="Once daily", prescriber="Dr A. MacKenzie",
                     issue_date=(today - timedelta(days=60)).strftime("%Y-%m-%d"),
                     next_due_date=(today + timedelta(days=5)).strftime("%Y-%m-%d"), active=True),
        Prescription(patient=patients[0], medication=med["aspirin"], dosage="75mg daily",
                     frequency="Once daily", prescriber="Dr A. MacKenzie",
                     issue_date=(today - timedelta(days=30)).strftime("%Y-%m-%d"),
                     next_due_date=(today + timedelta(days=2)).strftime("%Y-%m-%d"), active=True),

        # ── James Morrison (3917284650) ─────────────────────────────────────────
        # ON: Atorvastatin + Clarithromycin
        # TEST: Amiodarone → HIGH (statin toxicity + QT prolongation)
        # TEST: Warfarin   → MODERATE (clarithromycin raises Warfarin)
        # TEST: Ibuprofen  → LOW (no direct statin interaction)
        Prescription(patient=patients[1], medication=med["atorvastatin"], dosage="20mg nightly",
                     frequency="Once daily at night", prescriber="Dr B. Thomson",
                     issue_date=(today - timedelta(days=90)).strftime("%Y-%m-%d"),
                     next_due_date=(today + timedelta(days=10)).strftime("%Y-%m-%d"), active=True),
        Prescription(patient=patients[1], medication=med["clarithromycin"], dosage="500mg twice daily",
                     frequency="Twice daily", prescriber="Dr B. Thomson",
                     issue_date=(today - timedelta(days=3)).strftime("%Y-%m-%d"),
                     next_due_date=(today + timedelta(days=4)).strftime("%Y-%m-%d"), active=True),

        # ── Patricia Henderson (6012847391) ─────────────────────────────────────
        # ON: Lisinopril + Spironolactone
        # TEST: Ibuprofen  → HIGH (reduces ACE inhibitor effect + renal risk)
        # TEST: Ramipril   → HIGH (double ACE inhibitor + hyperkalemia)
        # TEST: Paracetamol → SAFE
        Prescription(patient=patients[2], medication=med["lisinopril"], dosage="10mg daily",
                     frequency="Once daily", prescriber="Dr C. Wilson",
                     issue_date=(today - timedelta(days=120)).strftime("%Y-%m-%d"),
                     next_due_date=(today + timedelta(days=7)).strftime("%Y-%m-%d"), active=True),
        Prescription(patient=patients[2], medication=med["spironolactone"], dosage="25mg daily",
                     frequency="Once daily", prescriber="Dr C. Wilson",
                     issue_date=(today - timedelta(days=14)).strftime("%Y-%m-%d"),
                     next_due_date=(today + timedelta(days=7)).strftime("%Y-%m-%d"), active=True),

        # ── Robert MacLeod (7384920156) ─────────────────────────────────────────
        # ON: Metformin (diabetes, otherwise healthy)
        # TEST: Ibuprofen     → MODERATE (renal clearance concern)
        # TEST: Clarithromycin → LOW (no direct interaction)
        # TEST: Paracetamol   → SAFE
        Prescription(patient=patients[3], medication=med["metformin"], dosage="500mg twice daily",
                     frequency="Twice daily with meals", prescriber="Dr D. Scott",
                     issue_date=(today - timedelta(days=45)).strftime("%Y-%m-%d"),
                     next_due_date=(today + timedelta(days=15)).strftime("%Y-%m-%d"), active=True),

        # ── Susan Graham (2847563019) ────────────────────────────────────────────
        # ON: Sertraline (depression)
        # TEST: Tramadol      → HIGH (serotonin syndrome)
        # TEST: Amitriptyline → HIGH (serotonin syndrome + CNS depression)
        # TEST: Omeprazole    → MODERATE (mild CYP2C19 interaction)
        # TEST: Paracetamol   → SAFE
        Prescription(patient=patients[4], medication=med["sertraline"], dosage="50mg daily",
                     frequency="Once daily in the morning", prescriber="Dr E. Hamilton",
                     issue_date=(today - timedelta(days=55)).strftime("%Y-%m-%d"),
                     next_due_date=(today + timedelta(days=3)).strftime("%Y-%m-%d"), active=True),

        # ── William Stevenson (5019283746) ──────────────────────────────────────
        # ON: Digoxin + Furosemide + Bisoprolol + Amiodarone (heart failure, elderly 81)
        # TEST: Clarithromycin → HIGH (raises Digoxin to toxic levels)
        # TEST: Spironolactone → MODERATE (potassium imbalance with Furosemide)
        # TEST: Ibuprofen      → HIGH (worsens heart failure, fluid retention)
        # TEST: Paracetamol    → SAFE
        Prescription(patient=patients[5], medication=med["digoxin"], dosage="125mcg daily",
                     frequency="Once daily", prescriber="Dr F. Paterson",
                     issue_date=(today - timedelta(days=180)).strftime("%Y-%m-%d"),
                     next_due_date=(today + timedelta(days=3)).strftime("%Y-%m-%d"), active=True),
        Prescription(patient=patients[5], medication=med["furosemide"], dosage="40mg daily",
                     frequency="Once daily in the morning", prescriber="Dr F. Paterson",
                     issue_date=(today - timedelta(days=180)).strftime("%Y-%m-%d"),
                     next_due_date=(today + timedelta(days=3)).strftime("%Y-%m-%d"), active=True),
        Prescription(patient=patients[5], medication=med["bisoprolol"], dosage="2.5mg daily",
                     frequency="Once daily", prescriber="Dr F. Paterson",
                     issue_date=(today - timedelta(days=90)).strftime("%Y-%m-%d"),
                     next_due_date=(today + timedelta(days=10)).strftime("%Y-%m-%d"), active=True),
        Prescription(patient=patients[5], medication=med["amiodarone"], dosage="200mg daily",
                     frequency="Once daily", prescriber="Dr F. Paterson",
                     issue_date=(today - timedelta(days=60)).strftime("%Y-%m-%d"),
                     next_due_date=(today + timedelta(days=8)).strftime("%Y-%m-%d"), active=True),

        # ── Dorothy Reid (8374650192) ────────────────────────────────────────────
        # ON: Prednisolone + Alendronic Acid + Calcium + Vit D (long-term steroids)
        # TEST: Ibuprofen  → HIGH (doubled GI bleed risk with Prednisolone)
        # TEST: Aspirin    → HIGH (GI bleed risk with Prednisolone)
        # TEST: Warfarin   → MODERATE (steroids can affect INR)
        # TEST: Paracetamol → SAFE
        Prescription(patient=patients[6], medication=med["prednisolone"], dosage="5mg daily",
                     frequency="Once daily with food", prescriber="Dr G. Bell",
                     issue_date=(today - timedelta(days=200)).strftime("%Y-%m-%d"),
                     next_due_date=(today + timedelta(days=8)).strftime("%Y-%m-%d"), active=True),
        Prescription(patient=patients[6], medication=med["alendronate"], dosage="70mg weekly",
                     frequency="Once weekly", prescriber="Dr G. Bell",
                     issue_date=(today - timedelta(days=200)).strftime("%Y-%m-%d"),
                     next_due_date=(today + timedelta(days=5)).strftime("%Y-%m-%d"), active=True),
        Prescription(patient=patients[6], medication=med["calcium_vitd"], dosage="1 tablet daily",
                     frequency="Once daily", prescriber="Dr G. Bell",
                     issue_date=(today - timedelta(days=200)).strftime("%Y-%m-%d"),
                     next_due_date=(today + timedelta(days=8)).strftime("%Y-%m-%d"), active=True),

        # ── George Fraser (1092837465) ───────────────────────────────────────────
        # ON: Omeprazole + Clopidogrel (post-stent)
        # TEST: Aspirin    → MODERATE (triple antithrombotic risk)
        # TEST: Ibuprofen  → HIGH (GI bleed + antiplatelet interaction)
        # TEST: Warfarin   → HIGH (clopidogrel + warfarin = major bleed risk)
        # TEST: Paracetamol → SAFE
        Prescription(patient=patients[7], medication=med["omeprazole"], dosage="20mg daily",
                     frequency="Once daily before food", prescriber="Dr H. Young",
                     issue_date=(today - timedelta(days=20)).strftime("%Y-%m-%d"),
                     next_due_date=(today + timedelta(days=10)).strftime("%Y-%m-%d"), active=True),
        Prescription(patient=patients[7], medication=med["clopidogrel"], dosage="75mg daily",
                     frequency="Once daily", prescriber="Dr H. Young",
                     issue_date=(today - timedelta(days=50)).strftime("%Y-%m-%d"),
                     next_due_date=(today + timedelta(days=10)).strftime("%Y-%m-%d"), active=True),

        # ── Helen Murray (9283746501) ────────────────────────────────────────────
        # ON: Salbutamol + Beclometasone + Montelukast (asthma)
        # TEST: Propranolol  → HIGH (beta-blocker blocks Salbutamol, triggers bronchospasm)
        # TEST: Ibuprofen    → HIGH (NSAID-exacerbated asthma)
        # TEST: Aspirin      → MODERATE (can trigger asthma in sensitive patients)
        # TEST: Amoxicillin  → SAFE (common antibiotic, no asthma interaction)
        Prescription(patient=patients[8], medication=med["salbutamol"], dosage="100mcg as needed",
                     frequency="PRN (as required)", prescriber="Dr I. Black",
                     issue_date=(today - timedelta(days=100)).strftime("%Y-%m-%d"),
                     next_due_date=(today + timedelta(days=20)).strftime("%Y-%m-%d"), active=True),
        Prescription(patient=patients[8], medication=med["beclometasone"], dosage="200mcg twice daily",
                     frequency="Twice daily", prescriber="Dr I. Black",
                     issue_date=(today - timedelta(days=100)).strftime("%Y-%m-%d"),
                     next_due_date=(today + timedelta(days=20)).strftime("%Y-%m-%d"), active=True),
        Prescription(patient=patients[8], medication=med["montelukast"], dosage="10mg nightly",
                     frequency="Once daily at night", prescriber="Dr I. Black",
                     issue_date=(today - timedelta(days=100)).strftime("%Y-%m-%d"),
                     next_due_date=(today + timedelta(days=20)).strftime("%Y-%m-%d"), active=True),

        # ── Thomas Robertson (4756019283) ───────────────────────────────────────
        # ON: Warfarin + Ibuprofen (CRITICAL — already prescribed together!)
        # TEST: Aspirin      → CRITICAL (triple bleeding risk)
        # TEST: Clopidogrel  → CRITICAL (triple antithrombotic)
        # TEST: Amiodarone   → HIGH (raises Warfarin INR significantly)
        # TEST: Paracetamol  → MODERATE (high doses can raise INR slightly)
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
        StockItem(medication=med["digoxin"],        quantity=22,  reorder_threshold=50,  reorder_quantity=200, expiry_date=(today + timedelta(days=310)).strftime("%Y-%m-%d"), supplier="AAH Pharmaceuticals", unit_cost=0.28),
        StockItem(medication=med["furosemide"],     quantity=110, reorder_threshold=80,  reorder_quantity=300, expiry_date=(today + timedelta(days=270)).strftime("%Y-%m-%d"), supplier="Unichem",             unit_cost=0.07),
        StockItem(medication=med["prednisolone"],   quantity=85,  reorder_threshold=80,  reorder_quantity=300, expiry_date=(today + timedelta(days=18)).strftime("%Y-%m-%d"),  supplier="Phoenix Healthcare",  unit_cost=0.06),
        StockItem(medication=med["bisoprolol"],     quantity=190, reorder_threshold=80,  reorder_quantity=300, expiry_date=(today + timedelta(days=420)).strftime("%Y-%m-%d"), supplier="Colorcon",            unit_cost=0.13),
        StockItem(medication=med["beclometasone"],  quantity=14,  reorder_threshold=30,  reorder_quantity=100, expiry_date=(today + timedelta(days=240)).strftime("%Y-%m-%d"), supplier="AAH Pharmaceuticals", unit_cost=4.20),
        StockItem(medication=med["montelukast"],    quantity=135, reorder_threshold=60,  reorder_quantity=200, expiry_date=(today + timedelta(days=330)).strftime("%Y-%m-%d"), supplier="Unichem",             unit_cost=0.32),
        StockItem(medication=med["alendronate"],    quantity=60,  reorder_threshold=40,  reorder_quantity=150, expiry_date=(today + timedelta(days=360)).strftime("%Y-%m-%d"), supplier="Phoenix Healthcare",  unit_cost=0.25),
        StockItem(medication=med["calcium_vitd"],   quantity=175, reorder_threshold=80,  reorder_quantity=300, expiry_date=(today + timedelta(days=410)).strftime("%Y-%m-%d"), supplier="Colorcon",            unit_cost=0.09),
        StockItem(medication=med["amiodarone"],     quantity=40,  reorder_threshold=50,  reorder_quantity=150, expiry_date=(today + timedelta(days=280)).strftime("%Y-%m-%d"), supplier="AAH Pharmaceuticals", unit_cost=0.55),
        StockItem(medication=med["furosemide"],     quantity=95,  reorder_threshold=80,  reorder_quantity=300, expiry_date=(today + timedelta(days=45)).strftime("%Y-%m-%d"),  supplier="Unichem",             unit_cost=0.07),
        StockItem(medication=med["bisoprolol"],     quantity=110, reorder_threshold=80,  reorder_quantity=300, expiry_date=(today + timedelta(days=52)).strftime("%Y-%m-%d"),  supplier="Colorcon",            unit_cost=0.13),
        StockItem(medication=med["montelukast"],    quantity=60,  reorder_threshold=60,  reorder_quantity=200, expiry_date=(today + timedelta(days=58)).strftime("%Y-%m-%d"),  supplier="Unichem",             unit_cost=0.32),
        StockItem(medication=med["levothyroxine"],  quantity=75,  reorder_threshold=80,  reorder_quantity=300, expiry_date=(today + timedelta(days=63)).strftime("%Y-%m-%d"),  supplier="AAH Pharmaceuticals", unit_cost=0.11),
        StockItem(medication=med["ramipril"],       quantity=8,   reorder_threshold=60,  reorder_quantity=200, expiry_date=(today + timedelta(days=340)).strftime("%Y-%m-%d"), supplier="Unichem",             unit_cost=0.12),
    ]
    db.add_all(stock_items)
    db.commit()
    db.close()

    print("✅ Seed complete:")
    print(f"   {len(patients_data)} patients")
    print(f"   {len(medications)} medications")
    print(f"   {len(prescriptions)} prescriptions")
    print(f"   {len(stock_items)} stock items")
    print()
    print("Test scenarios:")
    print("  1203480016  Margaret Campbell   — Warfarin + Aspirin   → try: Ibuprofen, Amiodarone, Paracetamol")
    print("  2407550013  James Morrison      — Atorvastatin + Clarithromycin → try: Amiodarone, Warfarin")
    print("  0811620018  Patricia Henderson  — Lisinopril + Spironolactone   → try: Ibuprofen, Ramipril")
    print("  3004710013  Robert MacLeod      — Metformin only        → try: Ibuprofen, Paracetamol")
    print("  1509580018  Susan Graham        — Sertraline            → try: Tramadol, Amitriptyline")
    print("  0312430019  William Stevenson   — Digoxin + Furosemide + Bisoprolol + Amiodarone → try: Clarithromycin, Ibuprofen")
    print("  1902670019  Dorothy Reid        — Prednisolone + Alendronate   → try: Ibuprofen, Aspirin")
    print("  2706800011  George Fraser       — Omeprazole + Clopidogrel     → try: Warfarin, Ibuprofen")
    print("  1108530028  Helen Murray        — Salbutamol + Beclometasone   → try: Propranolol, Ibuprofen")
    print("  2201380015  Thomas Robertson    — Warfarin + Ibuprofen (!)     → try: Aspirin, Amiodarone")


if __name__ == "__main__":
    seed()