-- Otorgar permisos SELECT, INSERT, UPDATE sobre tablas existentes
GRANT SELECT, INSERT, UPDATE, DELETE ON trades TO trading_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON signals TO trading_user;
GRANT USAGE, SELECT ON SEQUENCE trades_id_seq TO trading_user;
GRANT USAGE, SELECT ON SEQUENCE signals_id_seq TO trading_user;

-- Verificar permisos otorgados
SELECT grantee, privilege_type 
FROM information_schema.role_table_grants 
WHERE table_name='trades' AND grantee='trading_user';
