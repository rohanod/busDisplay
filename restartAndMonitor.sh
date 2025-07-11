#!/bin/bash

rm -f ~/busdisplay/busDisplay.log
rm -f ~/busdisplay/webui.log
sudo systemctl restart busdisplay.service
sleep 20
sudo systemctl status busdisplay.service
tail ~/busdisplay/busDisplay.log
tail ~/busdisplay/webui.log