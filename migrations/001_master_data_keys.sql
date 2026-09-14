-- Run in ONE transaction with the old scraping worker stopped.
-- Reviewed source-backed choices from the 2026-09-12 master-data investigation.
-- Keep curated rows in place: do not DROP or recreate either master table.
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '30s';
LOCK TABLE master_data, master_data_float IN ACCESS EXCLUSIVE MODE;

CREATE TEMP TABLE reviewed_master_data ON COMMIT DROP AS
SELECT * FROM (VALUES
  ('DK0009409336', 'Jyske', 5.0, 30, 30),
  ('DK0009409419', 'Jyske', 5.0, 30, 10),
  ('DK0009410508', 'Jyske', 6.0, 30, 10),
  ('DK0009413601', 'Jyske', 4.0, 30, 10),
  ('DK0009414419', 'Jyske', 4.0, 30, 30),
  ('DK0009416547', 'Jyske', 3.5, 30, 10),
  ('DK0009420143', 'Jyske', 4.0, 30, 10),
  ('DK0009420226', 'Jyske', 4.0, 30, 30)
) AS reviewed(isin, institute, coupon_rate, years_to_maturity, max_interest_only_period);

DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM reviewed_master_data r WHERE NOT EXISTS (
      SELECT 1 FROM master_data m WHERE m.isin = r.isin AND m.institute = r.institute
        AND m.coupon_rate = r.coupon_rate AND m.years_to_maturity = r.years_to_maturity
        AND m.max_interest_only_period = r.max_interest_only_period
    )
  ) THEN
    RAISE EXCEPTION 'A reviewed row is missing or changed; review the migration before proceeding';
  END IF;
  IF EXISTS (
    SELECT 1 FROM master_data m JOIN reviewed_master_data r USING (isin)
    WHERE m.institute IS DISTINCT FROM r.institute OR m.coupon_rate IS DISTINCT FROM r.coupon_rate
      OR m.years_to_maturity IS NULL OR m.max_interest_only_period IS NULL
      OR (r.institute = 'Jyske' AND (m.years_to_maturity <> 30 OR m.max_interest_only_period NOT IN (0, r.max_interest_only_period)))
  ) THEN
    RAISE EXCEPTION 'Unexpected variant for a reviewed ISIN; refusing automatic cleanup';
  END IF;
END $$;

DELETE FROM master_data m USING reviewed_master_data r
WHERE m.isin = r.isin AND (
  m.years_to_maturity <> r.years_to_maturity OR m.max_interest_only_period <> r.max_interest_only_period
);
-- Remove exact copies only. Nordea's different loan terms remain separate rows.
-- Other conflicting Jyske ISINs make the unique index fail and roll back the migration.
DELETE FROM master_data m USING (
  SELECT ctid, row_number() OVER (
    PARTITION BY isin, institute, coupon_rate, years_to_maturity, max_interest_only_period ORDER BY ctid
  ) AS occurrence FROM master_data
) duplicate WHERE m.ctid = duplicate.ctid AND duplicate.occurrence > 1;

DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM master_data_float
    WHERE fixed_rate_period IS NULL OR max_interest_only_period IS NULL
      OR fixed_rate_period::numeric <= 0 OR fixed_rate_period::numeric <> trunc(fixed_rate_period::numeric)
      OR max_interest_only_period::numeric < 0 OR max_interest_only_period::numeric <> trunc(max_interest_only_period::numeric)
  ) THEN
    RAISE EXCEPTION 'Invalid floating master numeric values; refusing lossy conversion';
  END IF;
END $$;
ALTER TABLE master_data_float
  ALTER COLUMN fixed_rate_period TYPE bigint USING fixed_rate_period::numeric::bigint,
  ALTER COLUMN max_interest_only_period TYPE bigint USING max_interest_only_period::numeric::bigint;
DELETE FROM master_data_float m USING (
  SELECT ctid, row_number() OVER (
    PARTITION BY institute, fixed_rate_period, max_interest_only_period ORDER BY ctid
  ) AS occurrence FROM master_data_float
) duplicate WHERE m.ctid = duplicate.ctid AND duplicate.occurrence > 1;

ALTER TABLE master_data
  ALTER COLUMN isin SET NOT NULL,
  ALTER COLUMN institute SET NOT NULL,
  ALTER COLUMN years_to_maturity SET NOT NULL,
  ALTER COLUMN max_interest_only_period SET NOT NULL;
ALTER TABLE master_data_float
  ALTER COLUMN institute SET NOT NULL,
  ALTER COLUMN fixed_rate_period SET NOT NULL,
  ALTER COLUMN max_interest_only_period SET NOT NULL;
ALTER TABLE master_data ADD CONSTRAINT master_data_product_key
  UNIQUE (isin, years_to_maturity, max_interest_only_period);
CREATE UNIQUE INDEX master_data_jyske_isin_key ON master_data (isin) WHERE institute = 'Jyske';
ALTER TABLE master_data_float ADD CONSTRAINT master_data_float_product_key
  UNIQUE (institute, fixed_rate_period, max_interest_only_period);
