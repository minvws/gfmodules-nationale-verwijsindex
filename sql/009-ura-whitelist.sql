CREATE TABLE ura_number_whitelist (
      ura_number VARCHAR(9) NOT NULL ,
      PRIMARY KEY (ura_number)
);

ALTER TABLE ura_number_whitelist OWNER TO localisation;
