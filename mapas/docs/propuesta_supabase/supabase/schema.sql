-- Simple Oficios: additive migration on top of the tables already in the project
-- (profiles, mechanic_profiles, appointments). It creates nothing that exists and
-- drops nothing. Run in the Supabase SQL Editor; every statement is idempotent.
--
-- Assumed conventions (confirm with Jorge):
--   profiles.role              : 'client' | 'mechanic'
--   appointments.status        : 'pending' | 'approved' | 'rejected' | 'cancelled' | 'completed' | 'no_show'
--   appointments.mechanic_id   : the mechanic's user id (= mechanic_profiles.user_id)

-- profiles: private contact data -----------------------------------------------------
alter table public.profiles
  add column if not exists phone text;

-- mechanic_profiles: search and reputation fields ------------------------------------
alter table public.mechanic_profiles
  add column if not exists specialties text[] not null default '{}',
  add column if not exists lat double precision,
  add column if not exists lng double precision,
  add column if not exists place_id text,
  add column if not exists rating numeric(2, 1) check (rating between 0 and 5),
  add column if not exists review_count integer not null default 0,
  add column if not exists verified boolean not null default false,
  add column if not exists active boolean not null default true;

create unique index if not exists mechanic_profiles_place_id_key
  on public.mechanic_profiles (place_id) where place_id is not null;

-- appointments: triage data and the mechanic's answer --------------------------------
-- client_area is a coarse zone (alcaldia or colonia), never the exact location.
alter table public.appointments
  add column if not exists specialty text,
  add column if not exists urgency text check (urgency in ('low', 'medium', 'high')),
  add column if not exists client_area text,
  add column if not exists responded_at timestamptz;

-- The existing policies are for the "authenticated" role; make sure it has table access.
grant select, insert on public.appointments to authenticated;

-- Post-appointment report. One per side (client / mechanic) = double confirmation. ----
create table if not exists public.appointment_reports (
  id uuid primary key default gen_random_uuid(),
  appointment_id uuid not null references public.appointments(id) on delete cascade,
  author_id uuid not null references public.profiles(id) on delete cascade,
  author_role text not null check (author_role in ('client', 'mechanic')),
  attended boolean not null,
  amount_mxn numeric(10, 2) check (amount_mxn >= 0),
  satisfaction smallint check (satisfaction between 1 and 5),
  recommendation text,
  created_at timestamptz not null default now(),
  unique (appointment_id, author_role)
);

create index if not exists appointments_mechanic_status_idx
  on public.appointments (mechanic_id, status);
create index if not exists appointments_client_idx
  on public.appointments (client_id);

alter table public.appointment_reports enable row level security;

drop policy if exists reports_select on public.appointment_reports;
create policy reports_select on public.appointment_reports
  for select to authenticated using (
    exists (select 1 from public.appointments a
            where a.id = appointment_id
              and (a.client_id = auth.uid() or a.mechanic_id = auth.uid()))
  );

drop policy if exists reports_insert on public.appointment_reports;
create policy reports_insert on public.appointment_reports
  for insert to authenticated with check (
    author_id = auth.uid()
    and exists (select 1 from public.appointments a
                where a.id = appointment_id
                  and a.status in ('approved', 'completed')
                  and ((author_role = 'client' and a.client_id = auth.uid())
                    or (author_role = 'mechanic' and a.mechanic_id = auth.uid())))
  );

-- Functions --------------------------------------------------------------------------

-- The assigned mechanic approves or rejects a pending appointment.
-- There is no UPDATE policy on appointments, so this is the only way to change status.
create or replace function public.respond_appointment(p_appointment_id uuid, p_approve boolean)
returns public.appointments
language plpgsql
security definer
set search_path = public
as $$
declare
  a public.appointments;
begin
  update public.appointments
     set status = case when p_approve then 'approved' else 'rejected' end,
         responded_at = now()
   where id = p_appointment_id and mechanic_id = auth.uid() and status = 'pending'
   returning * into a;
  if a.id is null then
    raise exception 'appointment not found or not pending';
  end if;
  return a;
end;
$$;

revoke execute on function public.respond_appointment(uuid, boolean) from public, anon;
grant execute on function public.respond_appointment(uuid, boolean) to authenticated;

-- Search: quality gates, then Bayesian-weighted rating (prior 4.2, weight 50), ties by distance.
create or replace function public.search_mechanics(
  p_lat double precision,
  p_lng double precision,
  p_specialty text default null,
  p_radius_km double precision default 10,
  p_limit integer default 5,
  p_min_rating numeric default 4.0,
  p_min_reviews integer default 20
)
returns table (
  user_id uuid,
  shop_name text,
  specialties text[],
  distance_km double precision,
  rating numeric,
  review_count integer,
  score double precision
)
language sql
stable
set search_path = public
as $$
  with base as (
    select m.user_id, m.shop_name, m.specialties, m.rating, m.review_count,
           6371 * 2 * asin(sqrt(
             power(sin(radians(m.lat - p_lat) / 2), 2)
             + cos(radians(p_lat)) * cos(radians(m.lat))
               * power(sin(radians(m.lng - p_lng) / 2), 2)
           )) as d
      from public.mechanic_profiles m
     where m.active and m.verified
       and m.lat is not null and m.lng is not null
       and (p_specialty is null or p_specialty = any (m.specialties))
       and coalesce(m.rating, 0) >= p_min_rating
       and m.review_count >= p_min_reviews
  )
  select b.user_id, b.shop_name, b.specialties,
         round(b.d::numeric, 2)::double precision,
         b.rating, b.review_count,
         (b.review_count::double precision / (b.review_count + 50)) * b.rating
           + (50.0 / (b.review_count + 50)) * 4.2
    from base b
   where b.d <= p_radius_km
   order by 7 desc, 4 asc
   limit p_limit;
$$;

grant execute on function public.search_mechanics(
  double precision, double precision, text, double precision, integer, numeric, integer
) to authenticated;
