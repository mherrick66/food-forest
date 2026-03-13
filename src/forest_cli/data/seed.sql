-- Categories
INSERT OR IGNORE INTO categories (name) VALUES ('plants');
INSERT OR IGNORE INTO categories (name) VALUES ('fruit_trees');
INSERT OR IGNORE INTO categories (name) VALUES ('irrigation');
INSERT OR IGNORE INTO categories (name) VALUES ('seeds');
INSERT OR IGNORE INTO categories (name) VALUES ('livestock');

-- Suppliers (INSERT OR IGNORE so seed.sql is idempotent)
INSERT OR IGNORE INTO suppliers (name, address, phone, website) VALUES
  ('Wilsons Nursery & Landscaping',
   '4218 Bee Ridge Rd, Sarasota, FL 34233',
   '(941) 378-0600',
   'https://wilsonsnursery.net');

INSERT OR IGNORE INTO suppliers (name, address, phone, website) VALUES
  ('Sweet Bay Nursery',
   '6831 Swift Rd, Sarasota, FL 34231',
   '(941) 923-6909',
   NULL);

INSERT OR IGNORE INTO suppliers (name, address, phone, website) VALUES
  ('J&P Tropicals',
   '7150 Hatton Ave, North Port, FL 34287',
   '(941) 426-1145',
   'https://jptropicals.com');

INSERT OR IGNORE INTO suppliers (name, address, phone, website) VALUES
  ('Ewing Irrigation & Landscape Supply',
   '1725 Cattlemen Rd, Sarasota, FL 34232',
   '(941) 371-3331',
   'https://ewing1.com');

INSERT OR IGNORE INTO suppliers (name, address, phone, website) VALUES
  ('SiteOne Landscape Supply',
   '8750 Fruitville Rd, Sarasota, FL 34240',
   '(941) 377-9922',
   'https://siteone.com');

INSERT OR IGNORE INTO suppliers (name, address, phone, website) VALUES
  ('Suncoast Hydroponics',
   '1208 53rd Ave E, Bradenton, FL 34203',
   '(941) 753-4769',
   'https://suncoasthydroponics.com');

INSERT OR IGNORE INTO suppliers (name, address, phone, website) VALUES
  ('Tractor Supply Co. — Sarasota',
   '6240 S Tamiami Trail, Sarasota, FL 34231',
   '(941) 923-1113',
   'https://tractorsupply.com');

INSERT OR IGNORE INTO suppliers (name, address, phone, website) VALUES
  ('Myakka City Feed & Farm Supply',
   '10900 State Road 70 E, Myakka City, FL 34251',
   '(941) 322-1500',
   NULL);

INSERT OR IGNORE INTO suppliers (name, address, phone, website) VALUES
  ('Sarasota County Extension Office',
   '6700 Clark Rd, Sarasota, FL 34241',
   '(941) 861-9900',
   'https://sfyl.ifas.ufl.edu/sarasota');

INSERT OR IGNORE INTO suppliers (name, address, phone, website) VALUES
  ('Southern States — Sarasota',
   '7281 Fruitville Rd, Sarasota, FL 34240',
   '(941) 371-2533',
   'https://southernstates.com');
