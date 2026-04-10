-- Supabase PostgreSQL schema

create table public.users (
  id uuid not null default gen_random_uuid (),
  username text not null,
  password text not null,
  email text not null,
  created_at timestamp with time zone null default now(),
  constraint users_pkey primary key (id),
  constraint users_email_key unique (email),
  constraint users_username_key unique (username)
) TABLESPACE pg_default;

create table public.textbooks (
  id uuid not null default gen_random_uuid (),
  user_id uuid null,
  title text not null,
  storage_path text not null,
  status text null default '''processing''::text'::text,
  file_size integer null,
  page_count smallint null,
  created_at timestamp with time zone null default now(),
  chunk_count integer null,
  constraint textbooks_pkey primary key (id),
  constraint textbooks_user_id_fkey foreign KEY (user_id) references users (id) on delete CASCADE
) TABLESPACE pg_default;

create table public.generated_content (
  id uuid not null default gen_random_uuid (),
  user_id uuid null,
  textbook_id uuid null,
  content_type text not null,
  content jsonb not null,
  created_at timestamp with time zone null default now(),
  constraint generated_content_pkey primary key (id),
  constraint generated_content_textbook_id_fkey foreign KEY (textbook_id) references textbooks (id) on delete CASCADE,
  constraint generated_content_user_id_fkey foreign KEY (user_id) references users (id) on delete CASCADE
) TABLESPACE pg_default;

create table public.chunks (
  id uuid not null default gen_random_uuid (),
  textbook_id uuid null,
  chapter_id uuid null,
  content text not null,
  page_number integer null,
  index integer null,
  created_at timestamp with time zone null default now(),
  constraint chunks_pkey primary key (id),
  constraint chunks_chapter_id_fkey foreign KEY (chapter_id) references chapters (id) on delete set null,
  constraint chunks_textbook_id_fkey foreign KEY (textbook_id) references textbooks (id) on delete CASCADE
) TABLESPACE pg_default;

create table public.chapters (
  id uuid not null default gen_random_uuid (),
  textbook_id uuid null,
  title text null,
  created_at timestamp with time zone null default now(),
  start_page smallint null,
  end_page smallint null,
  chunk_count integer null default 0,
  constraint chapters_pkey primary key (id),
  constraint chapters_textbook_id_fkey foreign KEY (textbook_id) references textbooks (id) on delete CASCADE
) TABLESPACE pg_default;

create table public.pretests (
  id uuid not null default gen_random_uuid(),
  textbook_id uuid null,
  chapter_id uuid null,
  chapter_title text not null,
  questions jsonb not null,
  status text null default 'ready',
  created_at timestamp null default now(),
  constraint pretests_pkey primary key (id),
  constraint pretests_textbook_id_fkey foreign key (textbook_id) references textbooks (id) on delete cascade,
  constraint pretests_chapter_id_fkey foreign key (chapter_id) references chapters (id) on delete cascade
) TABLESPACE pg_default;

create table public.pretest_attempts (
  id uuid not null default gen_random_uuid(),
  user_id uuid not null,
  textbook_id uuid not null,
  chapter_id uuid not null,
  pretest_id uuid not null,
  status text not null default 'in_progress',
  score integer null,
  total_questions integer not null,
  responses jsonb null,
  draft_answers jsonb null default '[]'::jsonb,
  current_question_index integer not null default 0,
  started_at timestamp with time zone null default now(),
  created_at timestamp with time zone null default now(),
  completed_at timestamp with time zone null,
  constraint pretest_attempts_pkey primary key (id),
  constraint pretest_attempts_user_id_fkey foreign key (user_id) references users (id) on delete cascade,
  constraint pretest_attempts_textbook_id_fkey foreign key (textbook_id) references textbooks (id) on delete cascade,
  constraint pretest_attempts_chapter_id_fkey foreign key (chapter_id) references chapters (id) on delete cascade,
  constraint pretest_attempts_pretest_id_fkey foreign key (pretest_id) references pretests (id) on delete cascade,
  constraint pretest_attempts_user_chapter_key unique (user_id, chapter_id)
) TABLESPACE pg_default;
