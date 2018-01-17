#!/bin/bash
ip_list=$(cat $1 | awk '{print $3}')
for ip in $ip_list
do
    sshpass -p infrasim ssh -o StrictHostKeyChecking=no infrasim@$ip <<EOF
        sudo infrasim node stop
        sudo rm -f ~/.infrasim/default/disk-sata-0-0.img
        #sudo sync;echo 3 > /proc/sys/vm/drop_caches
        #sudo swapoff -a;swapon -a
EOF
done

sudo service rackhd stop
echo "db.dropDatabase()" | mongo pxe
sudo service rackhd start
sleep 30s

for ip in $ip_list
do
    sshpass -p infrasim ssh -o StrictHostKeyChecking=no infrasim@$ip <<EOF
        sudo infrasim node start
EOF
done
sleep 30s
#sudo sync;echo 3 > /proc/sys/vm/drop_caches
#sudo swapoff -a;swapon -a
<$1
