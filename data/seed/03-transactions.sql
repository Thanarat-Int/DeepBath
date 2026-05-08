-- 60 days of realistic synthetic transactions for customer C0001 (account A1002)
-- Categories cover the demo Q&A: "เดือนที่แล้วใช้กับอาหารเท่าไหร่?"
INSERT INTO transactions (account_id, txn_date, amount, category, merchant, description) VALUES
    -- Salary
    ('A1002', CURRENT_DATE - INTERVAL '5 days',  50000.00, 'salary',    'Acme Corp Payroll',        'เงินเดือน'),
    ('A1002', CURRENT_DATE - INTERVAL '35 days', 50000.00, 'salary',    'Acme Corp Payroll',        'เงินเดือน'),
    -- Food (last 30 days, ~12 entries totalling ~5,640)
    ('A1002', CURRENT_DATE - INTERVAL '1 day',    -180.00, 'food',      'After You',          'ของหวาน'),
    ('A1002', CURRENT_DATE - INTERVAL '3 days',   -420.00, 'food',      'MK Restaurant',      'มื้อเย็น'),
    ('A1002', CURRENT_DATE - INTERVAL '5 days',   -350.00, 'food',      'Starbucks',          'กาแฟ'),
    ('A1002', CURRENT_DATE - INTERVAL '7 days',   -680.00, 'food',      'Sushi Hiro',         'มื้อกลางวัน'),
    ('A1002', CURRENT_DATE - INTERVAL '10 days',  -250.00, 'food',      '7-Eleven',           'อาหารตามสั่ง'),
    ('A1002', CURRENT_DATE - INTERVAL '12 days',  -540.00, 'food',      'Shabu Sushi',        'มื้อเย็น'),
    ('A1002', CURRENT_DATE - INTERVAL '15 days',  -320.00, 'food',      'Foodland',           'ของกินติดบ้าน'),
    ('A1002', CURRENT_DATE - INTERVAL '18 days',  -780.00, 'food',      'Bonchon',            'ไก่ทอด'),
    ('A1002', CURRENT_DATE - INTERVAL '20 days',  -420.00, 'food',      'McDonald''s',        'มื้อเย็น'),
    ('A1002', CURRENT_DATE - INTERVAL '23 days',  -290.00, 'food',      'KFC',                'มื้อกลางวัน'),
    ('A1002', CURRENT_DATE - INTERVAL '25 days',  -450.00, 'food',      'Yayoi',              'มื้อเย็น'),
    ('A1002', CURRENT_DATE - INTERVAL '28 days',  -380.00, 'food',      'Cafe Amazon',        'กาแฟ + ขนม'),
    -- Transport
    ('A1002', CURRENT_DATE - INTERVAL '2 days',   -120.00, 'transport', 'BTS',                'รถไฟฟ้า'),
    ('A1002', CURRENT_DATE - INTERVAL '6 days',   -250.00, 'transport', 'Bolt',               'แท็กซี่'),
    ('A1002', CURRENT_DATE - INTERVAL '14 days',  -180.00, 'transport', 'BTS',                'รถไฟฟ้า'),
    ('A1002', CURRENT_DATE - INTERVAL '22 days',  -300.00, 'transport', 'Grab',               'แท็กซี่กลับบ้าน'),
    -- Shopping
    ('A1002', CURRENT_DATE - INTERVAL '8 days',  -2400.00, 'shopping',  'Uniqlo',             'เสื้อผ้า'),
    ('A1002', CURRENT_DATE - INTERVAL '17 days', -1200.00, 'shopping',  'Lazada',             'ของใช้ในบ้าน'),
    -- Bills
    ('A1002', CURRENT_DATE - INTERVAL '11 days', -1800.00, 'utility',   'MEA',                'ค่าไฟ'),
    ('A1002', CURRENT_DATE - INTERVAL '11 days',  -450.00, 'utility',   'MWA',                'ค่าน้ำ'),
    ('A1002', CURRENT_DATE - INTERVAL '13 days',  -899.00, 'utility',   'AIS',                'ค่ามือถือ'),
    -- Investment
    ('A1002', CURRENT_DATE - INTERVAL '4 days',  -5000.00, 'investment','Asia Asset Mgmt',    'ซื้อกองทุน SET50')
ON CONFLICT DO NOTHING;

-- Recompute checking-account balance from synthesized transactions
UPDATE accounts
SET    balance = COALESCE(
           (SELECT SUM(amount) FROM transactions WHERE account_id = accounts.account_id),
           balance
       )
WHERE  account_id = 'A1002';
