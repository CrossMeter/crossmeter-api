#!/usr/bin/env python3
"""
Script to create test data for PIaaS development.
Run this after setting up your Supabase database.
"""

import asyncio
import sys
import os


sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.utils.test_data import create_test_data, create_additional_test_vendors


async def main():
    """Create all test data."""
    print("🚀 Creating PIaaS test data...")
    print("="*50)
    
    # Create basic test data - test commits
    success = await create_test_data()
    
    if success:
        print("\n" + "="*50)
        print("Creating additional test vendors...")
        await create_additional_test_vendors()
        
        print("\n" + "="*50)
        print("🎉 All test data created successfully!")
        print("\nNext steps:")
        print("1. Start the server: python run.py")
        print("2. Visit http://localhost:8000/docs for API documentation")
        print("3. Test the payment intent creation with the example curl command above")
    else:
        print("\n❌ Failed to create test data. Check your Supabase connection.")
        print("Make sure you have:")
        print("1. Created a .env file with your Supabase credentials")
        print("2. Run the SQL schema in your Supabase dashboard")


if __name__ == "__main__":
    asyncio.run(main())
