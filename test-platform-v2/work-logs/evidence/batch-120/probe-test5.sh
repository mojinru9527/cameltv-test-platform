#!/bin/bash
echo "---openvpn units---"
systemctl list-unit-files 2>/dev/null | grep -i openvpn || echo "no openvpn units"
echo "---probe 80---"
for ip in 198.18.1.2 198.18.1.43; do
  code=$(curl -s -o /dev/null -m 6 -w '%{http_code}' "http://$ip/" 2>/dev/null)
  echo "$ip:80 -> ${code:-fail}"
done
echo "---gw 80---"
curl -s -o /dev/null -m 6 -w 'gw:80 %{http_code}\n' http://10.7.7.1/ 2>&1 || true