#!/bin/bash
( crontab -l ; echo "30 2 1-15 * 6 {{ le_path }}/renew.sh >> {{ le_path }}/renews.log" ) | sort - | uniq - | crontab -
