# Dossier DEERTiME E15 (E15_EEA)

Analisi via USB di un tablet Android DEERTiME E15 con touchscreen compromesso, destinato al riuso come pannello informativo da scrivania in un homelab.
Data dell'analisi: 2026-11-08. Host: Linux (Ubuntu), libmtp 1.1.21, scrcpy 1.25, ADB.

## Sintesi

- SoC Allwinner A523, Android 14, kernel 5.15, bootloader bloccato, patch di sicurezza di maggio 2024.
- **RAM fisica reale: 3 GB.** Android riporta 6 GB e le inserzioni ne dichiarano 20 tra fisici e virtuali.
- Il tablet è stato ripristinato alle impostazioni di fabbrica e ora ha il debug USB attivo e autorizzato.
- Prima del ripristino era bloccato: esponeva solo MTP e il servizio non rispondeva. Le sezioni sul protocollo documentano quello stato.
- Supporta AOA 2.0, quindi il PC può iniettare mouse e tastiera via USB senza ADB.
- Per il riuso come pannello si consiglia di partire da Android con ambiente Linux in user space e di valutare postmarketOS come esperimento separato.

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

## Stato dopo il ripristino (misurato)

Con il debug USB attivo il tablet si presenta come `1f3a:4ee7`, con la sola interfaccia ADB (`ff/42/01`). Dati letti via ADB senza root.

| Voce | Valore |
| --- | --- |
| SoC | Allwinner A523 (`sun55iw3p1`, piattaforma `saturn`), arm64 |
| GPU | Mali-G57, OpenGL ES 3.2 |
| Android | 14 (SDK 34), primo livello API 34 |
| Patch di sicurezza | 2024-05-05 |
| Build | `E15_EEA_20240711`, tipo `user`, chiavi di release |
| Kernel | 5.15.123 (Android, build del 2024-07-11) |
| Bootloader | bloccato, verified boot `green` |
| Partizioni | A/B, Virtual A/B, dynamic partitions, Treble |
| Cifratura | per file |
| Display | 800x1280 a 60 Hz |
| Touch | `gslX680` |
| Wi-Fi | famiglia AIC8800 su SDIO (moduli `aic8800_*`) |
| PMIC | famiglia AXP2202 (`axp2202-pek`) |
| Sensori | accelerometro `sc7a20`, sensore Hall `MH248` |
| Sblocco OEM | `sys.oem_unlock_allowed=0`, `ro.oem_unlock_supported` vuoto, servizio `oem_lock` presente |

Senza root `/proc/cmdline` e `/proc/device-tree` non sono leggibili.

### RAM reale

| Fonte | Valore |
| --- | --- |
| `ro.boot.dramsize` | 3072 MB |
| Pagine presenti in `/proc/zoneinfo` | 786.432 da 4 KiB, cioè 3 GiB |
| Pagine gestite dal kernel | 729.569, circa 2,8 GiB |
| RAM usata + libera secondo `dumpsys meminfo` | circa 3,1 GB |
| `MemTotal` e "Total RAM" | 6.291.456 kB, esattamente il doppio di 3072 MB |
| Swap totale | 2.188.700 kB, zram |

Il valore di 6 GB mostrato da Android non corrisponde alla memoria fisica. I 14 GB virtuali pubblicizzati non risultano: lo swap totale è di circa 2,1 GB.

### Modalità USB osservate

| PID | Stato |
| --- | --- |
| `4ee1` | MTP |
| `4ee7` | ADB |
| `efe8` | Comparso per circa un secondo durante il ripristino. È l'ID della modalità FEL Allwinner, non ancora interrogata |

### AOA (Android Open Accessory)

`GET_PROTOCOL` (richiesta di controllo 51) restituisce la versione 2, che include l'iniezione HID. `scrcpy --otg` ha registrato mouse e tastiera senza errori, ma il primo test si è interrotto per un distacco USB, quindi la ricezione degli eventi sul tablet non è stata confermata.

## Specifiche del prodotto (dichiarato)

Da inserzioni e manuali online. La colonna a destra indica l'esito della verifica su questo esemplare.

| Voce | Valore dichiarato | Verifica |
| --- | --- | --- |
| SoC | Allwinner octa-core 1,8 GHz | A523 |
| Display | IPS 10,1" 1280x800 | 800x1280 confermato |
| RAM | 20 GB: 6 GB fisici + 14 GB virtuali | **Falso: 3 GB fisici, 2,1 GB zram** |
| Storage | 128 GB, espandibile con microSD | Non verificato |
| Fotocamere | 5 MP anteriore, 8 MP posteriore | Non verificato |
| Connettività | Wi-Fi 6, Bluetooth 5.0 | Non verificato |
| Batteria | 6000 mAh | Non verificato |
| Dimensioni e peso | circa 24,3 x 16,1 cm, 470 g | Non verificato |
| Sistema operativo | Fonti discordanti: Android 14 o 15 | Android 14 |

## Procedura di recupero

Senza hardware aggiuntivo si può provare `scrcpy --otg`, che usa AOA dal PC: cliccare nella finestra per catturare mouse e tastiera e guardare lo schermo del tablet, perché in questa modalità non c'è il mirroring.

In alternativa servono un adattatore OTG adatto alla porta del tablet, un mouse USB ed eventualmente una tastiera USB. Il supporto OTG di questo modello non è stato verificato.

1. Collegare il mouse al tablet tramite OTG e sbloccare con PIN o sequenza. La sequenza si traccia tenendo premuto il tasto sinistro.
2. Per estendere l'accesso, impostare un timeout schermo lungo o rimuovere temporaneamente il blocco.
3. **Solo file:** collegare il tablet al PC e scegliere "Trasferimento file" nella notifica USB.
4. **Controllo completo:** attivare Opzioni sviluppatore (7 tocchi su "Numero build"), poi "Debug wireless", con tablet e PC sulla stessa rete. Associare con `adb pair <ip>:<porta>`, collegare con `adb connect <ip>:<porta>` e usare `scrcpy`.

Il debug wireless evita il problema della porta unica: l'autorizzazione del debug USB comparirebbe mentre il mouse è scollegato.

### Da evitare

- Ripristino di fabbrica dal menu recovery: cancella tutti i dati.
- Copia diretta della memoria con strumenti Allwinner: su Android 14/15 i dati sono cifrati e legati alle credenziali di sblocco.
- Lasciare il tablet acceso se il touch genera tocchi fantasma: può sbagliare il PIN da solo e imporre attese crescenti.

## Riuso come pannello per homelab

Obiettivo: pannello informativo da scrivania, sempre acceso, senza bisogno del touch. La preferenza è per un client Linux.

| Strada | Sforzo | Rischio | Client Linux | Note |
| --- | --- | --- | --- | --- |
| Android + dashboard web in kiosk | Basso | Basso | No | Usa schermo, GPU e Wi-Fi già funzionanti |
| Android + Termux con Linux in user space | Medio | Basso | Parziale | Nessuno sblocco, gira sul kernel Android |
| postmarketOS con kernel mainline | Alto | Medio-alto | Completo | Dipende da bootloader, device tree e Wi-Fi |

### Strada consigliata

Partire da Android, che garantisce il pannello funzionante, e trattare postmarketOS come esperimento separato. Termux non è ancora stato provato su questo tablet.

Con 3 GB di RAM conviene evitare un desktop completo. Un compositor leggero o un browser a tutto schermo sono sufficienti.

Accorgimenti da verificare in fase di installazione:

- Tenere il tablet collegato via USB a una macchina dell'homelab: fornisce alimentazione e l'autorizzazione ADB sopravvive ai riavvii, utile dato che il touch non è affidabile.
- Android 12 e successivi possono terminare i processi di Termux in background. Il limite si può disattivare via ADB.
- Le patch sono ferme a maggio 2024: tenere il tablet su una rete isolata e non esporre servizi.
- Una batteria sempre in carica può gonfiarsi: controllarla periodicamente o alimentare il tablet tramite presa programmabile.

### Prerequisiti per postmarketOS

Stato noto: il supporto base per l'A523 è nel kernel mainline dalla 6.15. Un report di agosto 2026 su un Teclast P85T, tablet con lo stesso SoC, con Linux 7.2 indica funzionanti schermo, touch, Wi-Fi, GPU, audio e ricarica, mentre USB, Bluetooth, deep sleep e fotocamere non funzionano o non sono testati, e la RAM risulta ridotta.

Verifiche in ordine di rischio crescente:

1. Controllare in Opzioni sviluppatore se "Sblocco OEM" è presente e attivabile. Lo sblocco cancella i dati.
2. Interrogare la modalità FEL con `sunxi-tools` per capire se il secure boot è attivo.
3. Provare l'avvio da microSD con U-Boot e device tree adatti a questa scheda, senza toccare la memoria interna. Un'immagine di un altro tablet può usare tensioni e parametri RAM errati.

Punti critici: il Wi-Fi AIC8800 potrebbe richiedere un driver fuori albero e senza USB funzionante l'alternativa Ethernet viene meno. Serve inoltre un device tree specifico, ricavabile dal firmware originale.

## Verifiche ancora aperte

- Ricezione degli eventi AOA sul tablet.
- Stato dell'opzione "Sblocco OEM" e del secure boot.
- Avvio da microSD.
- Spazio reale di archiviazione e app preinstallate.
- Natura del guasto al touch, hardware o software.

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
- [Forum Manjaro: Teclast P85T con Linux 7.2](https://forum.manjaro.org/t/allwinner-h728-a523-a527-t527-initial-support-thread/173654/71)
- [linux-sunxi: A523](https://linux-sunxi.org/A523)
- [LKML: abilitazione GPU Mali su A523](https://lkml.iu.edu/hypermail/linux/kernel/2507.1/05967.html)
