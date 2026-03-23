-- Este script crea el rol anónimo requerido por PostgREST
-- Se ejecuta automáticamente al iniciar el contenedor de PostgreSQL

DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'postgrest_anon') THEN
    CREATE ROLE postgrest_anon NOLOGIN;
  END IF;
END
$$;

-- Dar permisos de lectura sobre tablas públicas al rol anónimo
-- (se amplía después de que Django cree las tablas con migrate)
GRANT USAGE ON SCHEMA public TO postgrest_anon;
