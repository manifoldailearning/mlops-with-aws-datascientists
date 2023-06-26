#!/bin/bash
EC2_INSTANCE_ID=$(curl -s http://169.254.169.254/latest/meta-data/instance-id)
EC2_INSTANCE_TYPE=$(curl -s http://169.254.169.254/latest/meta-data/instance-type)
EC2_AZ=$(curl -s http://169.254.169.254/latest/meta-data/placement/availability-zone)
sed -i "s/you are on Track/This is currently runnining on $EC2_INSANCE_TYPE with id - $EC2_INSTANCE_ID on AM - $EC2_AZ/g" /var/www/html/index.html
chmod 664 /var/www/html/index.html