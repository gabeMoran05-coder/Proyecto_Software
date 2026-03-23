-- =============================================================
--  FARMACIA INCLUSIVA — Script de Base de Datos
--  Instituto Tecnológico de Colima
--  Autores: Ayala Reynoso, Morán Aréchiga, Rodríguez García
-- =============================================================

CREATE DATABASE IF NOT EXISTS farmacia_inclusiva
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE farmacia_inclusiva;

-- =============================================================
--  TIPOS DE DATOS USADOS:
--  INT          → números enteros (IDs, cantidades, contadores)
--  VARCHAR(n)   → texto de longitud variable hasta n caracteres
--  BOOLEAN      → verdadero o falso (TRUE / FALSE)
--  DATE         → solo fecha (YYYY-MM-DD)
--  DATETIME     → fecha y hora (YYYY-MM-DD HH:MM:SS)
--  DECIMAL(10,2)→ números con decimales exactos (ideal para dinero)
--  ENUM         → solo acepta los valores que tú defines
-- =============================================================

-- -------------------------------------------------------------
-- 1. MÉTODO DE PAGO
-- -------------------------------------------------------------
CREATE TABLE Metodo_pago (
    id_metPag       INT             NOT NULL AUTO_INCREMENT,
    nombre_metodo   VARCHAR(50)     NOT NULL,          -- ej: Efectivo, Tarjeta
    descripcion     VARCHAR(150)    DEFAULT NULL,
    PRIMARY KEY (id_metPag)
);

-- -------------------------------------------------------------
-- 2. USUARIO  (cajeros y administradores)
-- -------------------------------------------------------------
CREATE TABLE Usuario (
    id_usuario      INT             NOT NULL AUTO_INCREMENT,
    usuario         VARCHAR(60)     NOT NULL UNIQUE,   -- nombre de inicio de sesión
    rol             VARCHAR(30)     NOT NULL,          -- administrador o cajero
    fecha_creacion  DATE            DEFAULT NULL,
    ultima_conexion DATETIME        DEFAULT NULL,      -- fecha Y hora de último acceso
    nombre          VARCHAR(80)     NOT NULL,
    ap_pat          VARCHAR(60)     DEFAULT NULL,
    ap_mat          VARCHAR(60)     DEFAULT NULL,
    telefono        VARCHAR(15)     DEFAULT NULL,      -- VARCHAR porque puede tener +52, etc
    PRIMARY KEY (id_usuario)
);

-- -------------------------------------------------------------
-- 3. CLIENTE
-- -------------------------------------------------------------
CREATE TABLE cliente (
    id_cliente      INT             NOT NULL AUTO_INCREMENT,
    nombre          VARCHAR(80)     NOT NULL,
    ap_pat          VARCHAR(60)     DEFAULT NULL,
    ap_mat          VARCHAR(60)     DEFAULT NULL,
    fecha_registro  DATE            DEFAULT NULL,
    telefono        VARCHAR(15)     DEFAULT NULL,      -- para envío de WhatsApp
    PRIMARY KEY (id_cliente)
);

-- -------------------------------------------------------------
-- 4. PROVEEDOR
-- -------------------------------------------------------------
CREATE TABLE Proveedor (
    id_prov     INT             NOT NULL AUTO_INCREMENT,
    telefono    VARCHAR(15)     DEFAULT NULL,
    nombre      VARCHAR(100)    NOT NULL,
    correo      VARCHAR(100)    DEFAULT NULL,
    direccion   VARCHAR(200)    DEFAULT NULL,
    PRIMARY KEY (id_prov)
);

-- -------------------------------------------------------------
-- 5. LOTE
-- -------------------------------------------------------------
CREATE TABLE Lote (
    id_lote             INT             NOT NULL AUTO_INCREMENT,
    id_prov             INT             NOT NULL,
    numero_lote         VARCHAR(60)     NOT NULL,
    fecha_fabricacion   DATE            DEFAULT NULL,
    fecha_caducidad     DATE            DEFAULT NULL,
    fecha_ingreso       DATE            DEFAULT NULL,
    stock_actual        INT             DEFAULT 0,
    activo              BOOLEAN         DEFAULT TRUE,
    fecha_compra        DATE            DEFAULT NULL,
    precio_compra       DECIMAL(10,2)   DEFAULT NULL,  -- DECIMAL evita errores de redondeo
    precio_venta        DECIMAL(10,2)   DEFAULT NULL,
    PRIMARY KEY (id_lote),
    CONSTRAINT fk_lote_prov FOREIGN KEY (id_prov) REFERENCES Proveedor(id_prov)
);

-- -------------------------------------------------------------
-- 6. MEDICAMENTO
-- -------------------------------------------------------------
CREATE TABLE Medicamento (
    id_med              INT             NOT NULL AUTO_INCREMENT,
    id_lote             INT             NOT NULL,
    nombre              VARCHAR(120)    NOT NULL,
    presentacion        VARCHAR(80)     DEFAULT NULL,  -- tableta, jarabe, cápsula, etc.
    concentracion       VARCHAR(60)     DEFAULT NULL,  -- 500mg, 10ml, etc.
    requiere_receta     BOOLEAN         DEFAULT FALSE,
    fecha_registro      DATE            DEFAULT NULL,
    estado_colorimetria ENUM('verde','amarillo','rojo','sin_stock') DEFAULT 'sin_stock',
    PRIMARY KEY (id_med),
    CONSTRAINT fk_med_lote FOREIGN KEY (id_lote) REFERENCES Lote(id_lote)
);

-- -------------------------------------------------------------
-- 7. CODIGOS QR
-- -------------------------------------------------------------
CREATE TABLE Codigos_QR (
    id_QR               INT             NOT NULL AUTO_INCREMENT,
    id_medicamento      INT             NOT NULL,
    token               VARCHAR(64)     NOT NULL UNIQUE, -- código único de seguridad
    url_qr              VARCHAR(255)    NOT NULL,
    fecha_generacion    DATE            DEFAULT NULL,
    fecha_regeneracion  DATE            DEFAULT NULL,
    contador_escaneos   INT             DEFAULT 0,
    activo              BOOLEAN         DEFAULT TRUE,
    PRIMARY KEY (id_QR),
    CONSTRAINT fk_qr_med FOREIGN KEY (id_medicamento) REFERENCES Medicamento(id_med)
);

-- -------------------------------------------------------------
-- 8. VENTAS
-- -------------------------------------------------------------
CREATE TABLE Ventas (
    id_ventas   INT             NOT NULL AUTO_INCREMENT,
    id_usuario  INT             NOT NULL,
    id_metPag   INT             NOT NULL,
    id_cliente  INT             DEFAULT NULL,          -- opcional, venta sin cliente registrado
    fecha_venta DATETIME        DEFAULT NULL,          -- fecha Y hora exacta de la venta
    total_venta DECIMAL(10,2)   DEFAULT NULL,
    PRIMARY KEY (id_ventas),
    CONSTRAINT fk_ventas_usuario FOREIGN KEY (id_usuario) REFERENCES Usuario(id_usuario),
    CONSTRAINT fk_ventas_pago    FOREIGN KEY (id_metPag)  REFERENCES Metodo_pago(id_metPag),
    CONSTRAINT fk_ventas_cliente FOREIGN KEY (id_cliente) REFERENCES cliente(id_cliente)
);

-- -------------------------------------------------------------
-- 9. DETALLE VENTAS MEDICAMENTO
-- -------------------------------------------------------------
CREATE TABLE Detalle_ventas_medicamento (
    id_detalle      INT             NOT NULL AUTO_INCREMENT,
    id_ventas       INT             NOT NULL,
    id_medicamento  INT             NOT NULL,
    cantidad        INT             DEFAULT NULL,
    precio_unitario DECIMAL(10,2)   DEFAULT NULL,
    subtotal        DECIMAL(10,2)   DEFAULT NULL,
    PRIMARY KEY (id_detalle),
    CONSTRAINT fk_det_ventas FOREIGN KEY (id_ventas)      REFERENCES Ventas(id_ventas),
    CONSTRAINT fk_det_med    FOREIGN KEY (id_medicamento) REFERENCES Medicamento(id_med)
);

-- -------------------------------------------------------------
-- 10. NOTIFICACIÓN
-- -------------------------------------------------------------
CREATE TABLE Notificacion (
    id_notificacion INT             NOT NULL AUTO_INCREMENT,
    id_venta        INT             NOT NULL,
    mensaje_enviado VARCHAR(255)    DEFAULT NULL,
    PRIMARY KEY (id_notificacion),
    CONSTRAINT fk_notif_venta FOREIGN KEY (id_venta) REFERENCES Ventas(id_ventas)
);

-- =============================================================
--  VISTAS ÚTILES
-- =============================================================

-- Muestra el estado de colorimetría de cada medicamento
CREATE OR REPLACE VIEW vista_colorimetria AS
SELECT
    m.id_med,
    m.nombre,
    m.presentacion,
    m.concentracion,
    l.stock_actual,
    l.fecha_caducidad,
    CASE
        WHEN l.stock_actual = 0                                            THEN 'sin_stock'
        WHEN l.fecha_caducidad < CURDATE()                                 THEN 'rojo'
        WHEN l.fecha_caducidad <= DATE_ADD(CURDATE(), INTERVAL 90 DAY)     THEN 'amarillo'
        ELSE 'verde'
    END AS colorimetria
FROM Medicamento m
JOIN Lote l ON l.id_lote = m.id_lote;

-- Muestra medicamentos que ya caducaron pero aún tienen stock
CREATE OR REPLACE VIEW vista_caducados AS
SELECT
    m.nombre,
    m.presentacion,
    l.numero_lote,
    l.fecha_caducidad,
    l.stock_actual,
    p.nombre AS proveedor
FROM Medicamento m
JOIN Lote      l ON l.id_lote = m.id_lote
JOIN Proveedor p ON p.id_prov = l.id_prov
WHERE l.fecha_caducidad < CURDATE()
  AND l.stock_actual > 0
ORDER BY l.fecha_caducidad;

-- Muestra las ventas realizadas el día de hoy
CREATE OR REPLACE VIEW vista_ventas_hoy AS
SELECT
    v.id_ventas,
    v.fecha_venta,
    u.nombre         AS cajero,
    c.nombre         AS cliente,
    mp.nombre_metodo AS metodo_pago,
    v.total_venta
FROM Ventas v
JOIN Usuario     u  ON u.id_usuario = v.id_usuario
JOIN Metodo_pago mp ON mp.id_metPag = v.id_metPag
LEFT JOIN cliente c ON c.id_cliente = v.id_cliente
WHERE DATE(v.fecha_venta) = CURDATE()
ORDER BY v.id_ventas DESC;

-- =============================================================
--  TRIGGERS (acciones automáticas de la base de datos)
-- =============================================================

DELIMITER $$

-- Actualiza el color del semáforo cuando cambia el stock o caducidad de un lote
CREATE TRIGGER trg_actualizar_colorimetria
AFTER UPDATE ON Lote
FOR EACH ROW
BEGIN
    UPDATE Medicamento
    SET estado_colorimetria = CASE
        WHEN NEW.stock_actual = 0                                            THEN 'sin_stock'
        WHEN NEW.fecha_caducidad < CURDATE()                                 THEN 'rojo'
        WHEN NEW.fecha_caducidad <= DATE_ADD(CURDATE(), INTERVAL 90 DAY)     THEN 'amarillo'
        ELSE 'verde'
    END
    WHERE id_lote = NEW.id_lote;
END$$

-- Descuenta el stock automáticamente al registrar una venta
CREATE TRIGGER trg_descontar_stock
AFTER INSERT ON Detalle_ventas_medicamento
FOR EACH ROW
BEGIN
    UPDATE Lote l
    JOIN Medicamento m ON m.id_lote = l.id_lote
    SET l.stock_actual = l.stock_actual - NEW.cantidad
    WHERE m.id_med = NEW.id_medicamento;
END$$

DELIMITER ;

-- =============================================================
--  DATOS INICIALES
-- =============================================================

INSERT INTO Metodo_pago (nombre_metodo, descripcion) VALUES
    ('Efectivo',      'Pago en efectivo en caja'),
    ('Tarjeta',       'Tarjeta de débito o crédito'),
    ('Transferencia', 'Transferencia bancaria o SPEI');

INSERT INTO Usuario (usuario, rol, nombre, ap_pat) VALUES
    ('admin', 'administrador', 'Administrador', 'Gi');

