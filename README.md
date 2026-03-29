# Backup Validation Project
**SQL Server On‑Prem → AWS S3 → RDS PostgreSQL Validation Pipeline**

## 📌 Overview
This project implements a complete validation pipeline to ensure that all SQL Server on‑premises backups (FULL, DIFF, LOG) are delivered to AWS S3 and properly reconciled in Amazon RDS PostgreSQL. The solution provides end‑to‑end traceability, auditing, and compliance verification for all database backups produced by the on‑prem SQL environment.

---

## 🚀 Architecture Summary

### **1. Source: SQL Server On‑Premises**
Backups are logged in:
DBAdmin.dbo.ProdBackup_Raw

This is the authoritative list of expected backups.

### **2. AWS Lambda Functions**
| Lambda | Purpose |
|--------|---------|
| **Lambda 1** | Reads SQL Server backup metadata and stores it in `backup_raw_onprem` (RDS PostgreSQL). |
| **Lambda 2** | Scans S3 buckets and inventories all delivered `.bak` and `.trn` files into `s3_backup_inventory`. |
| **Lambda 3** | Correlates expected vs delivered backups and updates `backup_delivery_status`. |

### **3. Destination: RDS PostgreSQL Schema**

schema: rds_backup_check
• backup_raw_onprem
• s3_backup_inventory
• backup_delivery_status

---

## 🧩 Data Flow Diagram


┌────────────────────┐     ┌────────────────────┐     ┌──────────────────────────┐
│ SQL Server On‑Prem │ --> │     Lambda 1        │ --> │  RDS: backup_raw_onprem  │
└────────────────────┘     └────────────────────┘     └──────────────────────────┘
┌────────────────────┐     ┌────────────────────┐     ┌──────────────────────────┐
│      AWS S3        │ --> │     Lambda 2        │ --> │  RDS: s3_backup_inventory │
└────────────────────┘     └────────────────────┘     └──────────────────────────┘
┌──────────────────────────┐ <-- Lambda 3 --> ┌──────────────────────────┐
│  backup_raw_onprem       │ <--------------> │  s3_backup_inventory      │
└──────────────────────────┘                  └──────────────────────────┘
↓
Updates backup_delivery_status

---

## ⏱ Project Roadmap

### ✅ **Completed**
- Python 3.11 environment configured
- pyodbc installed and tested
- SQL Server connectivity validated
- Lambda 1 tested locally successfully
- Project migrated into GitHub repository

### 🏗 **In Progress**
- Implement `backup_raw_onprem` UPSERT logic

### ⏳ **Upcoming**
1. Build Lambda 2 (S3 inventory)
2. Build Lambda 3 (reconciliation + delivery status)
3. End‑to‑end validation testing
4. Deployment using Docker‑based AWS Lambda images

---

## 🖥 Local Development

### **Python Interpreter**

C:\Users\rolando.sanchez\AppData\Local\Programs\Python\Python311\python.exe

### **Verify Python**
```powershell
& "C:\Users\rolando.sanchez\AppData\Local\Programs\Python\Python311\python.exe" --version

Install Dependencies:
& "C:\Users\rolando.sanchez\AppData\Local\Programs\Python\Python311\python.exe" -m pip install pyodbc

▶️ Running Lambda 1 Locally
Folder Structure
/BackupValidationProject
    /Lambdas
        run_local.py
        sandbox_backup_sqlraw_to_rds.py

Run the script
cd .\Lambdas\
& "C:\Users\rolando.sanchez\AppData\Local\Programs\Python\Python311\python.exe" run_local.py

Repository Structure
BackupValidationProject/
│
├── Lambdas/
│   ├── run_local.py
│   ├── sandbox_backup_sqlraw_to_rds.py   # Lambda 1 source
│
├── README.md
├── .gitignore
└── (additional documentation)