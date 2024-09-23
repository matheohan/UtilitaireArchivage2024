# Add Docker's official GPG key:
apt-get update
apt-get install ca-certificates curl
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc

# Add the repository to Apt sources:
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
   tee /etc/apt/sources.list.d/docker.list > /dev/null
apt-get update

# Install Docker
apt-get install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Move docker-compose 
mv docker-compose-template.yaml ../docker-compose.yaml

# Make Directory for nginx
mkdir ../nginx
cd ../nginx

# Make Directory for nginx
mkdir html
mkdir certs

# Create certificates
cd certs

# non-interactive and 10 years expiration
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -sha256 -days 3650 -nodes -subj "/C=XX/ST=StateName/L=CityName/O=CompanyName/OU=CompanySectionName/CN=CommonNameOrHostname"

# Move index.html and nginx.conf
cd .. 
mv ../UtilitaireArchivage2024/index.html html/index.html

# Move nginx.conf
mv ../UtilitaireArchivage2024/nginx.conf nginx.conf