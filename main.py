import streamlit as st
import sqlite3
import hashlib
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import os
import shutil
import random
import io
import time

DB_NAME = "construction.db"

def get_connection():
    conn = sqlite3.connect(DB_NAME, timeout=30, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cur = conn.cursor()
    cur.executescript("""
        CREATE TABLE IF NOT EXISTS Role (
            RoleId INTEGER PRIMARY KEY AUTOINCREMENT,
            Name TEXT UNIQUE
        );
        INSERT OR IGNORE INTO Role (Name) VALUES ('admin'), ('manager'), ('viewer');

        CREATE TABLE IF NOT EXISTS User (
            UserId INTEGER PRIMARY KEY AUTOINCREMENT,
            Login TEXT UNIQUE,
            PasswordHash TEXT,
            RoleId INTEGER,
            FOREIGN KEY(RoleId) REFERENCES Role(RoleId)
        );

        CREATE TABLE IF NOT EXISTS Customer (
            CustomerId INTEGER PRIMARY KEY AUTOINCREMENT,
            Name TEXT NOT NULL,
            Inn TEXT,
            Phone TEXT,
            Address TEXT
        );

        CREATE TABLE IF NOT EXISTS Project (
            ProjectId INTEGER PRIMARY KEY AUTOINCREMENT,
            Name TEXT NOT NULL,
            Address TEXT,
            CustomerId INTEGER,
            StartDate TEXT,
            PlannedEndDate TEXT,
            ActualEndDate TEXT,
            Budget REAL,
            FOREIGN KEY(CustomerId) REFERENCES Customer(CustomerId)
        );

        CREATE TABLE IF NOT EXISTS Supplier (
            SupplierId INTEGER PRIMARY KEY AUTOINCREMENT,
            Name TEXT NOT NULL,
            Inn TEXT,
            Phone TEXT,
            Address TEXT
        );

        CREATE TABLE IF NOT EXISTS Material (
            MaterialId INTEGER PRIMARY KEY AUTOINCREMENT,
            Name TEXT NOT NULL,
            Unit TEXT,
            Price REAL
        );

        CREATE TABLE IF NOT EXISTS Warehouse (
            WarehouseId INTEGER PRIMARY KEY AUTOINCREMENT,
            Name TEXT NOT NULL,
            Address TEXT
        );
        INSERT OR IGNORE INTO Warehouse (Name, Address) VALUES ('Основной склад', 'г. Елабуга, ул. Складская 1');

        CREATE TABLE IF NOT EXISTS Stock (
            StockId INTEGER PRIMARY KEY AUTOINCREMENT,
            MaterialId INTEGER,
            WarehouseId INTEGER,
            Quantity REAL DEFAULT 0,
            FOREIGN KEY(MaterialId) REFERENCES Material(MaterialId),
            FOREIGN KEY(WarehouseId) REFERENCES Warehouse(WarehouseId),
            UNIQUE(MaterialId, WarehouseId)
        );

        CREATE TABLE IF NOT EXISTS Supply (
            SupplyId INTEGER PRIMARY KEY AUTOINCREMENT,
            Date TEXT NOT NULL,
            MaterialId INTEGER,
            SupplierId INTEGER,
            Quantity REAL NOT NULL,
            Price REAL NOT NULL,
            InvoiceNumber TEXT,
            FOREIGN KEY(MaterialId) REFERENCES Material(MaterialId),
            FOREIGN KEY(SupplierId) REFERENCES Supplier(SupplierId)
        );

        CREATE TABLE IF NOT EXISTS MaterialIssue (
            IssueId INTEGER PRIMARY KEY AUTOINCREMENT,
            Date TEXT NOT NULL,
            ProjectId INTEGER,
            MaterialId INTEGER,
            Quantity REAL NOT NULL,
            Reason TEXT,
            FOREIGN KEY(ProjectId) REFERENCES Project(ProjectId),
            FOREIGN KEY(MaterialId) REFERENCES Material(MaterialId)
        );

        CREATE TABLE IF NOT EXISTS Employee (
            EmployeeId INTEGER PRIMARY KEY AUTOINCREMENT,
            FullName TEXT NOT NULL,
            Position TEXT,
            Phone TEXT,
            HireDate TEXT
        );

        CREATE TABLE IF NOT EXISTS Assignment (
            AssignmentId INTEGER PRIMARY KEY AUTOINCREMENT,
            EmployeeId INTEGER,
            ProjectId INTEGER,
            Role TEXT,
            StartDate TEXT,
            EndDate TEXT,
            FOREIGN KEY(EmployeeId) REFERENCES Employee(EmployeeId),
            FOREIGN KEY(ProjectId) REFERENCES Project(ProjectId)
        );

        CREATE TABLE IF NOT EXISTS WorkStage (
            StageId INTEGER PRIMARY KEY AUTOINCREMENT,
            ProjectId INTEGER,
            Name TEXT NOT NULL,
            PlannedStart TEXT,
            PlannedEnd TEXT,
            ActualStart TEXT,
            ActualEnd TEXT,
            Status TEXT DEFAULT 'planned',
            FOREIGN KEY(ProjectId) REFERENCES Project(ProjectId)
        );

        CREATE TABLE IF NOT EXISTS Contract (
            ContractId INTEGER PRIMARY KEY AUTOINCREMENT,
            Number TEXT NOT NULL,
            DateSigned TEXT NOT NULL,
            CustomerId INTEGER,
            ProjectId INTEGER,
            Amount REAL,
            Status TEXT DEFAULT 'active',
            Notes TEXT,
            FOREIGN KEY(CustomerId) REFERENCES Customer(CustomerId),
            FOREIGN KEY(ProjectId) REFERENCES Project(ProjectId)
        );

        CREATE TABLE IF NOT EXISTS Equipment (
            EquipmentId INTEGER PRIMARY KEY AUTOINCREMENT,
            Name TEXT NOT NULL,
            Type TEXT,
            SerialNumber TEXT,
            Ownership TEXT,
            RentalCostPerDay REAL,
            FuelConsumptionPerHour REAL,
            IsAvailable INTEGER DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS EquipmentUsage (
            UsageId INTEGER PRIMARY KEY AUTOINCREMENT,
            EquipmentId INTEGER,
            ProjectId INTEGER,
            Date DATE NOT NULL,
            HoursWorked REAL,
            FuelUsed REAL,
            FOREIGN KEY(EquipmentId) REFERENCES Equipment(EquipmentId),
            FOREIGN KEY(ProjectId) REFERENCES Project(ProjectId)
        );
    """)
    conn.commit()
    conn.close()

def seed_data():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM Customer")
    if cur.fetchone()[0] == 0:
        cur.execute("INSERT INTO Customer (Name, Inn, Phone, Address) VALUES ('ООО СтройИнвест', '1650123456', '+7(855)123-45-67', 'г. Елабуга, ул. Строителей 1')")
        cur.execute("INSERT INTO Customer (Name, Inn, Phone, Address) VALUES ('ИП Иванов', '1650987654', '+7(855)987-65-43', 'г. Набережные Челны, пр. Мира 10')")
    cur.execute("SELECT COUNT(*) FROM Supplier")
    if cur.fetchone()[0] == 0:
        cur.execute("INSERT INTO Supplier (Name, Inn, Phone, Address) VALUES ('ООО СтройКомплект', '1645001122', '+7(843)222-33-44', 'г. Казань, ул. Транспортная 5')")
        cur.execute("INSERT INTO Supplier (Name, Inn, Phone, Address) VALUES ('ООО БетонСнаб', '1645223344', '+7(855)555-66-77', 'г. Елабуга, ул. Заводская 12')")
    cur.execute("SELECT COUNT(*) FROM Material")
    if cur.fetchone()[0] == 0:
        cur.execute("INSERT INTO Material (Name, Unit, Price) VALUES ('Цемент', 'кг', 52.0)")
        cur.execute("INSERT INTO Material (Name, Unit, Price) VALUES ('Песок', 'кг', 16.5)")
        cur.execute("INSERT INTO Material (Name, Unit, Price) VALUES ('Кирпич', 'шт', 13.2)")
        cur.execute("INSERT INTO Material (Name, Unit, Price) VALUES ('Доска обрезная', 'м³', 12500.0)")
    cur.execute("SELECT COUNT(*) FROM Employee")
    if cur.fetchone()[0] == 0:
        cur.execute("INSERT INTO Employee (FullName, Position, Phone, HireDate) VALUES ('Петров П.П.', 'Прораб', '+7(855)111-22-33', '2023-01-10')")
        cur.execute("INSERT INTO Employee (FullName, Position, Phone, HireDate) VALUES ('Сидоров С.С.', 'Монтажник', '+7(855)222-33-44', '2023-02-15')")
        cur.execute("INSERT INTO Employee (FullName, Position, Phone, HireDate) VALUES ('Кузнецов К.К.', 'Разнорабочий', '+7(855)333-44-55', '2023-03-20')")
    cur.execute("SELECT COUNT(*) FROM Project")
    if cur.fetchone()[0] == 0:
        cur.execute("INSERT INTO Project (Name, Address, CustomerId, StartDate, PlannedEndDate, Budget) VALUES ('Жилой дом на ул. Центральной', 'г. Елабуга, ул. Центральная 15', 1, '2025-04-01', '2025-12-01', 5200000)")
        cur.execute("INSERT INTO Project (Name, Address, CustomerId, StartDate, PlannedEndDate, Budget) VALUES ('Реконструкция склада', 'г. Набережные Челны, пр. Дружбы 5', 2, '2025-05-10', '2025-09-01', 2650000)")
    cur.execute("SELECT COUNT(*) FROM Stock")
    if cur.fetchone()[0] == 0:
        cur.execute("INSERT INTO Stock (MaterialId, WarehouseId, Quantity) VALUES (1,1,5200)")
        cur.execute("INSERT INTO Stock (MaterialId, WarehouseId, Quantity) VALUES (2,1,10500)")
        cur.execute("INSERT INTO Stock (MaterialId, WarehouseId, Quantity) VALUES (3,1,8200)")
        cur.execute("INSERT INTO Stock (MaterialId, WarehouseId, Quantity) VALUES (4,1,55)")
    cur.execute("SELECT COUNT(*) FROM Equipment")
    if cur.fetchone()[0] == 0:
        cur.execute("INSERT INTO Equipment (Name, Type, SerialNumber, Ownership, RentalCostPerDay, FuelConsumptionPerHour, IsAvailable) VALUES ('Экскаватор JCB', 'excavator', 'JCB123', 'owned', 0, 15.2, 1)")
        cur.execute("INSERT INTO Equipment (Name, Type, SerialNumber, Ownership, RentalCostPerDay, FuelConsumptionPerHour, IsAvailable) VALUES ('Кран КАМАЗ', 'crane', 'KAM456', 'rented', 5200, 25.5, 1)")
        cur.execute("INSERT INTO Equipment (Name, Type, SerialNumber, Ownership, RentalCostPerDay, FuelConsumptionPerHour, IsAvailable) VALUES ('Бетономешалка', 'mixer', 'MIX789', 'owned', 0, 8.4, 1)")
    cur.execute("SELECT COUNT(*) FROM Contract")
    if cur.fetchone()[0] == 0:
        cur.execute("INSERT INTO Contract (Number, DateSigned, CustomerId, ProjectId, Amount, Status) VALUES ('Д-001', '2025-03-01', 1, 1, 5200000, 'active')")
        cur.execute("INSERT INTO Contract (Number, DateSigned, CustomerId, ProjectId, Amount, Status) VALUES ('Д-002', '2025-04-15', 2, 2, 2650000, 'active')")
    cur.execute("SELECT COUNT(*) FROM User")
    if cur.fetchone()[0] == 0:
        pwd_admin = hashlib.sha256("admin123".encode()).hexdigest()
        pwd_manager = hashlib.sha256("manager123".encode()).hexdigest()
        pwd_viewer = hashlib.sha256("viewer123".encode()).hexdigest()
        cur.execute("INSERT INTO User (Login, PasswordHash, RoleId) VALUES (?, ?, (SELECT RoleId FROM Role WHERE Name='admin'))", ("admin", pwd_admin))
        cur.execute("INSERT INTO User (Login, PasswordHash, RoleId) VALUES (?, ?, (SELECT RoleId FROM Role WHERE Name='manager'))", ("manager", pwd_manager))
        cur.execute("INSERT INTO User (Login, PasswordHash, RoleId) VALUES (?, ?, (SELECT RoleId FROM Role WHERE Name='viewer'))", ("viewer", pwd_viewer))
    conn.commit()
    conn.close()

def generate_bulk_data():
    conn = get_connection()
    cur = conn.cursor()
    customers = [row[0] for row in cur.execute("SELECT CustomerId FROM Customer").fetchall()]
    suppliers = [row[0] for row in cur.execute("SELECT SupplierId FROM Supplier").fetchall()]
    materials = cur.execute("SELECT MaterialId, Name FROM Material").fetchall()
    material_ids = [m[0] for m in materials]
    employees = [row[0] for row in cur.execute("SELECT EmployeeId FROM Employee").fetchall()]
    equipment_ids = [row[0] for row in cur.execute("SELECT EquipmentId FROM Equipment").fetchall()]
    if len(customers) < 2:
        cur.execute("INSERT OR IGNORE INTO Customer (Name) VALUES ('Генеральный заказчик 1'), ('Генеральный заказчик 2')")
        conn.commit()
        customers = [row[0] for row in cur.execute("SELECT CustomerId FROM Customer").fetchall()]
    if len(suppliers) < 2:
        cur.execute("INSERT OR IGNORE INTO Supplier (Name) VALUES ('Поставщик 1'), ('Поставщик 2')")
        conn.commit()
        suppliers = [row[0] for row in cur.execute("SELECT SupplierId FROM Supplier").fetchall()]
    if len(material_ids) < 2:
        cur.execute("INSERT OR IGNORE INTO Material (Name, Unit, Price) VALUES ('Арматура', 'кг', 45), ('Бетон', 'м³', 4000)")
        conn.commit()
        materials = cur.execute("SELECT MaterialId, Name FROM Material").fetchall()
        material_ids = [m[0] for m in materials]
    if len(employees) < 2:
        cur.execute("INSERT OR IGNORE INTO Employee (FullName) VALUES ('Тестовый сотрудник 1'), ('Тестовый сотрудник 2')")
        conn.commit()
        employees = [row[0] for row in cur.execute("SELECT EmployeeId FROM Employee").fetchall()]
    if len(equipment_ids) < 2:
        cur.execute("INSERT OR IGNORE INTO Equipment (Name) VALUES ('Бульдозер'), ('Автокран')")
        conn.commit()
        equipment_ids = [row[0] for row in cur.execute("SELECT EquipmentId FROM Equipment").fetchall()]
    cur.execute("DELETE FROM MaterialIssue")
    cur.execute("DELETE FROM Supply")
    cur.execute("DELETE FROM Assignment")
    cur.execute("DELETE FROM WorkStage")
    cur.execute("DELETE FROM Contract")
    cur.execute("DELETE FROM EquipmentUsage")
    cur.execute("DELETE FROM Project")
    cur.execute("UPDATE Stock SET Quantity = 0")
    base_date = datetime(2025, 1, 1)
    projects = []
    for i in range(5000):
        name = f"Объект строительства {i+1}"
        cust_id = random.choice(customers)
        start = base_date + timedelta(days=random.randint(0, 365))
        planned_end = start + timedelta(days=random.randint(30, 365))
        budget = random.randint(100000, 10000000)
        cur.execute("INSERT INTO Project (Name, Address, CustomerId, StartDate, PlannedEndDate, Budget) VALUES (?,?,?,?,?,?)",
                    (name, f"г. Елабуга, ул. Строительная {i+1}", cust_id, start, planned_end, budget))
        projects.append(cur.lastrowid)
    conn.commit()
    for i in range(5000):
        mat_id = random.choice(material_ids)
        sup_id = random.choice(suppliers)
        date = base_date + timedelta(days=random.randint(0, 500))
        qty = random.randint(100, 10000)
        price = random.randint(10, 5000)
        invoice = f"Н-{random.randint(1000,9999)}"
        cur.execute("INSERT INTO Supply (Date, MaterialId, SupplierId, Quantity, Price, InvoiceNumber) VALUES (?,?,?,?,?,?)",
                    (date, mat_id, sup_id, qty, price, invoice))
        cur.execute("SELECT StockId, Quantity FROM Stock WHERE MaterialId = ? AND WarehouseId = 1", (mat_id,))
        stock = cur.fetchone()
        if stock:
            new_qty = stock[1] + qty
            cur.execute("UPDATE Stock SET Quantity = ? WHERE StockId = ?", (new_qty, stock[0]))
        else:
            cur.execute("INSERT INTO Stock (MaterialId, WarehouseId, Quantity) VALUES (?, 1, ?)", (mat_id, qty))
    conn.commit()
    for i in range(5000):
        proj_id = random.choice(projects)
        mat_id = random.choice(material_ids)
        date = base_date + timedelta(days=random.randint(0, 500))
        qty = random.randint(1, 500)
        reason = f"Списание по наряду №{random.randint(100,999)}"
        cur.execute("SELECT Quantity FROM Stock WHERE MaterialId = ? AND WarehouseId = 1", (mat_id,))
        row = cur.fetchone()
        stock_qty = row[0] if row else 0
        if stock_qty >= qty:
            cur.execute("INSERT INTO MaterialIssue (Date, ProjectId, MaterialId, Quantity, Reason) VALUES (?,?,?,?,?)",
                        (date, proj_id, mat_id, qty, reason))
            cur.execute("UPDATE Stock SET Quantity = Quantity - ? WHERE MaterialId = ? AND WarehouseId = 1", (qty, mat_id))
        else:
            cur.execute("INSERT INTO MaterialIssue (Date, ProjectId, MaterialId, Quantity, Reason) VALUES (?,?,?,0,?)",
                        (date, proj_id, mat_id, reason))
    conn.commit()
    for i in range(5000):
        emp_id = random.choice(employees)
        proj_id = random.choice(projects)
        start = base_date + timedelta(days=random.randint(0, 365))
        end = start + timedelta(days=random.randint(30, 200))
        role = random.choice(["Прораб", "Монтажник", "Разнорабочий", "Водитель"])
        cur.execute("INSERT INTO Assignment (EmployeeId, ProjectId, Role, StartDate, EndDate) VALUES (?,?,?,?,?)",
                    (emp_id, proj_id, role, start, end))
    conn.commit()
    stage_templates = ["Котлован", "Фундамент", "Стены", "Кровля", "Отделка", "Электрика", "Сантехника", "Благоустройство"]
    for i in range(5000):
        proj_id = random.choice(projects)
        name = random.choice(stage_templates) + f" (этап {i%10+1})"
        planned_start = base_date + timedelta(days=random.randint(0, 365))
        planned_end = planned_start + timedelta(days=random.randint(10, 90))
        status = random.choice(["planned", "completed"])
        actual_start = planned_start if status == "completed" else None
        actual_end = planned_end if status == "completed" else None
        cur.execute("INSERT INTO WorkStage (ProjectId, Name, PlannedStart, PlannedEnd, ActualStart, ActualEnd, Status) VALUES (?,?,?,?,?,?,?)",
                    (proj_id, name, planned_start, planned_end, actual_start, actual_end, status))
    conn.commit()
    for i in range(5000):
        cust_id = random.choice(customers)
        proj_id = random.choice(projects)
        number = f"Д-{random.randint(10000,99999)}"
        date_signed = base_date + timedelta(days=random.randint(0, 400))
        amount = random.randint(500000, 15000000)
        status = random.choice(["active", "completed", "terminated"])
        cur.execute("INSERT INTO Contract (Number, DateSigned, CustomerId, ProjectId, Amount, Status) VALUES (?,?,?,?,?,?)",
                    (number, date_signed, cust_id, proj_id, amount, status))
    conn.commit()
    for i in range(5000):
        eq_id = random.choice(equipment_ids)
        proj_id = random.choice(projects)
        date = base_date + timedelta(days=random.randint(0, 500))
        hours = random.uniform(1, 12)
        fuel = hours * random.uniform(5, 25)
        cur.execute("INSERT INTO EquipmentUsage (EquipmentId, ProjectId, Date, HoursWorked, FuelUsed) VALUES (?,?,?,?,?)",
                    (eq_id, proj_id, date, hours, fuel))
    conn.commit()
    conn.close()
    st.toast("Сгенерировано 5000 записей", icon="✅", duration=5000)
    time.sleep(2)
    st.rerun()

def export_df_to_excel(df, filename_prefix):
    if df.empty:
        st.toast("Нет данных для экспорта", icon="⚠️", duration=3000)
        return
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Data')
    excel_data = output.getvalue()
    st.download_button(
        label="📥 Скачать Excel",
        data=excel_data,
        file_name=f"{filename_prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

def hash_password(pwd):
    return hashlib.sha256(pwd.encode()).hexdigest()

def check_referential_integrity(table, id_field, id_value):
    conn = get_connection()
    cur = conn.cursor()
    dependencies = {
        "Project": [("MaterialIssue", "ProjectId"), ("Assignment", "ProjectId"), ("WorkStage", "ProjectId"), ("Contract", "ProjectId"), ("EquipmentUsage", "ProjectId")],
        "Material": [("Stock", "MaterialId"), ("Supply", "MaterialId"), ("MaterialIssue", "MaterialId")],
        "Supplier": [("Supply", "SupplierId")],
        "Customer": [("Project", "CustomerId"), ("Contract", "CustomerId")],
        "Employee": [("Assignment", "EmployeeId")],
        "Warehouse": [("Stock", "WarehouseId")],
        "Equipment": [("EquipmentUsage", "EquipmentId")],
    }
    if table in dependencies:
        for dep_table, dep_field in dependencies[table]:
            cur.execute(f"SELECT COUNT(*) FROM {dep_table} WHERE {dep_field}=?", (id_value,))
            if cur.fetchone()[0] > 0:
                conn.close()
                return False
    conn.close()
    return True

def adjust_stock(cur, conn, material_id, warehouse_id, quantity_change):
    cur.execute("SELECT StockId, Quantity FROM Stock WHERE MaterialId=? AND WarehouseId=?", (material_id, warehouse_id))
    row = cur.fetchone()
    if row:
        new_qty = row[1] + quantity_change
        if new_qty < 0:
            return False
        cur.execute("UPDATE Stock SET Quantity=? WHERE StockId=?", (new_qty, row[0]))
    else:
        if quantity_change < 0:
            return False
        cur.execute("INSERT INTO Stock (MaterialId, WarehouseId, Quantity) VALUES (?,?,?)", (material_id, warehouse_id, quantity_change))
    return True

@st.cache_data(ttl=300)
def get_dict_cached(table, id_col, name_col):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"SELECT {id_col}, {name_col} FROM {table}")
    rows = cur.fetchall()
    conn.close()
    return {row[1]: row[0] for row in rows}

def login():
    st.title("🏗️ Строительная компания – Учёт")
    with st.form("login_form"):
        login = st.text_input("Логин")
        password = st.text_input("Пароль", type="password")
        if st.form_submit_button("Войти"):
            conn = get_connection()
            cur = conn.cursor()
            pwd_hash = hash_password(password)
            cur.execute("""
                SELECT u.UserId, u.Login, r.Name as RoleName
                FROM User u
                JOIN Role r ON u.RoleId = r.RoleId
                WHERE u.Login = ? AND u.PasswordHash = ?
            """, (login, pwd_hash))
            user = cur.fetchone()
            conn.close()
            if user:
                st.session_state.user_id = user[0]
                st.session_state.user_login = user[1]
                st.session_state.user_role = user[2]
                st.rerun()
            else:
                st.toast("Неверный логин или пароль", icon="❌", duration=3000)
    st.caption("demo: admin / admin123 | manager / manager123 | viewer / viewer123")

def main():
    st.set_page_config(page_title="Строительная компания – Учёт", layout="wide", page_icon="🏗️")
    st.markdown("""
    <style>
        .stApp { background: linear-gradient(135deg, #f8f9fc 0%, #e9ecef 100%); }
        .stMetric { background: white; border-radius: 20px; padding: 15px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); transition: box-shadow 0.2s; }
        .stMetric:hover { box-shadow: 0 8px 20px rgba(0,0,0,0.15); }
        .stTabs [data-baseweb="tab-list"] button [data-testid="stMarkdownContainer"] p { font-size: 1.1rem; font-weight: 600; color: #2c3e50; }
        .stTabs [data-baseweb="tab-list"] { gap: 24px; }
        .stButton button { border-radius: 30px; font-weight: 500; transition: all 0.2s; }
        .stButton button:hover { transform: scale(1.02); }
        [data-testid="stSidebar"] { background-color: #2c3e50; }
        [data-testid="stSidebar"] .stMarkdown, [data-testid="stSidebar"] .stRadio label div[data-testid="stMarkdownContainer"] p { color: #ecf0f1 !important; }
        [data-testid="stSidebar"] .stRadio [role="radiogroup"] label { background-color: transparent !important; border-radius: 8px; padding: 5px 10px; margin: 2px 0; }
        [data-testid="stSidebar"] .stRadio [role="radiogroup"] label[data-baseweb="radio"]:hover { background-color: rgba(255,255,255,0.1) !important; }
        div[data-testid="stExpander"] { border-radius: 15px; border: none; box-shadow: 0 2px 6px rgba(0,0,0,0.05); }
        .dataframe { border-radius: 12px; overflow: hidden; }
        h1, h2, h3, h4 { color: #1e466e; }
        .stDataFrame { overflow-x: auto; }
    </style>
    """, unsafe_allow_html=True)

    if "user_id" not in st.session_state:
        login()
        return

    with st.sidebar:
        st.markdown(f"**👤 {st.session_state.user_login} ({st.session_state.user_role})**")
        role = st.session_state.user_role
        if role == "admin":
            menu = ["🏠 Главная", "📚 Справочники", "📦 Поставки", "🔨 Расход материалов",
                    "👷 Назначения", "📅 Этапы работ", "📄 Договоры", "🚜 Техника",
                    "📊 Аналитика", "📑 Отчёты", "💾 Резервное копирование", "⚙️ Генерация тестов"]
        elif role == "manager":
            menu = ["🏠 Главная", "📚 Справочники", "📦 Поставки", "🔨 Расход материалов",
                    "👷 Назначения", "📅 Этапы работ", "📄 Договоры", "🚜 Техника",
                    "📊 Аналитика", "📑 Отчёты"]
        else:
            menu = ["🏠 Главная", "📑 Отчёты", "📊 Аналитика"]
        choice = st.radio("Меню", menu)
        if st.button("🚪 Выйти"):
            for key in list(st.session_state.keys()):
                if key.startswith("user_"):
                    del st.session_state[key]
            st.rerun()

    conn = get_connection()
    cur = conn.cursor()

    def get_dict(table, id_col, name_col):
        return get_dict_cached(table, id_col, name_col)

    if choice == "🏠 Главная":
        st.header("📊 Панель управления")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            cur.execute("SELECT COUNT(*) FROM Project WHERE date('now') BETWEEN StartDate AND PlannedEndDate")
            active = cur.fetchone()[0]
            st.metric("🏗️ Активные объекты", active)
        with col2:
            cur.execute("SELECT COUNT(*) FROM MaterialIssue WHERE date(Date) = date('now')")
            today_issues = cur.fetchone()[0]
            st.metric("📦 Расход материалов сегодня", today_issues)
        with col3:
            cur.execute("SELECT COUNT(*) FROM EquipmentUsage WHERE date(Date) = date('now')")
            eq_usage = cur.fetchone()[0]
            st.metric("🚜 Задействовано техники", eq_usage)
        with col4:
            cur.execute("SELECT COUNT(*) FROM WorkStage WHERE Status='planned' AND date(PlannedEnd) < date('now')")
            overdue = cur.fetchone()[0]
            st.metric("⚠️ Просроченных этапов", overdue, delta="!")
        st.markdown("---")
        st.subheader("📋 Последние события")
        events = pd.read_sql_query("""
            SELECT 'Поставка' as Событие, Date as Дата, InvoiceNumber as Документ FROM Supply
            UNION
            SELECT 'Расход материала' as Событие, Date as Дата, Reason as Основание FROM MaterialIssue
            ORDER BY Дата DESC LIMIT 10
        """, conn)
        if not events.empty:
            st.dataframe(events, use_container_width=True)
        else:
            st.info("Нет событий")

    elif choice == "📚 Справочники":
        st.header("📚 Справочники")
        tabs = st.tabs(["🏗️ Объекты", "👥 Сотрудники", "📦 Материалы", "🚚 Поставщики", "🤝 Заказчики", "📄 Договоры", "🚜 Техника"])
        with tabs[0]:
            st.subheader("Объекты строительства")
            df = pd.read_sql_query("""
                SELECT p.ProjectId, p.Name, p.Address, c.Name as CustomerName,
                       p.StartDate, p.PlannedEndDate, p.Budget
                FROM Project p
                LEFT JOIN Customer c ON p.CustomerId = c.CustomerId
            """, conn)
            df.rename(columns={"ProjectId":"ID","Name":"Название","Address":"Адрес",
                               "CustomerName":"Заказчик","StartDate":"Дата начала",
                               "PlannedEndDate":"Плановая дата окончания","Budget":"Бюджет, руб"}, inplace=True)
            st.dataframe(df, use_container_width=True)
            if st.button("📥 Экспорт объектов в Excel", key="exp_proj"):
                export_df_to_excel(df, "objects")
            if role in ["admin","manager"]:
                with st.expander("➕ Добавить объект"):
                    with st.form("add_project"):
                        name = st.text_input("Название")
                        addr = st.text_input("Адрес")
                        cust_dict = get_dict("Customer", "CustomerId", "Name")
                        cust_name = st.selectbox("Заказчик", [""] + list(cust_dict.keys()))
                        start = st.date_input("Дата начала", value=None)
                        planned_end = st.date_input("Плановая дата окончания", value=None)
                        budget = st.number_input("Бюджет (руб)", min_value=0.0, step=1000.0)
                        if st.form_submit_button("Сохранить"):
                            if name:
                                cur.execute("INSERT INTO Project (Name, Address, CustomerId, StartDate, PlannedEndDate, Budget) VALUES (?,?,?,?,?,?)",
                                            (name, addr, cust_dict.get(cust_name), start, planned_end, budget))
                                conn.commit()
                                st.toast("Добавлено", icon="✅", duration=5000)
                                time.sleep(1)
                                st.rerun()
                with st.expander("✏️ Редактировать / 🗑️ Удалить объект"):
                    proj_dict = get_dict("Project", "ProjectId", "Name")
                    if proj_dict:
                        proj_name = st.selectbox("Выберите объект", list(proj_dict.keys()))
                        proj_id = proj_dict[proj_name]
                        proj = cur.execute("SELECT * FROM Project WHERE ProjectId=?", (proj_id,)).fetchone()
                        if proj:
                            cust_dict = get_dict("Customer", "CustomerId", "Name")
                            current_cust = cur.execute("SELECT Name FROM Customer WHERE CustomerId=?", (proj["CustomerId"],)).fetchone()
                            current_cust_name = current_cust["Name"] if current_cust else ""
                            with st.form("edit_project"):
                                new_name = st.text_input("Название", proj["Name"])
                                new_addr = st.text_input("Адрес", proj["Address"] or "")
                                new_cust = st.selectbox("Заказчик", list(cust_dict.keys()), index=list(cust_dict.keys()).index(current_cust_name) if current_cust_name in cust_dict else 0)
                                start_val = datetime.strptime(proj["StartDate"][:10], "%Y-%m-%d") if proj["StartDate"] else None
                                planned_end_val = datetime.strptime(proj["PlannedEndDate"][:10], "%Y-%m-%d") if proj["PlannedEndDate"] else None
                                new_start = st.date_input("Дата начала", value=start_val)
                                new_planned = st.date_input("Плановая дата окончания", value=planned_end_val)
                                new_budget = st.number_input("Бюджет", value=float(proj["Budget"] or 0))
                                if st.form_submit_button("Обновить"):
                                    cur.execute("UPDATE Project SET Name=?, Address=?, CustomerId=?, StartDate=?, PlannedEndDate=?, Budget=? WHERE ProjectId=?",
                                                (new_name, new_addr, cust_dict[new_cust], new_start, new_planned, new_budget, proj_id))
                                    conn.commit()
                                    st.toast("Обновлено", icon="✅", duration=5000)
                                    time.sleep(1)
                                    st.rerun()
                            if role == "admin":
                                if st.button("Удалить объект", key="del_proj"):
                                    if check_referential_integrity("Project", "ProjectId", proj_id):
                                        cur.execute("DELETE FROM Project WHERE ProjectId=?", (proj_id,))
                                        conn.commit()
                                        st.toast("Удалено", icon="🗑️", duration=5000)
                                        time.sleep(1)
                                        st.rerun()
                                    else:
                                        st.toast("Нельзя удалить объект, есть ссылки", icon="⚠️", duration=5000)
        with tabs[1]:
            st.subheader("Сотрудники")
            df = pd.read_sql_query("SELECT EmployeeId, FullName, Position, Phone, HireDate FROM Employee", conn)
            df.rename(columns={"EmployeeId":"ID","FullName":"ФИО","Position":"Должность","Phone":"Телефон","HireDate":"Дата приёма"}, inplace=True)
            st.dataframe(df, use_container_width=True)
            if st.button("📥 Экспорт сотрудников в Excel", key="exp_emp"):
                export_df_to_excel(df, "employees")
            if role in ["admin","manager"]:
                with st.expander("➕ Добавить сотрудника"):
                    with st.form("add_emp"):
                        name = st.text_input("ФИО")
                        pos = st.text_input("Должность")
                        phone = st.text_input("Телефон")
                        hire = st.date_input("Дата приёма", value=None)
                        if st.form_submit_button("Сохранить"):
                            if name:
                                cur.execute("INSERT INTO Employee (FullName, Position, Phone, HireDate) VALUES (?,?,?,?)", (name, pos, phone, hire))
                                conn.commit()
                                st.toast("Добавлено", icon="✅", duration=5000)
                                time.sleep(1)
                                st.rerun()
                with st.expander("✏️ Редактировать / 🗑️ Удалить"):
                    emp_dict = get_dict("Employee","EmployeeId","FullName")
                    if emp_dict:
                        emp_name = st.selectbox("Выберите сотрудника", list(emp_dict.keys()))
                        emp_id = emp_dict[emp_name]
                        emp = cur.execute("SELECT * FROM Employee WHERE EmployeeId=?", (emp_id,)).fetchone()
                        if emp:
                            with st.form("edit_emp"):
                                new_name = st.text_input("ФИО", emp["FullName"])
                                new_pos = st.text_input("Должность", emp["Position"] or "")
                                new_phone = st.text_input("Телефон", emp["Phone"] or "")
                                hire_val = datetime.strptime(emp["HireDate"][:10], "%Y-%m-%d") if emp["HireDate"] else None
                                new_hire = st.date_input("Дата приёма", value=hire_val)
                                if st.form_submit_button("Обновить"):
                                    cur.execute("UPDATE Employee SET FullName=?, Position=?, Phone=?, HireDate=? WHERE EmployeeId=?",
                                                (new_name, new_pos, new_phone, new_hire, emp_id))
                                    conn.commit()
                                    st.toast("Обновлено", icon="✅", duration=5000)
                                    time.sleep(1)
                                    st.rerun()
                            if role=="admin" and st.button("Удалить сотрудника", key="del_emp"):
                                if check_referential_integrity("Employee","EmployeeId",emp_id):
                                    cur.execute("DELETE FROM Employee WHERE EmployeeId=?", (emp_id,))
                                    conn.commit()
                                    st.toast("Удалено", icon="🗑️", duration=5000)
                                    time.sleep(1)
                                    st.rerun()
                                else:
                                    st.toast("Есть назначения", icon="⚠️", duration=5000)
        with tabs[2]:
            st.subheader("Материалы")
            df = pd.read_sql_query("SELECT MaterialId, Name, Unit, Price FROM Material", conn)
            df.rename(columns={"MaterialId":"ID","Name":"Название","Unit":"Ед. изм.","Price":"Цена, руб"}, inplace=True)
            st.dataframe(df, use_container_width=True)
            if st.button("📥 Экспорт материалов в Excel", key="exp_mat"):
                export_df_to_excel(df, "materials")
            if role in ["admin","manager"]:
                with st.expander("➕ Добавить материал"):
                    with st.form("add_mat"):
                        name = st.text_input("Название")
                        unit = st.text_input("Ед. изм.")
                        price = st.number_input("Цена за ед., руб", min_value=0.0, step=0.1)
                        if st.form_submit_button("Сохранить"):
                            if name:
                                cur.execute("INSERT INTO Material (Name, Unit, Price) VALUES (?,?,?)", (name, unit, price))
                                conn.commit()
                                st.toast("Добавлено", icon="✅", duration=5000)
                                time.sleep(1)
                                st.rerun()
                with st.expander("✏️ Редактировать / 🗑️ Удалить материал"):
                    mat_dict = get_dict("Material","MaterialId","Name")
                    if mat_dict:
                        mat_name = st.selectbox("Выберите материал", list(mat_dict.keys()))
                        mat_id = mat_dict[mat_name]
                        mat = cur.execute("SELECT * FROM Material WHERE MaterialId=?", (mat_id,)).fetchone()
                        if mat:
                            with st.form("edit_mat"):
                                new_name = st.text_input("Название", mat["Name"])
                                new_unit = st.text_input("Ед. изм.", mat["Unit"] or "")
                                new_price = st.number_input("Цена", value=float(mat["Price"] or 0))
                                if st.form_submit_button("Обновить"):
                                    cur.execute("UPDATE Material SET Name=?, Unit=?, Price=? WHERE MaterialId=?", (new_name, new_unit, new_price, mat_id))
                                    conn.commit()
                                    st.toast("Обновлено", icon="✅", duration=5000)
                                    time.sleep(1)
                                    st.rerun()
                            if role=="admin" and st.button("Удалить материал", key="del_mat"):
                                if check_referential_integrity("Material","MaterialId",mat_id):
                                    cur.execute("DELETE FROM Material WHERE MaterialId=?", (mat_id,))
                                    conn.commit()
                                    st.toast("Удалено", icon="🗑️", duration=5000)
                                    time.sleep(1)
                                    st.rerun()
                                else:
                                    st.toast("Есть поставки/остатки/расходы", icon="⚠️", duration=5000)
        with tabs[3]:
            st.subheader("Поставщики")
            df = pd.read_sql_query("SELECT SupplierId, Name, Inn, Phone, Address FROM Supplier", conn)
            df.rename(columns={"SupplierId":"ID","Name":"Название","Inn":"ИНН","Phone":"Телефон","Address":"Адрес"}, inplace=True)
            st.dataframe(df, use_container_width=True)
            if st.button("📥 Экспорт поставщиков в Excel", key="exp_sup"):
                export_df_to_excel(df, "suppliers")
            if role in ["admin","manager"]:
                with st.expander("➕ Добавить поставщика"):
                    with st.form("add_sup"):
                        name = st.text_input("Название")
                        inn = st.text_input("ИНН")
                        phone = st.text_input("Телефон")
                        addr = st.text_input("Адрес")
                        if st.form_submit_button("Сохранить"):
                            if name:
                                cur.execute("INSERT INTO Supplier (Name, Inn, Phone, Address) VALUES (?,?,?,?)", (name, inn, phone, addr))
                                conn.commit()
                                st.toast("Добавлено", icon="✅", duration=5000)
                                time.sleep(1)
                                st.rerun()
                with st.expander("✏️ Редактировать / 🗑️ Удалить поставщика"):
                    sup_dict = get_dict("Supplier","SupplierId","Name")
                    if sup_dict:
                        sup_name = st.selectbox("Выберите поставщика", list(sup_dict.keys()))
                        sup_id = sup_dict[sup_name]
                        sup = cur.execute("SELECT * FROM Supplier WHERE SupplierId=?", (sup_id,)).fetchone()
                        if sup:
                            with st.form("edit_sup"):
                                new_name = st.text_input("Название", sup["Name"])
                                new_inn = st.text_input("ИНН", sup["Inn"] or "")
                                new_phone = st.text_input("Телефон", sup["Phone"] or "")
                                new_addr = st.text_input("Адрес", sup["Address"] or "")
                                if st.form_submit_button("Обновить"):
                                    cur.execute("UPDATE Supplier SET Name=?, Inn=?, Phone=?, Address=? WHERE SupplierId=?", (new_name, new_inn, new_phone, new_addr, sup_id))
                                    conn.commit()
                                    st.toast("Обновлено", icon="✅", duration=5000)
                                    time.sleep(1)
                                    st.rerun()
                            if role=="admin" and st.button("Удалить поставщика", key="del_sup"):
                                if check_referential_integrity("Supplier","SupplierId",sup_id):
                                    cur.execute("DELETE FROM Supplier WHERE SupplierId=?", (sup_id,))
                                    conn.commit()
                                    st.toast("Удалено", icon="🗑️", duration=5000)
                                    time.sleep(1)
                                    st.rerun()
                                else:
                                    st.toast("Есть поставки", icon="⚠️", duration=5000)
        with tabs[4]:
            st.subheader("Заказчики")
            df = pd.read_sql_query("SELECT CustomerId, Name, Inn, Phone, Address FROM Customer", conn)
            df.rename(columns={"CustomerId":"ID","Name":"Название","Inn":"ИНН","Phone":"Телефон","Address":"Адрес"}, inplace=True)
            st.dataframe(df, use_container_width=True)
            if st.button("📥 Экспорт заказчиков в Excel", key="exp_cust"):
                export_df_to_excel(df, "customers")
            if role in ["admin","manager"]:
                with st.expander("➕ Добавить заказчика"):
                    with st.form("add_cust"):
                        name = st.text_input("Название")
                        inn = st.text_input("ИНН")
                        phone = st.text_input("Телефон")
                        addr = st.text_input("Адрес")
                        if st.form_submit_button("Сохранить"):
                            if name:
                                cur.execute("INSERT INTO Customer (Name, Inn, Phone, Address) VALUES (?,?,?,?)", (name, inn, phone, addr))
                                conn.commit()
                                st.toast("Добавлено", icon="✅", duration=5000)
                                time.sleep(1)
                                st.rerun()
                with st.expander("✏️ Редактировать / 🗑️ Удалить заказчика"):
                    cust_dict = get_dict("Customer","CustomerId","Name")
                    if cust_dict:
                        cust_name = st.selectbox("Выберите заказчика", list(cust_dict.keys()))
                        cust_id = cust_dict[cust_name]
                        cust = cur.execute("SELECT * FROM Customer WHERE CustomerId=?", (cust_id,)).fetchone()
                        if cust:
                            with st.form("edit_cust"):
                                new_name = st.text_input("Название", cust["Name"])
                                new_inn = st.text_input("ИНН", cust["Inn"] or "")
                                new_phone = st.text_input("Телефон", cust["Phone"] or "")
                                new_addr = st.text_input("Адрес", cust["Address"] or "")
                                if st.form_submit_button("Обновить"):
                                    cur.execute("UPDATE Customer SET Name=?, Inn=?, Phone=?, Address=? WHERE CustomerId=?", (new_name, new_inn, new_phone, new_addr, cust_id))
                                    conn.commit()
                                    st.toast("Обновлено", icon="✅", duration=5000)
                                    time.sleep(1)
                                    st.rerun()
                            if role=="admin" and st.button("Удалить заказчика", key="del_cust"):
                                if check_referential_integrity("Customer","CustomerId",cust_id):
                                    cur.execute("DELETE FROM Customer WHERE CustomerId=?", (cust_id,))
                                    conn.commit()
                                    st.toast("Удалено", icon="🗑️", duration=5000)
                                    time.sleep(1)
                                    st.rerun()
                                else:
                                    st.toast("Есть объекты", icon="⚠️", duration=5000)
        with tabs[5]:
            st.subheader("Договоры")
            df = pd.read_sql_query("""
                SELECT c.ContractId, c.Number, c.DateSigned, cust.Name as Customer, p.Name as Project, c.Amount, c.Status, c.Notes
                FROM Contract c
                LEFT JOIN Customer cust ON c.CustomerId = cust.CustomerId
                LEFT JOIN Project p ON c.ProjectId = p.ProjectId
            """, conn)
            df.rename(columns={"ContractId":"ID","Number":"Номер","DateSigned":"Дата","Customer":"Заказчик",
                               "Project":"Объект","Amount":"Сумма, руб","Status":"Статус","Notes":"Примечания"}, inplace=True)
            st.dataframe(df, use_container_width=True)
            if st.button("📥 Экспорт договоров в Excel", key="exp_contract_ref"):
                export_df_to_excel(df, "contracts_ref")
            if role in ["admin","manager"]:
                with st.expander("➕ Добавить договор"):
                    with st.form("add_contract"):
                        num = st.text_input("Номер договора")
                        date_signed = st.date_input("Дата подписания", datetime.now())
                        cust_dict = get_dict("Customer","CustomerId","Name")
                        cust = st.selectbox("Заказчик", list(cust_dict.keys()))
                        proj_dict = get_dict("Project","ProjectId","Name")
                        proj = st.selectbox("Объект", [""] + list(proj_dict.keys()))
                        amount = st.number_input("Сумма, руб", min_value=0.0, step=1000.0)
                        status = st.selectbox("Статус", ["active","completed","terminated"])
                        notes = st.text_area("Примечания")
                        if st.form_submit_button("Сохранить"):
                            cur.execute("INSERT INTO Contract (Number, DateSigned, CustomerId, ProjectId, Amount, Status, Notes) VALUES (?,?,?,?,?,?,?)",
                                        (num, date_signed, cust_dict[cust], proj_dict.get(proj), amount, status, notes))
                            conn.commit()
                            st.toast("Добавлено", icon="✅", duration=5000)
                            time.sleep(1)
                            st.rerun()
                if role == "admin":
                    with st.expander("🗑️ Удалить договор"):
                        ids = [row["ID"] for _, row in df.iterrows()]
                        if ids:
                            cid = st.selectbox("Выберите ID договора для удаления", ids)
                            if st.button("Удалить", key="del_contract"):
                                cur.execute("DELETE FROM Contract WHERE ContractId=?", (cid,))
                                conn.commit()
                                st.toast("Удалено", icon="🗑️", duration=5000)
                                time.sleep(1)
                                st.rerun()
        with tabs[6]:
            st.subheader("Техника и оборудование")
            df = pd.read_sql_query("""
                SELECT EquipmentId, Name, Type, SerialNumber, Ownership,
                       RentalCostPerDay, FuelConsumptionPerHour, IsAvailable
                FROM Equipment
            """, conn)
            df.rename(columns={"EquipmentId":"ID","Name":"Название","Type":"Тип","SerialNumber":"Серийный номер",
                               "Ownership":"Владение","RentalCostPerDay":"Аренда (руб/день)",
                               "FuelConsumptionPerHour":"Расход топлива (л/ч)","IsAvailable":"Доступна"}, inplace=True)
            st.dataframe(df, use_container_width=True)
            if st.button("📥 Экспорт техники в Excel", key="exp_equip"):
                export_df_to_excel(df, "equipment")
            if role in ["admin","manager"]:
                with st.expander("➕ Добавить технику"):
                    with st.form("add_equip"):
                        name = st.text_input("Название")
                        typ = st.selectbox("Тип", ["excavator","crane","truck","mixer","other"])
                        serial = st.text_input("Серийный номер")
                        ownership = st.selectbox("Владение", ["owned","rented"])
                        rent_cost = st.number_input("Аренда (руб/день)", min_value=0.0, step=100.0)
                        fuel_cons = st.number_input("Расход топлива (л/ч)", min_value=0.0, step=0.5)
                        available = st.checkbox("Доступна", value=True)
                        if st.form_submit_button("Сохранить"):
                            cur.execute("INSERT INTO Equipment (Name, Type, SerialNumber, Ownership, RentalCostPerDay, FuelConsumptionPerHour, IsAvailable) VALUES (?,?,?,?,?,?,?)",
                                        (name, typ, serial, ownership, rent_cost, fuel_cons, int(available)))
                            conn.commit()
                            st.toast("Добавлено", icon="✅", duration=5000)
                            time.sleep(1)
                            st.rerun()
                if role == "admin":
                    with st.expander("🗑️ Удалить технику"):
                        ids = [row["ID"] for _, row in df.iterrows()]
                        if ids:
                            eid = st.selectbox("Выберите ID техники для удаления", ids)
                            if st.button("Удалить", key="del_eq"):
                                if check_referential_integrity("Equipment","EquipmentId",eid):
                                    cur.execute("DELETE FROM Equipment WHERE EquipmentId=?", (eid,))
                                    conn.commit()
                                    st.toast("Удалено", icon="🗑️", duration=5000)
                                    time.sleep(1)
                                    st.rerun()
                                else:
                                    st.toast("Есть записи об использовании", icon="⚠️", duration=5000)

    elif choice == "📦 Поставки":
        st.header("📦 Поставки материалов")
        df = pd.read_sql_query("""
            SELECT s.SupplyId, s.Date, m.Name as Material, m.Unit, sup.Name as Supplier,
                   s.Quantity, s.Price, s.InvoiceNumber
            FROM Supply s
            JOIN Material m ON s.MaterialId = m.MaterialId
            JOIN Supplier sup ON s.SupplierId = sup.SupplierId
            ORDER BY s.Date DESC
        """, conn)
        df.rename(columns={"SupplyId":"ID","Date":"Дата","Material":"Материал","Unit":"Ед. изм.","Supplier":"Поставщик",
                           "Quantity":"Количество","Price":"Цена, руб","InvoiceNumber":"Накладная"}, inplace=True)
        st.dataframe(df, use_container_width=True)
        if st.button("📥 Экспорт поставок в Excel", key="exp_supply"):
            export_df_to_excel(df, "supply")
        with st.form("add_supply"):
            col1, col2 = st.columns(2)
            with col1:
                date = st.date_input("Дата поставки", datetime.now())
                mat_dict = get_dict("Material", "MaterialId", "Name")
                material = st.selectbox("Материал", list(mat_dict.keys()))
                quantity = st.number_input("Количество", min_value=0.0, step=0.1)
            with col2:
                sup_dict = get_dict("Supplier", "SupplierId", "Name")
                supplier = st.selectbox("Поставщик", list(sup_dict.keys()))
                price = st.number_input("Цена за ед., руб", min_value=0.0, step=0.1)
                invoice = st.text_input("Номер накладной")
            if st.form_submit_button("Добавить поставку"):
                if material and supplier and quantity > 0:
                    cur.execute("INSERT INTO Supply (Date, MaterialId, SupplierId, Quantity, Price, InvoiceNumber) VALUES (?,?,?,?,?,?)",
                                (date, mat_dict[material], sup_dict[supplier], quantity, price, invoice))
                    if adjust_stock(cur, conn, mat_dict[material], 1, quantity):
                        conn.commit()
                        st.toast("Поставка добавлена", icon="✅", duration=5000)
                        time.sleep(1)
                        st.rerun()
                    else:
                        conn.rollback()
                        st.toast("Ошибка при обновлении склада", icon="❌", duration=5000)

    elif choice == "🔨 Расход материалов":
        st.header("🔨 Расход материалов на объекты")
        df = pd.read_sql_query("""
            SELECT i.IssueId, i.Date, p.Name as Project, m.Name as Material, m.Unit,
                   i.Quantity, i.Reason
            FROM MaterialIssue i
            JOIN Project p ON i.ProjectId = p.ProjectId
            JOIN Material m ON i.MaterialId = m.MaterialId
            ORDER BY i.Date DESC
        """, conn)
        df.rename(columns={"IssueId":"ID","Date":"Дата","Project":"Объект","Material":"Материал","Unit":"Ед. изм.","Quantity":"Количество","Reason":"Основание"}, inplace=True)
        st.dataframe(df, use_container_width=True)
        if st.button("📥 Экспорт расхода в Excel", key="exp_issue"):
            export_df_to_excel(df, "material_issue")
        with st.form("add_issue"):
            date = st.date_input("Дата расхода", datetime.now())
            proj_dict = get_dict("Project", "ProjectId", "Name")
            project = st.selectbox("Объект", list(proj_dict.keys()))
            mat_dict = get_dict("Material", "MaterialId", "Name")
            material = st.selectbox("Материал", list(mat_dict.keys()))
            quantity = st.number_input("Количество", min_value=0.0, step=0.1)
            reason = st.text_area("Основание (наряд, задание)")
            if st.form_submit_button("Списать материал"):
                cur.execute("SELECT Quantity FROM Stock WHERE MaterialId=? AND WarehouseId=1", (mat_dict[material],))
                row = cur.fetchone()
                stock_qty = row[0] if row else 0
                if stock_qty < quantity:
                    st.toast(f"Недостаточно материала. Доступно: {stock_qty}", icon="⚠️", duration=5000)
                else:
                    cur.execute("INSERT INTO MaterialIssue (Date, ProjectId, MaterialId, Quantity, Reason) VALUES (?,?,?,?,?)",
                                (date, proj_dict[project], mat_dict[material], quantity, reason))
                    if adjust_stock(cur, conn, mat_dict[material], 1, -quantity):
                        conn.commit()
                        st.toast("Расход оформлен", icon="✅", duration=5000)
                        time.sleep(1)
                        st.rerun()
                    else:
                        conn.rollback()
                        st.toast("Ошибка при списании", icon="❌", duration=5000)

    elif choice == "👷 Назначения":
        st.header("👷 Назначение сотрудников на объекты")
        df = pd.read_sql_query("""
            SELECT a.AssignmentId, e.FullName as Employee, p.Name as Project, a.Role, a.StartDate, a.EndDate
            FROM Assignment a
            JOIN Employee e ON a.EmployeeId = e.EmployeeId
            JOIN Project p ON a.ProjectId = p.ProjectId
        """, conn)
        df.rename(columns={"AssignmentId":"ID","Employee":"Сотрудник","Project":"Объект","Role":"Роль",
                           "StartDate":"Дата начала","EndDate":"Дата окончания"}, inplace=True)
        st.dataframe(df, use_container_width=True)
        if st.button("📥 Экспорт назначений в Excel", key="exp_assign"):
            export_df_to_excel(df, "assignments")
        with st.form("add_assign"):
            emp_dict = get_dict("Employee", "EmployeeId", "FullName")
            proj_dict = get_dict("Project", "ProjectId", "Name")
            emp = st.selectbox("Сотрудник", list(emp_dict.keys()))
            proj = st.selectbox("Объект", list(proj_dict.keys()))
            role = st.text_input("Роль (прораб, монтажник, ...)")
            start_date = st.date_input("Дата начала работы на объекте")
            end_date = st.date_input("Дата окончания", value=None)
            if st.form_submit_button("Назначить"):
                cur.execute("INSERT INTO Assignment (EmployeeId, ProjectId, Role, StartDate, EndDate) VALUES (?,?,?,?,?)",
                            (emp_dict[emp], proj_dict[proj], role, start_date, end_date))
                conn.commit()
                st.toast("Назначено", icon="✅", duration=5000)
                time.sleep(1)
                st.rerun()

    elif choice == "📅 Этапы работ":
        st.header("📅 Этапы работ по объектам")
        df = pd.read_sql_query("""
            SELECT w.StageId, p.Name as Project, w.Name, w.PlannedStart, w.PlannedEnd,
                   w.ActualStart, w.ActualEnd, w.Status
            FROM WorkStage w
            JOIN Project p ON w.ProjectId = p.ProjectId
        """, conn)
        df.rename(columns={"StageId":"ID","Project":"Объект","Name":"Название этапа","PlannedStart":"План. начало",
                           "PlannedEnd":"План. окончание","ActualStart":"Факт. начало","ActualEnd":"Факт. окончание",
                           "Status":"Статус"}, inplace=True)
        st.dataframe(df, use_container_width=True)
        if st.button("📥 Экспорт этапов в Excel", key="exp_stage"):
            export_df_to_excel(df, "work_stages")
        with st.form("add_stage"):
            proj_dict = get_dict("Project", "ProjectId", "Name")
            proj = st.selectbox("Объект", list(proj_dict.keys()))
            stage_name = st.text_input("Название этапа")
            planned_start = st.date_input("Плановая дата начала")
            planned_end = st.date_input("Плановая дата окончания")
            if st.form_submit_button("Добавить этап"):
                if stage_name:
                    cur.execute("INSERT INTO WorkStage (ProjectId, Name, PlannedStart, PlannedEnd, Status) VALUES (?,?,?,?,'planned')",
                                (proj_dict[proj], stage_name, planned_start, planned_end))
                    conn.commit()
                    st.toast("Добавлено", icon="✅", duration=5000)
                    time.sleep(1)
                    st.rerun()
        with st.expander("✅ Отметить фактическое выполнение этапа"):
            stage_list = cur.execute("SELECT StageId, Name FROM WorkStage WHERE Status='planned'").fetchall()
            if stage_list:
                stage_id = st.selectbox("Выберите этап", [row[0] for row in stage_list], format_func=lambda x: next((row[1] for row in stage_list if row[0]==x), ""))
                actual_start = st.date_input("Фактическая дата начала")
                actual_end = st.date_input("Фактическая дата окончания")
                if st.button("Закрыть этап как выполненный"):
                    cur.execute("UPDATE WorkStage SET ActualStart=?, ActualEnd=?, Status='completed' WHERE StageId=?", (actual_start, actual_end, stage_id))
                    conn.commit()
                    st.toast("Этап выполнен", icon="✅", duration=5000)
                    time.sleep(1)
                    st.rerun()

    elif choice == "📄 Договоры":
        st.header("📄 Договоры")
        df = pd.read_sql_query("""
            SELECT c.ContractId, c.Number, c.DateSigned, cust.Name as Customer, p.Name as Project,
                   c.Amount, c.Status, c.Notes
            FROM Contract c
            LEFT JOIN Customer cust ON c.CustomerId = cust.CustomerId
            LEFT JOIN Project p ON c.ProjectId = p.ProjectId
        """, conn)
        df.rename(columns={"ContractId":"ID","Number":"Номер","DateSigned":"Дата","Customer":"Заказчик",
                           "Project":"Объект","Amount":"Сумма, руб","Status":"Статус","Notes":"Примечания"}, inplace=True)
        st.dataframe(df, use_container_width=True)
        if st.button("📥 Экспорт договоров в Excel", key="exp_contract"):
            export_df_to_excel(df, "contracts")
        if role in ["admin","manager"]:
            with st.expander("➕ Добавить договор"):
                with st.form("add_contract"):
                    num = st.text_input("Номер договора")
                    date_signed = st.date_input("Дата подписания", datetime.now())
                    cust_dict = get_dict("Customer","CustomerId","Name")
                    cust = st.selectbox("Заказчик", list(cust_dict.keys()))
                    proj_dict = get_dict("Project","ProjectId","Name")
                    proj = st.selectbox("Объект", [""] + list(proj_dict.keys()))
                    amount = st.number_input("Сумма, руб", min_value=0.0, step=1000.0)
                    status = st.selectbox("Статус", ["active","completed","terminated"])
                    notes = st.text_area("Примечания")
                    if st.form_submit_button("Сохранить"):
                        cur.execute("INSERT INTO Contract (Number, DateSigned, CustomerId, ProjectId, Amount, Status, Notes) VALUES (?,?,?,?,?,?,?)",
                                    (num, date_signed, cust_dict[cust], proj_dict.get(proj), amount, status, notes))
                        conn.commit()
                        st.toast("Добавлено", icon="✅", duration=5000)
                        time.sleep(1)
                        st.rerun()
            if role == "admin":
                with st.expander("🗑️ Удалить договор"):
                    ids = [row["ID"] for _, row in df.iterrows()]
                    if ids:
                        cid = st.selectbox("Выберите ID договора для удаления", ids)
                        if st.button("Удалить", key="del_contract"):
                            cur.execute("DELETE FROM Contract WHERE ContractId=?", (cid,))
                            conn.commit()
                            st.toast("Удалено", icon="🗑️", duration=5000)
                            time.sleep(1)
                            st.rerun()

    elif choice == "🚜 Техника":
        st.header("🚜 Учёт использования техники")
        tab_usage, tab_log = st.tabs(["📝 Запись работы", "📋 История"])
        with tab_usage:
            with st.form("equip_usage"):
                eq_dict = get_dict("Equipment","EquipmentId","Name")
                equip = st.selectbox("Техника", list(eq_dict.keys()))
                proj_dict = get_dict("Project","ProjectId","Name")
                proj = st.selectbox("Объект", list(proj_dict.keys()))
                date = st.date_input("Дата работы", datetime.now())
                hours = st.number_input("Отработано часов", min_value=0.0, step=0.5)
                fuel = st.number_input("Фактический расход топлива (л)", min_value=0.0, step=1.0)
                if st.form_submit_button("Записать работу"):
                    cur.execute("INSERT INTO EquipmentUsage (EquipmentId, ProjectId, Date, HoursWorked, FuelUsed) VALUES (?,?,?,?,?)",
                                (eq_dict[equip], proj_dict[proj], date, hours, fuel))
                    conn.commit()
                    st.toast("Запись добавлена", icon="✅", duration=5000)
                    time.sleep(1)
                    st.rerun()
        with tab_log:
            df = pd.read_sql_query("""
                SELECT u.UsageId, e.Name as Equipment, p.Name as Project, u.Date, u.HoursWorked, u.FuelUsed
                FROM EquipmentUsage u
                JOIN Equipment e ON u.EquipmentId = e.EquipmentId
                JOIN Project p ON u.ProjectId = p.ProjectId
                ORDER BY u.Date DESC
            """, conn)
            df.rename(columns={"UsageId":"ID","Equipment":"Техника","Project":"Объект","Date":"Дата","HoursWorked":"Часы","FuelUsed":"Топливо (л)"}, inplace=True)
            st.dataframe(df, use_container_width=True)
            if st.button("📥 Экспорт использования техники в Excel", key="exp_equip_usage"):
                export_df_to_excel(df, "equipment_usage")

    elif choice == "📊 Аналитика":
        st.header("📊 Аналитика")
        mat_usage = pd.read_sql_query("""
            SELECT p.Name as Project, m.Name as Material, m.Unit, SUM(i.Quantity) as TotalUsed
            FROM MaterialIssue i
            JOIN Project p ON i.ProjectId = p.ProjectId
            JOIN Material m ON i.MaterialId = m.MaterialId
            GROUP BY p.Name, m.Name, m.Unit
        """, conn)
        if not mat_usage.empty:
            units = mat_usage["Unit"].unique()
            for unit in units:
                df_unit = mat_usage[mat_usage["Unit"] == unit]
                fig = px.bar(df_unit, x="Project", y="TotalUsed", color="Material",
                             title=f"Расход материалов (ед. изм.: {unit})",
                             labels={"TotalUsed": f"Количество, {unit}"})
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Нет данных о расходе материалов")
        equip_usage = pd.read_sql_query("""
            SELECT e.Name as Equipment, SUM(u.HoursWorked) as TotalHours
            FROM EquipmentUsage u
            JOIN Equipment e ON u.EquipmentId = e.EquipmentId
            GROUP BY e.Name
        """, conn)
        if not equip_usage.empty:
            fig2 = px.pie(equip_usage, names="Equipment", values="TotalHours", title="Загрузка техники (часы)")
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("Нет данных об использовании техники")
        contracts = pd.read_sql_query("""
            SELECT cust.Name as Customer, SUM(c.Amount) as TotalAmount
            FROM Contract c
            JOIN Customer cust ON c.CustomerId = cust.CustomerId
            GROUP BY cust.Name
        """, conn)
        if not contracts.empty:
            fig3 = px.bar(contracts, x="Customer", y="TotalAmount", title="Общая сумма договоров по заказчикам",
                          labels={"TotalAmount": "Сумма, руб"})
            st.plotly_chart(fig3, use_container_width=True)
        else:
            st.info("Нет данных о договорах")
        overdue = pd.read_sql_query("""
            SELECT p.Name as Project, w.Name as Stage, w.PlannedEnd
            FROM WorkStage w
            JOIN Project p ON w.ProjectId = p.ProjectId
            WHERE w.Status='planned' AND date(w.PlannedEnd) < date('now')
        """, conn)
        if not overdue.empty:
            st.subheader("⚠️ Просроченные этапы")
            st.dataframe(overdue, use_container_width=True)
            if st.button("📥 Экспорт просроченных этапов в Excel", key="exp_overdue"):
                export_df_to_excel(overdue, "overdue_stages")

    elif choice == "📑 Отчёты":
        st.header("📑 Отчёты")
        report_type = st.selectbox("Тип отчёта", [
            "Расход материалов по объекту",
            "Остатки материалов на складе",
            "Загрузка сотрудников по объектам",
            "Ход выполнения этапов работ по объекту",
            "Договоры по заказчикам",
            "Использование техники по объектам"
        ])
        if report_type == "Расход материалов по объекту":
            proj_dict = get_dict("Project","ProjectId","Name")
            proj_name = st.selectbox("Объект", list(proj_dict.keys()))
            if st.button("Показать"):
                df = pd.read_sql_query("""
                    SELECT i.Date, m.Name as Material, m.Unit, i.Quantity, i.Reason
                    FROM MaterialIssue i
                    JOIN Material m ON i.MaterialId = m.MaterialId
                    WHERE i.ProjectId = ?
                    ORDER BY i.Date
                """, conn, params=(proj_dict[proj_name],))
                df.rename(columns={"Date":"Дата","Material":"Материал","Unit":"Ед. изм.","Quantity":"Количество","Reason":"Основание"}, inplace=True)
                st.dataframe(df)
                if st.button("📥 Экспорт в Excel", key="exp_report_1"):
                    export_df_to_excel(df, f"report_material_issue_{proj_name}")
                if not df.empty:
                    fig = px.bar(df, x="Дата", y="Количество", color="Материал", title=f"Расход материалов на объекте {proj_name}", labels={"Количество": "Количество"})
                    st.plotly_chart(fig)
        elif report_type == "Остатки материалов на складе":
            df = pd.read_sql_query("""
                SELECT m.Name, m.Unit, s.Quantity
                FROM Stock s
                JOIN Material m ON s.MaterialId = m.MaterialId
                WHERE s.WarehouseId = 1
                ORDER BY m.Name
            """, conn)
            df.rename(columns={"Name":"Материал","Unit":"Ед. изм.","Quantity":"Остаток"}, inplace=True)
            st.dataframe(df)
            if st.button("📥 Экспорт в Excel", key="exp_report_2"):
                export_df_to_excel(df, "stock_balance")
        elif report_type == "Загрузка сотрудников по объектам":
            df = pd.read_sql_query("""
                SELECT e.FullName as Employee, p.Name as Project, a.Role, a.StartDate, a.EndDate
                FROM Assignment a
                JOIN Employee e ON a.EmployeeId = e.EmployeeId
                JOIN Project p ON a.ProjectId = p.ProjectId
                ORDER BY e.FullName
            """, conn)
            df.rename(columns={"Employee":"Сотрудник","Project":"Объект","Role":"Роль","StartDate":"Дата начала","EndDate":"Дата окончания"}, inplace=True)
            st.dataframe(df)
            if st.button("📥 Экспорт в Excel", key="exp_report_3"):
                export_df_to_excel(df, "employee_load")
        elif report_type == "Ход выполнения этапов работ по объекту":
            proj_dict = get_dict("Project","ProjectId","Name")
            proj_name = st.selectbox("Объект", list(proj_dict.keys()))
            df = pd.read_sql_query("""
                SELECT Name, PlannedStart, PlannedEnd, ActualStart, ActualEnd, Status,
                       CASE WHEN Status='planned' AND date('now') > PlannedEnd THEN 'Просрочен' ELSE '' END as Alert
                FROM WorkStage
                WHERE ProjectId = ?
                ORDER BY PlannedStart
            """, conn, params=(proj_dict[proj_name],))
            df.rename(columns={"Name":"Этап","PlannedStart":"План. начало","PlannedEnd":"План. окончание","ActualStart":"Факт. начало","ActualEnd":"Факт. окончание","Status":"Статус","Alert":"Предупреждение"}, inplace=True)
            st.dataframe(df)
            if st.button("📥 Экспорт в Excel", key="exp_report_4"):
                export_df_to_excel(df, f"work_stages_{proj_name}")
        elif report_type == "Договоры по заказчикам":
            df = pd.read_sql_query("""
                SELECT cust.Name as Customer, c.Number, c.DateSigned, p.Name as Project, c.Amount, c.Status
                FROM Contract c
                JOIN Customer cust ON c.CustomerId = cust.CustomerId
                LEFT JOIN Project p ON c.ProjectId = p.ProjectId
                ORDER BY cust.Name
            """, conn)
            st.dataframe(df)
            if st.button("📥 Экспорт в Excel", key="exp_report_5"):
                export_df_to_excel(df, "contracts_by_customer")
        elif report_type == "Использование техники по объектам":
            df = pd.read_sql_query("""
                SELECT p.Name as Project, e.Name as Equipment, SUM(u.HoursWorked) as TotalHours, SUM(u.FuelUsed) as TotalFuel
                FROM EquipmentUsage u
                JOIN Equipment e ON u.EquipmentId = e.EquipmentId
                JOIN Project p ON u.ProjectId = p.ProjectId
                GROUP BY p.Name, e.Name
            """, conn)
            df.rename(columns={"Project":"Объект","Equipment":"Техника","TotalHours":"Часы","TotalFuel":"Топливо (л)"}, inplace=True)
            st.dataframe(df)
            if st.button("📥 Экспорт в Excel", key="exp_report_6"):
                export_df_to_excel(df, "equipment_usage_by_project")

    elif choice == "💾 Резервное копирование":
        st.header("💾 Резервное копирование")
        if st.button("Скачать резервную копию базы данных"):
            try:
                with open(DB_NAME, "rb") as f:
                    db_bytes = f.read()
                st.download_button(
                    label="📥 Сохранить файл",
                    data=db_bytes,
                    file_name=f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db",
                    mime="application/octet-stream"
                )
            except Exception as e:
                st.error(f"Ошибка при чтении базы: {e}")

    elif choice == "⚙️ Генерация тестов":
        st.header("⚙️ Генерация тестовых данных")
        st.warning("Эта операция создаст 5000 записей в каждой из таблиц (проекты, поставки, расходы, назначения, этапы, договоры, использование техники). Существующие данные будут удалены. Процесс может занять несколько минут.")
        if st.button("Сгенерировать 5000 записей (удаляет старые данные)"):
            with st.spinner("Генерация данных... (до 2-3 минут)"):
                generate_bulk_data()
            st.toast("Генерация завершена. Страница будет обновлена.", icon="✅", duration=5000)
            time.sleep(2)
            st.rerun()

    conn.close()

if __name__ == "__main__":
    init_db()
    seed_data()
    main()
