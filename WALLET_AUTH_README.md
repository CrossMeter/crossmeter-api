# Wallet-Based Authentication for PIaaS

This document describes the implementation of wallet-based authentication using dynamic.xyz for the PIaaS backend, including automatic user creation on wallet connect.

## Overview

The backend now supports a two-tier authentication system:
1. **User Creation**: Automatic user creation when wallet connects
2. **Vendor Profile**: Optional vendor profile creation linked to user
3. **Traditional Authentication**: Email + Password (still supported)

## New API Endpoints

### 1. Create User on Wallet Connect
```
POST /v1/users/create-on-wallet-connect
```

**Request Body:**
```json
{
  "wallet_address": "string"
}
```

**Expected Response:**
```json
{
  "user_id": "string",
  "wallet_address": "string",
  "created_at": "timestamp",
  "updated_at": "timestamp"
}
```

**Status Codes:**
- `201` - User created successfully
- `409` - User already exists with this wallet address
- `400` - Invalid wallet address

### 2. Check Vendor Status by Wallet Address
```
GET /v1/vendors/wallet/{walletAddress}
```

**Expected Response:**
```json
{
  "exists": true,
  "vendor": {
    "vendor_id": "string",
    "name": "string",
    "email": "string",
    "wallet_address": "string",
    "webhook_url": "string",
    "preferred_dest_chain_id": number,
    "enabled_source_chains": [number],
    "metadata": {
      "description": "string",
      "website": "string"
    }
  },
  "isComplete": boolean
}
```

**Status Codes:**
- `200` - Status check completed (vendor may or may not exist)

### 3. Create Vendor with Wallet
```
POST /v1/vendors/create-with-wallet
```

**Request Body:**
```json
{
  "name": "string",
  "email": "string",
  "wallet_address": "string",
  "webhook_url": "string",
  "preferred_dest_chain_id": number,
  "enabled_source_chains": [number],
  "metadata": {
    "description": "string",
    "website": "string"
  }
}
```

**Expected Response:**
```json
{
  "access_token": "string",
  "vendor_id": "string"
}
```

### 4. Wallet-based Login
```
POST /v1/auth/login/wallet
```

**Request Body:**
```json
{
  "walletAddress": "string",
  "signature": "string" // optional
}
```

**Expected Response:**
```json
{
  "access_token": "string",
  "vendor_id": "string"
}
```

## Database Changes

### Schema Updates
- **New Users Table**: Stores wallet addresses and user IDs
- **Updated Vendors Table**: 
  - Added `user_id` column linking to users table
  - Made `password_hash` optional for wallet-based authentication
  - Added unique constraint on `wallet_address`
- **Indexes**: Added indexes for wallet address lookups

### Migration
Run the migration script to update existing databases:
```sql
-- migrate_wallet_auth.sql
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    wallet_address TEXT UNIQUE NOT NULL CHECK (LENGTH(wallet_address) = 42),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

ALTER TABLE vendors ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES users(id) ON DELETE CASCADE;
ALTER TABLE vendors ALTER COLUMN password_hash DROP NOT NULL;
ALTER TABLE vendors ADD CONSTRAINT IF NOT EXISTS vendors_wallet_address_unique UNIQUE (wallet_address);
CREATE INDEX IF NOT EXISTS idx_vendors_wallet_address ON vendors(wallet_address);
CREATE INDEX IF NOT EXISTS idx_users_wallet_address ON users(wallet_address);
```

## Implementation Details

### New Schemas
- `UserCreate`: For creating users with wallet addresses
- `UserResponse`: For user responses
- `VendorStatusResponse`: For vendor status checks
- `WalletLoginRequest`: For wallet-based login requests
- `WalletAuthResponse`: For wallet-based auth responses
- `VendorCreateWithWallet`: For creating vendors without passwords

### New Service Methods
- `UserService.create_user()`: Create user with wallet address
- `UserService.get_user_by_wallet()`: Get user by wallet address
- `VendorService.get_vendor_status_by_wallet()`: Check vendor status
- `VendorService.create_vendor_with_wallet()`: Create vendor linked to user
- `AuthService.authenticate_vendor_by_wallet()`: Authenticate by wallet address

### Authentication Flow
1. **Wallet Connect**: Frontend connects wallet via dynamic.xyz
2. **User Creation**: Frontend calls `POST /v1/users/create-on-wallet-connect` to create user
3. **Status Check**: Frontend calls `GET /v1/vendors/wallet/{walletAddress}` to check vendor status
4. **Vendor Creation**: If no vendor exists, frontend calls `POST /v1/vendors/create-with-wallet` to create vendor profile
5. **Login**: If vendor exists, frontend calls `POST /v1/auth/login/wallet` to get access token
6. **Authentication**: Frontend uses JWT token for subsequent authenticated requests

## Testing

Run the test script to verify the implementation:
```bash
python test_user_system.py
```

## Security Considerations

1. **Wallet Address Validation**: All wallet addresses are validated to be 42 characters (0x + 40 hex chars)
2. **Unique Constraints**: Database enforces unique wallet addresses across users
3. **User-Vendor Relationship**: One user can have one vendor profile
4. **JWT Tokens**: Same JWT token system as traditional authentication
5. **Optional Signature**: Signature verification can be added later for additional security

## Frontend Integration

The frontend should implement this flow:

### 1. Wallet Connection
```javascript
// Connect wallet via dynamic.xyz
const walletAddress = await connectWallet();

// Create user automatically
const userResponse = await fetch('/v1/users/create-on-wallet-connect', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ wallet_address: walletAddress })
});

if (userResponse.status === 201) {
  const user = await userResponse.json();
  // User created successfully
} else if (userResponse.status === 409) {
  // User already exists - this is fine
}
```

### 2. Vendor Status Check
```javascript
// Check if vendor profile exists
const statusResponse = await fetch(`/v1/vendors/wallet/${walletAddress}`);
const status = await statusResponse.json();

if (status.exists && status.isComplete) {
  // Vendor exists and is complete - redirect to dashboard
  const loginResponse = await fetch('/v1/auth/login/wallet', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ walletAddress })
  });
  const auth = await loginResponse.json();
  // Store token and redirect to dashboard
} else {
  // No vendor profile or incomplete - redirect to vendor setup
  redirectToVendorSetup();
}
```

### 3. Vendor Profile Creation
```javascript
// Create vendor profile
const vendorResponse = await fetch('/v1/vendors/create-with-wallet', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(vendorData)
});

if (vendorResponse.status === 201) {
  const auth = await vendorResponse.json();
  // Store token and redirect to dashboard
}
```

## Backward Compatibility

- Traditional email/password authentication remains unchanged
- Existing vendors can continue using their current authentication method
- New vendors can choose either authentication method
- All existing API endpoints continue to work as before
- Legacy vendor lookup methods are maintained for compatibility
