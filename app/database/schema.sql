-- PIaaS Database Schema for Supabase
-- Payment Infrastructure as a Service

-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Vendors table
CREATE TABLE IF NOT EXISTS vendors (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    vendor_id TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    webhook_url TEXT,
    preferred_dest_chain_id INTEGER NOT NULL,
    enabled_source_chains INTEGER[] DEFAULT '{1,8453,84532,10,42161,137}',
    wallet_address TEXT NOT NULL CHECK (LENGTH(wallet_address) = 42),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Products table
CREATE TABLE IF NOT EXISTS products (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    product_id TEXT UNIQUE NOT NULL,
    vendor_id TEXT NOT NULL REFERENCES vendors(vendor_id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    description TEXT,
    product_type TEXT NOT NULL CHECK (product_type IN ('one_time', 'subscription', 'usage_based')),
    default_amount_usdc_minor BIGINT CHECK (default_amount_usdc_minor > 0),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Customers table
CREATE TABLE IF NOT EXISTS customers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id TEXT UNIQUE NOT NULL,
    email TEXT NOT NULL,
    name TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Payment intents table
CREATE TABLE IF NOT EXISTS payment_intents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    intent_id TEXT UNIQUE NOT NULL,
    vendor_id TEXT NOT NULL REFERENCES vendors(vendor_id) ON DELETE CASCADE,
    product_id TEXT NOT NULL REFERENCES products(product_id) ON DELETE CASCADE,
    customer_id TEXT REFERENCES customers(customer_id) ON DELETE SET NULL,
    customer_email TEXT,
    src_chain_id INTEGER NOT NULL,
    dest_chain_id INTEGER NOT NULL,
    amount_usdc_minor BIGINT NOT NULL CHECK (amount_usdc_minor > 0),
    status TEXT NOT NULL DEFAULT 'created' CHECK (status IN ('created', 'awaiting_user_tx', 'submitted', 'settled')),
    router_address TEXT NOT NULL,
    router_function TEXT NOT NULL,
    calldata_hex TEXT NOT NULL,
    src_tx_hash TEXT,
    dest_tx_hash TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Subscriptions table
CREATE TABLE IF NOT EXISTS subscriptions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    subscription_id TEXT UNIQUE NOT NULL,
    vendor_id TEXT NOT NULL REFERENCES vendors(vendor_id) ON DELETE CASCADE,
    product_id TEXT NOT NULL REFERENCES products(product_id) ON DELETE CASCADE,
    plan_id TEXT NOT NULL,
    customer_email TEXT NOT NULL,
    customer_id TEXT REFERENCES customers(customer_id) ON DELETE SET NULL,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'paused', 'cancelled', 'expired')),
    src_chain_id INTEGER NOT NULL,
    dest_chain_id INTEGER NOT NULL,
    billing_interval TEXT NOT NULL CHECK (billing_interval IN ('monthly', 'quarterly', 'yearly')),
    amount_usdc_minor BIGINT NOT NULL CHECK (amount_usdc_minor > 0),
    next_renewal_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Webhook events table (for tracking webhook deliveries)
CREATE TABLE IF NOT EXISTS webhook_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    vendor_id TEXT NOT NULL REFERENCES vendors(vendor_id) ON DELETE CASCADE,
    event_type TEXT NOT NULL,
    payload JSONB NOT NULL,
    webhook_url TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'sent', 'failed', 'expired')),
    attempts INTEGER DEFAULT 0,
    max_attempts INTEGER DEFAULT 3,
    next_retry_at TIMESTAMP WITH TIME ZONE,
    last_attempt_at TIMESTAMP WITH TIME ZONE,
    response_status INTEGER,
    response_body TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_payment_intents_vendor_id ON payment_intents(vendor_id);
CREATE INDEX IF NOT EXISTS idx_payment_intents_status ON payment_intents(status);
CREATE INDEX IF NOT EXISTS idx_payment_intents_created_at ON payment_intents(created_at);
CREATE INDEX IF NOT EXISTS idx_subscriptions_vendor_id ON subscriptions(vendor_id);
CREATE INDEX IF NOT EXISTS idx_subscriptions_next_renewal ON subscriptions(next_renewal_at) WHERE status = 'active';
CREATE INDEX IF NOT EXISTS idx_webhook_events_status ON webhook_events(status);
CREATE INDEX IF NOT EXISTS idx_webhook_events_next_retry ON webhook_events(next_retry_at) WHERE status = 'pending';

-- Updated at triggers
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_vendors_updated_at BEFORE UPDATE ON vendors FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_products_updated_at BEFORE UPDATE ON products FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_customers_updated_at BEFORE UPDATE ON customers FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_payment_intents_updated_at BEFORE UPDATE ON payment_intents FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_subscriptions_updated_at BEFORE UPDATE ON subscriptions FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_webhook_events_updated_at BEFORE UPDATE ON webhook_events FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Row Level Security (RLS) policies
ALTER TABLE vendors ENABLE ROW LEVEL SECURITY;
ALTER TABLE products ENABLE ROW LEVEL SECURITY;
ALTER TABLE customers ENABLE ROW LEVEL SECURITY;
ALTER TABLE payment_intents ENABLE ROW LEVEL SECURITY;
ALTER TABLE subscriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE webhook_events ENABLE ROW LEVEL SECURITY;

-- Basic RLS policies (can be customized based on authentication needs)
CREATE POLICY "Enable all operations for service role" ON vendors FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "Enable all operations for service role" ON products FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "Enable all operations for service role" ON customers FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "Enable all operations for service role" ON payment_intents FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "Enable all operations for service role" ON subscriptions FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "Enable all operations for service role" ON webhook_events FOR ALL USING (auth.role() = 'service_role');
