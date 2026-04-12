from django.db import models


class Notificacion(models.Model):
    venta           = models.ForeignKey('ventas.Venta', on_delete=models.CASCADE, related_name='notificaciones')
    mensaje_enviado = models.TextField('Mensaje enviado')
    enviado         = models.BooleanField('Enviado', default=False)
    fecha_envio     = models.DateTimeField('Fecha de envío', null=True, blank=True)

    class Meta:
        verbose_name = 'Notificación'
        verbose_name_plural = 'Notificaciones'
        ordering = ['-fecha_envio']

    def __str__(self):
        return f"Notif. Venta #{self.venta_id} – {'Enviada' if self.enviado else 'Pendiente'}"
