# Update the machine
apt-get update
apt install -y

# Install ssh
apt install openssh-server -y

# Modify the sshd_config file
sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin yes/g' /etc/ssh/sshd_config

# Restart the ssh service
sysmtectl restart ssh

# Enable ssh service
systemctl enable ssh