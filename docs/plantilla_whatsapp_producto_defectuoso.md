# Plantilla WhatsApp: aviso_producto_defectuoso

Crear en Meta Business > Administrador de WhatsApp > Plantillas.

## Configuración sugerida

- Nombre: `aviso_producto_defectuoso`
- Categoria: `Utilidad`
- Idioma: `Español (México)` / codigo `es_MX`
- Encabezado: ninguno
- Pie de pagina: `Farmacia Inclusiva`

## Cuerpo

```text
Hola {{1}}, te contactamos de Farmacia Inclusiva por un aviso importante sobre un producto adquirido.

Medicamento: {{2}}
Lote: {{3}}
Venta: #{{4}}

Razón del contacto: {{5}}

Por precaución, no consumas el producto y comunícate con la farmacia para recibir indicaciones.
```

## Variables que envia el sistema

1. Nombre del cliente.
2. Nombre del medicamento.
3. Numero de lote.
4. Folio de venta.
5. Razón del contacto, por ejemplo `Defectuoso`, `Dañino o riesgoso`, `Caducado` o `Revisión preventiva del producto`.

## Variables de entorno

```env
WHATSAPP_RECALL_TEMPLATE_NAME=aviso_producto_defectuoso
WHATSAPP_RECALL_TEMPLATE_LANGUAGE=es_MX
WHATSAPP_BUSINESS_ACCOUNT_ID=
```

## Crear por API desde el proyecto

Cuando tengas `WHATSAPP_BUSINESS_ACCOUNT_ID` y un token con permisos de administracion de WhatsApp Business:

```bash
python manage.py crear_plantilla_aviso_producto_defectuoso
```

Despues de crearla, Meta debe aprobarla antes de que el boton "Enviar aviso" pueda usarla.
