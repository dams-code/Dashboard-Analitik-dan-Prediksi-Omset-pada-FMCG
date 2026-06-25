import os
import pandas as pd
import numpy as np
import pyodbc
from dotenv import load_dotenv
from sklearn.linear_model import LinearRegression

load_dotenv(dotenv_path='../.env')

server = os.getenv("DB_SERVER", "localhost")
database = os.getenv("DB_NAME", "AnalitikFMCG_DB")
user = os.getenv("DB_USER")
password = os.getenv("DB_PASSWORD")

setKoneksi = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server};DATABASE={database};UID={user};PWD={password}"

try:
    conn = pyodbc.connect(setKoneksi)
    print(f"koneksi ke SQL Server berhasil")
except Exception as e:
    print(f"Koneksi database SQL Server gagal: {e}")
    exit()
    
queryRawData = "SELECT * FROM Staging_Raw_Penjualan"
df = pd.read_sql(queryRawData, conn)

if df.empty:
    print("Database staging tidak ada data baru, proses diberhentikan");
    exit()
    
print(f"Berhasil memperoleh data kotor, {len(df)} data kotor")   

df["Kuantitas"] = pd.to_numeric(df["Kuantitas"], errors='coerce')
df["Harga_Satuan"] = pd.to_numeric(df["Harga_Satuan"], errors='coerce')
df["Total_Pembayaran"] = pd.to_numeric(df["Total_Pembayaran"], errors='coerce')

df.dropna(subset=["Nama_Produk", "Total_Pembayaran"], how='all', inplace=True)

df.drop_duplicates(subset=['TransaksiID'], keep='first', inplace=True)

df["Nama_Produk"] = df["Nama_Produk"].str.upper().str.strip()

mapping_produk = {
    'INDOMIE GORNG': 'INDOMIE GORENG',
    'INDOMIE GOR.': 'INDOMIE GORENG',
    'TEH BOTOL SRO': 'TEH BOTOL SOSRO',
    'KOPI KAPAL API 20G': 'KOPI KAPAL API'
}

df["Nama_Produk"] = df["Nama_Produk"].replace(mapping_produk)

df["Tanggal"] = pd.to_datetime(df["Tanggal"], errors='coerce', dayfirst='True')
df["Tanggal"] = df["Tanggal"].fillna(pd.Timestamp('2026-05-01'))

df = df[(df["Kuantitas"] > 0) & (df["Kuantitas"] <= 500)]

df["Harga_Satuan"] = df["Harga_Satuan"].fillna(df["Total_Pembayaran"] / df["Kuantitas"])
df["Total_Pembayaran"] = df["Kuantitas"] * df["Harga_Satuan"]

df.dropna(subset=["Harga_Satuan", "Total_Pembayaran"], how='all', inplace=True)

X_train = df[["Kuantitas", "Harga_Satuan"]]
y_train = df[["Total_Pembayaran"]]

model_experimen = LinearRegression()

model_experimen.fit(X_train, y_train)

df["Prediksi_Omset_HariBerikutnya"] = model_experimen.predict(X_train) * 1.10

cursor = conn.cursor()

cursor.execute("TRUNCATE TABLE Fact_Clean_Penjualan")

for index, row in df.iterrows():
    cursor.execute("""
            INSERT INTO Fact_Clean_Penjualan 
            (TransaksiID, Tanggal, Nama_Sales, Nama_Produk, Kuantitas, Harga_Satuan, Total_Pembayaran, Prediksi_Omset_HariBerikutnya)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        row['TransaksiID'],
        row['Tanggal'].strftime('%Y-%m-%d'),
        row['Nama_Sales'],
        row["Nama_Produk"],
        int(row["Kuantitas"]),
        float(row['Harga_Satuan']),
        float(row['Total_Pembayaran']),
        float(row['Prediksi_Omset_HariBerikutnya'])
    )

conn.commit()
cursor.close()
print(f"Proses Cleaning selesai, Total {len(df)} data bersih")
print(f"Data hasil Proses Cleaning berhasil terinput kedalam Table Fact_Clean_Penjualan")

