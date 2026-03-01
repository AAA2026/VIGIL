"""
Database Migration Scripts for Production

Run these to upgrade from dev (SQLite) to production (PostgreSQL)
or to apply optimizations to existing PostgreSQL deployments.
"""

from backend.db.session import db_session
from backend.db.models import Incident
from sqlalchemy import text

def migrate_create_production_indexes():
    """
    Create composite indexes for production performance.
    
    Safe to run multiple times (IF NOT EXISTS pattern).
    Estimated time: 5-30 seconds depending on table size.
    """
    with db_session() as s:
        try:
            # These match the Index definitions in models.py
            s.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_incident_dedup 
                ON incident (run_id, camera_id, type, timestamp DESC);
            """))
            
            s.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_incident_recent 
                ON incident (status, timestamp DESC);
            """))
            
            s.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_incident_camera_time 
                ON incident (camera_id, timestamp DESC);
            """))
            
            s.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_incident_type_time 
                ON incident (type, timestamp DESC);
            """))
            
            print("✅ All production indexes created/verified")
            return True
        except Exception as e:
            print(f"❌ Error creating indexes: {e}")
            return False


def analyze_table_statistics():
    """
    Update PostgreSQL table statistics for query optimizer.
    Must run after bulk imports or data changes.
    """
    with db_session() as s:
        try:
            s.execute(text("ANALYZE incident;"))
            s.execute(text("ANALYZE incident_action;"))
            s.execute(text("ANALYZE camera;"))
            print("✅ Table statistics updated")
            return True
        except Exception as e:
            print(f"⚠️  Could not ANALYZE (expected on SQLite): {e}")
            return False


def check_index_usage():
    """
    Report on index usage for optimization.
    PostgreSQL only.
    """
    with db_session() as s:
        try:
            result = s.execute(text("""
                SELECT 
                    schemaname,
                    tablename,
                    indexname,
                    idx_scan as scans,
                    idx_tup_read as tuples_read,
                    idx_tup_fetch as tuples_fetched,
                    pg_size_pretty(pg_relation_size(indexrelid)) as size
                FROM pg_stat_user_indexes
                WHERE tablename IN ('incident', 'incident_action')
                ORDER BY pg_relation_size(indexrelid) DESC;
            """))
            
            print("\n📊 Index Usage Statistics:")
            print("-" * 100)
            for row in result:
                print(f"{row}")
            print("-" * 100)
            
        except Exception as e:
            print(f"⚠️  Index stats not available (expected on SQLite): {e}")


def estimate_table_size():
    """
    Estimate incident table size for capacity planning.
    """
    with db_session() as s:
        try:
            # PostgreSQL way
            result = s.execute(text("""
                SELECT 
                    pg_size_pretty(pg_total_relation_size('incident')) as total_size,
                    pg_size_pretty(pg_relation_size('incident')) as table_size,
                    pg_size_pretty(pg_total_relation_size('incident') - pg_relation_size('incident')) as indexes_size,
                    COUNT(*) as row_count
                FROM incident;
            """)).first()
            
            if result:
                print(f"""
📦 Incident Table Size:
   Total:   {result[0]}
   Table:   {result[1]}
   Indexes: {result[2]}
   Rows:    {result[3]:,}
                """)
        except Exception as e:
            # SQLite way
            try:
                count = s.query(Incident).count()
                print(f"\n📦 Incident Table: {count:,} rows")
            except:
                print("Could not determine table size")


def reindex_production():
    """
    Rebuild all indexes to optimize performance.
    Should run during maintenance window (causes brief locks).
    PostgreSQL only.
    """
    with db_session() as s:
        try:
            print("⏳ Reindexing tables (this may take a minute)...")
            s.execute(text("REINDEX TABLE CONCURRENTLY incident;"))
            s.execute(text("REINDEX TABLE CONCURRENTLY incident_action;"))
            print("✅ Reindex completed")
            return True
        except Exception as e:
            print(f"❌ Reindex failed: {e}")
            return False


if __name__ == "__main__":
    import sys
    
    print("🔧 Vigil Database Migration Utility\n")
    
    if len(sys.argv) < 2:
        print("""
Usage: python -m backend.db.migrations <command>

Commands:
  create-indexes      Create production-optimized indexes
  analyze             Update query optimizer statistics
  check-indexes       Show index usage statistics
  table-size          Estimate table size and capacity
  reindex             Rebuild indexes (maintenance window)
  all                 Run all checks and optimizations
        """)
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "create-indexes":
        migrate_create_production_indexes()
    elif command == "analyze":
        analyze_table_statistics()
    elif command == "check-indexes":
        check_index_usage()
    elif command == "table-size":
        estimate_table_size()
    elif command == "reindex":
        reindex_production()
    elif command == "all":
        migrate_create_production_indexes()
        analyze_table_statistics()
        estimate_table_size()
        check_index_usage()
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
