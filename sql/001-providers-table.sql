CREATE TABLE providers (
      pseudonym VARCHAR(50) NOT NULL,
      provider_id VARCHAR(50) NOT NULL ,
      data_domain VARCHAR(100) NOT NULL,
      PRIMARY KEY (pseudonym, provider_id, data_domain)
);
