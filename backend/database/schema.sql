CREATE TABLE public.users (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  username text NOT NULL UNIQUE,
  password text NOT NULL,
  email text NOT NULL UNIQUE,
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT users_pkey PRIMARY KEY (id)
);

CREATE TABLE public.textbooks (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  user_id uuid,
  title text NOT NULL,
  storage_path text NOT NULL,
  status text DEFAULT '''processing''::text'::text,
  file_size integer,
  page_count smallint,
  created_at timestamp with time zone DEFAULT now(),
  chunk_count integer,
  is_starred boolean NOT NULL DEFAULT true,
  source_filename text,
  file_hash text,
  CONSTRAINT textbooks_pkey PRIMARY KEY (id),
  CONSTRAINT textbooks_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id)
);

CREATE TABLE public.chapters (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  textbook_id uuid,
  title text,
  created_at timestamp with time zone DEFAULT now(),
  start_page smallint,
  end_page smallint,
  chunk_count integer DEFAULT 0,
  topics jsonb DEFAULT '[]'::jsonb,
  CONSTRAINT chapters_pkey PRIMARY KEY (id),
  CONSTRAINT chapters_textbook_id_fkey FOREIGN KEY (textbook_id) REFERENCES public.textbooks(id)
);

CREATE TABLE public.chunks (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  textbook_id uuid,
  chapter_id uuid,
  content text NOT NULL,
  page_number integer,
  index integer,
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT chunks_pkey PRIMARY KEY (id),
  CONSTRAINT chunks_textbook_id_fkey FOREIGN KEY (textbook_id) REFERENCES public.textbooks(id),
  CONSTRAINT chunks_chapter_id_fkey FOREIGN KEY (chapter_id) REFERENCES public.chapters(id)
);

CREATE TABLE public.generated_content (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  user_id uuid,
  textbook_id uuid,
  content_type text NOT NULL,
  content jsonb NOT NULL,
  created_at timestamp with time zone DEFAULT now(),
  chapter_id uuid,
  CONSTRAINT generated_content_pkey PRIMARY KEY (id),
  CONSTRAINT generated_content_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id),
  CONSTRAINT generated_content_textbook_id_fkey FOREIGN KEY (textbook_id) REFERENCES public.textbooks(id),
  CONSTRAINT generated_content_chapter_id_fkey FOREIGN KEY (chapter_id) REFERENCES public.chapters(id)
);

CREATE TABLE public.flashcard_sets (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL,
  textbook_id uuid,
  chapter_id uuid,
  title text NOT NULL,
  time_studied integer DEFAULT 0,
  last_studied timestamp with time zone,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT flashcard_sets_pkey PRIMARY KEY (id),
  CONSTRAINT flashcard_sets_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id),
  CONSTRAINT flashcard_sets_chapter_id_fkey FOREIGN KEY (chapter_id) REFERENCES public.chapters(id),
  CONSTRAINT flashcard_sets_textbook_id_fkey FOREIGN KEY (textbook_id) REFERENCES public.textbooks(id)
);

CREATE TABLE public.flashcards (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  flashcard_set_id uuid NOT NULL,
  front jsonb NOT NULL,
  back jsonb NOT NULL,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  citation text,
  difficulty_type text,
  CONSTRAINT flashcards_pkey PRIMARY KEY (id),
  CONSTRAINT flashcards_flashcard-set_fkey FOREIGN KEY (flashcard_set_id) REFERENCES public.flashcard_sets(id)
);

CREATE TABLE public.flashcard_sessions (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL,
  flashcard_set_id uuid,
  time_studied integer DEFAULT 0,
  studied_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT flashcard_sessions_pkey PRIMARY KEY (id),
  CONSTRAINT flashcard_session_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id),
  CONSTRAINT flashcard_session_flashcard_set_id_fkey FOREIGN KEY (flashcard_set_id) REFERENCES public.flashcard_sets(id)
);

CREATE TABLE public.quizzes (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL,
  textbook_id uuid NOT NULL,
  chapter_id uuid NOT NULL,
  title text NOT NULL,
  time_studied integer DEFAULT 0,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT quizzes_pkey PRIMARY KEY (id),
  CONSTRAINT quizzes_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id),
  CONSTRAINT quizzes_textbook_id_fkey FOREIGN KEY (textbook_id) REFERENCES public.textbooks(id),
  CONSTRAINT quizzes_chapter_id_fkey FOREIGN KEY (chapter_id) REFERENCES public.chapters(id)
);

CREATE TABLE public.quiz_questions (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  quiz_id uuid NOT NULL,
  question jsonb NOT NULL,
  difficulty_type text,
  choices jsonb NOT NULL,
  answer text NOT NULL,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  topic text,
  explanation text,
  citation text,
  CONSTRAINT quiz_questions_pkey PRIMARY KEY (id),
  CONSTRAINT quiz_questions_quiz_id_fkey FOREIGN KEY (quiz_id) REFERENCES public.quizzes(id)
);

CREATE TABLE public.quiz_attempts (
  id bigint GENERATED ALWAYS AS IDENTITY NOT NULL,
  user_id uuid NOT NULL,
  quiz_id uuid,
  answers jsonb,
  score integer,
  time_studied integer DEFAULT 0,
  completed_at timestamp with time zone NOT NULL DEFAULT now(),
  total_questions integer,
  CONSTRAINT quiz_attempts_pkey PRIMARY KEY (id),
  CONSTRAINT quiz_session_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id),
  CONSTRAINT quiz_session_quiz_id_fkey FOREIGN KEY (quiz_id) REFERENCES public.quizzes(id)
);

CREATE TABLE public.summaries (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL,
  textbook_id uuid NOT NULL,
  chapter_id uuid NOT NULL,
  title text NOT NULL,
  content jsonb NOT NULL,
  version smallint DEFAULT '1'::smallint,
  time_studied integer DEFAULT 0,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT summaries_pkey PRIMARY KEY (id),
  CONSTRAINT summaries_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id),
  CONSTRAINT summaries_textbook_id_fkey FOREIGN KEY (textbook_id) REFERENCES public.textbooks(id),
  CONSTRAINT summaries_chapter_id_fkey FOREIGN KEY (chapter_id) REFERENCES public.chapters(id)
);

CREATE TABLE public.summary_sessions (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL,
  summary_id uuid,
  time_studied integer DEFAULT 0,
  studied_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT summary_sessions_pkey PRIMARY KEY (id),
  CONSTRAINT summary_sessions_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id),
  CONSTRAINT summary_sessions_summary_id_fkey FOREIGN KEY (summary_id) REFERENCES public.summaries(id)
);

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
