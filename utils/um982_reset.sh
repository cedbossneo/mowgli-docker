#!/bin/bash

DEVICE="/dev/gps"

# Fonction pour envoyer une commande proprement
send_cmd() {
    echo -ne "$1\r\n" | sudo tee "$DEVICE" > /dev/null
    sleep 0.2
}

echo "[*] RESET de l'UM980 via $DEVICE"

# Réinitialisation (FRESET)
echo "[1] Envoi de RESET..."
send_cmd 'RESET'
