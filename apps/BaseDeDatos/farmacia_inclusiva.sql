-- =============================================================
--  FARMACIA INCLUSIVA — Script de Base de Datos (PostgreSQL)
--  Instituto Tecnológico de Colima
--  Autores: Ayala Reynoso, Morán Aréchiga, Rodríguez García
-- =============================================================

-- -------------------------------------------------------------
-- 1. MÉTODO DE PAGO
-- -------------------------------------------------------------
CREATE TABLE metodo_pago (
    id_metPag       SERIAL          NOT NULL,
    nombre_metodo   VARCHAR(50)     NOT NULL,
    descripcion     VARCHAR(150)    DEFAULT NULL,
    PRIMARY KEY (id_metPag)
);

-- -------------------------------------------------------------
-- 2. USUARIO
-- -------------------------------------------------------------
CREATE TABLE usuario (
    id_usuario      SERIAL          NOT NULL,
    usuario         VARCHAR(60)     NOT NULL UNIQUE,
    rol             VARCHAR(30)     NOT NULL,
    fecha_creacion  DATE            DEFAULT NULL,
    ultima_conexion TIMESTAMP       DEFAULT NULL,
    nombre          VARCHAR(80)     NOT NULL,
    ap_pat          VARCHAR(60)     DEFAULT NULL,
    ap_mat          VARCHAR(60)     DEFAULT NULL,
    telefono        VARCHAR(15)     DEFAULT NULL,
    PRIMARY KEY (id_usuario)
);

-- -------------------------------------------------------------
-- 3. CLIENTE
-- -------------------------------------------------------------
CREATE TABLE cliente (
    id_cliente      SERIAL          NOT NULL,
    nombre          VARCHAR(80)     NOT NULL,
    ap_pat          VARCHAR(60)     DEFAULT NULL,
    ap_mat          VARCHAR(60)     DEFAULT NULL,
    fecha_registro  DATE            DEFAULT NULL,
    telefono        VARCHAR(15)     DEFAULT NULL,
    PRIMARY KEY (id_cliente)
);

-- -------------------------------------------------------------
-- 4. PROVEEDOR
-- -------------------------------------------------------------
CREATE TABLE proveedor (
    id_prov     SERIAL          NOT NULL,
    telefono    VARCHAR(15)     DEFAULT NULL,
    nombre      VARCHAR(100)    NOT NULL,
    correo      VARCHAR(100)    DEFAULT NULL,
    direccion   VARCHAR(200)    DEFAULT NULL,
    PRIMARY KEY (id_prov)
);

-- -------------------------------------------------------------
-- 5. LOTE
-- -------------------------------------------------------------
CREATE TABLE lote (
    id_lote             SERIAL          NOT NULL,
    id_prov             INTEGER         NOT NULL,
    numero_lote         VARCHAR(60)     NOT NULL,
    fecha_fabricacion   DATE            DEFAULT NULL,
    fecha_caducidad     DATE            DEFAULT NULL,
    fecha_ingreso       DATE            DEFAULT NULL,
    stock_actual        INTEGER         DEFAULT 0,
    activo              BOOLEAN         DEFAULT TRUE,
    fecha_compra        DATE            DEFAULT NULL,
    precio_compra       NUMERIC(10,2)   DEFAULT NULL,
    precio_venta        NUMERIC(10,2)   DEFAULT NULL,
    PRIMARY KEY (id_lote),
    CONSTRAINT fk_lote_prov FOREIGN KEY (id_prov) REFERENCES proveedor(id_prov)
);

-- -------------------------------------------------------------
-- 6. MEDICAMENTO
-- -------------------------------------------------------------
CREATE TABLE medicamento (
    id_med              SERIAL          NOT NULL,
    id_lote             INTEGER         NOT NULL,
    nombre              VARCHAR(120)    NOT NULL,
    presentacion        VARCHAR(80)     DEFAULT NULL,
    concentracion       VARCHAR(60)     DEFAULT NULL,
    requiere_receta     BOOLEAN         DEFAULT FALSE,
    fecha_registro      DATE            DEFAULT NULL,
    estado_colorimetria VARCHAR(20)     DEFAULT 'sin_stock'
                        CHECK (estado_colorimetria IN ('verde','amarillo','rojo','sin_stock')),
    PRIMARY KEY (id_med),
    CONSTRAINT fk_med_lote FOREIGN KEY (id_lote) REFERENCES lote(id_lote)
);

-- -------------------------------------------------------------
-- 7. CODIGOS QR
-- -------------------------------------------------------------
CREATE TABLE codigos_qr (
    id_qr               SERIAL          NOT NULL,
    id_medicamento      INTEGER         NOT NULL,
    token               VARCHAR(64)     NOT NULL UNIQUE,
    url_qr              VARCHAR(255)    NOT NULL,
    fecha_generacion    DATE            DEFAULT NULL,
    fecha_regeneracion  DATE            DEFAULT NULL,
    contador_escaneos   INTEGER         DEFAULT 0,
    activo              BOOLEAN         DEFAULT TRUE,
    PRIMARY KEY (id_qr),
    CONSTRAINT fk_qr_med FOREIGN KEY (id_medicamento) REFERENCES medicamento(id_med)
);

-- -------------------------------------------------------------
-- 8. VENTAS
-- -------------------------------------------------------------
CREATE TABLE ventas (
    id_ventas   SERIAL          NOT NULL,
    id_usuario  INTEGER         NOT NULL,
    id_metPag   INTEGER         NOT NULL,
    id_cliente  INTEGER         DEFAULT NULL,
    fecha_venta TIMESTAMP       DEFAULT NULL,
    total_venta NUMERIC(10,2)   DEFAULT NULL,
    PRIMARY KEY (id_ventas),
    CONSTRAINT fk_ventas_usuario FOREIGN KEY (id_usuario) REFERENCES usuario(id_usuario),
    CONSTRAINT fk_ventas_pago    FOREIGN KEY (id_metPag)  REFERENCES metodo_pago(id_metPag),
    CONSTRAINT fk_ventas_cliente FOREIGN KEY (id_cliente) REFERENCES cliente(id_cliente)
);

-- -------------------------------------------------------------
-- 9. DETALLE VENTAS MEDICAMENTO
-- -------------------------------------------------------------
CREATE TABLE detalle_ventas_medicamento (
    id_detalle      SERIAL          NOT NULL,
    id_ventas       INTEGER         NOT NULL,
    id_medicamento  INTEGER         NOT NULL,
    cantidad        INTEGER         DEFAULT NULL,
    precio_unitario NUMERIC(10,2)   DEFAULT NULL,
    subtotal        NUMERIC(10,2)   DEFAULT NULL,
    PRIMARY KEY (id_detalle),
    CONSTRAINT fk_det_ventas FOREIGN KEY (id_ventas)      REFERENCES ventas(id_ventas),
    CONSTRAINT fk_det_med    FOREIGN KEY (id_medicamento) REFERENCES medicamento(id_med)
);

