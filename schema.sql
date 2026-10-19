-- Reference schema (PostgreSQL). The app creates these tables automatically on first start,
-- so you only need this file for SQL practice or manual setup in Neon's SQL editor.
CREATE TABLE projects (
  id TEXT PRIMARY KEY, name TEXT NOT NULL, client TEXT, status TEXT NOT NULL DEFAULT 'Active');
CREATE TABLE packages (
  id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  name TEXT NOT NULL, budget DOUBLE PRECISION, ros TEXT);
CREATE TABLE suppliers (
  id TEXT PRIMARY KEY, package_id TEXT NOT NULL REFERENCES packages(id) ON DELETE CASCADE,
  name TEXT NOT NULL, tech TEXT NOT NULL, stage TEXT NOT NULL, total DOUBLE PRECISION,
  incoterm TEXT, payment TEXT, lead_weeks DOUBLE PRECISION, due TEXT, next_action TEXT,
  reason TEXT, updated_at TIMESTAMPTZ);
CREATE TABLE status_history (
  id SERIAL PRIMARY KEY, supplier_id TEXT NOT NULL REFERENCES suppliers(id) ON DELETE CASCADE,
  label TEXT NOT NULL, changed_at TIMESTAMPTZ);
CREATE TABLE notes (
  id TEXT PRIMARY KEY, package_id TEXT NOT NULL REFERENCES packages(id) ON DELETE CASCADE,
  supplier_id TEXT REFERENCES suppliers(id) ON DELETE CASCADE,
  body TEXT NOT NULL, created_at TIMESTAMPTZ);
CREATE INDEX ix_notes_package ON notes(package_id);
CREATE INDEX ix_packages_project ON packages(project_id);
CREATE INDEX ix_suppliers_package ON suppliers(package_id);

-- Example: best compliant bid and variance to budget per package
SELECT p.name AS project, k.name AS package, k.budget,
       MIN(s.total) FILTER (WHERE s.tech = 'Compliant') AS lowest_compliant,
       ROUND(100 * (MIN(s.total) FILTER (WHERE s.tech = 'Compliant') - k.budget) / NULLIF(k.budget, 0)) AS pct_vs_budget
FROM projects p JOIN packages k ON k.project_id = p.id LEFT JOIN suppliers s ON s.package_id = k.id
GROUP BY p.name, k.id ORDER BY p.name, k.name;
