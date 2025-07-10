#!/bin/bash

rm -f ~/busdisplay/busDisplay.log
sudo systemctl restart busdisplay.service
sleep 10
sudo systemctl status busdisplay.service
tail -f ~/busdisplay/busDisplay.log
journalctl -fu busdisplay.service