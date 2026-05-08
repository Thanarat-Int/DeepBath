-- Synthetic demo customers + accounts
INSERT INTO customers (customer_id, full_name, monthly_income, risk_profile) VALUES
    ('C0001', 'ธนรัตน์ ทดสอบ',  50000, 'moderate'),
    ('C0002', 'สมชาย ใจดี',     85000, 'aggressive'),
    ('C0003', 'มาลี ขยัน',       30000, 'conservative')
ON CONFLICT DO NOTHING;

INSERT INTO accounts (account_id, customer_id, account_type, balance) VALUES
    ('A1001', 'C0001', 'savings',  125430.50),
    ('A1002', 'C0001', 'checking',  18200.00),
    ('A2001', 'C0002', 'savings',  840000.00),
    ('A3001', 'C0003', 'savings',   42500.75)
ON CONFLICT DO NOTHING;
