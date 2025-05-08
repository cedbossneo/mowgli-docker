#!/bin/bash

DEVICE="/dev/gps"
BAUD_INITIAL=460800
BAUD_NEW=460800

# Fonction pour envoyer une commande proprement
send_cmd() {
    echo -ne "$1\r\n" | sudo tee "$DEVICE" > /dev/null
    sleep 0.2
}

echo "[*] Configuration de l'UM980 via $DEVICE"

# Réinitialisation (FRESET)
# echo "[1] Envoi de \$FRESET..."
# send_cmd '$FRESET'
# sleep 2

# Reconfigurer le port du RPi à 115200 pour la reprise après FRESET
#echo "[2] Reconfiguration du port $DEVICE à ${BAUD_INITIAL} bauds après FRESET..."
#stty -F "$DEVICE" $BAUD_INITIAL raw -echo -echoe -echok
#sleep 0.5

# Configuration initiale
#echo "[3] Envoi des commandes de configuration initiales..."
#send_cmd 'CONFIG SIGNALGROUP 2'
#sleep 2
#send_cmd 'CONFIG NMEA0183 V411'
#send_cmd 'MODE ROVER SURVEY MOW'
#send_cmd 'CONFIG PPP ENABLE E6-HAS'
#send_cmd 'CONFIG AGNSS DISABLE'
#send_cmd 'CONFIG SBAS DISABLE'
#send_cmd 'CONFIG RTK RELIABILITY 4 3'
#send_cmd 'CONFIG RTK TIMEOUT 600'
#send_cmd 'CONFIG PPP TIMEOUT 180'
#send_cmd 'CONFIG DGPS TIMEOUT 300'

#send_cmd 'GPGGA 0.1'
#send_cmd 'GPGSA 1'
#send_cmd 'GPGST 1'
#send_cmd 'GPGSV 1'
#send_cmd 'GPRMC 1'
#send_cmd 'GPVTG 1'

# Passage à une vitesse plus rapide (optionnel)
echo "[4] Passage à $BAUD_NEW bauds..."
send_cmd "CONFIG COM3 $BAUD_NEW"
sleep 1

# Reconfigurer le port RPi pour suivre le changement
echo "[5] Reconfiguration du port $DEVICE à ${BAUD_NEW} bauds..."
stty -F "$DEVICE" $BAUD_NEW raw -echo -echoe -echok
sleep 0.5

# Sauvegarde de la config
echo "[6] Envoi de SAVECONFIG..."
send_cmd 'SAVECONFIG'
