# test_db_connection.py
"""
Test script untuk verify database connection dan basic operations
Jalankan: python test_db_connection.py
"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import db_helper as db


def test_connection():
    """Test 1: Basic connection"""
    print("=" * 60)
    print("TEST 1: Database Connection")
    print("=" * 60)
    
    try:
        if db.test_connection():
            print("✅ Connection successful!")
            return True
        else:
            print("❌ Connection failed!")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_stats():
    """Test 2: Get dataset statistics"""
    print("\n" + "=" * 60)
    print("TEST 2: Dataset Statistics")
    print("=" * 60)
    
    for table in ['dataset_train', 'dataset_val', 'dataset_test']:
        print(f"\n📊 {table}:")
        stats = db.get_dataset_stats(table)
        if stats:
            print(f"  - Total records: {stats.get('total_records', 0)}")
            print(f"  - Unique intents: {stats.get('unique_intents', 0)}")
            print(f"  - Unique urgencies: {stats.get('unique_urgencies', 0)}")
            print(f"  - First record: {stats.get('first_record', 'N/A')}")
            print(f"  - Last record: {stats.get('last_record', 'N/A')}")
        else:
            print(f"  ⚠️  No data or error")


def test_insert():
    """Test 3: Insert sample data"""
    print("\n" + "=" * 60)
    print("TEST 3: Insert Sample Data")
    print("=" * 60)
    
    sample_data = {
        "text": "TEST: Emergency di tambang, ada pekerja terluka",
        "intent": "SOS",
        "urgency": "HIGH",
        "events": ["INJURY_MEDICAL"]
    }
    
    print("Inserting sample data to dataset_train...")
    print(f"  Text: {sample_data['text'][:50]}...")
    print(f"  Intent: {sample_data['intent']}")
    print(f"  Urgency: {sample_data['urgency']}")
    print(f"  Events: {sample_data['events']}")
    
    try:
        success = db.insert_dataset_row("dataset_train", sample_data)
        if success:
            print("✅ Insert successful!")
            return True
        else:
            print("❌ Insert failed!")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_query():
    """Test 4: Query data"""
    print("\n" + "=" * 60)
    print("TEST 4: Query Data")
    print("=" * 60)
    
    print("Querying dataset_train with intent='SOS', limit=5...")
    
    try:
        results = db.query_dataset(
            table_name="dataset_train",
            intent="SOS",
            limit=5
        )
        
        print(f"✅ Query returned {len(results)} rows")
        
        if results:
            print("\nSample results:")
            for i, row in enumerate(results[:3], 1):
                print(f"\n  Row {i}:")
                print(f"    ID: {row['id']}")
                print(f"    Text: {row['text'][:60]}...")
                print(f"    Intent: {row['intent']}")
                print(f"    Urgency: {row['urgency']}")
                print(f"    Events: {row['events']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_change_log():
    """Test 5: Check change log"""
    print("\n" + "=" * 60)
    print("TEST 5: Change Log")
    print("=" * 60)
    
    print("Logging a test change...")
    
    try:
        success = db.log_change(
            table_name="dataset_train",
            operation="TEST",
            record_id=None,
            old_data={"intent": "NON_SOS"},
            new_data={"intent": "SOS"},
            changed_by="test_script",
            description="This is a test log entry"
        )
        
        if success:
            print("✅ Change log successful!")
            return True
        else:
            print("❌ Change log failed!")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def main():
    print("\n" + "🚀" * 30)
    print("MZONE DATASET - DATABASE CONNECTION TEST")
    print("🚀" * 30 + "\n")
    
    # Run all tests
    results = []
    
    results.append(("Connection Test", test_connection()))
    
    if results[0][1]:  # Only continue if connection successful
        results.append(("Statistics Test", test_stats()))
        results.append(("Insert Test", test_insert()))
        results.append(("Query Test", test_query()))
        results.append(("Change Log Test", test_change_log()))
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    total = len(results)
    passed = sum(1 for _, p in results if p)
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Database is ready to use.")
        return 0
    else:
        print("\n⚠️  Some tests failed. Check configuration.")
        return 1


if __name__ == "__main__":
    try:
        exit_code = main()
        
        # Close connection pool
        print("\nClosing connection pool...")
        db.close_pool()
        print("✅ Done!")
        
        sys.exit(exit_code)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        db.close_pool()
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        db.close_pool()
        sys.exit(1)