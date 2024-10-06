# -*- coding: utf-8 -*-

import os
import requests
import logging
import json
import zipfile
import hashlib
import tarfile 
import paramiko
import time
from datetime import datetime
import smtplib
import base64

def load_config(config_path='config.json'):
    """
    Charge la configuration à partir d'un fichier JSON.
    
    :param config_path: Chemin vers le fichier de configuration (par défaut: 'config.json')
    :return: Dictionnaire contenant la configuration
    """
    with open(config_path, 'r') as config_file:
        return json.load(config_file)

def download_zip_file(url, destination):
    """
    Télécharge un fichier ZIP depuis une URL et le sauvegarde localement.
    
    :param url: URL du fichier à télécharger
    :param destination: Chemin local où sauvegarder le fichier
    :raises Exception: Si une erreur survient lors de la vérification de l'URL ou du téléchargement
    """
    try:
        # Vérifie d'abord si l'URL est accessible
        head_response = requests.head(url, allow_redirects=True, verify=False, timeout=5)
        head_response.raise_for_status()
    except requests.RequestException as e:
        raise Exception(f"Erreur lors de la vérification de l'URL : {url}")

    try:
        # Télécharge le fichier par morceaux pour gérer les fichiers volumineux
        response = requests.get(url, stream=True, verify=False)
        response.raise_for_status()

        with open(destination, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        logging.info(f"Téléchargement réussi : {destination}")
    except requests.RequestException as e:
        raise Exception(f"Erreur lors du téléchargement : {e}")

def extract_zip(zip_path, target_file):
    """
    Extrait un fichier spécifique d'une archive ZIP.
    
    :param zip_path: Chemin vers l'archive ZIP
    :param target_file: Nom du fichier à extraire de l'archive
    :raises Exception: Si le fichier cible n'est pas trouvé dans l'archive
    """
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        if target_file in zip_ref.namelist():
            zip_ref.extract(target_file, os.path.dirname(zip_path))
            logging.info(f"Fichier extrait : {target_file}")
        else:
            raise Exception(f"{target_file} introuvable dans l'archive {zip_path}")

def calculate_file_hash(file_path):
    """
    Calcule le hash SHA256 d'un fichier.
    
    :param file_path: Chemin vers le fichier
    :return: Hash SHA256 du fichier
    """
    sha256_hash = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def save_hash(hash_value, hash_file):
    """
    Sauvegarde la valeur du hash dans un fichier.
    
    :param hash_value: Valeur du hash à sauvegarder
    :param hash_file: Chemin du fichier où sauvegarder le hash
    """
    with open(hash_file, 'w') as f:
        f.write(hash_value)

def is_new_file(current_hash, hash_file):
    """
    Vérifie si le fichier est nouveau en comparant son hash avec le dernier hash enregistré.
    
    :param current_hash: Hash du fichier actuel
    :param hash_file: Chemin du fichier contenant le dernier hash connu
    :return: True si le fichier est nouveau, False sinon
    """
    try:
        with open(hash_file, 'r') as f:
            last_hash = f.read()
            return current_hash != last_hash
    except FileNotFoundError:
        # Si le fichier n'existe pas, c'est la première exécution
        return True

def create_tgz_archive(source_file, archive_name):
    """
    Crée une archive tar.gz à partir d'un fichier source.
    
    :param source_file: Chemin du fichier à archiver
    :param archive_name: Nom de l'archive à créer
    """
    with tarfile.open(archive_name, "w:gz") as tar:
        tar.add(source_file, arcname=os.path.basename(source_file))
    logging.info(f"Archive créée : {archive_name}")

def upload_to_sftp(archive_name, server_config):
    """
    Transfère un fichier vers un serveur SFTP.
    
    :param archive_name: Nom du fichier à transférer
    :param server_config: Dictionnaire contenant la configuration du serveur SFTP
    :raises Exception: Si une erreur survient lors du transfert
    """
    try:
        transport = paramiko.Transport((server_config['hostname'], server_config['port']))
        transport.connect(username=server_config['username'], password=server_config['password'])
        sftp = paramiko.SFTPClient.from_transport(transport)

        destination = f"{server_config['destination_path']}/{archive_name}"
        # Création du dossier de destination s'il n'existe pas
        try:
            sftp.stat(server_config['destination_path'])
        except IOError:
            sftp.mkdir(server_config['destination_path'])
        sftp.put(archive_name, destination)

        logging.info(f"Fichier {archive_name} transféré avec succès vers {server_config['hostname']}")

        sftp.close()
        transport.close()
    except Exception as e:
        logging.error(f"Erreur lors du transfert SFTP : {e}")
        raise e

def clean_old_archives(retention_days, server_config):
    """
    Supprime les anciennes archives sur le serveur SFTP en fonction de la durée de rétention.
    
    :param server_config: Dictionnaire contenant la configuration du serveur SFTP
    :param retention_days: Nombre de jours de rétention des archives
    :raises Exception: Si une erreur survient lors de la suppression des archives
    """
    try:
        transport = paramiko.Transport((server_config['hostname'], server_config['port']))
        transport.connect(username=server_config['username'], password=server_config['password'])
        sftp = paramiko.SFTPClient.from_transport(transport)
        
        retention_seconds = retention_days * 24 * 60 * 60
        now = time.time()
        
        for file in sftp.listdir(server_config['destination_path']):
            file_path = os.path.join(server_config['destination_path'], file)

            if (now - datetime.strptime(file.split(".")[0], '%Y%m%d').timestamp()) > retention_seconds:
                sftp.remove(file_path)
                logging.info(f"Fichier {file} supprimé (durée de rétention dépassée).")
        
        sftp.close()
        transport.close()
    except Exception as e:
        logging.error(f"Erreur lors de l'épuration des anciennes archives : {e}")
        raise e
    
def send_email(server_config):
    """
    Send an email with an attachment using only smtplib and base64 encoding.
    
    :param server_config: A dictionary containing email server and message details
    """
    general_config = server_config

    server_config = server_config['email']
    smtp_server = server_config['smtp_server']
    smtp_port = server_config['smtp_port']
    smtp_username = server_config['smtp_username']
    smtp_password = server_config['smtp_password']
    
    from_email = server_config['from_email']
    to_email = server_config['to_email']
    
    # Read and encode the file
    with open(f"./{general_config['logs_directory_name']}/{general_config['log_file_name']}", 'rb') as file:
        file_content = file.read()
        encoded_content = base64.b64encode(file_content).decode('utf-8')

    file_name = general_config['log_file_name']

    # Construct the email
    email_message = f"""From: {from_email}
To: {to_email}
Subject: {"An error occurred during execution"}
MIME-Version: 1.0
Content-Type: multipart/mixed; boundary="boundary_string"

--boundary_string
Content-Type: text/plain; charset="utf-8"
Content-Transfer-Encoding: 7bit

Please find below the attached log file.

--boundary_string
Content-Type: application/octet-stream; name="{file_name}"
Content-Disposition: attachment; filename="{file_name}"
Content-Transfer-Encoding: base64

{encoded_content}
--boundary_string--
"""

    # Send the email
    with smtplib.SMTP(smtp_server, smtp_port) as smtp:
        smtp.starttls()
        smtp.login(smtp_username, smtp_password)
        smtp.sendmail(from_email, to_email, email_message)