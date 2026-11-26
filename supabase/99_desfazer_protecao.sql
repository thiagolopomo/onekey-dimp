-- =====================================================================
-- DESFAZ 01_protege_manifest_e_acessos.sql (so em emergencia).
-- Volta ao comportamento anterior: a chave anon volta a conseguir gravar
-- em app_config e a mexer livremente em solicitacoes_acesso (a brecha
-- de seguranca volta junto).
-- =====================================================================

begin;

drop trigger if exists protege_solicitacoes_acesso on public.solicitacoes_acesso;
drop function if exists public.protege_solicitacoes_acesso();

drop policy if exists app_config_leitura_publica on public.app_config;
alter table public.app_config disable row level security;
grant insert, update, delete on table public.app_config to anon, authenticated;

commit;
