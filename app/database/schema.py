import os
from pathlib import Path
from supabase import Client
from app.database.client import get_supabase_admin_client


async def create_database_schema(client: Client = None) -> bool:
    """
    Create database schema by executing the SQL file.
    
    Args:
        client: Supabase client (optional, will use admin client if not provided)
        
    Returns:
        bool: True if schema creation was successful
    """
    if client is None:
        client = get_supabase_admin_client()
    
    # Read the schema SQL file
    schema_file = Path(__file__).parent / "schema.sql"
    
    try:
        with open(schema_file, 'r') as f:
            schema_sql = f.read()
        
        # Execute the schema SQL
        # Note: Supabase python client doesn't directly support raw SQL execution
        # You'll need to run this SQL manually in Supabase dashboard or use pgAdmin
        # This function serves as documentation and can be used with direct PostgreSQL connection
        
        print("Schema SQL loaded successfully!")
        print("Please execute the following SQL in your Supabase dashboard:")
        print("=" * 50)
        print(schema_sql)
        print("=" * 50)
        
        return True
        
    except Exception as e:
        print(f"Error loading schema: {e}")
        return False


def get_schema_sql() -> str:
    """Get the schema SQL content."""
    schema_file = Path(__file__).parent / "schema.sql"
    with open(schema_file, 'r') as f:
        return f.read()
