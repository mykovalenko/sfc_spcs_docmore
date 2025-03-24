#!/bin/bash

sudo apt update
sudo apt upgrade

#sudo apt install make
#sudo apt install net-tools
#sudo apt install ssh
#sudo systemctl enable ssh

# Remove potentially pre-installed packages:
for pkg in docker.io docker-doc docker-compose docker-compose-v2 podman-docker containerd runc; do sudo apt-get remove $pkg; done

# Add Docker's official GPG key:
sudo apt-get update
sudo apt-get install ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

# Add the repository to Apt sources:
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update

# Install Docker Engine: https://docs.docker.com/engine/install/ubuntu/
sudo apt-get install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo docker run hello-world

# Install Snowflake CLI
mkdir /tmp/snowflake
cd /tmp/snowflake
wget https://sfc-repo.snowflakecomputing.com/snowflake-cli/linux_x86_64/3.3.0/snowflake-cli-3.3.0.x86_64.deb
sudo dpkg -i snowflake-cli-3.3.0.x86_64.deb

mkdir $HOME/Snowflake
cd $HOME/Snowflake
