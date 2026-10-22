**🌍 Sprache · Language · Taal · Langue · Idioma**

| 🇩🇪 [Deutsch](README.md) | 🇬🇧 [English](README.en.md) | 🇳🇱 [Nederlands](README.nl.md) | 🇫🇷 [Français](README.fr.md) | 🇪🇸 **Español** |
|:---:|:---:|:---:|:---:|:---:|

# FRITZ!Box Netzwerk

Una integración de Home Assistant que muestra todos los dispositivos de la red doméstica de la FRITZ!Box en tu panel como una tabla ordenable – con dirección IP, dirección MAC, tipo de conexión y el nombre del dispositivo de Home Assistant correspondiente.

![Version](https://img.shields.io/badge/Version-2.0.0b5-blue)
![HACS](https://img.shields.io/badge/HACS-Custom-orange)

> Esta es la edición en español del README, disponible en cinco idiomas (consulta la barra de idiomas de arriba). El [README.md](README.md) alemán es el archivo principal y contiene la referencia completa de la tarjeta, el capítulo de solución de problemas y el historial completo de versiones. Las secciones marcadas «solo en alemán» aún no están traducidas. La integración y la tarjeta están traducidas al alemán, inglés y neerlandés.

---

## Contenido

- [Funciones](#funciones)
- [Requisitos](#requisitos)
- [Instalación](#instalación)
- [Configuración inicial](#configuración-inicial)
- [Ajustes](#ajustes)
- [Sensores](#sensores)
- [Eventos](#eventos)
- [Mesh y repetidores](#mesh-y-repetidores)
- [Filtro MAC y emparejamiento](#filtro-mac-y-emparejamiento)
- [Control parental: perfiles de acceso (experimental)](#control-parental-perfiles-de-acceso-experimental)
- [CPU y RAM de la caja (experimental)](#cpu-y-ram-de-la-caja-experimental)
- [Ajustes DNS (experimental)](#ajustes-dns-experimental)
- [Dirección IP estática (experimental)](#dirección-ip-estática-experimental)
- [Centro de notificaciones (opcional)](#centro-de-notificaciones-opcional)
- [La tarjeta del panel](#la-tarjeta-del-panel)
- [Servicios](#servicios)
- [Blueprints](#blueprints)
- [Indicación de versión y aviso de actualización](#indicación-de-versión-y-aviso-de-actualización)
- [Idiomas](#idiomas)
- [Seguridad](#seguridad)
- [Limitaciones conocidas](#limitaciones-conocidas)
- [Solución de problemas](#solución-de-problemas)
- [Integridad de los archivos](#integridad-de-los-archivos)
- [Desarrollo y pruebas](#desarrollo-y-pruebas)
- [Historial de versiones](#historial-de-versiones)
- [Licencia](#licencia)

---

## Funciones

- Todos los dispositivos de red conocidos de la FRITZ!Box en **una** tabla en el panel
- **Ordenable** haciendo clic en cualquier encabezado de columna, también con el teclado; **búsqueda** por nombre, IP, MAC, modelo y nombre de Home Assistant
- **Barra de filtros**: Todos, Activos, Inactivos, Invitados, Bloqueados, Actualización, IP fija, VPN – cada botón se puede ocultar por separado
- **Banda Wi-Fi** (2,4 / 5 GHz), **fabricante según la dirección MAC** (lista incluida, sin acceso a Internet), **copiar la MAC con un clic**
- **Filtro IP con comodines** (`192.168.2.*`) para repartir una red grande en varias tarjetas
- **Ventana de detalles** por dispositivo con todos los campos, Wake-on-LAN, cambio de nombre, etiqueta/nota/marca «reservado» y salto al dispositivo de Home Assistant
- **Última vez visto**, **interruptor de acceso a Internet** (experimental), **tipo de IP** (fija o dinámica)
- **Sensores de conexión** (velocidad de subida/bajada, velocidades de sincronización de la línea, IP externa, tiempo en línea, estado de la conexión) y **eventos** («dispositivo nuevo», «IP externa cambiada»)
- **Grupo Mesh**: FRITZ!Box y repetidores como una unidad, botón «Reiniciar todos los dispositivos FRITZ!»
- **Filtro MAC Wi-Fi** activado/desactivado y liberación temporal («emparejamiento»)
- **Control parental** (experimental): cambiar perfiles de acceso por dispositivo, también de forma temporal
- **Ajustes DNS** de la caja (experimental, desde 1.8.0): lectura y modificación
- **Dirección IP estática** por dispositivo (experimental, desde 1.8.0): asignación con comprobación de direcciones duplicadas, botón en la ventana de detalles; la vía de escritura se rehízo en 2.0.0 (interfaz REST, comprobación por relectura)
- **Reservas de la caja** (desde 2.0.0, sin probar en una caja): los dispositivos con «Asignar siempre la misma dirección IPv4 a este dispositivo de red» se leen de la caja y se cuentan como fijos
- **Dispositivos VPN** (desde 2.0.0, sin probar en una caja): los pares que la caja notifica con el indicador VPN pero sin dirección MAC (p. ej. WireGuard) ya no desaparecen de la lista; el botón de filtro **VPN** (`filter_vpn: false` lo oculta) muestra solo estos dispositivos
- **Indicación de versión y aviso de actualización** en la página de control de la tarjeta
- Totalmente configurable desde la interfaz, incluidos **colores libres**, tres idiomas (de, en, nl)

La tarjeta se entrega con la integración y se registra automáticamente como recurso de Lovelace.

---

## Requisitos

- Home Assistant 2024.11 o posterior
- Una FRITZ!Box con **«Permitir el acceso para aplicaciones»** activado (Red doméstica → Red → Ajustes de red)
- Un usuario de la FRITZ!Box con el permiso **«Ajustes de la FRITZ!Box»**

---

## Instalación

### Mediante HACS (recomendado)

1. HACS → Integraciones → menú arriba a la derecha → **Repositorios personalizados**
2. Añadir `https://github.com/Meine-smarte-Welt/fritzbox_netzwerk` como categoría *Integración*
3. Instalar «FRITZ!Box Netzwerk»
4. Reiniciar Home Assistant

**Versiones preliminares (beta, release candidate):** HACS solo las muestra si activas **«Mostrar versiones beta»** al descargar. Con una beta instalada, la indicación de versión de la tarjeta también avisa de betas más recientes.

### Manualmente

Copia la carpeta `custom_components/fritzbox_netzwerk` en el directorio `config` de Home Assistant y reinicia.

---

## Configuración inicial

Ajustes → Dispositivos y servicios → **Añadir integración** → «FRITZ!Box Netzwerk».

| Campo | Significado |
| --- | --- |
| Dirección | Nombre de host o dirección IP, normalmente `fritz.box` |
| Nombre de usuario | Usuario de la FRITZ!Box con el permiso «Ajustes de la FRITZ!Box» |
| Contraseña | La contraseña correspondiente |
| Conexión cifrada | HTTPS en lugar de HTTP hacia la FRITZ!Box |
| Puerto | `0` usa los puertos predeterminados; o introduce uno propio |
| Acceso remoto mediante MyFRITZ!/HTTPS | Usa HTTPS y el prefijo de ruta TR-064 `/tr064` |

Las credenciales se comprueban de inmediato (accesible, inicio de sesión válido, servicio de hosts utilizable). Si algo falla, el diálogo indica la causa concreta.

Para el acceso remoto introduce la dirección de MyFRITZ! o DynDNS **sin protocolo, puerto ni ruta**, indica el puerto HTTPS por separado y activa «Acceso remoto mediante MyFRITZ!/HTTPS». **Atención:** `fritzconnection` no verifica el certificado TLS; por Internet abierto, una VPN hacia tu propia FRITZ!Box es la opción más segura (detalles en el README alemán).

---

## Ajustes

Mediante *Configurar* en la integración:

| Ajuste | Valor por defecto | Significado |
| --- | --- | --- |
| Intervalo de consulta | 60 s | Con qué frecuencia se obtiene la lista de dispositivos (30–3600 s) |
| Registrar el tipo de IP | activado | Si se determina DHCP/estática |
| Intervalo del tipo de IP | 15 min | Ciclo de la recogida del tipo de IP |
| Registrar la banda Wi-Fi por dispositivo | activado | Lee los dispositivos conectados por red Wi-Fi para que la tarjeta muestre la banda |
| Crear rastreadores de dispositivos | desactivado | Un `device_tracker` por dispositivo de red |
| Crear repetidores como dispositivos propios | activado | Un dispositivo de Home Assistant por repetidor AVM, sensor mesh, botón «reiniciar todo» |
| Control de la FRITZ!Box (experimental) | desactivado | Interruptor Wi-Fi, interruptor del filtro MAC, botón de emparejamiento, botones de reconexión/reinicio |
| Servicio Wi-Fi de invitados (desde 1.9.1) | Automático | Número (1–4) del servicio Wi-Fi de la caja que es la red de invitados. «Automático» lo detecta solo; cámbialo únicamente si el interruptor de invitados o el código QR muestran la red equivocada |
| Comprobar a diario si hay una versión nueva | activado | Consulta GitHub una vez al día por la última versión; no se envían datos sobre ti ni sobre la caja |
| Controlar los perfiles de acceso del control parental (experimental) | desactivado | Activa los servicios y la selección de perfil en la ventana de detalles |
| Cambiar los ajustes DNS de la caja (experimental) | desactivado | Permite que `set_dns_settings` escriba; la lectura y la vista previa siempre funcionan |
| Establecer dirección IP estática (experimental) | desactivado | Permite que `set_static_ip` y el botón de la tarjeta escriban; la vista previa (`dry_run`) siempre funciona |
| Leer CPU y RAM de la caja (experimental) | desactivado | Tres sensores de la interfaz web de la caja |
| Crear dispositivos de red como dispositivos propios | desactivado | Un dispositivo HA por dispositivo seleccionado, elegido por patrón |
| Enviar mensajes al centro de notificaciones (desde 1.9.2b1) | activado | Interruptor principal de la conexión opcional, véase [Centro de notificaciones](#centro-de-notificaciones-opcional) |
| Tipos de mensaje a enviar (desde 1.9.2b1) | todos | Qué tipos de mensaje van al centro de notificaciones (conexión perdida, dispositivo vigilado sin conexión, dispositivo nuevo) |
| Duración del emparejamiento | 5 min | Cuánto tiempo permanece desactivado el filtro MAC durante el emparejamiento (1–120 min) |

---

## Sensores

| Sensor | Estado | Utilidad |
| --- | --- | --- |
| `sensor.<name>_gerate` | Número de dispositivos conectados | Lleva la lista completa de dispositivos en el atributo `hosts`; fuente de datos de la tarjeta |
| `sensor.<name>_gerate_mit_update` | Cantidad | Automatización «nuevo firmware disponible» |
| `sensor.<name>_gesperrte_gerate` | Cantidad | Supervisión del control parental |
| `sensor.<name>_download` / `_upload` | kB/s | Velocidad de transferencia actual |
| `sensor.<name>_mesh` | Cantidad en línea | Dispositivos FRITZ! accesibles (caja + repetidores); solo con repetidores |
| `sensor.<name>_download_leitungsrate` / `_upload_leitungsrate` | Mbit/s | Velocidad máxima de sincronización de la línea |
| `sensor.<name>_externe_ip` | Dirección IPv4 | IP pública actual |
| `sensor.<name>_online_seit` | Marca de tiempo | Desde cuándo está activa la conexión |
| `binary_sensor.<name>_internet_verbunden` | Conectado/No conectado | ¿Está la caja en línea? |

Si falta el servicio WAN (p. ej. la caja funciona solo como punto de acceso), estos sensores quedan «desconocido» sin afectar a la lista de dispositivos. El atributo `hosts` está excluido del recorder.

## Eventos

Desde 1.6.2: «dispositivo nuevo» en su primera aparición en la red doméstica e «IP externa cambiada», utilizables en automatizaciones sin llamadas TR-064 adicionales.

---

## Mesh y repetidores

La FRITZ!Box y sus repetidores AVM forman el mesh. La integración los trata como **un solo grupo**: los repetidores aparecen como dispositivos propios bajo la caja, hay un contador en línea y el botón «Reiniciar todos los dispositivos FRITZ!» (primero los repetidores, la caja al final). Desde 1.6.3 la tarjeta muestra en «Conectado a través de» a qué vecino mesh está unido un dispositivo, con la velocidad del enlace. Sin intensidad de señal en dBm (la lista mesh no la ofrece). Desde 1.9.0 un dispositivo también se trata como repetidor si la topología mesh de la caja lo lista como miembro del mesh, la banda Wi-Fi de los dispositivos detrás de un repetidor se lee del nombre de la interfaz mesh (dos suposiciones sin probar en hardware real), a los repetidores que solo tienen contraseña (sin nombre de usuario) se les reintenta con un nombre de usuario vacío, y la lista puede agruparse por conexión mesh (`group_by: mesh`). Detalles: README alemán.

## Filtro MAC y emparejamiento

Con *Control de la FRITZ!Box* activado obtienes `switch.<name>_mac_filter` (activado/desactivado de forma permanente) y `button.<name>_pairing_starten` (desactiva el filtro durante el tiempo configurado y lo **vuelve a activar automáticamente**). Los servicios `set_mac_filter` y `start_pairing` hacen lo mismo desde automatizaciones. Experimental.

## Control parental: perfiles de acceso (experimental)

La integración **cambia entre perfiles de acceso existentes** (Internet → Filtros → Perfiles de acceso); los sigues creando y editando en la FRITZ!Box. Activa la opción y usa la fila **Perfil de acceso** en la ventana de detalles o los servicios `list_access_profiles`, `get_access_profile`, `set_access_profile`. Con un número de minutos, el perfil se aplica solo ese tiempo y después se restablece el anterior. La fila puede ocultarse con `show_parental: false`. Usa la interfaz web no documentada, no TR-064.

## CPU y RAM de la caja (experimental)

La opción «Leer CPU y RAM de la caja (experimental)» (desactivada por defecto) crea tres sensores: carga de CPU, carga de RAM, temperatura de la CPU. Proceden de la página `ecoStat` de la interfaz web, no de TR-064; sin verificar en ninguna caja – compáralos con Sistema → Monitor de energía.

---

## Consumo de datos por dispositivo (experimental, desde 2.0.0b2)

Opción «Registrar el consumo de datos (experimental)» (desactivada por defecto). Responde a **qué dispositivo transfirió cuántos datos durante la última semana**, para encontrar dispositivos que hablan demasiado con Internet o saturan el Wi-Fi (petición de #26).

**Cómo funciona:** TR-064 no ofrece cifras de consumo por dispositivo. Por eso la integración lee el **monitor en línea** de la caja (interfaz web, API REST no documentada `api/v0/monitor/…`), que da una **tasa de datos** por dispositivo, y la integra en el tiempo en totales diarios y de 7 días (descarga y subida por separado). Los valores son **estimaciones**, no contadores de la caja.

**Requisitos y límites:**
- En la FRITZ!Box debe estar activado **«Guardar velocidades de datos de Internet»** por dispositivo (Red doméstica → Red → dispositivo → detalles; «Dispositivos individuales» en el monitor en línea, FRITZ!OS 7.90/8.0 o posterior). Los dispositivos sin este ajuste no aparecen.
- El recuento empieza al activar la opción; la caja no entrega valores pasados. Una semana completa requiere 7 días.
- Los totales se guardan en el almacenamiento de Home Assistant (8 días). Si Home Assistant o la consulta se interrumpen un tiempo, ese tiempo falta en los totales (el diagnóstico cuenta los huecos en `traffic.stats`).
- **Unidad sin verificar:** se suponen bytes por segundo. Si las cifras no cuadran, ajuste «Unidad de los valores del monitor en línea» a bits por segundo en las opciones. El diagnóstico muestra valores crudos en `traffic.shape.sample_values` para compararlos con el monitor en línea de la caja.

**Sensores (desde 2.0.0b3):** La opción crea *Estado del consumo de datos* (diagnóstico; muestra «Datos disponibles», «Esperando mediciones», «Ninguna fuente asignada», «Sin mediciones coincidentes» o «Error de lectura»; la causa está en los atributos), *Consumo de datos 7 días (todos los dispositivos)* y *Mayor consumidor de datos (7 días)* (nombre del dispositivo, ranking de los cinco primeros en los atributos). Cada dispositivo con valores recibe además *<dispositivo> Daten 7 Tage* y *<dispositivo> Daten heute* (unidad byte, visualización en GB; descarga, subida y evolución diaria como atributos). Los sensores de dispositivo solo aparecen cuando hay valores. **Si no ves nada, mira primero el sensor de estado.**

**En la tarjeta:** columna **Datos (7 días)** con barra (un clic en el encabezado ordena por mayor consumidor); la ventana de detalle muestra «Datos (7 días)» con descarga/subida, «Datos hoy» y una evolución diaria. La columna solo aparece si hay valores; ocultar con `show_traffic: false`. La exportación CSV contiene el valor de 7 días en bytes.

---

## Ajustes DNS (experimental)

Desde 1.8.0 la integración lee los ajustes DNS de la FRITZ!Box y – solo después de activar la opción – puede modificarlos.

| Lugar en la FRITZ!Box | Campo del servicio |
| --- | --- |
| Internet → Datos de acceso → Servidor DNS (IPv4) | `internet_ipv4_custom`, `internet_ipv4_dns1`, `internet_ipv4_dns2` |
| Internet → Datos de acceso → Servidor DNS (IPv6) | `internet_ipv6_custom`, `internet_ipv6_dns1`, `internet_ipv6_dns2` |
| Red doméstica → Red → Ajustes de red → Ampliado → IPv4 | `home_ipv4_dns` |
| Red doméstica → Red → Ajustes de red → Ampliado → IPv6 | `home_ipv6_dns`, `home_ipv6_advertise` |

- `fritzbox_netzwerk.get_dns_settings` solo lee y devuelve los valores como respuesta.
- `fritzbox_netzwerk.set_dns_settings` modifica únicamente los campos que indiques. Las direcciones se validan, la caja se lee primero, se comprueba tras escribir y se restablece el estado anterior si hay discrepancia. Si la caja pide una confirmación en dos pasos, no se cambia nada.
- `dry_run: true` muestra qué cambiaría y funciona sin la opción.

**Estado de las pruebas (con honestidad):** la estructura de las respuestas `dnscfg` e `ipv6`, el inicio de sesión y el formato de escritura solo se **leyeron** en una FRITZ!Box 5690 Pro. **La escritura no está probada en ninguna caja real.** La interfaz REST (`/api/v0/generic/…`) no está documentada por AVM, no es TR-064 y puede cambiar con FRITZ!OS. Unos servidores DNS erróneos pueden perturbar la resolución de nombres en toda la red doméstica – anota antes los valores.

## Dirección IP estática (experimental)

Desde 1.8.0 la integración puede asignar una dirección IPv4 fija a un dispositivo – equivale en la FRITZ!Box a *Red doméstica → Red → editar dispositivo → «Asignar siempre la misma dirección IPv4 a este dispositivo de red»*. Activa la opción «Establecer dirección IP estática (experimental)».

- **Servicio:** `fritzbox_netzwerk.set_static_ip` con `mac`, `ip` y `dry_run: true` opcional (vista previa, funciona sin la opción).
- **Botón en la tarjeta:** en la ventana de detalles, la fila «IP estática» → *Establecer* → introducir la dirección → *Comprobar* (solo comprobación) o *Aplicar*. Se puede ocultar con `show_static_ip: false`.
- **Sin direcciones duplicadas:** la solicitud se rechaza si la dirección pertenece a otro dispositivo activo, fijo o marcado como «reservado», es la de la propia caja, está fuera de la red doméstica, es una dirección de red/difusión o no es una dirección de dispositivo válida. Un dispositivo sin conexión con la misma dirección y una dirección dentro del rango DHCP solo producen una advertencia.
- **Reinicio necesario:** la nueva dirección solo se aplica después de reiniciar el dispositivo o de volver a conectarlo a la red.
- **Red de seguridad:** tras escribir, se vuelve a leer el estado (`query.lua`, si no REST o `edit_device`). Si la asignación no está activa después, el servicio informa de un error y – si estaba activa antes – restablece el estado anterior. Un HTTP 200 por sí solo no cuenta como éxito. Si el estado no puede releerse, la respuesta indica `verified: false` con una nota.
- **Confirmación en dos pasos:** si la caja pide una confirmación, no se cambia nada. Un usuario con la confirmación adicional activada puede hacer que la caja descarte los cambios sin ningún aviso – usa para la integración un usuario sin ella.

**Cómo escribe (desde 2.0.0):** a través de la interfaz REST de la interfaz web, tal como la describe un proyecto de terceros para FRITZ!OS 8.25 (`jvejmelka/fritzbox-static-lease`): `PUT /api/v0/generic/landevice/landevice/<UID>` con `{"static_dhcp": "1"}`; la dirección deseada se añade como `"ip"`. Hasta 1.9.x la integración usaba campos de formulario de `data.lua` que solo eran *supuestos* y que la caja no aceptaba – el cambio de dirección no funcionaba. La vía antigua queda ahora solo como alternativa si la caja responde a la solicitud REST con un error HTTP (FRITZ!OS más antiguo).

**Estado de las pruebas (con honestidad):** la comprobación de duplicados y todo el flujo de escritura están cubiertos por pruebas contra una caja **simulada**. **No** probado en una FRITZ!Box real: el campo `ip` de la solicitud REST no está probado ni siquiera en el proyecto de terceros, y los nombres de campo de la alternativa son supuestos. Muchas cajas siguen notificando la dirección antigua hasta que el dispositivo se reconecta – el servicio lo indica. Si en tu caja falla, abre un issue con el texto del error y la descarga de diagnóstico.

---

## Centro de notificaciones (opcional)

Desde **1.9.2b1** (beta) la integración puede enviar mensajes al **centro de notificaciones** – una integración «Meine smarte Welt» aparte, también opcional, que recoge, ordena y entrega mensajes. **Sin el centro de notificaciones instalado no ocurre nada:** ni errores, ni entradas de registro adicionales, ni solicitudes adicionales a la FRITZ!Box.

Informa a través del bus de eventos de Home Assistant (sin MQTT, sin broker). Los textos se envían una sola vez, al registrarse, en cinco idiomas (de, en, nl, fr, es); el centro de notificaciones elige el idioma de visualización. Al arrancar solo se notifica el **estado inicial** (visible, sin push) y después solo los cambios de estado – sin repeticiones.

| Tipo de mensaje | Urgencia | Se dispara cuando … | Se cierra |
| --- | --- | --- | --- |
| Conexión con la FRITZ!Box perdida | Advertencia | falla una solicitud a la caja (las entidades pasan a la vez a «no disponible») | en la siguiente solicitud correcta |
| Dispositivo vigilado sin conexión | Info | un dispositivo vigilado ya no está activo en la lista de dispositivos | cuando vuelve a estar activo |
| Dispositivo nuevo en la red | Info | un dispositivo aparece por primera vez en la red doméstica (mismo disparador que la entidad de evento «Dispositivo nuevo») | mensaje único, permanece hasta confirmarlo en el centro de notificaciones |

**Se vigilan** exactamente los dispositivos a los que la integración ya da un estado «conectado»: los repetidores (ajuste «Crear repetidores como dispositivos propios») y los dispositivos de red elegidos por patrón de IP (ajuste «Crear dispositivos de red como dispositivos propios»). Todos los demás dispositivos solo notifican «Dispositivo nuevo».

**Ajustes** en *Configurar*: un interruptor principal «Enviar mensajes al centro de notificaciones» y una selección de «Tipos de mensaje a enviar» (ordenados por urgencia). Desactivado significa que no se envía nada, y el centro de notificaciones cierra los mensajes ya abiertos de ese tipo. Un cambio recarga la integración como cualquier otro ajuste. Los interruptores existen **solo en este diálogo**, no en la tarjeta del panel.

**Qué contienen los mensajes:** el nombre del dispositivo (en «Dispositivo nuevo» también la dirección IP), nada más – ni credenciales, ni datos del fabricante o de la conexión. La dirección MAC sirve como identificador técnico para poder cerrar un mensaje más tarde; está en el evento, no en el texto del mensaje. Ni nombres ni direcciones acaban en el registro o en la descarga de diagnóstico; esta solo lista el estado de los interruptores y cuántos mensajes por tipo se han enviado desde el arranque.

**Límites:**

- Deliberadamente **no hay retardo propio** ni umbral nuevo: si la caja notifica un dispositivo vigilado como inactivo en una consulta, el mensaje aparece y se cierra en la siguiente consulta en la que esté activo. Si resulta demasiado ruidoso, desactiva el tipo de mensaje «Dispositivo vigilado sin conexión».
- «Dispositivo nuevo» notifica un dispositivo que apareció mientras Home Assistant estaba apagado como estado inicial tras el arranque (visible, sin push). Justo después de la configuración no notifica nada – igual que la entidad de evento.
- Si el inicio de sesión falla repetidamente y Home Assistant pide una nueva autenticación, eso no es un mensaje de «conexión perdida»; Home Assistant muestra para ello su propio aviso.
- **Estado de las pruebas:** comprobado solo contra un bus de eventos **simulado** (puente y disparadores, 44 pruebas). **No** contra un centro de notificaciones real, ni en una FRITZ!Box real o en un Home Assistant en marcha. Beta: se agradecen mucho los comentarios.

---

## La tarjeta del panel

La tarjeta se entrega con la integración (`custom:fritzbox-netzwerk-card`). Tiene un editor gráfico; cada columna, filtro, la barra de control y las filas de la ventana de detalles pueden activarse o desactivarse por separado, los colores son libres, tres idiomas. La referencia completa (columnas, ordenación, filtro IP, pestañas, agrupación, exportación CSV, código QR del Wi-Fi de invitados, deslizamiento en el móvil, colores) está en el README alemán.

```yaml
type: custom:fritzbox-netzwerk-card
entity: sensor.fritz_box_5690_pro_netzwerk_gerate
title: Red doméstica
show_title: true
show_status: true
show_name: true
show_ip: true
show_mac: true
show_connection: true
show_ha_name: true
show_ip_type: true
show_vendor: false
show_band: false
show_summary: true
show_search: true
show_filter: true
default_filter: aktiv   # alle | aktiv | inaktiv | gast | gesperrt | update | fest | vpn
ip_filter: ""           # p. ej. "192.168.2.*"
show_parental: true     # fila del perfil de acceso en la ventana de detalles
show_static_ip: true    # fila de IP estática en la ventana de detalles
sort_by: ip
sort_dir: asc
```

---

## Servicios

Si hay varias cajas configuradas, todos los servicios aceptan un campo opcional `config_entry` que selecciona la caja.

| Servicio | Utilidad |
| --- | --- |
| `set_device_name` | Cambiar el nombre de un dispositivo en la caja |
| `wake_on_lan` | Despertar un dispositivo |
| `set_internet_access` (experimental) | Bloquear/permitir el acceso a Internet de un dispositivo |
| `set_mac_filter`, `start_pairing` (experimental) | Filtro MAC Wi-Fi y emparejamiento temporal |
| `reboot_mesh` (experimental) | Reiniciar repetidores y caja |
| `gast_wlan_info` | Datos del Wi-Fi de invitados (para el código QR); desde 1.9.0 se detecta el servicio de invitados y un `service` opcional (1-4) puede forzarlo; desde 1.9.1 la tarjeta transmite el número conocido y el ajuste «Servicio Wi-Fi de invitados» puede fijarlo |
| `set_device_note` | Etiqueta, nota y marca «reservado» (solo se guarda en Home Assistant) |
| `mark_devices_reserved` | Marcar muchos dispositivos como «reservados» por patrón de IP (solo en Home Assistant; `dry_run` muestra una vista previa) |
| `list_access_profiles`, `get_access_profile`, `set_access_profile` (experimental) | Perfiles del control parental |
| `get_dns_settings`, `set_dns_settings` (experimental) | Ajustes DNS de la caja |
| `set_static_ip` (experimental) | Dirección IPv4 fija para un dispositivo |
| `install_blueprints`, `update_oui` | Instalar blueprints, actualizar la lista de fabricantes |

## Blueprints

La integración incluye blueprints y un script; el botón «Instalar blueprints» los copia en tu configuración de Home Assistant. Detalles: README alemán.

---

## Indicación de versión y aviso de actualización

La versión instalada se muestra en la tarjeta (pestaña del engranaje → versión de la aplicación), en el editor de la tarjeta y en el diálogo de opciones. Si existe una versión más reciente en GitHub (comprobada una vez al día), se resalta en naranja con un enlace a las notas de la versión.

## Idiomas

Alemán, inglés y neerlandés – en el config flow, las entidades, los servicios y la tarjeta (idioma tomado de Home Assistant, alternativa: inglés). El **README** está disponible en cinco idiomas: alemán, inglés, neerlandés, francés y español (barra de idiomas al principio de cada archivo).

## Seguridad

Las acciones de escritura requieren derechos de administrador; las entradas se validan en el backend; los textos de la tarjeta se escapan. Las opciones de las funciones de escritura experimentales están **desactivadas por defecto**, y las acciones arriesgadas tienen modos de vista previa (`dry_run`) siempre que es posible.

---

## Limitaciones conocidas

- **Falta «Eliminar todas las conexiones no utilizadas»** – TR-064 no tiene una acción para ello.
- **Centro de notificaciones (desde 1.9.2b1, beta)** solo está probado contra un bus de eventos simulado, no contra un centro de notificaciones real ni hardware real; los interruptores existen solo en el diálogo Configurar, no en la tarjeta, véase [Centro de notificaciones](#centro-de-notificaciones-opcional).
- **La IP estática y la escritura de DNS son experimentales** y usan la interfaz web no documentada de la caja. La escritura no está verificada en ninguna caja real; la ruta REST de la IP estática sigue la descripción de un proyecto de terceros para FRITZ!OS 8.25. Pueden dejar de funcionar con cualquier actualización de FRITZ!OS.
- **Reservas DHCP reconocidas solo en parte.** La caja no notifica por TR-064 las reservas *dentro* del rango DHCP. Desde 2.0.0 la integración las lee además de la interfaz web (mismo ciclo que el tipo de IP, `query.lua`, si no `netDev`); que tu FRITZ!OS entregue el indicador no está probado. Si no, esos dispositivos siguen apareciendo como «dinámicos» – la descarga de diagnóstico (`reservations`) indica qué vía funcionó. Como alternativa, márcalos a mano o en bloque (`mark_devices_reserved`).
- **Mesh solo en parte:** sin intensidad de señal en dBm.
- **El volumen de datos por dispositivo** no lo ofrece la caja por TR-064.
- **Dispositivos VPN (issue #29):** las entradas sin dirección MAC se descartaban antes como obsoletas; los pares que la caja marca como VPN (indicador `X_AVM-DE_VPN` o tipo de interfaz VPN/WireGuard/IPsec) y que tienen dirección IP se conservan ahora, con el identificador `VPN:<IP>`. Aparecen en la lista y en los contadores, pero no tienen entidades ni acciones que requieran una dirección MAC (despertar, bloquear, renombrar, IP estática). **No está probado que la caja liste así los pares WireGuard**; no existe una interfaz documentada para consultarlos por separado. La descarga de diagnóstico (`box_hosts.without_mac_samples`) muestra cómo marca la caja esas entradas.
- Los dispositivos se asocian con los dispositivos de Home Assistant solo por la dirección MAC.
- La lista completa está en el README alemán.

## Solución de problemas

Solo en alemán: véase el capítulo «Fehlerbehebung» en [README.md](README.md#fehlerbehebung). Dos notas: HACS decide por sí mismo cuándo muestra una versión nueva (issue #28) – usa ⋮ → *Actualizar información* en el repositorio dentro de HACS; y para los dispositivos sin conexión que faltan (issue #24), comprueba primero el ajuste «Ocultar dispositivos desconectados» y el filtro predeterminado de la tarjeta – hasta 2.0.0 ese ajuste también vaciaba las vistas «Inactivos» y «Sin conexión desde hace tiempo». Si aún faltan dispositivos, adjunta al issue la descarga de diagnóstico y el registro de depuración – indica cuántas entradas entregó la caja (`box_hosts`). Logger: `custom_components.fritzbox_netzwerk`; la descarga de diagnóstico está anonimizada.

## Integridad de los archivos

Cada archivo `.py`, `.js` y `.yaml` empieza con una cabecera SHA-256 sobre su contenido (desde la línea 2). Se comprueba con `tail -n +2 file.py | sha256sum`. Los hashes de los archivos JSON figuran en el [README.md](README.md#datei-integrität) alemán.

## Desarrollo y pruebas

```bash
pip install fritzconnection==1.15.1 segno==1.6.6 pytest
python3 -m pytest -q tests
node tests/test_card_editor_title.js custom_components/fritzbox_netzwerk/www/fritzbox-netzwerk-card.js
```

Las pruebas de 2.0.0 (`test_issue30_dns.py`, `test_static_ip.py`, `test_vpn_and_reservations.py`, con un `conftest.py` que carga los módulos sin Home Assistant) también se entregan como paquete aparte, no en el repositorio. Se ejecutan contra una FRITZ!Box simulada.

Las pruebas de 1.9.2b1 (`test_notification_bridge.py`, `test_nc_catalog.py`, `test_coordinator_nc.py`, `test_updates_prerelease.py`, con su propio `conftest.py` que sustituye Home Assistant por dobles) se entregan con la versión como paquete aparte, no en el repositorio.

El repositorio contiene las pruebas de 1.9.0 (`tests/test_issues_1_9_0.py`, `tests/conftest.py`, `tests/test_card_editor_title.js`); se ejecutan con datos sintéticos, no con hardware real. Las pruebas de 1.8.0 para `dns_settings.py` y `static_ip.py` no están incluidas.

## Historial de versiones

### 2.0.0b5 – Monitor en línea: rutas de interfaz alternativas

**Beta (versión preliminar).** Se basa en 2.0.0b4. **No probado en una FRITZ!Box real.**

- **Corregido (intento):** una caja real respondió «bad path» a `api/v0/monitor/datasets`. La integración prueba ahora `api/v0/monitor/…` y `api/v0/generic/monitor/…` por turno, recuerda la que funciona y lista todos los errores si falla. El diagnóstico y el sensor de estado muestran `schnittstelle` y la versión de FRITZ!OS. Que alguna variante exista en tu caja no está verificado.

### 2.0.0b4 – Petición del monitor en línea: cabeceras y texto de error

**Beta (versión preliminar).** Se basa en 2.0.0b3. **No probado en una FRITZ!Box real.**

- **Corregido (intento):** la petición `api/v0/monitor/datasets` fallaba con HTTP 400 en una caja real. Ahora envía las mismas cabeceras que el script comunitario en el que se basa la interfaz (`Content-Type`, `Accept`, `Referer`). Que fuera la causa no está verificado.
- **Mejor:** ante un error HTTP, el inicio de la respuesta de la caja aparece en el sensor de estado y en el registro.

### 2.0.0b3 – Sensores de consumo de datos, sensor de estado

**Beta (versión preliminar).** Se basa en 2.0.0b2. **No probado en una FRITZ!Box real ni en un Home Assistant en marcha.**

- **Nuevo:** sensores *Estado del consumo de datos*, *Consumo de datos 7 días (todos los dispositivos)*, *Mayor consumidor de datos (7 días)* y, por dispositivo, *Daten 7 Tage* y *Daten heute* (solo con la opción activada).
- **Mejor:** el sensor de estado indica la causa cuando no aparecen valores. Si ningún contador se asignó a un dispositivo, la siguiente lectura (2 minutos) reintenta en lugar de esperar 15.

### 2.0.0b2 – Consumo de datos por dispositivo (7 días, experimental)

**Beta (versión preliminar).** Se basa en 2.0.0b1. **No probado en una FRITZ!Box real ni en un Home Assistant en marcha** – solo contra una caja simulada.

- **Nuevo (#26, en parte):** opciones «Registrar el consumo de datos» y «Unidad de los valores del monitor en línea». La integración lee las tasas de datos por dispositivo del monitor en línea, las integra en totales diarios/de 7 días (descarga, subida, hoy) y las guarda de forma permanente. Requisito: «Guardar velocidades de datos de Internet» por dispositivo en la caja. Los valores son estimaciones; unidad, longitud de ventana y asignación sin verificar. Diagnóstico: `traffic`.
- **Nuevo (tarjeta):** columna «Datos (7 días)» (ordenable, visible solo con datos, `show_traffic`), filas en la ventana de detalle con evolución diaria, exportación CSV en bytes.

### 2.0.0b1 – IP estática mediante REST, reservas y dispositivos VPN, README en cinco idiomas

**Beta (versión preliminar).** Se basa en 1.9.2b1. **Nada de esto se probó en una FRITZ!Box real ni en un Home Assistant en marcha** – solo contra una caja simulada y datos sintéticos.

- **Corregido (cambiar la dirección IP):** `set_static_ip` y la fila «IP estática» de la tarjeta no funcionaban. Causa: los campos de formulario de `data.lua` eran solo supuestos y la caja nunca los aceptó. La integración escribe ahora por la ruta REST que un proyecto de terceros documenta para FRITZ!OS 8.25 (`PUT /api/v0/generic/landevice/landevice/<UID>`), relee el resultado (`query.lua`, si no REST o `edit_device`), notifica como error un cambio ausente o descartado en silencio (con una indicación sobre la confirmación en dos pasos) y restablece una asignación anterior. La vía antigua se mantiene como alternativa. El campo `ip` de la solicitud no está probado ni siquiera en el proyecto de terceros.
- **Corregido (#30):** `set_dns_settings` seguía revirtiendo el valor IPv4 en una FRITZ!Box 6591 Cable tras 1.9.1. Causa: el valor releído se comparaba como cadena sin procesar, y la caja abrevia un único grupo de ceros de una dirección IPv6 a `::` mientras que la integración conservaba `:0:`. Las direcciones IP se comparan ahora como direcciones, tanto en la comprobación tras un error HTTP como en la comprobación final. Reproducido y corregido contra una caja simulada.
- **Corregido (#31):** los dispositivos con «Asignar dirección IPv4 permanente» dentro del rango DHCP aparecían como «dinámicos» y faltaban en el filtro «IP fija» (la caja no lo notifica por TR-064). La integración lee ahora también las reservas de la interfaz web (`query.lua`, si no `netDev`, en el ciclo de la recogida del tipo de IP) y las cuenta como fijas. **Sin probar en una caja:** los nombres de campo proceden de descripciones de proyectos de terceros; si la caja no entrega el indicador, no cambia nada. La descarga de diagnóstico muestra en `reservations` qué vía funcionó.
- **Corregido (#29, causa probable):** las entradas sin dirección MAC se descartaban como obsoletas – los pares WireGuard no tienen. Los pares marcados como VPN que tienen dirección IP se conservan ahora con el identificador `VPN:<IP>` y se muestran como activos; no tienen entidades ni acciones que dependan de la MAC. **No está probado que la caja notifique los pares WireGuard en su lista de hosts**; `box_hosts.without_mac_samples` en el diagnóstico muestra cómo los marca.
- **Corregido (#24, una causa posible):** el ajuste «Ocultar dispositivos desconectados» también vaciaba las vistas «Inactivos» y «Sin conexión desde hace tiempo». Estas vistas muestran ahora los dispositivos sin conexión; el ajuste solo se aplica a las vistas mixtas (texto de ayuda añadido). La causa no está confirmada en todos los casos notificados.
- **Nuevo:** botón de filtro **VPN** en la barra de filtros de la tarjeta (junto a «IP fija»): muestra los dispositivos que la caja marca como VPN y las entradas conservadas como `VPN:<IP>`. Se oculta con `filter_vpn: false`, es posible `default_filter: vpn`, color del icono `color_cat_vpn`. Solo comprobado con una verificación de sintaxis de la tarjeta, no en un navegador.
- **Documentación:** el README está ahora disponible en **cinco idiomas** (de, en, nl, fr, es) con una barra de idiomas al principio de cada archivo. La integración y la tarjeta siguen traducidas a de, en y nl.
- **No resuelto:** #26 (volumen de datos por dispositivo) – TR-064 no lo ofrece, el issue sigue abierto. #20 se resolvió en 1.9.1 y lo confirmó quien lo notificó; #28 es una cuestión de HACS.

### 1.9.2b1 – Centro de notificaciones (opcional), aviso de actualización para versiones preliminares

**Beta (versión preliminar).** Se basa en 1.9.1. **Nada de esto se probó contra un centro de notificaciones real, en una FRITZ!Box real ni en un Home Assistant en marcha** – el puente y los disparadores solo se ejecutan contra un bus de eventos simulado.

- **Nuevo:** conexión opcional con el **centro de notificaciones** (esquema de interfaz 1, bus de eventos, sin MQTT). Tipos de mensaje: *Conexión con la FRITZ!Box perdida* (advertencia), *Dispositivo vigilado sin conexión* (info; repetidores y dispositivos elegidos por patrón de IP) y *Dispositivo nuevo en la red* (info). Textos en cinco idiomas; al arrancar solo el estado inicial sin push. Sin el centro de notificaciones no cambia nada. Véase [Centro de notificaciones](#centro-de-notificaciones-opcional).
- **Nuevo:** dos ajustes en *Configurar*: interruptor principal y selección de los tipos de mensaje a enviar (traducciones de/en/nl). La descarga de diagnóstico lista el estado de los interruptores y un contador por tipo de mensaje, sin contenidos.
- **Mejorado:** con una beta o release candidate instalada, la comprobación de actualizaciones también tiene en cuenta las versiones preliminares (lista de versiones en lugar de `releases/latest`, que nunca devuelve versiones preliminares). Con una versión final instalada sigues viendo solo versiones finales.
- **Nota:** HACS solo muestra versiones preliminares con «Mostrar versiones beta» activado.
- **No implementado:** una sección «Centro de notificaciones» en la tarjeta del panel (engranaje). La tarjeta todavía no tiene página de ajustes ni interfaz de escritura; los interruptores están en el diálogo Configurar.

### 1.9.1 – Servicio Wi-Fi de invitados seleccionable, DNS IPv6 con HTTP 400, diagnóstico ampliado

Se basa en 1.9.0. **Nada de esto se probó en una FRITZ!Box real ni en un Home Assistant en marcha** – solo contra datos sintéticos.

- **Nuevo (#20):** ajuste **«Servicio Wi-Fi de invitados»** (automático, 1–4). La tarjeta transmite el número de servicio conocido a `gast_wlan_info` (atributo `controls.guest_service`); el interruptor de invitados y el código QR siguen el mismo número. La descarga de diagnóstico lista `wlan_service_bands`. La sugerencia del issue (servicio 4 fijo) no se adoptó porque en otras cajas la red de invitados es el servicio 3.
- **Corregido (#30):** `set_dns_settings` revertía el valor IPv4 en una FRITZ!Box 6591 Cable porque la escritura de `home_ipv6_dns` responde con HTTP 400 aunque la caja aplica el valor. Un error HTTP al escribir IPv6 cuenta ahora como escrito si la relectura muestra el valor deseado (con un `hinweis` en la respuesta); si no, no cambia nada. Sin probar en una caja.
- **Corregido (#17):** el **título de la tarjeta** volvía a «Netzwerkgeräte» en el editor al borrar el último carácter. Causa: el Home Assistant actual notifica un campo de texto vaciado como `undefined` en lugar de una cadena vacía, lo que no se reconocía como «vaciado a propósito». Ahora se permite un **título vacío**: permanece vacío, se guarda como cadena vacía y la tarjeta no muestra entonces ninguna cabecera. Una tarjeta nueva sin título sigue mostrando «Netzwerkgeräte». Probado en el navegador contra un comportamiento simulado de Home Assistant, no en un panel real.
- **Mejorado (#24):** la descarga de diagnóstico y el registro de depuración indican cuántos dispositivos entregó la caja (`box_hosts`: `raw_total`, `raw_active`, `raw_without_mac`). **La causa de la desaparición de dispositivos sin conexión no se ha encontrado ni corregido.**
- **Documentación:** solución de problemas para #28 (HACS solo muestra actualizaciones tras «Actualizar información») y #24; nota sobre dispositivos VPN (#29) en las limitaciones conocidas.
- **No implementado:** #29 (pares VPN en la lista de dispositivos) – no verificable sin caja ni datos de ejemplo; #26 (volumen de datos por dispositivo) – no disponible por TR-064; #28 es cosa de HACS, no de la integración.

### 1.9.0 – Detección de mesh, servicio Wi-Fi de invitados, marca «reservado» en bloque, inicio de sesión del repetidor

Aborda los issues abiertos de GitHub en la medida de lo posible sin una caja real. **Nada de esto se probó en una FRITZ!Box real ni en un Home Assistant en marcha** – solo contra datos sintéticos.

- **Nuevo (#27):** agrupar la lista por **conexión mesh** (`group_by: mesh`).
- **Mejorado (carga):** menos solicitudes a la FRITZ!Box. Los datos que cambian poco (banda por dispositivo, topología mesh, IP externa, velocidades de sincronización) se obtienen como máximo cada 5 minutos en lugar de en cada actualización (aproximadamente 10–20 llamadas TR-064 menos por ciclo, según la configuración). El intervalo de consulta mínimo es ahora de 30 s (antes 15 s); los valores guardados más pequeños se elevan a 30 s. El efecto está calculado, no medido en una caja ni en Home Assistant.
- **Mejorado (tarjeta):** la lista se redibuja como máximo cada `refresh_interval` segundos (15 por defecto, `0` = inmediatamente como antes), espera mientras te desplazas o interactúas y conserva la posición de desplazamiento – la tarjeta ya no salta arriba. Las pequeñas fluctuaciones de la velocidad del enlace ya no provocan un redibujado. Sin probar en un navegador (solo una prueba de Node de la limitación).
- **Corregido (#21):** faltaba la **banda Wi-Fi** de los dispositivos detrás de un repetidor; ahora se lee también de la topología mesh (nombre de interfaz como `AP:5G:0` – suposición sin probar). Una banda de la propia lista Wi-Fi de la caja tiene prioridad.
- **Corregido (#16):** **no se detectaban todos los repetidores mesh**: además del nombre del modelo, ahora cuenta cada miembro mesh según la topología (`is_meshed`) (sin probar).
- **Corregido (#20):** el **código QR del Wi-Fi de invitados** mostraba una red principal en cajas con más de tres servicios Wi-Fi. El servicio de invitados se detecta ahora (el servicio más alto desde 3 que no notifica banda; si no, 3 como antes); el interruptor de invitados sigue la misma elección; `gast_wlan_info` acepta un `service` opcional y devuelve `dienst`. La suposición «los invitados no notifican banda» no está probada.
- **Corregido (#25):** el **reinicio del repetidor** fallaba en repetidores con solo contraseña: tras un inicio de sesión rechazado, reintenta con un nombre de usuario vacío.
- **Nuevo (#22, #23):** el servicio `mark_devices_reserved` marca muchos dispositivos como «reservados» por patrón de IP (solo Home Assistant). La caja no notifica por TR-064 las reservas *dentro* del rango DHCP, por lo que esos dispositivos aparecen como «dinámicos» – un límite de la interfaz, no un error.
- **No corregido (#24):** *los dispositivos sin conexión desaparecen* – no se encontró causa en el código; la descarga de diagnóstico incluye ahora los recuentos de activos/inactivos.
- **No implementado (#26):** *volumen de datos por dispositivo* – TR-064 no ofrece tráfico por dispositivo.
- **Ya corregido, issue aún abierto (#17):** el título ya no vuelve atrás al borrar el último carácter (corregido en 1.6.3); nueva prueba `tests/test_card_editor_title.js`.

### 1.8.0 – Ajustes DNS y dirección IP estática (experimental)

- **Nuevo:** servicios `get_dns_settings` y `set_dns_settings` (opción «Cambiar los ajustes DNS de la caja (experimental)», vista previa con `dry_run`).
- **Nuevo:** servicio `set_static_ip` y fila «IP estática» en la ventana de detalles de la tarjeta (opción «Establecer dirección IP estática (experimental)»): dirección IPv4 fija con comprobación de duplicados y aviso de reinicio. Interruptor de categoría `show_static_ip`.
- **Base:** interfaz web (REST `/api/v0/generic/…` para DNS, `data.lua` para IP estática), no TR-064. **La escritura no está probada en ninguna caja real; los nombres de campo de la IP estática son supuestos.**
- Traducciones (de/en/nl) y pruebas contra cajas simuladas (47 casos).

Versiones anteriores: véase el [README.md](README.md#versionshistorie) alemán.

## Licencia

MIT
