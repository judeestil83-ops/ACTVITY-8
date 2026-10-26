create table if not exists public.profiles (
  id uuid primary key references auth.users (id) on delete cascade,
  display_name text not null
    check (char_length(display_name) between 2 and 24),
  created_at timestamptz not null default now()
);

create table if not exists public.messages (
  id bigint generated always as identity primary key,
  user_id uuid not null default auth.uid()
    references public.profiles (id) on delete cascade,
  content text not null
    check (char_length(content) between 1 and 500),
  created_at timestamptz not null default now()
);

create index if not exists messages_created_at_idx
  on public.messages (created_at desc);

create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
declare
  chosen text;
begin
  chosen := left(
    trim(coalesce(new.raw_user_meta_data ->> 'display_name', '')), 24
  );
  if char_length(chosen) < 2 then
    chosen := 'Student';
  end if;

  insert into public.profiles (id, display_name)
  values (new.id, chosen);
  return new;
end;
$$;

revoke execute on function public.handle_new_user()
  from public, anon, authenticated;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();

revoke all on public.profiles from anon, authenticated;
revoke all on public.messages from anon, authenticated;

grant select on public.profiles to authenticated;
grant select, insert, delete on public.messages to authenticated;

alter table public.profiles enable row level security;
alter table public.messages enable row level security;

drop policy if exists "Signed-in users can read profiles" on public.profiles;
create policy "Signed-in users can read profiles"
  on public.profiles for select
  to authenticated
  using (true);

drop policy if exists "Signed-in users can read messages" on public.messages;
create policy "Signed-in users can read messages"
  on public.messages for select
  to authenticated
  using (true);

drop policy if exists "Users can send messages as themselves"
  on public.messages;
create policy "Users can send messages as themselves"
  on public.messages for insert
  to authenticated
  with check (user_id = (select auth.uid()));

drop policy if exists "Users can delete their own messages"
  on public.messages;
create policy "Users can delete their own messages"
  on public.messages for delete
  to authenticated
  using (user_id = (select auth.uid()));

do $$
begin
  if not exists (
    select 1 from pg_publication_tables
    where pubname = 'supabase_realtime'
      and schemaname = 'public'
      and tablename = 'messages'
  ) then
    alter publication supabase_realtime add table public.messages;
  end if;
end
$$;
