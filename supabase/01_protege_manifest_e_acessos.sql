-- =====================================================================
-- Protecao do Supabase dos apps (projeto jhkqfacpobwnirioskii)
--
-- 1) app_config (manifests de atualizacao: dimp_update_manifest,
--    wm_update_manifest): leitura continua publica (os apps leem com a
--    chave anon); gravar passa a exigir a chave secreta (service role).
--    Antes, qualquer pessoa com a chave anon (que esta dentro dos apps)
--    podia apontar o update para um instalador falso.
--
-- 2) solicitacoes_acesso: com a chave anon, direto na tabela, nao da mais
--    para aprovar/negar, trocar a maquina ou o app de um pedido, nem apagar
--    pedidos. Pedido novo sempre entra como 'pendente'.
--    Continua igual: o link de aprovar/negar do email (Edge Function
--    aprovar-acesso, que usa a chave secreta), o painel do Supabase, as
--    funcoes RPC (consultar_status_acesso, registrar_log_uso) e o pedido
--    de acesso feito pelos apps.
--
-- Como aplicar: Supabase > SQL Editor > New query > colar tudo > Run.
-- Para desfazer: 99_desfazer_protecao.sql
-- =====================================================================

begin;

-- ---------------------------------------------------------------------
-- 1) app_config
-- ---------------------------------------------------------------------
alter table public.app_config enable row level security;

-- Remove as policies atuais da tabela (alguma liberava escrita para anon)
do $$
declare p record;
begin
  for p in select policyname from pg_policies
           where schemaname = 'public' and tablename = 'app_config'
  loop
    execute format('drop policy %I on public.app_config', p.policyname);
  end loop;
end $$;

-- Leitura publica: os apps leem o manifest com a chave anon
create policy app_config_leitura_publica
  on public.app_config for select
  to anon, authenticated
  using (true);

-- Sem policy de escrita = anon/authenticated nao gravam. Reforco no privilegio:
revoke insert, update, delete, truncate on table public.app_config from anon, authenticated;
grant select on table public.app_config to anon, authenticated;

-- ---------------------------------------------------------------------
-- 2) solicitacoes_acesso
-- ---------------------------------------------------------------------
create or replace function public.protege_solicitacoes_acesso()
returns trigger
language plpgsql
set search_path = public, pg_temp
as $$
declare
  -- Restrito = chamada direta na tabela com a chave anon.
  -- Nao restringe: chave secreta (Edge Functions), painel do Supabase e
  -- funcoes RPC (request.path = /rpc/...).
  restrito boolean := current_user in ('anon', 'authenticated')
    and coalesce(current_setting('request.path', true), '') not like '/rpc/%';
begin
  if not restrito then
    return coalesce(new, old);
  end if;

  if tg_op = 'INSERT' then
    -- Pedido novo sempre entra como pendente, sem data de decisao
    new.status      := 'pendente';
    new.aprovado_em := null;
    new.negado_em   := null;
    return new;
  end if;

  if tg_op = 'UPDATE' then
    if new.app         is distinct from old.app
    or new.machine_id  is distinct from old.machine_id
    or new.aprovado_em is distinct from old.aprovado_em
    or new.negado_em   is distinct from old.negado_em
    or (new.status is distinct from old.status
        and not (new.status = 'pendente'
                 and coalesce(old.status, 'pendente') in ('pendente', 'negado')))
    then
      raise exception 'Somente o administrador pode aprovar ou negar acessos'
        using errcode = '42501';
    end if;
    return new;
  end if;

  -- DELETE
  raise exception 'Somente o administrador pode apagar pedidos de acesso'
    using errcode = '42501';
end;
$$;

drop trigger if exists protege_solicitacoes_acesso on public.solicitacoes_acesso;
create trigger protege_solicitacoes_acesso
  before insert or update or delete on public.solicitacoes_acesso
  for each row execute function public.protege_solicitacoes_acesso();

commit;

-- ---------------------------------------------------------------------
-- Conferencia (o resultado aparece embaixo do editor)
-- ---------------------------------------------------------------------
select 'app_config: RLS ligado' as item,
       (select relrowsecurity from pg_class where oid = 'public.app_config'::regclass)::text as valor
union all
select 'app_config: anon pode gravar?',
       (has_table_privilege('anon', 'public.app_config', 'INSERT')
        or has_table_privilege('anon', 'public.app_config', 'UPDATE')
        or has_table_privilege('anon', 'public.app_config', 'DELETE'))::text
union all
select 'app_config: policy ' || policyname::text, cmd::text || ' para ' || array_to_string(roles, ',')
  from pg_policies where schemaname = 'public' and tablename = 'app_config'
union all
select 'solicitacoes_acesso: RLS ligado',
       (select relrowsecurity from pg_class where oid = 'public.solicitacoes_acesso'::regclass)::text
union all
select 'solicitacoes_acesso: policy ' || policyname::text, cmd::text || ' para ' || array_to_string(roles, ',')
  from pg_policies where schemaname = 'public' and tablename = 'solicitacoes_acesso'
union all
select 'solicitacoes_acesso: trigger', tgname::text
  from pg_trigger
 where tgrelid = 'public.solicitacoes_acesso'::regclass and not tgisinternal;
