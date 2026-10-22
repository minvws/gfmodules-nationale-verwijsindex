CREATE SCHEMA IF NOT EXISTS admin;

CREATE TABLE admin.organizations (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    name varchar NOT NULL,
    external_id varchar NOT NULL,
    created_at timestamp DEFAULT now() NOT NULL,
    modified_at timestamp,
    deleted_at timestamp,
    CONSTRAINT organizations_pkey PRIMARY KEY (id)
);
CREATE UNIQUE INDEX uq_organizations_external_id_active ON admin.organizations (external_id) WHERE deleted_at IS NULL;

CREATE TABLE admin.clients (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    organization_id uuid NOT NULL,
    name varchar(100) NOT NULL,
    description varchar(255),
    created_at timestamp DEFAULT now() NOT NULL,
    modified_at timestamp,
    deleted_at timestamp,
    CONSTRAINT clients_pkey PRIMARY KEY (id),
    CONSTRAINT clients_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES admin.organizations (id)
);

CREATE TABLE admin.certificates (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    organization_id uuid NOT NULL,
    organization_identifier varchar(100),
    domain varchar(100),
    created_at timestamp DEFAULT now() NOT NULL,
    modified_at timestamp,
    deleted_at timestamp,
    CONSTRAINT certificates_pkey PRIMARY KEY (id),
    CONSTRAINT fk_certificates_organizations FOREIGN KEY (organization_id) REFERENCES admin.organizations (id)
);
CREATE UNIQUE INDEX uq_organization_id_organization_identifier_domain ON admin.certificates (organization_id, organization_identifier, domain) WHERE deleted_at IS NULL;

CREATE TABLE admin.sources (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    organization_id uuid NOT NULL,
    source_id varchar(100) NOT NULL,
    name varchar(150) NOT NULL,
    created_at timestamp DEFAULT now() NOT NULL,
    modified_at timestamp,
    deleted_at timestamp,
    CONSTRAINT sources_pkey PRIMARY KEY (id),
    CONSTRAINT fk_sources_organizations FOREIGN KEY (organization_id) REFERENCES admin.organizations (id)
);
CREATE UNIQUE INDEX uq_sources_source_id_active ON admin.sources (organization_id, source_id) WHERE deleted_at IS NULL;

CREATE TABLE admin.scopes (
    id integer GENERATED ALWAYS AS IDENTITY,
    name varchar(50),
    created_at timestamp DEFAULT now() NOT NULL,
    CONSTRAINT scopes_pkey PRIMARY KEY (id),
    CONSTRAINT scopes_name_key UNIQUE (name)
);

INSERT INTO admin.scopes (name) VALUES
    ('CREATE'),
    ('DELETE'),
    ('READ'),
    ('LOCALIZE');

CREATE TABLE admin.organizations_scopes (
    organization_id uuid NOT NULL,
    scope_id integer NOT NULL,
    created_at timestamp DEFAULT now() NOT NULL,
    CONSTRAINT pk_organizations_scopes PRIMARY KEY (organization_id, scope_id),
    CONSTRAINT fk_organization_scopes_organization FOREIGN KEY (organization_id) REFERENCES admin.organizations (id) ON DELETE CASCADE,
    CONSTRAINT fk_organization_scopes_scopes FOREIGN KEY (scope_id) REFERENCES admin.scopes (id)
);

CREATE TABLE admin.clients_scopes (
    client_id uuid NOT NULL,
    organization_id uuid NOT NULL,
    scope_id integer NOT NULL,
    created_at timestamp DEFAULT now() NOT NULL,
    CONSTRAINT pk_clients_scopes PRIMARY KEY (client_id, organization_id, scope_id),
    CONSTRAINT fk_clients_scopes_clients FOREIGN KEY (client_id) REFERENCES admin.clients (id) ON DELETE CASCADE,
    CONSTRAINT fk_clients_scopes_scopes FOREIGN KEY (organization_id, scope_id) REFERENCES admin.organizations_scopes (organization_id, scope_id)
);

CREATE TABLE admin.clients_certificates (
    client_id uuid NOT NULL,
    certificate_id uuid NOT NULL,
    created_at timestamp DEFAULT now() NOT NULL,
    CONSTRAINT pk_clients_certificates PRIMARY KEY (client_id, certificate_id),
    CONSTRAINT fk_clients_certificates_clients FOREIGN KEY (client_id) REFERENCES admin.clients (id) ON DELETE CASCADE,
    CONSTRAINT fk_clients_certificates_certificates FOREIGN KEY (certificate_id) REFERENCES admin.certificates (id) ON DELETE CASCADE
);

CREATE TABLE admin.clients_sources (
    client_id uuid NOT NULL,
    source_id uuid NOT NULL,
    CONSTRAINT pk_sources_clients PRIMARY KEY (source_id, client_id),
    CONSTRAINT fk_clients_sources_clients FOREIGN KEY (client_id) REFERENCES admin.clients (id) ON DELETE CASCADE,
    CONSTRAINT fk_clients_sources_sources FOREIGN KEY (source_id) REFERENCES admin.sources (id) ON DELETE CASCADE
);
