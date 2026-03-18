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
   '10824 Erie Rd, Parrish, FL 34219',
   '(941) 776-0501',
   NULL);

INSERT OR IGNORE INTO suppliers (name, address, phone, website) VALUES
  ('J&P Tropicals',
   '7150 Hatton Ave, North Port, FL 34287',
   '(941) 426-1145',
   'https://jptropicals.com');

INSERT OR IGNORE INTO suppliers (name, address, phone, website) VALUES
  ('Ewing Outdoor Supply',
   '6235 McIntosh Road, Sarasota, FL 34238',
   '(941) 927-9530',
   'https://ewingoutdoorsupply.com');

INSERT OR IGNORE INTO suppliers (name, address, phone, website) VALUES
  ('SiteOne Landscape Supply',
   '6055 Clark Center Ave, Sarasota, FL 34238',
   '(941) 923-2517',
   'https://siteone.com');

INSERT OR IGNORE INTO suppliers (name, address, phone, website) VALUES
  ('Suncoast Hydroponics',
   '1208 53rd Ave E, Bradenton, FL 34203',
   '(941) 753-4769',
   'https://suncoasthydroponics.com');

INSERT OR IGNORE INTO suppliers (name, address, phone, website) VALUES
  ('Tractor Supply Co. — Sarasota',
   '7130 Fruitville Rd, Sarasota, FL 34240',
   '(941) 342-0955',
   'https://tractorsupply.com');

INSERT OR IGNORE INTO suppliers (name, address, phone, website) VALUES
  ('Myakka Ranch & Farm Supply',
   '36140 State Road 70 E, Myakka City, FL 34251',
   '(941) 322-1783',
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

INSERT OR IGNORE INTO suppliers (name, address, phone, website) VALUES
  ('Punta Gorda Nursery',
   '2011 Shreve St, Punta Gorda, FL 33950',
   '(941) 639-0200',
   NULL);

INSERT OR IGNORE INTO suppliers (name, address, phone, website) VALUES
  ('Green Thumb Nursery — Venice',
   '650 Center Rd, Venice, FL 34285',
   '(941) 484-4989',
   NULL);

INSERT OR IGNORE INTO suppliers (name, address, phone, website) VALUES
  ('Sarasota Farmers Market',
   '1 N Lemon Ave, Sarasota, FL 34236',
   '(941) 225-9256',
   'https://sarasotafarmersmarket.org');

INSERT OR IGNORE INTO suppliers (name, address, phone, website) VALUES
  ('Tropicana Nursery',
   '5610 Palmer Blvd, Sarasota, FL 34232',
   '(941) 371-2662',
   NULL);

INSERT OR IGNORE INTO suppliers (name, address, phone, website) VALUES
  ('Tropical Nursery of SW Florida',
   '3520 Placida Rd, Englewood, FL 34224',
   '(941) 698-0200',
   NULL);

INSERT OR IGNORE INTO suppliers (name, address, phone, website) VALUES
  ('Home Depot Garden Center — Sarasota',
   '4111 Cattlemen Rd, Sarasota, FL 34233',
   '(941) 377-1900',
   'https://homedepot.com');

INSERT OR IGNORE INTO suppliers (name, address, phone, website) VALUES
  ('Lowes Garden Center — Sarasota',
   '5750 Fruitville Rd, Sarasota, FL 34232',
   '(941) 961-6261',
   'https://lowes.com');

INSERT OR IGNORE INTO suppliers (name, address, phone, website) VALUES
  ('DG Ace Hardware',
   '1230 S Tamiami Trail, Osprey, FL 34229',
   '(941) 918-0001',
   NULL);

INSERT OR IGNORE INTO suppliers (name, address, phone, website) VALUES
  ('Venice Seed & Garden',
   '303 W Venice Ave, Venice, FL 34285',
   '(941) 485-3200',
   NULL);

INSERT OR IGNORE INTO suppliers (name, address, phone, website) VALUES
  ('Natives Nursery',
   '6959 Adastra Lane, Sarasota, FL 34241',
   '(941) 342-1566',
   'https://nativesflorida.com');
