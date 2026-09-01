CREATE TABLE IF NOT EXISTS projects (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS documents (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL,
  source_path TEXT NOT NULL,
  source_format TEXT NOT NULL,
  current_model_json TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY (project_id) REFERENCES projects(id)
);

CREATE TABLE IF NOT EXISTS tokens (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL,
  type TEXT NOT NULL,
  masked_value TEXT NOT NULL,
  original_value TEXT NOT NULL,
  normalized_value TEXT NOT NULL,
  metadata_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL,
  UNIQUE(project_id, type, normalized_value),
  UNIQUE(project_id, masked_value),
  FOREIGN KEY (project_id) REFERENCES projects(id)
);

CREATE TABLE IF NOT EXISTS token_locations (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  token_id TEXT NOT NULL,
  document_id TEXT NOT NULL,
  block_id TEXT NOT NULL,
  inline_index INTEGER,
  start_offset INTEGER,
  end_offset INTEGER,
  FOREIGN KEY (token_id) REFERENCES tokens(id),
  FOREIGN KEY (document_id) REFERENCES documents(id)
);

CREATE TABLE IF NOT EXISTS processing_reports (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  project_id TEXT NOT NULL,
  document_id TEXT NOT NULL,
  status TEXT NOT NULL,
  token_count INTEGER NOT NULL DEFAULT 0,
  type_stats_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL,
  FOREIGN KEY (project_id) REFERENCES projects(id),
  FOREIGN KEY (document_id) REFERENCES documents(id)
);
