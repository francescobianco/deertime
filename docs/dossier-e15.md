# Dossier DEERTiME E15 (E15_EEA)

Analisi via USB di un tablet Android DEERTiME E15 con touchscreen non funzionante e schermata di blocco attiva.
Data dell'analisi: 2026-11-08. Host: Linux (Ubuntu), libmtp 1.1.21.

## Sintesi

- Il tablet si enumera correttamente via USB ed espone una sola interfaccia, MTP.
- Il gadget MTP nel kernel risponde, ma sugli endpoint dati non risponde nessuno, nemmeno a `GetDeviceInfo`.
- Non è stato possibile leggere storage, file o versione di Android.
- Causa più probabile, non confermata: tablet bloccato o in modalità "solo ricarica", con il servizio MTP di Android non in ascolto.
- Via d'uscita consigliata: sblocco con mouse USB su adattatore OTG, poi debug wireless e `scrcpy`.

I dati sono distinti in tre livelli: **misurato** su questo esemplare, **dichiarato** da fonti esterne, **ipotesi**.

## Identità USB (misurato)

| Campo | Valore |
| --- | --- |
| VID:PID | `1f3a:4ee1` (Allwinner Technology) |
| Produttore | `DEERTiME` |
| Prodotto | `E15_EEA` |
| Seriale | `E152024HGM18xxxxxx` (ultime cifre oscurate) |
| `bcdDevice` | 4.40 |
| `bcdUSB` | 2.00 |
| Velocità | 480 Mbit/s (High Speed) |
| `bMaxPacketSize0` | 64 |
| Configurazioni | 1, 500 mA dichiarati |
| Device status | Self Powered |

### Interfaccia 0, unica presente

Classe `06/01/01` (Imaging, Still Image Capture, PTP), stringa `MTP`.

| Endpoint | Tipo | Dimensione | Note |
| --- | --- | --- | --- |
| `0x81` IN | Bulk | 512 byte | Dati e risposte |
| `0x01` OUT | Bulk | 512 byte | Comandi e dati |
| `0x82` IN | Interrupt | 28 byte | Eventi, `bInterval` 6 |

Su Linux udev la classifica `ID_MTP_DEVICE=1`, `ID_GPHOTO2=1`, `ID_MEDIA_PLAYER=1`. Nessun driver del kernel è associato, come previsto per MTP, che è gestito in user space.

## Interfacce assenti (misurato)

- ADB: `adb devices` non elenca il dispositivo, quindi il debug USB è spento.
- Fastboot: nessun dispositivo.
- Nessuna seriale (`ttyACM`/`ttyUSB`), rete USB, mass storage o UVC.
- Il PID `4ee1` non è quello della modalità FEL Allwinner, quindi il tablet è avviato normalmente.

## Comportamento del protocollo (misurato)

| Prova | Esito |
| --- | --- |
| Stringa MS OS `0xEE` (controllo) | Risponde `MSFT100`, vendor code `0x01` |
| PTP `GetDeviceInfo` (`0x1001`) | Timeout, errore 110 dopo 4 s |
| PTP `OpenSession` (`0x1002`) | Timeout, errore 110 dopo 4 s |
| Montaggio GVFS | `Impossibile aprire il dispositivo MTP` |

Sequenza ripetuta nei log di sistema a ogni tentativo:

```text
Device 0 (VID=1f3a and PID=4ee1) is UNKNOWN in libmtp v1.1.21.
PTP_ERROR_IO: failed to open session, trying again after resetting USB interface
LIBMTP libusb: Attempt to reset device
usb 3-5: reset high-speed USB device
LIBMTP PANIC: failed to open session on second attempt
Unable to mount volume E15 EEA: Impossibile aprire il dispositivo MTP
```

Il fatto che il dispositivo sia sconosciuto a libmtp non è la causa del blocco: libmtp lo riconosce comunque come MTP tramite la stringa `MSFT100` e tenta di aprire la sessione.

## Diagnosi (ipotesi)

Il kernel del tablet risponde alle richieste di controllo, mentre la parte applicativa non consuma i comandi sugli endpoint bulk. `GetDeviceInfo` di norma non richiede una sessione aperta, quindi il timeout indica che il servizio MTP di Android non è in ascolto.

Questo è coerente con le segnalazioni pubbliche su dispositivi Android bloccati o in modalità "solo ricarica". Per confermarlo serve sbloccare il tablet e selezionare "Trasferimento file". Un cavo difettoso è improbabile, dato che enumerazione e trasferimenti di controllo funzionano, ma non è escluso del tutto.

## Specifiche del prodotto (dichiarato)

Da inserzioni e manuali online, non verificate su questo esemplare.

| Voce | Valore dichiarato |
| --- | --- |
| SoC | Allwinner octa-core 1,8 GHz, modello non indicato |
| Display | IPS 10,1" 1280x800 |
| RAM | 20 GB pubblicizzati: 6 GB fisici + 14 GB virtuali |
| Storage | 128 GB, espandibile con microSD |
| Fotocamere | 5 MP anteriore, 8 MP posteriore |
| Connettività | Wi-Fi 6, Bluetooth 5.0 |
| Batteria | 6000 mAh |
| Dimensioni e peso | circa 24,3 x 16,1 cm, 470 g |
| Sistema operativo | Fonti discordanti: Android 14 o 15 |

## Procedura di recupero

Requisiti: adattatore OTG adatto alla porta del tablet, mouse USB, eventualmente tastiera USB. Il supporto OTG di questo modello non è stato verificato.

1. Collegare il mouse al tablet tramite OTG e sbloccare con PIN o sequenza. La sequenza si traccia tenendo premuto il tasto sinistro.
2. Per estendere l'accesso, impostare un timeout schermo lungo o rimuovere temporaneamente il blocco.
3. **Solo file:** collegare il tablet al PC e scegliere "Trasferimento file" nella notifica USB.
4. **Controllo completo:** attivare Opzioni sviluppatore (7 tocchi su "Numero build"), poi "Debug wireless", con tablet e PC sulla stessa rete. Associare con `adb pair <ip>:<porta>`, collegare con `adb connect <ip>:<porta>` e usare `scrcpy`.

Il debug wireless evita il problema della porta unica: l'autorizzazione del debug USB comparirebbe mentre il mouse è scollegato.

### Da evitare

- Ripristino di fabbrica dal menu recovery: cancella tutti i dati.
- Copia diretta della memoria con strumenti Allwinner: su Android 14/15 i dati sono cifrati e legati alle credenziali di sblocco.
- Lasciare il tablet acceso se il touch genera tocchi fantasma: può sbagliare il PIN da solo e imporre attese crescenti.

## Verifiche ancora aperte

Una volta ottenuto ADB:

```sh
adb shell getprop ro.product.model
adb shell getprop ro.build.version.release
adb shell getprop ro.build.version.security_patch
adb shell getprop ro.board.platform
adb shell cat /proc/meminfo
adb shell df -h /data
adb shell pm list packages
```

Servono a confermare SoC, versione di Android, patch di sicurezza, RAM fisica reale e app preinstallate.

## Riprodurre la sonda

`tools/ptp_probe.py` invia solo operazioni di lettura: `GetDeviceInfo`, `OpenSession`, `GetStorageIDs`, `GetStorageInfo`, `CloseSession`.

```sh
python3 -m venv .venv
.venv/bin/pip install pyusb
.venv/bin/python tools/ptp_probe.py
```

Quando il tablet è sbloccato e in "Trasferimento file", la sonda dovrebbe restituire modello, versione e storage.

## Fonti

- [Manuale DEERTiME E15 (B0DB22J82Z)](https://manuals.plus/asin/B0DB22J82Z)
- [Manuale DEERTiME E15 (B0FJLH79LJ)](https://manuals.plus/asin/B0FJLH79LJ)
- [Red Hat bug 840541: MTP e schermo bloccato](https://bugzilla.redhat.com/show_bug.cgi?id=840541)
- [GNOME bug 678344: dispositivo bloccato](https://bugzilla.gnome.org/show_bug.cgi?id=678344)
- [Forum Purism: modalità solo ricarica](https://forums.puri.sm/t/libmtp-error-could-not-get-file-from-device/9925)
