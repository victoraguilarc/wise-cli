#!/bin/bash

# 	30 2 1-15 * 6 /opt/letsencrypt/renew.sh >> /opt/letsencrypt/renews.log

echo "Renewing Let's Encrypt Certificates..."
certbot renew --pre-hook "service {{ web_server }} stop" --post-hook "service {{ web_server }} start"
