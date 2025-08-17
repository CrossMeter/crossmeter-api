-- Migration script for wallet-based authentication and user management
-- Run this script on existing databases to support wallet-based auth and user creation

-- Create users table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    wallet_address TEXT UNIQUE NOT NULL CHECK (LENGTH(wallet_address) = 42),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Add user_id column to vendors table
ALTER TABLE vendors ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES users(id) ON DELETE CASCADE;

-- Make password_hash optional (if not already optional)
ALTER TABLE vendors ALTER COLUMN password_hash DROP NOT NULL;

-- Add unique constraint on wallet_address (if not exists)
ALTER TABLE vendors ADD CONSTRAINT IF NOT EXISTS vendors_wallet_address_unique UNIQUE (wallet_address);

-- Add indexes for wallet address lookups (if not exists)
CREATE INDEX IF NOT EXISTS idx_vendors_wallet_address ON vendors(wallet_address);
CREATE INDEX IF NOT EXISTS idx_users_wallet_address ON users(wallet_address);

-- Add updated_at trigger for users table
CREATE TRIGGER IF NOT EXISTS update_users_updated_at BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Enable RLS for users table
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
CREATE POLICY IF NOT EXISTS "Enable all operations for service role" ON users FOR ALL USING (auth.role() = 'service_role');

-- Add comment to explain the change
COMMENT ON COLUMN vendors.password_hash IS 'Optional password hash for traditional authentication. NULL for wallet-based authentication.';
COMMENT ON COLUMN vendors.user_id IS 'Reference to users table for wallet-based authentication.';
