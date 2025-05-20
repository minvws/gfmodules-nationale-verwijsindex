CREATE TABLE ura_number_allowlist (
      ura_number CHAR(8) NOT NULL ,
      description VARCHAR(255),
      PRIMARY KEY (ura_number)
);

ALTER TABLE ura_number_allowlist OWNER TO localisation;
