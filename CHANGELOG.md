# Registro de cambios

## 2026-11-22

### Órdenes de trabajo
- Se amplió el flujo de Nueva Orden para buscar vehículos por chapa y asociar un cliente existente o registrar uno nuevo.
- Se preservan el cliente, el vehículo y la chapa seleccionados al volver de los formularios de registro.
- Se corrigió el bloqueo del envío causado por un campo de kilometraje obligatorio que permanecía oculto.
- Se registra el kilometraje de ingreso en cada orden y se actualiza la lectura actual del vehículo.

### Clientes y vehículos
- El dashboard ahora enlaza a los listados de Clientes y Vehículos, con búsqueda, modificación y eliminación.
- Se permite asociar un mismo vehículo con varios clientes y asociar vehículos existentes sin duplicarlos.
- Se protege el historial: los registros vinculados a órdenes no se pueden eliminar.
- La edición de vehículos conserva el kilometraje como lectura de ingreso, actualizado desde las órdenes.

### Base de datos
- Se agregaron migraciones automáticas para la relación entre clientes y vehículos y para guardar el kilometraje en las órdenes existentes.
