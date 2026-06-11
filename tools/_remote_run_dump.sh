#!/bin/sh
set -eu
php -r 'include "/sites/www.fpsu.org.ua/configuration.php"; $c=new JConfig(); file_put_contents("/tmp/my_fpsu.cnf", "[client]\nuser=".$c->user."\npassword=".$c->password."\nhost=".$c->host."\n");'
export DB_NAME=fpsu_www
python3 /tmp/_server_dump2.py > /tmp/fpsu_full_dump.sql
ls -lh /tmp/fpsu_full_dump.sql
