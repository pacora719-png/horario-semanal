# Registro de Horario Semanal

App liviana y separada del ERP, pensada para que cualquier persona (por ejemplo
un encargado de turno) registre **solo la hora de entrada y salida** de cada
empleado, semana a semana — sin ver ni tocar nómina, sedes, inventario, etc.

Se conecta a la **misma base de datos PostgreSQL (Neon)** que usa el ERP
principal, así que todo lo que se registre aquí aparece automáticamente en
el ERP, en el módulo de Horas y Nómina.

## Qué hace

- Elegir un empleado activo (ya cargado en el ERP)
- Agregar un empleado nuevo (solo nombre y sede — el resto de sus datos
  como salario, cédula y afiliaciones se completan después en el ERP)
- Registrar entrada y salida de Lunes a Domingo de una semana, con un
  checkbox de "No trabajó" para los días libres
- Si ya existe un registro de ese día, lo actualiza en vez de duplicarlo

## Qué NO hace (a propósito)

Para mantenerla simple, esta app no incluye horas extra, recargos, tiempo a
descontar, bonificaciones ni deducciones — todo eso sigue completándose en
el ERP principal cuando se prepara la nómina. Aquí solo se busca precisión
en la hora de entrada y salida real de cada día.

## Cómo desplegarla

1. Sube esta carpeta a un **repositorio nuevo y separado** en GitHub (no lo
   mezcles con el repo del ERP)
2. Despliega en [Streamlit Cloud](https://streamlit.io/cloud) señalando
   `app.py`
3. En Settings → Secrets, pega el contenido de `secrets.toml.ejemplo`,
   usando la **misma** `database_url` que ya tienes configurada en el ERP
4. Si quieres pedir usuario/contraseña, deja la sección `[usuarios]`; si
   prefieres que quede abierta (por ejemplo en una tablet del negocio),
   bórrala por completo

## Nota

Como comparte base de datos con el ERP, no crea tablas nuevas — si la
tabla `empleados`, `ubicaciones` u `horas` no existen todavía (por ejemplo
si conectas esta app antes que el ERP alguna vez), esta app dará error al
guardar. Asegúrate de haber abierto el ERP principal al menos una vez
primero, para que la base de datos ya tenga su estructura creada.
