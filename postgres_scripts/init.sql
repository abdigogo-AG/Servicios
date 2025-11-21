-- Conectarse a la base de datos
\c registros;

-- ==========================================
-- 1. CATÁLOGOS (OFICIOS)
-- ==========================================
CREATE TABLE categorias_oficios (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(50) UNIQUE NOT NULL, -- 'Plomero', 'Electricista'
    icono_url TEXT 
);

-- Insertar los oficios básicos automáticamente
INSERT INTO categorias_oficios (nombre, icono_url) VALUES 
    ('Plomero', 'fas fa-wrench'), 
    ('Electricista', 'fas fa-bolt'), 
    ('Carpintero', 'fas fa-hammer'), 
    ('Jardinero', 'fas fa-leaf'), 
    ('Pintor', 'fas fa-paint-roller'), 
    ('Albañil', 'fas fa-trowel') 
ON CONFLICT DO NOTHING;

-- ==========================================
-- 2. USUARIOS (TABLA MADRE)
-- ==========================================
CREATE TABLE usuarios (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nombre VARCHAR(100) NOT NULL,
    apellidos VARCHAR(255) NOT NULL,
    correo_electronico VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    telefono VARCHAR(20) NOT NULL,
    fecha_nacimiento DATE, 
    foto_perfil_url TEXT,
    fecha_registro TIMESTAMPTZ DEFAULT NOW(),
    activo BOOLEAN DEFAULT TRUE,
    codigo_verificacion VARCHAR(6),

        -- PODERES DE ADMIN
    es_admin BOOLEAN DEFAULT FALSE,
    bloqueado_hasta TIMESTAMPTZ DEFAULT NULL -- Si tiene fecha futura, no puede entrar
);

-- ==========================================
-- 3. DETALLES DEL CLIENTE
-- ==========================================
CREATE TABLE detalles_cliente (
    usuario_id UUID PRIMARY KEY REFERENCES usuarios(id) ON DELETE CASCADE,
    calle VARCHAR(255),
    colonia VARCHAR(100),
    numero_exterior VARCHAR(20),
    numero_interior VARCHAR(20),
    referencias_domicilio TEXT,
    codigo_postal VARCHAR(10),
    ciudad VARCHAR(100),
    
    -- Coordenadas GPS
    latitud DECIMAL(9,6),
    longitud DECIMAL(9,6),
    
    id_cliente_pagos VARCHAR(100) 
);

-- ==========================================
-- 4. DETALLES DEL TRABAJADOR
-- ==========================================
CREATE TABLE detalles_trabajador (
    usuario_id UUID PRIMARY KEY REFERENCES usuarios(id) ON DELETE CASCADE,
    descripcion_bio TEXT,
    anios_experiencia INT,
    tarifa_hora_estimada DECIMAL(10,2),
    
    -- Documentación
    foto_ine_frente_url TEXT,
    foto_ine_reverso_url TEXT,
    antecedentes_penales_url TEXT,
    validado_por_admin BOOLEAN DEFAULT FALSE,
    
    -- Ubicación Base
    latitud DECIMAL(9,6),
    longitud DECIMAL(9,6),
    radio_cobertura_km INT DEFAULT 10,
    disponible BOOLEAN DEFAULT TRUE,
    
    -- Métricas
    calificacion_promedio DECIMAL(3, 2) DEFAULT 0, 
    total_evaluaciones INT DEFAULT 0
);

-- ==========================================
-- 5. RELACIÓN TRABAJADOR <-> OFICIOS
-- ==========================================
--Relacion de muchos a muchos
-- Esta tabla es vital para que un trabajador pueda ser "Plomero" Y "Electricista"
CREATE TABLE trabajador_oficios (
    usuario_id UUID REFERENCES detalles_trabajador(usuario_id) ON DELETE CASCADE,
    categoria_id INT REFERENCES categorias_oficios(id) ON DELETE CASCADE,
    PRIMARY KEY (usuario_id, categoria_id)
);

-- ==========================================
-- 6. ÍNDICES (OPTIMIZACIÓN)
-- ==========================================
CREATE INDEX IF NOT EXISTS idx_correo ON usuarios (correo_electronico);


-- Usuario: admin@sistema.com / Password: admin123(encriptado)
-- El hash es de 'admin123' generado con bcrypt









-- -- 5. Servicios (Depende de Clientes y Trabajadores)
-- CREATE TYPE estado_servicio AS ENUM (
--     'SOLICITADO', 'ACEPTADO', 'EN_CAMINO', 'EN_PROCESO', 'TERMINADO', 'CANCELADO'
-- );

-- CREATE TABLE servicios (
--     id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
--     cliente_id UUID REFERENCES detalles_cliente(usuario_id),
--     trabajador_id UUID REFERENCES detalles_trabajador(usuario_id),
--     categoria_id INT REFERENCES categorias_oficios(id),
    
--     descripcion_corta VARCHAR(255),
--     fecha_programada TIMESTAMPTZ,
--     precio_acordado DECIMAL(10,2),
--     estado estado_servicio DEFAULT 'SOLICITADO',
    
--     -- Snapshot de la dirección
--     direccion_servicio JSONB, 
    
--     created_at TIMESTAMPTZ DEFAULT NOW(),
--     updated_at TIMESTAMPTZ DEFAULT NOW()
-- );

-- -- 6. Evaluaciones (Depende de Servicios)
-- CREATE TABLE evaluaciones (
--     id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
--     servicio_id UUID REFERENCES servicios(id),
--     cliente_id UUID REFERENCES detalles_cliente(usuario_id),
--     trabajador_id UUID REFERENCES detalles_trabajador(usuario_id),
    
--     puntuacion INT NOT NULL CHECK (puntuacion >= 0 AND puntuacion <= 5),
--     comentario_corto VARCHAR(255),
    
--     created_at TIMESTAMPTZ DEFAULT NOW()
-- );

-- -- Índices
-- CREATE INDEX IF NOT EXISTS idx_correo ON usuarios (correo_electronico);
-- CREATE INDEX IF NOT EXISTS idx_trabajador_geo ON detalles_trabajador (latitud, longitud);

-- -- 7. Lógica del Trigger (Promedios)
-- CREATE OR REPLACE FUNCTION actualizar_promedio_trabajador()
-- RETURNS TRIGGER AS $$
-- BEGIN
--     UPDATE detalles_trabajador
--     SET 
--         calificacion_promedio = (
--             SELECT COALESCE(AVG(puntuacion), 0) -- COALESCE evita errores si es null
--             FROM evaluaciones 
--             WHERE trabajador_id = NEW.trabajador_id
--         ),
--         total_evaluaciones = (
--             SELECT COUNT(*) 
--             FROM evaluaciones 
--             WHERE trabajador_id = NEW.trabajador_id
--         )
--     WHERE usuario_id = NEW.trabajador_id;
    
--     RETURN NEW;
-- END;
-- $$ LANGUAGE plpgsql;

-- CREATE TRIGGER trigger_nueva_evaluacion
--AFTER INSERT ON evaluaciones
-- FOR EACH ROW
-- EXECUTE FUNCTION actualizar_promedio_trabajador();