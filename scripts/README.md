1. Install scripts into:
    - sudo cp scripts/pcc-aggregator /etc/systemd/system/pcc-aggregator.service
    - sudo cp scripts/pcc-monitor /etc/systemd/system/pcc-monitor.service

1. Run "sudo systemctl daemon-reload" to add the scripts

1. Turn on the services:
    - sudo systemctl enable --now pcc-aggregator.service
    - sudo systemctl enable --now pcc-monitor.service
