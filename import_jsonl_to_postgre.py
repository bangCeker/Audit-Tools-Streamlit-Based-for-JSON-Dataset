import psycopg2
import json
import os
from pathlib import Path

# Konfigurasi database
DB_CONFIG = {
    'host': 'localhost',
    'database': 'mzone_dataset',  # Ganti dengan nama database Anda
    'user': 'mzone',            # Ganti dengan username PostgreSQL Anda
    'password': 'mzone_pass_change',        # Ganti dengan password Anda
    'port': 5433                        # Port default PostgreSQL
}

# Mapping file JSONL ke tabel database
FILE_TABLE_MAPPING = {
    'train.jsonl': 'dataset_train',
    'val.jsonl': 'dataset_val',
    'test.jsonl': 'dataset_test'
}

def connect_to_db():
    """Membuat koneksi ke database PostgreSQL"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        print("✅ Koneksi ke database berhasil!")
        return conn
    except Exception as e:
        print(f"❌ Error koneksi ke database: {e}")
        return None

def import_jsonl_to_table(conn, jsonl_file, table_name):
    """Import data dari file JSONL ke tabel PostgreSQL"""
    
    if not os.path.exists(jsonl_file):
        print(f"⚠️  File {jsonl_file} tidak ditemukan, dilewati...")
        return 0
    
    cur = conn.cursor()
    count = 0
    errors = 0
    
    print(f"\n📥 Importing {jsonl_file} ke tabel {table_name}...")
    
    try:
        with open(jsonl_file, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                try:
                    # Parse JSON dari setiap baris
                    data = json.loads(line.strip())
                    
                    # Insert data ke database
                    cur.execute("""
                        INSERT INTO {} (text, intent, urgency, events)
                        VALUES (%s, %s, %s, %s)
                    """.format(table_name), (
                        data.get('text', ''),
                        data.get('intent', ''),
                        data.get('urgency', ''),
                        data.get('events', [])
                    ))
                    
                    count += 1
                    
                    # Commit setiap 100 baris untuk performa
                    if count % 100 == 0:
                        conn.commit()
                        print(f"  ✓ {count} baris berhasil diimport...")
                        
                except json.JSONDecodeError as e:
                    print(f"  ⚠️  Error parsing JSON di baris {line_num}: {e}")
                    errors += 1
                except Exception as e:
                    print(f"  ⚠️  Error insert di baris {line_num}: {e}")
                    errors += 1
        
        # Commit sisa data
        conn.commit()
        cur.close()
        
        print(f"✅ Selesai! Total {count} baris berhasil diimport dari {jsonl_file}")
        if errors > 0:
            print(f"⚠️  {errors} baris gagal diimport")
        
        return count
        
    except Exception as e:
        print(f"❌ Error saat membaca file {jsonl_file}: {e}")
        conn.rollback()
        return 0

def main():
    """Fungsi utama untuk menjalankan import"""
    
    print("=" * 60)
    print("IMPORT DATA JSONL KE POSTGRESQL")
    print("=" * 60)
    
    # Koneksi ke database
    conn = connect_to_db()
    if not conn:
        print("\n❌ Tidak bisa melanjutkan tanpa koneksi database")
        return
    
    total_imported = 0
    
    # Import setiap file JSONL
    for jsonl_file, table_name in FILE_TABLE_MAPPING.items():
        imported = import_jsonl_to_table(conn, jsonl_file, table_name)
        total_imported += imported
    
    # Tutup koneksi
    conn.close()
    
    print("\n" + "=" * 60)
    print(f"🎉 IMPORT SELESAI! Total {total_imported} baris data berhasil diimport")
    print("=" * 60)

if __name__ == "__main__":
    main()