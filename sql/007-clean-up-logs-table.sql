ALTER TABLE public.referral_request_logs DROP COLUMN pseudonym;
ALTER TABLE public.referral_request_logs DROP COLUMN data_domain;

ALTER TABLE public.referral_request_logs ADD endpoint varchar NOT NULL;
ALTER TABLE public.referral_request_logs ADD request_type varchar NOT NULL;
ALTER TABLE public.referral_request_logs ADD payload JSON NOT NULL;