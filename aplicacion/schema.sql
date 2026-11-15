CREATE TABLE IF NOT EXISTS consentimientos (
    id SERIAL PRIMARY KEY,
    usuario_id INT NOT NULL,
    finalidad VARCHAR(100) NOT NULL,
    version_texto VARCHAR(50) NOT NULL,
    estado VARCHAR(20) NOT NULL DEFAULT 'otorgado',
    fecha_otorgamiento TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_revocacion TIMESTAMP NULL
);
